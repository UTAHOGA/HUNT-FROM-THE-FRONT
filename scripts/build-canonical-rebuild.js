const { buildAndWriteAll } = require('../lib/canonical/generators');
const { writeCoverage } = require('../lib/canonical/coverage');

const now = new Date().toISOString();
const result = buildAndWriteAll(now);
writeCoverage(result.usage, { generation_result: 'passed' }, now);

console.log(JSON.stringify({
  ok: true,
  generated_at: now,
  canonical_files: [
    'canonical/shared-2026.json',
    'canonical/hunt-planner-2026.json',
    'canonical/hunt-research-2026.json',
    'canonical/hard-copies-2026.json',
    'canonical/outfitter-verification-2026.json',
  ],
  generated_pages: Object.keys(result.generatedPages).map(key => `generated/pages/${key}.json`),
  usage_entries: result.usage.length,
}, null, 2));
