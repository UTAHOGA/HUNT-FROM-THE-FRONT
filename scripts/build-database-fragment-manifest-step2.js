const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const HUNTS_ROOT = path.resolve(ROOT, '..', 'HUNTS');
const HUNTS_DATA_TRUTH = path.join(HUNTS_ROOT, 'data_truth');

const OUTPUT_CSV = path.join(ROOT, 'processed_data', 'audits', 'database_fragment_manifest.csv');
const OUTPUT_JSON = path.join(ROOT, 'processed_data', 'audits', 'database_fragment_manifest.json');

const SCAN_TARGETS = [
  { kind: 'local', rel: 'processed_data' },
  { kind: 'local', rel: 'pipeline' },
  { kind: 'local', rel: 'data' },
  { kind: 'local', rel: '_exports' },
  { kind: 'hunts', rel: 'data_truth' },
];

const INCLUDE_EXT = new Set(['.csv', '.json', '.tsv', '.txt', '.md', '.xlsx', '.xls', '.pdf', '.geojson', '.sqlite', '.db', '.zip']);

const CLASSIFICATIONS = new Set([
  'official_current_source',
  'normalized_truth_source',
  'candidate_promotion_file',
  'runtime_master',
  'prediction_runtime',
  'model_output',
  'harvest_evidence',
  'historical_crosswalk',
  'public_export',
  'static_build_output',
  'audit_validation_report',
  'manifest',
  'pdf_ingest_output',
  'fixture_preview',
  'obsolete_fragment',
  'unknown_needs_review',
]);

function normalize(p) {
  return String(p || '').replace(/\\/g, '/').replace(/^\.\//, '');
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function csvEscape(v) {
  const s = v == null ? '' : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function rowCountCsvStream(absPath) {
  return new Promise((resolve) => {
    let rows = 0;
    let headerSeen = false;
    const stream = fs.createReadStream(absPath, { encoding: 'utf8' });
    const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
    rl.on('line', (line) => {
      if (!line || !String(line).trim()) return;
      if (!headerSeen) {
        headerSeen = true;
        return;
      }
      rows += 1;
    });
    rl.on('close', () => resolve(String(rows)));
    rl.on('error', () => resolve('read_error'));
    stream.on('error', () => resolve('read_error'));
  });
}

function countJsonKeys(absPath, sizeBytes) {
  if (sizeBytes > 50 * 1024 * 1024) return 'not_counted_large_json';
  try {
    const raw = fs.readFileSync(absPath, 'utf8');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return String(parsed.length);
    if (parsed && typeof parsed === 'object') return String(Object.keys(parsed).length);
    return '0';
  } catch {
    return 'parse_error';
  }
}

function listFiles(absRoot) {
  const out = [];
  if (!fs.existsSync(absRoot)) return out;
  const stack = [absRoot];
  while (stack.length) {
    const dir = stack.pop();
    let entries = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const abs = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (['.git', 'node_modules', '.wrangler', '__pycache__'].includes(entry.name)) continue;
        stack.push(abs);
      } else {
        out.push(abs);
      }
    }
  }
  return out;
}

const explicitClassification = new Map([
  ['pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv', 'official_current_source'],
  ['processed_data/hunt_master_enriched.csv', 'runtime_master'],
  ['processed_data/hunt_unit_reference_linked.csv', 'runtime_master'],
  ['processed_data/draw_reality_engine.csv', 'prediction_runtime'],
  ['processed_data/draw_reality_engine_v2.csv', 'prediction_runtime'],
  ['processed_data/draw_reality_engine_predictive_v2.csv', 'prediction_runtime'],
  ['processed_data/ml_draw_predictions_v1.csv', 'prediction_runtime'],
  ['processed_data/point_ladder_view.csv', 'prediction_runtime'],
  ['processed_data/model_outputs/draw_prediction_engine_v1.csv', 'model_output'],
  ['processed_data/model_outputs/hunt_decision_scores_v1.csv', 'model_output'],
  ['processed_data/model_outputs/point_creep_forecast_v1.csv', 'model_output'],
  ['processed_data/model_outputs/model_run_report_v1.json', 'model_output'],
  ['processed_data/harvest_master.csv', 'harvest_evidence'],
  ['processed_data/harvest_quality_features_all_years_by_hunt_code.csv', 'harvest_evidence'],
  ['pipeline/RAW/hunt_unit_database/2026/csv/harvest_quality_features_by_hunt_code_2025_for_2026.csv', 'harvest_evidence'],
  ['processed_data/current_to_historical_hunt_code_crosswalk_2026.csv', 'historical_crosswalk'],
  ['processed_data/library/library_page_hunts.csv', 'public_export'],
  ['processed_data/library/library_page_summary.json', 'public_export'],
  ['processed_data/hard_data_exports/library/library_page_data.json', 'public_export'],
  ['processed_data/hard_data_exports/hard_data_manifest.web.json', 'public_export'],
]);

function classifyPath(filePath, sourceKind) {
  const rel = normalize(filePath);
  if (sourceKind === 'hunts') {
    if (rel.includes('/validation/')) return 'audit_validation_report';
    if (rel.includes('/normalized/')) return 'normalized_truth_source';
    if (rel.includes('/raw_inventory/') || rel.includes('/raw_packages/') || rel.includes('/extracted/')) return 'candidate_promotion_file';
    return 'candidate_promotion_file';
  }
  if (explicitClassification.has(rel)) return explicitClassification.get(rel);

  const lower = rel.toLowerCase();
  const basename = path.basename(lower);

  if (lower.startsWith('pages-dist/')) return 'static_build_output';
  if (lower.includes('/backups/')) return 'obsolete_fragment';
  if (lower.includes('/fixtures/')) return 'fixture_preview';
  if (lower.includes('/pdf_ingest/')) return 'pdf_ingest_output';
  if (lower.includes('/_fixture_rebuild_preview/')) return 'fixture_preview';
  if (/\s\(\d+\)(\.[^.]+)$/.test(path.basename(rel))) return 'obsolete_fragment';
  if (lower.includes('/audits/') || lower.includes('/validation/') || lower.includes('_audit') || lower.includes('_report') || lower.includes('_summary')) return 'audit_validation_report';
  if (lower.includes('/manifests/')) return 'manifest';
  if (lower.includes('/model_outputs/')) return 'model_output';
  if (lower.includes('/library/') || lower.includes('/hard_data_exports/') || lower.includes('/public/hard-copy/')) return 'public_export';
  if (lower.includes('draw_reality') || lower.includes('point_ladder') || lower.includes('ml_draw_predictions') || lower.includes('predictive_coverage') || lower.includes('draw_system_coverage')) return 'prediction_runtime';
  if (lower.includes('hunt_master_enriched') || lower.includes('hunt_unit_reference_linked')) return 'runtime_master';
  if (lower.includes('crosswalk')) return 'historical_crosswalk';
  if (lower.includes('harvest')) return 'harvest_evidence';
  if (lower.endsWith('database.csv') && lower.includes('hunt_unit_database/2026/csv/')) return 'official_current_source';
  if (lower.includes('candidate') || lower.includes('promotion') || lower.includes('compare') || lower.includes('reconcil') || lower.includes('canonical')) return 'candidate_promotion_file';
  if (lower.includes('obsolete') || basename.includes('backup') || basename.includes('tmp')) return 'obsolete_fragment';

  return 'unknown_needs_review';
}

function canonicalRole(classification, filePath) {
  const rel = normalize(filePath);
  switch (classification) {
    case 'official_current_source': return 'Official current 2026 source';
    case 'runtime_master': return 'Runtime enriched master/reference';
    case 'prediction_runtime': return 'Prediction/runtime feed';
    case 'model_output': return 'Model output artifact';
    case 'harvest_evidence': return 'Harvest evidence source';
    case 'historical_crosswalk': return 'Current-to-historical bridge';
    case 'public_export': return 'Curated public export';
    case 'static_build_output': return 'Static site build output';
    case 'audit_validation_report': return 'Audit/validation evidence';
    case 'manifest': return 'Pipeline/source manifest';
    case 'pdf_ingest_output': return 'PDF ingest/extraction output';
    case 'fixture_preview': return 'Fixture/preview output';
    case 'normalized_truth_source': return 'Normalized truth layer';
    case 'candidate_promotion_file': return 'Candidate promotion/review source';
    case 'obsolete_fragment': return 'Obsolete/duplicate fragment candidate';
    default:
      if (rel.startsWith('HUNTS/data_truth/')) return 'External truth candidate';
      return 'Needs review';
  }
}

function boolFlags(classification) {
  const publish = classification === 'public_export';
  const usePrediction = new Set(['official_current_source', 'runtime_master', 'prediction_runtime', 'historical_crosswalk', 'harvest_evidence']).has(classification);
  const copyToPages = new Set(['public_export', 'static_build_output']).has(classification);
  const archive = new Set(['obsolete_fragment', 'fixture_preview']).has(classification);
  return {
    should_publish_public: publish ? 'true' : 'false',
    should_use_prediction_engine: usePrediction ? 'true' : 'false',
    should_copy_to_pages_dist: copyToPages ? 'true' : 'false',
    should_archive: archive ? 'true' : 'false',
  };
}

function extensionFor(fileName) {
  const ext = path.extname(fileName).toLowerCase();
  return ext ? ext.slice(1) : '';
}

function familyKey(fileName) {
  const ext = path.extname(fileName).toLowerCase();
  let base = path.basename(fileName, ext).toLowerCase();
  base = base.replace(/[_-]v\d+(?:\.\d+)*/g, '');
  base = base.replace(/[_-](20\d{2}|19\d{2})/g, '');
  base = base.replace(/\s+/g, '_');
  base = base.replace(/__+/g, '_');
  return `${base}${ext}`;
}

async function main() {
  const records = [];

  for (const target of SCAN_TARGETS) {
    const absRoot = target.kind === 'local' ? path.join(ROOT, target.rel) : path.join(HUNTS_ROOT, target.rel);
    if (!fs.existsSync(absRoot)) continue;

    const files = listFiles(absRoot);
    for (const absPath of files) {
      const fileName = path.basename(absPath);
      const ext = path.extname(fileName).toLowerCase();
      if (!INCLUDE_EXT.has(ext)) continue;

      const rel = target.kind === 'local'
        ? normalize(path.relative(ROOT, absPath))
        : normalize(`HUNTS/${path.relative(HUNTS_ROOT, absPath)}`);

      const stat = fs.statSync(absPath);
      const classification = classifyPath(rel, target.kind);
      if (!CLASSIFICATIONS.has(classification)) continue;

      let rowCount = '';
      if (ext === '.csv' || ext === '.tsv') rowCount = await rowCountCsvStream(absPath);

      let jsonKeyCountValue = '';
      if (ext === '.json' || ext === '.geojson') jsonKeyCountValue = countJsonKeys(absPath, stat.size);

      const flags = boolFlags(classification);

      records.push({
        file_path: rel,
        file_name: fileName,
        extension: extensionFor(fileName),
        size_bytes: String(stat.size),
        size_mb: (stat.size / 1024 / 1024).toFixed(3),
        row_count_if_csv: rowCount,
        json_key_count_if_json: jsonKeyCountValue,
        modified_time_if_available: stat.mtime.toISOString(),
        classification,
        canonical_role: canonicalRole(classification, rel),
        should_publish_public: flags.should_publish_public,
        should_use_prediction_engine: flags.should_use_prediction_engine,
        should_copy_to_pages_dist: flags.should_copy_to_pages_dist,
        should_archive: flags.should_archive,
        suspected_duplicate_of: '',
        notes: target.kind === 'hunts' ? 'External HUNTS truth candidate; read-only inventory.' : '',
      });
    }
  }

  records.sort((a, b) => a.file_path.localeCompare(b.file_path));

  const dupByNameSize = new Map();
  for (const rec of records) {
    const key = `${rec.file_name.toLowerCase()}::${rec.size_bytes}`;
    if (!dupByNameSize.has(key)) dupByNameSize.set(key, []);
    dupByNameSize.get(key).push(rec);
  }
  for (const matches of dupByNameSize.values()) {
    if (matches.length < 2) continue;
    const canonical = matches[0].file_path;
    for (let i = 1; i < matches.length; i += 1) {
      matches[i].suspected_duplicate_of = canonical;
      matches[i].notes = matches[i].notes ? `${matches[i].notes} Duplicate file name+size match.` : 'Duplicate file name+size match.';
    }
  }

  const familyGroups = new Map();
  for (const rec of records) {
    const key = familyKey(rec.file_name);
    if (!familyGroups.has(key)) familyGroups.set(key, []);
    familyGroups.get(key).push(rec.file_path);
  }

  const counts = {};
  for (const rec of records) counts[rec.classification] = (counts[rec.classification] || 0) + 1;

  const huntsTruthCandidates = records.filter((r) => r.file_path.startsWith('HUNTS/data_truth/'));
  const localDataTruthFiles = new Set(records.filter((r) => !r.file_path.startsWith('HUNTS/')).map((r) => r.file_name.toLowerCase()));
  const likelyNeededNotImported = huntsTruthCandidates
    .filter((r) => ['normalized_truth_source', 'candidate_promotion_file'].includes(r.classification))
    .filter((r) => !localDataTruthFiles.has(r.file_name.toLowerCase()))
    .slice(0, 200)
    .map((r) => r.file_path);

  const staleFamilies = Array.from(familyGroups.entries())
    .filter(([, paths]) => paths.length > 1)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 200)
    .map(([family, paths]) => ({ family, count: paths.length, examples: paths.slice(0, 6) }));

  ensureDir(path.dirname(OUTPUT_CSV));

  const headers = [
    'file_path',
    'file_name',
    'extension',
    'size_bytes',
    'size_mb',
    'row_count_if_csv',
    'json_key_count_if_json',
    'modified_time_if_available',
    'classification',
    'canonical_role',
    'should_publish_public',
    'should_use_prediction_engine',
    'should_copy_to_pages_dist',
    'should_archive',
    'suspected_duplicate_of',
    'notes',
  ];

  const lines = [headers.map(csvEscape).join(',')];
  for (const rec of records) {
    lines.push(headers.map((h) => csvEscape(rec[h])).join(','));
  }
  fs.writeFileSync(OUTPUT_CSV, `${lines.join('\n')}\n`, 'utf8');

  const payload = {
    generated_at: new Date().toISOString(),
    root: ROOT,
    hunts_data_truth_root: fs.existsSync(HUNTS_DATA_TRUTH) ? HUNTS_DATA_TRUTH : null,
    row_count: records.length,
    classification_counts: counts,
    unknown_needs_review_count: counts.unknown_needs_review || 0,
    obsolete_fragment_count: counts.obsolete_fragment || 0,
    public_export_count: counts.public_export || 0,
    prediction_runtime_count: counts.prediction_runtime || 0,
    likely_needed_not_imported_from_hunts_data_truth: likelyNeededNotImported,
    duplicate_or_stale_families: staleFamilies,
    rows: records,
  };
  fs.writeFileSync(OUTPUT_JSON, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  console.log(`Wrote ${OUTPUT_CSV}`);
  console.log(`Wrote ${OUTPUT_JSON}`);
  console.log(`Manifest rows: ${records.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
