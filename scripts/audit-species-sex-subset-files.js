const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const CSV_DIR = 'pipeline/RAW/hunt_unit_database/2026/csv';
const REPORT_DIR = 'pipeline/RAW/hunt_unit_database/2026/reports';
const DATABASE_FILE = path.join(CSV_DIR, 'DATABASE.csv').replace(/\\/g, '/');
const STAMP = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+$/, '').replace('T', '_');

const EXCLUDE_FILES = new Set([
  'DATABASE.csv',
  'hunt_master_canonical_2026_built.csv',
  '2026_utah_dwr_hunt_matrix.csv',
]);

const FIELD_ALIASES = {
  hunt_name: ['hunt_name', 'hunt name', 'unit', 'name'],
  hunt_code: ['hunt_code', 'hunt code', 'hunt_number', 'hunt number', 'code'],
  sex_type: ['sex_type', 'sex type', 'sex'],
  species: ['species'],
  weapon: ['weapon'],
  hunt_type: ['hunt_type', 'hunt type'],
  season: ['season', 'season dates', 'dates'],
  permits_2026_res: ['permits_2026_res', 'permits_res_2026', 'res', 'resident'],
  permits_2026_nr: ['permits_2026_nr', 'permits_non-res_2026', 'permits_non_res_2026', 'non-res', 'nonres', 'nonresident'],
  permits_2026_total: ['permits_2026_total', 'permits_total_2026', 'total_2026_permits', 'total'],
  notes: ['notes', 'note', 'other', 'NOTES'],
};

const COMPARE_FIELDS = [
  'hunt_name',
  'sex_type',
  'species',
  'weapon',
  'hunt_type',
  'season',
  'permits_2026_res',
  'permits_2026_nr',
  'permits_2026_total',
  'notes',
];

const PERMIT_FIELDS = new Set([
  'permits_2026_res',
  'permits_2026_nr',
  'permits_2026_total',
]);

const SUBSET_TOKENS = [
  'all',
  'total',
  'cwmu',
  'conservation',
  'limited',
  'entry',
  'management',
  'private',
  'privatelands',
  'lands',
  'only',
  'statewide',
  'general',
  'season',
  'archery',
  'extended',
  'cactus',
  'anybull',
  'spikeonly',
  'youth',
  'maturebull',
  'permit',
  'control',
];

function abs(file) {
  return path.join(REPO, file);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        value += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(value);
      value = '';
    } else if (ch === '\n') {
      row.push(value);
      rows.push(row);
      row = [];
      value = '';
    } else if (ch !== '\r') {
      value += ch;
    }
  }
  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
  const records = rows
    .filter((r) => r.some((value) => String(value || '').trim()))
    .map((r) => Object.fromEntries(headers.map((header, idx) => [header, r[idx] || '']).filter(([header]) => header)));
  return { headers, records };
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\r\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function writeCsv(file, headers, records) {
  const lines = [headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))]
    .map((row) => row.map(csvEscape).join(','));
  fs.writeFileSync(abs(file), `${lines.join('\r\n')}\r\n`, 'utf8');
}

function clean(value) {
  return String(value ?? '').trim();
}

function compact(value) {
  return clean(value).replace(/\s+/g, ' ');
}

function normalizeComparison(value) {
  return compact(value)
    .replace(/[–—]/g, '-')
    .replace(/\s*-\s*/g, ' - ')
    .replace(/\s*\/\s*/g, '/')
    .toLowerCase();
}

function normalizeHeader(value) {
  return clean(value).replace(/^\uFEFF/, '').toLowerCase().replace(/[_\s]+/g, '_').replace(/-/g, '-');
}

function fieldFromRecord(record, field) {
  const aliases = FIELD_ALIASES[field] || [field];
  const keys = Object.keys(record);
  for (const alias of aliases) {
    const normalizedAlias = normalizeHeader(alias);
    const match = keys.find((key) => normalizeHeader(key) === normalizedAlias);
    if (match) return clean(record[match]);
  }
  return '';
}

function normalizeCode(value) {
  return clean(value).toUpperCase();
}

function fileBase(name) {
  return path.basename(name, '.csv').toLowerCase().replace(/\s+/g, '_');
}

function fileTokens(name) {
  return fileBase(name)
    .replace(/^2026_/, '')
    .split(/[_\s]+/)
    .filter(Boolean);
}

function broadRoot(name) {
  const tokens = fileTokens(name).filter((token) => !SUBSET_TOKENS.includes(token));
  return tokens.slice(0, 3).join('_');
}

function mode(values) {
  const counts = new Map();
  for (const value of values.filter(Boolean)) counts.set(value, (counts.get(value) || 0) + 1);
  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
}

function readTable(fileName) {
  const relative = path.join(CSV_DIR, fileName);
  const parsed = parseCsv(fs.readFileSync(abs(relative), 'utf8'));
  const rows = parsed.records.map((record, index) => {
    const normalized = {
      row_number: index + 2,
      hunt_code: normalizeCode(fieldFromRecord(record, 'hunt_code')),
    };
    for (const field of COMPARE_FIELDS) normalized[field] = fieldFromRecord(record, field);
    return { raw: record, ...normalized };
  });
  const huntRows = rows.filter((row) => row.hunt_code);
  const byCode = new Map();
  const duplicateCodes = [];
  for (const row of huntRows) {
    if (byCode.has(row.hunt_code)) duplicateCodes.push(row.hunt_code);
    if (!byCode.has(row.hunt_code)) byCode.set(row.hunt_code, row);
  }
  const codes = new Set(byCode.keys());
  const huntTypes = new Set(huntRows.map((row) => compact(row.hunt_type)).filter(Boolean));
  const weapons = new Set(huntRows.map((row) => compact(row.weapon)).filter(Boolean));
  const species = mode(huntRows.map((row) => compact(row.species)));
  const sex = mode(huntRows.map((row) => compact(row.sex_type)));
  return {
    file: fileName,
    path: relative.replace(/\\/g, '/'),
    headers: parsed.headers,
    rows_total: parsed.records.length,
    hunt_rows: huntRows.length,
    unique_hunt_codes: codes.size,
    blank_code_rows: rows.length - huntRows.length,
    duplicate_hunt_codes: [...new Set(duplicateCodes)].sort(),
    species,
    sex_type: sex,
    hunt_type_count: huntTypes.size,
    weapon_count: weapons.size,
    hunt_types: [...huntTypes].sort(),
    weapons: [...weapons].sort(),
    root: broadRoot(fileName),
    tokens: fileTokens(fileName),
    codes,
    byCode,
    appears_malformed: codes.size === 0 || parsed.headers.some((header, idx) => header === '' && idx < parsed.headers.length - 1),
  };
}

function loadTables() {
  const files = fs.readdirSync(abs(CSV_DIR))
    .filter((name) => name.toLowerCase().endsWith('.csv'))
    .filter((name) => !EXCLUDE_FILES.has(name))
    .filter((name) => !name.toLowerCase().includes('audit'))
    .sort();
  return files.map(readTable);
}

function loadDatabase() {
  const dbPath = abs(DATABASE_FILE);
  if (!fs.existsSync(dbPath)) return new Map();
  const parsed = parseCsv(fs.readFileSync(dbPath, 'utf8'));
  const byCode = new Map();
  for (const record of parsed.records) {
    const code = normalizeCode(fieldFromRecord(record, 'hunt_code'));
    if (!code || byCode.has(code)) continue;
    const row = {};
    for (const field of COMPARE_FIELDS) row[field] = fieldFromRecord(record, field);
    byCode.set(code, row);
  }
  return byCode;
}

function sameFamily(parent, child) {
  if (parent.file === child.file) return false;
  if (!parent.unique_hunt_codes || !child.unique_hunt_codes) return false;
  const sameSpecies = parent.species && child.species && parent.species.toLowerCase() === child.species.toLowerCase();
  const sameSex = parent.sex_type && child.sex_type && parent.sex_type.toLowerCase() === child.sex_type.toLowerCase();
  const rootMatch = parent.root && child.root && (child.root.startsWith(parent.root) || parent.root.startsWith(child.root));
  const baseMatch = fileBase(child.file).startsWith(fileBase(parent.file).replace(/_all(_2)?$/, ''));
  return (sameSpecies && sameSex) || rootMatch || baseMatch;
}

function overlap(parent, child) {
  let count = 0;
  for (const code of child.codes) if (parent.codes.has(code)) count += 1;
  return count;
}

function parentScore(parent, child) {
  if (!sameFamily(parent, child)) return -1;
  if (parent.unique_hunt_codes < child.unique_hunt_codes) return -1;
  const common = overlap(parent, child);
  if (!common) return -1;
  const childCoverage = common / child.unique_hunt_codes;
  const parentShare = common / parent.unique_hunt_codes;
  const parentBroadness = (parent.hunt_type_count + parent.weapon_count) - (child.hunt_type_count + child.weapon_count);
  const rootBonus = parent.root && child.root && child.root.startsWith(parent.root) ? 0.25 : 0;
  const nameBonus = fileBase(parent.file).includes('all') || fileBase(parent.file).includes('total') ? 0.2 : 0;
  return childCoverage * 4 + parentShare + parentBroadness * 0.05 + rootBonus + nameBonus;
}

function chooseParent(child, tables) {
  const candidates = tables
    .filter((parent) => parent.file !== child.file)
    .map((parent) => ({ parent, score: parentScore(parent, child), overlap: overlap(parent, child) }))
    .filter((item) => item.score >= 0 && item.overlap > 0)
    .sort((a, b) => b.score - a.score);
  const best = candidates[0];
  if (!best) return null;
  const childCoverage = best.overlap / child.unique_hunt_codes;
  if (childCoverage < 0.5) return null;
  return best.parent;
}

function compareChildToParent(parent, child, databaseByCode) {
  const missingFromParent = [];
  const mismatches = [];
  for (const code of child.codes) {
    const parentRow = parent.byCode.get(code);
    const childRow = child.byCode.get(code);
    if (!parentRow) {
      missingFromParent.push(code);
      continue;
    }
    for (const field of COMPARE_FIELDS) {
      const parentValue = parentRow[field] || '';
      const childValue = childRow[field] || '';
      if (!parentValue && !childValue) continue;
      if (normalizeComparison(parentValue) !== normalizeComparison(childValue)) {
        const databaseValue = databaseByCode.get(code)?.[field] || '';
        const parentMatchesDatabase = databaseValue !== '' || PERMIT_FIELDS.has(field)
          ? normalizeComparison(parentValue) === normalizeComparison(databaseValue)
          : null;
        const subsetMatchesDatabase = databaseValue !== '' || PERMIT_FIELDS.has(field)
          ? normalizeComparison(childValue) === normalizeComparison(databaseValue)
          : null;
        let databaseVerdict = '';
        if (parentMatchesDatabase === true && subsetMatchesDatabase === false) databaseVerdict = 'parent_matches_database';
        else if (parentMatchesDatabase === false && subsetMatchesDatabase === true) databaseVerdict = 'subset_matches_database';
        else if (parentMatchesDatabase === true && subsetMatchesDatabase === true) databaseVerdict = 'both_match_database';
        else if (parentMatchesDatabase === false && subsetMatchesDatabase === false) databaseVerdict = 'neither_matches_database';
        mismatches.push({
          parent_file: parent.file,
          subset_file: child.file,
          hunt_code: code,
          field,
          parent_value: parentValue,
          subset_value: childValue,
          database_value: databaseValue,
          database_verdict: databaseVerdict,
        });
      }
    }
  }
  const subsetCodes = new Set(child.codes);
  const parentOnlyCodes = [...parent.codes].filter((code) => !subsetCodes.has(code)).sort();
  return {
    parent_file: parent.file,
    subset_file: child.file,
    parent_unique_hunt_codes: parent.unique_hunt_codes,
    subset_unique_hunt_codes: child.unique_hunt_codes,
    overlap_hunt_codes: overlap(parent, child),
    missing_from_parent: missingFromParent.sort(),
    parent_only_codes: parentOnlyCodes,
    value_mismatches: mismatches,
  };
}

function markdown(report) {
  const databaseVerdicts = report.summary.database_verdict_counts || {};
  const lines = [
    '# 2026 Species/Sex Parent vs Subset Cross-Check',
    '',
    `Generated: ${report.generated_at}`,
    `CSV folder: ${CSV_DIR}`,
    '',
    'This audit compares broad species/sex CSV files against narrower subset files that appear to be split by hunt type and/or weapon.',
    '',
    '## Summary',
    '',
    `- Direct CSV tables scanned: ${report.summary.tables_scanned}`,
    `- Parent/subset relationships found: ${report.summary.relationships_found}`,
    `- Subset hunt codes missing from parent: ${report.summary.missing_from_parent_count}`,
    `- Shared-field value mismatches: ${report.summary.value_mismatch_count}`,
    `- Mismatches where parent matches DATABASE.csv: ${databaseVerdicts.parent_matches_database || 0}`,
    `- Mismatches where subset matches DATABASE.csv: ${databaseVerdicts.subset_matches_database || 0}`,
    `- Mismatches where neither matches DATABASE.csv: ${databaseVerdicts.neither_matches_database || 0}`,
    `- Files without a parent match: ${report.summary.orphan_files.length}`,
    `- Malformed/non-hunt tables: ${report.summary.malformed_files.length}`,
    '',
    '## Relationships',
    '',
    '| Parent | Subset | Parent Codes | Subset Codes | Overlap | Missing From Parent | Value Mismatches |',
    '| --- | --- | ---: | ---: | ---: | ---: | ---: |',
    ...report.relationships.map((item) => `| ${item.parent_file} | ${item.subset_file} | ${item.parent_unique_hunt_codes} | ${item.subset_unique_hunt_codes} | ${item.overlap_hunt_codes} | ${item.missing_from_parent.length} | ${item.value_mismatches.length} |`),
    '',
  ];
  if (report.summary.orphan_files.length) {
    lines.push('## Files Without Parent Match', '');
    report.summary.orphan_files.forEach((file) => lines.push(`- ${file}`));
    lines.push('');
  }
  if (report.summary.malformed_files.length) {
    lines.push('## Malformed / Non-Hunt Tables', '');
    report.summary.malformed_files.forEach((file) => lines.push(`- ${file}`));
    lines.push('');
  }
  const mismatchSample = report.relationships.flatMap((item) => item.value_mismatches).slice(0, 100);
  if (mismatchSample.length) {
    lines.push('## Mismatch Sample', '');
    lines.push('| Parent | Subset | Hunt Code | Field | Parent Value | Subset Value |');
    lines.push('| --- | --- | --- | --- | --- | --- |');
    mismatchSample.forEach((item) => {
      lines.push(`| ${item.parent_file} | ${item.subset_file} | ${item.hunt_code} | ${item.field} | ${item.parent_value.replace(/\|/g, '/')} | ${item.subset_value.replace(/\|/g, '/')} |`);
    });
    lines.push('');
  }
  return `${lines.join('\n')}\n`;
}

function main() {
  fs.mkdirSync(abs(REPORT_DIR), { recursive: true });
  const tables = loadTables();
  const databaseByCode = loadDatabase();
  const relationships = [];
  const parented = new Set();
  for (const child of tables) {
    if (child.appears_malformed) continue;
    const parent = chooseParent(child, tables);
    if (!parent) continue;
    if (parent.file === child.file) continue;
    if (parent.unique_hunt_codes === child.unique_hunt_codes && overlap(parent, child) === child.unique_hunt_codes) continue;
    relationships.push(compareChildToParent(parent, child, databaseByCode));
    parented.add(child.file);
  }
  relationships.sort((a, b) => a.parent_file.localeCompare(b.parent_file) || a.subset_file.localeCompare(b.subset_file));
  const malformedFiles = tables.filter((table) => table.appears_malformed).map((table) => table.file).sort();
  const orphanFiles = tables
    .filter((table) => !table.appears_malformed)
    .filter((table) => !parented.has(table.file))
    .map((table) => table.file)
    .sort();
  const report = {
    generated_at: new Date().toISOString(),
    csv_dir: CSV_DIR,
    database_file: DATABASE_FILE,
    compare_fields: COMPARE_FIELDS,
    summary: {
      tables_scanned: tables.length,
      relationships_found: relationships.length,
      missing_from_parent_count: relationships.reduce((sum, item) => sum + item.missing_from_parent.length, 0),
      value_mismatch_count: relationships.reduce((sum, item) => sum + item.value_mismatches.length, 0),
      database_verdict_counts: relationships
        .flatMap((item) => item.value_mismatches)
        .reduce((counts, mismatch) => {
          if (mismatch.database_verdict) counts[mismatch.database_verdict] = (counts[mismatch.database_verdict] || 0) + 1;
          return counts;
        }, {}),
      malformed_files: malformedFiles,
      orphan_files: orphanFiles,
    },
    table_inventory: tables.map((table) => ({
      file: table.file,
      rows_total: table.rows_total,
      hunt_rows: table.hunt_rows,
      unique_hunt_codes: table.unique_hunt_codes,
      blank_code_rows: table.blank_code_rows,
      duplicate_hunt_codes: table.duplicate_hunt_codes,
      species: table.species,
      sex_type: table.sex_type,
      hunt_type_count: table.hunt_type_count,
      weapon_count: table.weapon_count,
      appears_malformed: table.appears_malformed,
    })),
    relationships,
  };
  const jsonPath = `pipeline/RAW/hunt_unit_database/2026/reports/species_sex_subset_crosscheck_${STAMP}.json`;
  const mdPath = `pipeline/RAW/hunt_unit_database/2026/reports/species_sex_subset_crosscheck_${STAMP}.md`;
  const mismatchCsvPath = `pipeline/RAW/hunt_unit_database/2026/reports/species_sex_subset_crosscheck_mismatches_${STAMP}.csv`;
  fs.writeFileSync(abs(jsonPath), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(abs(mdPath), markdown(report), 'utf8');
  writeCsv(
    mismatchCsvPath,
    ['parent_file', 'subset_file', 'hunt_code', 'field', 'parent_value', 'subset_value', 'database_value', 'database_verdict'],
    relationships.flatMap((item) => item.value_mismatches),
  );
  console.log(JSON.stringify({
    ok: true,
    tables_scanned: report.summary.tables_scanned,
    relationships_found: report.summary.relationships_found,
    missing_from_parent_count: report.summary.missing_from_parent_count,
    value_mismatch_count: report.summary.value_mismatch_count,
    malformed_files: report.summary.malformed_files,
    orphan_file_count: report.summary.orphan_files.length,
    report_json: jsonPath,
    report_md: mdPath,
    mismatch_csv: mismatchCsvPath,
  }, null, 2));
}

main();
