const {
  PAGES,
  htmlContract,
  readCsv,
  readJson,
  sourceFiles,
  sourceSummary,
  verifyStandards,
  writeJson,
} = require('./inventory');
const { buildSchemas } = require('./schema-builder');
const { buildUsageMap, writeUsageMap } = require('./usage-map');

const ownerQuestions = [
  { id: 'owner-hard-copy-categories', question: 'Confirm whether Hard Copies should remain PDF-only or include CSV/XLSX downloads later.', status: 'needs_owner_input' },
  { id: 'owner-outfitter-cpo-threshold', question: 'Confirm the owner-approved threshold for C.P.O. designation before automating verification labels.', status: 'needs_owner_input' },
];

const sourceNeeded = [
  { id: 'source-utah-dwr-outfitter-registration', item: 'Utah DWR outfitter registration floor and public-resource language.', source_url: 'https://wildlife.utah.gov/guide/outfitter.html', status: 'source_needed' },
  { id: 'source-regulatory-disclaimer', item: 'Verification disclaimer: not a license, permit grant, land-access guarantee, agency authorization, or legal determination.', source_url: null, status: 'source_needed' },
];

function canonicalDataSource() {
  return require('fs').existsSync(require('path').join(__dirname, '..', '..', 'data/hunt-master-canonical-2026-database-candidate.json'))
    ? 'data/hunt-master-canonical-2026-database-candidate.json'
    : 'data/hunt-master-canonical-2026-foundation.json';
}

function configSources() {
  const names = [
    'HUNT_BOUNDARY_SOURCES',
    'BOUNDARY_MANIFEST_SOURCES',
    'DISPLAY_BOUNDARY_INDEX_SOURCES',
    'FINALIZED_BOUNDARY_SOURCES',
    'COMPOSITE_BOUNDARY_SOURCES',
    'HUNT_DATA_SOURCES',
    'OUTFITTERS_DATA_SOURCES',
    'OUTFITTER_FEDERAL_COVERAGE_SOURCES',
    'CONSERVATION_PERMIT_AREA_SOURCES',
    'CONSERVATION_PERMIT_HUNT_TABLE_SOURCES',
    'HUNT_RESEARCH_ENGINE_SOURCES',
    'HUNT_RESEARCH_LADDER_SOURCES',
    'HUNT_RESEARCH_MASTER_SOURCES',
    'HUNT_RESEARCH_REFERENCE_SOURCES',
  ];
  const { consumersFor } = require('./inventory');
  return names.map(name => ({ name, declared_in: 'config.js', consumed_by: consumersFor(name) }));
}

function csvDataset(file, keyFields) {
  const parsed = readCsv(file);
  const uniqueHuntCodes = [...new Set(parsed.records
    .map(row => String(row.hunt_code || row.huntCode || row.code || '').trim().toUpperCase())
    .filter(Boolean))]
    .sort();
  return { file, row_count: parsed.records.length, fields: parsed.headers, key_fields: keyFields, unique_hunt_codes: uniqueHuntCodes };
}

function buildCanonical(now = new Date().toISOString()) {
  buildSchemas();
  const contracts = Object.fromEntries(PAGES.map(page => [page.key, htmlContract(page.html)]));
  const catalogFile = canonicalDataSource();
  const huntCatalog = readJson(catalogFile, []);
  const displayIndex = readJson('processed_data/display-boundary-index-2026.json', []);
  const boundaryManifest = readJson('processed_data/boundary-manifest-2026.json', {});
  const outfittersPublic = readJson('data/outfitters-public.json', []);
  const outfittersInternal = readJson('data/outfitters.json', []);
  const outfittersCoverage = readJson('processed_data/outfitter-federal-unit-coverage-review.json', []);
  const hardCopyItems = readJson('processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json', []);

  const shared = {
    metadata: { id: 'shared-2026', generated_at: now, scope: PAGES.map(page => page.label), production_behavior: 'preserve_current_live_site_behavior' },
    versioning: { canonical_version: '2026.1.bottom-up', generator: 'scripts/build-canonical-rebuild.js', generated_files_are_derived: true },
    routes: PAGES.map(page => ({
      id: page.key,
      label: page.label,
      path: page.path,
      source_file: page.html,
      title: contracts[page.key].title || page.title,
      seo: { title: contracts[page.key].title || page.title, description: `${page.label} page in the UOGA hunt tool site.` },
      ui_contract: contracts[page.key],
    })),
    navigation: [
      { id: 'hunt-builder', label: 'HUNT BUILDER', href: './' },
      { id: 'hunt-research', label: 'HUNT RESEARCH', href: './research.html' },
      { id: 'outfitters', label: 'OUTFITTERS', href: './verify.html' },
      { id: 'hard-copies', label: 'HARD COPIES', href: './hard-copy.html' },
    ],
    assets: [
      { id: 'favicon', path: './assets/logos/favicon.ico.png' },
      { id: 'google-maps-logo', path: './assets/logos/google-maps-logo.png' },
      { id: 'google-earth-logo', path: './assets/logos/google_earth_logo.png' },
      { id: 'dwr-map-logo', path: './assets/logos/DWR-LOGO-maps.png' },
      { id: 'dwr-shield-logo', path: './assets/logos/WILDLIFE-LOGO.png' },
    ],
    config_sources: configSources(),
    owner_questions: ownerQuestions,
    regulatory_source_needed: sourceNeeded,
    provenance: sourceFiles().map(file => ({ file, role: 'implementation_inventory_source' })),
  };

  const planner = {
    metadata: { id: 'hunt-planner-2026', generated_at: now, route: './index.html', source_page: 'index.html' },
    provenance: [
      { file: 'index.html', role: 'page DOM/control contract' },
      { file: 'config.js', role: 'runtime source ordering' },
      { file: catalogFile, role: 'hunt catalog data' },
      { file: 'processed_data/display-boundary-index-2026.json', role: 'display boundary lookup' },
      { file: 'processed_data/boundary-manifest-2026.json', role: 'KMZ/merged boundary manifest' },
      { file: 'data/outfitters.json', role: 'verified outfitter cards' },
    ],
    route: shared.routes.find(route => route.id === 'hunt-planner'),
    filters: [
      { id: 'searchInput', field: 'search', type: 'text', behavior: 'live_text_filter' },
      { id: 'speciesFilter', field: 'species', type: 'select', behavior: 'live_faceted_filter' },
      { id: 'sexFilter', field: 'sex_type', type: 'select', behavior: 'live_faceted_filter' },
      { id: 'huntTypeFilter', field: 'hunt_type', type: 'select', behavior: 'live_faceted_filter' },
      { id: 'huntCategoryFilter', field: 'hunt_class', type: 'select', behavior: 'live_faceted_filter' },
      { id: 'weaponFilter', field: 'weapon', type: 'select', behavior: 'live_faceted_filter' },
      { id: 'unitFilter', field: 'hunt_name', type: 'select', behavior: 'live_faceted_filter' },
    ],
    map_modes: [
      { id: 'google', label: 'Google Maps', logo: './assets/logos/google-maps-logo.png' },
      { id: 'earth', label: 'Google Earth', logo: './assets/logos/google_earth_logo.png' },
      { id: 'dwr', label: 'Utah DWR Map', logo: './assets/logos/DWR-LOGO-maps.png' },
    ],
    land_layers: [
      { id: 'toggleDwrUnits', label: 'Hunt Units', group: 'core', default_checked: true },
      { id: 'toggleUSFS', label: 'USFS', group: 'federal', default_checked: true },
      { id: 'toggleBLM', label: 'BLM', group: 'federal', default_checked: true },
      { id: 'toggleBLMDetail', label: 'BLM Detail', group: 'federal', default_checked: false },
      { id: 'toggleSITLA', label: 'SITLA', group: 'state', default_checked: false },
      { id: 'toggleStateParks', label: 'State Parks', group: 'state', default_checked: false },
      { id: 'toggleWma', label: 'DWR WMA', group: 'state', default_checked: false },
      { id: 'togglePrivate', label: 'Private', group: 'private', default_checked: false },
      { id: 'toggleCwmu', label: 'CWMU', group: 'private', default_checked: false },
    ],
    hunt_catalog: huntCatalog,
    boundaries: {
      display_index: displayIndex,
      manifest: boundaryManifest,
      geometry_resolution_order: ['boundary_geojson_path', 'display_boundary_id', 'dwr_boundary_id', 'dwr_member_boundary_ids_fallback'],
    },
    outfitters: { public_records: outfittersPublic, internal_records: outfittersInternal, federal_coverage: outfittersCoverage },
    field_aliases_preserved: ['huntCode', 'code', 'title', 'unitName', 'unitCode', 'boundaryId', 'resolvedBoundaryIds'],
  };

  const research = {
    metadata: { id: 'hunt-research-2026', generated_at: now, route: './research.html', source_page: 'research.html' },
    provenance: [
      { file: 'research.html', role: 'page DOM/control contract' },
      { file: 'hunt-research.js', role: 'research interaction and probability display behavior' },
      { file: 'processed_data/draw_reality_engine.csv', role: 'draw engine rows' },
      { file: 'processed_data/point_ladder_view.csv', role: 'point ladder rows' },
      { file: 'processed_data/hunt_master_enriched.csv', role: 'hunt metadata rows' },
      { file: 'processed_data/hunt_unit_reference_linked.csv', role: 'source/provenance rows' },
    ],
    route: shared.routes.find(route => route.id === 'hunt-research'),
    input_controls: [
      { id: 'huntCodeInput', field: 'hunt_code', type: 'text' },
      { id: 'residencySelect', field: 'residency', type: 'select', options: ['Resident', 'Nonresident'] },
      { id: 'pointsInput', field: 'points', type: 'number' },
    ],
    local_storage_keys: ['selected_hunt_code', 'uoga_hunt_basket_v1', 'selected_hunt_research_points'],
    odds_selection_policy: [
      'Prefer display_odds_pct when present.',
      'Else prefer p_draw_mean converted from decimal to percent when present.',
      'Else use legacy projected odds fields.',
      'Never treat status MAX POOL as automatic 100 percent.',
      'Guaranteed only when guaranteed_probability >= 0.999 or simulator proof later exists.',
    ],
    modeled_fields: ['display_odds_pct', 'p_draw_mean', 'p_draw_p10', 'p_draw_p50', 'p_draw_p90', 'p_reserved_mean', 'p_random_mean', 'p_preference_mean', 'p_youth_mean', 'expected_cutoff_points', 'cutoff_bucket_probability', 'guaranteed_probability', 'reason_codes', 'model_version', 'rule_version', 'data_quality_grade', 'quota_source', 'data_cutoff_date'],
    legacy_fields: ['odds_2026_projected', 'max_pool_projection_2026', 'random_draw_odds_2026', 'draw_outlook', 'trend', 'status', 'gap', 'guaranteed_at_2026'],
    hunt_quality_fields: ['avg_days_2026', 'satisfaction_2026'],
    datasets: {
      draw_reality_engine: csvDataset('processed_data/draw_reality_engine.csv', ['hunt_code', 'residency', 'points']),
      point_ladder_view: csvDataset('processed_data/point_ladder_view.csv', ['hunt_code', 'residency', 'points']),
      hunt_master_enriched: csvDataset('processed_data/hunt_master_enriched.csv', ['hunt_code', 'residency', 'points']),
      hunt_unit_reference_linked: csvDataset('processed_data/hunt_unit_reference_linked.csv', ['hunt_code', 'residency']),
    },
  };

  const hardCopies = {
    metadata: { id: 'hard-copies-2026', generated_at: now, route: './hard-copy.html', source_page: 'hard-copy.html' },
    provenance: [
      { file: 'hard-copy.html', role: 'page DOM/rendering contract' },
      { file: 'processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json', role: 'visitor PDF library manifest' },
    ],
    route: shared.routes.find(route => route.id === 'hard-copies'),
    manifest_url: './processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json',
    group_labels: {
      draw_odds: 'Draw Odds / Results',
      harvest_report: 'Harvest Reports',
      conservation_permits: 'Conservation Permits',
      regulation: 'Regulations / Guidebooks',
    },
    filters: [
      { id: 'librarySearch', field: 'title/subtitle/type/group/year', type: 'search' },
      { id: 'libraryTypeFilter', field: 'type', type: 'select' },
      { id: 'libraryYearFilter', field: 'year', type: 'select' },
      { id: 'libraryChips', field: 'group', type: 'tablist' },
    ],
    library: { items: hardCopyItems },
  };

  const outfitterVerification = {
    metadata: { id: 'outfitter-verification-2026', generated_at: now, route: './verify.html', source_page: 'verify.html' },
    provenance: [
      { file: 'verify.html', role: 'verification standards content and modal behavior' },
      { file: 'data/outfitters.json', role: 'current outfitter listing fields used on planner cards' },
      { file: 'processed_data/outfitter-federal-unit-coverage-review.json', role: 'unit coverage evidence' },
    ],
    route: shared.routes.find(route => route.id === 'outfitter-verification'),
    designation_levels: [
      { id: 'verified', label: 'Verified', public: true },
      { id: 'cpo', label: 'Certified Professional Outfitter (C.P.O.)', public: true },
      { id: 'not-published', label: 'Not published', public: false },
    ],
    standards: verifyStandards(),
    modal: {
      id: 'dwrOutfitterModal',
      frame_id: 'dwrOutfitterFrame',
      fallback_id: 'dwrOutfitterFallback',
      dwr_url: 'https://wildlife.utah.gov/guide/outfitter.html',
    },
    outfitters: { public_records: outfittersPublic, internal_records: outfittersInternal, federal_coverage: outfittersCoverage },
    source_needed: sourceNeeded,
  };

  return { shared, planner, research, hardCopies, outfitterVerification, ownerQuestions, sourceNeeded };
}

function writeCanonicalPackage(pkg) {
  writeJson('canonical/shared-2026.json', pkg.shared);
  writeJson('canonical/hunt-planner-2026.json', pkg.planner);
  writeJson('canonical/hunt-research-2026.json', pkg.research);
  writeJson('canonical/hard-copies-2026.json', pkg.hardCopies);
  writeJson('canonical/outfitter-verification-2026.json', pkg.outfitterVerification);
}

function pageData(pkg) {
  return {
    'hunt-planner': {
      generated_from: 'canonical/hunt-planner-2026.json',
      route: pkg.planner.route,
      filters: pkg.planner.filters,
      map_modes: pkg.planner.map_modes,
      land_layers: pkg.planner.land_layers,
      hunt_catalog: pkg.planner.hunt_catalog,
      boundaries: pkg.planner.boundaries,
      outfitters: pkg.planner.outfitters,
    },
    'hunt-research': {
      generated_from: 'canonical/hunt-research-2026.json',
      route: pkg.research.route,
      input_controls: pkg.research.input_controls,
      odds_selection_policy: pkg.research.odds_selection_policy,
      modeled_fields: pkg.research.modeled_fields,
      legacy_fields: pkg.research.legacy_fields,
      hunt_quality_fields: pkg.research.hunt_quality_fields,
      datasets: pkg.research.datasets,
    },
    'hard-copies': {
      generated_from: 'canonical/hard-copies-2026.json',
      route: pkg.hardCopies.route,
      group_labels: pkg.hardCopies.group_labels,
      filters: pkg.hardCopies.filters,
      library: pkg.hardCopies.library,
    },
    'outfitter-verification': {
      generated_from: 'canonical/outfitter-verification-2026.json',
      route: pkg.outfitterVerification.route,
      designation_levels: pkg.outfitterVerification.designation_levels,
      standards: pkg.outfitterVerification.standards,
      modal: pkg.outfitterVerification.modal,
      outfitters: pkg.outfitterVerification.outfitters,
    },
  };
}

function writePageData(pkg) {
  const pages = pageData(pkg);
  for (const [key, value] of Object.entries(pages)) writeJson(`generated/pages/${key}.json`, value);
  return pages;
}

function buildAndWriteAll(now = new Date().toISOString()) {
  const pkg = buildCanonical(now);
  writeCanonicalPackage(pkg);
  const generatedPages = writePageData(pkg);
  const usage = buildUsageMap();
  writeUsageMap(usage);
  return { pkg, generatedPages, usage };
}

module.exports = {
  buildCanonical,
  buildAndWriteAll,
  writeCanonicalPackage,
  writePageData,
  pageData,
  ownerQuestions,
  sourceNeeded,
};
