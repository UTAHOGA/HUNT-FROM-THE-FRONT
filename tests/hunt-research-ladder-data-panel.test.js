const fs = require('fs');
const path = require('path');
const assert = require('assert');

const root = path.resolve(__dirname, '..');
const researchHtml = fs.readFileSync(path.join(root, 'research.html'), 'utf8');
const huntResearchJs = fs.readFileSync(path.join(root, 'hunt-research.js'), 'utf8');

assert(researchHtml.includes('id="pointLadderAccordion"'), 'point ladder accordion should have a stable id');
assert(researchHtml.includes('Hunt Data Snapshot'), 'modal should be decision-focused, not source-focused');
assert(researchHtml.includes('source-plain-note'), 'modal should include plain-language context styling');

assert(huntResearchJs.includes('pointLadderAccordion: document.getElementById'), 'ladder accordion should be wired in JS');
assert(huntResearchJs.includes('function setupLadderAutoOpen()'), 'ladder should auto-open setup function');
assert(huntResearchJs.includes('IntersectionObserver'), 'ladder should open when scrolled into view');
assert(huntResearchJs.includes("addEventListener('mouseenter'"), 'ladder should open on mouse entry');
assert(huntResearchJs.includes('function buildDecisionBoxes('), 'hunt data popup should render decision boxes');
assert(huntResearchJs.includes('Can You Catch The Train?'), 'hunt data popup should explain catch-up status');
assert(huntResearchJs.includes('Plain-English Formula'), 'hunt data popup should explain algorithm plainly');
assert(huntResearchJs.includes('Harvest Snapshot'), 'hunt data popup should show mapped harvest data');
assert(huntResearchJs.includes('buildDecisionBoxes(meta, row, referenceRow, filters)'), 'modal should use decision boxes');

console.log('hunt research ladder/data panel guard passed');
