#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DATABASE_CSV = path.join(ROOT, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv', 'DATABASE.csv');
const DWR_POPUP_CSV = path.join(ROOT, 'processed_data', 'dwr_huntplanner_hanumber_2026.csv');
const AUDIT_JSON = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_overlay_audit.json');
const AUDIT_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_overlay_audit.csv');

const DWR_COLUMNS = [
  'dwr_huntplanner_source_url',
  'dwr_huntplanner_source_retrieved_at',
  'dwr_huntplanner_management_stats_available',
  'dwr_huntplanner_season_date_text',
  'dwr_huntplanner_permits_2026_res',
  'dwr_huntplanner_permits_2026_nr',
  'dwr_huntplanner_permits_2026_total',
  'dwr_huntplanner_percent_harvest_success_previous_hunting_season',
  'dwr_huntplanner_current_age_3yr_average',
  'dwr_huntplanner_age_objective',
  'dwr_huntplanner_population_objective',
  'dwr_huntplanner_current_population_estimate'
];

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
    } else if (ch === '"') {
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

  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }

  if (!rows.length) return { headers: [], records: [] };
  const headers = rows[0].map(h => h.replace(/^\uFEFF/, ''));
  const records = rows.slice(1).filter(r => r.some(v => v !== '')).map(values => {
    const out = {};
    headers.forEach((header, index) => {
      out[header] = values[index] ?? '';
    });
    return out;
  });
  return { headers, records };
}

function csvEscape(value) {
  const s = value == null ? '' : String(value);
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function writeCsv(filePath, rows, headers) {
  const lines = [headers.join(',')];
  for (const row of rows) {
    lines.push(headers.map(header => csvEscape(row[header])).join(','));
  }
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

function normalizeCode(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function num(value) {
  const s = String(value ?? '').trim();
  if (!s) return null;
  const n = Number(s.replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
}

function sameNumeric(a, b) {
  const na = num(a);
  const nb = num(b);
  if (na == null && nb == null) return true;
  if (na == null || nb == null) return false;
  return na === nb;
}

function differenceType(databaseValue, dwrValue) {
  const db = String(databaseValue ?? '').trim();
  const dwr = String(dwrValue ?? '').trim();
  const dbn = num(db);
  const dwrn = num(dwr);
  if (!db && dwrn === 0) return 'DATABASE_BLANK_DWR_ZERO';
  if (!db && dwr) return 'DATABASE_BLANK_DWR_VALUE';
  if (db && !dwr) return 'DATABASE_VALUE_DWR_BLANK';
  if (dbn != null && dwrn != null && dbn !== dwrn) return 'NUMERIC_CONFLICT';
  return 'OTHER_DIFFERENCE';
}

function main() {
  if (!fs.existsSync(DATABASE_CSV)) throw new Error(`DATABASE.csv not found: ${DATABASE_CSV}`);
  if (!fs.existsSync(DWR_POPUP_CSV)) throw new Error(`DWR Hunt Planner extract not found: ${DWR_POPUP_CSV}`);

  const database = parseCsv(fs.readFileSync(DATABASE_CSV, 'utf8'));
  const popup = parseCsv(fs.readFileSync(DWR_POPUP_CSV, 'utf8'));
  const popupByCode = new Map();
  for (const row of popup.records) {
    const code = normalizeCode(row.hunt_code);
    if (code) popupByCode.set(code, row);
  }

  const headers = [...database.headers];
  for (const column of DWR_COLUMNS) {
    if (!headers.includes(column)) headers.push(column);
  }

  const permitMismatches = [];
  let matchedRows = 0;
  let missingPopupRows = 0;
  let percentHarvestRows = 0;
  let currentAgeRows = 0;
  let ageObjectiveRows = 0;
  let populationObjectiveRows = 0;

  for (const row of database.records) {
    const code = normalizeCode(row.hunt_code);
    const dwr = popupByCode.get(code);
    if (!dwr) {
      missingPopupRows += 1;
      continue;
    }

    matchedRows += 1;
    row.dwr_huntplanner_source_url = dwr.source_url || '';
    row.dwr_huntplanner_source_retrieved_at = dwr.source_retrieved_at || '';
    row.dwr_huntplanner_management_stats_available = dwr.management_stats_available || '';
    row.dwr_huntplanner_season_date_text = dwr.season_date_text || '';
    row.dwr_huntplanner_permits_2026_res = dwr.permits_2026_res || '';
    row.dwr_huntplanner_permits_2026_nr = dwr.permits_2026_nr || '';
    row.dwr_huntplanner_permits_2026_total = dwr.permits_2026_total || '';
    row.dwr_huntplanner_percent_harvest_success_previous_hunting_season = dwr.percent_harvest_success_previous_hunting_season || '';
    row.dwr_huntplanner_current_age_3yr_average = dwr.current_age_3yr_average || '';
    row.dwr_huntplanner_age_objective = dwr.age_objective || '';
    row.dwr_huntplanner_population_objective = dwr.population_objective || '';
    row.dwr_huntplanner_current_population_estimate = dwr.current_population_estimate || '';

    if (row.dwr_huntplanner_percent_harvest_success_previous_hunting_season) percentHarvestRows += 1;
    if (row.dwr_huntplanner_current_age_3yr_average) currentAgeRows += 1;
    if (row.dwr_huntplanner_age_objective) ageObjectiveRows += 1;
    if (row.dwr_huntplanner_population_objective) populationObjectiveRows += 1;

    for (const [databaseField, dwrField] of [
      ['permits_2026_res', 'permits_2026_res'],
      ['permits_2026_nr', 'permits_2026_nr'],
      ['permits_2026_total', 'permits_2026_total']
    ]) {
      if (!sameNumeric(row[databaseField], dwr[dwrField])) {
        permitMismatches.push({
          hunt_code: row.hunt_code,
          hunt_name: row.hunt_name,
          species: row.species,
          field: databaseField,
          difference_type: differenceType(row[databaseField], dwr[dwrField]),
          database_value: row[databaseField] || '',
          dwr_huntplanner_value: dwr[dwrField] || '',
          source_url: dwr.source_url || ''
        });
      }
    }
  }

  fs.mkdirSync(path.dirname(AUDIT_JSON), { recursive: true });
  writeCsv(DATABASE_CSV, database.records, headers);
  writeCsv(AUDIT_CSV, permitMismatches, [
    'hunt_code',
    'hunt_name',
    'species',
    'field',
    'difference_type',
    'database_value',
    'dwr_huntplanner_value',
    'source_url'
  ]);

  const differenceTypeCounts = permitMismatches.reduce((acc, row) => {
    acc[row.difference_type] = (acc[row.difference_type] || 0) + 1;
    return acc;
  }, {});

  const audit = {
    created_at: new Date().toISOString(),
    database_csv: path.relative(ROOT, DATABASE_CSV).replace(/\\/g, '/'),
    dwr_popup_csv: path.relative(ROOT, DWR_POPUP_CSV).replace(/\\/g, '/'),
    database_rows: database.records.length,
    dwr_popup_rows: popup.records.length,
    matched_hunt_code_rows: matchedRows,
    missing_dwr_popup_rows: missingPopupRows,
    columns_added_or_confirmed: DWR_COLUMNS,
    rows_with_percent_harvest_success_previous_hunting_season: percentHarvestRows,
    rows_with_current_age_3yr_average: currentAgeRows,
    rows_with_age_objective: ageObjectiveRows,
    rows_with_population_objective: populationObjectiveRows,
    permit_mismatch_cells: permitMismatches.length,
    permit_mismatch_hunt_codes: [...new Set(permitMismatches.map(r => r.hunt_code))].length,
    permit_difference_type_counts: differenceTypeCounts,
    audit_csv: path.relative(ROOT, AUDIT_CSV).replace(/\\/g, '/'),
    notes: [
      'DWR Hunt Planner fields were appended as source evidence columns; canonical permit columns were not overwritten.',
      'dwr_huntplanner_current_age_3yr_average is current age context from the Hunt Planner popup, not prior-year average harvest age.',
      'dwr_huntplanner_percent_harvest_success_previous_hunting_season is the previous hunting season value reported by the DWR Hunt Planner popup for the hunt code.'
    ]
  };
  fs.writeFileSync(AUDIT_JSON, `${JSON.stringify(audit, null, 2)}\n`, 'utf8');

  console.log('DWR Hunt Planner fields merged into DATABASE.csv.');
  console.log(`DATABASE rows: ${database.records.length}`);
  console.log(`Matched hunt codes: ${matchedRows}`);
  console.log(`Missing DWR popup rows: ${missingPopupRows}`);
  console.log(`Previous-season harvest success rows: ${percentHarvestRows}`);
  console.log(`Current age 3-year average rows: ${currentAgeRows}`);
  console.log(`Permit mismatch cells: ${permitMismatches.length}`);
  console.log(`Audit: ${AUDIT_JSON}`);
}

main();
