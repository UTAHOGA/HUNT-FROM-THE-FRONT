const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const DATABASE_FILE = 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv';
const CROSSWALK_FILE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_area_crosswalk_2026.csv';
const PUBLISHED_CROSSWALK = 'processed_data/conservation_area_crosswalk_2026.csv';
const PUBLISHED_JSON = 'processed_data/conservation_area_crosswalk_2026.json';
const REPORT_FILE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_crosswalk_promotion_report.json';

const SPECIAL_FIELDS = [
  'permits_2026_conservation',
  'permits_2026_expo',
  'permits_2026_sportsman',
  'special_permit_area_id',
  'special_permit_category',
  'special_permit_note',
  'special_permit_overlay_source',
];

function abs(file) {
  return path.join(REPO, file);
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
      } else if (ch === '"') quoted = false;
      else value += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') {
      row.push(value);
      value = '';
    } else if (ch === '\n') {
      row.push(value);
      rows.push(row);
      row = [];
      value = '';
    } else if (ch !== '\r') value += ch;
  }
  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
  const records = rows
    .filter((r) => r.some((cell) => String(cell || '').trim()))
    .map((r) => Object.fromEntries(headers.map((header, idx) => [header, r[idx] || ''])));
  return { headers, records };
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(headers, records) {
  return `${[headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))]
    .map((row) => row.map(csvEscape).join(','))
    .join('\r\n')}\r\n`;
}

function clean(value) {
  return String(value ?? '').trim();
}

function normalizeCode(value) {
  return clean(value).toUpperCase();
}

function main() {
  const database = parseCsv(fs.readFileSync(abs(DATABASE_FILE), 'utf8').replace(/^\uFEFF/, ''));
  const crosswalk = parseCsv(fs.readFileSync(abs(CROSSWALK_FILE), 'utf8').replace(/^\uFEFF/, ''));
  const headers = [...database.headers];
  for (const field of SPECIAL_FIELDS) {
    if (!headers.includes(field)) headers.push(field);
  }
  const byCode = new Map(database.records.map((row) => [normalizeCode(row.hunt_code), row]));
  const updates = [];
  const missingPrimaryCodes = [];

  for (const row of crosswalk.records) {
    if (row.review_status !== 'READY_FOR_OWNER_REVIEW') continue;
    const code = normalizeCode(row.primary_hunt_code);
    const target = byCode.get(code);
    if (!target) {
      missingPrimaryCodes.push(code);
      continue;
    }
    const values = {
      permits_2026_conservation: clean(row.permits_2026_conservation),
      special_permit_area_id: clean(row.conservation_area_id),
      special_permit_category: 'CONSERVATION',
      special_permit_note: `Conservation permit area ${row.conservation_area} covers ${row.included_hunt_code_count} applicable hunt codes; see conservation_area_crosswalk_2026.csv.`,
      special_permit_overlay_source: CROSSWALK_FILE,
    };
    for (const [field, value] of Object.entries(values)) {
      const before = clean(target[field]);
      if (before !== value) {
        target[field] = value;
        updates.push({ hunt_code: code, field, before, after: value });
      }
    }
  }

  fs.writeFileSync(abs(DATABASE_FILE), writeCsv(headers, database.records), 'utf8');
  fs.mkdirSync(path.dirname(abs(PUBLISHED_CROSSWALK)), { recursive: true });
  fs.copyFileSync(abs(CROSSWALK_FILE), abs(PUBLISHED_CROSSWALK));
  fs.writeFileSync(abs(PUBLISHED_JSON), `${JSON.stringify({
    generated_at: new Date().toISOString(),
    source_crosswalk: CROSSWALK_FILE,
    records: crosswalk.records,
  }, null, 2)}\n`, 'utf8');
  const report = {
    generated_at: new Date().toISOString(),
    database_file: DATABASE_FILE,
    source_crosswalk: CROSSWALK_FILE,
    published_crosswalk: PUBLISHED_CROSSWALK,
    published_json: PUBLISHED_JSON,
    updated_cells: updates.length,
    updated_hunt_codes: [...new Set(updates.map((item) => item.hunt_code))].sort(),
    missing_primary_codes: missingPrimaryCodes,
    updates,
  };
  fs.writeFileSync(abs(REPORT_FILE), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    ok: missingPrimaryCodes.length === 0,
    updated_cells: updates.length,
    updated_hunt_codes: report.updated_hunt_codes,
    published_crosswalk: PUBLISHED_CROSSWALK,
    report: REPORT_FILE,
  }, null, 2));
  if (missingPrimaryCodes.length) process.exitCode = 1;
}

main();
