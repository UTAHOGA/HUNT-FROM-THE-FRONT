const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const CSV_DIR = path.join('pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv');
const REPORT_DIR = path.join('pipeline', 'RAW', 'hunt_unit_database', '2026', 'reports');
const DATABASE_FILE = path.join(CSV_DIR, 'DATABASE.csv');
const BUILT_FILE = path.join(CSV_DIR, 'hunt_master_canonical_2026_built.csv');
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');

const PERMIT_FIELDS = ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total'];
const KEYWORDS = [
  'conservation',
  'expo',
  'sportsman',
  'auction',
  'statewide permit',
  'statewide',
];

function abs(relativePath) {
  return path.join(REPO, relativePath);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        value += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(value);
      value = '';
    } else if (ch === '\n') {
      row.push(value);
      rows.push(row);
      row = [];
      value = '';
    } else if (ch !== '\r') {
      value += ch;
    }
  }
  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
  return {
    headers,
    records: rows
      .filter((r) => r.some((cell) => String(cell || '').trim()))
      .map((r, index) => Object.fromEntries(headers.map((header, idx) => [header, r[idx] || '']).concat([['_row', index + 2]]))),
  };
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(relativePath, headers, records) {
  const lines = [headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))]
    .map((row) => row.map(csvEscape).join(','));
  fs.writeFileSync(abs(relativePath), `${lines.join('\r\n')}\r\n`, 'utf8');
}

function clean(value) {
  return String(value ?? '').trim();
}

function normalizeCode(value) {
  return clean(value).toUpperCase();
}

function hasPermitValue(row) {
  return PERMIT_FIELDS.some((field) => clean(row[field]));
}

function specialType(row) {
  const text = [
    row.hunt_name,
    row.hunt_code,
    row.hunt_type,
    row.hunt_class,
    row.weapon,
    row.NOTES,
    row.notes,
  ].map(clean).join(' ').toLowerCase();
  if (text.includes('expo')) return 'EXPO';
  if (text.includes('sportsman')) return 'SPORTSMAN';
  if (text.includes('auction')) return 'AUCTION';
  if (text.includes('conservation')) return 'CONSERVATION';
  if (text.includes('statewide permit') || text.includes('statewide')) return 'STATEWIDE';
  return '';
}

function byCode(records) {
  const map = new Map();
  for (const row of records) {
    const code = normalizeCode(row.hunt_code);
    if (code && !map.has(code)) map.set(code, row);
  }
  return map;
}

function readCsv(relativePath) {
  return parseCsv(fs.readFileSync(abs(relativePath), 'utf8').replace(/^\uFEFF/, ''));
}

function main() {
  fs.mkdirSync(abs(REPORT_DIR), { recursive: true });
  const database = readCsv(DATABASE_FILE);
  const built = readCsv(BUILT_FILE);
  const builtByCode = byCode(built.records);

  const candidates = [];
  const dbSpecialRows = database.records
    .filter((row) => normalizeCode(row.hunt_code))
    .filter((row) => {
      const text = [row.hunt_name, row.hunt_type, row.weapon, row.NOTES].map(clean).join(' ').toLowerCase();
      return KEYWORDS.some((keyword) => text.includes(keyword));
    });

  for (const row of dbSpecialRows) {
    const code = normalizeCode(row.hunt_code);
    const builtRow = builtByCode.get(code);
    const dbHasPermits = hasPermitValue(row);
    const builtHasPermits = builtRow ? hasPermitValue(builtRow) : false;
    const type = specialType(row) || specialType(builtRow || {});
    candidates.push({
      hunt_code: code,
      special_permit_type: type,
      hunt_name: row.hunt_name || builtRow?.hunt_name || '',
      species: row.species || builtRow?.species || '',
      sex_type: row.sex_type || builtRow?.sex_type || '',
      weapon: row.weapon || builtRow?.weapon || '',
      hunt_type: row.hunt_type || builtRow?.hunt_type || '',
      database_res: row.permits_2026_res || '',
      database_nr: row.permits_2026_nr || '',
      database_total: row.permits_2026_total || '',
      built_res: builtRow?.permits_2026_res || '',
      built_nr: builtRow?.permits_2026_nr || '',
      built_total: builtRow?.permits_2026_total || '',
      built_permit_status: builtRow?.permit_status || '',
      database_has_permits: dbHasPermits ? 'yes' : 'no',
      built_has_permits: builtHasPermits ? 'yes' : 'no',
      candidate_action: !dbHasPermits && builtHasPermits ? 'REVIEW_BACKFILL_FROM_BUILT' : dbHasPermits ? 'ALREADY_IN_DATABASE' : 'SOURCE_NEEDED',
      notes: row.NOTES || row.notes || '',
    });
  }

  const summary = candidates.reduce((acc, row) => {
    acc.total += 1;
    acc.by_action[row.candidate_action] = (acc.by_action[row.candidate_action] || 0) + 1;
    acc.by_type[row.special_permit_type || 'UNKNOWN'] = (acc.by_type[row.special_permit_type || 'UNKNOWN'] || 0) + 1;
    return acc;
  }, { total: 0, by_action: {}, by_type: {} });

  const report = {
    generated_at: new Date().toISOString(),
    database_file: DATABASE_FILE.replace(/\\/g, '/'),
    comparison_file: BUILT_FILE.replace(/\\/g, '/'),
    principle: 'Special-program permits are audited separately from normal published draw allocation fields before any backfill.',
    summary,
    candidates,
  };

  const jsonPath = path.join(REPORT_DIR, `special_permit_overlay_audit_${STAMP}.json`).replace(/\\/g, '/');
  const csvPath = path.join(REPORT_DIR, `special_permit_overlay_audit_${STAMP}.csv`).replace(/\\/g, '/');
  fs.writeFileSync(abs(jsonPath), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  writeCsv(csvPath, [
    'hunt_code',
    'special_permit_type',
    'hunt_name',
    'species',
    'sex_type',
    'weapon',
    'hunt_type',
    'database_res',
    'database_nr',
    'database_total',
    'built_res',
    'built_nr',
    'built_total',
    'built_permit_status',
    'database_has_permits',
    'built_has_permits',
    'candidate_action',
    'notes',
  ], candidates);

  console.log(JSON.stringify({
    ok: true,
    total_candidates: summary.total,
    by_action: summary.by_action,
    by_type: summary.by_type,
    report_json: jsonPath,
    report_csv: csvPath,
  }, null, 2));
}

main();
