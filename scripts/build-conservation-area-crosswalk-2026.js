const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const CSV_DIR = path.join('pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv');
const REPORT_DIR = path.join('pipeline', 'RAW', 'hunt_unit_database', '2026', 'reports');
const DATABASE_FILE = path.join(CSV_DIR, 'DATABASE.csv');
const RAW_WORKBOOK_GROUPED = path.join(REPORT_DIR, 'conservation_raw_workbook_grouped_2026.csv');
const PDF_EXTRACTED_GROUPED = path.join(REPORT_DIR, 'conservation_permits_2025_2027_grouped.csv');
const BUNDLE_FILE = path.join('processed_data', 'hard_data_exports', 'unit_specific_conservation_expo_bundles.csv');
const OUT_CSV = path.join(REPORT_DIR, 'conservation_area_crosswalk_2026.csv');
const OUT_JSON = path.join(REPORT_DIR, 'conservation_area_crosswalk_2026.json');

const AREA_RULES = [
  {
    species: 'Antlerless Elk',
    area: 'Manti',
    primary_hunt_code: 'EA1271',
    boundary_reference_species: 'Elk',
    boundary_reference_sex_type: 'Bull',
    boundary_reference_hunt_type: 'Limited Entry',
    area_patterns: [/^manti\b/i],
    exclude_patterns: [/expo/i, /conservation/i],
  },
  {
    species: 'Antlerless Elk',
    area: 'Fishlake',
    primary_hunt_code: 'EA1270',
    boundary_reference_species: 'Elk',
    boundary_reference_sex_type: 'Bull',
    boundary_reference_hunt_type: 'Limited Entry',
    area_patterns: [/^fishlake/i],
    exclude_patterns: [/expo/i, /conservation/i],
  },
  {
    species: 'Antlerless Elk',
    area: 'Wasatch Mtns',
    primary_hunt_code: 'EA2045',
    boundary_reference_species: 'Elk',
    boundary_reference_sex_type: 'Bull',
    boundary_reference_hunt_type: 'Limited Entry',
    area_patterns: [/^wasatch mtns/i],
    exclude_patterns: [/expo/i, /conservation/i],
  },
  {
    species: 'Antlerless Elk',
    area: 'La Sal',
    primary_hunt_code: 'EA1180',
    boundary_reference_species: 'Elk',
    boundary_reference_sex_type: 'Bull',
    boundary_reference_hunt_type: 'Limited Entry',
    area_patterns: [/^la sal/i],
    exclude_patterns: [/expo/i, /conservation/i],
  },
  {
    species: 'Antlerless Elk',
    area: 'Cache',
    primary_hunt_code: 'EA2041',
    boundary_reference_species: 'Elk',
    boundary_reference_sex_type: 'Bull',
    boundary_reference_hunt_type: 'Limited Entry',
    area_patterns: [/^cache/i],
    exclude_patterns: [/expo/i, /conservation/i],
  },
];

function abs(relativePath) {
  return path.join(REPO, relativePath);
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
      } else if (ch === '"') quoted = false;
      else value += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') {
      row.push(value);
      value = '';
    } else if (ch === '\n') {
      row.push(value);
      rows.push(row);
      row = [];
      value = '';
    } else if (ch !== '\r') value += ch;
  }
  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
  return {
    headers,
    records: rows
      .filter((r) => r.some((cell) => String(cell || '').trim()))
      .map((r) => Object.fromEntries(headers.map((header, idx) => [header, r[idx] || '']))),
  };
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(relativePath, headers, records) {
  const lines = [headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))]
    .map((row) => row.map(csvEscape).join(','));
  fs.writeFileSync(abs(relativePath), `${lines.join('\r\n')}\r\n`, 'utf8');
}

function clean(value) {
  return String(value ?? '').trim();
}

function key(value) {
  return clean(value).toLowerCase().replace(/\s+/g, ' ');
}

function readCsv(relativePath) {
  return parseCsv(fs.readFileSync(abs(relativePath), 'utf8').replace(/^\uFEFF/, ''));
}

function matchesArea(row, rule) {
  const name = clean(row.hunt_name);
  const joined = [row.hunt_name, row.hunt_type, row.weapon].map(clean).join(' ');
  if (rule.exclude_patterns?.some((pattern) => pattern.test(joined))) return false;
  return rule.area_patterns.some((pattern) => pattern.test(name));
}

function buildForRule(rule, database, permitsByKey, bundleRows) {
  const permit = permitsByKey.get(`${key(rule.species)}|${key(rule.area)}|any legal weapon`);
  const areaBundleRows = bundleRows
    .filter((row) => row.species === 'Elk')
    .filter((row) => row.sex_type === 'Antlerless')
    .filter((row) => rule.area_patterns.some((pattern) => pattern.test(clean(row.hunt_name))))
    .sort((a, b) => clean(a.hunt_code).localeCompare(clean(b.hunt_code)));
  const conservationBundleRows = areaBundleRows.filter((row) => /conservation/i.test(row.hunt_name) || /conservation/i.test(row.hunt_type));
  const expoBundleRows = areaBundleRows.filter((row) => /expo/i.test(row.hunt_name) || /expo/i.test(row.multi_unit_reason));
  const boundaryIds = [...new Set(areaBundleRows.flatMap((row) => clean(row.boundary_ids).split('|').map((item) => clean(item)).filter(Boolean)))].sort((a, b) => Number(a) - Number(b));
  const included = database
    .filter((row) => clean(row.species) === 'Elk')
    .filter((row) => clean(row.sex_type).toLowerCase() === 'antlerless')
    .filter((row) => matchesArea(row, rule))
    .map((row) => clean(row.hunt_code))
    .filter(Boolean)
    .sort();

  const boundaryRefs = database
    .filter((row) => clean(row.species) === rule.boundary_reference_species)
    .filter((row) => clean(row.sex_type) === rule.boundary_reference_sex_type)
    .filter((row) => clean(row.hunt_type) === rule.boundary_reference_hunt_type)
    .filter((row) => matchesArea(row, { ...rule, exclude_patterns: [] }))
    .map((row) => clean(row.hunt_code))
    .filter(Boolean)
    .sort();

  return {
    conservation_area_id: `CONSERVATION_${rule.species}_${rule.area}_2026`.toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/_+$/g, ''),
    conservation_species: rule.species,
    conservation_area: rule.area,
    primary_hunt_code: rule.primary_hunt_code,
    permits_2026_conservation: permit?.permits_2026_conservation || permit?.conservation_permit_count_2025_2027 || '',
    permit_source_area: permit?.area || '',
    permit_source_condition: permit?.condition || '',
    bundle_conservation_hunt_codes: conservationBundleRows.map((row) => clean(row.hunt_code)).join(';'),
    bundle_expo_hunt_codes: expoBundleRows.map((row) => clean(row.hunt_code)).join(';'),
    bundle_boundary_ids: boundaryIds.join(';'),
    bundle_boundary_id_count: boundaryIds.length,
    included_hunt_codes: included.join(';'),
    included_hunt_code_count: included.length,
    boundary_reference_hunt_codes: boundaryRefs.join(';'),
    boundary_reference_hunt_code_count: boundaryRefs.length,
    classification_note: 'Conservation permit area covers the listed applicable hunt codes; mapping should use the major LE bull elk boundary family where antlerless subunit geometry is broader/nested.',
    source_pdf: permit?.source_pdf || 'pipeline/RAW/hunt_unit_database/2026/pdf/Conservation Permits/2025-27 Conservation Permits.pdf',
    source_bundle: BUNDLE_FILE.replace(/\\/g, '/'),
    review_status: permit ? 'READY_FOR_OWNER_REVIEW' : 'SOURCE_AREA_NOT_EXTRACTED',
  };
}

function main() {
  fs.mkdirSync(abs(REPORT_DIR), { recursive: true });
  const database = readCsv(DATABASE_FILE).records;
  const conservationGroupedFile = fs.existsSync(abs(RAW_WORKBOOK_GROUPED)) ? RAW_WORKBOOK_GROUPED : PDF_EXTRACTED_GROUPED;
  const grouped = readCsv(conservationGroupedFile).records;
  const bundleRows = fs.existsSync(abs(BUNDLE_FILE)) ? readCsv(BUNDLE_FILE).records : [];
  const permitsByKey = new Map(grouped.map((row) => [`${key(row.species)}|${key(row.area)}|${key(row.condition)}`, row]));
  const records = AREA_RULES.map((rule) => buildForRule(rule, database, permitsByKey, bundleRows));
  const report = {
    generated_at: new Date().toISOString(),
    database_file: DATABASE_FILE.replace(/\\/g, '/'),
    conservation_grouped_file: conservationGroupedFile.replace(/\\/g, '/'),
    bundle_file: BUNDLE_FILE.replace(/\\/g, '/'),
    output_csv: OUT_CSV.replace(/\\/g, '/'),
    rows: records.length,
    note: 'This is an area-level crosswalk. It intentionally does not force conservation permits into normal public draw quota fields.',
    records,
  };
  writeCsv(OUT_CSV, [
    'conservation_area_id',
    'conservation_species',
    'conservation_area',
    'primary_hunt_code',
    'permits_2026_conservation',
    'permit_source_area',
    'permit_source_condition',
    'bundle_conservation_hunt_codes',
    'bundle_expo_hunt_codes',
    'bundle_boundary_ids',
    'bundle_boundary_id_count',
    'included_hunt_codes',
    'included_hunt_code_count',
    'boundary_reference_hunt_codes',
    'boundary_reference_hunt_code_count',
    'classification_note',
    'source_pdf',
    'source_bundle',
    'review_status',
  ], records);
  fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    ok: true,
    rows: records.length,
    output_csv: OUT_CSV.replace(/\\/g, '/'),
    output_json: OUT_JSON.replace(/\\/g, '/'),
  }, null, 2));
}

main();
