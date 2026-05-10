const { spawnSync } = require('child_process');

const steps = [
  { name: 'sync:permits-2026', cmd: 'npm.cmd run sync:permits-2026' },
  { name: 'verify:permits-2026', cmd: 'npm.cmd run verify:permits-2026' },
  { name: 'validate:canonical', cmd: 'npm.cmd run validate:canonical' },
  { name: 'compare:runtime-contracts', cmd: 'npm.cmd run compare:runtime-contracts' },
  { name: 'promotion:safety', cmd: 'npm.cmd run promotion:safety' },
  { name: 'test', cmd: 'npm.cmd test' },
  { name: 'build', cmd: 'npm.cmd run build' },
];

function runStep(step) {
  console.log(`\n=== ${step.name} ===`);
  const result = spawnSync(step.cmd, {
    stdio: 'inherit',
    shell: true,
  });
  if (result.error) {
    console.error(`Step failed: ${step.name}`);
    console.error(result.error.message);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`Step exited non-zero: ${step.name} (code ${result.status})`);
    process.exit(result.status || 1);
  }
}

for (const step of steps) {
  runStep(step);
}

console.log('\nHard-data integrity pipeline completed successfully.');
console.log('Primary reports:');
console.log('- canonical/permit-allocation-2026-integrity-report.json');
console.log('- docs/permit-allocation-2026-integrity-report.md');
console.log('- canonical/runtime-preservation-matrix.json');
console.log('- docs/runtime-preservation-matrix.md');
