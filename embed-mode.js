(() => {
  const SELECTED_HUNT_KEY = 'selected_hunt_code';
  const SELECTED_RESIDENCY_KEY = 'selected_hunt_research_residency';
  const SELECTED_POINTS_KEY = 'selected_hunt_research_points';
  const SELECTED_DRAW_POOL_KEY = 'selected_hunt_research_draw_pool';
  const SELECTED_CONTEXT_KEY = 'selectedHuntForResearch';

  const OUTLOOK_SOURCES = {
    decision: './processed_data/model_outputs/hunt_decision_scores_v1.csv',
    prediction: './processed_data/model_outputs/draw_prediction_engine_v1.csv',
    creep: './processed_data/model_outputs/point_creep_forecast_v1.csv',
    ladder: './processed_data/point_ladder_view.csv',
    master: './processed_data/hunt_master_enriched.csv',
    harvest: './processed_data/harvest_quality_features_all_years_by_hunt_code.csv',
    ageLatest: './processed_data/harvest_age_features_by_hunt_code_latest.csv',
    managementJson: './processed_data/management_context/hunt_management_objective_context.json',
  };

  const outlookCache = new Map();

  function isEmbedded() {
    try {
      return window.self !== window.top;
    } catch {
      return true;
    }
  }

  function resolveEmbedMode() {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get('embed');
    if (forced === '1' || forced === 'true') return true;
    if (forced === '0' || forced === 'false') return false;
    return isEmbedded();
  }

  function normalizeKey(value) {
    return String(value || '').trim().toUpperCase();
  }

  function normalizeLower(value) {
    return String(value || '').trim().toLowerCase();
  }

  function normalizeResidency(value) {
    const text = normalizeLower(value);
    if (text === 'nr' || text === 'non-resident' || text === 'nonresident') return 'Nonresident';
    if (text === 'r' || text === 'resident') return 'Resident';
    return text ? String(value).trim() : '';
  }

  function normalizeDrawPool(value) {
    return String(value || '').trim().toLowerCase().replace(/[\s-]+/g, '_') || 'standard';
  }

  function isResearchPage() {
    const path = String(window.location.pathname || '').toLowerCase();
    return path.endsWith('/research.html') || path.endsWith('/hunt-research.html') || path.endsWith('research.html') || path.endsWith('hunt-research.html');
  }

  function parseHashParams() {
    const hash = String(window.location.hash || '').replace(/^#/, '').trim();
    if (!hash) return new URLSearchParams();
    return new URLSearchParams(hash.includes('=') ? hash : '');
  }

  function readStoredResearchContext() {
    try {
      const raw = sessionStorage.getItem(SELECTED_CONTEXT_KEY) || localStorage.getItem(SELECTED_CONTEXT_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }

  function writeResearchContext(context) {
    const huntCode = normalizeKey(context.hunt_code || context.huntCode || context.code);
    if (!huntCode) return null;

    const normalized = {
      hunt_code: huntCode,
      hunt_name: String(context.hunt_name || context.huntName || context.name || context.title || '').trim(),
      species: String(context.species || '').trim(),
      residency: normalizeResidency(context.residency || context.residence || ''),
      current_points: context.current_points ?? context.selected_points ?? context.points ?? '',
      weapon: String(context.weapon || context.weapon_type || '').trim(),
      hunt_type: String(context.hunt_type || context.huntType || '').trim(),
      hunt_class: String(context.hunt_class || context.huntClass || '').trim(),
      boundary_id: String(context.boundary_id || context.boundaryId || '').trim(),
      unit_name: String(context.unit_name || context.unit || context.unitName || '').trim(),
      draw_pool: normalizeDrawPool(context.draw_pool || context.drawPool || ''),
      updated_at: Date.now(),
    };

    try {
      sessionStorage.setItem(SELECTED_CONTEXT_KEY, JSON.stringify(normalized));
      localStorage.setItem(SELECTED_CONTEXT_KEY, JSON.stringify(normalized));
      localStorage.setItem(SELECTED_HUNT_KEY, normalized.hunt_code);
      if (normalized.residency) localStorage.setItem(SELECTED_RESIDENCY_KEY, normalized.residency);
      if (normalized.current_points !== '' && normalized.current_points !== null && normalized.current_points !== undefined) {
        localStorage.setItem(SELECTED_POINTS_KEY, String(normalized.current_points));
      }
      if (normalized.draw_pool) localStorage.setItem(SELECTED_DRAW_POOL_KEY, normalized.draw_pool);
    } catch {
      // Storage may be unavailable in embedded/private contexts. The URL still carries the primary key.
    }

    return normalized;
  }

  function selectedContextFromUrl() {
    const query = new URLSearchParams(window.location.search);
    const hash = parseHashParams();
    const stored = readStoredResearchContext();
    const get = (...keys) => {
      for (const key of keys) {
        const queryValue = query.get(key);
        if (queryValue !== null && queryValue !== '') return queryValue;
        const hashValue = hash.get(key);
        if (hashValue !== null && hashValue !== '') return hashValue;
        if (stored[key] !== undefined && stored[key] !== null && stored[key] !== '') return stored[key];
      }
      return '';
    };

    return {
      hunt_code: get('hunt_code', 'huntCode', 'code'),
      hunt_name: get('hunt_name', 'huntName', 'name'),
      species: get('species'),
      residency: get('residency', 'resident_status'),
      current_points: get('points', 'current_points', 'selected_points'),
      weapon: get('weapon', 'weapon_type'),
      hunt_type: get('hunt_type', 'huntType'),
      hunt_class: get('hunt_class', 'huntClass'),
      boundary_id: get('boundary_id', 'boundaryId'),
      unit_name: get('unit_name', 'unit', 'unitName'),
      draw_pool: get('draw_pool', 'drawPool'),
    };
  }

  function getSelectedResearchContext() {
    const context = selectedContextFromUrl();
    const huntCodeInput = document.getElementById('huntCodeInput');
    const residencySelect = document.getElementById('residencySelect');
    const pointsInput = document.getElementById('pointsInput');
    const drawPoolSelect = document.getElementById('drawPoolSelect');

    return writeResearchContext({
      ...context,
      hunt_code: context.hunt_code || huntCodeInput?.value || localStorage.getItem(SELECTED_HUNT_KEY) || '',
      residency: context.residency || residencySelect?.value || localStorage.getItem(SELECTED_RESIDENCY_KEY) || 'Resident',
      current_points: context.current_points || pointsInput?.value || localStorage.getItem(SELECTED_POINTS_KEY) || '0',
      draw_pool: context.draw_pool || drawPoolSelect?.value || localStorage.getItem(SELECTED_DRAW_POOL_KEY) || 'standard',
    });
  }

  function captureResearchLinkClick(event) {
    const link = event.target?.closest?.('a[href*="research.html"], a[href*="hunt-research.html"], button[data-research-handoff]');
    if (!link) return;

    const host = link.closest('[data-hunt-code], [data-hunt], article, tr, .hunt-card, .uoga-backpack-item, .hunt-basket-card');
    const dataset = { ...(host?.dataset || {}), ...(link.dataset || {}) };
    const href = link.getAttribute('href') || '';
    let urlParams = new URLSearchParams();
    try {
      const url = new URL(href, window.location.href);
      urlParams = url.searchParams;
    } catch {
      urlParams = new URLSearchParams();
    }

    writeResearchContext({
      hunt_code: dataset.huntCode || dataset.hunt_code || urlParams.get('hunt_code') || urlParams.get('code'),
      hunt_name: dataset.huntName || dataset.hunt_name || dataset.name || '',
      species: dataset.species || '',
      residency: dataset.residency || urlParams.get('residency') || localStorage.getItem(SELECTED_RESIDENCY_KEY) || '',
      current_points: dataset.points || dataset.currentPoints || dataset.selectedPoints || urlParams.get('points') || localStorage.getItem(SELECTED_POINTS_KEY) || '',
      weapon: dataset.weapon || dataset.weaponType || '',
      hunt_type: dataset.huntType || dataset.hunt_type || '',
      hunt_class: dataset.huntClass || dataset.hunt_class || '',
      boundary_id: dataset.boundaryId || dataset.boundary_id || '',
      unit_name: dataset.unitName || dataset.unit_name || dataset.unit || '',
      draw_pool: dataset.drawPool || dataset.draw_pool || urlParams.get('draw_pool') || '',
    });
  }

  function tuneResearchEmptyState() {
    if (!isResearchPage()) return;

    const heroTitle = document.querySelector('.hero-copy h2');
    if (heroTitle) heroTitle.textContent = 'Hunt Application Outlook for your selected hunt.';

    const heroCopy = document.querySelector('.hero-copy p');
    if (heroCopy) {
      heroCopy.textContent = 'Select a hunt in Hunt Builder, then review odds, point ladder, harvest quality, age context, and state objective benchmarks here.';
    }

    const controlsHead = document.querySelector('.controls-card .card-head h2');
    if (controlsHead) controlsHead.textContent = 'Selected hunt handoff';

    const controlsKicker = document.querySelector('.controls-card .card-head p');
    if (controlsKicker) controlsKicker.textContent = 'Planner-selected context';

    const huntLabel = document.querySelector('label[for="huntCodeInput"]');
    if (huntLabel) huntLabel.textContent = 'Selected Hunt Code';

    const runButton = document.getElementById('runResearchButton');
    if (runButton) runButton.textContent = 'Refresh Outlook';

    const clearButton = document.getElementById('clearFiltersButton');
    if (clearButton) clearButton.textContent = 'Change Hunt';

    const detailEmpty = document.getElementById('detailEmpty');
    if (detailEmpty) {
      detailEmpty.innerHTML = `
        <strong style="display:block;margin-bottom:8px;color:var(--text);font-size:16px;">No selected hunt was carried over</strong>
        <p>Select a hunt from the Hunt Builder page to view its application outlook.</p>
        <p style="margin-top:10px;"><a class="research-link" href="./index.html">Choose a Hunt</a></p>`;
    }

    const plannerReadout = document.getElementById('plannerReadout');
    if (plannerReadout && !plannerReadout.dataset.handoffCopyApplied) {
      plannerReadout.textContent = 'Research reads the hunt selected in Hunt Builder. Query-string and Hunt Backpack handoffs are supported.';
      plannerReadout.dataset.handoffCopyApplied = 'true';
    }
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function parseCsv(text) {
    const source = String(text || '').replace(/^\ufeff/, '');
    const rows = [];
    let row = [];
    let field = '';
    let inQuotes = false;

    for (let i = 0; i < source.length; i += 1) {
      const char = source[i];
      const next = source[i + 1];
      if (char === '"') {
        if (inQuotes && next === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        row.push(field);
        field = '';
      } else if ((char === '\n' || char === '\r') && !inQuotes) {
        if (char === '\r' && next === '\n') i += 1;
        row.push(field);
        if (row.some((cell) => String(cell).trim() !== '')) rows.push(row);
        row = [];
        field = '';
      } else {
        field += char;
      }
    }

    if (field || row.length) {
      row.push(field);
      if (row.some((cell) => String(cell).trim() !== '')) rows.push(row);
    }

    if (!rows.length) return [];
    const headers = rows.shift().map((header) => String(header || '').trim());
    return rows.map((cells) => {
      const obj = {};
      headers.forEach((header, index) => {
        obj[header] = cells[index] ?? '';
      });
      return obj;
    });
  }

  async function loadText(source) {
    if (outlookCache.has(source)) return outlookCache.get(source);
    const promise = fetch(source, { cache: 'no-cache' })
      .then((response) => (response.ok ? response.text() : ''))
      .catch(() => '');
    outlookCache.set(source, promise);
    return promise;
  }

  async function loadCsv(source) {
    const text = await loadText(source);
    return text ? parseCsv(text) : [];
  }

  async function loadJson(source) {
    const text = await loadText(source);
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }

  function toNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function hasValue(value) {
    const text = String(value ?? '').trim();
    return !!text && text.toUpperCase() !== 'N/A' && text.toUpperCase() !== 'NOT AVAILABLE';
  }

  function firstValue(row, keys) {
    if (!row) return '';
    for (const key of keys) {
      if (hasValue(row[key])) return row[key];
    }
    return '';
  }

  function formatValue(value, fallback = 'Not available') {
    return hasValue(value) ? String(value).trim() : fallback;
  }

  function formatNumber(value, suffix = '') {
    const parsed = toNumber(value);
    if (parsed === null) return 'Not available';
    return `${parsed.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
  }

  function formatPercent(value) {
    const parsed = toNumber(value);
    if (parsed === null || parsed <= 0) return 'Not available';
    const percent = parsed <= 1 ? parsed * 100 : parsed;
    return `${percent.toLocaleString(undefined, { maximumFractionDigits: percent < 10 ? 2 : 1 })}%`;
  }

  function sameCode(row, huntCode) {
    const code = normalizeKey(row?.hunt_code || row?.current_hunt_code || row?.HuntNumber || row?.huntCode || row?.code);
    return code === normalizeKey(huntCode);
  }

  function sameResidency(row, residency) {
    const candidate = normalizeResidency(row?.residency || row?.resident_status || row?.Residency || 'Resident');
    return candidate === normalizeResidency(residency);
  }

  function rowYear(row) {
    return toNumber(row?.model_target_year || row?.year || row?.forecast_year || row?.reported_hunt_year) || 0;
  }

  function pickLatest(rows) {
    return [...rows].sort((a, b) => rowYear(b) - rowYear(a))[0] || null;
  }

  function findByCode(rows, huntCode) {
    return pickLatest(rows.filter((row) => sameCode(row, huntCode)));
  }

  function findByCodeResidency(rows, huntCode, residency) {
    return pickLatest(rows.filter((row) => sameCode(row, huntCode) && sameResidency(row, residency)));
  }

  function findPointRow(rows, huntCode, residency, points) {
    const pointNum = toNumber(points);
    const matches = rows.filter((row) => sameCode(row, huntCode) && sameResidency(row, residency));
    if (pointNum !== null) {
      const exact = matches.find((row) => toNumber(row.points || row.point_value || row.current_points) === pointNum);
      if (exact) return exact;
    }
    return pickLatest(matches);
  }

  function probabilityFrom(row) {
    const raw = firstValue(row, [
      'display_odds_pct',
      'p_draw_mean',
      'p50',
      'draw_probability',
      'modeled_draw_probability',
      'projected_total_probability_pct',
      'odds_2026_projected',
      'preference_draw_odds_2026',
      'modeled_preference_probability',
    ]);
    const parsed = toNumber(raw);
    if (parsed === null) return '';
    return parsed <= 1 ? parsed * 100 : parsed;
  }

  function decisionLabel(probability, qualityScore, statusText) {
    const status = String(statusText || '').toUpperCase();
    if (status.includes('EXCLUDED') || status.includes('STATUS') || status.includes('AVAILABILITY')) return 'STATUS / AVAILABILITY ONLY';
    if (probability === '' || probability === null) return 'INSUFFICIENT DATA';
    if (probability >= 60 && (qualityScore === null || qualityScore >= 65)) return 'STRONG APPLY';
    if (probability >= 25) return 'WITHIN REACH';
    if (qualityScore !== null && qualityScore >= 75) return 'QUALITY LONG SHOT';
    return 'LONG SHOT';
  }

  function recommendationText(label, probability, ageStatus, creep) {
    if (label === 'STATUS / AVAILABILITY ONLY') return 'This is not a predictive draw row. Use official availability/status and source notes.';
    if (label === 'STRONG APPLY') return 'Strong application candidate based on draw probability and available quality signals.';
    if (label === 'WITHIN REACH') return 'Based on your points, this hunt appears within reach compared with modeled and historical context.';
    if (ageStatus === 'ABOVE_OBJECTIVE') return 'Observed age is above the state objective; quality appears strong, but draw odds still matter.';
    if (toNumber(creep) !== null && toNumber(creep) >= 1) return 'Point creep risk: this hunt may become harder next year.';
    if (probability !== '' && probability < 10) return 'High-value context may exist, but this remains a long-shot application based on modeled odds.';
    return 'Review the ladder, harvest quality, and source details before deciding whether to apply.';
  }

  function buildCard(label, value, subvalue = '') {
    return `
      <div class="summary-card">
        <span class="label">${escapeHtml(label)}</span>
        <div class="value">${escapeHtml(value)}</div>
        ${subvalue ? `<div class="subvalue">${escapeHtml(subvalue)}</div>` : ''}
      </div>`;
  }

  function buildObjectiveStatus(species, management, ageRow) {
    if (!management) return { status: 'NO_OBJECTIVE_DATA', note: 'No approved management-objective data file was found for this hunt.' };
    const objectiveMin = toNumber(management.management_objective_min || management.objective_min || management.elk_age_objective_min);
    const objectiveMax = toNumber(management.management_objective_max || management.objective_max || management.elk_age_objective_max);
    const observedAge = toNumber(ageRow?.average_harvest_age || ageRow?.average_age || ageRow?.mean_age);
    if (objectiveMin === null && objectiveMax === null) return { status: 'NO_OBJECTIVE_DATA', note: 'Objective row exists but does not include a numeric min/max benchmark.' };
    if (observedAge === null) {
      return { status: String(species || '').toLowerCase().includes('elk') ? 'OBJECTIVE_ONLY_NO_OBSERVED_AGE' : 'OBJECTIVE_ONLY_NO_OBSERVED_DATA', note: 'State objective benchmark found; no verified observed age is available for this hunt.' };
    }
    if (objectiveMax !== null && observedAge > objectiveMax) return { status: 'ABOVE_OBJECTIVE', note: 'Observed age is above the state objective range.' };
    if (objectiveMin !== null && observedAge < objectiveMin) return { status: 'BELOW_OBJECTIVE', note: 'Observed age is below the state objective range.' };
    return { status: 'MEETING_OBJECTIVE', note: 'Observed age falls within the state objective range.' };
  }

  function normalizeManagementRows(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw;
    if (Array.isArray(raw.hunts)) return raw.hunts;
    if (Array.isArray(raw.rows)) return raw.rows;
    if (Array.isArray(raw.features)) return raw.features.map((feature) => ({ ...(feature.properties || {}), ...(feature || {}) }));
    return [];
  }

  async function loadOutlookData() {
    const [decision, prediction, creep, ladder, master, harvest, ageLatest, managementRaw] = await Promise.all([
      loadCsv(OUTLOOK_SOURCES.decision),
      loadCsv(OUTLOOK_SOURCES.prediction),
      loadCsv(OUTLOOK_SOURCES.creep),
      loadCsv(OUTLOOK_SOURCES.ladder),
      loadCsv(OUTLOOK_SOURCES.master),
      loadCsv(OUTLOOK_SOURCES.harvest),
      loadCsv(OUTLOOK_SOURCES.ageLatest),
      loadJson(OUTLOOK_SOURCES.managementJson),
    ]);

    return {
      decision,
      prediction,
      creep,
      ladder,
      master,
      harvest,
      ageLatest,
      management: normalizeManagementRows(managementRaw),
    };
  }

  function ensureDashboardShell() {
    let shell = document.getElementById('uogaApplicationOutlookDashboard');
    if (shell) return shell;

    const detailContent = document.getElementById('detailContent');
    const resultCardBody = detailContent?.closest('.card-body') || document.querySelector('.result-card .card-body') || document.querySelector('.main-stack');
    if (!resultCardBody) return null;

    shell = document.createElement('section');
    shell.id = 'uogaApplicationOutlookDashboard';
    shell.className = 'uoga-outlook-dashboard';
    shell.innerHTML = `
      <style>
        .uoga-outlook-dashboard { display: grid; gap: 14px; margin-top: 16px; }
        .uoga-outlook-panel { border: 1px solid var(--research-line-soft); border-radius: 18px; background: rgba(255,255,255,.045); padding: 14px; }
        .uoga-outlook-panel h3 { margin: 0 0 8px; color: var(--text); font-family: var(--font-display); font-size: 22px; line-height: 1; }
        .uoga-outlook-panel p { margin: 0; color: var(--research-muted); line-height: 1.55; }
        .uoga-outlook-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
        .uoga-outlook-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
        .uoga-outlook-badge { display: inline-flex; align-items: center; border: 1px solid rgba(240,120,0,.34); border-radius: 999px; padding: 5px 10px; color: var(--accent); background: rgba(240,120,0,.09); font-size: 11px; font-weight: 900; letter-spacing: .07em; text-transform: uppercase; }
        .uoga-outlook-mini-list { display: grid; gap: 10px; margin-top: 10px; }
        .uoga-outlook-alt { border: 1px solid rgba(170,124,84,.28); border-radius: 14px; padding: 10px; background: rgba(255,255,255,.04); }
        .uoga-outlook-alt strong { color: var(--text); display: block; margin-bottom: 3px; }
        @media (max-width: 1220px) { .uoga-outlook-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 720px) { .uoga-outlook-grid { grid-template-columns: 1fr; } }
      </style>
      <div id="uogaSelectedHuntSummary" class="uoga-outlook-panel"></div>
      <div id="uogaApplicationSummary" class="uoga-outlook-panel"></div>
      <div id="uogaHistoricalContext" class="uoga-outlook-panel"></div>
      <div id="uogaHarvestQuality" class="uoga-outlook-panel"></div>
      <div id="uogaAgeQuality" class="uoga-outlook-panel"></div>
      <div id="uogaStateObjective" class="uoga-outlook-panel"></div>
      <div id="uogaComparableHunts" class="uoga-outlook-panel"></div>
      <div id="uogaSourceDetails" class="uoga-outlook-panel"></div>`;

    if (detailContent && detailContent.parentElement) {
      detailContent.insertAdjacentElement('afterend', shell);
    } else {
      resultCardBody.appendChild(shell);
    }
    return shell;
  }

  function updateTitleFromContext(context, meta) {
    const code = normalizeKey(context?.hunt_code || meta?.hunt_code);
    const name = context?.hunt_name || meta?.hunt_name || meta?.hunt_name_2026 || code;
    const detailTitle = document.getElementById('detailTitle');
    if (detailTitle && code) detailTitle.textContent = `Hunt Application Outlook: ${code} — ${name}`;
  }

  function renderComparableHunts(container, data, context, meta, probability) {
    const species = String(meta?.species || context?.species || '').trim().toLowerCase();
    const huntCode = normalizeKey(context.hunt_code);
    const source = data.decision.length ? data.decision : data.master;
    const candidates = source
      .filter((row) => !sameCode(row, huntCode))
      .filter((row) => !species || String(firstValue(row, ['species', 'Species']) || '').toLowerCase() === species)
      .slice(0, 250)
      .map((row) => {
        const rowProb = probabilityFrom(row);
        const score = Math.abs((toNumber(rowProb) ?? 0) - (toNumber(probability) ?? 0));
        return { row, rowProb, score };
      })
      .sort((a, b) => a.score - b.score)
      .slice(0, 5);

    if (!candidates.length) {
      container.innerHTML = '<h3>Comparable Hunts</h3><p>No comparable hunt set is available from the loaded research data.</p>';
      return;
    }

    container.innerHTML = `
      <h3>Comparable Hunts</h3>
      <p>Transparent fallback ranking: same species first, then similar modeled probability or available quality context.</p>
      <div class="uoga-outlook-mini-list">
        ${candidates.map(({ row, rowProb }) => {
          const code = firstValue(row, ['hunt_code', 'current_hunt_code', 'code']);
          const name = firstValue(row, ['hunt_name', 'hunt_name_2026', 'unit_name', 'boundary_name']) || code;
          const reason = rowProb ? 'Similar species and comparable modeled outlook' : 'Similar species with available reference data';
          return `<div class="uoga-outlook-alt"><strong>${escapeHtml(code)} — ${escapeHtml(name)}</strong><p>${escapeHtml(rowProb ? formatPercent(rowProb) : 'Status/odds not available')} · ${escapeHtml(reason)}</p></div>`;
        }).join('')}
      </div>`;
  }

  async function renderOutlookDashboard() {
    if (!isResearchPage()) return;
    const context = getSelectedResearchContext();
    const shell = ensureDashboardShell();
    if (!shell) return;

    if (!context?.hunt_code) {
      shell.innerHTML = '<div class="uoga-outlook-panel"><h3>Select a hunt first</h3><p>Select a hunt from the Hunt Builder page to view its application outlook.</p><p style="margin-top:10px;"><a class="research-link" href="./index.html">Choose a Hunt</a></p></div>';
      return;
    }

    const data = await loadOutlookData();
    const huntCode = context.hunt_code;
    const residency = context.residency || 'Resident';
    const points = context.current_points || '0';
    const meta = findByCode(data.master, huntCode) || findByCode(data.ladder, huntCode) || {};
    const decision = findByCodeResidency(data.decision, huntCode, residency) || findByCode(data.decision, huntCode) || {};
    const prediction = findPointRow(data.prediction, huntCode, residency, points) || findByCodeResidency(data.prediction, huntCode, residency) || {};
    const ladder = findPointRow(data.ladder, huntCode, residency, points) || findByCodeResidency(data.ladder, huntCode, residency) || {};
    const creep = findByCodeResidency(data.creep, huntCode, residency) || findByCode(data.creep, huntCode) || {};
    const harvest = findByCode(data.harvest, huntCode) || {};
    const age = findByCode(data.ageLatest, huntCode) || {};
    const management = findByCode(data.management, huntCode) || null;

    const species = firstValue(meta, ['species', 'Species']) || context.species || firstValue(decision, ['species']) || 'Not available';
    const huntName = context.hunt_name || firstValue(meta, ['hunt_name', 'hunt_name_2026', 'Hunt Name']) || firstValue(decision, ['hunt_name']) || huntCode;
    const drawFamily = firstValue(decision, ['draw_system_type', 'draw_2026_system_type', 'draw_family']) || firstValue(meta, ['draw_system_type', 'draw_2026_system_type']) || 'Not available';
    const probability = probabilityFrom(prediction) || probabilityFrom(decision) || probabilityFrom(ladder);
    const qualityScore = toNumber(firstValue(decision, ['quality_score', 'decision_score', 'application_value_score', 'age_quality_score']));
    const ageStatus = buildObjectiveStatus(species, management, age);
    const label = decisionLabel(probability, qualityScore, firstValue(decision, ['algorithm_status', 'draw_system_type']) || drawFamily);
    const recommendation = recommendationText(label, probability, ageStatus.status, firstValue(creep, ['point_creep_1yr', 'point_creep_last_year']));
    const observedAge = firstValue(age, ['average_harvest_age', 'average_age', 'mean_age']);
    const percent5 = firstValue(age, ['percent_5plus', 'percent_mature_or_5_plus']);

    updateTitleFromContext(context, { ...meta, hunt_name: huntName, hunt_code: huntCode });

    shell.querySelector('#uogaSelectedHuntSummary').innerHTML = `
      <h3>Selected Hunt Summary</h3>
      <div class="uoga-outlook-grid">
        ${buildCard('Hunt', `${huntCode}`, huntName)}
        ${buildCard('Species', species)}
        ${buildCard('Residency / Points', `${residency} · ${points} pts`)}
        ${buildCard('Unit / Boundary', context.unit_name || firstValue(meta, ['unit_name', 'boundary_name']) || 'Not available', context.boundary_id || firstValue(meta, ['boundary_id']) || '')}
      </div>`;

    shell.querySelector('#uogaApplicationSummary').innerHTML = `
      <h3>Hunt Application Outlook</h3>
      <div class="uoga-outlook-grid">
        ${buildCard('Decision Label', label)}
        ${buildCard('Modeled Draw Probability', probability !== '' ? formatPercent(probability) : 'Not available')}
        ${buildCard('Draw Family', drawFamily)}
        ${buildCard('Point Creep', formatValue(firstValue(creep, ['point_creep_1yr', 'point_creep_last_year', 'point_creep_3yr']))}
      </div>
      <p style="margin-top:12px;">${escapeHtml(recommendation)}</p>`;

    shell.querySelector('#uogaHistoricalContext').innerHTML = `
      <h3>Historical Draw Context</h3>
      <div class="uoga-outlook-grid">
        ${buildCard('Actual / Historical Odds', formatValue(firstValue(ladder, ['display_2025_draw_results', 'dwr_result_display', 'actual_draw_odds', 'odds_2025_actual'])))}
        ${buildCard('Applicants', formatNumber(firstValue(ladder, ['applicants', 'eligible_applicants'])))}
        ${buildCard('Permits', formatNumber(firstValue(ladder, ['total_permits', 'permits', 'permits_2025_total', 'permits_2026_total'])))}
        ${buildCard('Guaranteed / Cutoff', formatValue(firstValue(ladder, ['guaranteed_line_points', 'expected_cutoff_points', 'cutoff_points', 'guaranteed_point_level'])))}
      </div>`;

    shell.querySelector('#uogaHarvestQuality').innerHTML = `
      <h3>Harvest Quality</h3>
      <div class="uoga-outlook-grid">
        ${buildCard('Success Rate', formatPercent(firstValue(harvest, ['success_rate_pct', 'percent_success', 'harvest_success']) || firstValue(meta, ['success_rate_pct', 'harvest_success'])))}
        ${buildCard('Harvest Total', formatNumber(firstValue(harvest, ['harvest_total', 'harvest']) || firstValue(meta, ['harvest_total'])))}
        ${buildCard('Hunters Afield', formatNumber(firstValue(harvest, ['hunters_afield', 'hunters']) || firstValue(meta, ['hunters_afield'])))}
        ${buildCard('Average Days Hunted', formatNumber(firstValue(harvest, ['average_days_hunted', 'average_days', 'mean_days_hunted']) || firstValue(meta, ['average_days_hunted', 'average_days'])))}
      </div>
      <p style="margin-top:10px;">Average days hunted is effort, not animal age.</p>`;

    shell.querySelector('#uogaAgeQuality').innerHTML = `
      <h3>Age Quality / Trophy Context</h3>
      <div class="uoga-outlook-grid">
        ${buildCard('Observed Avg. Harvest Age', toNumber(observedAge) ? formatNumber(observedAge, ' yrs') : 'No verified age data available')}
        ${buildCard('% Age 5+ / Mature Proxy', percent5 ? formatPercent(percent5) : 'Not available')}
        ${buildCard('Age Source Scope', formatValue(firstValue(age, ['age_source_scope', 'age_match_scope', 'crosswalk_confidence'])))}
        ${buildCard('Age Source Year', formatValue(firstValue(age, ['reported_hunt_year', 'model_target_year', 'year'])))}
      </div>
      <p style="margin-top:10px;">Percent 5+ is shown as an age-structure proxy and is not converted into average age.</p>`;

    shell.querySelector('#uogaStateObjective').innerHTML = `
      <h3>State Management Objective</h3>
      <div class="uoga-outlook-grid">
        ${buildCard('Objective Status', ageStatus.status)}
        ${buildCard('Objective Type', formatValue(firstValue(management, ['management_objective_type', 'objective_type', 'data_class'])))}
        ${buildCard('Objective Range', management ? `${formatValue(firstValue(management, ['management_objective_min', 'objective_min']))} – ${formatValue(firstValue(management, ['management_objective_max', 'objective_max']))}` : 'Not available')}
        ${buildCard('Context Source', management ? 'Management Plan Context' : 'No objective table loaded')}
      </div>
      <p style="margin-top:10px;">${escapeHtml(ageStatus.note)} State objectives are benchmarks, not predictions.</p>`;

    renderComparableHunts(shell.querySelector('#uogaComparableHunts'), data, context, meta, probability);

    shell.querySelector('#uogaSourceDetails').innerHTML = `
      <h3>Source / Freshness / Model Details</h3>
      <div class="uoga-outlook-badges">
        <span class="uoga-outlook-badge">Official DWR Source</span>
        <span class="uoga-outlook-badge">U.O.G.A. Modeled Output</span>
        <span class="uoga-outlook-badge">Management Plan Context</span>
        ${label === 'STATUS / AVAILABILITY ONLY' ? '<span class="uoga-outlook-badge">Status / Availability Only</span>' : ''}
      </div>
      <div class="uoga-outlook-grid" style="margin-top:12px;">
        ${buildCard('Model Version', formatValue(firstValue(decision, ['model_version']) || firstValue(prediction, ['model_version'])))}
        ${buildCard('Rule Version', formatValue(firstValue(decision, ['rule_version']) || firstValue(prediction, ['rule_version'])))}
        ${buildCard('Data As Of', formatValue(firstValue(decision, ['data_as_of']) || firstValue(prediction, ['data_cutoff_date', 'data_as_of'])))}
        ${buildCard('Age Source', formatValue(firstValue(age, ['source_file', 'age_source_file'])))}
      </div>`;
  }

  function scheduleOutlookRender() {
    if (!isResearchPage()) return;
    window.setTimeout(() => renderOutlookDashboard(), 250);
    window.setTimeout(() => renderOutlookDashboard(), 1200);
  }

  if (resolveEmbedMode()) {
    document.documentElement.classList.add('embed');
    if (document.body) document.body.classList.add('embed');
  }

  if (isResearchPage()) {
    writeResearchContext(selectedContextFromUrl());
  }

  document.addEventListener('click', captureResearchLinkClick, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      tuneResearchEmptyState();
      scheduleOutlookRender();
      ['huntCodeInput', 'residencySelect', 'pointsInput', 'drawPoolSelect'].forEach((id) => {
        document.getElementById(id)?.addEventListener('change', scheduleOutlookRender);
        document.getElementById(id)?.addEventListener('input', scheduleOutlookRender);
      });
      document.getElementById('runResearchButton')?.addEventListener('click', scheduleOutlookRender);
    }, { once: true });
  } else {
    tuneResearchEmptyState();
    scheduleOutlookRender();
  }
})();