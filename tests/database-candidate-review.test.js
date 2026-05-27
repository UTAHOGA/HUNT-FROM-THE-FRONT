const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const SCRIPT = path.join(ROOT, 'scripts', 'build-database-candidate-review-package.js');
const OUT_DIR = path.join(ROOT, 'data_truth', 'comparison_outputs', 'database_candidate_review');
const SUMMARY = path.join(OUT_DIR, 'database_candidate_review_summary.json');
const RECORDS = path.join(OUT_DIR, 'database_candidate_review_records.csv');
const BY_CODE = path.join(OUT_DIR, 'database_candidate_review_by_current_code.csv');
const INVENTORY = path.join(OUT_DIR, 'database_candidate_review_source_inventory.csv');

function parseCsvLine(line) {
  const values = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const c = line[i];
    const n = line[i + 1];
    if (c === '"' && inQuotes && n === '"') { field += '"'; i += 1; }
    else if (c === '"') inQuotes = !inQuotes;
    else if (c === ',' && !inQuotes) { values.push(field); field = ''; }
    else field += c;
  }
  values.push(field);
  return values;
}

function readHeader(file) {
  return parseCsvLine(fs.readFileSync(file, 'utf8').split(/\r?\n/)[0]);
}

childProcess.execFileSync(process.execPath, [SCRIPT], { cwd: ROOT, stdio: 'inherit' });

const summary = JSON.parse(fs.readFileSync(SUMMARY, 'utf8'));

if (summary.database_hunt_codes !== 1449) {
  throw new Error(`Expected 1449 database hunt codes, found ${summary.database_hunt_codes}`);
}
if (summary.source_files_present < 20) {
  throw new Error(`Expected at least 20 present source files, found ${summary.source_files_present}`);
}
if (summary.evidence_records < 10000) {
  throw new Error(`Expected substantial consolidated evidence records, found ${summary.evidence_records}`);
}
if (!fs.existsSync(RECORDS) || !fs.existsSync(BY_CODE) || !fs.existsSync(INVENTORY)) {
  throw new Error('Missing one or more database candidate review outputs.');
}

const recordHeader = readHeader(RECORDS);
[
  'evidence_domain',
  'source_dataset',
  'current_hunt_code',
  'candidate_hunt_code',
  'database_match_status',
  'review_status',
  'possible_fill_fields',
].forEach((field) => {
  if (!recordHeader.includes(field)) throw new Error(`Missing records column ${field}`);
});

const byCodeHeader = readHeader(BY_CODE);
[
  'current_hunt_code',
  'evidence_domains',
  'source_datasets',
  'possible_fill_fields',
  'review_statuses',
].forEach((field) => {
  if (!byCodeHeader.includes(field)) throw new Error(`Missing by-code column ${field}`);
});

console.log('database candidate review package test passed');
