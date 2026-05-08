const { writeJson } = require('./inventory');

const SCHEMAS = [
  ['shared', 'Shared 2026 Canonical Schema', ['metadata', 'versioning', 'routes', 'navigation', 'assets', 'provenance'], 'schemas/shared.schema.json'],
  ['hunt-planner', 'Hunt Planner 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'filters', 'map_modes', 'land_layers', 'hunt_catalog', 'boundaries'], 'schemas/hunt-planner.schema.json'],
  ['hunt-research', 'Hunt Research 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'input_controls', 'odds_selection_policy', 'datasets'], 'schemas/hunt-research.schema.json'],
  ['hard-copies', 'Hard Copies 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'manifest_url', 'group_labels', 'filters', 'library'], 'schemas/hard-copies.schema.json'],
  ['outfitter-verification', 'Outfitter Verification 2026 Canonical Schema', ['metadata', 'provenance', 'route', 'designation_levels', 'standards', 'modal', 'outfitters'], 'schemas/outfitter-verification.schema.json'],
];

function buildSchemas() {
  for (const [name, title, required, rootPath] of SCHEMAS) {
    const schema = {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      title,
      type: 'object',
      required,
      additionalProperties: true,
      properties: Object.fromEntries(required.map(key => [key, {}])),
    };
    writeJson(rootPath, schema);
    // Keep legacy mirror path for backward compatibility with existing tooling.
    writeJson(`schemas/canonical/${name}.schema.json`, schema);
  }
  return SCHEMAS.map(([, , , rootPath]) => rootPath);
}

module.exports = { buildSchemas, SCHEMAS };
