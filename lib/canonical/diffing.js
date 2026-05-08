const { PAGES, abs, htmlContract, readJson } = require('./inventory');

function duplicateIds(items, keyName = 'id') {
  const seen = new Set();
  const dupes = new Set();
  for (const item of items || []) {
    const value = item && item[keyName];
    if (!value) continue;
    if (seen.has(value)) dupes.add(value);
    seen.add(value);
  }
  return [...dupes];
}

function compareRuntimeContracts() {
  const findings = [];
  const shared = readJson('canonical/shared-2026.json', {});
  for (const page of PAGES) {
    const route = (shared.routes || []).find(item => item.id === page.key);
    if (!route) {
      findings.push({ level: 'error', message: `Missing shared route for ${page.key}` });
      continue;
    }
    const current = htmlContract(page.html);
    const generatedIds = new Set(route.ui_contract && route.ui_contract.ids || []);
    for (const id of current.ids) {
      if (!generatedIds.has(id)) findings.push({ level: 'error', message: `Dropped DOM id ${id} from ${page.html}` });
    }
  }

  const planner = readJson('generated/pages/hunt-planner.json', {});
  const foundation = readJson('data/hunt-master-canonical-2026-foundation.json', []);
  const generatedHunts = planner.hunt_catalog || [];
  if (generatedHunts.length < foundation.length) {
    findings.push({ level: 'error', message: `Generated hunt planner catalog has ${generatedHunts.length} hunts, fewer than current foundation ${foundation.length}` });
  }

  return {
    ok: findings.filter(item => item.level === 'error').length === 0,
    findings,
    checked_files: PAGES.map(page => page.html),
  };
}

function localAssetExists(runtimePath) {
  const value = String(runtimePath || '').split('?')[0];
  if (!value || value.startsWith('http') || value.startsWith('#') || value.startsWith('mailto:') || value.startsWith('tel:')) return true;
  return require('fs').existsSync(abs(value.replace(/^\.\//, '')));
}

module.exports = { compareRuntimeContracts, duplicateIds, localAssetExists };
