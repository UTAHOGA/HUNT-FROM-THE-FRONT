const {
  PAGES,
  consumersFor,
  fieldsForRows,
  htmlContract,
  pageTools,
  rowsFor,
  sourceFiles,
  writeJson,
} = require('./inventory');

function observedType(values) {
  const seen = values.filter(value => value !== undefined && value !== null && String(value).trim() !== '').slice(0, 40);
  if (!seen.length) return 'unknown';
  if (seen.every(Array.isArray)) return 'array';
  if (seen.every(value => typeof value === 'boolean' || ['TRUE', 'FALSE'].includes(String(value).trim().toUpperCase()))) return 'boolean-like';
  if (seen.every(value => typeof value === 'number' || /^-?\d+(\.\d+)?$/.test(String(value).trim()))) return 'number-like';
  if (seen.every(value => typeof value === 'object')) return 'object';
  return 'string';
}

function examples(rows, field) {
  const vals = rows
    .slice(0, 5000)
    .map(row => row && row[field])
    .filter(value => value !== undefined && value !== null && String(value).trim() !== '')
    .map(value => Array.isArray(value) ? value.slice(0, 4).join(';') : typeof value === 'object' ? JSON.stringify(value).slice(0, 120) : String(value).trim());
  return [...new Set(vals)].slice(0, 4);
}

function targetFor(field, file) {
  const clean = field.replace(/^#/, '');
  if (file.includes('draw_reality')) return `hunt-research-2026.datasets.draw_reality_engine.fields.${clean}`;
  if (file.includes('point_ladder')) return `hunt-research-2026.datasets.point_ladder_view.fields.${clean}`;
  if (file.includes('hunt_master_enriched')) return `hunt-research-2026.datasets.hunt_master_enriched.fields.${clean}`;
  if (file.includes('hunt_unit_reference')) return `hunt-research-2026.datasets.hunt_unit_reference_linked.fields.${clean}`;
  if (file.includes('hard_copy_pdf_manifest')) return `hard-copies-2026.library.items[].${clean}`;
  if (file.includes('outfitter')) return `outfitter-verification-2026.outfitters[].${clean}`;
  if (file.includes('boundary') || file.includes('display-boundary')) return `hunt-planner-2026.boundaries.display_index[].${clean}`;
  if (file.includes('hunt-master')) return `hunt-planner-2026.hunt_catalog[].${clean}`;
  if (file.endsWith('.html')) return `shared-2026.routes[].ui_contract.${clean}`;
  return `shared-2026.runtime.${clean}`;
}

function requiredOrOptional(field, file) {
  if (field.startsWith('#')) return 'required';
  if (file.includes('boundary')) return ['hunt_code', 'display_boundary_id', 'geometry_status'].includes(field) ? 'required' : 'optional';
  return ['hunt_code', 'hunt_name', 'species', 'weapon', 'hunt_type', 'title', 'href', 'type', 'group', 'year', 'residency', 'points'].includes(field) ? 'required' : 'optional';
}

function fallback(field) {
  const map = {
    hunt_code: 'Normalize uppercase; fallback aliases include huntCode/code where present.',
    hunt_name: 'Fallback aliases include title/unitName where present.',
    species: 'Displayed blank if absent; filter option omitted if no value.',
    weapon: 'Normalized by planner helper; falls back to raw Weapon alias.',
    href: 'Hard-copy item cannot render as a download card without a link.',
    title: 'Displayed as card title; falls back to hunt_code or filename where the current UI allows it.',
    year: 'Hard Copies derives year from title/subtitle/href if not supplied.',
    group: 'Hard Copies falls back to raw_library and can infer conservation_permits from text.',
    type: 'Hard Copies falls back to file.',
    boundary_geojson_path: 'Selected-hunt geometry prefers direct GeoJSON path before DWR ID fallback.',
    display_boundary_id: 'Website display geometry key; never treated as a DWR numeric boundary ID.',
    display_odds_pct: 'Research UI preferred modeled probability.',
    p_draw_mean: 'Research UI uses decimal modeled probability when display_odds_pct is absent.',
    status: 'Display-only; MAX POOL must not force 100 percent odds.',
  };
  return map[field] || 'Current app tolerates missing values unless this field is marked required.';
}

function buildUsageMap() {
  const usage = [];
  const seen = new Set();
  for (const file of sourceFiles()) {
    if (!file.endsWith('.csv') && !file.endsWith('.json')) continue;
    const rows = rowsFor(file);
    for (const field of fieldsForRows(rows)) {
      const key = `${file}::${field}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const consumed = consumersFor(field);
      usage.push({
        field_name: field,
        current_source_file: file,
        consumed_by_files: consumed,
        page_tool_using_it: pageTools(file, consumed),
        required_or_optional: requiredOrOptional(field, file),
        data_type_observed: observedType(rows.slice(0, 5000).map(row => row && row[field])),
        example_values: examples(rows, field),
        fallback_behavior: fallback(field),
        canonical_target_path: targetFor(field, file),
        migration_status: consumed.length || pageTools(file, consumed).length ? 'mapped' : 'intentionally_unmapped',
      });
    }
  }
  for (const page of PAGES) {
    const contract = htmlContract(page.html);
    for (const id of contract.ids) {
      usage.push({
        field_name: `#${id}`,
        current_source_file: page.html,
        consumed_by_files: [page.html],
        page_tool_using_it: [page.label],
        required_or_optional: 'required',
        data_type_observed: 'dom-id',
        example_values: [id],
        fallback_behavior: 'DOM hook required by current page script/CSS.',
        canonical_target_path: targetFor(`#${id}`, page.html),
        migration_status: 'mapped',
      });
    }
    for (const attr of contract.data_attributes) {
      usage.push({
        field_name: attr,
        current_source_file: page.html,
        consumed_by_files: [page.html],
        page_tool_using_it: [page.label],
        required_or_optional: 'optional',
        data_type_observed: 'html-data-attribute',
        example_values: [attr],
        fallback_behavior: 'HTML behavior hook used by current controls.',
        canonical_target_path: targetFor(attr, page.html),
        migration_status: 'mapped',
      });
    }
  }
  usage.sort((a, b) => `${a.current_source_file}:${a.field_name}`.localeCompare(`${b.current_source_file}:${b.field_name}`));
  return usage;
}

function writeUsageMap(usage) {
  writeJson('canonical/canonical-field-usage-map.json', usage);
}

module.exports = { buildUsageMap, writeUsageMap };
