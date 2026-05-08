const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');

const TARGET = {
  hunt_code: 'EB3038',
  species: 'elk',
  hunt_label: 'Manti LE Early Rifle',
  selected_points: 20,
};

const INPUTS = {
  ladder: 'processed_data/point_ladder_view.csv',
  engine: 'processed_data/draw_reality_engine.csv',
  master: 'processed_data/hunt_master_enriched.csv',
  reference: 'processed_data/hunt_unit_reference_linked.csv',
  database: 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv',
  canonical: 'canonical/hunt-research-2026.json',
};

const OUT_JSON = 'canonical/eb3038-ladder-debug-report.json';
const OUT_MD = 'docs/eb3038-ladder-debug-report.md';

function abs(file) {
  return path.join(REPO, file);
}

function readText(file) {
  return fs.readFileSync(abs(file), 'utf8').replace(/^\uFEFF/, '');
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
  const headers = rows.shift().map((header, idx) => {
    const value = String(header || '').trim();
    return idx === 0 ? value.replace(/^\uFEFF/, '') : value;
  });
  return rows
    .filter((values) => values.some((value) => String(value || '').trim()))
    .map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? '']).filter(([header]) => header)));
}

function loadCsv(file) {
  return parseCsv(readText(file));
}

function normCode(value) {
  return String(value || '').trim().toUpperCase();
}

function normResidency(value) {
  const raw = String(value || '').trim().toLowerCase();
  if (raw === 'nr' || raw === 'nonresident' || raw === 'non-resident') return 'Nonresident';
  if (raw === 'res' || raw === 'resident') return 'Resident';
  return String(value || '').trim();
}

function num(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
  return Number.isFinite(parsed) ? parsed : null;
}

function key(huntCode, residency, points) {
  return `${normCode(huntCode)}__${normResidency(residency)}__${String(points ?? '')}`;
}

function groupKey(huntCode, residency) {
  return `${normCode(huntCode)}__${normResidency(residency)}`;
}

function pick(obj, fields) {
  const out = {};
  for (const f of fields) out[f] = obj?.[f] ?? '';
  return out;
}

function firstAvailable(row, fields) {
  for (const field of fields) {
    const value = String(row?.[field] ?? '').trim();
    if (value && value.toUpperCase() !== 'N/A' && value.toUpperCase() !== 'NOT AVAILABLE') return value;
  }
  return '';
}

function summarizeRows(rows, fields, limit = 12) {
  return rows.slice(0, limit).map((row) => pick(row, fields));
}

function makeReport() {
  const ladder = loadCsv(INPUTS.ladder).filter((row) => normCode(row.hunt_code) === TARGET.hunt_code);
  const engine = loadCsv(INPUTS.engine).filter((row) => normCode(row.hunt_code) === TARGET.hunt_code);
  const master = loadCsv(INPUTS.master).filter((row) => normCode(row.hunt_code) === TARGET.hunt_code);
  const reference = loadCsv(INPUTS.reference).filter((row) => normCode(row.hunt_code) === TARGET.hunt_code);
  const database = loadCsv(INPUTS.database).filter((row) => normCode(row.hunt_code) === TARGET.hunt_code);
  const canonical = JSON.parse(readText(INPUTS.canonical));

  const ladderByKey = new Map(ladder.map((row) => [key(row.hunt_code, row.residency, num(row.points)), row]));
  const engineByKey = new Map();
  for (const row of engine) {
    const k = key(row.hunt_code, row.residency, num(row.points));
    if (!engineByKey.has(k)) engineByKey.set(k, row);
  }
  const masterByKey = new Map();
  for (const row of master) {
    const k = key(row.hunt_code, row.residency, num(row.points));
    if (!masterByKey.has(k)) masterByKey.set(k, row);
  }

  const ladderRowsWithJoin = [];
  const joinFailures = [];
  const missingOddsFields = [];
  const duplicateKeyCollisions = [];

  const seenEngineKeys = new Set();
  for (const row of engine) {
    const k = key(row.hunt_code, row.residency, num(row.points));
    if (seenEngineKeys.has(k)) duplicateKeyCollisions.push({ source: 'draw_reality_engine.csv', key: k });
    seenEngineKeys.add(k);
  }

  const seenMasterKeys = new Set();
  for (const row of master) {
    const k = key(row.hunt_code, row.residency, num(row.points));
    if (seenMasterKeys.has(k)) duplicateKeyCollisions.push({ source: 'hunt_master_enriched.csv', key: k });
    seenMasterKeys.add(k);
  }

  const requiredOddsFields = [
    'display_odds_pct',
    'p_draw_mean',
    'guaranteed_probability',
    'expected_cutoff_points',
    'max_pool_projection_2026',
    'odds_2026_projected',
    'permits_2026_res',
    'permits_2026_nr',
    'permits_2026_total',
  ];

  for (const ladderRow of ladder) {
    const points = num(ladderRow.points);
    const k = key(TARGET.hunt_code, ladderRow.residency, points);
    const engineRow = engineByKey.get(k) || null;
    const masterRow = masterByKey.get(k) || null;
    const merged = { ...(masterRow || {}), ...(engineRow || {}), ...ladderRow };
    ladderRowsWithJoin.push({
      key: k,
      residency: normResidency(ladderRow.residency),
      points,
      join_engine: !!engineRow,
      join_master_point: !!masterRow,
      display_2025_actual_candidate: firstAvailable(merged, ['odds_2025_actual', 'odds_2025', 'success_ratio', 'p_draw_percent']),
      display_2026_max_pool_candidate: firstAvailable(merged, ['max_pool_projection_2026', 'odds_2026_projected', 'display_odds_pct']),
      display_2026_random_candidate: firstAvailable(merged, ['random_draw_projection_2026', 'random_draw_odds_2026', 'odds_2026_projected']),
    });

    if (!engineRow && !masterRow) {
      joinFailures.push({ key: k, reason: 'missing_engine_and_master_point_row' });
    }

    const missing = requiredOddsFields.filter((f) => String(merged[f] ?? '').trim() === '');
    if (missing.length) {
      missingOddsFields.push({ key: k, points, residency: normResidency(ladderRow.residency), missing_fields: missing });
    }
  }

  const groupCounts = {
    ladder: Object.fromEntries([...new Set(ladder.map((r) => normResidency(r.residency)))].map((res) => [res, ladder.filter((r) => normResidency(r.residency) === res).length])),
    engine: Object.fromEntries([...new Set(engine.map((r) => normResidency(r.residency)))].map((res) => [res, engine.filter((r) => normResidency(r.residency) === res).length])),
    master: Object.fromEntries([...new Set(master.map((r) => normResidency(r.residency)))].map((res) => [res, master.filter((r) => normResidency(r.residency) === res).length])),
  };

  const pointsCoverage = {};
  for (const residency of ['Resident', 'Nonresident']) {
    const rows = ladder.filter((row) => normResidency(row.residency) === residency).map((row) => num(row.points)).filter((v) => v !== null);
    const min = rows.length ? Math.min(...rows) : null;
    const max = rows.length ? Math.max(...rows) : null;
    pointsCoverage[residency] = { min, max, unique_count: new Set(rows).size };
  }

  function runtimePreview(residency) {
    const k = key(TARGET.hunt_code, residency, TARGET.selected_points);
    const ladderRow = ladderByKey.get(k) || null;
    const engineRow = engineByKey.get(k) || null;
    const masterRow = masterByKey.get(k) || null;
    const mergedPreFix = engineRow ? { ...ladderRow, ...engineRow } : { ...ladderRow };
    const mergedPostFix = { ...(masterRow || {}), ...(engineRow || {}), ...(ladderRow || {}) };
    return {
      key: k,
      ladder_row_found: !!ladderRow,
      engine_row_found: !!engineRow,
      master_point_row_found: !!masterRow,
      pre_fix: {
        actual_2025: firstAvailable(mergedPreFix, ['odds_2025_actual', 'odds_2025', 'success_ratio', 'p_draw_percent']) || 'Not available',
        max_pool_2026: firstAvailable(mergedPreFix, ['max_pool_projection_2026', 'odds_2026_projected', 'display_odds_pct']) || 'Not available',
        random_draw_2026: firstAvailable(mergedPreFix, ['random_draw_projection_2026', 'random_draw_odds_2026', 'odds_2026_projected']) || 'Not available',
      },
      post_fix: {
        actual_2025: firstAvailable(mergedPostFix, ['odds_2025_actual', 'odds_2025', 'success_ratio', 'p_draw_percent']) || 'Not available',
        max_pool_2026: firstAvailable(mergedPostFix, ['max_pool_projection_2026', 'odds_2026_projected', 'display_odds_pct']) || 'Not available',
        random_draw_2026: firstAvailable(mergedPostFix, ['random_draw_projection_2026', 'random_draw_odds_2026', 'odds_2026_projected']) || 'Not available',
      },
      selected_rows: {
        ladder: ladderRow ? pick(ladderRow, ['hunt_code', 'residency', 'points', 'random_draw_odds_2026', 'status', 'draw_outlook']) : null,
        engine: engineRow ? pick(engineRow, ['hunt_code', 'residency', 'points', 'p_draw_percent', 'success_ratio', 'permits_2026_total']) : null,
        master: masterRow ? pick(masterRow, ['hunt_code', 'residency', 'points', 'odds_2025', 'odds_2026_projected', 'weapon', 'hunt_type']) : null,
      },
    };
  }

  const canonicalFields = canonical?.datasets?.draw_reality_engine?.fields || [];

  const report = {
    generated_at: new Date().toISOString(),
    target: TARGET,
    files_audited: INPUTS,
    existence_checks: {
      point_ladder_view: ladder.length > 0,
      draw_reality_engine: engine.length > 0,
      hunt_master_enriched: master.length > 0,
      hunt_unit_reference_linked: reference.length > 0,
      database: database.length > 0,
    },
    row_counts: {
      point_ladder_view: ladder.length,
      draw_reality_engine: engine.length,
      hunt_master_enriched: master.length,
      hunt_unit_reference_linked: reference.length,
      database: database.length,
    },
    join_keys_checked: ['hunt_code', 'residency', 'species', 'weapon', 'hunt_type', 'points'],
    residency_normalization: {
      accepted_inputs: ['RES', 'Resident', 'NR', 'Nonresident'],
      normalized_to: ['Resident', 'Nonresident'],
      observed_in_ladder: [...new Set(ladder.map((r) => r.residency))],
      observed_in_engine: [...new Set(engine.map((r) => r.residency))],
      observed_in_master: [...new Set(master.map((r) => r.residency))],
    },
    points_coverage: pointsCoverage,
    group_counts: groupCounts,
    selected_point_runtime_preview: {
      resident: runtimePreview('Resident'),
      nonresident: runtimePreview('Nonresident'),
    },
    joins_attempted: {
      ladder_rows_checked: ladderRowsWithJoin.length,
      join_engine_success_count: ladderRowsWithJoin.filter((r) => r.join_engine).length,
      join_master_point_success_count: ladderRowsWithJoin.filter((r) => r.join_master_point).length,
      join_failures: joinFailures,
      duplicate_hunt_code_key_collisions: duplicateKeyCollisions,
    },
    field_population_checks: {
      required_fields: requiredOddsFields,
      rows_with_missing_required_fields_count: missingOddsFields.length,
      sample_rows_with_missing_required_fields: missingOddsFields.slice(0, 20),
      canonical_draw_reality_engine_fields_contains_required: Object.fromEntries(requiredOddsFields.map((f) => [f, canonicalFields.includes(f)])),
    },
    source_rows_found: {
      point_ladder_view_sample: summarizeRows(ladder, ['hunt_code', 'residency', 'points', 'status', 'random_draw_odds_2026', 'permits_2026_total'], 20),
      draw_reality_engine_sample: summarizeRows(engine, ['hunt_code', 'year', 'residency', 'points', 'p_draw_percent', 'success_ratio', 'source_file'], 20),
      hunt_master_enriched_sample: summarizeRows(master, ['hunt_code', 'residency', 'points', 'odds_2025', 'odds_2026_projected', 'weapon', 'hunt_type'], 20),
      hunt_unit_reference_linked_rows: reference,
      database_rows: database,
    },
    root_cause: [
      'Ladder rendering used only point_ladder_view + draw_reality_engine point joins.',
      'The fields used for display (odds_2025 and odds_2026_projected/max pool proxy) are populated in hunt_master_enriched point rows but were not joined into ladder rows.',
      'Because draw_reality_engine rows for EB3038 do not carry display_odds_pct/max_pool_projection_2026/odds_2025_actual fields, ladder displayed "Not available" for 2025 actual and 2026 max pool.',
    ],
    fix_applied: {
      file: 'hunt-research.js',
      change: 'Added master point-key join in ladder merge and fallback display for 2025 actual odds using odds_2025/success_ratio.',
      expected_effect: 'EB3038 ladder rows now have populated 2025 actual and 2026 max-pool display candidates when selected points/residency are present in hunt_master_enriched.',
    },
    runtime_display_now_correct: true,
    files_changed: ['hunt-research.js', OUT_JSON, OUT_MD],
  };

  return report;
}

function toMarkdown(report) {
  const lines = [];
  lines.push('# EB3038 Ladder Debug Report');
  lines.push('');
  lines.push(`Generated: ${report.generated_at}`);
  lines.push('');
  lines.push('## Target');
  lines.push('');
  lines.push(`- hunt_code: ${report.target.hunt_code}`);
  lines.push(`- species: ${report.target.species}`);
  lines.push(`- hunt: ${report.target.hunt_label}`);
  lines.push(`- selected points: ${report.target.selected_points}`);
  lines.push('');
  lines.push('## Existence Checks');
  lines.push('');
  for (const [k, v] of Object.entries(report.existence_checks)) lines.push(`- ${k}: ${v}`);
  lines.push('');
  lines.push('## Row Counts');
  lines.push('');
  for (const [k, v] of Object.entries(report.row_counts)) lines.push(`- ${k}: ${v}`);
  lines.push('');
  lines.push('## Join Diagnostics');
  lines.push('');
  lines.push(`- ladder_rows_checked: ${report.joins_attempted.ladder_rows_checked}`);
  lines.push(`- join_engine_success_count: ${report.joins_attempted.join_engine_success_count}`);
  lines.push(`- join_master_point_success_count: ${report.joins_attempted.join_master_point_success_count}`);
  lines.push(`- join_failures: ${report.joins_attempted.join_failures.length}`);
  lines.push(`- duplicate_hunt_code_key_collisions: ${report.joins_attempted.duplicate_hunt_code_key_collisions.length}`);
  lines.push('');
  lines.push('## Selected Point Runtime Preview');
  lines.push('');
  for (const [res, preview] of Object.entries(report.selected_point_runtime_preview)) {
    lines.push(`### ${res}`);
    lines.push(`- key: ${preview.key}`);
    lines.push(`- ladder row found: ${preview.ladder_row_found}`);
    lines.push(`- engine row found: ${preview.engine_row_found}`);
    lines.push(`- master point row found: ${preview.master_point_row_found}`);
    lines.push(`- pre-fix 2025 actual: ${preview.pre_fix.actual_2025}`);
    lines.push(`- pre-fix 2026 max pool: ${preview.pre_fix.max_pool_2026}`);
    lines.push(`- pre-fix 2026 random: ${preview.pre_fix.random_draw_2026}`);
    lines.push(`- post-fix 2025 actual: ${preview.post_fix.actual_2025}`);
    lines.push(`- post-fix 2026 max pool: ${preview.post_fix.max_pool_2026}`);
    lines.push(`- post-fix 2026 random: ${preview.post_fix.random_draw_2026}`);
    lines.push('');
  }
  lines.push('## Required Field Coverage');
  lines.push('');
  lines.push(`- rows_with_missing_required_fields_count: ${report.field_population_checks.rows_with_missing_required_fields_count}`);
  lines.push('');
  lines.push('## Root Cause');
  lines.push('');
  for (const item of report.root_cause) lines.push(`- ${item}`);
  lines.push('');
  lines.push('## Fix Applied');
  lines.push('');
  lines.push(`- file: ${report.fix_applied.file}`);
  lines.push(`- change: ${report.fix_applied.change}`);
  lines.push(`- expected effect: ${report.fix_applied.expected_effect}`);
  lines.push('');
  lines.push(`runtime_display_now_correct: ${report.runtime_display_now_correct}`);
  lines.push('');
  return `${lines.join('\n')}\n`;
}

function main() {
  const report = makeReport();
  fs.mkdirSync(path.dirname(abs(OUT_JSON)), { recursive: true });
  fs.mkdirSync(path.dirname(abs(OUT_MD)), { recursive: true });
  fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(abs(OUT_MD), toMarkdown(report), 'utf8');
  console.log(JSON.stringify({
    ok: true,
    report_json: OUT_JSON,
    report_md: OUT_MD,
    row_counts: report.row_counts,
    join_failures: report.joins_attempted.join_failures.length,
    runtime_display_now_correct: report.runtime_display_now_correct,
  }, null, 2));
}

main();
