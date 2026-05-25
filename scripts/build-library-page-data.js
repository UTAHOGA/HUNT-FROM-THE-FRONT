const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

const INPUTS = {
  currentDatabase: 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv',
  currentCanonicalRaw: 'pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv',
  currentCanonicalProcessed: 'processed_data/hunt-master-canonical-2026-source-of-truth.csv',
  huntDatabaseComplete: 'processed_data/hunt_database_complete.csv',
  huntMasterEnriched: 'processed_data/hunt_master_enriched.csv',
  huntUnitReferenceLinked: 'processed_data/hunt_unit_reference_linked.csv',
  drawRealityEngine: 'processed_data/draw_reality_engine.csv',
  drawRealityEngineV2: 'processed_data/draw_reality_engine_v2.csv',
  drawRealityEnginePredictive: 'processed_data/draw_reality_engine_predictive_v2.csv',
  mlDrawPredictions: 'processed_data/ml_draw_predictions_v1.csv',
  pointLadderView: 'processed_data/point_ladder_view.csv',
  coverageReport: 'processed_data/draw_system_coverage_report.csv',
  predictiveCoverageReport: 'processed_data/predictive_coverage_report.csv',
  crosswalk: 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv',
  harvestMaster: 'processed_data/harvest_master.csv',
  harvestQualityAllYears: 'processed_data/harvest_quality_features_all_years_by_hunt_code.csv',
  harvestQuality2026: 'pipeline/RAW/hunt_unit_database/2026/csv/harvest_quality_features_by_hunt_code_2025_for_2026.csv',
  researchLibraryMaster: 'processed_data/research_library_master.csv',
};

const OUTPUTS = {
  libraryDir: 'processed_data/library',
  productionDir: 'processed_data/production',
  auditDir: 'processed_data/audits',
  hardDataExportDir: 'processed_data/hard_data_exports/library',
  publicHardCopyDataDir: 'public/hard-copy/data',
  publicHardCopyManifestDir: 'public/hard-copy/manifests',
  canonicalCurrent: 'processed_data/library/canonical_current_hunts_2026.csv',
  libraryCsv: 'processed_data/library/library_page_hunts.csv',
  libraryJson: 'processed_data/library/library_page_data.json',
  librarySummary: 'processed_data/library/library_page_summary.json',
  libraryManifestCsv: 'processed_data/library/hard_data_library_manifest.csv',
  libraryManifestJson: 'processed_data/library/hard_data_library_manifest.json',
  productionCsv: 'processed_data/production/library_page_hunts.csv',
  productionJson: 'processed_data/production/library_page_data.json',
  productionSummary: 'processed_data/production/library_page_summary.json',
  hardDataExportCsv: 'processed_data/hard_data_exports/library/library_page_hunts.csv',
  hardDataExportJson: 'processed_data/hard_data_exports/library/library_page_data.json',
  hardDataExportSummary: 'processed_data/hard_data_exports/library/library_page_summary.json',
  hardDataExportManifestCsv: 'processed_data/hard_data_exports/library/hard_data_manifest.csv',
  hardDataExportManifestJson: 'processed_data/hard_data_exports/library/hard_data_manifest.json',
  hardDataWebManifestJson: 'processed_data/hard_data_exports/hard_data_manifest.web.json',
  publicCsv: 'public/hard-copy/data/library_page_hunts.csv',
  publicJson: 'public/hard-copy/data/library_page_data.json',
  publicSummary: 'public/hard-copy/data/library_page_summary.json',
  publicManifestCsv: 'public/hard-copy/manifests/hard_data_manifest.csv',
  publicManifestJson: 'public/hard-copy/manifests/hard_data_manifest.json',
  buildReport: 'processed_data/audits/library_page_build_report.json',
  missingInputs: 'processed_data/audits/library_page_missing_inputs.csv',
};

function abs(rel) {
  return path.join(ROOT, rel);
}

function exists(rel) {
  return fs.existsSync(abs(rel));
}

function ensureDir(rel) {
  fs.mkdirSync(abs(rel), { recursive: true });
}

function ensureParent(rel) {
  ensureDir(path.dirname(rel));
}

function normalizeHeader(value) {
  return String(value || '')
    .replace(/^\uFEFF/, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  const src = String(text || '').replace(/^\uFEFF/, '');

  for (let i = 0; i < src.length; i += 1) {
    const c = src[i];
    const n = src[i + 1];
    if (c === '"' && inQuotes && n === '"') {
      field += '"';
      i += 1;
    } else if (c === '"') {
      inQuotes = !inQuotes;
    } else if (c === ',' && !inQuotes) {
      row.push(field);
      field = '';
    } else if ((c === '\n' || c === '\r') && !inQuotes) {
      if (c === '\r' && n === '\n') i += 1;
      row.push(field);
      if (row.some((v) => String(v).trim() !== '')) rows.push(row);
      row = [];
      field = '';
    } else {
      field += c;
    }
  }

  row.push(field);
  if (row.some((v) => String(v).trim() !== '')) rows.push(row);
  if (!rows.length) return [];

  const headers = rows[0].map(normalizeHeader);
  return rows.slice(1).map((values) => {
    const out = {};
    headers.forEach((header, index) => {
      out[header] = String(values[index] == null ? '' : values[index]).trim();
    });
    return out;
  });
}

function readCsv(rel) {
  if (!exists(rel)) return [];
  const rows = parseCsv(fs.readFileSync(abs(rel), 'utf8'));
  rows.forEach((row) => { row.__source_file = rel; });
  return rows;
}

function writeJson(rel, value) {
  ensureParent(rel);
  fs.writeFileSync(abs(rel), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeCsv(rel, rows) {
  ensureParent(rel);
  if (!rows.length) {
    fs.writeFileSync(abs(rel), '', 'utf8');
    return;
  }
  const headers = Array.from(rows.reduce((set, row) => {
    Object.keys(row).forEach((key) => set.add(key));
    return set;
  }, new Set()));
  const escape = (value) => {
    const s = value == null ? '' : String(value);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [headers.map(escape).join(',')].concat(
    rows.map((row) => headers.map((header) => escape(row[header])).join(',')),
  );
  fs.writeFileSync(abs(rel), `${lines.join('\n')}\n`, 'utf8');
}

function copyIfExists(fromRel, toRel) {
  if (!exists(fromRel)) return false;
  ensureParent(toRel);
  fs.copyFileSync(abs(fromRel), abs(toRel));
  return true;
}

function first(row, candidates) {
  for (const candidate of candidates) {
    const key = normalizeHeader(candidate);
    const value = row[key];
    if (value != null && String(value).trim() !== '') return String(value).trim();
  }
  return '';
}

function huntCode(row) {
  return first(row, [
    'hunt_code', 'huntcode', 'hunt_number', 'huntnumber', 'hunt no', 'hunt_no',
    'hunt', 'code', 'permit_number', 'permit_no', 'hunt id', 'hunt_id',
  ]).toUpperCase().replace(/\s+/g, '').replace(/[^A-Z0-9]/g, '');
}

function species(row) {
  return first(row, ['species', 'hunt_species', 'animal', 'big_game_species', 'category', 'hunt_category', 'hunt_type_species']);
}

function huntName(row) {
  return first(row, ['hunt_name', 'huntname', 'name', 'hunt_title', 'display_name', 'description', 'hunt_description', 'unit_name', 'hunt_unit']);
}

function unit(row) {
  return first(row, ['unit', 'unit_name', 'hunt_unit', 'management_unit', 'area', 'location', 'boundary_name', 'display_unit']);
}

function weapon(row) {
  return first(row, ['weapon', 'weapon_type', 'legal_weapon', 'method', 'season_type']);
}

function permits(row) {
  return first(row, ['permits', 'permit_count', 'permit_count_2026', 'permits_2026', 'total_permits', 'available', 'quota', 'allotment']);
}

function classification(row) {
  return first(row, ['classification', 'hunt_classification', 'draw_type', 'prediction_type', 'model_type', 'category', 'status', 'coverage_status', 'reason', 'reason_code', 'reason_codes']);
}

function probability(row) {
  return first(row, ['display_odds_pct', 'p_draw_mean', 'p_draw_p50', 'draw_probability', 'odds', 'probability', 'p50']);
}

function modelVersion(row) {
  return first(row, ['model_version', 'model', 'version', 'rule_version']);
}

function indexByCode(rows) {
  const index = new Map();
  for (const row of rows) {
    const code = huntCode(row);
    if (!code) continue;
    if (!index.has(code)) index.set(code, []);
    index.get(code).push(row);
  }
  return index;
}

function firstByCode(index, code) {
  const rows = index.get(code) || [];
  return rows[0] || {};
}

function countBy(rows, key) {
  return rows.reduce((counts, row) => {
    const value = String(row[key] || 'UNKNOWN').trim() || 'UNKNOWN';
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
}

function roleFor(rel) {
  if (rel.endsWith('DATABASE.csv')) return 'current official/canonical 2026 hunt database';
  if (rel.includes('hunt_master_canonical') || rel.includes('hunt-master-canonical')) return 'canonical current hunt source of truth';
  if (rel.includes('hunt_master_enriched')) return 'enriched hunt master';
  if (rel.includes('draw_reality_engine_predictive')) return 'primary prediction output';
  if (rel.includes('draw_reality_engine')) return 'draw reality engine output';
  if (rel.includes('ml_draw_predictions')) return 'ML prediction output';
  if (rel.includes('point_ladder')) return 'point ladder output';
  if (rel.includes('coverage')) return 'coverage/classification report';
  if (rel.includes('crosswalk')) return 'current-to-historical crosswalk';
  if (rel.includes('harvest')) return 'harvest evidence';
  if (rel.includes('research_library_master')) return 'research-page source';
  return 'supporting input';
}

function groupFor(rel) {
  if (rel.includes('library_page')) return 'exports';
  if (rel.includes('manifest')) return 'exports';
  if (rel.includes('DATABASE.csv') || rel.includes('hunt-master-canonical') || rel.includes('hunt_master_canonical')) return 'canonical';
  if (rel.includes('draw_reality') || rel.includes('point_ladder') || rel.includes('prediction')) return 'exports';
  if (rel.includes('coverage') || rel.includes('audit')) return 'pipeline_logs';
  if (rel.includes('crosswalk')) return 'raw_library';
  if (rel.includes('harvest')) return 'raw_library';
  if (rel.includes('research')) return 'raw_library';
  return 'exports';
}

function typeFor(rel) {
  const ext = path.extname(rel).replace('.', '').toLowerCase();
  return ext || 'file';
}

function titleFromRel(rel) {
  return path.basename(rel, path.extname(rel))
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

function webHref(rel) {
  return `./${rel.replace(/\\/g, '/')}`;
}

function inputStatus(name, rel) {
  const rows = exists(rel) ? readCsv(rel) : [];
  return {
    name,
    source_file: rel,
    role: roleFor(rel),
    exists: exists(rel) ? 'true' : 'false',
    row_count: rows.length,
  };
}

function pickCurrentSource() {
  return [
    INPUTS.currentDatabase,
    INPUTS.currentCanonicalProcessed,
    INPUTS.currentCanonicalRaw,
    INPUTS.huntDatabaseComplete,
    INPUTS.huntMasterEnriched,
  ].find((rel) => exists(rel)) || null;
}

function classifyState({ hasPrediction, hasCoverage, classText }) {
  const upper = String(classText || '').toUpperCase();
  const nonPredictiveTerms = [
    'HARVEST_OBJECTIVE', 'UNLIMITED', 'PRIVATE_LANDS', 'SPORTSMAN', 'CONSERVATION',
    'EXPO', 'AVAILABILITY', 'ALLOCATION', 'NONPREDICTIVE', 'NON_PREDICTIVE', 'OUT_OF_SCOPE',
  ];
  if (hasPrediction) return 'PREDICTION_ELIGIBLE_AND_MODELED';
  if (nonPredictiveTerms.some((term) => upper.includes(term))) return 'EXCLUDED_WITH_DOCUMENTED_NON_PREDICTIVE_REASON';
  if (hasCoverage) return 'CLASSIFIED_NEEDS_MODEL_OR_EXCLUSION_REVIEW';
  return 'MANUAL_REVIEW_REQUIRED';
}

function manifestItem(rel, subtitle, options = {}) {
  return {
    group: options.group || groupFor(rel),
    type: options.type || typeFor(rel),
    year: options.year || '2026',
    title: options.title || titleFromRel(rel),
    subtitle,
    href: webHref(rel),
    source: options.source || (rel.startsWith('processed_data/') ? 'processed_data' : 'pipeline'),
    scope: options.scope || 'runtime',
  };
}

function main() {
  for (const dir of [
    OUTPUTS.libraryDir,
    OUTPUTS.productionDir,
    OUTPUTS.auditDir,
    OUTPUTS.hardDataExportDir,
    OUTPUTS.publicHardCopyDataDir,
    OUTPUTS.publicHardCopyManifestDir,
  ]) ensureDir(dir);

  const inputs = Object.entries(INPUTS).map(([name, rel]) => inputStatus(name, rel));
  writeCsv(OUTPUTS.missingInputs, inputs.filter((input) => input.exists !== 'true'));

  const currentSource = pickCurrentSource();
  if (!currentSource) {
    throw new Error('No current 2026 hunt database source found. Expected pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv or canonical processed fallback.');
  }
  copyIfExists(currentSource, OUTPUTS.canonicalCurrent);

  const currentRows = readCsv(currentSource);
  const enrichedRows = readCsv(INPUTS.huntMasterEnriched);
  const referenceRows = readCsv(INPUTS.huntUnitReferenceLinked);
  const predictiveRows = readCsv(INPUTS.drawRealityEnginePredictive);
  const realityRows = readCsv(INPUTS.drawRealityEngine).concat(readCsv(INPUTS.drawRealityEngineV2));
  const mlRows = readCsv(INPUTS.mlDrawPredictions);
  const pointRows = readCsv(INPUTS.pointLadderView);
  const coverageRows = readCsv(INPUTS.coverageReport).concat(readCsv(INPUTS.predictiveCoverageReport));
  const crosswalkRows = readCsv(INPUTS.crosswalk);
  const harvestRows = readCsv(INPUTS.harvestMaster).concat(readCsv(INPUTS.harvestQualityAllYears)).concat(readCsv(INPUTS.harvestQuality2026));
  const researchRows = readCsv(INPUTS.researchLibraryMaster);

  const currentIndex = indexByCode(currentRows);
  const enrichedIndex = indexByCode(enrichedRows);
  const referenceIndex = indexByCode(referenceRows);
  const predictiveIndex = indexByCode(predictiveRows);
  const realityIndex = indexByCode(realityRows);
  const mlIndex = indexByCode(mlRows);
  const pointIndex = indexByCode(pointRows);
  const coverageIndex = indexByCode(coverageRows);
  const crosswalkIndex = indexByCode(crosswalkRows);
  const harvestIndex = indexByCode(harvestRows);

  const pageRows = [];

  for (const [code, rows] of currentIndex.entries()) {
    const cur = rows[0] || {};
    const enriched = firstByCode(enrichedIndex, code);
    const reference = firstByCode(referenceIndex, code);
    const predictive = firstByCode(predictiveIndex, code);
    const reality = firstByCode(realityIndex, code);
    const ml = firstByCode(mlIndex, code);
    const point = firstByCode(pointIndex, code);
    const coverage = firstByCode(coverageIndex, code);

    const hasPrediction = predictiveIndex.has(code) || realityIndex.has(code) || mlIndex.has(code);
    const hasPointLadder = pointIndex.has(code);
    const hasCrosswalk = crosswalkIndex.has(code);
    const hasHarvestEvidence = harvestIndex.has(code);
    const hasCoverage = coverageIndex.has(code);
    const classText = classification(coverage) || classification(enriched) || classification(predictive) || classification(reality) || '';
    const finalState = classifyState({ hasPrediction, hasCoverage, classText });
    const gateStatus = finalState === 'PREDICTION_ELIGIBLE_AND_MODELED' || finalState === 'EXCLUDED_WITH_DOCUMENTED_NON_PREDICTIVE_REASON'
      ? 'PASS'
      : 'BLOCK';

    pageRows.push({
      hunt_code: code,
      species: species(cur) || species(enriched) || species(reference),
      hunt_name: huntName(cur) || huntName(enriched) || huntName(reference),
      unit: unit(cur) || unit(enriched) || unit(reference),
      weapon: weapon(cur) || weapon(enriched) || weapon(reference),
      permits_2026: permits(cur) || permits(enriched) || permits(reference),
      classification: classText,
      modeled: hasPrediction ? 'true' : 'false',
      has_prediction: hasPrediction ? 'true' : 'false',
      has_point_ladder: hasPointLadder ? 'true' : 'false',
      has_crosswalk: hasCrosswalk ? 'true' : 'false',
      has_harvest_evidence: hasHarvestEvidence ? 'true' : 'false',
      has_coverage_record: hasCoverage ? 'true' : 'false',
      display_odds_or_probability: probability(predictive) || probability(reality) || probability(ml) || probability(point),
      model_version: modelVersion(predictive) || modelVersion(reality) || modelVersion(ml),
      final_state: finalState,
      gate_status: gateStatus,
      manual_review_required: gateStatus === 'BLOCK' ? 'true' : 'false',
      source_current_database: currentSource,
      source_prediction: hasPrediction ? INPUTS.drawRealityEnginePredictive : '',
      source_crosswalk: hasCrosswalk ? INPUTS.crosswalk : '',
      source_coverage: hasCoverage ? INPUTS.coverageReport : '',
    });
  }

  const summary = {
    generated_at: new Date().toISOString(),
    current_source_used: currentSource,
    counts: {
      total_current_hunts: pageRows.length,
      modeled_count: pageRows.filter((row) => row.has_prediction === 'true').length,
      excluded_non_predictive_count: pageRows.filter((row) => row.final_state === 'EXCLUDED_WITH_DOCUMENTED_NON_PREDICTIVE_REASON').length,
      manual_review_count: pageRows.filter((row) => row.manual_review_required === 'true').length,
      promotion_gate_pass_count: pageRows.filter((row) => row.gate_status === 'PASS').length,
      promotion_gate_block_count: pageRows.filter((row) => row.gate_status === 'BLOCK').length,
      research_library_rows_detected: researchRows.length,
    },
    species_counts: countBy(pageRows, 'species'),
    classification_counts: countBy(pageRows, 'classification'),
    final_state_counts: countBy(pageRows, 'final_state'),
    gate_status_counts: countBy(pageRows, 'gate_status'),
    inputs,
    recommendation: pageRows.some((row) => row.gate_status === 'BLOCK')
      ? 'REVIEW: hard-data library page package built, but blocked rows remain. Review manual_review_required=true rows before live promotion.'
      : 'PASS: hard-data library page package built with no blocked current hunt rows.',
  };

  const manifestRows = inputs.map((input) => ({
    ...input,
    used_as_current_source: input.source_file === currentSource ? 'true' : 'false',
  }));

  writeCsv(OUTPUTS.libraryCsv, pageRows);
  writeJson(OUTPUTS.libraryJson, pageRows);
  writeJson(OUTPUTS.librarySummary, summary);
  writeCsv(OUTPUTS.libraryManifestCsv, manifestRows);
  writeJson(OUTPUTS.libraryManifestJson, summary);

  writeCsv(OUTPUTS.productionCsv, pageRows);
  writeJson(OUTPUTS.productionJson, pageRows);
  writeJson(OUTPUTS.productionSummary, summary);

  writeCsv(OUTPUTS.hardDataExportCsv, pageRows);
  writeJson(OUTPUTS.hardDataExportJson, pageRows);
  writeJson(OUTPUTS.hardDataExportSummary, summary);
  writeCsv(OUTPUTS.hardDataExportManifestCsv, manifestRows);
  writeJson(OUTPUTS.hardDataExportManifestJson, summary);

  writeCsv(OUTPUTS.publicCsv, pageRows);
  writeJson(OUTPUTS.publicJson, pageRows);
  writeJson(OUTPUTS.publicSummary, summary);
  writeCsv(OUTPUTS.publicManifestCsv, manifestRows);
  writeJson(OUTPUTS.publicManifestJson, summary);

  const webManifest = [
    manifestItem(OUTPUTS.hardDataExportCsv, 'Page-ready hard-data hunt library records as CSV.', { group: 'exports', title: 'Hard Data Library Page Records CSV' }),
    manifestItem(OUTPUTS.hardDataExportJson, 'Page-ready hard-data hunt library records as JSON.', { group: 'exports', title: 'Hard Data Library Page Records JSON' }),
    manifestItem(OUTPUTS.hardDataExportSummary, 'Build summary for modeled, excluded, manual-review, and gate status counts.', { group: 'exports', title: 'Hard Data Library Page Summary' }),
    manifestItem(OUTPUTS.hardDataExportManifestCsv, 'CSV manifest of source files used to build the hard-data library page package.', { group: 'exports', title: 'Hard Data Library Source Manifest CSV', scope: 'audit' }),
    manifestItem(OUTPUTS.hardDataExportManifestJson, 'JSON manifest and build status for the hard-data library page package.', { group: 'exports', title: 'Hard Data Library Source Manifest JSON', scope: 'audit' }),
  ];

  for (const input of inputs.filter((item) => item.exists === 'true')) {
    webManifest.push(manifestItem(input.source_file, `${input.role}; ${input.row_count} detected rows.`, {
      group: groupFor(input.source_file),
      title: titleFromRel(input.source_file),
      scope: input.role.includes('coverage') || input.role.includes('crosswalk') ? 'audit' : 'runtime',
    }));
  }

  const uniqueManifest = Array.from(new Map(webManifest.map((item) => [item.href, item])).values());
  writeJson(OUTPUTS.hardDataWebManifestJson, uniqueManifest);

  writeJson(OUTPUTS.buildReport, summary);

  console.log('\nHard-data library page build complete');
  console.log('====================================');
  console.log(`Current source used: ${currentSource}`);
  console.log(`Total current hunts: ${summary.counts.total_current_hunts}`);
  console.log(`Modeled:             ${summary.counts.modeled_count}`);
  console.log(`Excluded:            ${summary.counts.excluded_non_predictive_count}`);
  console.log(`Manual review:       ${summary.counts.manual_review_count}`);
  console.log(`Gate PASS:           ${summary.counts.promotion_gate_pass_count}`);
  console.log(`Gate BLOCK:          ${summary.counts.promotion_gate_block_count}`);
  console.log('\nPrimary outputs:');
  console.log(`- ${OUTPUTS.libraryCsv}`);
  console.log(`- ${OUTPUTS.librarySummary}`);
  console.log(`- ${OUTPUTS.hardDataExportJson}`);
  console.log(`- ${OUTPUTS.hardDataWebManifestJson}`);
  console.log(`\n${summary.recommendation}`);
}

try {
  main();
} catch (error) {
  console.error('Failed to build hard-data library page package.');
  console.error(error);
  process.exit(1);
}
