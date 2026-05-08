const fs = require('fs');
const { abs, readJson } = require('./inventory');
const { SCHEMAS } = require('./schema-builder');
const { compareRuntimeContracts, duplicateIds, localAssetExists } = require('./diffing');

const canonicalFiles = [
  ['canonical/shared-2026.json', 'shared'],
  ['canonical/hunt-planner-2026.json', 'hunt-planner'],
  ['canonical/hunt-research-2026.json', 'hunt-research'],
  ['canonical/hard-copies-2026.json', 'hard-copies'],
  ['canonical/outfitter-verification-2026.json', 'outfitter-verification'],
];

function hasTodo(value) {
  return JSON.stringify(value).includes('TODO');
}

function validateRequired(schemaName, data) {
  const schema = SCHEMAS.find(([name]) => name === schemaName);
  if (!schema) return [];
  const required = schema[2];
  return required.filter(field => data[field] === undefined).map(field => `Missing required field ${schemaName}.${field}`);
}

function validateCanonical() {
  const errors = [];
  const warnings = [];

  for (const [file, schemaName] of canonicalFiles) {
    if (!fs.existsSync(abs(file))) {
      errors.push(`Missing ${file}`);
      continue;
    }
    const data = readJson(file, null);
    errors.push(...validateRequired(schemaName, data).map(message => `${file}: ${message}`));
    if (hasTodo(data)) errors.push(`${file}: contains unresolved TODO text`);
  }

  for (const file of [
    'generated/pages/hunt-planner.json',
    'generated/pages/hunt-research.json',
    'generated/pages/hard-copies.json',
    'generated/pages/outfitter-verification.json',
    'canonical/four-page-canonical-coverage.json',
    'docs/four-page-canonical-coverage.md',
    'canonical/canonical-field-usage-map.json',
    'canonical/canonical-rebuild-coverage.json',
    'docs/canonical-field-usage-map.md',
    'docs/canonical-rebuild-coverage.md',
  ]) {
    if (!fs.existsSync(abs(file))) errors.push(`Missing ${file}`);
  }

  const shared = readJson('canonical/shared-2026.json', {});
  errors.push(...duplicateIds(shared.routes || []).map(id => `Duplicate route id ${id}`));
  errors.push(...duplicateIds(shared.assets || []).map(id => `Duplicate asset id ${id}`));
  for (const asset of shared.assets || []) {
    if (!localAssetExists(asset.path)) errors.push(`Missing asset ${asset.path}`);
  }
  for (const nav of shared.navigation || []) {
    if (!nav.href || !/^(#|\.\/|https?:\/\/)/.test(nav.href)) errors.push(`Invalid nav href ${nav.href}`);
  }

  const planner = readJson('generated/pages/hunt-planner.json', {});
  const huntCodes = new Set();
  for (const hunt of planner.hunt_catalog || []) {
    const code = String(hunt.hunt_code || hunt.huntCode || hunt.code || '').trim().toUpperCase();
    if (!code) errors.push('Planner hunt catalog contains row without hunt_code');
    if (huntCodes.has(code)) errors.push(`Duplicate hunt_code in generated planner data: ${code}`);
    huntCodes.add(code);
  }
  for (const control of ['speciesFilter', 'sexFilter', 'huntTypeFilter', 'huntCategoryFilter', 'weaponFilter', 'unitFilter']) {
    if (!(planner.filters || []).some(filter => filter.id === control)) errors.push(`Missing planner filter ${control}`);
  }

  const research = readJson('generated/pages/hunt-research.json', {});
  for (const field of ['display_odds_pct', 'p_draw_mean', 'guaranteed_probability']) {
    if (!(research.modeled_fields || []).includes(field)) errors.push(`Missing research modeled field ${field}`);
  }
  for (const field of ['odds_2026_projected', 'max_pool_projection_2026', 'random_draw_odds_2026', 'status']) {
    if (!(research.legacy_fields || []).includes(field)) errors.push(`Missing research legacy field ${field}`);
  }
  const policy = (research.odds_selection_policy || []).join(' ');
  if (!/Never treat status MAX POOL/.test(policy)) errors.push('Research policy does not preserve MAX POOL safety rule');

  const hardCopies = readJson('generated/pages/hard-copies.json', {});
  for (const item of (hardCopies.library && hardCopies.library.items || []).slice(0, 10000)) {
    if (!item.title || !item.href || !item.type || !item.group) errors.push(`Hard-copy item missing required display/download fields: ${JSON.stringify(item).slice(0, 160)}`);
    if (!/^(#|\.\/|https?:\/\/)/.test(item.href)) errors.push(`Invalid hard-copy href ${item.href}`);
    if (!localAssetExists(item.href)) warnings.push(`Referenced hard-copy file not found locally: ${item.href}`);
  }

  const verification = readJson('generated/pages/outfitter-verification.json', {});
  if (!(verification.standards || []).length) errors.push('Outfitter verification standards are missing');
  if (!verification.modal || !verification.modal.dwr_url) errors.push('Outfitter DWR modal URL is missing');

  const coverage = readJson('canonical/four-page-canonical-coverage.json', readJson('canonical/canonical-rebuild-coverage.json', {}));
  if (!(coverage.owner_questions || []).length) errors.push('Coverage missing owner_questions list');
  if (!(coverage.regulatory_source_needed || []).length) errors.push('Coverage missing regulatory_source_needed list');
  const usage = readJson('canonical/canonical-field-usage-map.json', []);
  const allowed = new Set(['mapped', 'intentionally_unmapped', 'deprecated', 'needs_owner_input', 'source_needed']);
  for (const item of usage) {
    if (!allowed.has(item.migration_status)) errors.push(`Invalid migration_status ${item.migration_status} for ${item.field_name}`);
  }

  const contract = compareRuntimeContracts();
  if (!contract.ok) errors.push(...contract.findings.filter(item => item.level === 'error').map(item => item.message));

  return { ok: errors.length === 0, errors, warnings, contract };
}

module.exports = { validateCanonical };
