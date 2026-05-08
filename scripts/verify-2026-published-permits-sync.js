const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const SOURCE_LABEL = 'DATABASE_2026_DWR_APPROVED_PUBLISHED_PERMITS';
const STAMP = new Date().toISOString().replace(/[-:]/g, '').slice(0, 15);

const DATABASE_FILE = 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv';

const CSV_TARGETS = [
  {
    file: 'processed_data/hunt_master_enriched.csv',
    expectPublicPermits: true,
  },
  {
    file: 'processed_data/hunt_unit_reference_linked.csv',
    expectPublicPermits: true,
  },
  {
    file: 'processed_data/draw_reality_engine.csv',
    expectPublicPermits: true,
  },
  {
    file: 'processed_data/point_ladder_view.csv',
    expectPublicPermits: false,
  },
];

const JSON_TARGETS = [
  'data/hunt-master-canonical-2026-database-candidate.json',
  'data/hunt-master-canonical-2026-foundation.json',
  'data/hunt-master-canonical-2026-source-of-truth.json',
  'processed_data/hunt-master-canonical-2026-source-of-truth.json',
  'canonical/hunt-planner-2026.json',
  'generated/pages/hunt-planner.json',
];

function abs(file) {
  return path.join(REPO, file);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        value += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(value);
      value = '';
    } else if (ch === '\n') {
      row.push(value);
      rows.push(row);
      row = [];
      value = '';
    } else if (ch !== '\r') {
      value += ch;
    }
  }

  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }

  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map((h) => String(h || '').trim());
  return {
    headers,
    records: rows
      .filter((r) => r.some((v) => String(v || '').trim() !== ''))
      .map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i] || '']))),
  };
}

function readCsv(file) {
  return parseCsv(fs.readFileSync(abs(file), 'utf8'));
}

function normCode(value) {
  return String(value || '').trim().toUpperCase();
}

function clean(value) {
  return String(value ?? '').trim();
}

function permitNumber(value) {
  const match = clean(value).match(/-?\d+/);
  return match ? match[0] : '';
}

function residencyPublicPermit(row, db) {
  const residency = clean(row.residency).toLowerCase();
  if (residency.includes('non')) return db.permits_2026_nr || db.permits_2026_total || '';
  if (residency.includes('res')) return db.permits_2026_res || db.permits_2026_total || '';
  return db.permits_2026_total || db.permits_2026_res || db.permits_2026_nr || '';
}

function loadDatabase() {
  const { records } = readCsv(DATABASE_FILE);
  const byCode = new Map();
  const duplicates = [];
  for (const row of records) {
    const code = normCode(row.hunt_code || row.hunt_number);
    if (!code) continue;
    const normalized = {
      hunt_code: code,
      permits_2026_res: permitNumber(row.permits_2026_res),
      permits_2026_nr: permitNumber(row.permits_2026_nr),
      permits_2026_total: permitNumber(row.permits_2026_total || row.total_2026_permits),
    };
    if (byCode.has(code)) duplicates.push(code);
    byCode.set(code, normalized);
  }
  return { byCode, duplicates };
}

function verifyCsvTarget(target, dbByCode) {
  const { headers, records } = readCsv(target.file);
  const required = [
    'permits_2026_res',
    'permits_2026_nr',
    'permits_2026_total',
    'permits_2026_source',
  ];
  if (target.expectPublicPermits) {
    required.push('public_permits_2026', 'public_permits_2026_source');
  }

  const missingColumns = required.filter((field) => !headers.includes(field));
  const mismatches = [];
  let matchedRows = 0;

  records.forEach((row, index) => {
    const code = normCode(row.hunt_code || row.hunt_number);
    const db = dbByCode.get(code);
    if (!db) return;
    matchedRows += 1;

    for (const field of ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total']) {
      if (db[field] && clean(row[field]) !== db[field]) {
        mismatches.push({
          row_number: index + 2,
          hunt_code: code,
          field,
          expected: db[field],
          actual: clean(row[field]),
        });
      }
    }

    const hasAnyPermit = db.permits_2026_res || db.permits_2026_nr || db.permits_2026_total;
    if (hasAnyPermit && clean(row.permits_2026_source) !== SOURCE_LABEL) {
      mismatches.push({
        row_number: index + 2,
        hunt_code: code,
        field: 'permits_2026_source',
        expected: SOURCE_LABEL,
        actual: clean(row.permits_2026_source),
      });
    }

    if (target.expectPublicPermits && db.permits_2026_total) {
      const expectedPublic = residencyPublicPermit(row, db);
      if (expectedPublic && clean(row.public_permits_2026) !== expectedPublic) {
        mismatches.push({
          row_number: index + 2,
          hunt_code: code,
          residency: clean(row.residency),
          field: 'public_permits_2026',
          expected: expectedPublic,
          actual: clean(row.public_permits_2026),
        });
      }
      if (expectedPublic && clean(row.public_permits_2026_source) !== SOURCE_LABEL) {
        mismatches.push({
          row_number: index + 2,
          hunt_code: code,
          field: 'public_permits_2026_source',
          expected: SOURCE_LABEL,
          actual: clean(row.public_permits_2026_source),
        });
      }
    }
  });

  return {
    file: target.file,
    rows: records.length,
    matched_rows: matchedRows,
    missing_columns: missingColumns,
    mismatch_count: mismatches.length,
    sample_mismatches: mismatches.slice(0, 50),
  };
}

function findHuntsArray(value) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== 'object') return [];
  if (Array.isArray(value.hunt_catalog)) return value.hunt_catalog;
  if (Array.isArray(value.hunts)) return value.hunts;
  if (value.hunt_planner && Array.isArray(value.hunt_planner.hunts)) return value.hunt_planner.hunts;
  return [];
}

function verifyJsonTarget(file, dbByCode) {
  if (!fs.existsSync(abs(file))) {
    return { file, exists: false, mismatch_count: 1, sample_mismatches: [{ reason: 'missing_file' }] };
  }
  const data = JSON.parse(fs.readFileSync(abs(file), 'utf8'));
  const hunts = findHuntsArray(data);
  const mismatches = [];
  let matchedRows = 0;

  hunts.forEach((hunt, index) => {
    const code = normCode(hunt.hunt_code || hunt.hunt_number || hunt.id);
    const db = dbByCode.get(code);
    if (!db) return;
    matchedRows += 1;
    for (const field of ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total']) {
      if (db[field] && clean(hunt[field]) !== db[field]) {
        mismatches.push({
          row_index: index,
          hunt_code: code,
          field,
          expected: db[field],
          actual: clean(hunt[field]),
        });
      }
    }
    if ((db.permits_2026_res || db.permits_2026_nr || db.permits_2026_total)
      && clean(hunt.permits_2026_source) !== SOURCE_LABEL) {
      mismatches.push({
        row_index: index,
        hunt_code: code,
        field: 'permits_2026_source',
        expected: SOURCE_LABEL,
        actual: clean(hunt.permits_2026_source),
      });
    }
  });

  return {
    file,
    exists: true,
    rows: hunts.length,
    matched_rows: matchedRows,
    mismatch_count: mismatches.length,
    sample_mismatches: mismatches.slice(0, 50),
  };
}

function writeReport(report) {
  const outJson = `processed_data/permit_sync_2026_published_verification_${STAMP}.json`;
  const outMd = `processed_data/permit_sync_2026_published_verification_${STAMP}.md`;
  fs.writeFileSync(abs(outJson), JSON.stringify(report, null, 2));

  const lines = [
    '# 2026 Published Permit Verification',
    '',
    `Generated: ${report.generated_at}`,
    `Permit source: ${SOURCE_LABEL}`,
    `Overall status: ${report.ok ? 'PASS' : 'FAIL'}`,
    '',
    '## CSV Targets',
    '',
    '| File | Rows | Matched | Missing Columns | Mismatches |',
    '| --- | ---: | ---: | --- | ---: |',
  ];
  for (const target of report.csv_results) {
    lines.push(`| ${target.file} | ${target.rows} | ${target.matched_rows} | ${target.missing_columns.join(', ') || 'none'} | ${target.mismatch_count} |`);
  }
  lines.push('', '## JSON Targets', '', '| File | Rows | Matched | Mismatches |', '| --- | ---: | ---: | ---: |');
  for (const target of report.json_results) {
    lines.push(`| ${target.file} | ${target.rows || 0} | ${target.matched_rows || 0} | ${target.mismatch_count} |`);
  }
  lines.push('', '## Notes', '');
  lines.push('This verifies that 2026 published permit fields match DATABASE.csv and remain source-labeled separately from harvest/draw-result permit fields.');
  fs.writeFileSync(abs(outMd), `${lines.join('\n')}\n`);

  return { outJson, outMd };
}

function main() {
  const { byCode: dbByCode, duplicates } = loadDatabase();
  const csvResults = CSV_TARGETS.map((target) => verifyCsvTarget(target, dbByCode));
  const jsonResults = JSON_TARGETS.map((file) => verifyJsonTarget(file, dbByCode));
  const ok = [...csvResults, ...jsonResults].every((r) => r.mismatch_count === 0 && (!r.missing_columns || r.missing_columns.length === 0));
  const report = {
    generated_at: new Date().toISOString(),
    ok,
    source_label: SOURCE_LABEL,
    database_file: DATABASE_FILE,
    database_unique_codes: dbByCode.size,
    database_duplicate_codes: [...new Set(duplicates)].sort(),
    csv_results: csvResults,
    json_results: jsonResults,
  };
  const outputs = writeReport(report);
  console.log(JSON.stringify({ ok, ...outputs }, null, 2));
  if (!ok) process.exitCode = 1;
}

main();
