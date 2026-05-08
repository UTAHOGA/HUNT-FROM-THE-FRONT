const { writeJson } = require('./inventory');

const SCHEMAS = [
  ['shared', 'Shared 2026 Canonical Schema', ['metadata', 'versioning', 'routes', 'navigation', 'assets', 'provenance']],
  ['hunt-planner', 'Hunt Planner 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'filters', 'map_modes', 'land_layers', 'hunt_catalog', 'boundaries']],
  ['hunt-research', 'Hunt Research 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'input_controls', 'odds_selection_policy', 'datasets']],
  ['hard-copies', 'Hard Copies 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'manifest_url', 'group_labels', 'filters', 'library']],
  ['outfitter-verification', 'Outfitter Verification 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'designation_levels', 'standards', 'modal', 'outfitters']],
];

function buildSchemas() {
  for (const [name, title, required] of SCHEMAS) {
    writeJson(`schemas/canonical/${name}.schema.json`, {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      title,
      type: 'object',
      required,
      additionalProperties: true,
      properties: Object.fromEntries(required.map(key => [key, {}])),
    });
  }
  return SCHEMAS.map(([name]) => `schemas/canonical/${name}.schema.json`);
}

module.exports = { buildSchemas, SCHEMAS };
