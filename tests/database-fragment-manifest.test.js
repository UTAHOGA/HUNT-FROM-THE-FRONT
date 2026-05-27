const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const MANIFEST = path.join(ROOT, 'data_truth', 'comparison_outputs', 'database_fragment_audit', 'database_fragment_manifest.csv');
const RECOMMENDATIONS = path.join(ROOT, 'data_truth', 'comparison_outputs', 'database_fragment_audit', 'database_fragment_recommendations.csv');
const SUMMARY = path.join(ROOT, 'data_truth', 'comparison_outputs', 'database_fragment_audit', 'database_fragment_summary.json');
const REPORT = path.join(ROOT, 'processed_data', 'database_fragment_audit.md');

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exit(1);
  }
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

function readRows(filePath) {
  const lines = fs.readFileSync(filePath, 'utf8').trim().split(/\r?\n/);
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] || '';
    });
    return row;
  });
}

assert(fs.existsSync(MANIFEST), 'database fragment manifest is missing');
assert(fs.existsSync(RECOMMENDATIONS), 'database fragment recommendations file is missing');
assert(fs.existsSync(SUMMARY), 'database fragment summary is missing');
assert(fs.existsSync(REPORT), 'database fragment markdown report is missing');

const rows = readRows(MANIFEST);
const summary = JSON.parse(fs.readFileSync(SUMMARY, 'utf8'));
const recommendationText = fs.readFileSync(RECOMMENDATIONS, 'utf8');
const recommendationRows = readRows(RECOMMENDATIONS);
assert(rows.length > 0, 'manifest has no rows');
assert(recommendationRows.length === rows.length, 'recommendations row count should match manifest rows');
assert(Number(summary.total_files) === rows.length, 'summary total_files does not match manifest rows');

const official = rows.find((row) => row.relative_path === 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv');
assert(official, 'official DATABASE.csv row is missing');
assert(official.classification === 'official_current_source', 'DATABASE.csv is not classified as official_current_source');

const crosswalk = rows.find((row) => row.relative_path === 'processed_data/current_to_historical_hunt_code_crosswalk_2026.csv');
assert(crosswalk, 'current-to-historical crosswalk row is missing');
assert(crosswalk.has_current_hunt_code === 'true', 'crosswalk does not expose current_hunt_code');
assert(crosswalk.has_historical_hunt_code === 'true', 'crosswalk does not expose historical_hunt_code');
assert(crosswalk.classification === 'runtime_engine_output', 'crosswalk should remain runtime_engine_output');

const obsoleteCount = rows.filter((row) => row.classification === 'obsolete_fragment').length;
assert(obsoleteCount > 0, 'expected at least one obsolete fragment to be classified');
assert(recommendationText.includes('external_import_review'), 'expected external import review bucket');
assert(recommendationText.includes('delete_or_ignore_candidate'), 'expected delete/ignore candidate bucket');

console.log(`PASS: database fragment manifest validation (${rows.length} rows)`);
