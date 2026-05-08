const fs = require('fs');
const { abs, sourceFiles, sourceSummary, writeJson } = require('./inventory');
const { sourceNeeded, ownerQuestions } = require('./generators');

function mdTable(rows, columns) {
  const clean = value => String(value ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
  return [
    `| ${columns.map(column => column.label).join(' | ')} |`,
    `| ${columns.map(() => '---').join(' | ')} |`,
    ...rows.map(row => `| ${columns.map(column => clean(typeof column.value === 'function' ? column.value(row) : row[column.value])).join(' | ')} |`),
  ].join('\n');
}

function writeCoverage(usage, validationStatus = {}, now = new Date().toISOString()) {
  const sourceSummaries = sourceFiles().map(sourceSummary);
  const mapped = usage.filter(item => item.migration_status === 'mapped');
  const unmapped = usage
    .filter(item => item.migration_status === 'intentionally_unmapped')
    .map(item => ({ ...item, reason: 'Observed in source data but not currently consumed by the four live tools.' }));
  const deprecated = usage.filter(item => item.migration_status === 'deprecated');

  const coverage = {
    metadata: { generated_at: now, generator: 'scripts/build-canonical-rebuild.js', scope: ['Hunt Planner', 'Hunt Research', 'Hard Copies', 'Outfitter Verification'] },
    source_files_scanned: sourceSummaries,
    fields_discovered: usage,
    fields_mapped: mapped,
    fields_unmapped: unmapped,
    deprecated_fields: deprecated,
    owner_questions: ownerQuestions,
    regulatory_source_needed: sourceNeeded,
    validation_status: {
      generated: true,
      validate_command: 'npm run validate:canonical',
      page_generation_command: 'npm run generate:page-data',
      contract_diff_command: 'npm run compare:runtime-contracts',
      promotion_safety_command: 'npm run promotion:safety',
      test_command: 'npm run test',
      build_command: 'npm run build',
      ...validationStatus,
    },
  };
  writeJson('canonical/canonical-rebuild-coverage.json', coverage);

  fs.writeFileSync(abs('docs/canonical-field-usage-map.md'), `# Canonical Field Usage Map

Generated: ${now}

This map is bottom-up from the four live UOGA tools. Every discovered field is either mapped into the scoped canonical package or explicitly marked intentionally unmapped.

${mdTable(usage, [
  { label: 'Field', value: 'field_name' },
  { label: 'Current Source', value: 'current_source_file' },
  { label: 'Consumed By', value: item => item.consumed_by_files.join(', ') || 'not consumed' },
  { label: 'Page/Tool', value: item => item.page_tool_using_it.join(', ') || 'none' },
  { label: 'Req/Opt', value: 'required_or_optional' },
  { label: 'Type', value: 'data_type_observed' },
  { label: 'Examples', value: item => item.example_values.join('; ') },
  { label: 'Fallback', value: 'fallback_behavior' },
  { label: 'Canonical Target', value: 'canonical_target_path' },
  { label: 'Status', value: 'migration_status' },
])}
`, 'utf8');

  fs.writeFileSync(abs('docs/canonical-rebuild-coverage.md'), `# Canonical Rebuild Coverage

Generated: ${now}

## Scope

- Hunt Planner
- Hunt Research
- Hard Copies
- Outfitter Verification

## Source Files Scanned

${mdTable(sourceSummaries, [
  { label: 'File', value: 'file' },
  { label: 'Kind', value: 'kind' },
  { label: 'Rows/Bytes', value: item => item.row_count ?? item.byte_count ?? '' },
  { label: 'Fields', value: item => (item.fields || []).slice(0, 24).join(', ') },
])}

## Fields Discovered

- Total discovered field entries: ${usage.length}
- Mapped: ${mapped.length}
- Intentionally unmapped: ${unmapped.length}
- Deprecated: ${deprecated.length}

## Fields Mapped

See [canonical-field-usage-map.md](./canonical-field-usage-map.md) and [canonical/canonical-field-usage-map.json](../canonical/canonical-field-usage-map.json).

## Fields Intentionally Unmapped

${unmapped.length ? mdTable(unmapped, [
  { label: 'Field', value: 'field_name' },
  { label: 'Source', value: 'current_source_file' },
  { label: 'Reason', value: 'reason' },
]) : 'None.'}

## Deprecated Fields

${deprecated.length ? mdTable(deprecated, [{ label: 'Field', value: 'field_name' }, { label: 'Source', value: 'current_source_file' }]) : 'None.'}

## Owner Questions

${mdTable(ownerQuestions, [{ label: 'ID', value: 'id' }, { label: 'Question', value: 'question' }, { label: 'Status', value: 'status' }])}

## Source-Needed Regulation/Legal Items

${mdTable(sourceNeeded, [{ label: 'ID', value: 'id' }, { label: 'Item', value: 'item' }, { label: 'URL', value: 'source_url' }, { label: 'Status', value: 'status' }])}

## Generated Page Data

- generated/pages/hunt-planner.json
- generated/pages/hunt-research.json
- generated/pages/hard-copies.json
- generated/pages/outfitter-verification.json

## Validation Commands

- npm run generate:page-data
- npm run validate:canonical
- npm run compare:runtime-contracts
- npm run promotion:safety
- npm run test
- npm run build

## Test Results

${validationStatus.test_result || 'Pending until validation commands are run after generation.'}
`, 'utf8');

  return coverage;
}

module.exports = { writeCoverage };
