const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const AUDIT_JSON = 'processed_data/canonical_data_drop_audit_20260508.json';
const OUT_JSON = 'canonical/data-drop-audit-report.json';
const OUT_MD = 'docs/data-drop-audit-report.md';

const VALID_CLASSES = new Set(['SAFE_DERIVED_DROP', 'INTENTIONAL_LEGACY_DROP', 'PROMOTION_BLOCKER']);

function abs(file) {
  return path.join(REPO, file);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(abs(file), 'utf8'));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(abs(file)), { recursive: true });
  fs.writeFileSync(abs(file), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeText(file, value) {
  fs.mkdirSync(path.dirname(abs(file)), { recursive: true });
  fs.writeFileSync(abs(file), value, 'utf8');
}

function runtimeConsumersForField(field) {
  const files = ['index.html', 'research.html', 'hard-copy.html', 'verify.html', 'config.js', 'app.js', 'data.js', 'boundary-resolver.js', 'hunt-research.js', 'ui.js', 'header-layout.js'];
  const escaped = String(field).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`(^|[^A-Za-z0-9_])${escaped}([^A-Za-z0-9_]|$)`);
  return files.filter(file => fs.existsSync(abs(file)) && pattern.test(fs.readFileSync(abs(file), 'utf8')));
}

function researchCanonical() {
  return JSON.parse(fs.readFileSync(abs('canonical/hunt-research-2026.json'), 'utf8'));
}

function fieldPreservedInResearchCanonical(field, sourceFile) {
  const research = researchCanonical();
  if ((research.hunt_quality_fields || []).includes(field)) return true;
  if (!sourceFile.includes('hunt_master_enriched.csv')) return false;
  return !!(research.datasets
    && research.datasets.hunt_master_enriched
    && Array.isArray(research.datasets.hunt_master_enriched.fields)
    && research.datasets.hunt_master_enriched.fields.includes(field));
}

function huntCodePreservedInResearchCanonical(code, sourceFile) {
  if (!sourceFile.includes('hunt_master_enriched.csv')) return false;
  const research = researchCanonical();
  return !!(research.datasets
    && research.datasets.hunt_master_enriched
    && Array.isArray(research.datasets.hunt_master_enriched.unique_hunt_codes)
    && research.datasets.hunt_master_enriched.unique_hunt_codes.includes(code));
}

function classifyMissingHuntCode(sourceFile, code) {
  if (sourceFile.includes('DATABASE.csv') || sourceFile.includes('foundation.json')) {
    return {
      classification: 'PROMOTION_BLOCKER',
      reason: 'Primary/source canonical hunt code would be missing from the generated canonical.',
      runtime_impact: 'Would remove a visitor-facing hunt from planner filtering/search/mapping.',
      promotion_blocker: true,
    };
  }
  if (sourceFile.includes('hunt_master_enriched.csv')) {
    if (huntCodePreservedInResearchCanonical(code, sourceFile)) {
      return {
        classification: 'SAFE_DERIVED_DROP',
        reason: 'This code is absent from the Planner hunt_catalog but is preserved in the Hunt Research canonical dataset contract and live processed CSV.',
        runtime_impact: 'No Planner impact. Hunt Research keeps the code through processed_data/hunt_master_enriched.csv and canonical/hunt-research-2026.json dataset metadata.',
        promotion_blocker: false,
      };
    }
    return {
      classification: 'PROMOTION_BLOCKER',
      reason: 'This hunt_code exists in the live Hunt Research metadata CSV. Even if absent from DATABASE.csv, the research runtime can still reference it.',
      runtime_impact: 'Could make an existing research row fail to resolve metadata or appear unsupported.',
      promotion_blocker: true,
    };
  }
  return {
    classification: 'INTENTIONAL_LEGACY_DROP',
    reason: 'This hunt_code appears only in an older built artifact and is absent from the current DATABASE.csv primary truth file.',
    runtime_impact: 'No current runtime source list points to this built CSV; exclusion does not affect live planner/research pages.',
    promotion_blocker: false,
  };
}

function classifyMissingField(sourceFile, field) {
  if (fieldPreservedInResearchCanonical(field, sourceFile)) {
    return {
      classification: 'SAFE_DERIVED_DROP',
      reason: 'Field is absent from the Planner hunt_catalog but preserved in canonical/hunt-research-2026.json under the Hunt Research dataset contract.',
      runtime_impact: 'No Planner impact. Hunt Research continues to load the field from its processed CSV and the canonical package documents the field.',
      promotion_blocker: false,
    };
  }
  const consumers = runtimeConsumersForField(field);
  if (consumers.length) {
    return {
      classification: 'PROMOTION_BLOCKER',
      reason: `Field is referenced by live runtime files: ${consumers.join(', ')}.`,
      runtime_impact: 'Field must be preserved, aliased, or supplied through the generated page data before promotion.',
      promotion_blocker: true,
    };
  }
  if (sourceFile.includes('hunt_master_enriched.csv')) {
    return {
      classification: 'SAFE_DERIVED_DROP',
      reason: 'Field belongs to the Hunt Research processed/materialized CSV dataset, not the Hunt Planner hunt_catalog. The scoped research canonical preserves the dataset field contract rather than duplicating every processed row into planner canonical.',
      runtime_impact: 'No planner impact. Research still loads the processed CSV directly and its schema is represented under canonical/hunt-research-2026.json.',
      promotion_blocker: false,
    };
  }
  return {
    classification: 'INTENTIONAL_LEGACY_DROP',
    reason: 'Field appears only in an older/derived built artifact and is not referenced by the live runtime.',
    runtime_impact: 'No current visitor-facing runtime impact.',
    promotion_blocker: false,
  };
}

function classifyComparison(comparison) {
  const sourceFile = comparison.source_file;
  const missingHuntCodes = comparison.missing_in_target.map(code => ({
    source_file: sourceFile,
    missing_hunt_codes: [code],
    missing_fields: [],
    ...classifyMissingHuntCode(sourceFile, code),
  }));
  const meaningfulByField = new Map((comparison.meaningful_source_only_fields || []).map(item => [item.field, item.examples || []]));
  const missingFields = comparison.source_only_fields.map(field => ({
    source_file: sourceFile,
    missing_hunt_codes: [],
    missing_fields: [field],
    examples: meaningfulByField.get(field) || [],
    ...classifyMissingField(sourceFile, field),
  }));
  return [...missingHuntCodes, ...missingFields].map(item => {
    if (!VALID_CLASSES.has(item.classification)) throw new Error(`Invalid classification ${item.classification}`);
    return item;
  });
}

function expectationLabel(comparison, classifications) {
  if (!comparison.missing_in_target_count && !comparison.meaningful_source_only_fields.length) return 'expected';
  if (classifications.some(item => item.promotion_blocker)) return 'blocking';
  if (classifications.some(item => item.classification === 'SAFE_DERIVED_DROP')) return 'derived';
  return 'legacy';
}

function markdown(report) {
  const lines = [];
  lines.push('# Data Drop Audit Report');
  lines.push('');
  lines.push(`Generated: ${report.generated_at}`);
  lines.push('');
  lines.push('## Promotion Rule Result');
  lines.push('');
  lines.push(`- DATABASE.csv green light: ${report.database_primary_green_light ? 'YES' : 'NO'}`);
  lines.push(`- Promotion blockers found: ${report.promotion_blockers.length}`);
  lines.push('');
  lines.push('## Direct Comparison Summary');
  lines.push('');
  lines.push('| Source file | Row count | Unique hunt codes | Missing in canonical | Extra in canonical | Source-only fields | Target-only fields | Changed shared fields | Difference type |');
  lines.push('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |');
  for (const item of report.direct_comparisons) {
    lines.push(`| ${item.source_file} | ${item.row_count} | ${item.unique_hunt_code_count} | ${item.hunt_codes_present_in_source_missing_from_new_canonical.length} | ${item.hunt_codes_present_in_new_canonical_missing_from_source.length} | ${item.fields_present_in_source_missing_from_new_canonical.length} | ${item.fields_present_in_new_canonical_missing_from_source.length} | ${item.changed_values_for_shared_fields.length} | ${item.differences_are} |`);
  }
  lines.push('');
  lines.push('## Classified Missing Items');
  lines.push('');
  if (!report.classified_missing_items.length) {
    lines.push('No missing hunt codes or missing fields were found.');
  } else {
    lines.push('| Source | Hunt codes | Fields | Classification | Runtime impact | Promotion blocker | Reason |');
    lines.push('| --- | --- | --- | --- | --- | --- | --- |');
    for (const item of report.classified_missing_items) {
      lines.push(`| ${item.source_file} | ${(item.missing_hunt_codes || []).join(', ') || ''} | ${(item.missing_fields || []).join(', ') || ''} | ${item.classification} | ${item.runtime_impact} | ${item.promotion_blocker ? 'true' : 'false'} | ${item.reason} |`);
    }
  }
  lines.push('');
  lines.push('## Promotion Blockers');
  lines.push('');
  if (!report.promotion_blockers.length) {
    lines.push('None.');
  } else {
    for (const blocker of report.promotion_blockers) {
      lines.push(`- ${blocker.source_file}: ${blocker.missing_hunt_codes.join(', ') || blocker.missing_fields.join(', ')} - ${blocker.reason}`);
    }
  }
  return `${lines.join('\n')}\n`;
}

const audit = readJson(AUDIT_JSON);
const canonicalComparisons = audit.comparisons.filter(item => item.target === 'canonical/hunt-planner-2026.json hunt_catalog');
const classified = [];
const direct = [];

for (const comparison of canonicalComparisons) {
  const comparisonClassifications = classifyComparison(comparison);
  classified.push(...comparisonClassifications);
  direct.push({
    source_file: comparison.source_file,
    target_file: comparison.target_file,
    row_count: comparison.source_rows,
    unique_hunt_code_count: comparison.source_unique_codes,
    new_canonical_row_count: comparison.target_rows,
    new_canonical_unique_hunt_code_count: comparison.target_unique_codes,
    hunt_codes_present_in_source_missing_from_new_canonical: comparison.missing_in_target,
    hunt_codes_present_in_new_canonical_missing_from_source: comparison.extra_in_target,
    fields_present_in_source_missing_from_new_canonical: comparison.source_only_fields,
    fields_present_in_new_canonical_missing_from_source: comparison.target_only_fields,
    changed_values_for_shared_fields: comparison.mismatched_shared_fields,
    differences_are: expectationLabel(comparison, comparisonClassifications),
  });
}

const databaseComparison = direct.find(item => item.source_file.includes('DATABASE.csv'));
const report = {
  generated_at: new Date().toISOString(),
  compared_new_canonical: 'canonical/hunt-planner-2026.json hunt_catalog',
  database_primary_green_light: !!databaseComparison
    && databaseComparison.hunt_codes_present_in_source_missing_from_new_canonical.length === 0
    && databaseComparison.fields_present_in_source_missing_from_new_canonical.length === 0,
  direct_comparisons: direct,
  classified_missing_items: classified,
  promotion_blockers: classified.filter(item => item.promotion_blocker),
};

writeJson(OUT_JSON, report);
writeText(OUT_MD, markdown(report));

console.log(JSON.stringify({
  ok: true,
  report_json: OUT_JSON,
  report_md: OUT_MD,
  database_primary_green_light: report.database_primary_green_light,
  classified_missing_items: report.classified_missing_items.length,
  promotion_blockers: report.promotion_blockers.length,
}, null, 2));
