#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DATABASE_CSV = path.join(ROOT, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv', 'DATABASE.csv');
const DWR_POPUP_CSV = path.join(ROOT, 'processed_data', 'dwr_huntplanner_hanumber_2026.csv');
const AUDIT_JSON = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_overlay_audit.json');
const AUDIT_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_overlay_audit.csv');
const NONMATCH_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_permit_nonmatches.csv');

const REMOVED_DWR_OVERLAY_COLUMNS = [
  'dwr_huntplanner_source_url',
  'dwr_huntplanner_source_retrieved_at',
  'dwr_huntplanner_management_stats_available',
  'dwr_huntplanner_season_date_text',
  'dwr_huntplanner_permits_2026_res',
  'dwr_huntplanner_permits_2026_nr',
  'dwr_huntplanner_permits_2026_total',
  'dwr_huntplanner_percent_harvest_success_previous_hunting_season',
  'dwr_huntplanner_current_age_3yr_average',
];

const DATA_COLUMNS = [
  'percent_harvest_success_previous_hunting_season',
  'current_age_3yr_average',
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

  const headers = database.headers.filter(column => !REMOVED_DWR_OVERLAY_COLUMNS.includes(column));
  for (const column of DATA_COLUMNS) {
    if (!headers.includes(column)) headers.push(column);
  }

  const permitComparisons = [];
  let matchedRows = 0;
  let missingPopupRows = 0;
  let percentHarvestRows = 0;
  let currentAgeRows = 0;
  let permitExactMatches = 0;
  let permitBlankDwrZero = 0;
  let permitBlankDwrValue = 0;
  let permitNumericConflicts = 0;
  let permitOtherDifferences = 0;

  for (const row of database.records) {
    for (const column of REMOVED_DWR_OVERLAY_COLUMNS) {
      delete row[column];
    }

    const code = normalizeCode(row.hunt_code);
    const dwr = popupByCode.get(code);
    if (!dwr) {
      missingPopupRows += 1;
      continue;
    }

    matchedRows += 1;
    row.percent_harvest_success_previous_hunting_season = dwr.percent_harvest_success_previous_hunting_season || '';
    row.current_age_3yr_average = dwr.current_age_3yr_average || '';
    row.dwr_huntplanner_age_objective = dwr.age_objective || '';
    row.dwr_huntplanner_population_objective = dwr.population_objective || '';
    row.dwr_huntplanner_current_population_estimate = dwr.current_population_estimate || '';

    if (row.percent_harvest_success_previous_hunting_season) percentHarvestRows += 1;
    if (row.current_age_3yr_average) currentAgeRows += 1;

    for (const [databaseField, dwrField] of [
      ['permits_2026_res', 'permits_2026_res'],
      ['permits_2026_nr', 'permits_2026_nr'],
      ['permits_2026_total', 'permits_2026_total']
    ]) {
      const comparisonStatus = sameNumeric(row[databaseField], dwr[dwrField])
        ? 'MATCH'
        : differenceType(row[databaseField], dwr[dwrField]);

      if (comparisonStatus === 'MATCH') permitExactMatches += 1;
      else if (comparisonStatus === 'DATABASE_BLANK_DWR_ZERO') permitBlankDwrZero += 1;
      else if (comparisonStatus === 'DATABASE_BLANK_DWR_VALUE') permitBlankDwrValue += 1;
      else if (comparisonStatus === 'NUMERIC_CONFLICT') permitNumericConflicts += 1;
      else permitOtherDifferences += 1;

      permitComparisons.push({
        hunt_code: row.hunt_code,
        hunt_name: row.hunt_name,
        species: row.species,
        field: databaseField,
        comparison_status: comparisonStatus,
        database_value: row[databaseField] || '',
        dwr_huntplanner_value: dwr[dwrField] || '',
        source_url: dwr.source_url || ''
      });
    }
  }

  fs.mkdirSync(path.dirname(AUDIT_JSON), { recursive: true });
  writeCsv(DATABASE_CSV, database.records, headers);
  writeCsv(AUDIT_CSV, permitComparisons, [
    'hunt_code',
    'hunt_name',
    'species',
    'field',
    'comparison_status',
    'database_value',
    'dwr_huntplanner_value',
    'source_url'
  ]);
  writeCsv(NONMATCH_CSV, permitComparisons.filter(row => row.comparison_status !== 'MATCH'), [
    'hunt_code',
    'hunt_name',
    'species',
    'field',
    'comparison_status',
    'database_value',
    'dwr_huntplanner_value',
    'source_url'
  ]);

  const comparisonStatusCounts = permitComparisons.reduce((acc, row) => {
    acc[row.comparison_status] = (acc[row.comparison_status] || 0) + 1;
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
    columns_removed: REMOVED_DWR_OVERLAY_COLUMNS,
    columns_added_or_confirmed: DATA_COLUMNS,
    rows_with_percent_harvest_success_previous_hunting_season: percentHarvestRows,
    rows_with_current_age_3yr_average: currentAgeRows,
    permit_comparison_cells: permitComparisons.length,
    permit_exact_match_cells: permitExactMatches,
    permit_nonmatch_cells: permitComparisons.length - permitExactMatches,
    permit_nonmatch_hunt_codes: [...new Set(permitComparisons.filter(r => r.comparison_status !== 'MATCH').map(r => r.hunt_code))].length,
    permit_comparison_status_counts: comparisonStatusCounts,
    permit_blank_dwr_zero_cells: permitBlankDwrZero,
    permit_blank_dwr_value_cells: permitBlankDwrValue,
    permit_numeric_conflict_cells: permitNumericConflicts,
    permit_other_difference_cells: permitOtherDifferences,
    audit_csv: path.relative(ROOT, AUDIT_CSV).replace(/\\/g, '/'),
    permit_nonmatch_csv: path.relative(ROOT, NONMATCH_CSV).replace(/\\/g, '/'),
    notes: [
      'DATABASE.csv uses the existing permits_2026_res, permits_2026_nr, and permits_2026_total columns; duplicate DWR-prefixed permit columns are not kept.',
      'percent_harvest_success_previous_hunting_season is populated from the DWR Hunt Planner popup by hunt code.',
      'current_age_3yr_average is DWR Hunt Planner current age context, not prior-year average harvest age.',
      'dwr_huntplanner_age_objective, dwr_huntplanner_population_objective, and dwr_huntplanner_current_population_estimate are retained as DWR Hunt Planner management-context fields.',
      'Permit values are compared in the audit; nonmatching values are reported and existing DATABASE permit columns are not overwritten by this script.'
    ]
  };
  fs.writeFileSync(AUDIT_JSON, `${JSON.stringify(audit, null, 2)}\n`, 'utf8');

  console.log('DWR Hunt Planner harvest/age fields merged into DATABASE.csv.');
  console.log(`DATABASE rows: ${database.records.length}`);
  console.log(`Matched hunt codes: ${matchedRows}`);
  console.log(`Missing DWR popup rows: ${missingPopupRows}`);
  console.log(`Previous-season harvest success rows: ${percentHarvestRows}`);
  console.log(`Current age 3-year average rows: ${currentAgeRows}`);
  console.log(`Permit exact-match cells: ${permitExactMatches}`);
  console.log(`Permit non-match cells: ${permitComparisons.length - permitExactMatches}`);
  console.log(`Audit: ${AUDIT_JSON}`);
  console.log(`Permit nonmatches: ${NONMATCH_CSV}`);
}

main();
