const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const ACTIVE_TABLE = 'D:/DOCUMENTS/GitHub/HUNTS/pages-dist/data/conservation-permit-hunt-table-2025-27.csv';
const EXTRACTED_GROUPED = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_permits_2025_2027_grouped.csv';
const REPORT_DIR = 'pipeline/RAW/hunt_unit_database/2026/reports';
const OUT_JSON = `${REPORT_DIR}/conservation_table_source_compare_2026.json`;
const OUT_CSV = `${REPORT_DIR}/conservation_table_source_compare_2026.csv`;

function abs(file) {
  return path.isAbsolute(file) || /^[A-Za-z]:\//.test(file) ? file : path.join(REPO, file);
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
  const headers = (rows.shift() || []).map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
  return {
    headers,
    records: rows
      .filter((r) => r.some((cell) => String(cell || '').trim()))
      .map((r) => Object.fromEntries(headers.map((header, idx) => [header, r[idx] || '']))),
  };
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(file, headers, rows) {
  const output = [headers, ...rows.map((row) => headers.map((header) => row[header] || ''))]
    .map((row) => row.map(csvEscape).join(','))
    .join('\r\n') + '\r\n';
  fs.writeFileSync(abs(file), output, 'utf8');
}

function clean(value) {
  return String(value ?? '').trim();
}

function norm(value) {
  return clean(value)
    .toLowerCase()
    .replace(/black bear/g, 'bear')
    .replace(/&/g, ' and ')
    .replace(/\bmtns\b/g, 'mountains')
    .replace(/\bmtn\b/g, 'mountain')
    .replace(/\bhunter s choice\b/g, 'hunters choice')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function keyFromExtracted(row) {
  return `${norm(row.species)}|${norm(row.area)}|${norm(row.condition)}`;
}

function keyFromActive(row) {
  return `${norm(row.sourceSpecies || row.species)}|${norm(row.area)}|${norm(row.conditions || row.weapon)}`;
}

function main() {
  fs.mkdirSync(abs(REPORT_DIR), { recursive: true });
  const active = parseCsv(fs.readFileSync(abs(ACTIVE_TABLE), 'utf8').replace(/^\uFEFF/, ''));
  const extracted = parseCsv(fs.readFileSync(abs(EXTRACTED_GROUPED), 'utf8').replace(/^\uFEFF/, ''));
  const extractedByKey = new Map(extracted.records.map((row) => [keyFromExtracted(row), row]));
  const activeByKey = new Map();
  const activeSystemObjectRows = [];

  for (const row of active.records) {
    if (Object.values(row).some((value) => clean(value) === 'System.Object[]')) activeSystemObjectRows.push(row.huntCode);
    const key = keyFromActive(row);
    const current = activeByKey.get(key) || {
      key,
      active_permit_count: 0,
      active_rows: 0,
      active_hunt_codes: [],
      species: row.sourceSpecies || row.species,
      area: row.area,
      condition: row.conditions || row.weapon,
    };
    current.active_permit_count += Number(row.permitCount || 0);
    current.active_rows += 1;
    current.active_hunt_codes.push(row.huntCode);
    activeByKey.set(key, current);
  }

  const comparisons = [];
  for (const [key, activeRow] of activeByKey.entries()) {
    const extractedRow = extractedByKey.get(key);
    comparisons.push({
      key,
      species: activeRow.species,
      area: activeRow.area,
      condition: activeRow.condition,
      active_permit_count: String(activeRow.active_permit_count),
      extracted_permit_count: extractedRow?.permits_2026_conservation || extractedRow?.conservation_permit_count_2025_2027 || '',
      active_rows: String(activeRow.active_rows),
      active_hunt_codes: activeRow.active_hunt_codes.join(';'),
      compare_status: !extractedRow
        ? 'active_only'
        : Number(extractedRow.permits_2026_conservation || extractedRow.conservation_permit_count_2025_2027 || 0) === activeRow.active_permit_count
          ? 'match'
          : 'count_mismatch',
    });
  }
  for (const [key, extractedRow] of extractedByKey.entries()) {
    if (activeByKey.has(key)) continue;
    comparisons.push({
      key,
      species: extractedRow.species,
      area: extractedRow.area,
      condition: extractedRow.condition,
      active_permit_count: '',
      extracted_permit_count: extractedRow.permits_2026_conservation || extractedRow.conservation_permit_count_2025_2027 || '',
      active_rows: '',
      active_hunt_codes: '',
      compare_status: 'extracted_only',
    });
  }

  const summary = comparisons.reduce((acc, row) => {
    acc[row.compare_status] = (acc[row.compare_status] || 0) + 1;
    return acc;
  }, {});
  const report = {
    generated_at: new Date().toISOString(),
    active_table: ACTIVE_TABLE,
    extracted_grouped: EXTRACTED_GROUPED,
    active_rows: active.records.length,
    extracted_rows: extracted.records.length,
    unique_active_keys: activeByKey.size,
    unique_extracted_keys: extractedByKey.size,
    system_object_artifact_rows: activeSystemObjectRows.length,
    summary,
    note: 'The active pages-dist table contains useful permit counts but also has System.Object[] export artifacts in list fields.',
  };
  fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  writeCsv(OUT_CSV, ['key', 'species', 'area', 'condition', 'active_permit_count', 'extracted_permit_count', 'active_rows', 'active_hunt_codes', 'compare_status'], comparisons);
  console.log(JSON.stringify({ ok: true, ...report, report_json: OUT_JSON, report_csv: OUT_CSV }, null, 2));
}

main();
