const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const crypto = require('crypto');
const zlib = require('zlib');

const ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'processed_data', 'public_contracts');

const INPUT_CANDIDATES = {
  predictive: [
    path.join(ROOT, 'processed_data', 'draw_reality_engine_predictive_v2.csv'),
    path.join(ROOT, 'processed_data', 'draw_reality_engine_v2.csv'),
    path.join(ROOT, 'data', 'utah', 'fixtures', 'draw_reality_engine.csv'),
  ],
  oddsHistory: [
    path.join(ROOT, 'processed_data', 'draw_reality_engine_v2.csv'),
    path.join(ROOT, 'processed_data', 'draw_reality_engine_predictive_v2.csv'),
    path.join(ROOT, 'data', 'utah', 'fixtures', 'draw_reality_engine.csv'),
  ],
  outlook: [
    path.join(ROOT, 'processed_data', 'research_page', 'hunt_application_outlook.json'),
  ],
  outfittersPublic: [
    path.join(ROOT, 'data', 'outfitters-public.json'),
    path.join(ROOT, 'data', 'outfitters.json'),
  ],
  huntUnitsLite: [
    path.join(ROOT, 'data', 'hunt-boundaries-lite.geojson'),
    path.join(ROOT, 'data', 'hunt_boundaries.geojson'),
  ],
};

function rel(filePath) {
  return path.relative(ROOT, filePath).replace(/\\/g, '/');
}

async function ensureDir(dirPath) {
  await fsp.mkdir(dirPath, { recursive: true });
}

async function exists(filePath) {
  try {
    await fsp.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function resolveInput(role, candidates = []) {
  for (const candidate of candidates) {
    if (await exists(candidate)) {
      return { role, filePath: candidate, exists: true };
    }
  }
  return { role, filePath: candidates[0] || '', exists: false };
}

function decodeMaybeGzip(buffer) {
  return buffer.length >= 2 && buffer[0] === 0x1f && buffer[1] === 0x8b
    ? zlib.gunzipSync(buffer).toString('utf8')
    : buffer.toString('utf8');
}

async function readText(filePath) {
  const buffer = await fsp.readFile(filePath);
  return decodeMaybeGzip(buffer).replace(/^\uFEFF/, '');
}

function parseCsvLine(line) {
  const cells = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === ',' && !quoted) {
      cells.push(cell);
      cell = '';
    } else {
      cell += ch;
    }
  }
  cells.push(cell);
  return cells;
}

function parseCsv(text) {
  const rows = [];
  let line = '';
  let quoted = false;
  const lines = [];
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') {
        line += ch + text[i + 1];
        i += 1;
        continue;
      }
      quoted = !quoted;
    }
    if ((ch === '\n' || ch === '\r') && !quoted) {
      if (ch === '\r' && text[i + 1] === '\n') i += 1;
      lines.push(line);
      line = '';
    } else {
      line += ch;
    }
  }
  if (line) lines.push(line);
  const nonEmpty = lines.filter((entry) => entry.trim());
  if (!nonEmpty.length) return rows;
  const headers = parseCsvLine(nonEmpty[0]).map((header) => header.trim());
  for (const rawLine of nonEmpty.slice(1)) {
    const cells = parseCsvLine(rawLine);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = cells[index] ?? '';
    });
    rows.push(row);
  }
  return rows;
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(rows, outPath, preferredColumns = []) {
  const columns = preferredColumns.length
    ? preferredColumns
    : Array.from(rows.reduce((set, row) => {
      Object.keys(row || {}).forEach((key) => set.add(key));
      return set;
    }, new Set()));
  const lines = [columns.join(',')];
  rows.forEach((row) => {
    lines.push(columns.map((column) => csvEscape(row?.[column])).join(','));
  });
  return fsp.writeFile(outPath, `${lines.join('\n')}\n`, 'utf8');
}

function clean(value) {
  const text = String(value ?? '').trim();
  return text && !['NULL', 'NONE', 'N/A', 'NA', 'NOT AVAILABLE', 'UNDEFINED'].includes(text.toUpperCase()) ? text : '';
}

function first(row, keys) {
  for (const key of keys) {
    const value = clean(row?.[key]);
    if (value) return value;
  }
  return '';
}

function numberOrBlank(value) {
  const text = clean(value);
  if (!text) return '';
  const parsed = Number(text.replace(/[^0-9.-]/g, ''));
  return Number.isFinite(parsed) ? parsed : '';
}

function uniqueBy(rows, keyFn) {
  const seen = new Set();
  const output = [];
  rows.forEach((row) => {
    const key = keyFn(row);
    if (!key || seen.has(key)) return;
    seen.add(key);
    output.push(row);
  });
  return output;
}

function toArray(value) {
  return Array.isArray(value) ? value : [];
}

function inferReportedYear(row) {
  const direct = first(row, ['year', 'source_year', 'reported_hunt_year', 'quota_source_year']);
  if (direct) return direct;
  const predictionYear = Number(first(row, ['prediction_year']));
  if (Number.isFinite(predictionYear) && predictionYear > 0) return String(predictionYear - 1);
  return '';
}

async function fileSnapshot(filePath, role) {
  try {
    const buffer = await fsp.readFile(filePath);
    const decoded = decodeMaybeGzip(buffer);
    const rowCount = filePath.toLowerCase().endsWith('.csv')
      ? Math.max(0, decoded.split(/\r?\n/).filter(Boolean).length - 1)
      : Array.isArray(JSON.parse(decoded || '[]'))
        ? JSON.parse(decoded || '[]').length
        : null;
    return {
      file_path: rel(filePath),
      role,
      exists: true,
      size_bytes: buffer.length,
      sha256: crypto.createHash('sha256').update(buffer).digest('hex'),
      row_count: rowCount,
    };
  } catch (error) {
    return {
      file_path: rel(filePath),
      role,
      exists: false,
      size_bytes: 0,
      sha256: '',
      row_count: null,
      error: error.message,
    };
  }
}

async function main() {
  await ensureDir(OUT_DIR);

  const inputResolution = {
    predictive: await resolveInput('predictive', INPUT_CANDIDATES.predictive),
    oddsHistory: await resolveInput('oddsHistory', INPUT_CANDIDATES.oddsHistory),
    outlook: await resolveInput('outlook', INPUT_CANDIDATES.outlook),
    outfittersPublic: await resolveInput('outfittersPublic', INPUT_CANDIDATES.outfittersPublic),
    huntUnitsLite: await resolveInput('huntUnitsLite', INPUT_CANDIDATES.huntUnitsLite),
  };

  const predictiveRows = inputResolution.predictive.exists
    ? parseCsv(await readText(inputResolution.predictive.filePath))
    : [];
  const oddsRows = inputResolution.oddsHistory.exists
    ? parseCsv(await readText(inputResolution.oddsHistory.filePath))
    : [];
  const outlookRows = inputResolution.outlook.exists
    ? toArray(JSON.parse(await readText(inputResolution.outlook.filePath)))
    : [];
  let outfittersRows = inputResolution.outfittersPublic.exists
    ? toArray(JSON.parse(await readText(inputResolution.outfittersPublic.filePath)))
    : [];
  let outfittersFallbackPath = '';
  if (!outfittersRows.length) {
    for (const candidate of INPUT_CANDIDATES.outfittersPublic.slice(1)) {
      if (!(await exists(candidate))) continue;
      try {
        const rows = toArray(JSON.parse(await readText(candidate)));
        if (rows.length) {
          outfittersRows = rows;
          outfittersFallbackPath = candidate;
          break;
        }
      } catch {
        // Ignore malformed fallback and continue.
      }
    }
  }

  let predictionRows = predictiveRows.map((row) => ({
    hunt_code: first(row, ['hunt_code']),
    hunt_name: first(row, ['hunt_name', 'unit_name', 'unit']),
    species: first(row, ['species', 'sportsman_species']),
    sex_type: first(row, ['sex_type']),
    weapon: first(row, ['weapon']),
    hunt_type: first(row, ['hunt_type']),
    hunt_class: first(row, ['hunt_class']),
    residency: first(row, ['residency']),
    points: first(row, ['points']),
    draw_pool: first(row, ['draw_pool']),
    modeled_draw_probability: numberOrBlank(first(row, ['p_draw_mean', 'p_draw', 'p_availability'])),
    modeled_draw_probability_pct: numberOrBlank(first(row, ['p_draw_pct', 'availability_pct'])),
    guaranteed_line_points: first(row, ['guaranteed_at_2026', 'projected_2026_max_cutoff_point']),
    status: first(row, ['status', 'draw_outlook', 'availability_status']),
    model_version: first(row, ['model_version']),
    rule_version: first(row, ['rule_version']),
    source_file: first(row, ['source_file', 'sportsman_source_file', 'quota_source_file', 'truth_source_file']),
    data_quality_flags: first(row, ['data_quality_flags', 'reason_codes']),
  })).filter((row) => row.hunt_code);

  let oddsHistoryRows = oddsRows.map((row) => ({
    hunt_code: first(row, ['hunt_code']),
    boundary_id: first(row, ['boundary_id']),
    hunt_name: first(row, ['hunt_name']),
    species: first(row, ['species']),
    sex_type: first(row, ['sex_type']),
    weapon: first(row, ['weapon']),
    hunt_type: first(row, ['hunt_type']),
    hunt_class: first(row, ['hunt_class']),
    reported_hunt_year: inferReportedYear(row),
    model_target_year: inferReportedYear(row) ? Number(inferReportedYear(row)) + 1 : '',
    draw_pool: first(row, ['draw_pool']),
    residency: first(row, ['residency']),
    points: first(row, ['points']),
    eligible_applicants: numberOrBlank(first(row, ['eligible_applicants', 'applicants', 'forecast_applicants_at_level'])),
    bonus_permits: numberOrBlank(first(row, ['bonus_permits'])),
    regular_permits: numberOrBlank(first(row, ['regular_permits'])),
    total_permits: numberOrBlank(first(row, ['total_permits', 'permits_2026_total', 'permit_allotment_2026_total', 'quota_2026_total'])),
    success_ratio: numberOrBlank(first(row, ['success_ratio', 'p_draw_mean'])),
    source_file: first(row, ['source_file', 'truth_source_file']),
    source_pdf_page: first(row, ['source_pdf_page', 'source_report_page']),
    validation_status: first(row, ['validation_status', 'data_quality_grade', 'status']),
  })).filter((row) => row.hunt_code);

  const contractOutlookRows = outlookRows.map((row) => ({
    hunt_code: first(row, ['hunt_code']),
    hunt_name: first(row, ['hunt_name']),
    species: first(row, ['species']),
    residency: first(row, ['residency']),
    draw_family: first(row, ['draw_family']),
    draw_pool: first(row, ['draw_pool']),
    hunt_class: first(row, ['hunt_class']),
    weapon: first(row, ['weapon']),
    unit_name: first(row, ['unit_name']),
    boundary_id: first(row, ['boundary_id']),
    modeled_draw_probability: first(row, ['modeled_draw_probability']),
    guaranteed_line_points: first(row, ['guaranteed_line_points']),
    point_creep_1yr: first(row, ['point_creep_1yr']),
    permits_2026_res: first(row, ['permits_2026_res']),
    permits_2026_nonres: first(row, ['permits_2026_nonres']),
    permits_2026_total: first(row, ['permits_2026_total']),
    harvest_success_pct: first(row, ['harvest_success_pct']),
    average_days_hunted: first(row, ['average_days_hunted']),
    average_harvest_age: first(row, ['average_harvest_age']),
    current_age_3yr_average: first(row, ['current_age_3yr_average']),
    percent_5plus: first(row, ['percent_5plus']),
    management_objective_type: first(row, ['management_objective_type']),
    management_objective_range: first(row, ['management_objective_range']),
    management_objective_status: first(row, ['management_objective_status']),
    decision_label: first(row, ['decision_label']),
    recommended_action: first(row, ['recommended_action']),
    data_confidence: first(row, ['data_confidence']),
    source_badges: first(row, ['source_badges']),
  })).filter((row) => row.hunt_code);

  let predictionFallbackFromOutlook = false;
  if ((!predictionRows.length || (predictionRows.length < 100 && contractOutlookRows.length >= 100)) && contractOutlookRows.length) {
    predictionFallbackFromOutlook = true;
    predictionRows = contractOutlookRows.map((row) => {
      const probability = numberOrBlank(row.modeled_draw_probability);
      return {
      hunt_code: row.hunt_code,
      hunt_name: row.hunt_name,
      species: row.species,
      sex_type: '',
      weapon: row.weapon,
      hunt_type: row.draw_family,
      hunt_class: row.hunt_class,
      residency: row.residency,
      points: '',
      draw_pool: row.draw_pool,
      modeled_draw_probability: probability,
      modeled_draw_probability_pct: probability === '' ? '' : probability * 100,
      guaranteed_line_points: row.guaranteed_line_points,
      status: row.decision_label || '',
      model_version: 'contract_fallback_from_outlook',
      rule_version: '',
      source_file: inputResolution.outlook.exists ? rel(inputResolution.outlook.filePath) : '',
      data_quality_flags: row.data_confidence || '',
    };
    });
  }

  let oddsFallbackFromOutlook = false;
  if ((!oddsHistoryRows.length || (oddsHistoryRows.length < 100 && contractOutlookRows.length >= 100)) && contractOutlookRows.length) {
    oddsFallbackFromOutlook = true;
    oddsHistoryRows = contractOutlookRows.map((row) => ({
      hunt_code: row.hunt_code,
      boundary_id: row.boundary_id,
      hunt_name: row.hunt_name,
      species: row.species,
      sex_type: '',
      weapon: row.weapon,
      hunt_type: row.draw_family,
      hunt_class: row.hunt_class,
      reported_hunt_year: '2025',
      model_target_year: 2026,
      draw_pool: row.draw_pool,
      residency: row.residency,
      points: '',
      eligible_applicants: '',
      bonus_permits: '',
      regular_permits: '',
      total_permits: numberOrBlank(row.permits_2026_total),
      success_ratio: numberOrBlank(row.modeled_draw_probability),
      source_file: inputResolution.outlook.exists ? rel(inputResolution.outlook.filePath) : '',
      source_pdf_page: '',
      validation_status: row.data_confidence || '',
    }));
  }

  const huntUnitsOut = path.join(OUT_DIR, 'hunt_units.geojson');
  if (inputResolution.huntUnitsLite.exists) {
    await fsp.copyFile(inputResolution.huntUnitsLite.filePath, huntUnitsOut);
  } else {
    await fsp.writeFile(huntUnitsOut, JSON.stringify({
      type: 'FeatureCollection',
      metadata: {
        generated_at: new Date().toISOString(),
        note: 'Boundary source not available during contract build.',
      },
      features: [],
    }, null, 2), 'utf8');
  }

  await fsp.writeFile(path.join(OUT_DIR, 'hunt_predictions.json'), JSON.stringify(predictionRows, null, 2), 'utf8');
  await fsp.writeFile(path.join(OUT_DIR, 'hunt_odds_history.json'), JSON.stringify(oddsHistoryRows, null, 2), 'utf8');
  await writeCsv(oddsHistoryRows, path.join(OUT_DIR, 'hunt_odds_history.csv'));
  await fsp.writeFile(path.join(OUT_DIR, 'hunt_application_outlook.json'), JSON.stringify(contractOutlookRows, null, 2), 'utf8');
  await fsp.writeFile(path.join(OUT_DIR, 'outfitters-public.json'), JSON.stringify(outfittersRows, null, 2), 'utf8');

  const snapshots = [];
  snapshots.push(await fileSnapshot(inputResolution.predictive.filePath, 'source_runtime_for_hunt_predictions'));
  snapshots.push(await fileSnapshot(inputResolution.oddsHistory.filePath, 'source_runtime_for_hunt_odds_history'));
  snapshots.push(await fileSnapshot(inputResolution.outlook.filePath, 'source_contract_for_hunt_application_outlook'));
  snapshots.push(await fileSnapshot(outfittersFallbackPath || inputResolution.outfittersPublic.filePath, 'source_public_outfitter_records'));
  snapshots.push(await fileSnapshot(inputResolution.huntUnitsLite.filePath, 'source_boundary_lite_geojson'));
  for (const output of [
    'hunt_predictions.json',
    'hunt_odds_history.json',
    'hunt_odds_history.csv',
    'hunt_application_outlook.json',
    'outfitters-public.json',
    'hunt_units.geojson',
  ]) {
    snapshots.push(await fileSnapshot(path.join(OUT_DIR, output), `public_contract:${output}`));
  }

  const summary = {
    generated_at: new Date().toISOString(),
    input_resolution: {
      predictive: rel(inputResolution.predictive.filePath),
      oddsHistory: rel(inputResolution.oddsHistory.filePath),
      outlook: rel(inputResolution.outlook.filePath),
      outfittersPublic: rel(outfittersFallbackPath || inputResolution.outfittersPublic.filePath),
      huntUnitsLite: rel(inputResolution.huntUnitsLite.filePath),
    },
    outputs: {
      hunt_predictions_rows: predictionRows.length,
      hunt_odds_history_rows: oddsHistoryRows.length,
      hunt_application_outlook_rows: contractOutlookRows.length,
      outfitters_public_rows: Array.isArray(outfittersRows) ? outfittersRows.length : 0,
      hunt_units_features: (() => {
        try {
          const geo = JSON.parse(fs.readFileSync(huntUnitsOut, 'utf8'));
          return Array.isArray(geo.features) ? geo.features.length : 0;
        } catch {
          return 0;
        }
      })(),
      unique_prediction_hunts: uniqueBy(predictionRows, (row) => row.hunt_code).length,
      unique_outlook_hunts: uniqueBy(contractOutlookRows, (row) => row.hunt_code).length,
      prediction_source_mode: predictionFallbackFromOutlook ? 'outlook_fallback' : 'runtime_csv',
      odds_history_source_mode: oddsFallbackFromOutlook ? 'outlook_fallback' : 'runtime_csv',
      outfitters_source_mode: outfittersFallbackPath ? 'outfitters_json_fallback' : 'outfitters_public_json',
    },
    source_notes: [
      'Contracts are website-facing display products only.',
      'Prediction math, p_draw, permit truth, and source truth files are not modified by this script.',
      'hunt_units.geojson is copied from the existing lite boundary artifact for browser-safe delivery.',
      'Technical source paths belong in collapsed source/freshness details, not primary hunter-facing panels.',
      'When primary runtime CSVs are missing, this contract build uses the first available reviewed fallback input.',
    ],
  };

  await fsp.writeFile(path.join(OUT_DIR, 'source_snapshots.json'), JSON.stringify({ ...summary, snapshots }, null, 2), 'utf8');
  await fsp.writeFile(path.join(OUT_DIR, 'public_contract_summary.json'), JSON.stringify(summary, null, 2), 'utf8');

  console.log(JSON.stringify(summary.outputs, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
