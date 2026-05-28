(() => {
  const CURRENT_YEAR = "2026";
  const MANIFEST_URLS = [
    "./processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json",
    "./processed_data/hard_data_exports/hard_data_manifest.web.json",
    "./processed_data/hard_data_exports/library/public_library_manual_items.json",
  ];

  const PDFJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs";
  const PDFJS_WORKER_CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs";
  const PAGE_FLIP_CDN = "https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.min.js";

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

  let pdfjsLib = null;
  let pageFlipLoadPromise = null;
  let pdfLibLoadPromise = null;
  let pageFlipInstance = null;
  let activeSpreadMeta = [];
  let activePdfPageCount = 0;
  let activePdfSpreads = [];
  let activeSpreadIndex = 0;

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
    const hasWord = (term) => new RegExp(`\\b${term}\\b`, "i").test(hay);
    if (hay.includes("outfitter")) return "outfitters";
    if (hay.includes("calendar") || hay.includes("deadline") || hay.includes("season date") || hay.includes("application date")) return "calendar";
    if (hasWord("expo")) return "expo";
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
    if (folderId === "conservation") {
      const hasConservationPermit = /conservation[\s-]*permit/.test(hay);
      const isExpo = /\bexpo\b/.test(hay);
      const isDraw = /\bdraw\b|\bdraw result/.test(hay);
      return currentCycle(`${hay} ${year}`) && hasConservationPermit && !isExpo && !isDraw;
    }
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
    const viewerHref = String(raw.viewer_href || "").trim();
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
      viewerHref,
      searchText: `${title} ${subtitle} ${href} ${year} ${type} ${group} ${folderId} ${raw.source || ""} ${raw.scope || ""} ${viewerHref}`.toLowerCase(),
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

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      document.head.appendChild(script);
    });
  }

  async function ensurePageFlipLibrary() {
    if (!pageFlipLoadPromise) {
      pageFlipLoadPromise = loadScript(PAGE_FLIP_CDN);
    }
    await pageFlipLoadPromise;
  }

  function enforceConservationSingleItem(items) {
    const conservation = items.filter((item) => item.folderId === "conservation");
    if (conservation.length <= 1) return items;

    const scoreItem = (item) => {
      const hay = `${item.title || ""} ${item.subtitle || ""} ${item.href || ""}`.toLowerCase();
      let score = 0;
      if (String(item.delivery || "").toLowerCase() === "pages-local") score += 200;
      if (item.type === "pdf") score += 120;
      if (/2026|2025[-/]27|2025[-/]2027/.test(`${item.year || ""} ${hay}`)) score += 90;
      if (/public\/hard-copy|manual|web/.test(hay)) score += 40;
      if (/\bexpo\b|\bdraw\b/.test(hay)) score -= 300;
      if (item.type === "csv" || item.type === "xlsx") score -= 50;
      return score;
    };

    const best = [...conservation].sort((a, b) => scoreItem(b) - scoreItem(a))[0];
    return items.filter((item) => item.folderId !== "conservation").concat(best);
  }

  async function ensurePdfLibrary() {
    if (!pdfLibLoadPromise) {
      pdfLibLoadPromise = import(PDFJS_CDN).then((module) => {
        pdfjsLib = module;
        pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_CDN;
      });
    }
    await pdfLibLoadPromise;
  }

  function closeEmbed() {
    const panel = byId("uogaEmbedPanel");
    const frame = byId("uogaEmbedFrame");
    panel.hidden = true;
    frame.src = "about:blank";
  }

  function openEmbed(item) {
    closePdfFlipbook();
    const panel = byId("uogaEmbedPanel");
    const frame = byId("uogaEmbedFrame");
    const title = byId("uogaEmbedTitle");
    title.textContent = item.title || "Embedded Resource";
    frame.src = item.href;
    panel.hidden = false;
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function closePdfFlipbook() {
    const panel = byId("uogaPdfFlipPanel");
    const book = byId("uogaPdfFlipbook");
    const status = byId("uogaPdfStatus");
    const download = byId("uogaPdfDownload");
    if (pageFlipInstance) {
      pageFlipInstance.destroy();
      pageFlipInstance = null;
    }
    activeSpreadMeta = [];
    activePdfPageCount = 0;
    activePdfSpreads = [];
    activeSpreadIndex = 0;
    book.innerHTML = "";
    panel.hidden = true;
    document.body.classList.remove("uoga-modal-open");
    status.textContent = "Loading...";
    download.href = "#";
  }

  async function renderPdfPages(pdfDoc, targetWidth = 430) {
    const pageCount = Math.min(pdfDoc.numPages, 60);
    const pages = [];
    for (let i = 1; i <= pageCount; i += 1) {
      const page = await pdfDoc.getPage(i);
      const initialViewport = page.getViewport({ scale: 1 });
      const scale = targetWidth / initialViewport.width;
      const viewport = page.getViewport({ scale });
      const canvas = document.createElement("canvas");
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      const ctx = canvas.getContext("2d", { alpha: false });
      await page.render({ canvasContext: ctx, viewport }).promise;

      const pageWrap = document.createElement("div");
      pageWrap.className = "uoga-pdf-page";
      pageWrap.dataset.pageNumber = String(i);
      pageWrap.appendChild(canvas);
      pages.push(pageWrap);
    }
    return { pages, pageCount };
  }

  function buildSpreads(pages, pageCount, isMobile) {
    if (isMobile) {
      const spreads = pages.map((page, index) => {
        const spread = document.createElement("div");
        spread.className = "uoga-pdf-spread single";
        spread.appendChild(page);
        spread.dataset.spreadIndex = String(index);
        return spread;
      });
      const spreadMeta = pages.map((_, index) => ({ label: `Page ${index + 1} of ${pageCount}` }));
      return { spreads, spreadMeta };
    }

    const spreads = [];
    const spreadMeta = [];

    const coverSpread = document.createElement("div");
    coverSpread.className = "uoga-pdf-spread cover";
    coverSpread.dataset.spreadIndex = "0";
    coverSpread.appendChild(pages[0]);
    spreads.push(coverSpread);
    spreadMeta.push({ label: `Cover (Page 1 of ${pageCount})` });

    for (let pageNum = 2; pageNum <= pageCount; pageNum += 2) {
      const spread = document.createElement("div");
      const rightPageNum = pageNum + 1;
      const isSingle = rightPageNum > pageCount;
      spread.className = `uoga-pdf-spread ${isSingle ? "single" : ""}`.trim();
      spread.dataset.spreadIndex = String(spreads.length);
      spread.appendChild(pages[pageNum - 1]);
      if (!isSingle) spread.appendChild(pages[rightPageNum - 1]);
      spreads.push(spread);
      spreadMeta.push({
        label: isSingle
          ? `Page ${pageNum} of ${pageCount}`
          : `Pages ${pageNum}-${rightPageNum} of ${pageCount}`,
      });
    }

    return { spreads, spreadMeta };
  }

  function updateFlipStatus(spreadIndex) {
    const status = byId("uogaPdfStatus");
    if (pageFlipInstance) {
      const index = Math.max(0, Number(spreadIndex) || 0);
      if (activePdfPageCount <= 0) {
        status.textContent = "Loading...";
        return;
      }
      if (index === 0) {
        status.textContent = `Cover (Page 1 of ${activePdfPageCount})`;
        return;
      }
      const leftPage = index + 1;
      const rightPage = Math.min(leftPage + 1, activePdfPageCount);
      status.textContent = leftPage === rightPage
        ? `Page ${leftPage} of ${activePdfPageCount}`
        : `Pages ${leftPage}-${rightPage} of ${activePdfPageCount}`;
      return;
    }
    const meta = activeSpreadMeta[spreadIndex];
    if (!meta) {
      status.textContent = activePdfPageCount ? `Page 1 of ${activePdfPageCount}` : "Loading...";
      return;
    }
    status.textContent = meta.label;
  }

  function showPdfSpread(index) {
    const book = byId("uogaPdfFlipbook");
    if (!activePdfSpreads.length) {
      book.innerHTML = "";
      return;
    }
    activeSpreadIndex = Math.max(0, Math.min(index, activePdfSpreads.length - 1));
    book.innerHTML = "";
    book.appendChild(activePdfSpreads[activeSpreadIndex]);
    updateFlipStatus(activeSpreadIndex);
  }

  async function openPdfFlipbook(item) {
    closeEmbed();
    const panel = byId("uogaPdfFlipPanel");
    const title = byId("uogaPdfFlipTitle");
    const status = byId("uogaPdfStatus");
    const book = byId("uogaPdfFlipbook");
    const download = byId("uogaPdfDownload");
    const viewerHref = item.viewerHref || item.href;

    panel.hidden = false;
    document.body.classList.add("uoga-modal-open");
    title.textContent = item.title || "PDF Viewer";
    download.href = safeUrl(viewerHref);
    status.textContent = "Loading PDF...";
    book.innerHTML = "";

    try {
      await ensurePdfLibrary();
      await ensurePageFlipLibrary();
      const pdf = await pdfjsLib.getDocument(safeUrl(viewerHref)).promise;
      const isMobile = window.innerWidth <= 760;
      const targetWidth = isMobile ? 320 : 640;
      const { pages, pageCount } = await renderPdfPages(pdf, targetWidth);
      if (!pages.length) {
        status.textContent = "No renderable pages.";
        return;
      }

      activePdfPageCount = pageCount;

      try {
        pageFlipInstance = new window.St.PageFlip(book, {
          width: 620,
          height: 800,
          size: "stretch",
          minWidth: 360,
          maxWidth: 700,
          minHeight: 520,
          maxHeight: 900,
          showCover: true,
          usePortrait: isMobile,
          drawShadow: true,
          flippingTime: 700,
          mobileScrollSupport: false,
        });
        pages.forEach((page) => book.appendChild(page));
        pageFlipInstance.loadFromHTML(book.querySelectorAll(".uoga-pdf-page"));
        updateFlipStatus(0);
        pageFlipInstance.on("flip", (event) => {
          updateFlipStatus(Number(event.data || 0));
        });
      } catch (flipError) {
        if (pageFlipInstance) {
          pageFlipInstance.destroy();
          pageFlipInstance = null;
        }
        const { spreads, spreadMeta } = buildSpreads(pages, pageCount, isMobile);
        activeSpreadMeta = spreadMeta;
        activePdfSpreads = spreads;
        showPdfSpread(0);
      }
    } catch (error) {
      document.body.classList.remove("uoga-modal-open");
      status.textContent = "Could not load flipbook. Use Download PDF.";
      book.innerHTML = `<div class="public-empty">${esc(error.message || "Flipbook failed to load")}</div>`;
    }
  }

  function bindStaticControls() {
    byId("uogaEmbedClose").addEventListener("click", closeEmbed);
    byId("uogaPdfFlipClose").addEventListener("click", closePdfFlipbook);
    byId("uogaPdfFlipPanel").querySelector(".uoga-pdf-flip-backdrop")?.addEventListener("click", closePdfFlipbook);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closePdfFlipbook();
    });
    byId("uogaPdfPrev").addEventListener("click", () => {
      if (pageFlipInstance) {
        pageFlipInstance.flipPrev();
      } else {
        showPdfSpread(activeSpreadIndex - 1);
      }
    });
    byId("uogaPdfNext").addEventListener("click", () => {
      if (pageFlipInstance) {
        pageFlipInstance.flipNext();
      } else {
        showPdfSpread(activeSpreadIndex + 1);
      }
    });
  }

  function renderFolderButtons(items, state, onFolderClick) {
    const wall = byId("uogaFolderWall");
    wall.innerHTML = FOLDERS.map((folder) => {
      const count = items.filter((item) => item.folderId === folder.id).length;
      const active = state.activeFolder === folder.id ? "active" : "";
      const label = `${folder.title} (${count} files)`;
      return `
        <button class="public-folder ${active}" type="button" data-folder="${esc(folder.id)}" aria-label="${esc(label)}">
          <span class="public-folder-title">${esc(folder.title)}</span>
          <span class="public-folder-description">${esc(folder.description)}</span>
          <span class="public-folder-count">${count} file${count === 1 ? "" : "s"}</span>
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
      closePdfFlipbook();
      return;
    }

    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    panelTitle.textContent = state.activeFolder
      ? (FOLDERS.find((f) => f.id === state.activeFolder) || {}).title || "Filtered Results"
      : "Search Results";

    const filtered = filterItems(items, state).sort((a, b) => (b.year || "").localeCompare(a.year || "") || a.title.localeCompare(b.title));
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
      closePdfFlipbook();
      return;
    }

    grid.innerHTML = filtered.map((item, idx) => {
      const delivery = item.delivery ? ` | ${item.delivery}` : "";
      const meta = `${item.type.toUpperCase()}${item.year ? ` | ${item.year}` : ""}${delivery}`;
      const base = `
        <strong>${esc(item.title)}</strong>
        <span>${esc(item.subtitle)}</span>
        <em>${esc(meta)}</em>
      `;

      if (item.type === "pdf") {
        const originalHref = safeUrl(item.href);
        const viewerHref = item.viewerHref ? safeUrl(item.viewerHref) : "";
        const viewerDownload = viewerHref
          ? `<a class="public-file-action" href="${esc(viewerHref)}" target="_blank" rel="noopener noreferrer">Download Viewer PDF</a>`
          : "";
        return `
          <div class="public-file-card">
            ${base}
            <div class="public-file-actions">
              <button class="public-file-action" type="button" data-action="flip" data-index="${idx}">View Flipbook</button>
              <a class="public-file-action" href="${esc(originalHref)}" target="_blank" rel="noopener noreferrer">Download Original</a>
              ${viewerDownload}
            </div>
          </div>
        `;
      }

      if (item.embedded) {
        return `
          <div class="public-file-card">
            ${base}
            <div class="public-file-actions">
              <button class="public-file-action" type="button" data-action="embed" data-index="${idx}">View Calendar</button>
            </div>
          </div>
        `;
      }

      const href = safeUrl(item.href);
      return `
        <div class="public-file-card">
          ${base}
          <div class="public-file-actions">
            <a class="public-file-action" href="${esc(href)}" target="_blank" rel="noopener noreferrer">Open File</a>
          </div>
        </div>
      `;
    }).join("");

    grid.querySelectorAll("[data-action='flip']").forEach((button) => {
      button.addEventListener("click", () => {
        const idx = Number(button.getAttribute("data-index"));
        if (Number.isFinite(idx) && filtered[idx]) openPdfFlipbook(filtered[idx]);
      });
    });

    grid.querySelectorAll("[data-action='embed']").forEach((button) => {
      button.addEventListener("click", () => {
        const idx = Number(button.getAttribute("data-index"));
        if (Number.isFinite(idx) && filtered[idx]) openEmbed(filtered[idx]);
      });
    });

  }

  function start(items) {
    const state = { activeFolder: "", query: "" };
    const search = byId("uogaLibrarySearch");
    const clear = byId("uogaLibraryClear");
    bindStaticControls();

    const renderAll = () => {
      renderFolderButtons(items, state, (folderId) => {
        state.activeFolder = state.activeFolder === folderId ? "" : folderId;
        renderAll();
      });
      renderResults(items, state);
    };

    if (search) {
      search.addEventListener("input", () => {
        state.query = search.value || "";
        renderAll();
      });
    }

    if (clear) {
      clear.addEventListener("click", () => {
        state.query = "";
        state.activeFolder = "";
        if (search) search.value = "";
        renderAll();
      });
    }

    renderAll();
  }

  Promise.all(MANIFEST_URLS.map(fetchManifest))
    .then((allSets) => allSets.flat().map(toPublicItem).filter(Boolean))
    .then((items) => dedupe([...items, ...FIXED_PUBLIC_ITEMS]))
    .then((items) => enforceConservationSingleItem(items))
    .then(start)
    .catch((error) => {
      const panel = byId("uogaResultsPanel");
      const grid = byId("uogaLibrarySections");
      panel.hidden = false;
      panel.setAttribute("aria-hidden", "false");
      grid.innerHTML = `<div class="public-empty">Could not load public library manifests: ${esc(error.message)}</div>`;
    });
})();
