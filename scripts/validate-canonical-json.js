const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const canonicalPath = path.join(repo, 'hunt-master-canonical-2026.json');
const schemaPath = path.join(repo, 'schemas', 'hunt-master-canonical-2026.schema.json');

function fail(message, details = undefined) {
  const err = new Error(message);
  err.details = details;
  throw err;
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail(`Invalid JSON: ${file}`, error.message);
  }
}

function typeOf(value) {
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  return typeof value;
}

function validateRequiredShape(data, schema, pointer = '$') {
  if (!schema || typeof schema !== 'object') return [];
  const errors = [];
  const expectedType = schema.type;
  if (expectedType) {
    const actual = typeOf(data);
    const ok = Array.isArray(expectedType) ? expectedType.includes(actual) : actual === expectedType;
    if (!ok) errors.push(`${pointer} expected ${expectedType} but got ${actual}`);
  }
  if (schema.required && data && typeof data === 'object' && !Array.isArray(data)) {
    for (const key of schema.required) {
      if (!Object.prototype.hasOwnProperty.call(data, key)) errors.push(`${pointer}.${key} is required`);
    }
  }
  if (schema.properties && data && typeof data === 'object' && !Array.isArray(data)) {
    for (const [key, childSchema] of Object.entries(schema.properties)) {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        errors.push(...validateRequiredShape(data[key], childSchema, `${pointer}.${key}`));
      }
    }
  }
  if (schema.items && Array.isArray(data)) {
    if (schema.minItems && data.length < schema.minItems) errors.push(`${pointer} has ${data.length} items; expected at least ${schema.minItems}`);
    data.forEach((item, index) => errors.push(...validateRequiredShape(item, schema.items, `${pointer}[${index}]`)));
  }
  return errors;
}

function walk(value, callback, pointer = '$', parentKey = '') {
  callback(value, pointer, parentKey);
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, callback, `${pointer}[${index}]`, String(index)));
  } else if (value && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      walk(child, callback, `${pointer}.${key}`, key);
    }
  }
}

function collectDuplicateIds(data) {
  const ids = new Map();
  const duplicates = [];
  walk(data, (value, pointer, key) => {
    if (key === 'id' && typeof value === 'string' && value.trim()) {
      if (ids.has(value)) duplicates.push({ id: value, first: ids.get(value), duplicate: pointer });
      else ids.set(value, pointer);
    }
  });
  return duplicates;
}

function collectTodoStrings(data) {
  const hits = [];
  walk(data, (value, pointer) => {
    if (typeof value === 'string' && /\bTODO\b/i.test(value)) hits.push({ pointer, value });
  });
  return hits;
}

function validateAppFacingHuntFields(data) {
  const required = ['id', 'hunt_code', 'huntCode', 'code', 'title', 'hunt_name', 'unitName', 'species', 'sex_type', 'weapon', 'hunt_type', 'season', 'permits_2026_res', 'permits_2026_nr', 'permits_2026_total', 'geometry', 'provenance'];
  const errors = [];
  if (!Array.isArray(data.hunt_catalog)) fail('hunt_catalog must be an array');
  data.hunt_catalog.forEach((hunt, index) => {
    for (const field of required) {
      if (!Object.prototype.hasOwnProperty.call(hunt, field)) errors.push(`hunt_catalog[${index}] missing ${field}`);
    }
    const code = String(hunt.hunt_code || '').trim().toUpperCase();
    if (!code) errors.push(`hunt_catalog[${index}] has blank hunt_code`);
    if (String(hunt.huntCode || '').trim().toUpperCase() !== code) errors.push(`${code} huntCode alias mismatch`);
    if (String(hunt.code || '').trim().toUpperCase() !== code) errors.push(`${code} code alias mismatch`);
  });
  return errors;
}

function validateNeedsOwnerMarkers(data) {
  const errors = [];
  walk(data, (value, pointer) => {
    if (value && typeof value === 'object' && !Array.isArray(value) && Object.prototype.hasOwnProperty.call(value, 'status')) {
      const looksLikeUnknownMarker = Object.prototype.hasOwnProperty.call(value, 'value') || Object.prototype.hasOwnProperty.call(value, 'question');
      if (looksLikeUnknownMarker && ['needs_owner_input', 'source_needed'].includes(value.status)) {
        if (!Object.prototype.hasOwnProperty.call(value, 'value')) errors.push(`${pointer} missing value`);
        if (value.value !== null) errors.push(`${pointer}.value should be null for ${value.status}`);
        if (!value.question) errors.push(`${pointer} missing question`);
      }
    }
  });
  return errors;
}

function runValidation() {
  const data = readJson(canonicalPath);
  const schema = readJson(schemaPath);
  const errors = [];
  errors.push(...validateRequiredShape(data, schema));
  errors.push(...validateAppFacingHuntFields(data));
  errors.push(...validateNeedsOwnerMarkers(data));
  const duplicateIds = collectDuplicateIds(data);
  const todoHits = collectTodoStrings(data);
  if (duplicateIds.length) errors.push(`Duplicate IDs: ${JSON.stringify(duplicateIds.slice(0, 20))}`);
  if (todoHits.length) errors.push(`Unresolved TODO strings: ${JSON.stringify(todoHits.slice(0, 20))}`);

  const requiredTop = schema.required || [];
  for (const key of requiredTop) {
    if (!Object.prototype.hasOwnProperty.call(data, key)) errors.push(`Missing top-level section ${key}`);
  }

  if (errors.length) {
    console.error(JSON.stringify({ ok: false, errors }, null, 2));
    process.exit(1);
  }

  const summary = {
    ok: true,
    canonical: path.relative(repo, canonicalPath),
    schema: path.relative(repo, schemaPath),
    top_level_sections: requiredTop.length,
    hunt_catalog_count: data.hunt_catalog.length,
    species_count: data.species.length,
    hunt_units_count: data.hunt_units.length,
    seasons_count: data.seasons.length,
    packages_count: data.packages.length,
    outfitter_count: Array.isArray(data.outfitters) ? data.outfitters.length : 0,
  };
  console.log(JSON.stringify(summary, null, 2));
}

if (require.main === module) runValidation();

module.exports = {
  readJson,
  validateRequiredShape,
  validateAppFacingHuntFields,
  validateNeedsOwnerMarkers,
  collectDuplicateIds,
  collectTodoStrings,
  runValidation,
};

