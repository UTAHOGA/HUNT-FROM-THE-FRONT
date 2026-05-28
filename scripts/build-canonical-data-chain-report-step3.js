const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT_CSV = path.join(ROOT, 'processed_data', 'audits', 'canonical_data_chain_report.csv');
const OUTPUT_JSON = path.join(ROOT, 'processed_data', 'audits', 'canonical_data_chain_report.json');
const PAGES_LIMIT_BYTES = 25 * 1024 * 1024;

const CHAIN = [
  { file_path: 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv', canonical_role: 'official_current_source' },
  { file_path: 'processed_data/hunt_master_enriched.csv', canonical_role: 'runtime_master' },
  { file_path: 'processed_data/hunt_unit_reference_linked.csv', canonical_role: 'runtime_master' },
  { file_path: 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv', canonical_role: 'historical_bridge' },
  { file_path: 'processed_data/draw_reality_engine.csv', canonical_role: 'prediction_runtime' },
  { file_path: 'processed_data/draw_reality_engine_v2.csv', canonical_role: 'prediction_runtime' },
  { file_path: 'processed_data/draw_reality_engine_predictive_v2.csv', canonical_role: 'prediction_runtime' },
  { file_path: 'processed_data/ml_draw_predictions_v1.csv', canonical_role: 'prediction_runtime' },
  { file_path: 'processed_data/point_ladder_view.csv', canonical_role: 'prediction_runtime' },
  { file_path: 'processed_data/harvest_master.csv', canonical_role: 'harvest_evidence' },
  { file_path: 'processed_data/harvest_quality_features_all_years_by_hunt_code.csv', canonical_role: 'harvest_evidence' },
  { file_path: 'pipeline/RAW/hunt_unit_database/2026/csv/harvest_quality_features_by_hunt_code_2025_for_2026.csv', canonical_role: 'harvest_evidence' },
  { file_path: 'processed_data/model_outputs/draw_prediction_engine_v1.csv', canonical_role: 'model_output' },
  { file_path: 'processed_data/model_outputs/hunt_decision_scores_v1.csv', canonical_role: 'model_output' },
  { file_path: 'processed_data/model_outputs/point_creep_forecast_v1.csv', canonical_role: 'model_output' },
  { file_path: 'processed_data/model_outputs/model_run_report_v1.json', canonical_role: 'model_output_report' },
  { file_path: 'processed_data/library/library_page_hunts.csv', canonical_role: 'public_export' },
  { file_path: 'processed_data/library/library_page_summary.json', canonical_role: 'public_export' },
  { file_path: 'processed_data/hard_data_exports/library/library_page_data.json', canonical_role: 'public_export' },
  { file_path: 'processed_data/hard_data_exports/hard_data_manifest.web.json', canonical_role: 'public_export' },
];

const PUBLIC_LIBRARY_ALLOWED = new Set([
  'processed_data/library/library_page_hunts.csv',
  'processed_data/library/library_page_summary.json',
  'processed_data/hard_data_exports/library/library_page_data.json',
  'processed_data/hard_data_exports/hard_data_manifest.web.json',
]);

const HARD_DATA_RUNTIME_REQUIRED = new Set([
  'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv',
  'processed_data/hunt_master_enriched.csv',
  'processed_data/hunt_unit_reference_linked.csv',
  'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv',
  'processed_data/draw_reality_engine.csv',
  'processed_data/draw_reality_engine_v2.csv',
  'processed_data/draw_reality_engine_predictive_v2.csv',
  'processed_data/ml_draw_predictions_v1.csv',
  'processed_data/point_ladder_view.csv',
  'processed_data/harvest_master.csv',
  'processed_data/harvest_quality_features_all_years_by_hunt_code.csv',
  'pipeline/RAW/hunt_unit_database/2026/csv/harvest_quality_features_by_hunt_code_2025_for_2026.csv',
  'processed_data/library/library_page_hunts.csv',
  'processed_data/library/library_page_summary.json',
  'processed_data/hard_data_exports/library/library_page_data.json',
  'processed_data/hard_data_exports/hard_data_manifest.web.json',
]);

const RESEARCH_RUNTIME_REQUIRED = new Set([
  'processed_data/hunt_master_enriched.csv',
  'processed_data/hunt_unit_reference_linked.csv',
  'processed_data/draw_reality_engine.csv',
  'processed_data/draw_reality_engine_v2.csv',
  'processed_data/draw_reality_engine_predictive_v2.csv',
  'processed_data/ml_draw_predictions_v1.csv',
  'processed_data/point_ladder_view.csv',
  'processed_data/harvest_master.csv',
  'processed_data/harvest_quality_features_all_years_by_hunt_code.csv',
  'pipeline/RAW/hunt_unit_database/2026/csv/harvest_quality_features_by_hunt_code_2025_for_2026.csv',
  'processed_data/model_outputs/draw_prediction_engine_v1.csv',
  'processed_data/model_outputs/hunt_decision_scores_v1.csv',
  'processed_data/model_outputs/point_creep_forecast_v1.csv',
  'processed_data/model_outputs/model_run_report_v1.json',
]);

function normalizePath(p) {
  return String(p || '').replace(/\\/g, '/').replace(/^\.\//, '');
}

function normalizeHeader(value) {
  return String(value || '')
    .replace(/^\uFEFF/, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function normalizeCode(value) {
  return String(value || '').toUpperCase().replace(/\s+/g, '').replace(/[^A-Z0-9]/g, '');
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function csvEscape(v) {
  const s = v == null ? '' : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function extensionFor(p) {
  const ext = path.extname(p).toLowerCase();
  return ext ? ext.slice(1) : '';
}

function parseCsvLine(line) {
  const values = [];
  let field = '';
  let inQuotes = false;
  const src = String(line || '').replace(/^\uFEFF/, '');
  for (let i = 0; i < src.length; i += 1) {
    const c = src[i];
    const n = src[i + 1];
    if (c === '"' && inQuotes && n === '"') {
      field += '"';
      i += 1;
    } else if (c === '"') {
      inQuotes = !inQuotes;
    } else if (c === ',' && !inQuotes) {
      values.push(field);
      field = '';
    } else {
      field += c;
    }
  }
  values.push(field);
  return values;
}

function detectPrimaryKey(headers, filePath) {
  const set = new Set(headers);
  const rel = normalizePath(filePath);
  if (rel === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv' && set.has('current_hunt_code')) return 'current_hunt_code';
  for (const candidate of ['hunt_code', 'current_hunt_code', 'current_code', 'current_hunt_number', 'hunt_number', 'hunt_id']) {
    if (set.has(candidate)) return candidate;
  }
  return '';
}

function pickCodeColumn(headers, filePath) {
  const set = new Set(headers);
  const rel = normalizePath(filePath);
  if (rel === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv') {
    return set.has('current_hunt_code') ? 'current_hunt_code' : '';
  }
  for (const candidate of ['hunt_code', 'current_hunt_code', 'current_code', 'current_hunt_number', 'hunt_number', 'hunt_id']) {
    if (set.has(candidate)) return candidate;
  }
  return '';
}

async function profileCsv(absPath, filePath) {
  const result = {
    row_count_if_csv: '',
    primary_key_detected: '',
    code_column_used: '',
    code_set: new Set(),
    header_map: [],
  };

  let headers = [];
  let rowCount = 0;
  const stream = fs.createReadStream(absPath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  for await (const line of rl) {
    if (!String(line || '').trim()) continue;
    if (!headers.length) {
      headers = parseCsvLine(line).map(normalizeHeader);
      result.header_map = headers;
      result.primary_key_detected = detectPrimaryKey(headers, filePath);
      result.code_column_used = pickCodeColumn(headers, filePath);
      continue;
    }
    rowCount += 1;
    if (result.code_column_used) {
      const values = parseCsvLine(line);
      const idx = headers.indexOf(result.code_column_used);
      if (idx >= 0 && idx < values.length) {
        const code = normalizeCode(values[idx]);
        if (code) result.code_set.add(code);
      }
    }
  }
  result.row_count_if_csv = String(rowCount);
  return result;
}

function profileJson(absPath) {
  const size = fs.statSync(absPath).size;
  if (size > 50 * 1024 * 1024) return { json_key_count_if_json: 'not_counted_large_json', model_run_report_fields: {} };
  try {
    const raw = fs.readFileSync(absPath, 'utf8');
    const parsed = JSON.parse(raw);
    const keyCount = Array.isArray(parsed) ? parsed.length : (parsed && typeof parsed === 'object' ? Object.keys(parsed).length : 0);
    const modelRunFields = {};
    if (normalizePath(absPath).endsWith('processed_data/model_outputs/model_run_report_v1.json')) {
      modelRunFields.engine_version = parsed.engine_version || '';
      modelRunFields.input_dir = parsed.input_dir || '';
      modelRunFields.output_dir = parsed.output_dir || '';
      modelRunFields.allowed_hunt_codes = parsed?.counts?.allowed_hunt_codes ?? '';
      modelRunFields.draw_prediction_rows = parsed?.counts?.draw_prediction_rows ?? '';
      modelRunFields.decision_rows = parsed?.counts?.decision_rows ?? '';
      modelRunFields.point_creep_rows = parsed?.counts?.point_creep_rows ?? '';
      modelRunFields.draw_codes_ok = parsed?.validations?.draw_codes_ok ?? '';
      modelRunFields.decision_codes_ok = parsed?.validations?.decision_codes_ok ?? '';
      modelRunFields.point_creep_codes_ok = parsed?.validations?.point_creep_codes_ok ?? '';
    }
    return { json_key_count_if_json: String(keyCount), model_run_report_fields: modelRunFields };
  } catch {
    return { json_key_count_if_json: 'parse_error', model_run_report_fields: {} };
  }
}

function boolText(value) {
  return value ? 'true' : 'false';
}

function setDiff(a, b) {
  const out = new Set();
  for (const value of a) if (!b.has(value)) out.add(value);
  return out;
}

function sampleFromSet(set, limit = 10) {
  return Array.from(set).slice(0, limit).join('|');
}

function isLfsPointer(absPath) {
  try {
    const fd = fs.openSync(absPath, 'r');
    const buffer = Buffer.alloc(512);
    const read = fs.readSync(fd, buffer, 0, 512, 0);
    fs.closeSync(fd);
    const head = buffer.toString('utf8', 0, read);
    return head.includes('version https://git-lfs.github.com/spec/v1');
  } catch {
    return false;
  }
}

function recommendedStatus(filePath, exists, missingCount, extraCount, notes) {
  if (!exists) return 'FAIL_MISSING_FILE';
  const rel = normalizePath(filePath);
  if (rel === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv') {
    if (notes.includes('crosswalk_matched_current_codes=169')) return 'PASS_EXPECTED_PARTIAL_BRIDGE';
    return 'WARN_CROSSWALK_MATCH_NOT_169';
  }
  if (rel === 'processed_data/draw_reality_engine_predictive_v2.csv' || rel === 'processed_data/ml_draw_predictions_v1.csv') {
    return 'PASS_SUBSET_PREDICTION_ELIGIBLE';
  }
  if (rel.includes('/model_outputs/')) return 'PASS_MODEL_OUTPUT_ARTIFACT';
  if (missingCount > 0 && (rel.includes('harvest_') || rel.includes('harvest'))) return 'WARN_PARTIAL_HARVEST_COVERAGE';
  if (missingCount > 0) return 'WARN_PARTIAL_COVERAGE';
  if (extraCount > 0) return 'WARN_HAS_NONCURRENT_CODES';
  return 'PASS';
}

async function main() {
  const now = new Date().toISOString();

  const currentFile = CHAIN.find((f) => f.canonical_role === 'official_current_source').file_path;
  const currentAbs = path.join(ROOT, currentFile);
  if (!fs.existsSync(currentAbs)) throw new Error(`Missing official current source: ${currentFile}`);

  const currentProfile = await profileCsv(currentAbs, currentFile);
  const currentCodes = currentProfile.code_set;
  if (!currentCodes.size) throw new Error('Official current source has zero hunt codes.');

  const rows = [];
  const cloudflareFallbackFiles = [];
  const internalRuntimeFiles = [];
  const publicAllowedFiles = [];
  const predictiveSubsetFiles = [];
  const failures = [];

  for (const item of CHAIN) {
    const rel = normalizePath(item.file_path);
    const abs = path.join(ROOT, rel);
    const exists = fs.existsSync(abs);
    const ext = extensionFor(rel);

    let sizeBytes = 0;
    let sizeMb = '0.000';
    let rowCount = '';
    let jsonKeyCount = '';
    let primaryKey = '';
    let fileCodes = new Set();
    let notes = [];

    if (exists) {
      const stat = fs.statSync(abs);
      sizeBytes = stat.size;
      sizeMb = (stat.size / 1024 / 1024).toFixed(3);

      if (ext === 'csv') {
        const profile = await profileCsv(abs, rel);
        rowCount = profile.row_count_if_csv;
        primaryKey = profile.primary_key_detected;
        fileCodes = profile.code_set;

        if (rel === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv') {
          if (profile.code_column_used !== 'current_hunt_code') {
            notes.push('ERROR: crosswalk current join key is not current_hunt_code');
          } else {
            notes.push('crosswalk_join_key=current_hunt_code');
          }
          if (profile.header_map.includes('historical_hunt_code')) {
            notes.push('historical_hunt_code_preserved_as_metadata');
          }
        }

        if (rel === 'processed_data/hunt_master_enriched.csv') {
          const lfs = isLfsPointer(abs);
          notes.push(lfs ? 'ERROR: appears to be Git LFS pointer' : 'validated_real_csv_not_lfs_pointer');
          if (sizeBytes < 1024 * 1024) notes.push('WARN: unusually small size for hunt_master_enriched.csv');
          if (profile.header_map[0] !== 'hunt_code') notes.push(`WARN: first_header=${profile.header_map[0] || 'none'}`);
        }
      }

      if (ext === 'json') {
        const jsonProfile = profileJson(abs);
        jsonKeyCount = jsonProfile.json_key_count_if_json;
        if (Object.keys(jsonProfile.model_run_report_fields).length) {
          notes.push(`engine_version=${jsonProfile.model_run_report_fields.engine_version}`);
          notes.push(`input_dir=${jsonProfile.model_run_report_fields.input_dir}`);
          notes.push(`output_dir=${jsonProfile.model_run_report_fields.output_dir}`);
          notes.push(`allowed_hunt_codes=${jsonProfile.model_run_report_fields.allowed_hunt_codes}`);
          notes.push(`draw_prediction_rows=${jsonProfile.model_run_report_fields.draw_prediction_rows}`);
          notes.push(`decision_rows=${jsonProfile.model_run_report_fields.decision_rows}`);
          notes.push(`point_creep_rows=${jsonProfile.model_run_report_fields.point_creep_rows}`);
          notes.push(`draw_codes_ok=${jsonProfile.model_run_report_fields.draw_codes_ok}`);
          notes.push(`decision_codes_ok=${jsonProfile.model_run_report_fields.decision_codes_ok}`);
          notes.push(`point_creep_codes_ok=${jsonProfile.model_run_report_fields.point_creep_codes_ok}`);
        }
      }
    }

    const matchSet = new Set();
    for (const code of fileCodes) if (currentCodes.has(code)) matchSet.add(code);
    const missingSet = setDiff(currentCodes, fileCodes);
    const extraSet = setDiff(fileCodes, currentCodes);

    if (rel === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv') {
      notes.push(`crosswalk_current_code_rows=${fileCodes.size}`);
      notes.push(`crosswalk_matched_current_codes=${matchSet.size}`);
      notes.push(`crosswalk_unmatched_current_hunt_code_rows=${extraSet.size}`);
    }

    if (rel === 'processed_data/draw_reality_engine_predictive_v2.csv' || rel === 'processed_data/ml_draw_predictions_v1.csv') {
      notes.push('subset_may_be_prediction_eligible_only');
      predictiveSubsetFiles.push(rel);
    }

    if (rel.includes('harvest')) {
      if (missingSet.size > 0) notes.push('harvest_coverage_partial_missing_codes_expected_for_no_harvest_or_non_harvest_categories');
    }

    const cloudflareFallback = sizeBytes > PAGES_LIMIT_BYTES;
    if (cloudflareFallback) cloudflareFallbackFiles.push(rel);

    const pagesPublishable = !cloudflareFallback;
    const publicLibraryAllowed = PUBLIC_LIBRARY_ALLOWED.has(rel);
    const researchRuntime = RESEARCH_RUNTIME_REQUIRED.has(rel);
    const hardDataRuntime = HARD_DATA_RUNTIME_REQUIRED.has(rel);

    if (!publicLibraryAllowed) internalRuntimeFiles.push(rel);
    if (publicLibraryAllowed) publicAllowedFiles.push(rel);

    const recStatus = recommendedStatus(rel, exists, missingSet.size, extraSet.size, notes.join('; '));
    if (recStatus.startsWith('FAIL') || notes.some((n) => n.startsWith('ERROR'))) failures.push({ file_path: rel, recommended_status: recStatus, notes: notes.join('; ') });

    rows.push({
      file_path: rel,
      canonical_role: item.canonical_role,
      exists: boolText(exists),
      extension: ext,
      size_bytes: String(sizeBytes),
      size_mb: sizeMb,
      row_count_if_csv: rowCount,
      json_key_count_if_json: jsonKeyCount,
      primary_key_detected: primaryKey,
      current_hunt_code_match_count: String(matchSet.size),
      missing_current_hunt_codes_count: String(missingSet.size),
      extra_noncurrent_hunt_codes_count: String(extraSet.size),
      missing_current_hunt_codes_sample: sampleFromSet(missingSet),
      extra_noncurrent_hunt_codes_sample: sampleFromSet(extraSet),
      cloudflare_fallback_required: boolText(cloudflareFallback),
      pages_dist_publishable: boolText(pagesPublishable),
      public_library_allowed: boolText(publicLibraryAllowed),
      research_runtime_required: boolText(researchRuntime),
      hard_data_runtime_required: boolText(hardDataRuntime),
      recommended_status: recStatus,
      notes: notes.join('; '),
    });
  }

  const headers = [
    'file_path',
    'canonical_role',
    'exists',
    'extension',
    'size_bytes',
    'size_mb',
    'row_count_if_csv',
    'json_key_count_if_json',
    'primary_key_detected',
    'current_hunt_code_match_count',
    'missing_current_hunt_codes_count',
    'extra_noncurrent_hunt_codes_count',
    'missing_current_hunt_codes_sample',
    'extra_noncurrent_hunt_codes_sample',
    'cloudflare_fallback_required',
    'pages_dist_publishable',
    'public_library_allowed',
    'research_runtime_required',
    'hard_data_runtime_required',
    'recommended_status',
    'notes',
  ];

  const csvLines = [headers.map(csvEscape).join(',')];
  for (const row of rows) csvLines.push(headers.map((h) => csvEscape(row[h])).join(','));

  ensureDir(path.dirname(OUTPUT_CSV));
  fs.writeFileSync(OUTPUT_CSV, `${csvLines.join('\n')}\n`, 'utf8');

  const summary = {
    generated_at: now,
    canonical_current_source: currentFile,
    current_hunt_universe_count: currentCodes.size,
    crosswalk_expected_match_count: 169,
    crosswalk_actual_match_count: Number((rows.find((r) => r.file_path === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv') || {}).current_hunt_code_match_count || 0),
    predictive_subset_files: predictiveSubsetFiles,
    cloudflare_fallback_files: cloudflareFallbackFiles,
    public_library_allowed_files: publicAllowedFiles,
    internal_runtime_files: Array.from(new Set(internalRuntimeFiles)),
    failures,
    rows,
  };
  fs.writeFileSync(OUTPUT_JSON, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');

  console.log(`Wrote ${OUTPUT_CSV}`);
  console.log(`Wrote ${OUTPUT_JSON}`);
  console.log(`Current hunt universe count from DATABASE.csv: ${currentCodes.size}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
