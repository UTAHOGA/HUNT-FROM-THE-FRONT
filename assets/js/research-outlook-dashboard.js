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
    return parsed === null || parsed <= 0 ? "Not available" : parsed.toFixed(1);
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

  function statCard(label, value, note) {
    return `
      <div class="uoga-outlook-stat">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
        ${note ? `<small>${escapeHtml(note)}</small>` : ""}
      </div>`;
  }

  function section(title, body, extraClass = "") {
    return `
      <section class="uoga-outlook-section ${extraClass}">
        <h4>${escapeHtml(title)}</h4>
        ${body}
      </section>`;
  }

  function listRows(items) {
    if (!items.length) return `<p class="uoga-outlook-muted">Not available from the loaded runtime rows.</p>`;
    return `<ul class="uoga-outlook-list">${items.map((item) => `<li>${item}</li>`).join("")}</ul>`;
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

  function renderComparableTable(rows) {
    if (!rows.length) return `<p class="uoga-outlook-muted">No comparable rows loaded for this species/type/residency slice.</p>`;
    return `
      <div class="uoga-outlook-table-wrap">
        <table class="uoga-outlook-table">
          <thead><tr><th>Hunt</th><th>Permits</th><th>Age</th><th>Harvest</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td><strong>${escapeHtml(row.hunt_code || "")}</strong><br><span>${escapeHtml(row.hunt_name || "")}</span></td>
                <td>${escapeHtml(formatInteger(firstValue(row, ["permits_2026_total", "public_permits_2026", "permit_allotment_2026_total"])))}</td>
                <td>${escapeHtml(formatAge(row.average_harvest_age))}</td>
                <td>${escapeHtml(formatPercent(firstValue(row, ["success_percent", "harvest_success_percent_2025", "percent_harvest_success"])))}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  }

  function renderManagementSection(rows) {
    if (!rows.length) return "";
    return section("State Management Objective", rows.map((row) => `
      <div class="uoga-outlook-objective">
        <strong>${escapeHtml(row.management_objective_type || "Management objective")}</strong>
        <p>${escapeHtml(formatValue(row.management_objective_min))}${hasValue(row.management_objective_max) ? ` to ${escapeHtml(row.management_objective_max)}` : ""} ${escapeHtml(row.objective_unit || "")}</p>
        <small>${escapeHtml(row.notes || row.objective_status_rule || "Context only. Does not change draw odds or permit quotas.")}</small>
      </div>`).join(""));
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
    const sourceBits = [
      `engine: ${state.sources.engine || "not loaded"}`,
      `ladder: ${state.sources.ladder || "not loaded"}`,
      `master: ${state.sources.master || "not loaded"}`,
      `reference: ${state.sources.reference || "not loaded"}`,
      state.sources.management ? `management: ${state.sources.management}` : "",
    ].filter(Boolean);

    return `
      <div class="uoga-outlook-shell">
        <div class="uoga-outlook-head">
          <div>
            <p>Hunt Application Outlook</p>
            <h3>${escapeHtml(selection.huntCode || "No hunt selected")}: ${escapeHtml(title)}</h3>
            <span>${escapeHtml(selection.residency)} | ${escapeHtml(String(selection.points))} points | ${escapeHtml(selection.drawPool)} draw pool</span>
          </div>
          <div class="uoga-outlook-loaded">Dashboard add-on loaded.</div>
        </div>
        <div class="uoga-outlook-stats">
          ${statCard("Estimated Draw Odds", formatPercent(odds), "Display only; core math unchanged")}
          ${statCard("2026 Permits", formatInteger(permitTotal), "From loaded runtime rows")}
          ${statCard("Avg Harvest Age", formatAge(averageAge), "Reviewed hard-data age")}
          ${statCard("Current Age 3-yr Avg", formatAge(currentAge), "DWR Hunt Planner context")}
        </div>
        <div class="uoga-outlook-grid">
          ${section("Selected Hunt Summary", listRows([
            `<strong>Species:</strong> ${escapeHtml(formatValue(meta?.species || selectedRow?.species))}`,
            `<strong>Weapon:</strong> ${escapeHtml(formatValue(meta?.weapon || selectedRow?.weapon))}`,
            `<strong>Hunt type:</strong> ${escapeHtml(formatValue(meta?.hunt_type || selectedRow?.hunt_type))}`,
            `<strong>Boundary ID:</strong> ${escapeHtml(formatValue(meta?.boundary_id || reference?.boundary_id || selectedRow?.boundary_id))}`,
          ]))}
          ${section("Hunt Application Outlook", listRows([
            `<strong>Selected odds:</strong> ${escapeHtml(formatPercent(odds))}`,
            `<strong>Point status:</strong> ${escapeHtml(formatValue(selectedRow?.status || selectedRow?.draw_outlook || meta?.draw_outlook))}`,
            `<strong>Trend:</strong> ${escapeHtml(formatValue(selectedRow?.trend || meta?.trend))}`,
            `<strong>Guaranteed line:</strong> ${escapeHtml(formatValue(selectedRow?.guaranteed_at_2026 || meta?.guaranteed_at_2026))}`,
          ]))}
          ${section("Historical Draw Context", listRows([
            `<strong>Ladder rows loaded:</strong> ${escapeHtml(String(ladderRows.length))}`,
            `<strong>Engine rows loaded:</strong> ${escapeHtml(String(engineRows.length))}`,
            `<strong>2025 result:</strong> ${escapeHtml(formatValue(selectedRow?.display_2025_draw_results || selectedRow?.dwr_result_display || meta?.odds_2025))}`,
            `<strong>Applicants at level:</strong> ${escapeHtml(formatInteger(selectedRow?.applicants_at_level || selectedRow?.eligible_applicants))}`,
          ]))}
          ${section("Harvest Quality", listRows([
            `<strong>Harvest success:</strong> ${escapeHtml(formatPercent(harvestSuccess))}`,
            `<strong>Average days hunted:</strong> ${escapeHtml(formatValue(avgDays))}`,
            `<strong>Harvest source:</strong> ${escapeHtml(formatValue(reference?.source_pdf || meta?.truth_source_file || meta?.truth_source_status))}`,
          ]))}
          ${section("Age Quality / Trophy Context", listRows([
            `<strong>Average harvest age:</strong> ${escapeHtml(formatAge(averageAge))}`,
            `<strong>Current age 3-year average:</strong> ${escapeHtml(formatAge(currentAge))}`,
            `<strong>Age source:</strong> ${escapeHtml(formatValue(meta?.average_harvest_age_source_file || selectedRow?.average_harvest_age_source_file))}`,
            `<strong>Review status:</strong> ${escapeHtml(formatValue(meta?.average_harvest_age_review_status || selectedRow?.average_harvest_age_review_status))}`,
          ]))}
          ${renderManagementSection(managementRows)}
          ${section("Comparable Hunts", renderComparableTable(comparable), "uoga-outlook-wide")}
          ${section("Source / Freshness / Model Details", listRows([
            `<strong>Engine mode:</strong> ${escapeHtml(window.UOGA_CONFIG?.HUNT_RESEARCH_ENGINE_MODE || "observed")}`,
            `<strong>Data version:</strong> ${escapeHtml(window.UOGA_CONFIG?.HUNT_RESEARCH_DATA_VERSION || "not configured")}`,
            `<strong>Loaded source paths:</strong> ${escapeHtml(sourceBits.join(" | "))}`,
          ]), "uoga-outlook-wide")}
        </div>
      </div>`;
  }

  function ensureStyles() {
    if (document.getElementById("uogaOutlookDashboardStyles")) return;
    const style = document.createElement("style");
    style.id = "uogaOutlookDashboardStyles";
    style.textContent = `
      #${DASHBOARD_ID} {
        margin: 12px 0 16px;
        border: 1px solid rgba(124, 77, 38, 0.28);
        border-radius: 22px;
        overflow: hidden;
        background:
          radial-gradient(circle at top left, rgba(240, 120, 0, 0.14), transparent 32%),
          linear-gradient(180deg, rgba(255, 252, 246, 0.96), rgba(244, 233, 219, 0.96));
        color: var(--text);
        box-shadow: 0 18px 42px rgba(70, 43, 20, 0.12);
      }
      .uoga-outlook-shell { padding: 16px; display: grid; gap: 14px; }
      .uoga-outlook-head { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; }
      .uoga-outlook-head p { margin: 0 0 4px; color: var(--accent); font-weight: 900; letter-spacing: 0.08em; text-transform: uppercase; font-size: 11px; }
      .uoga-outlook-head h3 { margin: 0; font-family: var(--font-display); font-size: clamp(22px, 3vw, 34px); line-height: .96; }
      .uoga-outlook-head span { display: block; margin-top: 7px; color: var(--muted); font-weight: 800; }
      .uoga-outlook-loaded { border: 1px solid rgba(0, 128, 72, .25); color: #006c3b; background: rgba(0, 166, 80, .12); border-radius: 999px; padding: 8px 11px; font-weight: 900; white-space: nowrap; }
      .uoga-outlook-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
      .uoga-outlook-stat { border: 1px solid rgba(124, 77, 38, 0.18); border-radius: 16px; padding: 12px; background: rgba(255, 255, 255, .56); display: grid; gap: 3px; }
      .uoga-outlook-stat span, .uoga-outlook-section h4 { color: #6e4323; font-size: 11px; font-weight: 950; letter-spacing: .06em; text-transform: uppercase; }
      .uoga-outlook-stat strong { font-size: 20px; color: #24170f; }
      .uoga-outlook-stat small, .uoga-outlook-muted, .uoga-outlook-objective small { color: var(--muted); line-height: 1.5; }
      .uoga-outlook-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
      .uoga-outlook-section { border: 1px solid rgba(124, 77, 38, 0.16); border-radius: 18px; background: rgba(255,255,255,.48); padding: 13px; }
      .uoga-outlook-section h4 { margin: 0 0 9px; }
      .uoga-outlook-list { margin: 0; padding-left: 18px; display: grid; gap: 7px; color: #2b1c12; }
      .uoga-outlook-objective { display: grid; gap: 5px; }
      .uoga-outlook-objective p { margin: 0; color: #2b1c12; }
      .uoga-outlook-wide { grid-column: 1 / -1; }
      .uoga-outlook-table-wrap { overflow-x: auto; }
      .uoga-outlook-table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .uoga-outlook-table th, .uoga-outlook-table td { border-bottom: 1px solid rgba(124, 77, 38, 0.14); padding: 8px; text-align: left; vertical-align: top; }
      .uoga-outlook-table th { color: #6e4323; font-size: 11px; letter-spacing: .05em; text-transform: uppercase; }
      .uoga-outlook-table span { color: var(--muted); }
      @media (max-width: 900px) {
        .uoga-outlook-head { display: grid; }
        .uoga-outlook-stats, .uoga-outlook-grid { grid-template-columns: 1fr; }
        .uoga-outlook-loaded { width: fit-content; }
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
      <div class="uoga-outlook-shell">
        <div class="uoga-outlook-head">
          <div>
            <p>Hunt Application Outlook</p>
            <h3>${escapeHtml(selection.huntCode || "Selected hunt")}</h3>
            <span>${escapeHtml(selection.residency)} | ${escapeHtml(String(selection.points))} points</span>
          </div>
          <div class="uoga-outlook-loaded">Dashboard add-on loaded.</div>
        </div>
        <p class="uoga-outlook-muted">Loading Cloudflare runtime rows for the full outlook dashboard.</p>
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
        <div class="uoga-outlook-shell">
          <div class="uoga-outlook-head">
            <div>
              <p>Hunt Application Outlook</p>
              <h3>No hunt selected yet</h3>
              <span>Dashboard add-on loaded.</span>
            </div>
          </div>
          <p class="uoga-outlook-muted">Choose a hunt in Hunt Builder or pass a hunt_code in the URL.</p>
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
        <div class="uoga-outlook-shell">
          <div class="uoga-outlook-head">
            <div>
              <p>Hunt Application Outlook</p>
              <h3>${escapeHtml(selection.huntCode)}</h3>
              <span>${escapeHtml(selection.residency)} | ${escapeHtml(String(selection.points))} points</span>
            </div>
            <div class="uoga-outlook-loaded">Dashboard add-on loaded.</div>
          </div>
          <p class="uoga-outlook-muted">${escapeHtml(state.error)}</p>
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
