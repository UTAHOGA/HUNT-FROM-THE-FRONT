const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const CSV_DIR = path.join(REPO, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv');
const DATABASE_FILE = path.join(CSV_DIR, 'DATABASE.csv');
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');
const BACKUP_DIR = path.join(REPO, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'backups', `database_backfill_${STAMP}`);
const REPORT_JSON = path.join(REPO, 'processed_data', `database_backfill_report_${STAMP}.json`);
const REPORT_MD = path.join(REPO, 'processed_data', `database_backfill_report_${STAMP}.md`);

const EXCLUDED_FILES = new Set([
  'DATABASE.csv',
  'hunt_master_canonical_2026_built.csv',
  '2026_utah_dwr_hunt_matrix.csv',
]);

const FIELD_ALIASES = {
  hunt_name: ['hunt_name', 'unit', 'hunt_unit', 'name'],
  hunt_code: ['hunt_code', 'hunt_number', 'code'],
  sex_type: ['sex_type', 'sex'],
  species: ['species'],
  weapon: ['weapon'],
  hunt_type: ['hunt_type', 'hunt_class', 'draw_type'],
  season: ['season', 'season_date_text', 'season_dates'],
  permits_2026_res: ['permits_2026_res', 'res_2026_permits', 'resident_2026_permits'],
  permits_2026_nr: ['permits_2026_nr', 'permits_2026_nres', 'nr_2026_permits', 'nonres_2026_permits', 'non_res_2026_permits'],
  permits_2026_total: ['permits_2026_total', 'total_2026_permits', 'permit_qty', 'permits'],
  NOTES: ['NOTES', 'notes', 'other'],
};

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
  const lines = [headers.map(csvEscape).join(',')];
  for (const record of records) {
    lines.push(headers.map(header => csvEscape(record[header] || '')).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase();
}

function normalizeValue(value) {
  return String(value ?? '').trim();
}

function readCsv(file) {
  return parseCsv(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
}

function isTargetCsv(fileName) {
  const lower = fileName.toLowerCase();
  if (!lower.endsWith('.csv')) return false;
  if (EXCLUDED_FILES.has(fileName)) return false;
  if (lower.includes('backup')) return false;
  return true;
}

function headerLookup(headers) {
  const byLower = new Map(headers.map(header => [header.toLowerCase(), header]));
  return {
    findAny(names) {
      for (const name of names) {
        if (byLower.has(name.toLowerCase())) return byLower.get(name.toLowerCase());
      }
      return null;
    },
  };
}

function truthHeaderFor(targetHeader) {
  const lower = targetHeader.toLowerCase();
  for (const [truthHeader, aliases] of Object.entries(FIELD_ALIASES)) {
    if (aliases.some(alias => alias.toLowerCase() === lower)) return truthHeader;
  }
  return null;
}

function indexDatabase() {
  const parsed = readCsv(DATABASE_FILE);
  const index = new Map();
  const duplicates = [];
  for (const row of parsed.records) {
    const code = normalizeCode(row.hunt_code);
    if (!code) continue;
    if (index.has(code)) duplicates.push(code);
    index.set(code, row);
  }
  return { headers: parsed.headers, records: parsed.records, index, duplicates };
}

function chooseTargetHeaders(targetHeaders, dbHeaders) {
  const headers = [...targetHeaders];
  const lookup = headerLookup(headers);
  for (const dbHeader of dbHeaders) {
    const aliases = FIELD_ALIASES[dbHeader] || [dbHeader];
    if (!lookup.findAny(aliases)) headers.push(dbHeader);
  }
  return headers;
}

function updateRecord(record, targetHeaders, outputHeaders, dbRow) {
  const changes = [];
  const lookup = headerLookup(targetHeaders);
  for (const header of outputHeaders) {
    const truthHeader = truthHeaderFor(header) || (dbRow[header] !== undefined ? header : null);
    if (!truthHeader || dbRow[truthHeader] === undefined) continue;
    const truthValue = normalizeValue(dbRow[truthHeader]);
    if (!truthValue) continue;
    const targetHeader = lookup.findAny(FIELD_ALIASES[truthHeader] || [truthHeader]) || header;
    if (targetHeader !== header && outputHeaders.includes(targetHeader)) continue;
    const oldValue = normalizeValue(record[header]);
    if (oldValue !== truthValue) {
      record[header] = truthValue;
      changes.push({ field: header, truth_field: truthHeader, before: oldValue, after: truthValue });
    }
  }
  return changes;
}

function processCsv(file, db) {
  const parsed = readCsv(file);
  const lookup = headerLookup(parsed.headers);
  const codeHeader = lookup.findAny(FIELD_ALIASES.hunt_code);
  if (!codeHeader) {
    return {
      file: path.relative(REPO, file).replace(/\\/g, '/'),
      skipped: true,
      reason: 'missing hunt_code/hunt_number column',
      rows: parsed.records.length,
      matched_rows: 0,
      changed_cells: 0,
      added_headers: [],
      changes: [],
    };
  }

  const outputHeaders = chooseTargetHeaders(parsed.headers, db.headers);
  const addedHeaders = outputHeaders.filter(header => !parsed.headers.includes(header));
  const changes = [];
  let matchedRows = 0;

  for (let rowIndex = 0; rowIndex < parsed.records.length; rowIndex += 1) {
    const record = parsed.records[rowIndex];
    for (const header of outputHeaders) {
      if (record[header] === undefined) record[header] = '';
    }
    const code = normalizeCode(record[codeHeader]);
    if (!code || !db.index.has(code)) continue;
    matchedRows += 1;
    const rowChanges = updateRecord(record, parsed.headers, outputHeaders, db.index.get(code));
    if (rowChanges.length) {
      changes.push({
        row_number: rowIndex + 2,
        hunt_code: code,
        changes: rowChanges,
      });
    }
  }

  if (changes.length || addedHeaders.length) {
    fs.mkdirSync(BACKUP_DIR, { recursive: true });
    fs.copyFileSync(file, path.join(BACKUP_DIR, path.basename(file)));
    fs.writeFileSync(file, writeCsv(outputHeaders, parsed.records), 'utf8');
  }

  return {
    file: path.relative(REPO, file).replace(/\\/g, '/'),
    skipped: false,
    rows: parsed.records.length,
    matched_rows: matchedRows,
    changed_cells: changes.reduce((sum, row) => sum + row.changes.length, 0),
    changed_rows: changes.length,
    added_headers: addedHeaders,
    changes,
  };
}

function markdown(report) {
  const lines = [
    '# DATABASE Backfill Report',
    '',
    `Generated: ${report.generated_at}`,
    '',
    `Database rows: ${report.database_rows}`,
    `Database unique hunt codes: ${report.database_unique_codes}`,
    `Backup directory: ${report.backup_dir}`,
    '',
    '| File | Rows | Matched rows | Changed rows | Changed cells | Added headers | Skipped |',
    '| --- | ---: | ---: | ---: | ---: | --- | --- |',
  ];
  for (const item of report.files) {
    lines.push(`| ${item.file} | ${item.rows} | ${item.matched_rows} | ${item.changed_rows || 0} | ${item.changed_cells || 0} | ${(item.added_headers || []).join(', ')} | ${item.skipped ? item.reason : ''} |`);
  }
  lines.push('');
  lines.push('## Changed Values');
  lines.push('');
  for (const item of report.files.filter(file => file.changes && file.changes.length)) {
    lines.push(`### ${item.file}`);
    lines.push('');
    for (const row of item.changes.slice(0, 200)) {
      lines.push(`- Row ${row.row_number}, ${row.hunt_code}: ${row.changes.map(change => `${change.field}: "${change.before}" -> "${change.after}"`).join('; ')}`);
    }
    if (item.changes.length > 200) lines.push(`- ... ${item.changes.length - 200} additional changed rows omitted from markdown; see JSON report.`);
    lines.push('');
  }
  return `${lines.join('\n')}\n`;
}

const db = indexDatabase();
const files = fs.readdirSync(CSV_DIR)
  .filter(isTargetCsv)
  .sort()
  .map(fileName => path.join(CSV_DIR, fileName));

const results = files.map(file => processCsv(file, db));
const report = {
  generated_at: new Date().toISOString(),
  database_file: path.relative(REPO, DATABASE_FILE).replace(/\\/g, '/'),
  database_rows: db.records.length,
  database_unique_codes: db.index.size,
  database_duplicate_codes: db.duplicates,
  backup_dir: path.relative(REPO, BACKUP_DIR).replace(/\\/g, '/'),
  excluded_files: [...EXCLUDED_FILES],
  files: results,
  totals: {
    files_processed: results.filter(item => !item.skipped).length,
    files_skipped: results.filter(item => item.skipped).length,
    changed_cells: results.reduce((sum, item) => sum + (item.changed_cells || 0), 0),
    changed_rows: results.reduce((sum, item) => sum + (item.changed_rows || 0), 0),
  },
};

fs.mkdirSync(path.dirname(REPORT_JSON), { recursive: true });
fs.writeFileSync(REPORT_JSON, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
fs.writeFileSync(REPORT_MD, markdown(report), 'utf8');

console.log(JSON.stringify({
  ok: true,
  files_processed: report.totals.files_processed,
  files_skipped: report.totals.files_skipped,
  changed_rows: report.totals.changed_rows,
  changed_cells: report.totals.changed_cells,
  backup_dir: report.backup_dir,
  report_json: path.relative(REPO, REPORT_JSON).replace(/\\/g, '/'),
  report_md: path.relative(REPO, REPORT_MD).replace(/\\/g, '/'),
}, null, 2));
