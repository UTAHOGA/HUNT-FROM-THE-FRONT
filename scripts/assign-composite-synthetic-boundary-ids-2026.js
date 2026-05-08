const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');

const SYNTHETIC_MAP = 'processed_data/display-boundary-synthetic-id-map-2026.json';
const INDEX_CSV = 'processed_data/display-boundary-index-2026.csv';
const INDEX_JSON = 'processed_data/display-boundary-index-2026.json';
const CANDIDATE = 'data/hunt-master-canonical-2026-database-candidate.json';
const CANONICAL_TARGETS = [
  'data/hunt-master-canonical-2026-foundation.json',
  'data/hunt-master-canonical-2026-source-of-truth.json',
  'processed_data/hunt-master-canonical-2026-source-of-truth.json',
];
const REPORT_JSON = `canonical/composite-synthetic-boundary-id-assign-2026-${STAMP}.json`;
const REPORT_MD = `docs/composite-synthetic-boundary-id-assign-2026-${STAMP}.md`;

function abs(file) {
  return path.join(REPO, file);
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase();
}

function clean(value) {
  return String(value || '').trim();
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

function main() {
  const syntheticMap = JSON.parse(fs.readFileSync(abs(SYNTHETIC_MAP), 'utf8'));
  const ids = syntheticMap.ids || {};

  const indexCsv = parseCsv(fs.readFileSync(abs(INDEX_CSV), 'utf8').replace(/^\uFEFF/, ''));
  const indexRows = indexCsv.records;
  const updates = [];

  for (const row of indexRows) {
    const code = normalizeCode(row.hunt_code);
    const memberIds = clean(row.member_boundary_ids);
    if (!code || !memberIds) continue;
    const synthetic = clean(ids[code]);
    if (!synthetic) continue;
    const before = clean(row.boundary_id);
    if (before !== synthetic) {
      row.boundary_id = synthetic;
      updates.push({ hunt_code: code, from: before, to: synthetic, member_boundary_ids: memberIds });
    }
  }

  fs.writeFileSync(abs(INDEX_CSV), writeCsv(indexCsv.headers, indexRows), 'utf8');

  const indexJson = JSON.parse(fs.readFileSync(abs(INDEX_JSON), 'utf8'));
  const jsonRecords = Array.isArray(indexJson.records) ? indexJson.records : [];
  const csvByCode = new Map(indexRows.map((r) => [normalizeCode(r.hunt_code), r]));
  for (const record of jsonRecords) {
    const code = normalizeCode(record.hunt_code);
    const src = csvByCode.get(code);
    if (!src) continue;
    record.boundary_id = clean(src.boundary_id) || null;
  }
  indexJson.generated_at = new Date().toISOString().slice(0, 10);
  fs.writeFileSync(abs(INDEX_JSON), `${JSON.stringify(indexJson, null, 2)}\n`, 'utf8');

  const candidate = JSON.parse(fs.readFileSync(abs(CANDIDATE), 'utf8'));
  const candidateByCode = new Map(candidate.map((row) => [normalizeCode(row.hunt_code), row]));
  const canonicalUpdates = [];
  for (const update of updates) {
    const row = candidateByCode.get(update.hunt_code);
    if (!row) continue;
    const before = clean(row.boundary_id);
    if (before !== update.to) {
      row.boundary_id = update.to;
      canonicalUpdates.push({ hunt_code: update.hunt_code, from: before, to: update.to });
    }
  }

  fs.writeFileSync(abs(CANDIDATE), `${JSON.stringify(candidate, null, 2)}\n`, 'utf8');
  for (const target of CANONICAL_TARGETS) {
    fs.writeFileSync(abs(target), `${JSON.stringify(candidate, null, 2)}\n`, 'utf8');
  }

  const metadataUpdates = [];
  for (const update of updates) {
    const row = csvByCode.get(update.hunt_code);
    const geo = clean(row?.boundary_geojson_path);
    if (!geo) continue;
    const full = abs(geo);
    if (!fs.existsSync(full)) continue;
    const doc = JSON.parse(fs.readFileSync(full, 'utf8'));
    if (!doc.metadata || typeof doc.metadata !== 'object') doc.metadata = {};
    const before = clean(doc.metadata.boundary_id);
    if (before !== update.to) {
      doc.metadata.boundary_id = update.to;
      fs.writeFileSync(full, JSON.stringify(doc), 'utf8');
      metadataUpdates.push({ hunt_code: update.hunt_code, file: geo, from: before, to: update.to });
    }
  }

  const report = {
    generated_at: new Date().toISOString(),
    synthetic_map: SYNTHETIC_MAP,
    index_rows_checked: indexRows.length,
    composite_rows_updated: updates.length,
    canonical_rows_updated: canonicalUpdates.length,
    geojson_metadata_updated: metadataUpdates.length,
    sample_updates: updates.slice(0, 80),
    sample_canonical_updates: canonicalUpdates.slice(0, 80),
    sample_geojson_metadata_updates: metadataUpdates.slice(0, 80),
  };
  fs.writeFileSync(abs(REPORT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(abs(REPORT_MD), [
    '# Composite Synthetic Boundary ID Assignment (2026)',
    '',
    `Generated: ${report.generated_at}`,
    `Synthetic map: ${SYNTHETIC_MAP}`,
    '',
    `- Composite rows updated in display index: ${report.composite_rows_updated}`,
    `- Canonical rows updated: ${report.canonical_rows_updated}`,
    `- GeoJSON metadata rows updated: ${report.geojson_metadata_updated}`,
    '',
    `Machine report: ${REPORT_JSON}`,
  ].join('\n') + '\n', 'utf8');

  console.log(JSON.stringify({
    ok: true,
    composite_rows_updated: updates.length,
    canonical_rows_updated: canonicalUpdates.length,
    geojson_metadata_updated: metadataUpdates.length,
    report_json: REPORT_JSON,
    report_md: REPORT_MD,
  }, null, 2));
}

main();
