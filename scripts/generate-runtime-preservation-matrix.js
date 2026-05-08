const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const OUT_JSON = 'canonical/runtime-preservation-matrix.json';
const OUT_MD = 'docs/runtime-preservation-matrix.md';

const RUNTIME_FILES = [
  'index.html',
  'research.html',
  'hard-copy.html',
  'verify.html',
  'config.js',
  'app.js',
  'data.js',
  'boundary-resolver.js',
  'hunt-research.js',
  'ui.js',
  'header-layout.js',
  'google-basemap.js',
];

const DATASETS = [
  { source: 'data/hunt-master-canonical-2026-database-candidate.json', dataset: 'hunt-planner-2026.hunt_catalog', jsonPath: ['canonical/hunt-planner-2026.json', 'hunt_catalog'] },
  { source: 'processed_data/display-boundary-index-2026.json', dataset: 'hunt-planner-2026.boundaries.display_index', jsonPath: ['canonical/hunt-planner-2026.json', 'boundaries', 'display_index'] },
  { source: 'processed_data/boundary-manifest-2026.json', dataset: 'hunt-planner-2026.boundaries.manifest.records', jsonPath: ['canonical/hunt-planner-2026.json', 'boundaries', 'manifest', 'records'] },
  { source: 'data/outfitters.json', dataset: 'outfitter-verification-2026.outfitters.internal_records', jsonPath: ['canonical/outfitter-verification-2026.json', 'outfitters', 'internal_records'] },
  { source: 'processed_data/outfitter-federal-unit-coverage-review.json', dataset: 'outfitter-verification-2026.outfitters.federal_coverage', jsonPath: ['canonical/outfitter-verification-2026.json', 'outfitters', 'federal_coverage'] },
  { source: 'processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json', dataset: 'hard-copies-2026.library.items', jsonPath: ['canonical/hard-copies-2026.json', 'library', 'items'] },
  { source: 'processed_data/draw_reality_engine.csv', dataset: 'hunt-research-2026.datasets.draw_reality_engine', csvContract: ['canonical/hunt-research-2026.json', 'datasets', 'draw_reality_engine', 'fields'] },
  { source: 'processed_data/point_ladder_view.csv', dataset: 'hunt-research-2026.datasets.point_ladder_view', csvContract: ['canonical/hunt-research-2026.json', 'datasets', 'point_ladder_view', 'fields'] },
  { source: 'processed_data/hunt_master_enriched.csv', dataset: 'hunt-research-2026.datasets.hunt_master_enriched', csvContract: ['canonical/hunt-research-2026.json', 'datasets', 'hunt_master_enriched', 'fields'] },
  { source: 'processed_data/hunt_unit_reference_linked.csv', dataset: 'hunt-research-2026.datasets.hunt_unit_reference_linked', csvContract: ['canonical/hunt-research-2026.json', 'datasets', 'hunt_unit_reference_linked', 'fields'] },
];

const ALIASES = {
  hunt_code: ['huntCode', 'code', 'HuntCode'],
  hunt_name: ['title', 'unitName'],
  boundary_id: ['boundaryId', 'Boundary_Id', 'BoundaryID'],
  display_boundary_id: ['displayBoundaryId', 'UOGA_DISPLAY_BOUNDARY_ID'],
  dwr_boundary_id: ['dwrBoundaryId'],
  dwr_member_boundary_ids: ['dwrMemberBoundaryIds', 'member_boundary_ids', 'memberBoundaryIds'],
  boundary_geojson_path: ['boundaryGeojsonPath'],
  boundary_kmz_path: ['boundaryKmzPath'],
  boundary_kml_path: ['boundaryKmlPath'],
  merged_boundary_id: ['mergedBoundaryId'],
  boundary_geometry_type: ['boundaryGeometryType'],
};

function abs(file) {
  return path.join(REPO, file);
}

function readText(file) {
  return fs.existsSync(abs(file)) ? fs.readFileSync(abs(file), 'utf8').replace(/^\uFEFF/, '') : '';
}

function readJson(file) {
  return JSON.parse(readText(file));
}

function getByPath(value, parts) {
  return parts.reduce((current, part) => current && current[part], value);
}

function parseCsvHeader(file) {
  const first = readText(file).split(/\r?\n/)[0] || '';
  const headers = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < first.length; i += 1) {
    const ch = first[i];
    const next = first[i + 1];
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
      headers.push(cell.trim().replace(/^\uFEFF/, ''));
      cell = '';
    } else {
      cell += ch;
    }
  }
  headers.push(cell.trim().replace(/^\uFEFF/, ''));
  return headers.map(header => header.replace(/^"|"$/g, ''));
}

function rowsFromJsonSource(source) {
  const value = readJson(source);
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== 'object') return [];
  for (const key of ['records', 'items', 'outfitters', 'features', 'hunts']) {
    if (Array.isArray(value[key])) return value[key];
  }
  return [];
}

function fieldsFromRows(rows) {
  const fields = new Set();
  rows.slice(0, 5000).forEach(row => {
    if (row && typeof row === 'object') Object.keys(row).forEach(field => fields.add(field));
  });
  return [...fields].sort();
}

function fieldsForDataset(dataset) {
  if (!fs.existsSync(abs(dataset.source))) return [];
  if (dataset.source.endsWith('.csv')) {
    const fields = new Set(parseCsvHeader(dataset.source));
    if (dataset.source === 'processed_data/draw_reality_engine.csv') {
      const research = readJson('canonical/hunt-research-2026.json');
      for (const field of research.modeled_fields || []) fields.add(field);
      for (const field of research.legacy_fields || []) fields.add(field);
      for (const field of research.hunt_quality_fields || []) fields.add(field);
    }
    return [...fields].sort();
  }
  return fieldsFromRows(rowsFromJsonSource(dataset.source));
}

function runtimeUsage(field) {
  const aliases = ALIASES[field] || [];
  const names = [field, ...aliases];
  const usedBy = [];
  for (const file of RUNTIME_FILES) {
    const text = readText(file);
    const used = names.some(name => {
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return new RegExp(`(^|[^A-Za-z0-9_])${escaped}([^A-Za-z0-9_]|$)`).test(text);
    });
    if (used) usedBy.push(file);
  }
  return usedBy;
}

function canonicalFields(dataset) {
  if (dataset.csvContract) {
    const [file, ...parts] = dataset.csvContract;
    const fields = new Set(getByPath(readJson(file), parts) || []);
    if (dataset.source === 'processed_data/draw_reality_engine.csv') {
      const research = readJson('canonical/hunt-research-2026.json');
      for (const field of research.modeled_fields || []) fields.add(field);
      for (const field of research.legacy_fields || []) fields.add(field);
      for (const field of research.hunt_quality_fields || []) fields.add(field);
    }
    return [...fields];
  }
  if (dataset.jsonPath) {
    const [file, ...parts] = dataset.jsonPath;
    const rows = getByPath(readJson(file), parts);
    return fieldsFromRows(Array.isArray(rows) ? rows : []);
  }
  return [];
}

function canonicalPath(dataset, field) {
  if (dataset.csvContract) return `${dataset.dataset}.fields.${field}`;
  return `${dataset.dataset}[].${field}`;
}

function isPreserved(field, dataset) {
  const fields = canonicalFields(dataset);
  if (fields.includes(field)) return true;
  return (ALIASES[field] || []).some(alias => fields.includes(alias));
}

function matrix() {
  const rows = [];
  for (const dataset of DATASETS) {
    for (const field of fieldsForDataset(dataset)) {
      const usedBy = runtimeUsage(field);
      const preserved = isPreserved(field, dataset);
      rows.push({
        field,
        source: path.basename(dataset.source),
        source_file: dataset.source,
        runtime_used: usedBy.length > 0,
        used_by: usedBy,
        canonical_path: canonicalPath(dataset, field),
        preserved,
        alias: ALIASES[field] || null,
        promotion_safe: preserved || usedBy.length === 0,
      });
    }
  }
  rows.sort((a, b) => `${a.source_file}:${a.field}`.localeCompare(`${b.source_file}:${b.field}`));
  return rows;
}

function markdown(rows) {
  const lines = [];
  lines.push('# Runtime Preservation Matrix');
  lines.push('');
  lines.push(`Generated: ${new Date().toISOString()}`);
  lines.push('');
  lines.push('| Field | Source | Runtime used | Used by | Canonical path | Preserved | Alias | Promotion safe |');
  lines.push('| --- | --- | --- | --- | --- | --- | --- | --- |');
  for (const row of rows) {
    lines.push(`| ${row.field} | ${row.source_file} | ${row.runtime_used} | ${row.used_by.join(', ') || ''} | ${row.canonical_path} | ${row.preserved} | ${row.alias ? row.alias.join(', ') : ''} | ${row.promotion_safe} |`);
  }
  return `${lines.join('\n')}\n`;
}

const rows = matrix();
fs.mkdirSync(path.dirname(abs(OUT_JSON)), { recursive: true });
fs.mkdirSync(path.dirname(abs(OUT_MD)), { recursive: true });
fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(rows, null, 2)}\n`, 'utf8');
fs.writeFileSync(abs(OUT_MD), markdown(rows), 'utf8');

const unsafe = rows.filter(row => !row.promotion_safe);
console.log(JSON.stringify({
  ok: unsafe.length === 0,
  report_json: OUT_JSON,
  report_md: OUT_MD,
  rows: rows.length,
  runtime_used: rows.filter(row => row.runtime_used).length,
  unsafe: unsafe.length,
}, null, 2));

if (unsafe.length) process.exit(1);
