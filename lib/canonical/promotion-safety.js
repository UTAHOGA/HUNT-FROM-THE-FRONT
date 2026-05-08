const { readJson } = require('./inventory');
const { validateCanonical } = require('./validators');

function promotionSafetyCheck() {
  const validation = validateCanonical();
  const usage = readJson('canonical/canonical-field-usage-map.json', []);
  const consumedUnmapped = usage.filter(item =>
    item.migration_status !== 'mapped'
    && Array.isArray(item.consumed_by_files)
    && item.consumed_by_files.length
  );
  const coverage = readJson('canonical/canonical-rebuild-coverage.json', {});
  const hardCopies = readJson('generated/pages/hard-copies.json', {});
  const planner = readJson('generated/pages/hunt-planner.json', {});

  const blockers = [];
  if (!validation.ok) blockers.push(...validation.errors);
  if (consumedUnmapped.length) blockers.push(`${consumedUnmapped.length} consumed fields are not mapped`);
  if (!coverage.validation_status) blockers.push('Coverage lacks validation_status');
  if (!(hardCopies.library && hardCopies.library.items && hardCopies.library.items.length)) blockers.push('Hard Copies generated data has no library items');
  if (!(planner.hunt_catalog && planner.hunt_catalog.length)) blockers.push('Hunt Planner generated data has no hunt catalog');

  return {
    safe_to_promote: blockers.length === 0,
    blockers,
    warnings: validation.warnings,
  };
}

module.exports = { promotionSafetyCheck };
