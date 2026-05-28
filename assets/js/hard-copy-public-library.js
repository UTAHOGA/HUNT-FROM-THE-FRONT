(() => {
  const CURRENT_YEAR = "2026";
  const MANIFEST_URLS = [
    "./processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json",
    "./processed_data/hard_data_exports/hard_data_manifest.web.json",
    "./processed_data/hard_data_exports/library/public_library_manual_items.json",
  ];

  const FOLDERS = [
    { id: "rules", title: "UTAH DWR RULES & REGULATIONS", description: "Current-year/current-cycle public rules and regulation PDFs." },
    { id: "harvest", title: "HARVEST DATA", description: "Public harvest reports and data across years." },
    { id: "draw", title: "DRAW RESULTS", description: "Public draw results and draw odds across years." },
    { id: "conservation", title: "CONSERVATION PERMITS", description: "Current-cycle conservation permit references." },
    { id: "expo", title: "HUNT EXPO", description: "Current-year Hunt Expo permit number references." },
    { id: "calendar", title: "SIGNIFICANT DATES / CALENDAR", description: "Application windows, deadlines, season dates, and calendar references." },
    { id: "units2026", title: "2026 HUNT UNITS / PERMIT NUMBERS", description: "Current 2026 hunt code, hunt name, unit, and permit numbers." },
    { id: "outfitters", title: "UTAH OUTFITTERS BY HUNT CODE/HUNT NAME", description: "Outfitter resources tied to hunt code and hunt name." },
  ];

  const RUNTIME_DENYLIST = [
    "processed_data/hunt_master_enriched.csv",
    "processed_data/point_ladder_view.csv",
    "processed_data/draw_reality_engine_predictive_v2.csv",
    "processed_data/draw_reality_engine_v2.csv",
    "processed_data/ml_draw_predictions_v1.csv",
    "processed_data/draw_system_coverage_report.csv",
    "processed_data/predictive_coverage_report.csv",
    "processed_data/model_outputs/",
    "processed_data/audits/",
    "current_to_historical_hunt_code_crosswalk_2026.csv",
    "hard_data_manifest",
    "library_page_data.json",
    "library_page_summary.json",
    "hunt_database_complete.csv",
  ];

  const ALLOWLIST_FILES = [
    "processed_data/hard_data_exports/library/library_page_hunts.csv",
    "processed_data/library/library_page_hunts.csv",
  ];

  const FIXED_PUBLIC_ITEMS = [
    {
      id: "units2026::library-page-hunts",
      folderId: "units2026",
      title: "2026 Hunt Units / Permit Numbers by Hunt Code and Hunt Name",
      subtitle: "Current 2026 hunt code, hunt name, hunt unit, and permit table.",
      href: "./processed_data/hard_data_exports/library/library_page_hunts.csv",
      type: "csv",
      year: "2026",
      group: "exports",
      delivery: "pages-local",
      searchText: "2026 hunt units permit numbers hunt code hunt name hunt unit permits library_page_hunts csv",
      embedded: false,
    },
  ];

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function safeUrl(value) {
    try {
      const url = new URL(String(value), window.location.origin);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
    } catch {
      return "#";
    }
  }

  function inferYear(item) {
    const text = `${item.year || ""} ${item.title || ""} ${item.subtitle || ""} ${item.href || ""}`;
    const yearMatch = text.match(/\b(20\d{2})\b/);
    if (yearMatch) return yearMatch[1];
    const cycleMatch = text.match(/\b(20\d{2})-(\d{2})\b/);
    if (cycleMatch) return cycleMatch[1];
    return "";
  }

  function currentCycle(text) {
    return /2026/.test(text) || /2025[-_/ ]?26/.test(text) || /2025[-_/ ]?27/.test(text);
  }

  function toFolderId(item) {
    const hay = `${item.group || ""} ${item.source || ""} ${item.title || ""} ${item.subtitle || ""} ${item.href || ""}`.toLowerCase();
    if (hay.includes("outfitter")) return "outfitters";
    if (hay.includes("calendar") || hay.includes("deadline") || hay.includes("season date") || hay.includes("application date")) return "calendar";
    if (hay.includes("expo")) return "expo";
    if (hay.includes("conservation")) return "conservation";
    if (hay.includes("harvest")) return "harvest";
    if (hay.includes("draw") || hay.includes("odds") || hay.includes("bonus point")) return "draw";
    if (hay.includes("regulation") || hay.includes("rules") || hay.includes("guidebook") || hay.includes("proclamation") || hay.includes("application")) return "rules";
    if (hay.includes("library_page_hunts")) return "units2026";
    if (hay.includes("hunt units") || hay.includes("permit numbers") || hay.includes("allotment") || hay.includes("hunt_code")) return "units2026";
    return "";
  }

  function isRuntimeDenied(item) {
    const hay = `${item.href || ""} ${item.local_href || ""} ${item.title || ""} ${item.subtitle || ""} ${item.source || ""}`.toLowerCase();
    return RUNTIME_DENYLIST.some((token) => hay.includes(token.toLowerCase()));
  }

  function isExplicitAllow(item) {
    const hay = `${item.href || ""} ${item.local_href || ""}`.toLowerCase();
    return ALLOWLIST_FILES.some((token) => hay.includes(token.toLowerCase()));
  }

  function passesFolderRules(folderId, item) {
    const hay = `${item.title || ""} ${item.subtitle || ""} ${item.href || ""}`.toLowerCase();
    const year = String(item.year || inferYear(item));
    if (folderId === "rules") return currentCycle(`${hay} ${year}`);
    if (folderId === "conservation") return currentCycle(`${hay} ${year}`);
    if (folderId === "expo") return year === CURRENT_YEAR || (currentCycle(`${hay} ${year}`) && hay.includes("permit"));
    if (folderId === "units2026") return year === CURRENT_YEAR || isExplicitAllow(item);
    if (folderId === "calendar") return true;
    return true;
  }

  function toPublicItem(raw) {
    const title = String(raw.title || "").trim();
    const href = String(raw.href || "").trim();
    const type = String(raw.type || "").trim().toLowerCase();
    const subtitle = String(raw.subtitle || "").trim();
    const group = String(raw.group || "").trim().toLowerCase();
    const delivery = String(raw.delivery || "").trim();
    const year = String(raw.year || inferYear(raw)).trim();
    const folderId = toFolderId(raw);

    if (!title || !href || !folderId) return null;
    if (type === "json") return null;
    if (!["pdf", "csv", "xlsx", "iframe", "link"].includes(type)) return null;
    if (isRuntimeDenied(raw) && !isExplicitAllow(raw)) return null;
    if (!passesFolderRules(folderId, { title, href, subtitle, year })) return null;

    const embedded = type === "iframe" || delivery === "embedded";
    return {
      id: `${folderId}::${title.toLowerCase()}::${href.toLowerCase()}::${type}`,
      folderId,
      title: title.includes("library_page_hunts")
        ? "2026 Hunt Units / Permit Numbers by Hunt Code and Hunt Name"
        : title,
      subtitle:
        subtitle ||
        (folderId === "units2026"
          ? "Current 2026 hunt code, hunt name, hunt unit, and permit table."
          : "Public hunt-library source file."),
      href,
      type,
      year,
      group,
      delivery,
      embedded,
      searchText: `${title} ${subtitle} ${href} ${year} ${type} ${group} ${folderId} ${raw.source || ""} ${raw.scope || ""}`.toLowerCase(),
    };
  }

  async function fetchManifest(url) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) return [];
      const text = await response.text();
      const parsed = JSON.parse(String(text || "").replace(/^\uFEFF/, ""));
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function dedupe(items) {
    const seen = new Map();
    items.forEach((item) => {
      if (!seen.has(item.id)) seen.set(item.id, item);
    });
    return Array.from(seen.values());
  }

  function renderFolderButtons(items, state, onFolderClick) {
    const wall = byId("uogaFolderWall");
    wall.innerHTML = FOLDERS.map((folder) => {
      const count = items.filter((item) => item.folderId === folder.id).length;
      const active = state.activeFolder === folder.id ? "active" : "";
      return `
        <button class="public-folder ${active}" type="button" data-folder="${esc(folder.id)}">
          <h3>${esc(folder.title)}</h3>
          <p>${esc(folder.description)}</p>
          <span class="count">${count} files</span>
        </button>
      `;
    }).join("");

    wall.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => onFolderClick(button.dataset.folder || ""));
    });
  }

  function filterItems(items, state) {
    const query = state.query.trim().toLowerCase();
    return items.filter((item) => {
      if (state.activeFolder && item.folderId !== state.activeFolder) return false;
      if (!query) return true;
      const folderTitle = (FOLDERS.find((f) => f.id === item.folderId) || {}).title || "";
      return `${item.searchText} ${folderTitle}`.toLowerCase().includes(query);
    });
  }

  function shouldShowResults(state) {
    return Boolean(state.activeFolder) || state.query.trim().length > 0;
  }

  function closeEmbed() {
    const panel = byId("uogaEmbedPanel");
    const frame = byId("uogaEmbedFrame");
    panel.hidden = true;
    frame.src = "about:blank";
  }

  function openEmbed(item) {
    const panel = byId("uogaEmbedPanel");
    const frame = byId("uogaEmbedFrame");
    const title = byId("uogaEmbedTitle");
    title.textContent = item.title || "Embedded Resource";
    frame.src = item.href;
    panel.hidden = false;
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function bindEmbedClose() {
    const close = byId("uogaEmbedClose");
    close.addEventListener("click", closeEmbed);
  }

  function renderResults(items, state) {
    const panel = byId("uogaResultsPanel");
    const panelTitle = byId("uogaResultsTitle");
    const panelCount = byId("uogaLibraryCount");
    const chips = byId("uogaActiveFilters");
    const grid = byId("uogaLibrarySections");

    if (!shouldShowResults(state)) {
      panel.hidden = true;
      panel.setAttribute("aria-hidden", "true");
      chips.innerHTML = "";
      grid.innerHTML = "";
      panelCount.textContent = "0 files";
      closeEmbed();
      return;
    }

    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");

    panelTitle.textContent = state.activeFolder
      ? (FOLDERS.find((f) => f.id === state.activeFolder) || {}).title || "Filtered Results"
      : "Search Results";

    const filtered = filterItems(items, state)
      .sort((a, b) => (b.year || "").localeCompare(a.year || "") || a.title.localeCompare(b.title));

    panelCount.textContent = `${filtered.length} files`;

    const chipsList = [];
    if (state.activeFolder) {
      chipsList.push(`<span class="public-chip">Folder: ${esc((FOLDERS.find((f) => f.id === state.activeFolder) || {}).title || "")}</span>`);
    }
    if (state.query.trim()) {
      chipsList.push(`<span class="public-chip">Search: ${esc(state.query.trim())}</span>`);
    }
    chips.innerHTML = chipsList.join("");

    if (!filtered.length) {
      grid.innerHTML = `<div class="public-empty">No public files match this folder/search.</div>`;
      closeEmbed();
      return;
    }

    grid.innerHTML = filtered.map((item, idx) => {
      const delivery = item.delivery ? ` | ${item.delivery}` : "";
      const meta = `${item.type.toUpperCase()}${item.year ? ` | ${item.year}` : ""}${delivery}`;
      if (item.embedded) {
        return `
          <button class="public-file-card public-file-card--button" type="button" data-embed-index="${idx}">
            <strong>${esc(item.title)}</strong>
            <span>${esc(item.subtitle)}</span>
            <em>${esc(meta)}</em>
          </button>
        `;
      }
      const href = safeUrl(item.href);
      return `
        <a class="public-file-card" href="${esc(href)}" target="_blank" rel="noopener noreferrer">
          <strong>${esc(item.title)}</strong>
          <span>${esc(item.subtitle)}</span>
          <em>${esc(meta)}</em>
        </a>
      `;
    }).join("");

    grid.querySelectorAll("[data-embed-index]").forEach((button) => {
      button.addEventListener("click", () => {
        const idx = Number(button.getAttribute("data-embed-index"));
        if (Number.isFinite(idx) && filtered[idx]) openEmbed(filtered[idx]);
      });
    });
  }

  function start(items) {
    const state = { activeFolder: "", query: "" };
    const search = byId("uogaLibrarySearch");
    const clear = byId("uogaLibraryClear");
    bindEmbedClose();

    const renderAll = () => {
      renderFolderButtons(items, state, (folderId) => {
        state.activeFolder = state.activeFolder === folderId ? "" : folderId;
        renderAll();
      });
      renderResults(items, state);
    };

    search.addEventListener("input", () => {
      state.query = search.value || "";
      renderAll();
    });

    clear.addEventListener("click", () => {
      state.query = "";
      state.activeFolder = "";
      search.value = "";
      renderAll();
    });

    renderAll();
  }

  Promise.all(MANIFEST_URLS.map(fetchManifest))
    .then((allSets) => allSets.flat().map(toPublicItem).filter(Boolean))
    .then((items) => dedupe([...items, ...FIXED_PUBLIC_ITEMS]))
    .then(start)
    .catch((error) => {
      const panel = byId("uogaResultsPanel");
      const grid = byId("uogaLibrarySections");
      panel.hidden = false;
      panel.setAttribute("aria-hidden", "false");
      grid.innerHTML = `<div class="public-empty">Could not load public library manifests: ${esc(error.message)}</div>`;
    });
})();
