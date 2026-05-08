const { buildCanonical, writePageData } = require('../lib/canonical/generators');

const pkg = buildCanonical();
const pages = writePageData(pkg);

console.log(JSON.stringify({
  ok: true,
  generated_pages: Object.keys(pages).map(key => `generated/pages/${key}.json`),
}, null, 2));
