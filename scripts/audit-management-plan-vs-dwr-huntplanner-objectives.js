#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DATABASE_CSV = path.join(ROOT, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv', 'DATABASE.csv');
const ELK_PLAN_CSV = path.join(ROOT, 'processed_data', 'audits', 'elk_plan_foundational_reference.csv');
const DEER_PLAN_CSV = path.join(ROOT, 'processed_data', 'audits', 'mule_deer_plan_foundational_reference.csv');
const OUT_JSON = path.join(ROOT, 'processed_data', 'audits', 'management_plan_dwr_huntplanner_objective_comparison.json');
const OUT_CSV = path.join(ROOT, 'processed_data', 'audits', 'management_plan_dwr_huntplanner_objective_comparison.csv');

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
      } else if (ch === '"') inQuotes = false;
      else cell += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n') {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else if (ch !== '\r') cell += ch;
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows[0].map(h => h.replace(/^\uFEFF/, ''));
  return {
    headers,
    records: rows.slice(1).filter(r => r.some(v => v !== '')).map(values => {
      const out = {};
      headers.forEach((header, index) => {
        out[header] = values[index] ?? '';
      });
      return out;
    })
  };
}

function csvEscape(value) {
  const s = value == null ? '' : String(value);
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function writeCsv(filePath, rows, headers) {
  const lines = [headers.join(',')];
  for (const row of rows) lines.push(headers.map(header => csvEscape(row[header])).join(','));
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

function numeric(value) {
  const n = Number(String(value ?? '').replace(/,/g, '').trim());
  return Number.isFinite(n) ? n : null;
}

function planValue(rows, keyId) {
  const row = rows.find(r => r.key_id === keyId);
  return row ? numeric(row.value) : null;
}

function dwrSpeciesSummary(databaseRows, species) {
  const byBoundary = new Map();
  for (const row of databaseRows) {
    if (row.species !== species) continue;
    if (!row.boundary_id) continue;
    if (!row.dwr_huntplanner_population_objective && !row.dwr_huntplanner_current_population_estimate) continue;
    const key = `${row.species}|${row.boundary_id}`;
    if (!byBoundary.has(key)) byBoundary.set(key, row);
  }

  const uniqueRows = [...byBoundary.values()];
  const objectiveSum = uniqueRows.reduce((sum, row) => sum + (numeric(row.dwr_huntplanner_population_objective) || 0), 0);
  const estimateSum = uniqueRows.reduce((sum, row) => sum + (numeric(row.dwr_huntplanner_current_population_estimate) || 0), 0);

  return {
    unique_boundary_rows: uniqueRows.length,
    dwr_population_objective_sum: objectiveSum,
    dwr_current_population_estimate_sum: estimateSum
  };
}

function comparisonRow({ species, metric, planValueNumber, dwrValueNumber, dwrBoundaryCount, planSource }) {
  const difference = dwrValueNumber == null || planValueNumber == null ? '' : dwrValueNumber - planValueNumber;
  const percentDifference = difference === '' || !planValueNumber ? '' : (difference / planValueNumber) * 100;
  return {
    species,
    metric,
    plan_value: planValueNumber ?? '',
    dwr_huntplanner_dedup_boundary_sum: dwrValueNumber ?? '',
    difference,
    percent_difference: percentDifference === '' ? '' : percentDifference.toFixed(2),
    dwr_unique_boundary_count: dwrBoundaryCount,
    comparison_status: difference === 0 ? 'MATCH' : 'NOT_EXACT_MATCH',
    interpretation: 'Management-plan statewide values and DWR Hunt Planner unit/boundary popup values are related context but should not be treated as identical truth without unit-scope reconciliation.',
    plan_source: planSource
  };
}

function main() {
  const database = parseCsv(fs.readFileSync(DATABASE_CSV, 'utf8')).records;
  const elkPlan = parseCsv(fs.readFileSync(ELK_PLAN_CSV, 'utf8')).records;
  const deerPlan = parseCsv(fs.readFileSync(DEER_PLAN_CSV, 'utf8')).records;
  const elk = dwrSpeciesSummary(database, 'Elk');
  const deer = dwrSpeciesSummary(database, 'Deer');

  const rows = [
    comparisonRow({
      species: 'Elk',
      metric: 'Statewide population objective',
      planValueNumber: planValue(elkPlan, 'ELK_STATEWIDE_POP_OBJECTIVE'),
      dwrValueNumber: elk.dwr_population_objective_sum,
      dwrBoundaryCount: elk.unique_boundary_rows,
      planSource: 'elk_plan.pdf'
    }),
    comparisonRow({
      species: 'Elk',
      metric: 'Current statewide population estimate',
      planValueNumber: planValue(elkPlan, 'ELK_STATEWIDE_POP_EST'),
      dwrValueNumber: elk.dwr_current_population_estimate_sum,
      dwrBoundaryCount: elk.unique_boundary_rows,
      planSource: 'elk_plan.pdf'
    }),
    comparisonRow({
      species: 'Deer',
      metric: 'Statewide population objective',
      planValueNumber: planValue(deerPlan, 'MD_POP_OBJ_STATEWIDE'),
      dwrValueNumber: deer.dwr_population_objective_sum,
      dwrBoundaryCount: deer.unique_boundary_rows,
      planSource: 'mule_deer_plan.pdf'
    }),
    comparisonRow({
      species: 'Deer',
      metric: '2023 postseason population estimate',
      planValueNumber: planValue(deerPlan, 'MD_POSTSEASON_2023_EST'),
      dwrValueNumber: deer.dwr_current_population_estimate_sum,
      dwrBoundaryCount: deer.unique_boundary_rows,
      planSource: 'mule_deer_plan.pdf'
    })
  ];

  fs.mkdirSync(path.dirname(OUT_JSON), { recursive: true });
  writeCsv(OUT_CSV, rows, [
    'species',
    'metric',
    'plan_value',
    'dwr_huntplanner_dedup_boundary_sum',
    'difference',
    'percent_difference',
    'dwr_unique_boundary_count',
    'comparison_status',
    'interpretation',
    'plan_source'
  ]);

  fs.writeFileSync(OUT_JSON, `${JSON.stringify({
    created_at: new Date().toISOString(),
    database_csv: path.relative(ROOT, DATABASE_CSV).replace(/\\/g, '/'),
    elk_plan_csv: path.relative(ROOT, ELK_PLAN_CSV).replace(/\\/g, '/'),
    deer_plan_csv: path.relative(ROOT, DEER_PLAN_CSV).replace(/\\/g, '/'),
    comparison_rows: rows,
    notes: [
      'DWR Hunt Planner values are deduped by species + boundary_id before summing.',
      'The comparison is scope/context validation only; it does not overwrite plan or DATABASE values.',
      'Observed nonmatches indicate the Hunt Planner popup fields should be retained as unit/hunt context, not assumed to equal statewide plan totals.'
    ]
  }, null, 2)}\n`, 'utf8');

  console.log(`Wrote ${OUT_CSV}`);
  console.log(`Wrote ${OUT_JSON}`);
}

main();
