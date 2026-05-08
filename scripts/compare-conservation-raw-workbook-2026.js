const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RAW_WORKBOOK = 'D:/DOCUMENTS/GitHub/HUNTS/data/conservation-permit-workbook-2025-27-raw.csv';
const EXTRACTED_DETAIL = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_permits_2025_2027_extracted_detail.csv';
const EXTRACTED_GROUPED = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_permits_2025_2027_grouped.csv';
const OUT_DETAIL_COMPARE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_raw_workbook_detail_compare_2026.csv';
const OUT_GROUPED = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_raw_workbook_grouped_2026.csv';
const OUT_HUNTERS_CHOICE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_hunters_choice_2026.csv';
const OUT_JSON = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_raw_workbook_compare_2026.json';

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
    .replace(/&/g, ' and ')
    .replace(/\bmtns\b/g, 'mountains')
    .replace(/\bmtn\b/g, 'mountain')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function money(value) {
  const n = Number(clean(value).replace(/[$,]/g, ''));
  return Number.isFinite(n) ? n.toFixed(2) : '';
}

function rowKey(row) {
  return [
    norm(row.species),
    norm(row.area),
    norm(row.condition),
    money(row.average_value || row.value),
    norm(row.organization),
  ].join('|');
}

function groupKey(row) {
  return [norm(row.species), norm(row.area), norm(row.condition)].join('|');
}

function conditionNote(condition) {
  const text = clean(condition).toLowerCase();
  if (text === "hunter's choice") return "Winning bidder chooses one eligible season for that unit/species; this is not a multiseason permit.";
  if (text === "hunter's choice (early)") return "Hunter's Choice label from source; interpreted as season-choice for the listed early season context, not multiseason.";
  if (text === "hunter's choice (late)") return "Hunter's Choice label from source; interpreted as season-choice for the listed late season context, not multiseason.";
  return '';
}

function main() {
  const raw = parseCsv(fs.readFileSync(abs(RAW_WORKBOOK), 'utf8').replace(/^\uFEFF/, ''));
  const detail = parseCsv(fs.readFileSync(abs(EXTRACTED_DETAIL), 'utf8').replace(/^\uFEFF/, ''));
  const extractedGrouped = parseCsv(fs.readFileSync(abs(EXTRACTED_GROUPED), 'utf8').replace(/^\uFEFF/, ''));
  const detailKeys = new Map();
  detail.records.forEach((row) => detailKeys.set(rowKey(row), (detailKeys.get(rowKey(row)) || 0) + 1));
  const rawKeys = new Map();
  raw.records.forEach((row) => rawKeys.set(rowKey(row), (rawKeys.get(rowKey(row)) || 0) + 1));

  const detailCompare = [];
  for (const [key, count] of rawKeys.entries()) {
    const extractedCount = detailKeys.get(key) || 0;
    if (count !== extractedCount) detailCompare.push({ key, raw_count: String(count), extracted_count: String(extractedCount), status: 'count_mismatch_or_missing' });
  }
  for (const [key, count] of detailKeys.entries()) {
    if (rawKeys.has(key)) continue;
    detailCompare.push({ key, raw_count: '0', extracted_count: String(count), status: 'extracted_only' });
  }

  const groupedMap = new Map();
  for (const row of raw.records) {
    const key = groupKey(row);
    const current = groupedMap.get(key) || {
      species: row.species,
      area: row.area,
      condition: row.condition,
      condition_note: conditionNote(row.condition),
      permits_2026_conservation: 0,
      conservation_permit_count_2025_2027: 0,
      organizations: new Set(),
      average_value: money(row.average_value),
      source_rows: [],
    };
    current.permits_2026_conservation += 1;
    current.conservation_permit_count_2025_2027 += 1;
    current.organizations.add(row.organization);
    current.source_rows.push(row.source_row || row.row_number);
    groupedMap.set(key, current);
  }
  const grouped = [...groupedMap.values()].map((row) => ({
    species: row.species,
    area: row.area,
    condition: row.condition,
    condition_note: row.condition_note,
    conservation_permit_count_2025_2027: String(row.conservation_permit_count_2025_2027),
    permits_2026_conservation: String(row.permits_2026_conservation),
    organizations: [...row.organizations].sort().join(';'),
    average_value: row.average_value,
    source_rows: row.source_rows.join(';'),
    source_csv: RAW_WORKBOOK,
  })).sort((a, b) => `${a.species}|${a.area}|${a.condition}`.localeCompare(`${b.species}|${b.area}|${b.condition}`));

  const extractedGroupKeys = new Map(extractedGrouped.records.map((row) => [groupKey(row), row]));
  const groupedMatches = grouped.filter((row) => {
    const extracted = extractedGroupKeys.get(groupKey(row));
    return extracted && clean(extracted.permits_2026_conservation || extracted.conservation_permit_count_2025_2027) === row.permits_2026_conservation;
  }).length;

  writeCsv(OUT_DETAIL_COMPARE, ['key', 'raw_count', 'extracted_count', 'status'], detailCompare);
  writeCsv(OUT_GROUPED, ['species', 'area', 'condition', 'condition_note', 'conservation_permit_count_2025_2027', 'permits_2026_conservation', 'organizations', 'average_value', 'source_rows', 'source_csv'], grouped);
  const huntersChoice = grouped.filter((row) => clean(row.condition).toLowerCase() === "hunter's choice");
  writeCsv(OUT_HUNTERS_CHOICE, ['species', 'area', 'condition', 'condition_note', 'permits_2026_conservation', 'organizations', 'average_value', 'source_rows', 'source_csv'], huntersChoice);
  const report = {
    generated_at: new Date().toISOString(),
    raw_workbook: RAW_WORKBOOK,
    extracted_detail: EXTRACTED_DETAIL,
    extracted_grouped: EXTRACTED_GROUPED,
    raw_rows: raw.records.length,
    extracted_detail_rows: detail.records.length,
    raw_grouped_rows: grouped.length,
    extracted_grouped_rows: extractedGrouped.records.length,
    detail_mismatches: detailCompare.length,
    grouped_count_matches: groupedMatches,
    grouped_count_nonmatches: grouped.length - groupedMatches,
    system_object_artifacts: raw.records.filter((row) => Object.values(row).some((value) => clean(value) === 'System.Object[]')).length,
    grouped_output: OUT_GROUPED,
    hunters_choice_output: OUT_HUNTERS_CHOICE,
    hunters_choice_rows: huntersChoice.length,
    detail_compare_output: OUT_DETAIL_COMPARE,
  };
  fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: detailCompare.length === 0, ...report, report_json: OUT_JSON }, null, 2));
}

main();
