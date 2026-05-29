#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = process.cwd();
const SEARCH_DIRS = [
  'processed_data',
  'processed_data/harvest_age_crosswalk',
  'processed_data/hard_data_exports',
  'data_model/harvest_quality',
  'data_truth/harvest_results_truth',
  'pipeline/RAW/hunt_unit_database',
  'local_only',
  '_exports',
  '.'
];

const OUT_ALL = path.join(ROOT, 'processed_data', 'harvest_age_features_by_hunt_code_all_years.csv');
const OUT_LATEST = path.join(ROOT, 'processed_data', 'harvest_age_features_by_hunt_code_latest.csv');
const OUT_REVIEW = path.join(ROOT, 'processed_data', 'harvest_age_features_by_hunt_code_review.csv');
const OUT_AUDIT_JSON = path.join(ROOT, 'processed_data', 'harvest_age_features_merge_audit.json');
const OUT_AUDIT_CSV = path.join(ROOT, 'processed_data', 'harvest_age_features_merge_audit.csv');

const DATABASE_CSV = path.join(ROOT, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv', 'DATABASE.csv');
const CROSSWALK_CSV = path.join(ROOT, 'processed_data', 'current_to_historical_hunt_code_crosswalk_2026.csv');

const FILE_PATTERNS = [
  /average_harvest_age_.*_features_by_hunt_code\.csv$/i,
  /average_harvest_age_.*_crosswalk_to_hunt_codes\.csv$/i,
  /black_bear_.*_age_features_by_hunt_code\.csv$/i,
  /cougar_.*_age_features.*\.csv$/i,
  /mountain_goat_.*_age_features_by_hunt_code\.csv$/i,
  /elk_.*_age_features_by_hunt_code\.csv$/i,
  /combined_average_harvest_age_.*_features_by_hunt_code\.csv$/i,
  /harvest_age_features_by_hunt_code.*\.csv$/i,
  /average_age.*\.csv$/i,
  /age_.*crosswalk.*\.csv$/i,
  /harvest_quality_features_.*age.*\.csv$/i,
  /harvest_quality_features_by_hunt_code_\d{4}_for_\d{4}\.csv$/i
];

const DAYS_FIELD_PATTERNS = [
  /average[_\s]?days/i,
  /mean[_\s]?days/i,
  /days[_\s]?hunted/i,
  /hunter[_\s]?days/i,
  /pursuit[_\s]?days/i
];

const AGE_FIELD_PATTERNS = [
  /average[_\s]?harvest[_\s]?age/i,
  /^average[_\s]?age$/i,
  /avg[_\s]?age/i,
  /mean[_\s]?age/i,
  /age[_\s]?average/i,
  /^averageage/i,
  /^meanage/i,
  /^avgage/i,
  /average_age_\d{4}/i,
  /avg_age_\d{4}/i
];

const PERCENT_5_PATTERNS = [
  /percent[_\s]?5\+?/i,
  /pct[_\s]?5\+?/i,
  /five[_\s-]?plus/i,
  /mature/i
];

const ADULT_MALE_PATTERNS = [/percent[_\s]?adult[_\s]?male/i, /adult[_\s]?male/i];
const ADULT_FEMALE_PATTERNS = [/percent[_\s]?adult[_\s]?female/i, /adult[_\s]?female/i];

const TROPHY_ELIGIBLE_SPECIES = [
  'elk',
  'deer',
  'mule deer',
  'pronghorn',
  'moose',
  'mountain goat',
  'bighorn sheep',
  'desert bighorn sheep',
  'rocky mountain bighorn sheep',
  'bison',
  'black bear',
  'cougar'
];

const CANONICAL_COLUMNS = [
  'hunt_code',
  'historical_hunt_code',
  'current_hunt_code',
  'hunt_name',
  'species',
  'reported_hunt_year',
  'model_target_year',
  'unit',
  'unit_name',
  'boundary_id',
  'boundary_name',
  'average_harvest_age',
  'age_data_available',
  'percent_5plus',
  'percent_mature_or_5_plus',
  'percent_adult_male',
  'percent_adult_female',
  'age_metric_type',
  'age_source_scope',
  'source_file',
  'source_page',
  'source_table_title',
  'source_row_key',
  'source_package_file',
  'source_package_path',
  'crosswalk_method',
  'crosswalk_confidence',
  'crosswalk_score',
  'review_status',
  'review_reason',
  'do_not_use_for_permit_quota',
  'do_not_use_directly_for_p_draw',
  'quality_score_eligible',
  'trophy_age_score_eligible',
  'notes',
  'database_code_present',
  'database_hunt_name',
  'database_species',
  'database_match_notes'
];

function norm(v) {
  return String(v ?? '').trim();
}

function cleanToken(v) {
  return norm(v).replace(/^"+|"+$/g, '').trim();
}

function hasMeaningful(v) {
  const s = cleanToken(v).toLowerCase();
  if (!s) return false;
  if (['unknown', 'na', 'n/a', 'null', 'none', 'not available', 'not_loaded', 'not loaded'].includes(s)) return false;
  return true;
}

function normKey(v) {
  return norm(v).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function normCode(v) {
  return norm(v).toUpperCase().replace(/\s+/g, '').replace(/[^A-Z0-9]/g, '');
}

function isLikelyHuntCode(v) {
  return /^[A-Z]{1,3}\d{3,5}$/.test(v);
}

function toBoolStr(v) {
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  const s = norm(v).toLowerCase();
  if (['true', 'yes', '1', 'y'].includes(s)) return 'true';
  if (['false', 'no', '0', 'n'].includes(s)) return 'false';
  return '';
}

function extractNumber(v) {
  const s = norm(v);
  if (!s) return null;
  const m = s.replace(/,/g, '').match(/-?\d+(?:\.\d+)?/);
  if (!m) return null;
  const n = Number(m[0]);
  if (!Number.isFinite(n)) return null;
  return n;
}

function detectYears(filePath, row) {
  const out = { reported_hunt_year: '', model_target_year: '' };
  const candidatesReported = [
    row.reported_hunt_year,
    row.hunt_year,
    row.harvest_year,
    row.year,
    row.season_year
  ].map(extractNumber).filter((x) => x && x >= 1900 && x <= 2100);
  const candidatesTarget = [
    row.model_target_year,
    row.target_year,
    row.prediction_year,
    row.draw_year,
    row.publish_year
  ].map(extractNumber).filter((x) => x && x >= 1900 && x <= 2100);

  if (candidatesReported.length) out.reported_hunt_year = String(candidatesReported[0]);
  if (candidatesTarget.length) out.model_target_year = String(candidatesTarget[0]);

  const rel = filePath.replace(/\\/g, '/');
  const pair = rel.match(/(20\d{2})_for_(20\d{2})/i) || rel.match(/(20\d{2})\s*for\s*(20\d{2})/i);
  if (pair) {
    if (!out.reported_hunt_year) out.reported_hunt_year = pair[1];
    if (!out.model_target_year) out.model_target_year = pair[2];
  }

  if (!out.reported_hunt_year && out.model_target_year) {
    out.reported_hunt_year = String(Number(out.model_target_year) - 1);
  }
  if (!out.model_target_year && out.reported_hunt_year) {
    out.model_target_year = String(Number(out.reported_hunt_year) + 1);
  }

  return out;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];

    if (ch === '"') {
      if (inQuotes && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (!inQuotes && ch === ',') {
      row.push(field);
      field = '';
      continue;
    }

    if (!inQuotes && (ch === '\n' || ch === '\r')) {
      if (ch === '\r' && text[i + 1] === '\n') i += 1;
      row.push(field);
      field = '';
      if (row.length > 1 || (row.length === 1 && norm(row[0]) !== '')) rows.push(row);
      row = [];
      continue;
    }

    field += ch;
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  if (!rows.length) return { headers: [], records: [] };

  const headers = rows[0].map((h) => norm(h));
  const records = [];
  for (let i = 1; i < rows.length; i++) {
    const vals = rows[i];
    const rec = {};
    for (let j = 0; j < headers.length; j++) rec[headers[j]] = vals[j] ?? '';
    records.push(rec);
  }
  return { headers, records };
}

function csvEscape(v) {
  const s = String(v ?? '');
  if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function writeCsv(filePath, rows, columns) {
  const lines = [columns.map(csvEscape).join(',')];
  for (const row of rows) lines.push(columns.map((c) => csvEscape(row[c] ?? '')).join(','));
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
}

function getAllCsvFiles() {
  const seen = new Set();
  const out = [];

  function walk(abs) {
    if (!fs.existsSync(abs)) return;
    const stat = fs.statSync(abs);
    if (!stat.isDirectory()) return;
    const ents = fs.readdirSync(abs, { withFileTypes: true });
    for (const ent of ents) {
      const p = path.join(abs, ent.name);
      if (ent.isDirectory()) {
        if (['node_modules', '.git', '.wrangler', 'pages-dist'].includes(ent.name)) continue;
        walk(p);
      } else if (ent.isFile() && ent.name.toLowerCase().endsWith('.csv')) {
        const rel = path.relative(ROOT, p).replace(/\\/g, '/');
        if (!seen.has(rel)) {
          seen.add(rel);
          out.push({ abs: p, rel, name: ent.name });
        }
      }
    }
  }

  for (const dir of SEARCH_DIRS) walk(path.join(ROOT, dir));
  return out;
}

function selectCandidate(file, headerLine) {
  const name = file.name;
  const relLower = file.rel.toLowerCase();
  const headerLower = (headerLine || '').toLowerCase();

  if (FILE_PATTERNS.some((rx) => rx.test(name))) return { use: true, reason: 'filename_pattern' };

  const hasAgeLikeHeader =
    /average[_\s]?harvest[_\s]?age|average[_\s]?age|avg[_\s]?age|mean[_\s]?age|percent[_\s]?5\+?|pct[_\s]?5\+?|adult[_\s]?male|adult[_\s]?female/.test(headerLower);
  const inRelevantPath = /harvest|age|cougar|bear|goat|elk|deer|moose|pronghorn|bison|sheep/.test(relLower);

  if (hasAgeLikeHeader && inRelevantPath) return { use: true, reason: 'header_age_terms' };

  return { use: false, reason: 'no_pattern_or_age_header' };
}

function pickColumn(headersNormMap, patternList) {
  for (const [raw, key] of headersNormMap.entries()) {
    if (patternList.some((rx) => rx.test(key) || rx.test(raw.toLowerCase()))) return raw;
  }
  return '';
}

function loadDatabase() {
  const result = {
    found: false,
    map: new Map(),
    count: 0,
    bySpeciesName: new Map(),
    byNameOnly: new Map()
  };
  if (!fs.existsSync(DATABASE_CSV)) return result;
  const text = fs.readFileSync(DATABASE_CSV, 'utf8');
  const { records } = parseCsv(text);
  const map = new Map();
  const bySpeciesName = new Map();
  const byNameOnly = new Map();

  function pushIndex(index, key, row) {
    if (!key) return;
    const arr = index.get(key) || [];
    arr.push(row);
    index.set(key, arr);
  }

  function normName(v) {
    return norm(v).toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  for (const r of records) {
    const code = normCode(r.hunt_code);
    if (!code || !isLikelyHuntCode(code)) continue;
    const dbRow = {
      hunt_code: code,
      hunt_name: norm(r.hunt_name),
      species: norm(r.species),
      boundary_id: norm(r.boundary_id),
      boundary_name: norm(r.boundary_name)
    };
    map.set(code, dbRow);
    pushIndex(bySpeciesName, `${normName(dbRow.species)}||${normName(dbRow.hunt_name)}`, dbRow);
    pushIndex(byNameOnly, normName(dbRow.hunt_name), dbRow);
  }
  result.found = true;
  result.map = map;
  result.count = map.size;
  result.bySpeciesName = bySpeciesName;
  result.byNameOnly = byNameOnly;
  return result;
}

function loadCrosswalk() {
  const result = { found: false, rows: 0, histToCurrent: new Map(), matchCount: 0 };
  if (!fs.existsSync(CROSSWALK_CSV)) return result;
  const text = fs.readFileSync(CROSSWALK_CSV, 'utf8');
  const { records } = parseCsv(text);
  const histMap = new Map();
  for (const r of records) {
    const cur = normCode(r.current_hunt_code || r.current_code || r.current_hunt_number);
    const hist = normCode(r.historical_hunt_code);
    if (cur && hist && isLikelyHuntCode(cur) && isLikelyHuntCode(hist)) {
      if (!histMap.has(hist)) histMap.set(hist, cur);
    }
  }
  result.found = true;
  result.rows = records.length;
  result.histToCurrent = histMap;
  result.matchCount = histMap.size;
  return result;
}

function parseConfidence(v, scope) {
  const s = norm(v).toLowerCase();
  if (!s) {
    if (scope === 'hunt_code_direct') return 'medium';
    if (scope === 'unit_level_repeated_to_hunt_code') return 'unit_level_medium';
    if (scope === 'unit_level_needs_hunt_code_crosswalk') return 'low_review';
    return 'low_review';
  }
  if (['high', 'medium', 'low'].includes(s)) return s;
  if (s.includes('unit_level_high')) return 'unit_level_high';
  if (s.includes('unit_level_medium')) return 'unit_level_medium';
  if (s.includes('unit') && s.includes('high')) return 'unit_level_high';
  if (s.includes('unit') && s.includes('medium')) return 'unit_level_medium';
  if (s.includes('exact')) return 'high';
  if (s.includes('promoted')) return 'high';
  if (s.includes('low')) return 'low_review';
  return 'medium';
}

function dedupeRows(rows) {
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    const hash = crypto
      .createHash('sha1')
      .update(CANONICAL_COLUMNS.map((c) => String(r[c] ?? '')).join('|'))
      .digest('hex');
    if (seen.has(hash)) continue;
    seen.add(hash);
    out.push(r);
  }
  return out;
}

function speciesEligible(species, reviewStatus, metricType, huntName) {
  if (reviewStatus !== 'PASS') return 'false';
  const s = norm(species).toLowerCase();
  const name = norm(huntName).toLowerCase();
  if (name.includes('antlerless')) return 'false';
  if (!TROPHY_ELIGIBLE_SPECIES.some((x) => s.includes(x))) return 'false';
  if ((s.includes('black bear') || s.includes('cougar')) && metricType === 'percent_5plus_only') return 'true';
  return 'true';
}

function sortLatestCandidate(a, b) {
  const yearA = Number(a.model_target_year || 0);
  const yearB = Number(b.model_target_year || 0);
  if (yearB !== yearA) return yearB - yearA;

  const statusRank = { PASS: 3, REVIEW: 2, BLOCK: 1 };
  const rA = statusRank[a.review_status] || 0;
  const rB = statusRank[b.review_status] || 0;
  if (rB !== rA) return rB - rA;

  const metricRank = {
    average_harvest_age_and_percent_5plus: 3,
    average_harvest_age: 2,
    mean_age: 2,
    percent_5plus_only: 1,
    unknown_review: 0
  };
  const mA = metricRank[a.age_metric_type] || 0;
  const mB = metricRank[b.age_metric_type] || 0;
  if (mB !== mA) return mB - mA;

  const confRank = {
    high: 5,
    unit_level_high: 4,
    medium: 3,
    unit_level_medium: 2,
    low_review: 1,
    low: 1
  };
  const cA = confRank[norm(a.crosswalk_confidence).toLowerCase()] || 0;
  const cB = confRank[norm(b.crosswalk_confidence).toLowerCase()] || 0;
  if (cB !== cA) return cB - cA;

  const srcA = norm(a.source_file) && norm(a.source_page) ? 1 : 0;
  const srcB = norm(b.source_file) && norm(b.source_page) ? 1 : 0;
  return srcB - srcA;
}

function main() {
  const audit = {
    created_at: new Date().toISOString(),
    candidate_files_scanned: 0,
    candidate_files_used: 0,
    candidate_files_skipped: [],
    rows_read_total: 0,
    rows_written_all_years: 0,
    rows_written_latest: 0,
    rows_excluded_unaligned: 0,
    rows_review: 0,
    rows_block: 0,
    rows_pass: 0,
    zero_age_values_removed: 0,
    average_days_false_positive_blocks: 0,
    species_counts: {},
    year_counts: {},
    source_file_counts: {},
    review_reason_counts: {},
    database_validation: {
      database_csv_found: false,
      database_current_hunt_code_count: 0,
      rows_with_hunt_code_in_database: 0,
      rows_with_hunt_code_not_in_database: 0
    },
    crosswalk_validation: {
      crosswalk_found: false,
      crosswalk_rows: 0,
      historical_to_current_matches: 0
    },
    outputs: {
      all_years: OUT_ALL,
      latest: OUT_LATEST,
      review: OUT_REVIEW,
      audit_json: OUT_AUDIT_JSON,
      audit_csv: OUT_AUDIT_CSV
    }
  };

  const db = loadDatabase();
  audit.database_validation.database_csv_found = db.found;
  audit.database_validation.database_current_hunt_code_count = db.count;

  const crosswalk = loadCrosswalk();
  audit.crosswalk_validation.crosswalk_found = crosswalk.found;
  audit.crosswalk_validation.crosswalk_rows = crosswalk.rows;
  audit.crosswalk_validation.historical_to_current_matches = crosswalk.matchCount;

  const csvFiles = getAllCsvFiles();
  audit.candidate_files_scanned = csvFiles.length;

  const mergedRows = [];

  for (const file of csvFiles) {
    let headerLine = '';
    try {
      const buf = fs.readFileSync(file.abs, 'utf8');
      headerLine = (buf.split(/\r?\n/, 1)[0] || '').trim();
      const decision = selectCandidate(file, headerLine);
      if (!decision.use) {
        audit.candidate_files_skipped.push({ file: file.rel, reason: decision.reason });
        continue;
      }

      const { headers, records } = parseCsv(buf);
      if (!headers.length || !records.length) {
        audit.candidate_files_skipped.push({ file: file.rel, reason: 'empty_or_unreadable_csv' });
        continue;
      }

      const normMap = new Map();
      for (const h of headers) normMap.set(h, normKey(h));

      const ageCol = pickColumn(normMap, AGE_FIELD_PATTERNS);
      const pct5Col = pickColumn(normMap, PERCENT_5_PATTERNS);
      const adultMaleCol = pickColumn(normMap, ADULT_MALE_PATTERNS);
      const adultFemaleCol = pickColumn(normMap, ADULT_FEMALE_PATTERNS);
      const daysCol = pickColumn(normMap, DAYS_FIELD_PATTERNS);

      if (!ageCol && !pct5Col && !adultMaleCol && !adultFemaleCol) {
        audit.candidate_files_skipped.push({ file: file.rel, reason: 'no_age_or_proxy_columns' });
        continue;
      }

      audit.candidate_files_used += 1;
      audit.rows_read_total += records.length;

      for (let i = 0; i < records.length; i++) {
        const src = records[i];
        const row = {};

        const keyed = {};
        for (const [k, v] of Object.entries(src)) keyed[normKey(k)] = v;

        let huntCode = normCode(
          src.hunt_code ?? src.huntnumber ?? src.hunt_number ?? src.hunting_number ?? src.current_hunt_code ?? ''
        );
        if (!isLikelyHuntCode(huntCode)) huntCode = '';

        const species = norm(src.species || keyed.species || '').replace(/^"|"$/g, '');
        const huntName = norm(src.hunt_name || src.boundary_name || src.unit_name || src.unit || src.management_unit || '');
        const unit = norm(src.unit || src.management_unit || '');
        const unitName = norm(src.unit_name || src.boundary_name || '');

        const years = detectYears(file.rel, keyed);

        const rawAge = ageCol ? src[ageCol] : '';
        const rawPct5 = pct5Col ? src[pct5Col] : '';
        const rawAdultMale = adultMaleCol ? src[adultMaleCol] : '';
        const rawAdultFemale = adultFemaleCol ? src[adultFemaleCol] : '';
        const rawDays = daysCol ? src[daysCol] : '';

        const hasAnyAgeSignalRaw = [rawAge, rawPct5, rawAdultMale, rawAdultFemale].some((v) => norm(v) !== '');
        if (!hasAnyAgeSignalRaw) {
          continue;
        }

        let avgAgeNum = extractNumber(rawAge);
        let pct5Num = extractNumber(rawPct5);
        let adultMaleNum = extractNumber(rawAdultMale);
        let adultFemaleNum = extractNumber(rawAdultFemale);

        let reviewReasons = [];
        let blocked = false;

        if (rawAge && daysCol && ageCol && DAYS_FIELD_PATTERNS.some((rx) => rx.test(normKey(ageCol)))) {
          avgAgeNum = null;
          blocked = true;
          reviewReasons.push('FALSE_AGE_FIELD_AVERAGE_DAYS_NOT_ANIMAL_AGE');
          audit.average_days_false_positive_blocks += 1;
        }

        if (avgAgeNum !== null && avgAgeNum <= 0) {
          avgAgeNum = null;
          blocked = true;
          reviewReasons.push('ZERO_AGE_VALUE_REMOVED');
          audit.zero_age_values_removed += 1;
        }

        const hasAvgAge = avgAgeNum !== null && avgAgeNum > 0;
        const hasPct5 = pct5Num !== null;
        const hasAdultMale = adultMaleNum !== null;
        const hasAdultFemale = adultFemaleNum !== null;

        let ageMetricType = 'unknown_review';
        if (hasAvgAge && hasPct5) ageMetricType = 'average_harvest_age_and_percent_5plus';
        else if (hasAvgAge && /mean/i.test(ageCol || '')) ageMetricType = 'mean_age';
        else if (hasAvgAge) ageMetricType = 'average_harvest_age';
        else if (hasPct5) ageMetricType = 'percent_5plus_only';
        else if (hasAdultMale) ageMetricType = 'percent_adult_male';
        else if (hasAdultFemale) ageMetricType = 'percent_adult_female';

        let sourceScope = 'source_context_review';
        const relLower = file.rel.toLowerCase();
        if (huntCode) sourceScope = 'hunt_code_direct';
        else if (/statewide/.test(`${huntName} ${unit} ${unitName}`.toLowerCase())) sourceScope = 'statewide_only';
        else if (unit || unitName || /unit/.test(relLower)) sourceScope = 'unit_level_needs_hunt_code_crosswalk';
        else if (/management/.test(relLower)) sourceScope = 'management_unit_level';

        const sourceFile = norm(
          src.source_file || src.source_csv || src.source_document || path.basename(file.rel)
        );
        const sourcePage = norm(src.source_page || src.page || src.pdf_page || '');
        const sourceTableTitle = norm(src.source_table_title || src.source_table || src.table_title || src.source_table_name || '');
        const sourceRowKey = norm(
          src.source_row_key || src.row_key || `${path.basename(file.rel)}::${i + 1}`
        );
        const sourcePackageFile = path.basename(file.rel);
        const sourcePackagePath = file.rel;

        const crosswalkMethod = norm(src.crosswalk_method || src.mapping_method || src.match_method || src.hunt_code_mapping_method || '');
        const crosswalkConf = parseConfidence(src.crosswalk_confidence || src.mapping_confidence || src.confidence || '', sourceScope);
        const crosswalkScoreNum = extractNumber(src.crosswalk_score || src.mapping_score || src.score || '');

        let historicalHuntCode = '';
        let currentHuntCode = '';

        if (huntCode && crosswalk.histToCurrent.has(huntCode)) {
          historicalHuntCode = huntCode;
          currentHuntCode = crosswalk.histToCurrent.get(huntCode);
        }

        let dbMatchCode = huntCode && db.map.has(huntCode) ? huntCode : (currentHuntCode && db.map.has(currentHuntCode) ? currentHuntCode : '');
        let dbRow = dbMatchCode ? db.map.get(dbMatchCode) : null;

        function normNameLocal(v) {
          return norm(v).toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();
        }

        if (!dbRow) {
          const k1 = `${normNameLocal(species)}||${normNameLocal(huntName)}`;
          const k2 = normNameLocal(huntName);
          const candidates1 = db.bySpeciesName.get(k1) || [];
          const candidates2 = db.byNameOnly.get(k2) || [];
          let matched = null;
          if (candidates1.length === 1) matched = candidates1[0];
          else if (candidates1.length > 1 && huntCode) {
            matched = candidates1.find((x) => x.hunt_code === huntCode) || null;
          }
          if (!matched && candidates2.length === 1) matched = candidates2[0];
          if (matched) {
            dbRow = matched;
            dbMatchCode = matched.hunt_code;
            if (!huntCode) huntCode = matched.hunt_code;
          }
        }

        const databaseCodePresent = dbRow ? 'true' : 'false';
        const databaseHuntName = dbRow ? dbRow.hunt_name : '';
        const databaseSpecies = dbRow ? dbRow.species : '';

        let databaseMatchNotes = '';
        if (!huntCode) databaseMatchNotes = 'NO_HUNT_CODE_IN_SOURCE_ROW';
        else if (dbRow && dbMatchCode === huntCode) databaseMatchNotes = 'DIRECT_DATABASE_MATCH';
        else if (dbRow && dbMatchCode === currentHuntCode) databaseMatchNotes = 'MATCHED_VIA_CURRENT_HUNT_CODE_CROSSWALK';
        else if (dbRow) databaseMatchNotes = 'MATCHED_VIA_DATABASE_NAME_SPECIES';
        else databaseMatchNotes = 'NO_DATABASE_MATCH';

        const alignedHuntName = cleanToken(huntName || (dbRow ? dbRow.hunt_name : ''));
        const alignedSpecies = cleanToken(species || (dbRow ? dbRow.species : ''));
        const alignedBoundaryId = cleanToken(src.boundary_id || (dbRow ? dbRow.boundary_id : ''));

        if (!hasMeaningful(alignedSpecies)) {
          blocked = true;
          reviewReasons.push('SPECIES_MISSING');
        }
        if (!hasMeaningful(alignedHuntName)) {
          blocked = true;
          reviewReasons.push('HUNT_NAME_MISSING');
        }
        const boundaryMissingAlignment = !hasMeaningful(alignedBoundaryId);
        if (boundaryMissingAlignment) reviewReasons.push('BOUNDARY_ID_MISSING_ALIGNMENT');
        if (!years.reported_hunt_year || !years.model_target_year) {
          blocked = true;
          reviewReasons.push('YEAR_UNIDENTIFIED');
        }
        if (!sourceFile) {
          blocked = true;
          reviewReasons.push('SOURCE_FILE_MISSING');
        }

        if (!huntCode && !['statewide_only', 'unit_level_needs_hunt_code_crosswalk'].includes(sourceScope)) {
          blocked = true;
          reviewReasons.push('HUNT_CODE_MISSING_SCOPE_INVALID');
        }

        if (!hasAvgAge && !hasPct5 && !hasAdultMale && !hasAdultFemale) {
          blocked = true;
          reviewReasons.push('NO_USABLE_AGE_METRIC');
        }

        let reviewStatus = 'PASS';

        const confPass = ['high', 'medium', 'unit_level_high', 'unit_level_medium'].includes(crosswalkConf);

        if (blocked) {
          reviewStatus = 'BLOCK';
        } else if (!huntCode) {
          reviewStatus = 'REVIEW';
          reviewReasons.push('HUNT_CODE_MISSING_NEEDS_CROSSWALK');
        } else if (boundaryMissingAlignment) {
          reviewStatus = 'REVIEW';
        } else if (!confPass) {
          reviewStatus = 'REVIEW';
          reviewReasons.push('LOW_CONFIDENCE_CROSSWALK');
        } else if (!hasAvgAge && (hasPct5 || hasAdultMale || hasAdultFemale)) {
          reviewStatus = 'REVIEW';
          reviewReasons.push('PROXY_ONLY_NO_AVERAGE_AGE');
        } else if (sourceScope === 'unit_level_needs_hunt_code_crosswalk') {
          reviewStatus = 'REVIEW';
          reviewReasons.push('UNIT_LEVEL_SOURCE_NEEDS_ROW_LEVEL_CROSSWALK');
        }

        if (alignedSpecies.toLowerCase().includes('cougar') && sourceScope === 'unit_level_needs_hunt_code_crosswalk') {
          reviewStatus = 'REVIEW';
          reviewReasons.push('COUGAR_UNIT_ONLY_NEEDS_CURRENT_CG_CROSSWALK');
        }

        if (!dbRow && huntCode && !currentHuntCode) {
          reviewStatus = reviewStatus === 'BLOCK' ? 'BLOCK' : 'REVIEW';
          reviewReasons.push('HUNT_CODE_NOT_IN_CURRENT_DATABASE');
        }

        const notes = [
          norm(src.notes || src.data_quality_flags || ''),
          !hasAvgAge && hasPct5 ? 'PERCENT_5PLUS_PROXY_ONLY' : '',
          currentHuntCode ? `CROSSWALK_CURRENT_CODE=${currentHuntCode}` : ''
        ].filter(Boolean).join('|');

        const doNotPermit = toBoolStr(src.do_not_use_for_permit_quota) || 'true';
        const doNotPDraw = toBoolStr(src.do_not_use_directly_for_p_draw) || 'true';

        const qualityEligible = reviewStatus === 'PASS' ? 'true' : 'false';
        const trophyEligible = speciesEligible(alignedSpecies, reviewStatus, ageMetricType, alignedHuntName);

        row.hunt_code = huntCode;
        row.historical_hunt_code = historicalHuntCode;
        row.current_hunt_code = currentHuntCode;
        row.hunt_name = alignedHuntName;
        row.species = alignedSpecies;
        row.reported_hunt_year = years.reported_hunt_year;
        row.model_target_year = years.model_target_year;
        row.unit = unit;
        row.unit_name = unitName;
        row.boundary_id = alignedBoundaryId;
        row.boundary_name = norm(src.boundary_name || (dbRow ? dbRow.boundary_name : ''));
        row.average_harvest_age = hasAvgAge ? String(avgAgeNum) : '';
        row.age_data_available = hasAvgAge || hasPct5 || hasAdultMale || hasAdultFemale ? 'true' : 'false';
        row.percent_5plus = hasPct5 ? String(pct5Num) : '';
        row.percent_mature_or_5_plus = hasPct5 ? String(pct5Num) : '';
        row.percent_adult_male = hasAdultMale ? String(adultMaleNum) : '';
        row.percent_adult_female = hasAdultFemale ? String(adultFemaleNum) : '';
        row.age_metric_type = ageMetricType;
        row.age_source_scope = sourceScope;
        row.source_file = sourceFile;
        row.source_page = sourcePage;
        row.source_table_title = sourceTableTitle;
        row.source_row_key = sourceRowKey;
        row.source_package_file = sourcePackageFile;
        row.source_package_path = sourcePackagePath;
        row.crosswalk_method = crosswalkMethod;
        row.crosswalk_confidence = crosswalkConf;
        row.crosswalk_score = crosswalkScoreNum !== null ? String(crosswalkScoreNum) : '';
        row.review_status = reviewStatus;
        row.review_reason = Array.from(new Set(reviewReasons)).join('|');
        row.do_not_use_for_permit_quota = doNotPermit;
        row.do_not_use_directly_for_p_draw = doNotPDraw;
        row.quality_score_eligible = qualityEligible;
        row.trophy_age_score_eligible = trophyEligible;
        row.notes = notes;
        row.database_code_present = databaseCodePresent;
        row.database_hunt_name = databaseHuntName;
        row.database_species = databaseSpecies;
        row.database_match_notes = databaseMatchNotes;

        for (const col of CANONICAL_COLUMNS) if (!(col in row)) row[col] = '';
        mergedRows.push(row);
      }
    } catch (err) {
      audit.candidate_files_skipped.push({ file: file.rel, reason: `read_or_parse_error:${String(err.message || err)}` });
    }
  }

  const deduped = dedupeRows(mergedRows);
  const alignedAllYearsRows = deduped.filter(
    (r) => hasMeaningful(r.hunt_code) && hasMeaningful(r.hunt_name) && hasMeaningful(r.species) && hasMeaningful(r.boundary_id)
  );

  const latestMap = new Map();
  for (const row of alignedAllYearsRows) {
    const effectiveCode = row.current_hunt_code || row.hunt_code;
    if (!effectiveCode) continue;
    const key = `${effectiveCode}||${norm(row.species).toLowerCase()}`;

    const clone = { ...row };
    if (row.current_hunt_code && row.current_hunt_code !== row.hunt_code) {
      clone.historical_hunt_code = row.hunt_code;
      clone.hunt_code = row.current_hunt_code;
      clone.database_match_notes = `${clone.database_match_notes}|LATEST_OUTPUT_USES_CURRENT_HUNT_CODE`;
    }

    if (!latestMap.has(key)) {
      latestMap.set(key, clone);
    } else {
      const winner = [latestMap.get(key), clone].sort(sortLatestCandidate)[0];
      latestMap.set(key, winner);
    }
  }

  const latestRows = Array.from(latestMap.values()).sort((a, b) => {
    if (a.hunt_code < b.hunt_code) return -1;
    if (a.hunt_code > b.hunt_code) return 1;
    return Number(b.model_target_year || 0) - Number(a.model_target_year || 0);
  });

  const reviewRows = deduped.filter(
    (r) =>
      r.review_status !== 'PASS' ||
      !hasMeaningful(r.hunt_code) ||
      !hasMeaningful(r.hunt_name) ||
      !hasMeaningful(r.species) ||
      !hasMeaningful(r.boundary_id)
  );

  for (const row of deduped) {
    audit.species_counts[row.species || 'UNKNOWN'] = (audit.species_counts[row.species || 'UNKNOWN'] || 0) + 1;
    audit.year_counts[row.reported_hunt_year || 'UNKNOWN'] = (audit.year_counts[row.reported_hunt_year || 'UNKNOWN'] || 0) + 1;
    audit.source_file_counts[row.source_file || 'UNKNOWN'] = (audit.source_file_counts[row.source_file || 'UNKNOWN'] || 0) + 1;

    if (row.review_reason) {
      for (const reason of row.review_reason.split('|')) {
        if (!reason) continue;
        audit.review_reason_counts[reason] = (audit.review_reason_counts[reason] || 0) + 1;
      }
    }

    if (row.review_status === 'PASS') audit.rows_pass += 1;
    if (row.review_status === 'REVIEW') audit.rows_review += 1;
    if (row.review_status === 'BLOCK') audit.rows_block += 1;

    if (row.database_code_present === 'true') audit.database_validation.rows_with_hunt_code_in_database += 1;
    else if (row.hunt_code) audit.database_validation.rows_with_hunt_code_not_in_database += 1;
  }

  audit.rows_excluded_unaligned = deduped.length - alignedAllYearsRows.length;
  audit.rows_written_all_years = alignedAllYearsRows.length;
  audit.rows_written_latest = latestRows.length;

  writeCsv(OUT_ALL, alignedAllYearsRows, CANONICAL_COLUMNS);
  writeCsv(OUT_LATEST, latestRows, CANONICAL_COLUMNS);
  writeCsv(OUT_REVIEW, reviewRows, CANONICAL_COLUMNS);

  const auditRows = [];
  function pushAudit(key, value) {
    auditRows.push({ key, value: typeof value === 'string' ? value : JSON.stringify(value) });
  }

  for (const [k, v] of Object.entries(audit)) {
    if (k === 'outputs') continue;
    pushAudit(k, v);
  }
  for (const [k, v] of Object.entries(audit.outputs)) pushAudit(`outputs.${k}`, v);

  fs.mkdirSync(path.dirname(OUT_AUDIT_JSON), { recursive: true });
  fs.writeFileSync(OUT_AUDIT_JSON, JSON.stringify(audit, null, 2), 'utf8');
  writeCsv(OUT_AUDIT_CSV, auditRows, ['key', 'value']);

  const topSpecies = Object.entries(audit.species_counts).sort((a, b) => b[1] - a[1]).slice(0, 12);
  console.log('Harvest Age Master Backfill Summary');
  console.log('------------------------------------');
  console.log(`candidate files scanned: ${audit.candidate_files_scanned}`);
  console.log(`files used: ${audit.candidate_files_used}`);
  console.log(`all-years rows: ${audit.rows_written_all_years}`);
  console.log(`latest rows: ${audit.rows_written_latest}`);
  console.log(`PASS/REVIEW/BLOCK: ${audit.rows_pass}/${audit.rows_review}/${audit.rows_block}`);
  console.log(`zero age values removed: ${audit.zero_age_values_removed}`);
  console.log(`average-days false positives blocked: ${audit.average_days_false_positive_blocks}`);
  console.log('top species counts:', topSpecies.map(([s, c]) => `${s}:${c}`).join(', '));
  console.log('outputs:');
  console.log(`- ${OUT_ALL}`);
  console.log(`- ${OUT_LATEST}`);
  console.log(`- ${OUT_REVIEW}`);
  console.log(`- ${OUT_AUDIT_JSON}`);
  console.log(`- ${OUT_AUDIT_CSV}`);
}

main();
