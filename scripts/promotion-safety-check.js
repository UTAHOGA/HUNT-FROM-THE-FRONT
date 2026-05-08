const { promotionSafetyCheck } = require('../lib/canonical/promotion-safety');

const result = promotionSafetyCheck();
console.log(JSON.stringify(result, null, 2));

if (!result.safe_to_promote) process.exit(1);
