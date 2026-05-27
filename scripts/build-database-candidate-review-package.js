const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const DATABASE = 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv';
const OUT_DIR = 'data_truth/comparison_outputs/database_candidate_review';
const REPORT = 'processed_data/database_candidate_review.md';

const SOURCES = [
  ['draw_results', 'processed_data/draw_reality_engine.csv'],
  ['draw_results', 'processed_data/draw_reality_engine_v2.csv'],
  ['prediction', 'processed_data/draw_reality_engine_predictive_v2.csv'],
  ['prediction', 'processed_data/ml_draw_predictions_v1.csv'],
  ['point_ladder', 'processed_data/point_ladder_view.csv'],
  ['coverage', 'processed_data/draw_system_coverage_report.csv'],
  ['coverage', 'processed_data/predictive_coverage_report.csv'],
  ['harvest', 'processed_data/harvest_master.csv'],
  ['harvest', 'processed_data/harvest_quality_features_all_years_by_hunt_code.csv'],
  ['harvest', 'pipeline/RAW/hunt_unit_database/2026/csv/harvest_quality_features_by_hunt_code_2025_for_2026.csv'],
  ['harvest_truth', 'data_truth/harvest_results_truth/normalized/harvest_quality_features_all_years_by_hunt_code.csv'],
  ['harvest_truth', 'data_truth/harvest_results_truth/normalized/harvest_results_all_years_long.csv'],
  ['permit_candidate', 'data_truth/draw_results_truth/normalized/expo_permit_draw_results_2026_total_only.csv'],
  ['crosswalk', 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv'],
  ['crosswalk', 'data_truth/crosswalk_truth/normalized/current_to_historical_hunt_code_crosswalk_2026.csv'],
  ['crosswalk', 'data_truth/crosswalk_truth/normalized/black_bear_BR_2024_2025_2026_crosswalk.csv'],
  ['permit_candidate', 'data_truth/permit_overlay_truth/validation/black_bear_2026_vs_2025_code_comparison.csv'],
  ['permit_candidate', 'data_truth/permit_overlay_truth/validation/elk_antlerless_private_lands_EA_2026_promotion_audit.csv'],
  ['permit_candidate', 'data_truth/permit_overlay_truth/validation/elk_private_lands_EL_LO_2026_rac_candidate_matches.csv'],
  ['permit_candidate', 'processed_data/model_outputs/dwr_2025_draw_result_permit_comparison.csv'],
  ['permit_candidate', 'processed_data/permits_2025_draw_results_promotion_report.csv'],
  ['permit_candidate', 'processed_data/permits_2025_draw_field_promotion_report.csv'],
  ['permit_candidate', 'processed_data/permits_2026_draw_field_promotion_report.csv'],
  ['comparison', 'processed_data/hunt_code_comparison_2025_to_2026.csv'],
  ['comparison', 'processed_data/complete_2023_harvest_vs_draw_comparison.csv'],
];

function abs(rel) { return path.join(ROOT, rel); }
function exists(rel) { return fs.existsSync(abs(rel)); }
function ensureParent(rel) { fs.mkdirSync(path.dirname(abs(rel)), { recursive: true }); }
function normalizeHeader(value) {
  return String(value || '')
    .replace(/^\uFEFF/, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}
function parseCsvLine(line) {
  const values = [];
  let field = '';
  let inQuotes = false;
  const src = String(line || '').replace(/^\uFEFF/, '');
  for (let i = 0; i < src.length; i += 1) {
    const c = src[i];
    const n = src[i + 1];
    if (c === '"' && inQuotes && n === '"') { field += '"'; i += 1; }
    else if (c === '"') inQuotes = !inQuotes;
    else if (c === ',' && !inQuotes) { values.push(field); field = ''; }
    else field += c;
  }
  values.push(field);
  return values;
}
function rowFromValues(headers, values, sourceFile) {
  const row = {};
  headers.forEach((header, index) => { row[header] = String(values[index] == null ? '' : values[index]).trim(); });
  row.__source_file = sourceFile;
  return row;
}
async function scanCsv(rel, onRow) {
  if (!exists(rel)) return { rows: 0, headers: [] };
  const rl = readline.createInterface({ input: fs.createReadStream(abs(rel), { encoding: 'utf8' }), crlfDelay: Infinity });
  let headers = null;
  let count = 0;
  for await (const line of rl) {
    if (!String(line || '').trim()) continue;
    if (!headers) { headers = parseCsvLine(line).map(normalizeHeader); continue; }
    count += 1;
    await onRow(rowFromValues(headers, parseCsvLine(line), rel), count);
  }
  return { rows: count, headers: headers || [] };
}
function esc(value) {
  const s = value == null ? '' : String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function writeCsv(rel, rows, preferredHeaders = []) {
  ensureParent(rel);
  const headerSet = new Set(preferredHeaders);
  for (const row of rows) Object.keys(row).forEach((key) => headerSet.add(key));
  const headers = Array.from(headerSet);
  const lines = [headers.map(esc).join(',')];
  for (const row of rows) lines.push(headers.map((header) => esc(row[header])).join(','));
  fs.writeFileSync(abs(rel), `${lines.join('\n')}\n`, 'utf8');
}
function writeJson(rel, value) {
  ensureParent(rel);
  fs.writeFileSync(abs(rel), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}
function first(row, names) {
  for (const name of names) {
    const value = row[normalizeHeader(name)];
    if (value != null && String(value).trim() !== '') return String(value).trim();
  }
  return '';
}
function cleanCode(value) {
  return String(value || '').trim().toUpperCase().replace(/\s+/g, '').replace(/[^A-Z0-9]/g, '');
}
function cleanNumber(value) {
  const text = String(value || '').replace(/,/g, '').trim();
  if (!text || ['N/A', 'NA', 'NONE'].includes(text.toUpperCase())) return 0;
  const n = Number(text);
  return Number.isFinite(n) ? n : 0;
}
function addToSet(item, field, value) {
  if (!value) return;
  if (!item[field]) item[field] = new Set();
  item[field].add(String(value));
}
function setFirst(item, field, value) {
  if (!item[field] && value != null && String(value).trim() !== '') item[field] = String(value).trim();
}
function stringifySets(row) {
  const out = {};
  for (const [key, value] of Object.entries(row)) {
    out[key] = value instanceof Set ? Array.from(value).sort().join(' | ') : value;
  }
  return out;
}
function candidateCode(row) {
  return cleanCode(first(row, [
    'hunt_code', 'source_hunt_code', 'candidate_hunt_code', 'historical_hunt_code',
    'historical_2025_code', 'historical_2024_code', 'candidate_rac_hunt_code', 'current_hunt_code', 'current_2026_code',
    'hunt number', 'hunt_number', 'hunt_no', 'code',
  ]));
}
function currentCode(row) {
  return cleanCode(first(row, ['current_hunt_code', 'current_2026_code', 'candidate_rac_hunt_code', 'hunt_code', 'candidate_hunt_code', 'source_hunt_code']));
}
function boundaryId(row) {
  return first(row, ['boundary_id', 'candidate_boundary_id', 'current_boundary_id', 'area_id', 'special_permit_area_id']);
}
function reportedYear(row) {
  return first(row, ['reported_draw_year', 'reported_hunt_year', 'year', 'source_year', 'sportsman_source_year']);
}
function modelTargetYear(row) {
  return first(row, ['model_target_year', 'prediction_year', 'forecast_year']);
}
function sourceFileValue(row) {
  return first(row, ['source_file', 'rac_source_file', 'source_path', 'source_file_path', 'truth_source_file', 'quota_source_file', 'target_file']);
}
function sourceStatus(row) {
  return first(row, ['source_status', 'validation_status', 'normalization_status', 'status', 'audit_status', 'crosswalk_status', 'mapping_status', 'promotion_status', 'data_status']);
}
function domainMetric(domain, row) {
  if (domain.includes('harvest')) return 'harvest_quality';
  if (domain === 'crosswalk') return 'hunt_code_crosswalk';
  if (domain === 'coverage') return 'model_coverage';
  if (domain === 'prediction') return 'prediction_runtime';
  if (domain === 'point_ladder') return 'point_ladder_runtime';
  if (domain === 'permit_candidate') return 'permit_candidate';
  if (first(row, ['comparison_field'])) return first(row, ['comparison_field']);
  return 'draw_results';
}
function sourceDataset(rel) {
  return path.basename(rel, path.extname(rel));
}
function possibleFillFields(db, evidence) {
  const fields = [];
  if (!db) return fields;
  if (!db.boundary_id && evidence.candidate_boundary_id) fields.push('boundary_id');
  if (evidence.model_target_year === '2026' || evidence.reported_year === '2026') {
    if (!db.permits_2026_total && evidence.candidate_total_value > 0) fields.push('permits_2026_total');
    if (!db.permit_allotment_2026_total && evidence.candidate_total_value > 0) fields.push('permit_allotment_2026_total');
  }
  if (evidence.model_target_year === '2025' || evidence.reported_year === '2025') {
    if (!db.permits_2025_total && evidence.candidate_total_value > 0) fields.push('permits_2025_total');
    if (!db.permits_2025_draw_total && evidence.candidate_total_value > 0) fields.push('permits_2025_draw_total');
  }
  return fields;
}
async function loadDatabase() {
  const db = new Map();
  await scanCsv(DATABASE, (row) => {
    const code = cleanCode(first(row, ['hunt_code']));
    if (!code) return;
    db.set(code, {
      hunt_code: code,
      boundary_id: first(row, ['boundary_id']),
      hunt_name: first(row, ['hunt_name']),
      species: first(row, ['species']),
      sex_type: first(row, ['sex_type']),
      weapon: first(row, ['weapon']),
      hunt_type: first(row, ['hunt_type']),
      season: first(row, ['season']),
      permits_2026_total: first(row, ['permits_2026_total']),
      permit_allotment_2026_total: first(row, ['permit_allotment_2026_total']),
      permits_2025_total: first(row, ['permits_2025_total']),
      permits_2025_draw_total: first(row, ['permits_2025_draw_total']),
    });
  });
  return db;
}
function aggregateEvidence(aggregates, domain, rel, row) {
  const code = candidateCode(row);
  const curCode = currentCode(row);
  if (!code && !curCode) return false;
  const current = curCode || code;
  const candidate = code || curCode;
  const year = reportedYear(row);
  const targetYear = modelTargetYear(row);
  const residency = first(row, ['residency']);
  const metric = domainMetric(domain, row);
  const key = [domain, sourceDataset(rel), current, candidate, year, targetYear, residency, metric].join('\u001f');
  if (!aggregates.has(key)) {
    aggregates.set(key, {
      evidence_domain: domain,
      source_dataset: sourceDataset(rel),
      current_hunt_code: current,
      candidate_hunt_code: candidate,
      reported_year: year,
      model_target_year: targetYear,
      residency,
      metric,
      row_count: 0,
      candidate_total_value: 0,
      candidate_resident_value: 0,
      candidate_nonresident_value: 0,
      candidate_applicants: 0,
      candidate_harvest: 0,
      candidate_hunters_afield: 0,
      candidate_success_pct: '',
      candidate_boundary_id: '',
      candidate_species: '',
      candidate_hunt_name: '',
      candidate_sex_type: '',
      candidate_hunt_type: '',
      candidate_weapon: '',
      source_files: new Set(),
      source_paths: new Set(),
      source_statuses: new Set(),
      source_row_examples: new Set(),
    });
  }
  const item = aggregates.get(key);
  item.row_count += 1;
  item.candidate_total_value += cleanNumber(first(row, [
    'total_public_draw_permits', 'total_public_permits', 'total_permits', 'permits',
    'permits_2026_total', 'permit_allotment_2026_total', 'quota_2026_total',
    'rac_permits_2026_total', 'permits_2025_total', 'permits_2024_total',
    'total_quota', 'observed_values', 'expected_2025_draw_total', 'harvest_objective_take_quota',
  ]));
  item.candidate_resident_value += cleanNumber(first(row, [
    'resident_total_permits', 'permits_2026_res', 'permits_2025_res', 'permits_2024_res', 'rac_permits_2026_res', 'resident_quota',
  ]));
  item.candidate_nonresident_value += cleanNumber(first(row, [
    'nonresident_total_permits', 'permits_2026_nr', 'permits_2025_nr', 'permits_2024_nr', 'rac_permits_2026_nr', 'nonresident_quota',
  ]));
  item.candidate_applicants += cleanNumber(first(row, [
    'eligible_applicants', 'resident_eligible_applicants', 'nonresident_eligible_applicants',
    'applicants', 'total_applications', 'sportsman_applicants',
  ]));
  item.candidate_harvest += cleanNumber(first(row, ['harvest_total', 'harvest', 'success_harvest']));
  item.candidate_hunters_afield += cleanNumber(first(row, ['hunters_afield', 'hunters', 'success_hunters']));
  setFirst(item, 'candidate_success_pct', first(row, ['percent_success', 'success_rate_pct', 'hunter_success_rate']));
  setFirst(item, 'candidate_boundary_id', boundaryId(row));
  setFirst(item, 'candidate_species', first(row, ['species']));
  setFirst(item, 'candidate_hunt_name', first(row, ['hunt_name', 'source_hunt_name', 'rac_hunt_name', 'hunt_name_2026', 'hunt_name_2025', 'hunt_name_2024', 'database_hunt_name', 'raw_hunt_name']));
  setFirst(item, 'candidate_sex_type', first(row, ['sex_type']));
  setFirst(item, 'candidate_hunt_type', first(row, ['hunt_type', 'hunt_type_2026', 'hunt_type_2025']));
  setFirst(item, 'candidate_weapon', first(row, ['weapon', 'source_weapon', 'rac_weapon', 'weapon_2026', 'weapon_2025']));
  addToSet(item, 'source_paths', rel);
  addToSet(item, 'source_files', sourceFileValue(row) || rel);
  addToSet(item, 'source_statuses', sourceStatus(row));
  addToSet(item, 'source_row_examples', first(row, ['source_row', 'row_number', 'page_number', 'source_pdf_page']));
  return true;
}

async function main() {
  const database = await loadDatabase();
  const aggregates = new Map();
  const inventory = [];

  for (const [domain, rel] of SOURCES) {
    const status = {
      evidence_domain: domain,
      source_path: rel,
      source_dataset: sourceDataset(rel),
      exists: exists(rel) ? 'true' : 'false',
      source_rows: 0,
      evidence_rows_used: 0,
      source_size_bytes: exists(rel) ? fs.statSync(abs(rel)).size : 0,
    };
    if (exists(rel)) {
      const scan = await scanCsv(rel, (row) => {
        status.source_rows += 1;
        if (aggregateEvidence(aggregates, domain, rel, row)) status.evidence_rows_used += 1;
      });
      status.headers = scan.headers.join(' | ');
    }
    inventory.push(status);
    console.log(`${status.exists === 'true' ? 'Scanned' : 'Missing'} ${rel}: ${status.source_rows} rows, ${status.evidence_rows_used} evidence rows`);
  }

  const records = Array.from(aggregates.values()).map((item) => {
    const db = database.get(item.current_hunt_code) || database.get(item.candidate_hunt_code);
    const databaseMatchStatus = database.has(item.current_hunt_code)
      ? 'CURRENT_CODE_MATCH'
      : database.has(item.candidate_hunt_code)
        ? 'CANDIDATE_CODE_MATCH'
        : 'MISSING_FROM_DATABASE';
    const fillFields = possibleFillFields(db, item);
    return stringifySets({
      ...item,
      database_match_status: databaseMatchStatus,
      database_hunt_code: db?.hunt_code || '',
      database_boundary_id: db?.boundary_id || '',
      database_species: db?.species || '',
      database_hunt_name: db?.hunt_name || '',
      database_sex_type: db?.sex_type || '',
      database_hunt_type: db?.hunt_type || '',
      database_weapon: db?.weapon || '',
      database_permits_2026_total: db?.permits_2026_total || '',
      database_permit_allotment_2026_total: db?.permit_allotment_2026_total || '',
      database_permits_2025_total: db?.permits_2025_total || '',
      database_permits_2025_draw_total: db?.permits_2025_draw_total || '',
      possible_fill_fields: fillFields.join(' | '),
      review_status: databaseMatchStatus === 'MISSING_FROM_DATABASE' ? 'CROSSWALK_REQUIRED' : fillFields.length ? 'POSSIBLE_DATABASE_FILL' : 'COMPARISON_EVIDENCE',
    });
  }).sort((a, b) => String(a.current_hunt_code).localeCompare(String(b.current_hunt_code)) || String(a.evidence_domain).localeCompare(String(b.evidence_domain)));

  const byCodeMap = new Map();
  for (const record of records) {
    const code = record.database_hunt_code || record.current_hunt_code || record.candidate_hunt_code;
    if (!byCodeMap.has(code)) {
      byCodeMap.set(code, {
        current_hunt_code: code,
        database_match_status: record.database_match_status,
        database_boundary_id: record.database_boundary_id,
        database_species: record.database_species,
        database_hunt_name: record.database_hunt_name,
        database_sex_type: record.database_sex_type,
        database_hunt_type: record.database_hunt_type,
        database_weapon: record.database_weapon,
        evidence_record_count: 0,
        source_row_count: 0,
        evidence_domains: new Set(),
        source_datasets: new Set(),
        reported_years: new Set(),
        model_target_years: new Set(),
        possible_fill_fields: new Set(),
        review_statuses: new Set(),
      });
    }
    const item = byCodeMap.get(code);
    item.evidence_record_count += 1;
    item.source_row_count += cleanNumber(record.row_count);
    addToSet(item, 'evidence_domains', record.evidence_domain);
    addToSet(item, 'source_datasets', record.source_dataset);
    addToSet(item, 'reported_years', record.reported_year);
    addToSet(item, 'model_target_years', record.model_target_year);
    String(record.possible_fill_fields || '').split('|').map((x) => x.trim()).filter(Boolean).forEach((x) => item.possible_fill_fields.add(x));
    addToSet(item, 'review_statuses', record.review_status);
  }
  const byCode = Array.from(byCodeMap.values()).map(stringifySets).sort((a, b) => String(a.current_hunt_code).localeCompare(String(b.current_hunt_code)));

  const outRecords = `${OUT_DIR}/database_candidate_review_records.csv`;
  const outByCode = `${OUT_DIR}/database_candidate_review_by_current_code.csv`;
  const outInventory = `${OUT_DIR}/database_candidate_review_source_inventory.csv`;
  const outSummary = `${OUT_DIR}/database_candidate_review_summary.json`;
  const recordHeaders = [
    'evidence_domain', 'source_dataset', 'current_hunt_code', 'candidate_hunt_code',
    'database_match_status', 'review_status', 'possible_fill_fields',
    'reported_year', 'model_target_year', 'residency', 'metric', 'row_count',
    'candidate_total_value', 'candidate_resident_value', 'candidate_nonresident_value',
    'candidate_applicants', 'candidate_harvest', 'candidate_hunters_afield', 'candidate_success_pct',
    'candidate_boundary_id', 'candidate_species', 'candidate_hunt_name', 'candidate_sex_type',
    'candidate_hunt_type', 'candidate_weapon', 'database_hunt_code', 'database_boundary_id',
    'database_species', 'database_hunt_name', 'database_sex_type', 'database_hunt_type',
    'database_weapon', 'database_permits_2026_total', 'database_permit_allotment_2026_total',
    'database_permits_2025_total', 'database_permits_2025_draw_total',
    'source_files', 'source_paths', 'source_statuses', 'source_row_examples',
  ];
  writeCsv(outRecords, records, recordHeaders);
  writeCsv(outByCode, byCode, [
    'current_hunt_code', 'database_match_status', 'database_boundary_id', 'database_species',
    'database_hunt_name', 'database_sex_type', 'database_hunt_type', 'database_weapon',
    'evidence_record_count', 'source_row_count', 'evidence_domains', 'source_datasets',
    'reported_years', 'model_target_years', 'possible_fill_fields', 'review_statuses',
  ]);
  writeCsv(outInventory, inventory, ['evidence_domain', 'source_dataset', 'source_path', 'exists', 'source_rows', 'evidence_rows_used', 'source_size_bytes', 'headers']);

  const summary = {
    generated_at: new Date().toISOString(),
    current_database: DATABASE,
    database_hunt_codes: database.size,
    source_files_registered: SOURCES.length,
    source_files_present: inventory.filter((row) => row.exists === 'true').length,
    source_rows_scanned: inventory.reduce((sum, row) => sum + row.source_rows, 0),
    evidence_records: records.length,
    current_code_rollup_rows: byCode.length,
    database_match_status_counts: countBy(records, 'database_match_status'),
    review_status_counts: countBy(records, 'review_status'),
    evidence_domain_counts: countBy(records, 'evidence_domain'),
    possible_fill_record_count: records.filter((row) => row.review_status === 'POSSIBLE_DATABASE_FILL').length,
    missing_database_record_count: records.filter((row) => row.database_match_status === 'MISSING_FROM_DATABASE').length,
    outputs: {
      records: outRecords,
      by_current_code: outByCode,
      source_inventory: outInventory,
      summary: outSummary,
      report: REPORT,
    },
    guardrail: 'Comparison evidence only. This package does not modify DATABASE.csv or promote any values.',
  };
  writeJson(outSummary, summary);
  writeReport(summary);
  if (records.length === 0) throw new Error('No candidate evidence records were generated.');
  if (byCode.length === 0) throw new Error('No by-current-code records were generated.');
  console.log(JSON.stringify(summary, null, 2));
}

function countBy(rows, field) {
  const counts = {};
  for (const row of rows) {
    const key = String(row[field] || 'UNKNOWN').trim() || 'UNKNOWN';
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}
function writeReport(summary) {
  ensureParent(REPORT);
  const lines = [
    '# Database Candidate Review Package',
    '',
    `Generated: \`${summary.generated_at}\``,
    '',
    'This is the consolidated review surface for candidate promotion/data-fill evidence. It compares normalized draw, harvest, crosswalk, permit-candidate, coverage, and prediction evidence against the current 2026 `DATABASE.csv` without changing the database.',
    '',
    `- Current database hunt codes: \`${summary.database_hunt_codes}\``,
    `- Source files registered: \`${summary.source_files_registered}\``,
    `- Source files present: \`${summary.source_files_present}\``,
    `- Source rows scanned: \`${summary.source_rows_scanned}\``,
    `- Evidence records: \`${summary.evidence_records}\``,
    `- Current-code rollup rows: \`${summary.current_code_rollup_rows}\``,
    `- Possible database-fill evidence records: \`${summary.possible_fill_record_count}\``,
    `- Missing-database evidence records: \`${summary.missing_database_record_count}\``,
    '',
    '## Outputs',
    '',
  ];
  Object.entries(summary.outputs).forEach(([key, value]) => lines.push(`- \`${key}\`: \`${value}\``));
  fs.writeFileSync(abs(REPORT), `${lines.join('\n')}\n`, 'utf8');
}

main().catch((error) => {
  console.error('Failed to build database candidate review package.');
  console.error(error);
  process.exit(1);
});
