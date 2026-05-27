const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const HUNTS_ROOT = path.resolve(ROOT, '..', 'HUNTS');
const OUT_DIR = path.join(ROOT, 'data_truth', 'comparison_outputs', 'database_fragment_audit');
const REPORT_PATH = path.join(ROOT, 'processed_data', 'database_fragment_audit.md');

const SCAN_ROOTS = [
  { repo: 'HUNT-BUILDER', label: 'processed_data', root: path.join(ROOT, 'processed_data') },
  { repo: 'HUNT-BUILDER', label: 'pipeline_RAW', root: path.join(ROOT, 'pipeline', 'RAW') },
  { repo: 'HUNT-BUILDER', label: 'data_truth_local_fragments', root: path.join(ROOT, 'data_truth') },
  { repo: 'HUNTS', label: 'data_truth_external_candidates', root: path.join(HUNTS_ROOT, 'data_truth') },
];

const OFFICIAL_CURRENT = normalizePath('pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv');
const KNOWN_RUNTIME = new Set([
  'processed_data/hunt_master_enriched.csv',
  'processed_data/draw_reality_engine.csv',
  'processed_data/draw_reality_engine_v2.csv',
  'processed_data/draw_reality_engine_predictive_v2.csv',
  'processed_data/ml_draw_predictions_v1.csv',
  'processed_data/point_ladder_view.csv',
  'processed_data/harvest_master.csv',
  'processed_data/harvest_quality_features_all_years_by_hunt_code.csv',
  'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv',
  'processed_data/hunt_unit_reference_linked.csv',
  'processed_data/draw_system_coverage_report.csv',
  'processed_data/predictive_coverage_report.csv',
].map(normalizePath));

const PUBLIC_EXPORT_HINTS = [
  'processed_data/library/',
  'processed_data/hard_data_exports/library/',
  'library_page_hunts',
  'library_page_data',
  'library_page_summary',
  'hard_data_manifest.web',
].map(normalizePath);

const WANTED_EXTENSIONS = new Set([
  '.csv',
  '.json',
  '.md',
  '.pdf',
  '.xlsx',
  '.xls',
  '.sqlite',
  '.db',
  '.geojson',
  '.zip',
]);

const DOMAIN_PATTERN = /(database|draw|odds|permit|allot|allocation|harvest|crosswalk|hunt[_ -]?code|hunt[_ -]?master|point[_ -]?ladder|prediction|coverage|conservation|expo|rac|boundary|library_page|hard_data_manifest)/i;

function normalizePath(value) {
  return String(value || '').replace(/\\/g, '/').replace(/^\.\//, '');
}

function relativeFromRepo(absPath, repoRoot) {
  return normalizePath(path.relative(repoRoot, absPath));
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function esc(value) {
  const text = value == null ? '' : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(filePath, rows) {
  ensureDir(path.dirname(filePath));
  const headers = [
    'review_bucket',
    'repo',
    'scan_root',
    'classification',
    'domain',
    'recommended_action',
    'reason',
    'relative_path',
    'absolute_path',
    'file_name',
    'extension',
    'size_bytes',
    'size_mb',
    'row_count',
    'header_columns',
    'has_hunt_code',
    'has_current_hunt_code',
    'has_historical_hunt_code',
    'has_boundary_id',
    'modified_utc',
  ];
  const lines = [headers.map(esc).join(',')];
  for (const row of rows) lines.push(headers.map((header) => esc(row[header])).join(','));
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

function writeJson(filePath, value) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function reviewBucket(row) {
  if (row.classification === 'official_current_source') return 'canonical_source';
  if (row.classification === 'runtime_engine_output') return 'runtime_keep';
  if (row.classification === 'page_public_export') return 'public_export_keep';
  if (row.repo === 'HUNTS' && ['normalized_truth_source', 'candidate_promotion_file'].includes(row.classification)) return 'external_import_review';
  if (row.classification === 'candidate_promotion_file') return 'local_candidate_review';
  if (row.classification === 'normalized_truth_source') return 'local_truth_keep';
  if (row.classification === 'obsolete_fragment' && row.recommended_action === 'ignore_or_delete_after_owner_approval') return 'delete_or_ignore_candidate';
  if (row.classification === 'obsolete_fragment') return 'archive_only';
  if (row.classification === 'audit_validation_report') return 'audit_archive';
  return 'manual_review';
}

function listFiles(root) {
  const out = [];
  if (!fs.existsSync(root)) return out;
  const excludedOutputDir = normalizePath(OUT_DIR);
  const stack = [root];
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
        if (['.git', 'node_modules', '.wrangler', 'pages-dist'].includes(entry.name)) continue;
        if (normalizePath(abs).startsWith(excludedOutputDir)) continue;
        stack.push(abs);
      } else {
        out.push(abs);
      }
    }
  }
  return out;
}

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

async function csvProfile(absPath, maxCountBytes = 125 * 1024 * 1024) {
  const stat = fs.statSync(absPath);
  const profile = { row_count: '', header_columns: '' };
  let headers = [];
  let count = 0;
  try {
    const rl = readline.createInterface({ input: fs.createReadStream(absPath, { encoding: 'utf8' }), crlfDelay: Infinity });
    for await (const line of rl) {
      if (!String(line || '').trim()) continue;
      if (!headers.length) {
        headers = parseCsvLine(line).map(normalizeHeader);
        profile.header_columns = headers.join('|');
        if (stat.size > maxCountBytes) {
          profile.row_count = 'not_counted_large_file';
          rl.close();
          break;
        }
        continue;
      }
      count += 1;
    }
    if (profile.row_count !== 'not_counted_large_file') profile.row_count = String(count);
  } catch (error) {
    profile.row_count = `read_error:${error.message}`;
  }
  return profile;
}

function domainFor(rel) {
  const lower = rel.toLowerCase();
  if (lower.includes('crosswalk')) return 'crosswalk';
  if (lower.includes('harvest')) return 'harvest';
  if (lower.includes('draw') || lower.includes('odds') || lower.includes('point_ladder')) return 'draw';
  if (lower.includes('permit') || lower.includes('allot') || lower.includes('allocation') || lower.includes('conservation') || lower.includes('expo') || lower.includes('rac')) return 'permit';
  if (lower.includes('boundary') || lower.endsWith('.geojson')) return 'crosswalk';
  if (lower.includes('library_page') || lower.includes('hard_data_manifest')) return 'public_library';
  return 'unknown';
}

function classify({ repo, rel, fileName }) {
  const lower = rel.toLowerCase();
  const normalizedRel = normalizePath(rel);
  if (repo === 'HUNT-BUILDER' && normalizedRel === OFFICIAL_CURRENT) {
    return ['official_current_source', 'keep_canonical', 'current official 2026 DWR Hunt Planner source database'];
  }
  if (/\s\(\d+\)(?=\.[^.]+$)/.test(fileName)) {
    return ['obsolete_fragment', 'ignore_or_delete_after_owner_approval', 'duplicate Windows copy suffix indicates fragment, not canonical truth'];
  }
  if (repo === 'HUNT-BUILDER' && KNOWN_RUNTIME.has(normalizedRel)) {
    return ['runtime_engine_output', 'keep_runtime_do_not_public_dump', 'known runtime or database-support file used by engine/library builds'];
  }
  if (repo === 'HUNT-BUILDER' && PUBLIC_EXPORT_HINTS.some((hint) => normalizedRel.includes(hint))) {
    return ['page_public_export', 'keep_public_or_generated', 'generated public Hunt Library export'];
  }
  if (lower.includes('/validation/') || lower.includes('_validation') || lower.includes('_audit') || lower.includes('_summary.json') || lower.includes('_report.json') || lower.includes('_report.md')) {
    return ['audit_validation_report', 'keep_as_audit_or_archive', 'validation, audit, or report artifact'];
  }
  if (lower.includes('candidate') || lower.includes('promotion') || lower.includes('_vs_database') || lower.includes('compare') || lower.includes('comparison') || lower.includes('reconciliation') || lower.includes('lock_2026') || lower.includes('canonical')) {
    return ['candidate_promotion_file', 'review_for_possible_import_or_rollup', 'candidate/reconciliation evidence; do not overwrite canonical cells directly'];
  }
  if (lower.includes('/normalized/') || lower.includes('\\normalized\\')) {
    return ['normalized_truth_source', 'keep_truth_source', 'normalized truth-layer source candidate'];
  }
  if (lower.includes('/raw_packages/') || lower.includes('/raw_sources/') || lower.endsWith('.zip')) {
    return ['obsolete_fragment', 'archive_only_after_rollup_review', 'raw package or bundle copy should not feed runtime directly'];
  }
  return ['unknown_needs_review', 'manual_review', 'matched domain terms but no stronger classification rule'];
}

function addCount(map, key) {
  map[key] = (map[key] || 0) + 1;
}

async function main() {
  const rows = [];
  const roots = [];

  for (const scanRoot of SCAN_ROOTS) {
    const rootExists = fs.existsSync(scanRoot.root);
    roots.push({ ...scanRoot, exists: rootExists });
    if (!rootExists) continue;
    for (const absPath of listFiles(scanRoot.root)) {
      const ext = path.extname(absPath).toLowerCase();
      const fileName = path.basename(absPath);
      const rel = scanRoot.repo === 'HUNT-BUILDER'
        ? relativeFromRepo(absPath, ROOT)
        : relativeFromRepo(absPath, HUNTS_ROOT);
      if (!WANTED_EXTENSIONS.has(ext)) continue;
      if (!DOMAIN_PATTERN.test(rel) && normalizePath(rel) !== OFFICIAL_CURRENT) continue;

      const stat = fs.statSync(absPath);
      const [classification, recommended_action, reason] = classify({ repo: scanRoot.repo, rel, fileName });
      let profile = { row_count: '', header_columns: '' };
      if (ext === '.csv') profile = await csvProfile(absPath);
      const headers = profile.header_columns.split('|').filter(Boolean);
      rows.push({
        repo: scanRoot.repo,
        scan_root: scanRoot.label,
        classification,
        domain: domainFor(rel),
        recommended_action,
        reason,
        relative_path: rel,
        absolute_path: absPath,
        file_name: fileName,
        extension: ext.replace(/^\./, ''),
        size_bytes: stat.size,
        size_mb: (stat.size / 1024 / 1024).toFixed(3),
        row_count: profile.row_count,
        header_columns: profile.header_columns,
        has_hunt_code: headers.includes('hunt_code') ? 'true' : 'false',
        has_current_hunt_code: headers.includes('current_hunt_code') ? 'true' : 'false',
        has_historical_hunt_code: headers.includes('historical_hunt_code') ? 'true' : 'false',
        has_boundary_id: headers.includes('boundary_id') ? 'true' : 'false',
        modified_utc: stat.mtime.toISOString(),
      });
    }
  }

  rows.sort((a, b) => `${a.repo}/${a.classification}/${a.relative_path}`.localeCompare(`${b.repo}/${b.classification}/${b.relative_path}`));

  const classificationCounts = {};
  const domainCounts = {};
  const repoCounts = {};
  const recommendedActionCounts = {};
  for (const row of rows) {
    addCount(classificationCounts, row.classification);
    addCount(domainCounts, row.domain);
    addCount(repoCounts, row.repo);
    addCount(recommendedActionCounts, row.recommended_action);
  }

  const currentCrosswalkRows = rows.filter((row) => row.relative_path.replace(/\\/g, '/') === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv');
  const huntsImportCandidates = rows.filter((row) => row.repo === 'HUNTS' && ['normalized_truth_source', 'candidate_promotion_file'].includes(row.classification));
  const duplicateFragments = rows.filter((row) => row.classification === 'obsolete_fragment' && /\s\(\d+\)(?=\.[^.]+$)/.test(row.file_name));
  const recommendationRows = rows.map((row) => ({ review_bucket: reviewBucket(row), ...row }))
    .sort((a, b) => `${a.review_bucket}/${a.repo}/${a.relative_path}`.localeCompare(`${b.review_bucket}/${b.repo}/${b.relative_path}`));

  const reviewBucketCounts = {};
  for (const row of recommendationRows) addCount(reviewBucketCounts, row.review_bucket);

  const summary = {
    generated_at: new Date().toISOString(),
    active_repo: ROOT,
    external_truth_repo: HUNTS_ROOT,
    scanned_roots: roots.map((root) => ({ repo: root.repo, label: root.label, root: root.root, exists: root.exists })),
    total_files: rows.length,
    classification_counts: classificationCounts,
    domain_counts: domainCounts,
    repo_counts: repoCounts,
    recommended_action_counts: recommendedActionCounts,
    review_bucket_counts: reviewBucketCounts,
    duplicate_copy_suffix_fragments: duplicateFragments.length,
    hunts_import_candidate_files_for_review: huntsImportCandidates.length,
    crosswalk_profile: currentCrosswalkRows[0] || null,
    notes: [
      'DATABASE.csv remains the official current 2026 source.',
      'Files classified as candidate_promotion_file are evidence only until reviewed against DATABASE.csv.',
      'Files with a Windows copy suffix such as " (2)" are classified as obsolete_fragment and were not deleted.',
      'HUNTS data_truth files were inventoried for import review, not copied into HUNT-BUILDER.',
    ],
  };

  const manifest = path.join(OUT_DIR, 'database_fragment_manifest.csv');
  const recommendations = path.join(OUT_DIR, 'database_fragment_recommendations.csv');
  const summaryPath = path.join(OUT_DIR, 'database_fragment_summary.json');
  writeCsv(manifest, rows);
  writeCsv(recommendations, recommendationRows);
  writeJson(summaryPath, summary);

  const firstList = (items, bucket, limit = 12) => items.filter((item) => item.review_bucket === bucket).slice(0, limit);
  const mdList = (items) => (items.length ? items.map((item) => `- \`${item.relative_path}\` (${item.classification})`).join('\n') : '- None found.');

  const markdown = [
    '# Database Fragment Audit',
    '',
    `Generated UTC: ${summary.generated_at}`,
    '',
    '## Scope',
    '',
    '- Active repo: `C:\\Users\\tyler\\Desktop\\GitHub\\HUNT-BUILDER`',
    '- External candidate repo scanned read-only: `C:\\Users\\tyler\\Desktop\\GitHub\\HUNTS\\data_truth`',
    '- Canonical current source: `pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv`',
    '- No canonical runtime files were overwritten by this audit.',
    '',
    '## Counts',
    '',
    `- Total inventoried files: ${summary.total_files}`,
    `- Duplicate copy-suffix fragments: ${summary.duplicate_copy_suffix_fragments}`,
    `- HUNTS import candidates for review: ${summary.hunts_import_candidate_files_for_review}`,
    '',
    '## Classification Counts',
    '',
    ...Object.entries(classificationCounts).sort().map(([key, value]) => `- ${key}: ${value}`),
    '',
    '## Recommended Actions',
    '',
    ...Object.entries(recommendedActionCounts).sort().map(([key, value]) => `- ${key}: ${value}`),
    '',
    '## Review Buckets',
    '',
    ...Object.entries(reviewBucketCounts).sort().map(([key, value]) => `- ${key}: ${value}`),
    '',
    '## Canonical Source Files',
    '',
    mdList(firstList(recommendationRows, 'canonical_source', 20)),
    '',
    '## Runtime Files To Keep Internal',
    '',
    mdList(firstList(recommendationRows, 'runtime_keep', 20)),
    '',
    '## External HUNTS Files For Import Review',
    '',
    mdList(firstList(recommendationRows, 'external_import_review', 20)),
    '',
    '## Delete Or Ignore Candidates',
    '',
    mdList(firstList(recommendationRows, 'delete_or_ignore_candidate', 20)),
    '',
    '## Archive-Only Candidates',
    '',
    mdList(firstList(recommendationRows, 'archive_only', 20)),
    '',
    '## Crosswalk Profile',
    '',
    currentCrosswalkRows[0]
      ? `- ${currentCrosswalkRows[0].relative_path}: ${currentCrosswalkRows[0].row_count} rows; has current_hunt_code=${currentCrosswalkRows[0].has_current_hunt_code}; has historical_hunt_code=${currentCrosswalkRows[0].has_historical_hunt_code}`
      : '- Crosswalk file was not found in the manifest.',
    '',
    '## Outputs',
    '',
    '- `data_truth/comparison_outputs/database_fragment_audit/database_fragment_manifest.csv`',
    '- `data_truth/comparison_outputs/database_fragment_audit/database_fragment_recommendations.csv`',
    '- `data_truth/comparison_outputs/database_fragment_audit/database_fragment_summary.json`',
  ].join('\n');
  ensureDir(path.dirname(REPORT_PATH));
  fs.writeFileSync(REPORT_PATH, `${markdown}\n`, 'utf8');

  console.log(`Fragment manifest rows: ${rows.length}`);
  console.log(`Duplicate copy-suffix fragments: ${duplicateFragments.length}`);
  console.log(`HUNTS import candidates for review: ${huntsImportCandidates.length}`);
  console.log(`Wrote ${manifest}`);
  console.log(`Wrote ${recommendations}`);
  console.log(`Wrote ${summaryPath}`);
  console.log(`Wrote ${REPORT_PATH}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
