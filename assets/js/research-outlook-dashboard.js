(() => {
  "use strict";

  const DASHBOARD_ID = "uogaApplicationOutlookDashboard";
  const SELECTED_HUNT_KEY = "selected_hunt_code";
  const SELECTED_RESIDENCY_KEY = "selected_hunt_research_residency";
  const SELECTED_POINTS_KEY = "selected_hunt_research_points";
  const SELECTED_DRAW_POOL_KEY = "selected_hunt_research_draw_pool";

  const state = {
    loaded: false,
    loading: false,
    loadPromise: null,
    coreReady: false,
    error: "",
    rows: {
      engine: [],
      ladder: [],
      master: [],
      reference: [],
      management: [],
    },
    sources: {},
  };

  function isResearchPage() {
    const path = String(window.location.pathname || "").toLowerCase();
    return path.endsWith("/research.html") || path.endsWith("research.html");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeCode(value) {
    return String(value || "").trim().toUpperCase();
  }

  function normalizeResidency(value) {
    const text = String(value || "").trim().toLowerCase();
    if (["nr", "non-res", "nonresident", "non-resident"].includes(text)) return "Nonresident";
    return "Resident";
  }

  function normalizeDrawPool(value) {
    return String(value || "").trim().toLowerCase() || "standard";
  }

  function num(value) {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(String(value).replace(/[^0-9.-]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function hasValue(value) {
    const text = String(value ?? "").trim();
    return !!text && !["N/A", "NA", "NOT AVAILABLE", "NULL", "NONE"].includes(text.toUpperCase());
  }

  function firstValue(source, keys) {
    if (!source) return "";
    for (const key of keys) {
      if (hasValue(source[key])) return source[key];
    }
    return "";
  }

  function formatValue(value, fallback = "Not available") {
    return hasValue(value) ? String(value).trim() : fallback;
  }

  function formatInteger(value) {
    const parsed = num(value);
    return parsed === null ? "Not available" : parsed.toLocaleString();
  }

  function formatAge(value) {
    const parsed = num(value);
    return parsed === null || parsed <= 0 ? "No verified age data" : parsed.toFixed(1);
  }

  function formatPercent(value) {
    const parsed = num(value);
    if (parsed === null) return "Not available";
    const pct = parsed <= 1 && parsed > 0 ? parsed * 100 : parsed;
    if (pct >= 99.95) return "100%";
    if (pct >= 10) return `${pct.toFixed(1)}%`;
    return `${pct.toFixed(2)}%`;
  }

  function readParams() {
    const search = new URLSearchParams(window.location.search || "");
    const hash = new URLSearchParams(String(window.location.hash || "").replace(/^#/, ""));
    return {
      get(name) {
        return search.get(name) || hash.get(name) || "";
      },
      has(name) {
        return search.has(name) || hash.has(name);
      },
    };
  }

  function readStoredSelectionObject() {
    const stores = [window.sessionStorage, window.localStorage].filter(Boolean);
    for (const store of stores) {
      try {
        const raw = store.getItem("selectedHuntForResearch");
        if (!raw) continue;
        if (raw.trim().startsWith("{")) return JSON.parse(raw);
        return { hunt_code: raw };
      } catch {
        // Storage can be blocked in embedded contexts; URL parameters still work.
      }
    }
    return {};
  }

  function readStorageValue(key) {
    for (const store of [window.sessionStorage, window.localStorage].filter(Boolean)) {
      try {
        const value = store.getItem(key);
        if (hasValue(value)) return value;
      } catch {
        // Ignore blocked storage.
      }
    }
    return "";
  }

  function getSelection() {
    const params = readParams();
    const storedObject = readStoredSelectionObject();
    const huntInput = document.getElementById("huntCodeInput");
    const residencyInput = document.getElementById("residencySelect");
    const drawPoolInput = document.getElementById("drawPoolSelect");
    const pointsInput = document.getElementById("pointsInput");
    const huntCode = normalizeCode(
      params.get("hunt_code")
      || huntInput?.value
      || storedObject.hunt_code
      || storedObject.huntCode
      || readStorageValue(SELECTED_HUNT_KEY)
    );
    const residency = normalizeResidency(
      params.get("residency")
      || residencyInput?.value
      || storedObject.residency
      || readStorageValue(SELECTED_RESIDENCY_KEY)
    );
    const drawPool = normalizeDrawPool(
      params.has("draw_pool") ? params.get("draw_pool")
        : (drawPoolInput?.value || storedObject.draw_pool || storedObject.drawPool || readStorageValue(SELECTED_DRAW_POOL_KEY))
    );
    const points = num(
      params.get("points")
      || pointsInput?.value
      || storedObject.points
      || storedObject.selected_points
      || readStorageValue(SELECTED_POINTS_KEY)
      || "0"
    );
    return { huntCode, residency, drawPool, points: points ?? 0 };
  }

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let value = "";
    let inQuotes = false;
    const source = String(text || "");

    for (let i = 0; i < source.length; i += 1) {
      const char = source[i];
      const next = source[i + 1];
      if (char === '"') {
        if (inQuotes && next === '"') {
          value += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === "," && !inQuotes) {
        row.push(value);
        value = "";
      } else if ((char === "\n" || char === "\r") && !inQuotes) {
        if (char === "\r" && next === "\n") i += 1;
        row.push(value);
        if (row.some((cell) => String(cell || "").trim() !== "")) rows.push(row);
        row = [];
        value = "";
      } else {
        value += char;
      }
    }

    if (value.length || row.length) {
      row.push(value);
      if (row.some((cell) => String(cell || "").trim() !== "")) rows.push(row);
    }

    if (rows.length < 2) return [];
    const headers = rows[0].map((header) => String(header || "").trim());
    return rows.slice(1).map((record) => {
      const mapped = {};
      headers.forEach((header, index) => {
        mapped[header] = record[index] ?? "";
      });
      return mapped;
    });
  }

  async function fetchText(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Request failed for ${url}`);
    const text = await response.text();
    if (text.startsWith("version https://git-lfs.github.com/spec/v1")) {
      throw new Error(`Git LFS pointer served instead of data for ${url}`);
    }
    return text;
  }

  async function loadFirst(sources) {
    let lastError = null;
    for (const source of (sources || []).filter(Boolean)) {
      try {
        return { source, text: await fetchText(source) };
      } catch (error) {
        lastError = error;
        console.warn("Outlook dashboard source failed:", source, error);
      }
    }
    throw lastError || new Error("No dashboard data source could be loaded.");
  }

  function getManagementSources() {
    const version = window.UOGA_CONFIG?.HUNT_RESEARCH_DATA_VERSION || "research-outlook-dashboard-2";
    const cloudflare = "https://json.uoga.workers.dev";
    return [
      `./processed_data/management_context/hunt_management_objective_context.json?v=${version}`,
      `${cloudflare}/processed_data/management_context/hunt_management_objective_context.json?v=${version}`,
      `${cloudflare}/management_context/hunt_management_objective_context.json?v=${version}`,
    ];
  }

  async function loadData() {
    if (state.loaded) return;
    if (state.loadPromise) return state.loadPromise;
    state.loading = true;
    state.loadPromise = (async () => {
      try {
        const management = await loadFirst(getManagementSources());
        state.rows.management = JSON.parse(management.text);
        state.sources.management = management.source;
      } catch (error) {
        state.rows.management = [];
        state.sources.management = "";
        console.info("No management objective context loaded for dashboard.", error);
      }

      state.loaded = true;
      state.loading = false;
    })();

    try {
      await state.loadPromise;
    } catch (error) {
      state.loading = false;
      state.loadPromise = null;
      throw error;
    }
  }

  function applyCoreSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== "object") return;
    state.rows.engine = Array.isArray(snapshot.engineRows) ? snapshot.engineRows : [];
    state.rows.ladder = Array.isArray(snapshot.ladderRows) ? snapshot.ladderRows : [];
    state.rows.master = Array.isArray(snapshot.masterRows) ? snapshot.masterRows : [];
    state.rows.reference = Array.isArray(snapshot.referenceRows)
      ? snapshot.referenceRows
      : (snapshot.referenceRow ? [snapshot.referenceRow] : []);
    state.sources = {
      ...(snapshot.loadedSources || {}),
      management: state.sources.management || "",
    };
    state.coreReady = true;
  }

  function rowMatches(row, selection) {
    return normalizeCode(row.hunt_code) === selection.huntCode
      && normalizeResidency(row.residency) === selection.residency
      && normalizeDrawPool(row.draw_pool) === selection.drawPool;
  }

  function findContext(selection) {
    const masterRows = state.rows.master.filter((row) => rowMatches(row, selection));
    const meta = masterRows.find((row) => num(row.points) === selection.points)
      || masterRows[0]
      || state.rows.master.find((row) => normalizeCode(row.hunt_code) === selection.huntCode)
      || null;
    const reference = state.rows.reference.find((row) => rowMatches(row, selection))
      || state.rows.reference.find((row) => normalizeCode(row.hunt_code) === selection.huntCode)
      || null;
    const ladderRows = state.rows.ladder
      .filter((row) => rowMatches(row, selection))
      .sort((a, b) => (num(b.points) ?? 0) - (num(a.points) ?? 0));
    const ladderPoint = ladderRows.find((row) => num(row.points) === selection.points) || null;
    const engineRows = state.rows.engine
      .filter((row) => rowMatches(row, selection))
      .sort((a, b) => (num(b.points) ?? 0) - (num(a.points) ?? 0));
    const enginePoint = engineRows.find((row) => num(row.points) === selection.points) || null;
    const selectedRow = enginePoint || ladderPoint || engineRows[0] || ladderRows[0] || meta || reference || {};
    const managementRows = Array.isArray(state.rows.management)
      ? state.rows.management.filter((row) => normalizeCode(row.hunt_code) === selection.huntCode)
      : [];
    const comparable = buildComparableRows(selection, meta, selectedRow);
    return { meta, reference, ladderRows, ladderPoint, engineRows, enginePoint, selectedRow, managementRows, comparable };
  }

  function buildComparableRows(selection, meta, selectedRow) {
    const species = String(meta?.species || selectedRow?.species || "").trim().toLowerCase();
    const huntType = String(meta?.hunt_type || selectedRow?.hunt_type || "").trim().toLowerCase();
    const seen = new Set([selection.huntCode]);
    const rows = [];
    for (const row of state.rows.master) {
      const code = normalizeCode(row.hunt_code);
      if (!code || seen.has(code)) continue;
      if (normalizeResidency(row.residency) !== selection.residency) continue;
      if (normalizeDrawPool(row.draw_pool) !== selection.drawPool) continue;
      if (species && String(row.species || "").trim().toLowerCase() !== species) continue;
      if (huntType && String(row.hunt_type || "").trim().toLowerCase() !== huntType) continue;
      seen.add(code);
      rows.push(row);
      if (rows.length >= 5) break;
    }
    return rows;
  }

  function metricRow(label, value, note = "") {
    return `
      <div class="uoga-outlook-metric">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
        ${note ? `<small>${escapeHtml(note)}</small>` : ""}
      </div>`;
  }

  function panel(title, body, extraClass = "") {
    return `
      <section class="uoga-outlook-panel ${extraClass}">
        <h4>${escapeHtml(title)}</h4>
        ${body}
      </section>`;
  }

  function listRows(items) {
    if (!items.length) return `<p class="uoga-outlook-muted">Not available from the loaded runtime rows.</p>`;
    return `<div class="uoga-outlook-metrics">${items.join("")}</div>`;
  }

  function getHarvestSuccess(meta, reference, selectedRow) {
    return firstValue(meta, ["success_percent", "harvest_success_percent_2025", "percent_harvest_success", "success_harvest"])
      || firstValue(reference, ["harvest_success_percent_2025", "success_percent", "percent_harvest_success"])
      || firstValue(selectedRow, ["success_ratio"]);
  }

  function getAverageDays(meta, reference) {
    return firstValue(meta, ["harvest_average_days_2025", "average_days_hunted", "avg_days_hunted"])
      || firstValue(reference, ["harvest_average_days_2025", "average_days_hunted", "avg_days_hunted"]);
  }

  function getAge(meta, reference, selectedRow) {
    return firstValue(meta, ["average_harvest_age"])
      || firstValue(reference, ["average_harvest_age"])
      || firstValue(selectedRow, ["average_harvest_age"]);
  }

  function getCurrentAge(meta, reference, selectedRow) {
    return firstValue(meta, ["current_age_3yr_average"])
      || firstValue(reference, ["current_age_3yr_average"])
      || firstValue(selectedRow, ["current_age_3yr_average"]);
  }

  function getSelectedOdds(selectedRow, ladderPoint, meta) {
    return firstValue(selectedRow, ["p_draw_pct", "random_draw_odds_2026", "odds_2026_projected", "success_ratio"])
      || firstValue(ladderPoint, ["random_draw_odds_2026", "p_draw_pct", "success_ratio"])
      || firstValue(meta, ["odds_2026_projected", "odds_2025"]);
  }

  function getPermitTotal(meta, reference, selectedRow) {
    return firstValue(meta, ["permits_2026_total", "permit_allotment_2026_total", "public_permits_2026"])
      || firstValue(reference, ["permits_2026_total", "public_permits_2026"])
      || firstValue(selectedRow, ["total_permits", "quota_2026_total"]);
  }

  function getPercentFivePlus(meta, reference, selectedRow) {
    return firstValue(meta, ["percent_5_plus", "percent_5plus", "percent_five_plus", "harvest_age_percent_5plus"])
      || firstValue(reference, ["percent_5_plus", "percent_5plus", "percent_five_plus", "harvest_age_percent_5plus"])
      || firstValue(selectedRow, ["percent_5_plus", "percent_5plus", "percent_five_plus", "harvest_age_percent_5plus"]);
  }

  function getGuaranteedLine(selectedRow, meta) {
    return firstValue(selectedRow, ["guaranteed_at_2026", "guaranteed_points", "min_points_guaranteed", "guaranteed_line"])
      || firstValue(meta, ["guaranteed_at_2026", "guaranteed_points", "min_points_guaranteed", "guaranteed_line"]);
  }

  function getPointTrend(selectedRow, meta) {
    return firstValue(selectedRow, ["point_creep", "point_trend", "trend", "draw_trend"])
      || firstValue(meta, ["point_creep", "point_trend", "trend", "draw_trend"]);
  }

  function decisionLabel(odds) {
    const parsed = num(odds);
    if (parsed === null) return "Needs source review";
    const pct = parsed <= 1 && parsed > 0 ? parsed * 100 : parsed;
    if (pct >= 90) return "Strong draw position";
    if (pct >= 55) return "Competitive application";
    if (pct >= 20) return "Long-shot but live";
    return "Very long odds";
  }

  function recommendationSentence(odds, permitTotal) {
    const parsed = num(odds);
    const permits = num(permitTotal);
    if (parsed === null) return "Draw outlook is waiting on a verified odds row for this selected point level.";
    const pct = parsed <= 1 && parsed > 0 ? parsed * 100 : parsed;
    if (pct >= 90) return "This looks like a strong application position if the loaded ladder remains current.";
    if (pct >= 55) return "This is a reasonable application candidate; compare quality and opportunity before committing.";
    if (pct >= 20) return "This is a reach application; use comparable hunts to decide if the upside is worth it.";
    if (permits !== null && permits <= 5) return "Odds are thin and permit volume is very small, so treat this as a premium swing.";
    return "Odds are thin at this point level; consider comparable hunts with better opportunity.";
  }

  function renderComparableCards(rows) {
    if (!rows.length) return `<p class="uoga-outlook-muted">No comparable rows loaded for this species/type/residency slice.</p>`;
    return `
      <div class="uoga-comparable-grid">
        ${rows.slice(0, 5).map((row) => `
          <article class="uoga-comparable-card">
            <strong>${escapeHtml(row.hunt_code || "")}</strong>
            <span>${escapeHtml(row.hunt_name || "Comparable hunt")}</span>
            <div>
              <b>${escapeHtml(formatInteger(firstValue(row, ["permits_2026_total", "public_permits_2026", "permit_allotment_2026_total"])))}</b>
              <small>permits</small>
            </div>
            <div>
              <b>${escapeHtml(formatAge(row.average_harvest_age))}</b>
              <small>avg age</small>
            </div>
          </article>`).join("")}
      </div>`;
  }

  function renderManagementPanel(rows) {
    const row = rows[0] || {};
    const objectiveRange = hasValue(row.management_objective_min)
      ? `${formatValue(row.management_objective_min)}${hasValue(row.management_objective_max) ? ` to ${formatValue(row.management_objective_max)}` : ""} ${formatValue(row.objective_unit, "")}`.trim()
      : "No objective row loaded";
    return panel("State Objective / Management Read", `
      <div class="uoga-badge">Management Plan Context</div>
      ${listRows([
        metricRow("Objective type", formatValue(row.management_objective_type, "No objective row loaded")),
        metricRow("Objective range", objectiveRange),
        metricRow("Observed vs objective", formatValue(row.objective_status || row.observed_vs_objective_status || row.objective_status_rule)),
      ])}
      <p class="uoga-outlook-note">${escapeHtml(formatValue(row.notes || row.objective_status_rule, "Benchmark only — does not change draw odds."))}</p>
      <p class="uoga-outlook-muted">Benchmark only — does not change draw odds.</p>
    `);
  }

  function sourceDetails(selection, selectedRow, meta, sourceBits) {
    const sourceFile = firstValue(selectedRow, ["source_file", "truth_source_file", "average_harvest_age_source_file"])
      || firstValue(meta, ["truth_source_file", "average_harvest_age_source_file"]);
    const sourcePage = firstValue(selectedRow, ["page_number", "source_page", "truth_source_page"])
      || firstValue(meta, ["page_number", "source_page", "truth_source_page"]);
    return `
      <details class="uoga-source-details">
        <summary>Source / freshness / model details</summary>
        <div class="uoga-source-grid">
          ${metricRow("Engine mode", window.UOGA_CONFIG?.HUNT_RESEARCH_ENGINE_MODE || "observed")}
          ${metricRow("Data version", window.UOGA_CONFIG?.HUNT_RESEARCH_DATA_VERSION || "not configured")}
          ${metricRow("Model/rule version", window.UOGA_CONFIG?.HUNT_RESEARCH_RULE_VERSION || window.UOGA_CONFIG?.HUNT_RESEARCH_MODEL_VERSION || "core Research rules")}
          ${metricRow("Selected hunt", `${selection.huntCode} / ${selection.residency} / ${selection.points} pts`)}
          ${metricRow("Source file", formatValue(sourceFile))}
          ${metricRow("Source page", formatValue(sourcePage))}
        </div>
        <p class="uoga-source-paths">${escapeHtml(sourceBits.join(" | "))}</p>
      </details>`;
  }

  function dashboardHtml(selection, context) {
    const { meta, reference, ladderRows, ladderPoint, engineRows, selectedRow, managementRows, comparable } = context;
    const title = meta?.hunt_name || selectedRow?.hunt_name || reference?.hunt_name || selection.huntCode || "Selected hunt";
    const odds = getSelectedOdds(selectedRow, ladderPoint, meta);
    const averageAge = getAge(meta, reference, selectedRow);
    const currentAge = getCurrentAge(meta, reference, selectedRow);
    const harvestSuccess = getHarvestSuccess(meta, reference, selectedRow);
    const avgDays = getAverageDays(meta, reference);
    const permitTotal = getPermitTotal(meta, reference, selectedRow);
    const guaranteedLine = getGuaranteedLine(selectedRow, meta);
    const pointTrend = getPointTrend(selectedRow, meta);
    const pointStatus = firstValue(selectedRow, ["status", "draw_outlook", "point_status"])
      || firstValue(meta, ["status", "draw_outlook", "point_status"]);
    const percentFivePlus = getPercentFivePlus(meta, reference, selectedRow);
    const decision = decisionLabel(odds);
    const recommendation = recommendationSentence(odds, permitTotal);
    const sourceBits = [
      `engine: ${state.sources.engine || "not loaded"}`,
      `ladder: ${state.sources.ladder || "not loaded"}`,
      `master: ${state.sources.master || "not loaded"}`,
      `reference: ${state.sources.reference || "not loaded"}`,
      state.sources.management ? `management: ${state.sources.management}` : "",
    ].filter(Boolean);

    return `
      <div class="uoga-outlook-dashboard">
        <section class="uoga-outlook-hero">
          <div class="uoga-outlook-hero-title">
            <p>Hunt Application Outlook</p>
            <h3>${escapeHtml(selection.huntCode || "No hunt selected")}: ${escapeHtml(title)}</h3>
            <span>${escapeHtml(selection.residency)} · ${escapeHtml(String(selection.points))} points · ${escapeHtml(selection.drawPool)} draw pool</span>
          </div>
          ${metricRow("Decision read", decision)}
          ${metricRow("Estimated draw odds", formatPercent(odds))}
          ${metricRow("2026 permits", formatInteger(permitTotal))}
          <p class="uoga-outlook-recommendation">${escapeHtml(recommendation)}</p>
        </section>
        <div class="uoga-outlook-grid">
          ${panel("Application Read", listRows([
            metricRow("Estimated draw odds", formatPercent(odds)),
            metricRow("Point status", formatValue(pointStatus)),
            metricRow("Guaranteed line", formatValue(guaranteedLine)),
            metricRow("Point creep / trend", formatValue(pointTrend)),
            metricRow("Permits", formatInteger(permitTotal)),
          ]))}
          ${panel("Hunt Quality", listRows([
            metricRow("Harvest success", formatPercent(harvestSuccess)),
            metricRow("Average days hunted", formatValue(avgDays)),
            metricRow("Average harvest age", formatAge(averageAge)),
            metricRow("Current 3-year age avg", formatAge(currentAge)),
            metricRow("Percent 5+", formatPercent(percentFivePlus)),
          ]))}
          ${renderManagementPanel(managementRows)}
        </div>
        <section class="uoga-outlook-panel is-compact uoga-outlook-wide">
          <h4>Comparable Hunts</h4>
          ${renderComparableCards(comparable)}
        </section>
        ${sourceDetails(selection, selectedRow, meta, sourceBits)}
      </div>`;
  }

  function ensureStyles() {
    if (document.getElementById("uogaOutlookDashboardStyles")) return;
    const style = document.createElement("style");
    style.id = "uogaOutlookDashboardStyles";
    style.textContent = `
      #${DASHBOARD_ID} {
        margin: 12px 0 18px;
        border: 1px solid rgba(124, 77, 38, 0.28);
        border-radius: 22px;
        overflow: hidden;
        background:
          radial-gradient(circle at top left, rgba(240, 120, 0, 0.14), transparent 32%),
          linear-gradient(180deg, rgba(255, 252, 246, 0.96), rgba(244, 233, 219, 0.96));
        color: var(--text);
        box-shadow: 0 18px 42px rgba(70, 43, 20, 0.12);
      }
      .uoga-outlook-dashboard {
        display: grid;
        gap: 14px;
        padding: 14px;
      }
      .uoga-outlook-hero {
        align-items: center;
        display: grid;
        gap: 12px;
        grid-template-columns: minmax(260px, 1.25fr) repeat(3, minmax(150px, .6fr));
      }
      .uoga-outlook-hero-title {
        min-width: 0;
      }
      .uoga-outlook-hero-title p,
      .uoga-outlook-panel h4,
      .uoga-source-details summary {
        color: #6e4323;
        font-size: 11px;
        font-weight: 950;
        letter-spacing: .06em;
        text-transform: uppercase;
      }
      .uoga-outlook-hero-title p {
        margin: 0 0 4px;
      }
      .uoga-outlook-hero-title h3 {
        font-family: var(--font-display);
        font-size: clamp(22px, 2.4vw, 32px);
        line-height: .98;
        margin: 0;
      }
      .uoga-outlook-hero-title span {
        color: var(--muted);
        display: block;
        font-weight: 850;
        margin-top: 6px;
      }
      .uoga-outlook-recommendation {
        align-self: stretch;
        background: rgba(255, 255, 255, .58);
        border: 1px solid rgba(124, 77, 38, 0.15);
        border-radius: 16px;
        color: #2b1c12;
        display: flex;
        flex-direction: column;
        font-weight: 800;
        justify-content: center;
        line-height: 1.38;
        margin: 0;
        padding: 12px;
      }
      .uoga-outlook-grid {
        display: grid;
        gap: 14px;
        grid-template-columns: 1fr 1fr 1fr;
      }
      .uoga-outlook-panel {
        background: rgba(255,255,255,.50);
        border: 1px solid rgba(124, 77, 38, 0.16);
        border-radius: 18px;
        min-height: auto;
        padding: 13px;
      }
      .uoga-outlook-panel.is-compact {
        min-height: auto;
      }
      .uoga-outlook-panel h4 {
        margin: 0 0 10px;
      }
      .uoga-outlook-wide { grid-column: 1 / -1; }
      .uoga-outlook-metrics {
        display: grid;
        gap: 8px;
      }
      .uoga-outlook-panel .uoga-outlook-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .uoga-outlook-metric {
        background: rgba(255, 255, 255, .56);
        border: 1px solid rgba(124, 77, 38, 0.13);
        border-radius: 13px;
        display: grid;
        gap: 2px;
        padding: 8px 9px;
      }
      .uoga-outlook-metric span {
        color: #7b5a39;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: .04em;
        text-transform: uppercase;
      }
      .uoga-outlook-metric strong {
        color: #24170f;
        font-size: 16px;
        line-height: 1.12;
      }
      .uoga-outlook-metric small,
      .uoga-outlook-muted,
      .uoga-outlook-note {
        color: var(--muted);
        line-height: 1.45;
      }
      .uoga-badge {
        background: rgba(0, 166, 80, .12);
        border: 1px solid rgba(0, 128, 72, .25);
        border-radius: 999px;
        color: #006c3b;
        display: inline-flex;
        font-size: 11px;
        font-weight: 950;
        margin-bottom: 9px;
        padding: 6px 9px;
        text-transform: uppercase;
      }
      .uoga-outlook-note {
        margin: 10px 0 0;
      }
      .uoga-comparable-grid {
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(5, minmax(0, 1fr));
      }
      .uoga-comparable-card {
        background: rgba(255, 255, 255, .58);
        border: 1px solid rgba(124, 77, 38, 0.14);
        border-radius: 15px;
        display: grid;
        gap: 7px;
        min-width: 0;
        padding: 11px;
      }
      .uoga-comparable-card strong {
        color: #24170f;
        font-size: 16px;
      }
      .uoga-comparable-card span {
        color: var(--muted);
        min-height: 34px;
      }
      .uoga-comparable-card div {
        align-items: baseline;
        display: flex;
        gap: 6px;
      }
      .uoga-comparable-card b {
        color: #24170f;
      }
      .uoga-comparable-card small {
        color: var(--muted);
      }
      .uoga-source-details {
        background: rgba(255, 255, 255, .38);
        border: 1px solid rgba(124, 77, 38, 0.13);
        border-radius: 16px;
        margin-top: 4px;
        padding: 10px 12px;
      }
      .uoga-source-details summary {
        cursor: pointer;
      }
      .uoga-source-details[open] {
        padding-bottom: 12px;
      }
      .uoga-source-grid {
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        margin-top: 10px;
      }
      .uoga-source-paths {
        color: var(--muted);
        font-size: 12px;
        line-height: 1.5;
        overflow-wrap: anywhere;
      }
      @media (max-width: 1220px) {
        .uoga-outlook-hero {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .uoga-outlook-hero-title,
        .uoga-outlook-recommendation {
          grid-column: 1 / -1;
        }
        .uoga-outlook-grid,
        .uoga-source-grid {
          grid-template-columns: 1fr;
        }
        .uoga-comparable-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
      @media (max-width: 768px) {
        .uoga-outlook-dashboard,
        .uoga-outlook-hero,
        .uoga-outlook-grid,
        .uoga-comparable-grid,
        .uoga-source-grid,
        .uoga-outlook-panel .uoga-outlook-metrics {
          grid-template-columns: 1fr;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function ensurePanel() {
    const ladder = document.getElementById("pointLadderAccordion");
    const detailContent = document.getElementById("detailContent");
    const parent = ladder?.parentElement || detailContent || document.querySelector(".result-card .card-body") || document.querySelector(".main-stack");
    if (!parent) return null;

    let panel = document.getElementById(DASHBOARD_ID);
    if (!panel) {
      panel = document.createElement("section");
      panel.id = DASHBOARD_ID;
      panel.setAttribute("aria-live", "polite");
    }
    if (ladder && ladder.parentElement) {
      ladder.parentElement.insertBefore(panel, ladder);
    } else if (detailContent && !panel.parentElement) {
      detailContent.insertAdjacentElement("afterend", panel);
    } else if (!panel.parentElement) {
      parent.appendChild(panel);
    }
    return panel;
  }

  function renderLoading(panel, selection) {
    panel.innerHTML = `
      <div class="uoga-outlook-dashboard">
        <section class="uoga-outlook-hero">
          <div class="uoga-outlook-hero-title">
            <p>Hunt Application Outlook</p>
            <h3>${escapeHtml(selection.huntCode || "Selected hunt")}</h3>
            <span>${escapeHtml(selection.residency)} · ${escapeHtml(String(selection.points))} points</span>
          </div>
          <p class="uoga-outlook-recommendation">Loading Research rows for the dashboard display layer.</p>
        </section>
      </div>`;
  }

  async function render() {
    if (!isResearchPage()) return;
    ensureStyles();
    const panel = ensurePanel();
    if (!panel) return;
    if (!state.coreReady && window.UOGA_HUNT_RESEARCH_SNAPSHOT) {
      applyCoreSnapshot(window.UOGA_HUNT_RESEARCH_SNAPSHOT);
    }

    const selection = getSelection();
    if (!selection.huntCode) {
      panel.innerHTML = `
        <div class="uoga-outlook-dashboard">
          <section class="uoga-outlook-hero">
            <div class="uoga-outlook-hero-title">
              <p>Hunt Application Outlook</p>
              <h3>No hunt selected yet</h3>
              <span>Dashboard add-on loaded.</span>
            </div>
            <p class="uoga-outlook-recommendation">Choose a hunt in Hunt Builder or pass a hunt_code in the URL.</p>
          </section>
        </div>`;
      return;
    }

    if (!state.coreReady) {
      renderLoading(panel, selection);
      return;
    }
    try {
      await loadData();
      const context = findContext(selection);
      panel.innerHTML = dashboardHtml(selection, context);
    } catch (error) {
      state.error = error && error.message ? error.message : String(error);
      panel.innerHTML = `
        <div class="uoga-outlook-dashboard">
          <section class="uoga-outlook-hero">
            <div class="uoga-outlook-hero-title">
              <p>Hunt Application Outlook</p>
              <h3>${escapeHtml(selection.huntCode)}</h3>
              <span>${escapeHtml(selection.residency)} · ${escapeHtml(String(selection.points))} points</span>
            </div>
            <p class="uoga-outlook-recommendation">${escapeHtml(state.error)}</p>
          </section>
        </div>`;
    }
  }

  function bindRefreshEvents() {
    window.addEventListener("uoga:hunt-research-rendered", (event) => {
      applyCoreSnapshot(event.detail);
      window.setTimeout(render, 0);
    });

    ["huntCodeInput", "residencySelect", "drawPoolSelect", "pointsInput", "runResearchButton"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      const eventName = id === "runResearchButton" ? "click" : "change";
      el.addEventListener(eventName, () => window.setTimeout(render, 0));
      if (id === "huntCodeInput" || id === "pointsInput") {
        el.addEventListener("input", () => window.setTimeout(render, 120));
      }
    });

    const detail = document.getElementById("detailContent");
    if (detail && window.MutationObserver) {
      const observer = new MutationObserver(() => window.setTimeout(render, 0));
      observer.observe(detail, { attributes: true, attributeFilter: ["hidden"] });
    }
  }

  function init() {
    bindRefreshEvents();
    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
