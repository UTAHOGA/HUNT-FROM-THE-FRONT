const { validateCanonical } = require('../lib/canonical/validators');

const result = validateCanonical();
console.log(JSON.stringify(result, null, 2));

if (!result.ok) process.exit(1);
