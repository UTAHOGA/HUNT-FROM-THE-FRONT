const assert = require('assert');
const { readJson } = require('../lib/canonical/inventory');
const { compareRuntimeContracts } = require('../lib/canonical/diffing');
const { validateCanonical } = require('../lib/canonical/validators');
const { promotionSafetyCheck } = require('../lib/canonical/promotion-safety');

const validation = validateCanonical();
assert.strictEqual(validation.ok, true, validation.errors.join('\n'));

const contract = compareRuntimeContracts();
assert.strictEqual(contract.ok, true, JSON.stringify(contract.findings, null, 2));

const planner = readJson('generated/pages/hunt-planner.json', {});
assert.ok(Array.isArray(planner.hunt_catalog), 'Planner generated data must include hunt_catalog array');
assert.ok(planner.hunt_catalog.length >= 1288, 'Planner generated data must preserve current hunt catalog size');
for (const id of ['speciesFilter', 'sexFilter', 'huntTypeFilter', 'huntCategoryFilter', 'weaponFilter', 'unitFilter']) {
  assert.ok(planner.filters.some(filter => filter.id === id), `Missing planner filter ${id}`);
}

const research = readJson('generated/pages/hunt-research.json', {});
assert.ok(research.modeled_fields.includes('p_draw_mean'), 'Research generated data must include p_draw_mean');
assert.ok(research.legacy_fields.includes('status'), 'Research generated data must preserve legacy status');
assert.ok(research.hunt_quality_fields.includes('avg_days_2026'), 'Research generated data must preserve avg_days_2026 quality field');
assert.ok(research.hunt_quality_fields.includes('satisfaction_2026'), 'Research generated data must preserve satisfaction_2026 quality field');
assert.ok(research.odds_selection_policy.join(' ').includes('MAX POOL'), 'Research generated data must document MAX POOL safety rule');

const hardCopies = readJson('generated/pages/hard-copies.json', {});
assert.ok(hardCopies.library.items.length > 0, 'Hard Copies generated data must include PDF manifest items');
assert.ok(hardCopies.library.items.every(item => item.title && item.href && item.group && item.type), 'Every hard-copy item needs title, href, group, and type');

const verification = readJson('generated/pages/outfitter-verification.json', {});
assert.ok(verification.standards.length > 0, 'Outfitter Verification generated data must include standards');
assert.ok(verification.modal.dwr_url, 'Outfitter Verification generated data must include DWR modal URL');

const usage = readJson('canonical/canonical-field-usage-map.json', []);
const allowed = new Set(['mapped', 'intentionally_unmapped', 'deprecated', 'needs_owner_input', 'source_needed']);
assert.ok(usage.every(item => allowed.has(item.migration_status)), 'Every usage-map item must use an allowed migration_status');

const coverage = readJson('canonical/canonical-rebuild-coverage.json', {});
assert.ok(coverage.owner_questions.length > 0, 'Coverage must list owner questions');
assert.ok(coverage.regulatory_source_needed.length > 0, 'Coverage must list source-needed legal/regulatory items');

const promotion = promotionSafetyCheck();
assert.strictEqual(promotion.safe_to_promote, true, promotion.blockers.join('\n'));

console.log('canonical rebuild tests passed');
