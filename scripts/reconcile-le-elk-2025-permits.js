const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PATCH_FILE = path.join(ROOT, 'processed_data', 'le_elk_2025_database_patch.csv');
const REPORT_DIR = path.join(ROOT, 'processed_data', 'le_elk_2025_reconciliation');
const WRITE_MODE = process.argv.includes('--write');
const MODE = WRITE_MODE ? 'write' : 'dry_run';
const SOURCE_LABEL = '2025 LE Elk Draw Results PDF';

const DATABASE_FIELDS = [
  'permits_2025_draw_res',
  'permits_2025_draw_nr',
  'permits_2025_draw_total',
  'permits_2025_draw_source',
];
const RUNTIME_FIELDS = [
  'permits_2025_draw_res_total',
  'permits_2025_draw_nr_total',
  'permits_2025_draw_total',
  'permits_2025_draw_res_bonus',
  'permits_2025_draw_res_regular',
  'permits_2025_draw_nr_bonus',
  'permits_2025_draw_nr_regular',
  'permits_2025_draw_bonus_total',
  'permits_2025_draw_regular_total',
  'res_success_ratio_2025',
  'nr_success_ratio_2025',
  'pdf_page',
  'dwr_report_page',
  'permits_2025_source',
];

const CSV_TARGETS = [
  {
    kind: 'database_csv',
    file: path.join(ROOT, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv', 'DATABASE.csv'),
    fields: DATABASE_FIELDS,
  },
  ...[
    path.join(ROOT, 'processed_data', 'hunt_master_enriched.csv'),
    path.join(ROOT, 'processed_data', 'hunt_unit_reference_linked.csv'),
    path.join(ROOT, 'processed_data', 'point_ladder_view.csv'),
    path.join(ROOT, 'processed_data', 'draw_reality_engine.csv'),
    path.join(ROOT, 'processed_data', 'draw_reality_engine_predictive_v2.csv'),
    path.join(ROOT, 'processed_data', 'draw_reality_engine_predictive.csv'),
    path.join(ROOT, 'data', 'hunt-master-canonical-2026-database-candidate.csv'),
  ].map((file) => ({ kind: 'runtime_csv', file, fields: RUNTIME_FIELDS })),
];

const JSON_TARGETS = [
  path.join(ROOT, 'data', 'hunt-master-canonical-2026-foundation.json'),
  path.join(ROOT, 'data', 'hunt-master-canonical-2026-source-of-truth.json'),
  path.join(ROOT, 'processed_data', 'hunt-master-canonical-2026-source-of-truth.json'),
  path.join(ROOT, 'canonical', 'hunt-planner-2026.json'),
  path.join(ROOT, 'generated', 'pages', 'hunt-planner.json'),
].map((file) => ({ kind: 'catalog_json', file, fields: RUNTIME_FIELDS }));

const CODE_TARGETS = [
  path.join(ROOT, 'hunt-research.js'),
  path.join(ROOT, 'engine', 'utah', 'point_ladder_pool.py'),
].map((file) => ({ kind: 'label_file', file }));

function relative(file) {
  return path.relative(ROOT, file).replace(/\\/g, '/');
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function timestamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

function reportRow(file, kind, overrides = {}) {
  return {
    file: relative(file),
    status: overrides.status || 'ok',
    kind,
    'rows checked': overrides.rowsChecked || 0,
    'matched rows': overrides.matchedRows || 0,
    'matched hunt codes': overrides.matchedHuntCodes || 0,
    'changed cells': overrides.changedCells || 0,
    written: Boolean(overrides.written),
    'backup path': overrides.backupPath || '',
    error: overrides.error || '',
  };
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cell += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
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

  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  if (rows.length === 0) {
    return { headers: [], records: [] };
  }

  const headers = rows[0];
  const records = rows.slice(1).filter((values) => values.some((value) => value !== '')).map((values) => {
    const record = {};
    headers.forEach((header, index) => {
      record[header] = values[index] ?? '';
    });
    return record;
  });

  return { headers, records };
}

function csvEscape(value) {
  const text = value == null ? '' : String(value);
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function writeCsv(headers, records) {
  const lines = [headers.map(csvEscape).join(',')];
  for (const record of records) {
    lines.push(headers.map((header) => csvEscape(record[header] ?? '')).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}

function loadPatch() {
  if (!fs.existsSync(PATCH_FILE)) {
    throw new Error(`Required patch file is missing: ${relative(PATCH_FILE)}`);
  }

  const parsed = parseCsv(fs.readFileSync(PATCH_FILE, 'utf8'));
  const patches = new Map();

  for (const record of parsed.records) {
    const code = normalizeCode(record.hunt_code);
    if (!code) continue;
    if (!/^EB\d+/i.test(code)) continue;
    patches.set(code, record);
  }

  return { patches, rows: parsed.records.length, ebRows: patches.size };
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase();
}

function firstValue(row, keys) {
  for (const key of keys) {
    if (row[key] != null && String(row[key]).trim() !== '') return String(row[key]);
  }
  return '';
}

function looksLikeLeElk(row) {
  const code = normalizeCode(firstValue(row, ['hunt_code', 'huntCode', 'code', 'Hunt Number', 'huntNumber']));
  if (!/^EB\d+/i.test(code)) return false;

  const joined = [
    firstValue(row, ['species', 'Species']),
    firstValue(row, ['hunt_name', 'huntName', 'name', 'title', 'Hunt Name']),
    firstValue(row, ['hunt_type', 'huntType', 'permit_type', 'permitType', 'Weapon']),
  ].join(' ').toLowerCase();

  return joined.length === 0 || joined.includes('elk') || joined.includes('bull') || joined.includes('limited entry') || joined.includes('le ');
}

function patchValue(patch, field) {
  if (field === 'permits_2025_source') return SOURCE_LABEL;
  if (field === 'permits_2025_draw_source') return SOURCE_LABEL;
  if (field === 'permits_2025_draw_res') return patch.permits_year_res || patch.permits_2025_draw_res_total || '';
  if (field === 'permits_2025_draw_nr') return patch.permits_year_nr || patch.permits_2025_draw_nr_total || '';
  if (field === 'permits_2025_draw_total') return patch.permits_year_total || patch.permits_2025_draw_total || '';
  return patch[field] == null ? '' : String(patch[field]);
}

function applyFieldPatch(row, patch, fields) {
  let changedCells = 0;
  for (const field of fields) {
    const next = patchValue(patch, field);
    if (next === '') continue;
    const previous = row[field] == null ? '' : String(row[field]);
    if (previous !== next) {
      row[field] = next;
      changedCells += 1;
    }
  }
  return changedCells;
}

function writeWithBackup(file, contents) {
  const backupPath = `${file}.backup-${timestamp()}`;
  fs.copyFileSync(file, backupPath);
  fs.writeFileSync(file, contents);
  return backupPath;
}

function reconcileCsv(target, patches) {
  if (!fs.existsSync(target.file)) {
    return reportRow(target.file, target.kind, { status: 'missing' });
  }

  const original = fs.readFileSync(target.file, 'utf8');
  const parsed = parseCsv(original);
  const headers = [...parsed.headers];
  let matchedRows = 0;
  const matchedCodes = new Set();
  let changedCells = 0;

  for (const field of target.fields) {
    if (!headers.includes(field)) headers.push(field);
  }

  for (const row of parsed.records) {
    const code = normalizeCode(firstValue(row, ['hunt_code', 'huntCode', 'code', 'Hunt Number', 'huntNumber']));
    const patch = patches.get(code);
    if (!patch || !looksLikeLeElk(row)) continue;
    matchedRows += 1;
    matchedCodes.add(code);
    changedCells += applyFieldPatch(row, patch, target.fields);
  }

  let written = false;
  let backupPath = '';
  if (WRITE_MODE && changedCells > 0) {
    backupPath = writeWithBackup(target.file, writeCsv(headers, parsed.records));
    written = true;
  }

  return reportRow(target.file, target.kind, {
    status: changedCells > 0 ? 'patched' : 'ok_no_changes',
    rowsChecked: parsed.records.length,
    matchedRows,
    matchedHuntCodes: matchedCodes.size,
    changedCells,
    written,
    backupPath: backupPath ? relative(backupPath) : '',
  });
}

function findPatchableArrays(data) {
  if (Array.isArray(data)) return [data];
  if (!data || typeof data !== 'object') return [];

  const arrays = [];
  for (const key of ['hunt_catalog', 'hunts']) {
    if (Array.isArray(data[key])) arrays.push(data[key]);
  }
  return arrays;
}

function reconcileJson(target, patches) {
  if (!fs.existsSync(target.file)) {
    return reportRow(target.file, target.kind, { status: 'missing' });
  }

  let data;
  try {
    data = JSON.parse(fs.readFileSync(target.file, 'utf8'));
  } catch (error) {
    return reportRow(target.file, target.kind, { status: 'error', error: error.message });
  }

  const arrays = findPatchableArrays(data);
  let rowsChecked = 0;
  let matchedRows = 0;
  const matchedCodes = new Set();
  let changedCells = 0;

  for (const array of arrays) {
    for (const item of array) {
      rowsChecked += 1;
      if (!item || typeof item !== 'object') continue;
      const code = normalizeCode(firstValue(item, ['hunt_code', 'huntCode', 'code']));
      const patch = patches.get(code);
      if (!patch || !looksLikeLeElk(item)) continue;
      matchedRows += 1;
      matchedCodes.add(code);
      changedCells += applyFieldPatch(item, patch, target.fields);
    }
  }

  let written = false;
  let backupPath = '';
  if (WRITE_MODE && changedCells > 0) {
    backupPath = writeWithBackup(target.file, `${JSON.stringify(data, null, 2)}\n`);
    written = true;
  }

  return reportRow(target.file, target.kind, {
    status: arrays.length === 0 ? 'no_supported_catalog_array' : (changedCells > 0 ? 'patched' : 'ok_no_changes'),
    rowsChecked,
    matchedRows,
    matchedHuntCodes: matchedCodes.size,
    changedCells,
    written,
    backupPath: backupPath ? relative(backupPath) : '',
  });
}

function reconcileLabels(target) {
  if (!fs.existsSync(target.file)) {
    return reportRow(target.file, target.kind, { status: 'missing' });
  }

  const original = fs.readFileSync(target.file, 'utf8');
  const updated = original
    .replace(/2025 Actual Odds/g, '2025 Draw Results')
    .replace(/2026 Max Pool/g, '2026 Max Point Pool');
  const changedCells = original === updated ? 0 : (original.match(/2025 Actual Odds|2026 Max Pool/g) || []).length;

  let written = false;
  let backupPath = '';
  if (WRITE_MODE && changedCells > 0) {
    backupPath = writeWithBackup(target.file, updated);
    written = true;
  }

  return reportRow(target.file, target.kind, {
    status: changedCells > 0 ? 'patched' : 'ok_no_changes',
    rowsChecked: 1,
    matchedRows: changedCells > 0 ? 1 : 0,
    matchedHuntCodes: 0,
    changedCells,
    written,
    backupPath: backupPath ? relative(backupPath) : '',
  });
}

function writeReports(rows, patchInfo, hadError) {
  ensureDir(REPORT_DIR);
  const jsonPath = path.join(REPORT_DIR, `le_elk_2025_reconciliation_${MODE}.json`);
  const csvPath = path.join(REPORT_DIR, `le_elk_2025_reconciliation_${MODE}_summary.csv`);
  const report = {
    mode: MODE,
    generated_at: new Date().toISOString(),
    patch_file: relative(PATCH_FILE),
    patch_rows: patchInfo?.rows || 0,
    patch_eb_hunt_codes: patchInfo?.ebRows || 0,
    had_error: hadError,
    rows,
  };
  const headers = ['file', 'status', 'kind', 'rows checked', 'matched rows', 'matched hunt codes', 'changed cells', 'written', 'backup path', 'error'];
  fs.writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`);
  fs.writeFileSync(csvPath, writeCsv(headers, rows));
  return { jsonPath, csvPath };
}

function main() {
  const rows = [];
  let patchInfo = null;
  let hadError = false;

  try {
    patchInfo = loadPatch();
  } catch (error) {
    hadError = true;
    rows.push(reportRow(PATCH_FILE, 'patch_csv', { status: 'error', error: error.message }));
    const outputs = writeReports(rows, patchInfo, hadError);
    console.error(error.message);
    console.error(`Wrote ${relative(outputs.jsonPath)} and ${relative(outputs.csvPath)}`);
    process.exitCode = 1;
    return;
  }

  for (const target of CSV_TARGETS) {
    try {
      rows.push(reconcileCsv(target, patchInfo.patches));
    } catch (error) {
      hadError = true;
      rows.push(reportRow(target.file, target.kind, { status: 'error', error: error.message }));
    }
  }

  for (const target of JSON_TARGETS) {
    try {
      rows.push(reconcileJson(target, patchInfo.patches));
    } catch (error) {
      hadError = true;
      rows.push(reportRow(target.file, target.kind, { status: 'error', error: error.message }));
    }
  }

  for (const target of CODE_TARGETS) {
    try {
      rows.push(reconcileLabels(target));
    } catch (error) {
      hadError = true;
      rows.push(reportRow(target.file, target.kind, { status: 'error', error: error.message }));
    }
  }

  const outputs = writeReports(rows, patchInfo, hadError);
  const totalChangedCells = rows.reduce((sum, row) => sum + Number(row['changed cells'] || 0), 0);
  const totalWritten = rows.filter((row) => row.written).length;

  console.log(`Mode: ${MODE}`);
  console.log(`Patch EB hunt codes: ${patchInfo.ebRows}`);
  console.log(`Changed cells: ${totalChangedCells}`);
  console.log(`Files written: ${totalWritten}`);
  console.log(`Reports: ${relative(outputs.jsonPath)}, ${relative(outputs.csvPath)}`);

  if (hadError) process.exitCode = 1;
}

main();
