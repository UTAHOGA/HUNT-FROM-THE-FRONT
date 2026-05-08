const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const displayIndexPath = path.join(repo, 'processed_data', 'display-boundary-index-2026.json');
const syntheticIdMapPath = path.join(repo, 'processed_data', 'display-boundary-synthetic-id-map-2026.json');
const boundaryDir = path.join(repo, 'processed_data', 'boundaries');
const officialTableDir = path.join(repo, 'data');
const reportJson = path.join(repo, 'processed_data', 'boundary_id_render_map_verification_2026.json');
const reportMd = path.join(repo, 'processed_data', 'boundary_id_render_map_verification_2026.md');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeId(value) {
  const raw = String(value ?? '').trim();
  if (!raw) return '';
  return /^-?\d+(\.\d+)?$/.test(raw) ? String(Math.trunc(Number(raw))) : raw;
}

function isNumeric(value) {
  return /^\d+$/.test(String(value ?? '').trim());
}

function loadRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === 'object') return payload.rows || payload.records || payload.items || [];
  return [];
}

function firstValue(obj, keys) {
  if (!obj || typeof obj !== 'object') return '';
  for (const key of keys) {
    const value = obj[key];
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return '';
}

function loadOfficialBoundaryIdsByCode() {
  const byCode = new Map();
  if (!fs.existsSync(officialTableDir)) return byCode;
  const files = fs.readdirSync(officialTableDir).filter((name) => /_hunt_table_official\.json$/i.test(name));
  files.forEach((fileName) => {
    const filePath = path.join(officialTableDir, fileName);
    let rows = [];
    try {
      rows = loadRows(readJson(filePath));
    } catch (_) {
      rows = [];
    }
    rows.forEach((row) => {
      const source = row?.attributes && typeof row.attributes === 'object' ? row.attributes : row;
      const code = firstValue(source, ['HUNT_NUMBER', 'hunt_number', 'hunt_code', 'HUNT_CODE', 'HuntCode']).toUpperCase().replace(/[^A-Z0-9]/g, '');
      const boundaryId = normalizeId(firstValue(source, ['BOUNDARYID', 'BoundaryID', 'boundary_id', 'Boundary_Id', 'boundaryId']));
      if (!code || !isNumeric(boundaryId)) return;
      if (!byCode.has(code)) byCode.set(code, new Set());
      byCode.get(code).add(boundaryId);
    });
  });
  return byCode;
}

function fail(list, code, reason, detail = {}) {
  list.push({ hunt_code: code || '', reason, ...detail });
}

function main() {
  const displayIndex = readJson(displayIndexPath);
  const syntheticIdMap = fs.existsSync(syntheticIdMapPath) ? readJson(syntheticIdMapPath) : { ids: {} };
  const rows = asArray(displayIndex.records);
  const syntheticIds = syntheticIdMap.ids || {};
  const officialBoundaryIdsByCode = loadOfficialBoundaryIdsByCode();
  const failures = [];
  const warnings = [];
  const unavailableRows = [];
  const seenBoundaryIds = new Map();
  let singleBoundaryRows = 0;
  let syntheticBoundaryRows = 0;
  let mappedRows = 0;

  rows.forEach((row) => {
    const code = String(row.hunt_code || '').trim().toUpperCase();
    const boundaryId = normalizeId(row.boundary_id);
    const memberIds = asArray(row.member_boundary_ids).map(normalizeId).filter(Boolean);
    const sourceIds = asArray(row.source_boundary_ids).map(normalizeId).filter(Boolean);
    const geometryStatus = String(row.geometry_status || '').trim();
    const geoPath = String(row.boundary_geojson_path || '').trim();
    const geometryType = String(row.boundary_geometry_type || '').trim();

    if (!code) fail(failures, code, 'missing_hunt_code');
    if (!boundaryId) fail(failures, code, 'missing_boundary_id');
    if (boundaryId && !isNumeric(boundaryId)) fail(failures, code, 'boundary_id_not_numeric', { boundary_id: boundaryId });
    if ('display_boundary_id' in row) fail(failures, code, 'deprecated_display_boundary_id_field_present');
    if ('dwr_boundary_id' in row) fail(failures, code, 'deprecated_dwr_boundary_id_field_present');

    if (boundaryId) {
      if (!seenBoundaryIds.has(boundaryId)) seenBoundaryIds.set(boundaryId, []);
      seenBoundaryIds.get(boundaryId).push(code);
    }

    const isSynthetic = syntheticIds[code] === boundaryId;
    if (isSynthetic) {
      syntheticBoundaryRows += 1;
    } else {
      singleBoundaryRows += 1;
      if (!sourceIds.includes(boundaryId)) {
        fail(warnings, code, 'single_boundary_source_ids_do_not_echo_boundary_id', {
          boundary_id: boundaryId,
          source_boundary_ids: sourceIds,
        });
      }
    }

    if (geometryStatus === 'mapped') mappedRows += 1;
    if (geometryStatus !== 'mapped') {
      unavailableRows.push({
        hunt_code: code,
        boundary_id: boundaryId,
        geometry_status: geometryStatus || 'missing',
        boundary_geojson_path: geoPath || null,
      });
    }

    const officialIds = officialBoundaryIdsByCode.has(code)
      ? [...officialBoundaryIdsByCode.get(code)].sort((a, b) => Number(a) - Number(b))
      : [];
    if (officialIds.length === 1 && isSynthetic && boundaryId !== officialIds[0]) {
      fail(failures, code, 'official_single_boundary_id_not_used', {
        boundary_id: boundaryId,
        official_boundary_id: officialIds[0],
      });
    }
    if (officialIds.length > 1 && isSynthetic) {
      const sortedMemberIds = memberIds.slice().sort((a, b) => Number(a) - Number(b));
      if (sortedMemberIds.join(';') !== officialIds.join(';')) {
        fail(failures, code, 'official_multi_boundary_ids_not_preserved_as_members', {
          boundary_id: boundaryId,
          member_boundary_ids: sortedMemberIds,
          official_boundary_ids: officialIds,
        });
      }
    }
    if (geoPath) {
      const absoluteGeoPath = path.join(repo, geoPath);
      if (!fs.existsSync(absoluteGeoPath)) {
        fail(failures, code, 'boundary_geojson_path_missing_file', { boundary_geojson_path: geoPath });
      } else {
        const geojson = readJson(absoluteGeoPath);
        const metadata = geojson.metadata || {};
        const featureCount = asArray(geojson.features).length;
        const metadataBoundaryId = normalizeId(metadata.boundary_id);
        const metadataMembers = asArray(metadata.member_boundary_ids).map(normalizeId).filter(Boolean);
        if (metadataBoundaryId !== boundaryId) {
          fail(failures, code, 'geojson_metadata_boundary_id_mismatch', {
            index_boundary_id: boundaryId,
            metadata_boundary_id: metadataBoundaryId,
          });
        }
        if (memberIds.join(';') !== metadataMembers.join(';')) {
          fail(failures, code, 'geojson_metadata_member_ids_mismatch', {
            index_member_boundary_ids: memberIds,
            metadata_member_boundary_ids: metadataMembers,
          });
        }
        if (geometryStatus === 'mapped' && !featureCount) {
          fail(failures, code, 'mapped_row_has_zero_geojson_features', { boundary_geojson_path: geoPath });
        }
      }
    }

    if (/UOGA_/i.test(JSON.stringify(row))) {
      fail(failures, code, 'uoga_string_present_in_public_boundary_index_row');
    }
    if (/UOGA_/i.test(JSON.stringify({ code, boundaryId, memberIds, sourceIds, geometryType }))) {
      fail(failures, code, 'uoga_string_present_in_boundary_fields');
    }
  });

  const duplicateBoundaryIds = [];
  for (const [boundaryId, codes] of seenBoundaryIds.entries()) {
    const uniqueCodes = [...new Set(codes)];
    if (Object.values(syntheticIds).includes(boundaryId) && uniqueCodes.length > 1) {
      duplicateBoundaryIds.push({ boundary_id: boundaryId, hunt_codes: uniqueCodes });
    }
  }
  duplicateBoundaryIds.forEach((entry) => fail(failures, '', 'duplicate_synthetic_boundary_id', entry));

  const report = {
    generated_at: new Date().toISOString(),
    display_index_path: path.relative(repo, displayIndexPath).replace(/\\/g, '/'),
    synthetic_id_map_path: path.relative(repo, syntheticIdMapPath).replace(/\\/g, '/'),
    rows_checked: rows.length,
    mapped_rows: mappedRows,
    single_boundary_rows: singleBoundaryRows,
    synthetic_5000_boundary_rows: syntheticBoundaryRows,
    official_hunt_codes_with_boundary_ids: officialBoundaryIdsByCode.size,
    unavailable_rows: unavailableRows.length,
    unavailable_hunt_codes: unavailableRows,
    failures,
    warnings,
    promotion_safe: failures.length === 0,
  };

  fs.writeFileSync(reportJson, JSON.stringify(report, null, 2));
  fs.writeFileSync(reportMd, [
    '# Boundary ID Render Map Verification 2026',
    '',
    `Generated: ${report.generated_at}`,
    '',
    `Rows checked: ${report.rows_checked}`,
    `Mapped rows: ${report.mapped_rows}`,
    `Single-boundary rows: ${report.single_boundary_rows}`,
    `5000-range render-boundary rows: ${report.synthetic_5000_boundary_rows}`,
    `Unavailable rows: ${report.unavailable_rows}`,
    `Failures: ${failures.length}`,
    `Warnings: ${warnings.length}`,
    `Promotion safe: ${report.promotion_safe ? 'YES' : 'NO'}`,
    '',
    '## Failures',
    failures.length ? failures.map((item) => `- ${item.hunt_code || '(global)'}: ${item.reason}`).join('\n') : '- None',
    '',
    '## Warnings',
    warnings.length ? warnings.map((item) => `- ${item.hunt_code || '(global)'}: ${item.reason}`).join('\n') : '- None',
    '',
  ].join('\n'));

  if (failures.length) {
    console.error(JSON.stringify(report, null, 2));
    process.exit(1);
  }
  console.log(JSON.stringify(report, null, 2));
}

main();
