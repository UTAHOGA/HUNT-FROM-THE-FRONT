const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..');
const outJson = path.join(repoRoot, 'processed_data', 'audits', 'research_runtime_source_audit.json');
const outCsv = path.join(repoRoot, 'processed_data', 'audits', 'research_runtime_source_audit.csv');

const urls = [
  'https://json.uoga.workers.dev/processed_data/point_ladder_view.csv',
  'https://json.uoga.workers.dev/point_ladder_view.csv',
  'https://json.uoga.workers.dev/processed_data/hunt_master_enriched.csv',
  'https://json.uoga.workers.dev/hunt_master_enriched.csv',
  'https://json.uoga.workers.dev/processed_data/hunt_unit_reference_linked.csv',
  'https://json.uoga.workers.dev/hunt_unit_reference_linked.csv',
  'https://json.uoga.workers.dev/processed_data/draw_reality_engine_v2.csv',
  'https://json.uoga.workers.dev/draw_reality_engine_v2.csv',
  'https://json.uoga.workers.dev/processed_data/draw_reality_engine_predictive_v2.csv',
  'https://json.uoga.workers.dev/draw_reality_engine_predictive_v2.csv',
];

const criticalFiles = [
  'point_ladder_view.csv',
  'hunt_master_enriched.csv',
  'hunt_unit_reference_linked.csv',
];

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function firstNonemptyLine(text) {
  return String(text || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean) || '';
}

function looksLikeCsv(text) {
  const firstLine = firstNonemptyLine(text);
  if (!firstLine) return false;
  const lower = firstLine.toLowerCase();
  return firstLine.includes(',') && !lower.startsWith('<html') && !lower.startsWith('{');
}

async function auditUrl(url) {
  const row = {
    url,
    status: 0,
    content_type: '',
    byte_length: 0,
    first_200_chars: '',
    is_lfs_pointer: false,
    looks_like_csv: false,
    ok_for_research: false,
    error: '',
  };

  try {
    const response = await fetch(url, { cache: 'no-store' });
    const text = await response.text();
    row.status = response.status;
    row.content_type = response.headers.get('content-type') || '';
    row.byte_length = Buffer.byteLength(text, 'utf8');
    row.first_200_chars = text.slice(0, 200);
    row.is_lfs_pointer = text.startsWith('version https://git-lfs.github.com/spec/v1');
    row.looks_like_csv = looksLikeCsv(text);
    row.ok_for_research = response.status === 200 && !row.is_lfs_pointer && row.looks_like_csv;
  } catch (error) {
    row.error = error && error.message ? error.message : String(error);
  }

  return row;
}

async function main() {
  const createdAt = new Date().toISOString();
  const results = [];
  for (const url of urls) {
    results.push(await auditUrl(url));
  }

  const critical = {};
  for (const fileName of criticalFiles) {
    critical[fileName] = results.some((row) => row.ok_for_research && row.url.endsWith(`/${fileName}`));
  }

  const summary = {
    created_at: createdAt,
    urls_checked: results.length,
    urls_ok_for_research: results.filter((row) => row.ok_for_research).length,
    urls_lfs_pointer: results.filter((row) => row.is_lfs_pointer).length,
    critical_files: criticalFiles,
    critical_files_ok: critical,
    dashboard_gate_ok: Object.values(critical).every(Boolean),
  };

  fs.mkdirSync(path.dirname(outJson), { recursive: true });
  fs.writeFileSync(outJson, JSON.stringify({ ...summary, results }, null, 2), 'utf8');

  const headers = [
    'url',
    'status',
    'content_type',
    'byte_length',
    'first_200_chars',
    'is_lfs_pointer',
    'looks_like_csv',
    'ok_for_research',
    'error',
  ];
  const csv = [
    headers.join(','),
    ...results.map((row) => headers.map((header) => csvEscape(row[header])).join(',')),
  ].join('\n');
  fs.writeFileSync(outCsv, `${csv}\n`, 'utf8');

  console.log(`Research runtime source audit: ${summary.urls_ok_for_research}/${summary.urls_checked} URLs OK`);
  for (const [fileName, ok] of Object.entries(critical)) {
    console.log(`${ok ? 'OK' : 'FAIL'} critical ${fileName}`);
  }
  console.log(`Wrote ${path.relative(repoRoot, outJson)}`);
  console.log(`Wrote ${path.relative(repoRoot, outCsv)}`);

  if (!summary.dashboard_gate_ok) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
