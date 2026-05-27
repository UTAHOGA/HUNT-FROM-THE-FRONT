const fs = require('fs');
const path = require('path');
const assert = require('assert');

const root = path.resolve(__dirname, '..');
const indexHtml = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const appJs = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const styleCss = fs.readFileSync(path.join(root, 'style.css'), 'utf8');

const orderedControls = [
  'searchInput',
  'speciesFilter',
  'sexFilter',
  'huntTypeFilter',
  'weaponFilter',
  'huntCategoryFilter',
  'unitFilter',
];

let lastIndex = -1;
for (const controlId of orderedControls) {
  const idx = indexHtml.indexOf(`id="${controlId}"`);
  assert(idx > lastIndex, `${controlId} should appear after the previous selection-matrix control`);
  lastIndex = idx;
}

for (const stepClass of [
  'matrix-step--sex is-collapsed',
  'matrix-step--hunt-type is-collapsed',
  'matrix-step--weapon is-collapsed',
  'matrix-step--hunt-class is-collapsed',
  'matrix-step--unit is-collapsed',
]) {
  assert(indexHtml.includes(stepClass), `${stepClass} should be collapsed on page entry`);
}

assert(appJs.includes('function syncProgressiveSelectionMatrix()'), 'progressive matrix sync function should exist');
assert(appJs.includes('resetDownstreamMatrixControls(changedId)'), 'upstream filter changes should reset downstream controls');
assert(appJs.includes('getNextVisibleMatrixControlId(sequence, idx)'), 'auto-advance should skip collapsed controls');
assert(appJs.includes('function saveHuntAndOpenResearch('), 'selected hunts should save to Backpack before opening Hunt Research');
assert(appJs.includes('data-hunt-research-key'), 'matching hunt cards should expose a direct save-and-research action');
assert(appJs.includes('Research This Hunt'), 'selected hunt panel should expose the Research This Hunt action');
assert(styleCss.includes('.matrix-step.is-collapsed'), 'collapsed matrix-step CSS should exist');

console.log('selection matrix progressive behavior guard passed');
