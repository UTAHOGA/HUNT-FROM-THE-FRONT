#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DATABASE_CSV = path.join(ROOT, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv', 'DATABASE.csv');
const DWR_POPUP_CSV = path.join(ROOT, 'processed_data', 'dwr_huntplanner_hanumber_2026.csv');
const AUDIT_JSON = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_overlay_audit.json');
const AUDIT_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_overlay_audit.csv');
const NONMATCH_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_permit_nonmatches.csv');
const ALLOTMENT_AUDIT_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_allotment_fill_audit.csv');
const BACKFILL_VS_2025_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_dwr_huntplanner_2026_backfilled_permits_vs_2025.csv');

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

function hasNonZeroNumeric(value) {
  const n = num(value);
  return n != null && n !== 0;
}

function sameNumeric(a, b) {
  const na = num(a);
  const nb = num(b);
  if (na == null && nb == null) return true;
  if (na == null || nb == null) return false;
  return na === nb;
}

function sameDisplayValue(a, b) {
  const sa = String(a ?? '').trim();
  const sb = String(b ?? '').trim();
  if (!sa && !sb) return true;
  if (sameNumeric(sa, sb)) return true;
  return sa.toLowerCase() === sb.toLowerCase();
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

function compareBackfillTo2025(row, databaseField, dwrValue, sourceUrl) {
  const field2025 = databaseField.replace('permits_2026_', 'permits_2025_');
  const value2025 = row[field2025] || '';
  const n2026 = num(dwrValue);
  const n2025 = num(value2025);
  let absoluteChange = '';
  let percentChange = '';
  let changeFlag = 'NO_2025_VALUE';

  if (n2026 != null && n2025 != null) {
    absoluteChange = n2026 - n2025;
    if (n2025 === 0) {
      changeFlag = n2026 === 0 ? 'NO_CHANGE' : 'NEW_FROM_ZERO_2025';
    } else {
      percentChange = (absoluteChange / n2025) * 100;
      changeFlag = Math.abs(percentChange) >= 20 ? 'BIG_CHANGE_20_PERCENT_OR_MORE' : 'WITHIN_20_PERCENT';
    }
  }

  return {
    hunt_code: row.hunt_code,
    hunt_name: row.hunt_name,
    species: row.species,
    field_2026: databaseField,
    field_2025: field2025,
    value_2026_backfilled_from_dwr: dwrValue || '',
    value_2025: value2025,
    absolute_change: absoluteChange,
    percent_change: percentChange === '' ? '' : percentChange.toFixed(2),
    change_flag: changeFlag,
    dwr_source_url: sourceUrl || ''
  };
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
  const allotmentAuditRows = [];
  let allotmentFilledCells = 0;
  let allotmentAlreadyMatchedCells = 0;
  let allotmentNotFilledNonmatchCells = 0;
  let allotmentNoDatabasePermitCells = 0;
  let allotmentConflictCells = 0;
  const backfillVs2025Rows = [];
  let permitCellsBackfilledFromDwr = 0;
  let permitBackfillBigChangeCells = 0;
  let permitBackfillNo2025ValueCells = 0;

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

    let rowAllotmentFilled = false;
    let rowPermitBackfilled = false;
    for (const [databaseField, dwrField, allotmentField] of [
      ['permits_2026_res', 'permits_2026_res', 'permit_allotment_2026_res'],
      ['permits_2026_nr', 'permits_2026_nr', 'permit_allotment_2026_nr'],
      ['permits_2026_total', 'permits_2026_total', 'permit_allotment_2026_total']
    ]) {
      let backfilledPermitFromDwr = false;
      if (!String(row[databaseField] ?? '').trim() && !String(row[allotmentField] ?? '').trim() && hasNonZeroNumeric(dwr[dwrField])) {
        row[databaseField] = dwr[dwrField];
        row[allotmentField] = dwr[dwrField];
        backfilledPermitFromDwr = true;
        rowPermitBackfilled = true;
        rowAllotmentFilled = true;
        permitCellsBackfilledFromDwr += 1;
        const backfillRow = compareBackfillTo2025(row, databaseField, dwr[dwrField], dwr.source_url || '');
        if (backfillRow.change_flag === 'BIG_CHANGE_20_PERCENT_OR_MORE' || backfillRow.change_flag === 'NEW_FROM_ZERO_2025') {
          permitBackfillBigChangeCells += 1;
        }
        if (backfillRow.change_flag === 'NO_2025_VALUE') permitBackfillNo2025ValueCells += 1;
        backfillVs2025Rows.push(backfillRow);
      }

      const comparisonStatus = backfilledPermitFromDwr
        ? 'BACKFILLED_FROM_DWR_NONZERO'
        : sameNumeric(row[databaseField], dwr[dwrField])
        ? 'MATCH'
        : differenceType(row[databaseField], dwr[dwrField]);

      if (comparisonStatus === 'MATCH' || comparisonStatus === 'BACKFILLED_FROM_DWR_NONZERO') permitExactMatches += 1;
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

      let allotmentAction = '';
      if (backfilledPermitFromDwr) {
        allotmentFilledCells += 1;
        allotmentAction = 'FILLED_PERMIT_AND_ALLOTMENT_FROM_DWR_NONZERO';
      } else if (!String(row[databaseField] ?? '').trim()) {
        allotmentNoDatabasePermitCells += 1;
        allotmentAction = 'NOT_FILLED_NO_DATABASE_PERMIT_VALUE';
      } else if (comparisonStatus !== 'MATCH') {
        allotmentNotFilledNonmatchCells += 1;
        allotmentAction = 'NOT_FILLED_PERMIT_DWR_NONMATCH';
      } else if (!String(row[allotmentField] ?? '').trim()) {
        row[allotmentField] = row[databaseField];
        allotmentFilledCells += 1;
        rowAllotmentFilled = true;
        allotmentAction = 'FILLED_FROM_MATCHED_DATABASE_AND_DWR_PERMIT';
      } else if (sameDisplayValue(row[allotmentField], row[databaseField])) {
        allotmentAlreadyMatchedCells += 1;
        allotmentAction = 'ALREADY_MATCHED_DATABASE_AND_DWR_PERMIT';
      } else {
        allotmentConflictCells += 1;
        allotmentAction = 'ALLOTMENT_CONFLICT_NOT_OVERWRITTEN';
      }

      allotmentAuditRows.push({
        hunt_code: row.hunt_code,
        hunt_name: row.hunt_name,
        species: row.species,
        permit_field: databaseField,
        allotment_field: allotmentField,
        dwr_field: dwrField,
        permit_dwr_comparison_status: comparisonStatus,
        allotment_action: allotmentAction,
        database_permit_value: row[databaseField] || '',
        allotment_value_after: row[allotmentField] || '',
        dwr_huntplanner_value: dwr[dwrField] || '',
        source_url: dwr.source_url || ''
      });
    }

    if (rowAllotmentFilled) {
      if (!row.permit_allotment_2026_source) row.permit_allotment_2026_source = 'DWR_HUNT_PLANNER_HaNumber_MATCHED_PERMITS_2026';
      if (!row.permit_allotment_2026_source_file) row.permit_allotment_2026_source_file = dwr.source_url || '';
      if (!row.permit_allotment_2026_status) row.permit_allotment_2026_status = 'DWR_HUNTPLANNER_CONFIRMED_MATCH';
    }
    if (rowPermitBackfilled) {
      if (!row.permits_2026_source) row.permits_2026_source = 'DWR_HUNT_PLANNER_HaNumber_NONZERO_BACKFILL';
      if (!row.permit_allotment_2026_source) row.permit_allotment_2026_source = 'DWR_HUNT_PLANNER_HaNumber_NONZERO_BACKFILL';
      if (!row.permit_allotment_2026_source_file) row.permit_allotment_2026_source_file = dwr.source_url || '';
      if (!row.permit_allotment_2026_status) row.permit_allotment_2026_status = 'DWR_HUNTPLANNER_NONZERO_BACKFILLED';
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
  writeCsv(NONMATCH_CSV, permitComparisons.filter(row => !['MATCH', 'BACKFILLED_FROM_DWR_NONZERO'].includes(row.comparison_status)), [
    'hunt_code',
    'hunt_name',
    'species',
    'field',
    'comparison_status',
    'database_value',
    'dwr_huntplanner_value',
    'source_url'
  ]);
  writeCsv(ALLOTMENT_AUDIT_CSV, allotmentAuditRows, [
    'hunt_code',
    'hunt_name',
    'species',
    'permit_field',
    'allotment_field',
    'dwr_field',
    'permit_dwr_comparison_status',
    'allotment_action',
    'database_permit_value',
    'allotment_value_after',
    'dwr_huntplanner_value',
    'source_url'
  ]);
  const comparisonStatusCounts = permitComparisons.reduce((acc, row) => {
    acc[row.comparison_status] = (acc[row.comparison_status] || 0) + 1;
    return acc;
  }, {});
  let effectiveBackfillVs2025Rows = backfillVs2025Rows;
  if (!effectiveBackfillVs2025Rows.length && fs.existsSync(BACKFILL_VS_2025_CSV)) {
    effectiveBackfillVs2025Rows = parseCsv(fs.readFileSync(BACKFILL_VS_2025_CSV, 'utf8')).records;
  }
  const effectiveBackfillBigChangeCells = effectiveBackfillVs2025Rows.filter(row => (
    row.change_flag === 'BIG_CHANGE_20_PERCENT_OR_MORE' || row.change_flag === 'NEW_FROM_ZERO_2025'
  )).length;
  const effectiveBackfillNo2025ValueCells = effectiveBackfillVs2025Rows.filter(row => row.change_flag === 'NO_2025_VALUE').length;
  const effectiveAllotmentFilledCells = allotmentFilledCells || effectiveBackfillVs2025Rows.length;
  writeCsv(BACKFILL_VS_2025_CSV, effectiveBackfillVs2025Rows, [
    'hunt_code',
    'hunt_name',
    'species',
    'field_2026',
    'field_2025',
    'value_2026_backfilled_from_dwr',
    'value_2025',
    'absolute_change',
    'percent_change',
    'change_flag',
    'dwr_source_url'
  ]);

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
    permit_cells_backfilled_from_dwr_nonzero: effectiveBackfillVs2025Rows.length,
    permit_backfill_cells_filled_this_run: permitCellsBackfilledFromDwr,
    permit_backfill_big_change_cells_vs_2025: effectiveBackfillBigChangeCells,
    permit_backfill_no_2025_value_cells: effectiveBackfillNo2025ValueCells,
    allotment_filled_cells_total: effectiveAllotmentFilledCells,
    allotment_filled_cells_this_run: allotmentFilledCells,
    allotment_filled_cells_from_matched_database_and_dwr: effectiveAllotmentFilledCells,
    allotment_already_matched_cells: allotmentAlreadyMatchedCells,
    allotment_not_filled_permit_dwr_nonmatch_cells: allotmentNotFilledNonmatchCells,
    allotment_not_filled_no_database_permit_cells: allotmentNoDatabasePermitCells,
    allotment_conflict_not_overwritten_cells: allotmentConflictCells,
    audit_csv: path.relative(ROOT, AUDIT_CSV).replace(/\\/g, '/'),
    permit_nonmatch_csv: path.relative(ROOT, NONMATCH_CSV).replace(/\\/g, '/'),
    allotment_audit_csv: path.relative(ROOT, ALLOTMENT_AUDIT_CSV).replace(/\\/g, '/'),
    backfill_vs_2025_csv: path.relative(ROOT, BACKFILL_VS_2025_CSV).replace(/\\/g, '/'),
    notes: [
      'DATABASE.csv uses the existing permits_2026_res, permits_2026_nr, and permits_2026_total columns; duplicate DWR-prefixed permit columns are not kept.',
      'permit_allotment_2026_res, permit_allotment_2026_nr, and permit_allotment_2026_total are filled only when DATABASE permits_2026_* and DWR Hunt Planner popup values match exactly.',
      'If both DATABASE permits_2026_* and permit_allotment_2026_* are blank while the DWR Hunt Planner popup has a nonzero value, both DATABASE fields are backfilled from DWR and compared to the matching 2025 permit field.',
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
  console.log(`Permit cells backfilled from DWR nonzero values: ${effectiveBackfillVs2025Rows.length}`);
  console.log(`Permit cells filled this run: ${permitCellsBackfilledFromDwr}`);
  console.log(`Allotment cells filled from matched permits: ${effectiveAllotmentFilledCells}`);
  console.log(`Allotment cells filled this run: ${allotmentFilledCells}`);
  console.log(`Allotment cells already matched: ${allotmentAlreadyMatchedCells}`);
  console.log(`Audit: ${AUDIT_JSON}`);
  console.log(`Permit nonmatches: ${NONMATCH_CSV}`);
  console.log(`Allotment audit: ${ALLOTMENT_AUDIT_CSV}`);
  console.log(`Backfill vs 2025 audit: ${BACKFILL_VS_2025_CSV}`);
}

main();
