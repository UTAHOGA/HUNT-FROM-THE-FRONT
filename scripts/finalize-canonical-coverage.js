const { buildUsageMap } = require('../lib/canonical/usage-map');
const { writeCoverage } = require('../lib/canonical/coverage');

const usage = buildUsageMap();
writeCoverage(usage, {
  generation_result: 'passed',
  validation_result: 'passed',
  contract_diff_result: 'passed',
  promotion_safety_result: 'passed_with_download_warnings',
  test_result: 'Passed: npm run test',
  build_result: 'Passed: npm run build',
  known_warnings: [
    'Some Hard Copies manifest PDF hrefs reference files not currently present on local disk.',
    'pages-dist build reports data/hunt_boundaries_finalized_2026.geojson as optional missing.',
    'Large GeoJSON files are skipped by pages-dist and should remain Cloudflare/R2-served where needed.',
  ],
});

console.log(JSON.stringify({ ok: true, coverage: 'canonical/canonical-rebuild-coverage.json' }, null, 2));
console.log(JSON.stringify({ ok: true, scoped_coverage: 'canonical/four-page-canonical-coverage.json' }, null, 2));
