const assert = require('assert');
const path = require('path');
const {
  readJson,
  validateRequiredShape,
  validateAppFacingHuntFields,
  validateNeedsOwnerMarkers,
  collectDuplicateIds,
  collectTodoStrings,
} = require('../scripts/validate-canonical-json');

const repo = path.resolve(__dirname, '..');
const canonical = readJson(path.join(repo, 'hunt-master-canonical-2026.json'));
const schema = readJson(path.join(repo, 'schemas', 'hunt-master-canonical-2026.schema.json'));

assert.doesNotThrow(() => JSON.stringify(canonical), 'canonical JSON should parse and stringify');
assert.deepStrictEqual(validateRequiredShape(canonical, schema), [], 'canonical must comply with required schema shape');
assert.deepStrictEqual(validateAppFacingHuntFields(canonical), [], 'all hunt rows must include app-facing fields');
assert.deepStrictEqual(validateNeedsOwnerMarkers(canonical), [], 'needs_owner_input/source_needed markers must be complete');
assert.deepStrictEqual(collectDuplicateIds(canonical), [], 'all IDs must be unique');
assert.deepStrictEqual(collectTodoStrings(canonical), [], 'canonical must not contain TODO strings');

for (const section of schema.required) {
  assert.ok(Object.prototype.hasOwnProperty.call(canonical, section), `missing top-level section ${section}`);
}

assert.ok(Array.isArray(canonical.hunt_catalog) && canonical.hunt_catalog.length >= 1394, 'hunt_catalog should include full database candidate coverage');
assert.ok(Array.isArray(canonical.species) && canonical.species.length >= 10, 'species list should be populated');
assert.ok(Array.isArray(canonical.hunt_units) && canonical.hunt_units.length > 0, 'hunt_units should be populated');
assert.ok(Array.isArray(canonical.seasons) && canonical.seasons.length === canonical.hunt_catalog.length, 'season records should line up with hunt rows');

console.log(JSON.stringify({ ok: true, tests: 10, hunt_catalog_count: canonical.hunt_catalog.length }, null, 2));
