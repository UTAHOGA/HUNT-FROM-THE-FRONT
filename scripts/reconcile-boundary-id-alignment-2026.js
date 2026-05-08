const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');

const CANDIDATE = 'data/hunt-master-canonical-2026-database-candidate.json';
const TARGET_CANONICALS = [
  'data/hunt-master-canonical-2026-foundation.json',
  'data/hunt-master-canonical-2026-source-of-truth.json',
  'processed_data/hunt-master-canonical-2026-source-of-truth.json',
];
const INDEX_CSV = 'processed_data/display-boundary-index-2026.csv';
const INDEX_JSON = 'processed_data/display-boundary-index-2026.json';
const REPORT_JSON = `canonical/boundary-id-alignment-reconcile-2026-${STAMP}.json`;
const REPORT_MD = `docs/boundary-id-alignment-reconcile-2026-${STAMP}.md`;

function abs(file) {
  return path.join(REPO, file);
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase();
}

function clean(value) {
  return String(value || '').trim();
}

function isNumericId(value) {
  return /^\d+$/.test(clean(value));
}

function isPlaceholder5000(value) {
  return /^5\d{3,}$/.test(clean(value));
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n') {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else if (ch !== '\r') {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const headers = rows.shift().map((h) => String(h || '').trim().replace(/^\uFEFF/, ''));
  const records = rows
    .filter((values) => values.some((value) => String(value || '').trim()))
    .map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] || '']).filter(([header]) => header)));
  return { headers, records };
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\r\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function writeCsv(headers, records) {
  const rows = [headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))];
  return `${rows.map((row) => row.map(csvEscape).join(',')).join('\r\n')}\r\n`;
}

function firstMemberId(record) {
  const raw = clean(record.member_boundary_ids);
  if (!raw) return '';
  const first = raw.split(';').map((v) => clean(v)).find(Boolean) || '';
  return isNumericId(first) ? first : '';
}

function loadCandidateRows() {
  const data = JSON.parse(fs.readFileSync(abs(CANDIDATE), 'utf8'));
  if (!Array.isArray(data)) throw new Error(`${CANDIDATE} is not an array.`);
  return data;
}

function loadIndexCsv() {
  return parseCsv(fs.readFileSync(abs(INDEX_CSV), 'utf8').replace(/^\uFEFF/, ''));
}

function main() {
  const candidateRows = loadCandidateRows();
  const index = loadIndexCsv();
  const indexByCode = new Map();
  for (const row of index.records) {
    const code = normalizeCode(row.hunt_code);
    if (code) indexByCode.set(code, row);
  }

  const beforeMismatches = [];
  for (const row of candidateRows) {
    const code = normalizeCode(row.hunt_code);
    const idx = indexByCode.get(code);
    if (!idx) continue;
    const cb = clean(row.boundary_id);
    const ib = clean(idx.boundary_id);
    if (cb !== ib) beforeMismatches.push({ hunt_code: code, canonical_boundary_id: cb, index_boundary_id: ib });
  }

  const actions = {
    index_5000_to_canonical_numeric: 0,
    index_5000_to_member_numeric: 0,
    canonical_blank_to_index_numeric: 0,
    canonical_nonnumeric_to_index_numeric: 0,
    unresolved_kept: 0,
  };
  const actionRows = [];

  for (const row of candidateRows) {
    const code = normalizeCode(row.hunt_code);
    const idx = indexByCode.get(code);
    if (!idx) continue;

    let cb = clean(row.boundary_id);
    let ib = clean(idx.boundary_id);
    if (cb === ib) continue;

    const memberFirst = firstMemberId(idx);
    const cbNum = isNumericId(cb);
    const ibNum = isNumericId(ib);

    // 1) Replace placeholder 5000+ in index wherever possible.
    if (isPlaceholder5000(ib)) {
      if (cbNum) {
        idx.boundary_id = cb;
        actions.index_5000_to_canonical_numeric += 1;
        actionRows.push({ hunt_code: code, action: 'index_5000_to_canonical_numeric', from: ib, to: cb });
        continue;
      }
      if (memberFirst) {
        idx.boundary_id = memberFirst;
        ib = memberFirst;
        actions.index_5000_to_member_numeric += 1;
        actionRows.push({ hunt_code: code, action: 'index_5000_to_member_numeric', from: ib, to: memberFirst });
      } else {
        actions.unresolved_kept += 1;
        actionRows.push({ hunt_code: code, action: 'unresolved_kept', canonical_boundary_id: cb, index_boundary_id: ib });
        continue;
      }
    }

    // Refresh after potential index update.
    cb = clean(row.boundary_id);
    ib = clean(idx.boundary_id);
    if (cb === ib) continue;

    // 2) If canonical is blank and index has numeric, fill canonical.
    if (!cb && isNumericId(ib)) {
      row.boundary_id = ib;
      actions.canonical_blank_to_index_numeric += 1;
      actionRows.push({ hunt_code: code, action: 'canonical_blank_to_index_numeric', from: cb, to: ib });
      continue;
    }

    // 3) If canonical is non-numeric token and index has numeric, adopt numeric in canonical.
    if (cb && !isNumericId(cb) && isNumericId(ib)) {
      row.boundary_id = ib;
      actions.canonical_nonnumeric_to_index_numeric += 1;
      actionRows.push({ hunt_code: code, action: 'canonical_nonnumeric_to_index_numeric', from: cb, to: ib });
      continue;
    }

    actions.unresolved_kept += 1;
    actionRows.push({ hunt_code: code, action: 'unresolved_kept', canonical_boundary_id: cb, index_boundary_id: ib });
  }

  const afterMismatches = [];
  for (const row of candidateRows) {
    const code = normalizeCode(row.hunt_code);
    const idx = indexByCode.get(code);
    if (!idx) continue;
    const cb = clean(row.boundary_id);
    const ib = clean(idx.boundary_id);
    if (cb !== ib) afterMismatches.push({ hunt_code: code, canonical_boundary_id: cb, index_boundary_id: ib });
  }

  // Write updated candidate + promoted canonical targets.
  fs.writeFileSync(abs(CANDIDATE), `${JSON.stringify(candidateRows, null, 2)}\n`, 'utf8');
  for (const target of TARGET_CANONICALS) {
    fs.writeFileSync(abs(target), `${JSON.stringify(candidateRows, null, 2)}\n`, 'utf8');
  }

  // Write updated CSV index.
  fs.writeFileSync(abs(INDEX_CSV), writeCsv(index.headers, index.records), 'utf8');

  // Write updated JSON index.
  const indexJson = JSON.parse(fs.readFileSync(abs(INDEX_JSON), 'utf8'));
  const records = Array.isArray(indexJson.records) ? indexJson.records : [];
  const csvMap = new Map(index.records.map((r) => [normalizeCode(r.hunt_code), r]));
  for (const record of records) {
    const code = normalizeCode(record.hunt_code);
    const src = csvMap.get(code);
    if (!src) continue;
    record.boundary_id = clean(src.boundary_id) || null;
    const members = clean(src.member_boundary_ids);
    record.member_boundary_ids = members ? members.split(';').map((v) => clean(v)).filter(Boolean) : [];
    record.member_boundary_count = record.member_boundary_ids.length;
  }
  indexJson.generated_at = new Date().toISOString().slice(0, 10);
  fs.writeFileSync(abs(INDEX_JSON), `${JSON.stringify(indexJson, null, 2)}\n`, 'utf8');

  // Keep per-hunt GeoJSON metadata boundary IDs aligned with the index.
  const geojsonMetadataUpdates = [];
  for (const row of index.records) {
    const code = normalizeCode(row.hunt_code);
    const boundaryId = clean(row.boundary_id);
    const geoPath = clean(row.boundary_geojson_path);
    if (!code || !geoPath || !boundaryId) continue;
    const fullGeo = abs(geoPath);
    if (!fs.existsSync(fullGeo)) continue;
    try {
      const geo = JSON.parse(fs.readFileSync(fullGeo, 'utf8'));
      if (!geo || typeof geo !== 'object') continue;
      if (!geo.metadata || typeof geo.metadata !== 'object') geo.metadata = {};
      const before = clean(geo.metadata.boundary_id);
      if (before !== boundaryId) {
        geo.metadata.boundary_id = boundaryId;
        fs.writeFileSync(fullGeo, JSON.stringify(geo), 'utf8');
        geojsonMetadataUpdates.push({ hunt_code: code, file: geoPath, before, after: boundaryId });
      }
    } catch (_err) {
      // ignore parse failures here; verification script will surface hard failures.
    }
  }

  const report = {
    generated_at: new Date().toISOString(),
    source_of_truth: CANDIDATE,
    before_mismatch_count: beforeMismatches.length,
    after_mismatch_count: afterMismatches.length,
    actions,
    geojson_metadata_updates: geojsonMetadataUpdates.length,
    samples_before: beforeMismatches.slice(0, 60),
    samples_after: afterMismatches.slice(0, 60),
    sample_actions: actionRows.slice(0, 120),
    sample_geojson_metadata_updates: geojsonMetadataUpdates.slice(0, 80),
  };
  fs.writeFileSync(abs(REPORT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  const md = [
    '# Boundary ID Alignment Reconcile 2026',
    '',
    `Generated: ${report.generated_at}`,
    `Source of truth: ${CANDIDATE}`,
    '',
    `- Before mismatches: ${report.before_mismatch_count}`,
    `- After mismatches: ${report.after_mismatch_count}`,
    '',
    '## Actions',
    `- index_5000_to_canonical_numeric: ${actions.index_5000_to_canonical_numeric}`,
    `- index_5000_to_member_numeric: ${actions.index_5000_to_member_numeric}`,
    `- canonical_blank_to_index_numeric: ${actions.canonical_blank_to_index_numeric}`,
    `- canonical_nonnumeric_to_index_numeric: ${actions.canonical_nonnumeric_to_index_numeric}`,
    `- unresolved_kept: ${actions.unresolved_kept}`,
    `- geojson_metadata_updates: ${geojsonMetadataUpdates.length}`,
    '',
    'Machine report:',
    `- ${REPORT_JSON}`,
  ].join('\n');
  fs.writeFileSync(abs(REPORT_MD), `${md}\n`, 'utf8');

  console.log(JSON.stringify({
    ok: true,
    before_mismatch_count: report.before_mismatch_count,
    after_mismatch_count: report.after_mismatch_count,
    actions,
    updated_files: [
      CANDIDATE,
      ...TARGET_CANONICALS,
      INDEX_CSV,
      INDEX_JSON,
      REPORT_JSON,
      REPORT_MD,
    ],
  }, null, 2));
}

main();
