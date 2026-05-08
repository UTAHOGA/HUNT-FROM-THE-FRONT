const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const DATABASE = 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv';
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');
const BACKUP_DIR = `processed_data/backups/permit_sync_${STAMP}`;
const REPORT_JSON = `processed_data/permit_sync_2026_published_report_${STAMP}.json`;
const REPORT_MD = `processed_data/permit_sync_2026_published_report_${STAMP}.md`;

const SOURCE_LABEL = 'DATABASE_2026_DWR_APPROVED_PUBLISHED_PERMITS';

const CSV_TARGETS = [
  {
    file: 'processed_data/hunt_master_enriched.csv',
    requireColumns: ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total', 'permits_2026_source', 'public_permits_2026_source'],
    updatePublicPermits: true,
  },
  {
    file: 'processed_data/hunt_unit_reference_linked.csv',
    requireColumns: ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total', 'permits_2026_source', 'public_permits_2026_source'],
    updatePublicPermits: true,
  },
  {
    file: 'processed_data/draw_reality_engine.csv',
    requireColumns: ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total', 'permits_2026_source'],
    updatePublicPermits: true,
  },
  {
    file: 'processed_data/point_ladder_view.csv',
    requireColumns: ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total', 'permits_2026_source'],
    updatePublicPermits: false,
  },
];

const JSON_TARGETS = [
  'data/hunt-master-canonical-2026-database-candidate.json',
  'data/hunt-master-canonical-2026-foundation.json',
  'data/hunt-master-canonical-2026-source-of-truth.json',
  'processed_data/hunt-master-canonical-2026-source-of-truth.json',
  'canonical/hunt-planner-2026.json',
  'generated/pages/hunt-planner.json',
];

function abs(file) {
  return path.join(REPO, file);
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
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map(header => String(header || '').trim().replace(/^\uFEFF/, ''));
  const records = rows
    .filter(values => values.some(value => String(value || '').trim()))
    .map(values => Object.fromEntries(headers.map((header, index) => [header, values[index] || '']).filter(([header]) => header)));
  return { headers, records };
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\r\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function writeCsv(headers, records) {
  return `${[headers, ...records.map(record => headers.map(header => record[header] || ''))]
    .map(row => row.map(csvEscape).join(','))
    .join('\r\n')}\r\n`;
}

function readCsv(file) {
  return parseCsv(fs.readFileSync(abs(file), 'utf8').replace(/^\uFEFF/, ''));
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase();
}

function normalizeResidency(value) {
  const text = String(value || '').trim().toLowerCase();
  if (text.startsWith('non')) return 'Nonresident';
  if (text.startsWith('res')) return 'Resident';
  return '';
}

function cleanPermit(value) {
  const text = String(value ?? '').trim();
  if (!text) return '';
  const numeric = text.match(/-?\d+(?:\.\d+)?/);
  if (!numeric) return text;
  const n = Number(numeric[0]);
  return Number.isFinite(n) ? String(Math.trunc(n)) : text;
}

function permitsForPublic(row, residency) {
  if (residency === 'Nonresident') return cleanPermit(row.permits_2026_nr) || cleanPermit(row.permits_2026_total);
  if (residency === 'Resident') return cleanPermit(row.permits_2026_res) || cleanPermit(row.permits_2026_total);
  return cleanPermit(row.permits_2026_total) || cleanPermit(row.permits_2026_res) || cleanPermit(row.permits_2026_nr);
}

function updateValue(record, field, value, changes) {
  const before = String(record[field] ?? '').trim();
  const after = String(value ?? '').trim();
  if (!after) return;
  if (before !== after) {
    record[field] = after;
    changes.push({ field, before, after });
  }
}

function databaseIndex() {
  const parsed = readCsv(DATABASE);
  const index = new Map();
  for (const row of parsed.records) {
    const code = normalizeCode(row.hunt_code);
    if (!code) continue;
    index.set(code, {
      ...row,
      permits_2026_res: cleanPermit(row.permits_2026_res),
      permits_2026_nr: cleanPermit(row.permits_2026_nr),
      permits_2026_total: cleanPermit(row.permits_2026_total),
    });
  }
  return { ...parsed, index };
}

function backup(file) {
  const dest = abs(path.join(BACKUP_DIR, file));
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(abs(file), dest);
}

function syncCsv(target, db) {
  const parsed = readCsv(target.file);
  const headers = [...parsed.headers];
  const addedColumns = [];
  for (const col of target.requireColumns) {
    if (!headers.includes(col)) {
      headers.push(col);
      addedColumns.push(col);
    }
  }
  const rowChanges = [];
  let matchedRows = 0;
  for (let index = 0; index < parsed.records.length; index += 1) {
    const record = parsed.records[index];
    for (const header of headers) {
      if (record[header] === undefined) record[header] = '';
    }
    const code = normalizeCode(record.hunt_code || record.huntCode || record.code);
    if (!code || !db.index.has(code)) continue;
    const truth = db.index.get(code);
    matchedRows += 1;
    const changes = [];
    updateValue(record, 'permits_2026_res', truth.permits_2026_res, changes);
    updateValue(record, 'permits_2026_nr', truth.permits_2026_nr, changes);
    updateValue(record, 'permits_2026_total', truth.permits_2026_total, changes);
    if (truth.permits_2026_res || truth.permits_2026_nr || truth.permits_2026_total) {
      updateValue(record, 'permits_2026_source', SOURCE_LABEL, changes);
    }
    if (target.updatePublicPermits) {
      const residency = normalizeResidency(record.residency);
      const publicPermit = permitsForPublic(truth, residency);
      updateValue(record, 'public_permits_2026', publicPermit, changes);
      if (publicPermit) updateValue(record, 'public_permits_2026_source', SOURCE_LABEL, changes);
    }
    if (changes.length) rowChanges.push({ row_number: index + 2, hunt_code: code, changes });
  }
  if (rowChanges.length || addedColumns.length) {
    backup(target.file);
    fs.writeFileSync(abs(target.file), writeCsv(headers, parsed.records), 'utf8');
  }
  return {
    file: target.file,
    rows: parsed.records.length,
    matched_rows: matchedRows,
    added_columns: addedColumns,
    changed_rows: rowChanges.length,
    changed_cells: rowChanges.reduce((sum, row) => sum + row.changes.length, 0),
    changes: rowChanges,
  };
}

function arrayFromJsonTarget(file, data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.hunt_catalog)) return data.hunt_catalog;
  if (Array.isArray(data.hunts)) return data.hunts;
  if (data.hunt_planner && Array.isArray(data.hunt_planner.hunts)) return data.hunt_planner.hunts;
  return [];
}

function syncJson(file, db) {
  if (!fs.existsSync(abs(file))) return { file, skipped: true, reason: 'missing file' };
  const data = JSON.parse(fs.readFileSync(abs(file), 'utf8'));
  const rows = arrayFromJsonTarget(file, data);
  const changes = [];
  for (let index = 0; index < rows.length; index += 1) {
    const record = rows[index];
    const code = normalizeCode(record.hunt_code || record.huntCode || record.code);
    if (!code || !db.index.has(code)) continue;
    const truth = db.index.get(code);
    const rowChanges = [];
    updateValue(record, 'permits_2026_res', truth.permits_2026_res, rowChanges);
    updateValue(record, 'permits_2026_nr', truth.permits_2026_nr, rowChanges);
    updateValue(record, 'permits_2026_total', truth.permits_2026_total, rowChanges);
    if (truth.permits_2026_res || truth.permits_2026_nr || truth.permits_2026_total) {
      updateValue(record, 'permits_2026_source', SOURCE_LABEL, rowChanges);
    }
    if (rowChanges.length) changes.push({ index, hunt_code: code, changes: rowChanges });
  }
  if (changes.length) {
    backup(file);
    fs.writeFileSync(abs(file), `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  }
  return {
    file,
    rows: rows.length,
    changed_rows: changes.length,
    changed_cells: changes.reduce((sum, row) => sum + row.changes.length, 0),
    changes,
  };
}

function markdown(report) {
  const lines = [
    '# 2026 Published Permit Sync Report',
    '',
    `Generated: ${report.generated_at}`,
    '',
    `Permit source: ${SOURCE_LABEL}`,
    `Backup directory: ${report.backup_dir}`,
    '',
    'These values are 2026 DWR approved/published permit allotments from DATABASE.csv. They are intentionally separate from 2025 draw-result permits, historical odds, and harvest-report metrics.',
    '',
    '## CSV Targets',
    '',
    '| File | Rows | Matched | Added columns | Changed rows | Changed cells |',
    '| --- | ---: | ---: | --- | ---: | ---: |',
    ...report.csv_results.map(item => `| ${item.file} | ${item.rows} | ${item.matched_rows} | ${item.added_columns.join(', ')} | ${item.changed_rows} | ${item.changed_cells} |`),
    '',
    '## JSON Targets',
    '',
    '| File | Rows | Changed rows | Changed cells |',
    '| --- | ---: | ---: | ---: |',
    ...report.json_results.map(item => `| ${item.file} | ${item.rows || 0} | ${item.changed_rows || 0} | ${item.changed_cells || 0} |`),
    '',
  ];
  return `${lines.join('\n')}\n`;
}

const db = databaseIndex();
const csvResults = CSV_TARGETS.map(target => syncCsv(target, db));
const jsonResults = JSON_TARGETS.map(file => syncJson(file, db));
const report = {
  generated_at: new Date().toISOString(),
  source_label: SOURCE_LABEL,
  database_file: DATABASE,
  database_rows: db.records.length,
  database_unique_codes: db.index.size,
  backup_dir: BACKUP_DIR,
  csv_results: csvResults,
  json_results: jsonResults,
  totals: {
    csv_changed_cells: csvResults.reduce((sum, item) => sum + item.changed_cells, 0),
    json_changed_cells: jsonResults.reduce((sum, item) => sum + (item.changed_cells || 0), 0),
  },
};

fs.mkdirSync(path.dirname(abs(REPORT_JSON)), { recursive: true });
fs.writeFileSync(abs(REPORT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
fs.writeFileSync(abs(REPORT_MD), markdown(report), 'utf8');

console.log(JSON.stringify({
  ok: true,
  source_label: SOURCE_LABEL,
  backup_dir: BACKUP_DIR,
  csv_changed_cells: report.totals.csv_changed_cells,
  json_changed_cells: report.totals.json_changed_cells,
  report_json: REPORT_JSON,
  report_md: REPORT_MD,
}, null, 2));
