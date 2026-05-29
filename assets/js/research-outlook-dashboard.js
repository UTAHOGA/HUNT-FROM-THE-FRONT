(() => {
  "use strict";

  const DASHBOARD_ID = "uogaApplicationOutlookDashboard";
  const SELECTED_HUNT_KEY = "selected_hunt_code";
  const SELECTED_RESIDENCY_KEY = "selected_hunt_research_residency";
  const SELECTED_POINTS_KEY = "selected_hunt_research_points";

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

  function hasValue(value) {
    return String(value ?? "").trim() !== "";
  }

  function normalizeCode(value) {
    return String(value || "").trim().toUpperCase();
  }

  function normalizeResidency(value) {
    const text = String(value || "").trim().toLowerCase();
    if (["nr", "non-res", "nonresident", "non-resident"].includes(text)) return "Nonresident";
    return "Resident";
  }

  function numericPoints(value) {
    const parsed = Number(String(value ?? "").replace(/[^0-9.-]/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function readParams() {
    const search = new URLSearchParams(window.location.search || "");
    const hash = new URLSearchParams(String(window.location.hash || "").replace(/^#/, ""));
    return {
      get(name) {
        return search.get(name) || hash.get(name) || "";
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
        // Storage can be blocked in embedded contexts; URL and form values still work.
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
    const stored = readStoredSelectionObject();
    const huntInput = document.getElementById("huntCodeInput");
    const residencyInput = document.getElementById("residencySelect");
    const pointsInput = document.getElementById("pointsInput");
    return {
      huntCode: normalizeCode(
        params.get("hunt_code")
        || huntInput?.value
        || stored.hunt_code
        || stored.huntCode
        || readStorageValue(SELECTED_HUNT_KEY)
      ),
      residency: normalizeResidency(
        params.get("residency")
        || residencyInput?.value
        || stored.residency
        || readStorageValue(SELECTED_RESIDENCY_KEY)
      ),
      points: numericPoints(
        params.get("points")
        || pointsInput?.value
        || stored.points
        || stored.selected_points
        || readStorageValue(SELECTED_POINTS_KEY)
      ),
    };
  }

  function ensureStyles() {
    if (document.getElementById("uogaApplicationOutlookStyles")) return;
    const style = document.createElement("style");
    style.id = "uogaApplicationOutlookStyles";
    style.textContent = `
      #${DASHBOARD_ID}.uoga-outlook-card {
        margin: 18px 0 20px;
        width: 100%;
      }

      #${DASHBOARD_ID} .uoga-outlook-proof {
        display: grid;
        gap: 10px;
      }

      #${DASHBOARD_ID} .uoga-outlook-kicker {
        color: #7a4f18;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        margin: 0;
        text-transform: uppercase;
      }

      #${DASHBOARD_ID} h3 {
        color: #1d2a1f;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(1.35rem, 2vw, 1.9rem);
        line-height: 1.08;
        margin: 0;
      }

      #${DASHBOARD_ID} .uoga-outlook-line {
        color: #263128;
        font-weight: 800;
        margin: 0;
      }

      #${DASHBOARD_ID} .uoga-outlook-subtext {
        color: #596459;
        line-height: 1.55;
        margin: 0;
        max-width: 980px;
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
      panel.className = "research-card uoga-outlook-card";
      panel.setAttribute("aria-live", "polite");
    }

    if (ladder && ladder.parentElement) {
      ladder.parentElement.insertBefore(panel, ladder);
    } else if (detailContent) {
      detailContent.insertAdjacentElement("afterend", panel);
    } else {
      parent.appendChild(panel);
    }
    return panel;
  }

  function render() {
    if (!isResearchPage()) return;
    ensureStyles();
    const panel = ensurePanel();
    if (!panel) return;

    const selection = getSelection();
    const huntCode = selection.huntCode || "selected hunt";
    const residency = selection.residency || "Resident";
    const points = selection.points;

    panel.innerHTML = `
      <div class="card-body uoga-outlook-proof">
        <p class="uoga-outlook-kicker">Hunt Application Outlook</p>
        <h3>Hunt Application Outlook</h3>
        <p class="uoga-outlook-line">Dashboard add-on loaded for ${escapeHtml(huntCode)} &middot; ${escapeHtml(residency)} &middot; ${escapeHtml(points)} points.</p>
        <p class="uoga-outlook-subtext">This panel will display draw outlook, harvest quality, age quality, management objectives, comparable hunts, and source/model details.</p>
      </div>`;
  }

  function bindRefreshEvents() {
    window.addEventListener("uoga:hunt-research-rendered", () => window.setTimeout(render, 0));
    ["huntCodeInput", "residencySelect", "pointsInput", "runResearchButton"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      const eventName = id === "runResearchButton" ? "click" : "change";
      el.addEventListener(eventName, () => window.setTimeout(render, 0));
      if (id === "huntCodeInput" || id === "pointsInput") {
        el.addEventListener("input", () => window.setTimeout(render, 120));
      }
    });
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
