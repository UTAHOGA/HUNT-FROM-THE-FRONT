const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..', '..');
const manifestPath = path.join(repo, 'processed_data', 'boundary-manifest-2026.json');
const canonicalPath = path.join(repo, 'data', 'hunt-master-canonical-2026-source-of-truth.json');
const dwrGeoPath = path.join(repo, 'data', 'hunt_boundaries.geojson');
const conservationBundlePath = path.join(repo, 'processed_data', 'hard_data_exports', 'unit_specific_conservation_expo_bundles.csv');
const boundaryOverridePath = path.join(repo, 'processed_data', 'boundary-id-overrides-2026.json');
const officialHuntTableDir = path.join(repo, 'data');
const outGeoDir = path.join(repo, 'processed_data', 'boundaries');
const outJson = path.join(repo, 'processed_data', 'display-boundary-index-2026.json');
const outCsv = path.join(repo, 'processed_data', 'display-boundary-index-2026.csv');
const syntheticDisplayIdJson = path.join(repo, 'processed_data', 'display-boundary-synthetic-id-map-2026.json');
const syntheticDisplayIdCsv = path.join(repo, 'processed_data', 'display-boundary-synthetic-id-map-2026.csv');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
}

function normCode(value) {
  return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function normBoundaryId(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (/^-?\d+(\.\d+)?$/.test(raw)) return String(Math.trunc(Number(raw)));
  return raw;
}

function isNumericBoundaryId(value) {
  return /^\d+$/.test(String(value || '').trim());
}

function parseIdList(value) {
  if (Array.isArray(value)) {
    return [...new Set(value.map((entry) => String(entry || '').trim()).filter(Boolean))];
  }
  const text = String(value || '').trim();
  if (!text) return [];
  if ((text.startsWith('[') && text.endsWith(']')) || (text.startsWith('{') && text.endsWith('}'))) {
    try {
      return parseIdList(JSON.parse(text));
    } catch (_) {}
  }
  if (/[,|;/]/.test(text)) {
    return [...new Set(text.split(/[,|;/]/).map((entry) => String(entry || '').trim()).filter(Boolean))];
  }
  return [text];
}

function loadRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === 'object') {
    return payload.features || payload.rows || payload.records || payload.items || [];
  }
  return [];
}

function loadSyntheticDisplayIds(filePath) {
  if (!fs.existsSync(filePath)) return {};
  try {
    const payload = readJson(filePath);
    if (payload && typeof payload === 'object' && payload.ids && typeof payload.ids === 'object') {
      return payload.ids;
    }
    if (payload && typeof payload === 'object') return payload;
  } catch (_) {}
  return {};
}

function getFirstValue(obj, keys) {
  if (!obj || typeof obj !== 'object') return '';
  for (const key of keys) {
    const value = obj[key];
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return '';
}

function loadOfficialBoundaryRows(dataDir) {
  const rowsByCode = new Map();
  if (!fs.existsSync(dataDir)) return rowsByCode;
  const files = fs.readdirSync(dataDir)
    .filter((name) => /_hunt_table_official\.json$/i.test(name));
  files.forEach((fileName) => {
    const filePath = path.join(dataDir, fileName);
    let rows = [];
    try {
      rows = loadRows(readJson(filePath));
    } catch (_) {
      rows = [];
    }
    rows.forEach((row) => {
      const source = row?.attributes && typeof row.attributes === 'object' ? row.attributes : row;
      const code = normCode(getFirstValue(source, ['HUNT_NUMBER', 'hunt_number', 'hunt_code', 'HUNT_CODE', 'HuntCode']));
      const boundaryId = normBoundaryId(getFirstValue(source, ['BOUNDARYID', 'BoundaryID', 'boundary_id', 'Boundary_Id', 'boundaryId']));
      if (!code || !isNumericBoundaryId(boundaryId)) return;
      if (!rowsByCode.has(code)) rowsByCode.set(code, []);
      rowsByCode.get(code).push({
        boundary_id: boundaryId,
        boundary_name: getFirstValue(source, ['BOUNDARY_NAME', 'Boundary_Name', 'boundary_name', 'NAME', 'Name']),
        season: getFirstValue(source, ['SEASON', 'Season', 'season']),
        source_file: fileName,
      });
    });
  });
  return rowsByCode;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      row.push(cell);
      cell = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i += 1;
      row.push(cell);
      if (row.some((value) => String(value || '').trim())) rows.push(row);
      row = [];
      cell = '';
    } else {
      cell += char;
    }
  }

  row.push(cell);
  if (row.some((value) => String(value || '').trim())) rows.push(row);
  if (!rows.length) return [];

  const headers = rows[0].map((header) => String(header || '').trim());
  return rows.slice(1).map((values) => {
    const record = {};
    headers.forEach((header, index) => {
      record[header] = values[index] ?? '';
    });
    return record;
  });
}

function csvCell(value) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function main() {
  fs.mkdirSync(outGeoDir, { recursive: true });

  const manifestRows = loadRows(readJson(manifestPath));
  const canonicalRows = loadRows(readJson(canonicalPath));
  const conservationBundleRows = fs.existsSync(conservationBundlePath)
    ? parseCsv(fs.readFileSync(conservationBundlePath, 'utf8'))
    : [];
  const boundaryOverrideRows = fs.existsSync(boundaryOverridePath)
    ? loadRows(readJson(boundaryOverridePath))
    : [];
  const officialBoundaryRowsByCode = loadOfficialBoundaryRows(officialHuntTableDir);
  const dwrGeo = readJson(dwrGeoPath);
  const dwrFeatures = Array.isArray(dwrGeo.features) ? dwrGeo.features : [];

  const featuresByBoundaryId = new Map();
  dwrFeatures.forEach((feature) => {
    const props = feature && feature.properties ? feature.properties : {};
    const rawId = props.BoundaryID ?? props.BOUNDARYID ?? props.Boundary_Id ?? props.boundary_id;
    const boundaryId = normBoundaryId(rawId);
    if (!boundaryId || !isNumericBoundaryId(boundaryId)) return;
    if (!featuresByBoundaryId.has(boundaryId)) featuresByBoundaryId.set(boundaryId, []);
    featuresByBoundaryId.get(boundaryId).push(feature);
  });

  const manifestByCode = new Map();
  manifestRows.forEach((row) => {
    const code = normCode(row.hunt_code || row.huntCode || row.HUNT_CODE);
    if (code) manifestByCode.set(code, row);
  });

  const canonicalByCode = new Map();
  canonicalRows.forEach((row) => {
    const code = normCode(row.hunt_code || row.huntCode || row.code || row.HuntCode);
    if (code && !canonicalByCode.has(code)) canonicalByCode.set(code, row);
  });

  const conservationBundleByCode = new Map();
  conservationBundleRows.forEach((row) => {
    const code = normCode(row.hunt_code || row.huntCode || row.HUNT_CODE);
    if (code) conservationBundleByCode.set(code, row);
  });
  const boundaryOverrideByCode = new Map();
  boundaryOverrideRows.forEach((row) => {
    const code = normCode(row.hunt_code || row.huntCode || row.HUNT_CODE || row.HUNT_NUMBER);
    if (code) boundaryOverrideByCode.set(code, row);
  });

  const allCodes = [...new Set([
    ...canonicalByCode.keys(),
    ...manifestByCode.keys(),
    ...conservationBundleByCode.keys(),
    ...boundaryOverrideByCode.keys(),
  ])].sort();
  const records = [];
  let noGeometry = 0;
  const syntheticDisplayIds = loadSyntheticDisplayIds(syntheticDisplayIdJson);
  let nextSyntheticDisplayId = Math.max(
    4999,
    ...Object.values(syntheticDisplayIds)
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value) && value >= 5000),
  ) + 1;
  const getSyntheticDisplayBoundaryId = (code) => {
    if (!syntheticDisplayIds[code]) {
      syntheticDisplayIds[code] = String(nextSyntheticDisplayId);
      nextSyntheticDisplayId += 1;
    }
    return String(syntheticDisplayIds[code]);
  };

  allCodes.forEach((code) => {
    const manifestRow = manifestByCode.get(code) || null;
    const canonicalRow = canonicalByCode.get(code) || null;
    const conservationBundleRow = conservationBundleByCode.get(code) || null;
    const boundaryOverrideRow = boundaryOverrideByCode.get(code) || null;

    const overrideBoundaryId = normBoundaryId(boundaryOverrideRow?.boundary_id ?? boundaryOverrideRow?.BoundaryID);
    const manifestBoundaryId = normBoundaryId(manifestRow?.boundary_id ?? manifestRow?.boundaryId ?? manifestRow?.BoundaryID);
    const canonicalBoundaryId = normBoundaryId(canonicalRow?.boundary_id ?? canonicalRow?.boundaryId ?? canonicalRow?.BoundaryID ?? canonicalRow?.boundaryIdNumeric);
    const candidateBoundaryId = overrideBoundaryId || manifestBoundaryId || canonicalBoundaryId;
    const dwrBoundaryId = isNumericBoundaryId(candidateBoundaryId) ? candidateBoundaryId : '';

    const mergedBoundaryId = String(manifestRow?.merged_boundary_id || manifestRow?.mergedBoundaryId || '').trim();
    const memberBoundaryIds = parseIdList(
      manifestRow?.member_boundary_ids || manifestRow?.memberBoundaryIds || manifestRow?.dwr_member_boundary_ids || []
    ).map(normBoundaryId).filter((id) => isNumericBoundaryId(id));
    const conservationBundleBoundaryIds = parseIdList(
      conservationBundleRow?.boundary_ids || conservationBundleRow?.dwr_member_boundary_ids || conservationBundleRow?.member_boundary_ids || []
    ).map(normBoundaryId).filter((id) => isNumericBoundaryId(id));
    const overrideMemberBoundaryIds = parseIdList(
      boundaryOverrideRow?.member_boundary_ids || boundaryOverrideRow?.source_boundary_ids || []
    ).map(normBoundaryId).filter((id) => isNumericBoundaryId(id));
    const officialBoundaryRows = officialBoundaryRowsByCode.get(code) || [];
    const officialBoundaryIds = [...new Set(officialBoundaryRows.map((row) => row.boundary_id).filter((id) => isNumericBoundaryId(id)))];
    const usingConservationBundle = Boolean(conservationBundleRow && conservationBundleBoundaryIds.length);
    const usingBoundaryOverride = Boolean(boundaryOverrideRow && (dwrBoundaryId || overrideMemberBoundaryIds.length));
    const usingOfficialBoundaryRows = Boolean(!usingConservationBundle && officialBoundaryIds.length);
    let displayMemberBoundaryIds = memberBoundaryIds;
    if (overrideMemberBoundaryIds.length) {
      displayMemberBoundaryIds = overrideMemberBoundaryIds;
    } else if (conservationBundleBoundaryIds.length) {
      displayMemberBoundaryIds = conservationBundleBoundaryIds;
    } else if (officialBoundaryIds.length > 1) {
      displayMemberBoundaryIds = officialBoundaryIds;
    }
    const officialSingleBoundaryId = officialBoundaryIds.length === 1 ? officialBoundaryIds[0] : '';
    const bundleGeometryType = conservationBundleBoundaryIds.length > 1 ? 'conservation_expo_bundle' : '';

    const isComposite = Boolean(
      mergedBoundaryId
      || displayMemberBoundaryIds.length > 1
      || String(manifestRow?.boundary_geometry_type || '').toLowerCase().includes('merged')
      || bundleGeometryType
    );

    const displayBoundaryId = isComposite
      ? getSyntheticDisplayBoundaryId(code)
      : (dwrBoundaryId ? dwrBoundaryId : (officialSingleBoundaryId || getSyntheticDisplayBoundaryId(code)));
    const overrideGeoPath = String(boundaryOverrideRow?.boundary_geojson_path || '').trim();
    const manifestGeoPath = overrideGeoPath || String(manifestRow?.boundary_geojson_path || '').trim();
    const sourceBoundaryIds = isComposite
      ? displayMemberBoundaryIds
      : (dwrBoundaryId ? [dwrBoundaryId] : (officialSingleBoundaryId ? [officialSingleBoundaryId] : displayMemberBoundaryIds));
    const boundarySourceAuthority = sourceBoundaryIds.length ? 'Utah DWR' : '';
    const boundarySourceFile = usingBoundaryOverride
      ? (boundaryOverrideRow?.source_file || 'boundary-id-overrides-2026.json')
      : usingConservationBundle
      ? 'unit_specific_conservation_expo_bundles.csv'
      : (usingOfficialBoundaryRows ? [...new Set(officialBoundaryRows.map((row) => row.source_file))].join(';') : (manifestGeoPath ? 'boundary-manifest-2026.json' : (sourceBoundaryIds.length ? 'hunt_boundaries.geojson' : '')));
    const overrideGeometryType = String(boundaryOverrideRow?.boundary_geometry_type || '').trim();

    let features = [];
    if (manifestGeoPath) {
      const absoluteManifestGeoPath = path.join(repo, manifestGeoPath);
      if (fs.existsSync(absoluteManifestGeoPath)) {
        try {
          const payload = readJson(absoluteManifestGeoPath);
          features = Array.isArray(payload.features) ? payload.features : [];
        } catch (_) {}
      }
    }

    if (!features.length) {
      const geometryIds = isComposite ? displayMemberBoundaryIds : (dwrBoundaryId ? [dwrBoundaryId] : (officialSingleBoundaryId ? [officialSingleBoundaryId] : displayMemberBoundaryIds));
      const seen = new Set();
      geometryIds.forEach((id) => {
        (featuresByBoundaryId.get(id) || []).forEach((feature) => {
          const key = JSON.stringify(feature.properties || {});
          if (seen.has(key)) return;
          seen.add(key);
          features.push(feature);
        });
      });
    }

    const boundaryGeojsonPath = `processed_data/boundaries/${code}.geojson`;
    fs.writeFileSync(
      path.join(outGeoDir, `${code}.geojson`),
      JSON.stringify({
        type: 'FeatureCollection',
        metadata: {
          hunt_code: code,
          boundary_id: displayBoundaryId,
          member_boundary_ids: isComposite ? displayMemberBoundaryIds : [],
          source_boundary_ids: sourceBoundaryIds,
          source_hunt_code: code,
          merged_boundary_id: mergedBoundaryId || (bundleGeometryType ? `${code}_BUNDLE_2026` : null),
          boundary_geometry_type: overrideGeometryType || bundleGeometryType || (isComposite ? 'merged_kmz' : 'single_kmz'),
          generated_from: 'display-boundary-index-2026-builder',
          boundary_source_authority: boundarySourceAuthority || null,
          boundary_source_file: boundarySourceFile || null,
        },
        features,
      })
    );

    if (!features.length) noGeometry += 1;

    records.push({
      hunt_code: code,
      boundary_id: displayBoundaryId,
      member_boundary_ids: isComposite ? displayMemberBoundaryIds : [],
      source_boundary_ids: sourceBoundaryIds,
      boundary_source_authority: boundarySourceAuthority || null,
      boundary_source_file: boundarySourceFile || null,
      merged_boundary_id: mergedBoundaryId || (bundleGeometryType ? `${code}_BUNDLE_2026` : null),
      boundary_geometry_type: overrideGeometryType || bundleGeometryType || (isComposite ? 'merged_kmz' : 'single_kmz'),
      geometry_status: features.length ? 'mapped' : 'unavailable',
      boundary_geojson_path: boundaryGeojsonPath,
      boundary_kmz_path: boundaryOverrideRow?.boundary_kmz_path || manifestRow?.boundary_kmz_path || null,
      boundary_kml_path: boundaryOverrideRow?.boundary_kml_path || manifestRow?.boundary_kml_path || null,
      dwr_boundary_link: manifestRow?.dwr_boundary_link || null,
      member_boundary_count: isComposite ? displayMemberBoundaryIds.length : 0,
    });
  });

  const jsonDoc = {
    generated_at: new Date().toISOString().slice(0, 10),
    source: 'canonical + boundary-manifest + conservation/expo bundles + dwr-boundary-geojson',
    count: records.length,
    records,
  };
  fs.writeFileSync(outJson, JSON.stringify(jsonDoc, null, 2));

  const headers = [
    'hunt_code',
    'boundary_id',
    'member_boundary_ids',
    'source_boundary_ids',
    'boundary_source_authority',
    'boundary_source_file',
    'merged_boundary_id',
    'boundary_geometry_type',
    'geometry_status',
    'boundary_geojson_path',
    'boundary_kmz_path',
    'boundary_kml_path',
    'dwr_boundary_link',
    'member_boundary_count',
  ];
  const lines = [headers.join(',')];
  records.forEach((row) => {
    const cols = headers.map((key) => {
      const value = key === 'member_boundary_ids' || key === 'source_boundary_ids'
        ? (Array.isArray(row[key]) ? row[key].join(';') : '')
        : row[key];
      return csvCell(value);
    });
    lines.push(cols.join(','));
  });
  fs.writeFileSync(outCsv, lines.join('\n'));

  fs.writeFileSync(syntheticDisplayIdJson, JSON.stringify({
    generated_at: new Date().toISOString().slice(0, 10),
    id_range: '5000+',
    purpose: 'Internal website display geometry IDs for non-single-DWR display boundaries. These are not Utah DWR BoundaryIDs.',
    ids: Object.fromEntries(Object.entries(syntheticDisplayIds).sort(([a], [b]) => a.localeCompare(b))),
  }, null, 2));
  const syntheticLines = ['hunt_code,boundary_id'];
  Object.entries(syntheticDisplayIds)
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([code, id]) => syntheticLines.push(`${csvCell(code)},${csvCell(id)}`));
  fs.writeFileSync(syntheticDisplayIdCsv, syntheticLines.join('\n'));

  console.log(JSON.stringify({
    records: records.length,
    noGeometry,
    outJson,
    outCsv,
    syntheticDisplayIdJson,
    syntheticDisplayIdCsv,
  }, null, 2));
}

main();
