const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const OUT_JSON = 'processed_data/canonical_data_drop_audit_20260508.json';
const OUT_MD = 'processed_data/canonical_data_drop_audit_20260508.md';

const SOURCES = [
  {
    id: 'database_csv',
    label: 'DATABASE.csv',
    file: 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv',
    kind: 'csv',
  },
  {
    id: 'built_csv',
    label: 'hunt_master_canonical_2026_built.csv',
    file: 'pipeline/RAW/hunt_unit_database/2026/csv/hunt_master_canonical_2026_built.csv',
    kind: 'csv',
  },
  {
    id: 'hunt_master_enriched_csv',
    label: 'processed_data/hunt_master_enriched.csv',
    file: 'processed_data/hunt_master_enriched.csv',
    kind: 'csv',
  },
  {
    id: 'foundation_json',
    label: 'hunt-master-canonical-2026-foundation.json',
    file: 'data/hunt-master-canonical-2026-foundation.json',
    kind: 'json-array',
  },
];

const TARGETS = [
  {
    id: 'canonical_hunt_planner',
    label: 'canonical/hunt-planner-2026.json hunt_catalog',
    file: 'canonical/hunt-planner-2026.json',
    kind: 'json-path',
    path: ['hunt_catalog'],
  },
  {
    id: 'generated_hunt_planner',
    label: 'generated/pages/hunt-planner.json hunt_catalog',
    file: 'generated/pages/hunt-planner.json',
    kind: 'json-path',
    path: ['hunt_catalog'],
  },
  {
    id: 'root_hunt_master_canonical',
    label: 'hunt-master-canonical-2026.json hunt_catalog',
    file: 'hunt-master-canonical-2026.json',
    kind: 'json-path',
    path: ['hunt_catalog'],
    optional: true,
  },
];

function abs(file) {
  return path.join(REPO, file);
}

function readText(file) {
  return fs.existsSync(abs(file)) ? fs.readFileSync(abs(file), 'utf8').replace(/^\uFEFF/, '') : '';
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n') {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else if (ch !== '\r') {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  if (!rows.length) return [];
  const headers = rows.shift().map(v => String(v || '').trim());
  return rows
    .filter(values => values.some(v => String(v || '').trim()))
    .map(values => Object.fromEntries(headers.map((header, index) => [header, values[index] || '']).filter(([header]) => header)));
}

function getByPath(value, parts) {
  return parts.reduce((current, part) => current && current[part], value);
}

function rowsFor(spec) {
  if (!fs.existsSync(abs(spec.file))) {
    if (spec.optional) return [];
    throw new Error(`Missing required audit file: ${spec.file}`);
  }
  if (spec.kind === 'csv') return parseCsv(readText(spec.file));
  const json = JSON.parse(readText(spec.file));
  if (spec.kind === 'json-array') return Array.isArray(json) ? json : [];
  if (spec.kind === 'json-path') return getByPath(json, spec.path) || [];
  return [];
}

function codeOf(row) {
  return String(row.hunt_code || row.huntCode || row.code || row.HuntCode || row['Hunt Code'] || row.hunt_number || '').trim().toUpperCase();
}

function fieldSet(rows) {
  const fields = new Set();
  rows.slice(0, 10000).forEach(row => {
    if (row && typeof row === 'object') Object.keys(row).forEach(key => fields.add(key));
  });
  return fields;
}

function firstMeaningful(row, field) {
  const value = row && row[field];
  if (Array.isArray(value)) return value.length ? value.slice(0, 4).join(';') : '';
  if (value && typeof value === 'object') return JSON.stringify(value).slice(0, 100);
  return String(value ?? '').trim();
}

function indexRows(rows) {
  const index = new Map();
  const duplicates = new Map();
  for (const row of rows) {
    const code = codeOf(row);
    if (!code) continue;
    if (index.has(code)) {
      if (!duplicates.has(code)) duplicates.set(code, [index.get(code)]);
      duplicates.get(code).push(row);
    }
    if (!index.has(code)) index.set(code, row);
  }
  return { index, duplicates };
}

function compareSourceToTarget(source, target) {
  const sourceRows = rowsFor(source);
  const targetRows = rowsFor(target);
  const sourceIndex = indexRows(sourceRows);
  const targetIndex = indexRows(targetRows);
  const sourceCodes = new Set(sourceIndex.index.keys());
  const targetCodes = new Set(targetIndex.index.keys());
  const missingInTarget = [...sourceCodes].filter(code => !targetCodes.has(code)).sort();
  const extraInTarget = [...targetCodes].filter(code => !sourceCodes.has(code)).sort();
  const sharedCodes = [...sourceCodes].filter(code => targetCodes.has(code)).sort();
  const sourceFields = fieldSet(sourceRows);
  const targetFields = fieldSet(targetRows);
  const sourceOnlyFields = [...sourceFields].filter(field => !targetFields.has(field)).sort();
  const targetOnlyFields = [...targetFields].filter(field => !sourceFields.has(field)).sort();
  const meaningfulSourceOnly = sourceOnlyFields.map(field => {
    const examples = [];
    for (const row of sourceRows) {
      const value = firstMeaningful(row, field);
      if (value && !examples.includes(value)) examples.push(value);
      if (examples.length >= 4) break;
    }
    return { field, examples };
  }).filter(item => item.examples.length);

  const mismatchedSharedFields = [];
  const comparableFields = [...sourceFields].filter(field => targetFields.has(field));
  for (const field of comparableFields) {
    let checked = 0;
    let mismatch = 0;
    const examples = [];
    for (const code of sharedCodes.slice(0, 10000)) {
      const sourceValue = firstMeaningful(sourceIndex.index.get(code), field);
      const targetValue = firstMeaningful(targetIndex.index.get(code), field);
      if (!sourceValue && !targetValue) continue;
      checked += 1;
      if (sourceValue !== targetValue) {
        mismatch += 1;
        if (examples.length < 5) examples.push({ hunt_code: code, source: sourceValue, target: targetValue });
      }
    }
    if (mismatch) mismatchedSharedFields.push({ field, checked, mismatch, examples });
  }

  return {
    source: source.label,
    target: target.label,
    source_file: source.file,
    target_file: target.file,
    source_rows: sourceRows.length,
    target_rows: targetRows.length,
    source_unique_codes: sourceCodes.size,
    target_unique_codes: targetCodes.size,
    shared_codes: sharedCodes.length,
    missing_in_target_count: missingInTarget.length,
    missing_in_target: missingInTarget,
    extra_in_target_count: extraInTarget.length,
    extra_in_target: extraInTarget.slice(0, 250),
    source_duplicate_code_count: sourceIndex.duplicates.size,
    source_duplicate_codes: [...sourceIndex.duplicates.keys()].sort().slice(0, 250),
    target_duplicate_code_count: targetIndex.duplicates.size,
    target_duplicate_codes: [...targetIndex.duplicates.keys()].sort().slice(0, 250),
    source_field_count: sourceFields.size,
    target_field_count: targetFields.size,
    source_only_fields: sourceOnlyFields,
    target_only_fields: targetOnlyFields,
    meaningful_source_only_fields: meaningfulSourceOnly,
    mismatched_shared_fields: mismatchedSharedFields,
    significant_drop: missingInTarget.length > 0 || meaningfulSourceOnly.length > 0,
  };
}

function markdown(report) {
  const lines = [];
  lines.push('# Canonical Data Drop Audit');
  lines.push('');
  lines.push(`Generated: ${report.generated_at}`);
  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push('| Source | Target | Source codes | Target codes | Shared | Missing in target | Source-only fields | Significant drop |');
  lines.push('| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |');
  for (const c of report.comparisons) {
    lines.push(`| ${c.source} | ${c.target} | ${c.source_unique_codes} | ${c.target_unique_codes} | ${c.shared_codes} | ${c.missing_in_target_count} | ${c.meaningful_source_only_fields.length} | ${c.significant_drop ? 'YES' : 'no'} |`);
  }
  lines.push('');
  for (const c of report.comparisons) {
    lines.push(`## ${c.source} -> ${c.target}`);
    lines.push('');
    lines.push(`- Source rows: ${c.source_rows}`);
    lines.push(`- Target rows: ${c.target_rows}`);
    lines.push(`- Source unique hunt codes: ${c.source_unique_codes}`);
    lines.push(`- Target unique hunt codes: ${c.target_unique_codes}`);
    lines.push(`- Missing in target: ${c.missing_in_target_count}${c.missing_in_target_count ? ` (${c.missing_in_target.slice(0, 80).join(', ')}${c.missing_in_target.length > 80 ? ', ...' : ''})` : ''}`);
    lines.push(`- Extra in target: ${c.extra_in_target_count}${c.extra_in_target_count ? ` (${c.extra_in_target.slice(0, 80).join(', ')}${c.extra_in_target_count > 80 ? ', ...' : ''})` : ''}`);
    lines.push(`- Source duplicate codes: ${c.source_duplicate_code_count}`);
    lines.push(`- Target duplicate codes: ${c.target_duplicate_code_count}`);
    lines.push('');
    if (c.meaningful_source_only_fields.length) {
      lines.push('### Meaningful source-only fields');
      lines.push('');
      for (const item of c.meaningful_source_only_fields) {
        lines.push(`- ${item.field}: ${item.examples.join(' | ')}`);
      }
      lines.push('');
    }
    if (c.mismatched_shared_fields.length) {
      lines.push('### Shared-field mismatches, top fields');
      lines.push('');
      for (const item of c.mismatched_shared_fields.slice(0, 20)) {
        lines.push(`- ${item.field}: ${item.mismatch}/${item.checked} checked differ`);
      }
      lines.push('');
    }
  }
  return `${lines.join('\n')}\n`;
}

const comparisons = [];
for (const source of SOURCES) {
  for (const target of TARGETS) {
    if (target.optional && !fs.existsSync(abs(target.file))) continue;
    comparisons.push(compareSourceToTarget(source, target));
  }
}

const report = {
  generated_at: new Date().toISOString(),
  sources: SOURCES,
  targets: TARGETS.filter(target => !target.optional || fs.existsSync(abs(target.file))),
  comparisons,
};

fs.mkdirSync(path.dirname(abs(OUT_JSON)), { recursive: true });
fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
fs.writeFileSync(abs(OUT_MD), markdown(report), 'utf8');

console.log(JSON.stringify({
  ok: true,
  report_json: OUT_JSON,
  report_md: OUT_MD,
  comparisons: comparisons.map(c => ({
    source: c.source,
    target: c.target,
    source_unique_codes: c.source_unique_codes,
    target_unique_codes: c.target_unique_codes,
    missing_in_target_count: c.missing_in_target_count,
    meaningful_source_only_fields: c.meaningful_source_only_fields.length,
    significant_drop: c.significant_drop,
  })),
}, null, 2));
