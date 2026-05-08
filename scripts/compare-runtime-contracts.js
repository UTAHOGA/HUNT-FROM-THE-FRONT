const { compareRuntimeContracts } = require('../lib/canonical/diffing');

const result = compareRuntimeContracts();
console.log(JSON.stringify(result, null, 2));

if (!result.ok) process.exit(1);
