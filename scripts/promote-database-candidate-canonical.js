const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');
const BACKUP_DIR = `processed_data/backups/runtime_canonical_promote_${STAMP}`;

const SOURCE = 'data/hunt-master-canonical-2026-database-candidate.json';
const TARGETS = [
  'data/hunt-master-canonical-2026-foundation.json',
  'data/hunt-master-canonical-2026-source-of-truth.json',
  'processed_data/hunt-master-canonical-2026-source-of-truth.json',
];

function abs(file) {
  return path.join(REPO, file);
}

function normalizeCode(value) {
  return String(value || '').trim().toUpperCase();
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(abs(file), 'utf8'));
}

function rowsFromJson(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.hunt_catalog)) return data.hunt_catalog;
  if (Array.isArray(data.hunts)) return data.hunts;
  return [];
}

function stats(rows) {
  const codes = new Set(rows.map((row) => normalizeCode(row.hunt_code || row.huntCode || row.code)).filter(Boolean));
  return {
    rows: rows.length,
    unique_hunt_codes: codes.size,
    with_2026_permit_total: rows.filter((row) => String(row.permits_2026_total || '').trim()).length,
    with_2026_permit_source: rows.filter((row) => String(row.permits_2026_source || '').trim()).length,
  };
}

function backup(file) {
  const dest = abs(path.join(BACKUP_DIR, file));
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(abs(file), dest);
}

function main() {
  const sourceData = readJson(SOURCE);
  const sourceRows = rowsFromJson(sourceData);
  if (!sourceRows.length) {
    throw new Error(`${SOURCE} does not contain runtime hunt rows.`);
  }
  const sourceStats = stats(sourceRows);
  if (sourceStats.unique_hunt_codes < 1300) {
    throw new Error(`${SOURCE} has only ${sourceStats.unique_hunt_codes} unique hunt codes; refusing to promote.`);
  }

  const targetReports = [];
  for (const target of TARGETS) {
    const beforeRows = fs.existsSync(abs(target)) ? rowsFromJson(readJson(target)) : [];
    if (fs.existsSync(abs(target))) backup(target);
    fs.mkdirSync(path.dirname(abs(target)), { recursive: true });
    fs.writeFileSync(abs(target), `${JSON.stringify(sourceData, null, 2)}\n`, 'utf8');
    const afterRows = rowsFromJson(readJson(target));
    targetReports.push({
      file: target,
      before: stats(beforeRows),
      after: stats(afterRows),
    });
  }

  const report = {
    generated_at: new Date().toISOString(),
    source: SOURCE,
    backup_dir: BACKUP_DIR,
    source_stats: sourceStats,
    targets: targetReports,
  };
  const reportJson = `processed_data/runtime_canonical_promotion_report_${STAMP}.json`;
  const reportMd = `processed_data/runtime_canonical_promotion_report_${STAMP}.md`;
  fs.writeFileSync(abs(reportJson), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(abs(reportMd), [
    '# Runtime Canonical Promotion Report',
    '',
    `Generated: ${report.generated_at}`,
    `Source: ${SOURCE}`,
    `Backup directory: ${BACKUP_DIR}`,
    '',
    '| Target | Before codes | After codes | After rows | Permit-source rows |',
    '| --- | ---: | ---: | ---: | ---: |',
    ...targetReports.map((item) => `| ${item.file} | ${item.before.unique_hunt_codes} | ${item.after.unique_hunt_codes} | ${item.after.rows} | ${item.after.with_2026_permit_source} |`),
    '',
  ].join('\n'));

  console.log(JSON.stringify({
    ok: true,
    source_stats: sourceStats,
    backup_dir: BACKUP_DIR,
    report_json: reportJson,
    report_md: reportMd,
  }, null, 2));
}

main();
