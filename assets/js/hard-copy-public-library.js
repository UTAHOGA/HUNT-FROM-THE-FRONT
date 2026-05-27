(() => {
  const CURRENT_YEAR = '2026';
  const MANIFESTS = [
    './processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json',
    './processed_data/hard_data_exports/hard_data_manifest.web.json'
  ];
  const FOLDERS = [
    ['UTAH DWR RULES & REGULATIONS', 'Current-year proclamations, guidebooks, field rules, and application materials.'],
    ['HARVEST DATA', 'Public harvest reports and harvest evidence by year.'],
    ['DRAW RESULTS', 'Public draw odds and draw result files by year.'],
    ['CONSERVATION PERMITS', 'Current-cycle conservation permit documents and permit numbers.'],
    ['HUNT EXPO', 'Current-year Hunt Expo permit numbers only.'],
    ['SIGNIFICANT DATES / CALENDAR', 'Application windows, season dates, deadlines, and calendar references.'],
    ['2026 HUNT UNITS / PERMIT NUMBERS', 'Current hunt codes, hunt names, units, and posted or allotted permit numbers.'],
    ['UTAH OUTFITTERS BY HUNT CODE/HUNT NAME', 'Outfitter resources tied back to hunt code and hunt name.']
  ];
  const byId = id => document.getElementById(id);
  const esc = value => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
  function safeUrl(value) {
    try {
      const url = new URL(String(value), window.location.origin);
      return ['http:', 'https:', 'mailto:', 'tel:'].includes(url.protocol) ? url.href : '#';
    } catch { return '#'; }
  }
  function inferYear(item) {
    const text = `${item.title || ''} ${item.subtitle || ''} ${item.href || ''}`;
    const match = text.match(/\b(20\d{2})\b/);
    return match ? match[1] : '';
  }
  function titleKey(title) {
    return String(title || '').toLowerCase()
      .replace(/\((csv|json|xlsx|pdf)\)/gi, '')
      .replace(/\s+/g, ' ')
      .trim();
  }
  function currentCycle(text) {
    return /2026/.test(text) || /2025[-_ ]?27/.test(text) || /2025[-_ ]?2027/.test(text);
  }
  function folderFor(item) {
    const h = [item.group, item.title, item.subtitle, item.href, item.source, item.scope, item.type].join(' ').toLowerCase();
    if (h.includes('outfitter')) return 'UTAH OUTFITTERS BY HUNT CODE/HUNT NAME';
    if (h.includes('expo')) return 'HUNT EXPO';
    if (h.includes('conservation')) return 'CONSERVATION PERMITS';
    if (h.includes('harvest')) return 'HARVEST DATA';
    if (h.includes('draw') || h.includes('odds') || h.includes('results')) return 'DRAW RESULTS';
    if (h.includes('date') || h.includes('calendar') || h.includes('deadline') || h.includes('season')) return 'SIGNIFICANT DATES / CALENDAR';
    if (h.includes('unit') || h.includes('map') || h.includes('permit') || h.includes('allotment') || h.includes('hunt_table') || h.includes('hunt table')) return '2026 HUNT UNITS / PERMIT NUMBERS';
    if (h.includes('regulation') || h.includes('guidebook') || h.includes('application') || h.includes('rules') || h.includes('proclamation')) return 'UTAH DWR RULES & REGULATIONS';
    return '2026 HUNT UNITS / PERMIT NUMBERS';
  }
  function isPrivateRuntime(item) {
    const h = [item.title, item.subtitle, item.href, item.group].join(' ').toLowerCase();
    return [
      'draw_reality_engine', 'ml_draw_predictions', 'point_ladder_view', 'hunt_master_enriched',
      'draw_system_coverage_report', 'predictive_coverage_report', 'hard_data_manifest',
      'library_page_data', 'library_page_summary', 'hunt_database_complete', 'crosswalk',
      'harvest_quality_features'
    ].some(token => h.includes(token));
  }
  function publicTitle(item) {
    const h = `${item.title || ''} ${item.href || ''}`.toLowerCase();
    if (h.includes('library_page_hunts')) return '2026 Hunt Units / Permit Numbers by Hunt Code and Hunt Name';
    return item.title || 'Untitled File';
  }
  function publicRole(item) {
    const h = `${item.title || ''} ${item.href || ''} ${item.subtitle || ''}`.toLowerCase();
    if (h.includes('library_page_hunts')) return 'Current-year hunt code, hunt name, unit, and posted or allotted permit number table.';
    if (h.includes('expo')) return 'Current-year Hunt Expo permit number reference.';
    return item.subtitle || '';
  }
  function isPublicItem(item) {
    const h = [item.group, item.title, item.subtitle, item.href, item.source, item.scope, item.type].join(' ').toLowerCase();
    const folder = folderFor(item);
    const year = item.year || inferYear(item);
    if (item.type === 'json') return false;
    if (h.includes('library_page_hunts')) return true;
    if (isPrivateRuntime(item)) return false;
    if (folder === 'UTAH DWR RULES & REGULATIONS') return year === CURRENT_YEAR || currentCycle(h);
    if (folder === 'CONSERVATION PERMITS') return currentCycle(h);
    if (folder === 'HUNT EXPO') return currentCycle(h) && (h.includes('permit') || h.includes('tag'));
    if (folder === '2026 HUNT UNITS / PERMIT NUMBERS') return currentCycle(h) && (h.includes('permit') || h.includes('unit') || h.includes('hunt table') || h.includes('hunt_table'));
    return true;
  }
  function normalize(items) {
    const map = new Map();
    items.forEach(raw => {
      const type = String(raw.type || 'file').toLowerCase().trim();
      const year = raw.year || inferYear(raw);
      const folder = folderFor(raw);
      const item = { ...raw, type, year, folder, titleKey: titleKey(raw.title), publicTitle: publicTitle(raw), publicRole: publicRole(raw) };
      if (!isPublicItem(item)) return;
      const key = `${folder}::${year}::${item.titleKey}::${type}::${item.href || ''}`;
      if (!map.has(key)) map.set(key, item);
    });
    const rows = [...map.values()];
    const hasXlsx = new Set(rows.filter(i => i.type === 'xlsx').map(i => `${i.folder}::${i.year}::${i.titleKey}`));
    return rows.filter(i => {
      if (i.type !== 'csv') return true;
      const key = `${i.folder}::${i.year}::${i.titleKey}`;
      if (hasXlsx.has(key)) return false;
      if (String(i.companion_type || '').toLowerCase() === 'xlsx') return false;
      if (String(i.companion_href || '').toLowerCase().endsWith('.xlsx')) return false;
      return true;
    });
  }
  function folderRank(name) {
    const index = FOLDERS.findIndex(([folder]) => folder === name);
    return index < 0 ? 999 : index;
  }
  function typeRank(type) {
    const order = ['pdf', 'xlsx', 'csv', 'json', 'sqlite'];
    const index = order.indexOf(String(type || '').toLowerCase());
    return index < 0 ? 999 : index;
  }
  async function loadManifest(url) {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  }
  function render(items) {
    const rows = normalize(items);
    const state = { folder: 'all', type: 'all', year: 'all' };
    const search = byId('uogaLibrarySearch');
    const wall = byId('uogaFolderWall');
    const typeSelect = byId('uogaLibraryType');
    const yearSelect = byId('uogaLibraryYear');
    const sections = byId('uogaLibrarySections');
    const count = byId('uogaLibraryCount');
    const chips = byId('uogaActiveFilters');
    const clear = byId('uogaLibraryClear');
    const types = ['all', ...new Set(rows.map(i => i.type))].sort((a, b) => typeRank(a) - typeRank(b) || a.localeCompare(b));
    const years = ['all', ...new Set(rows.map(i => i.year).filter(Boolean))].sort((a, b) => Number(b) - Number(a));
    typeSelect.innerHTML = types.map(t => `<option value="${esc(t)}">${esc(t === 'all' ? 'All file types' : t.toUpperCase())}</option>`).join('');
    yearSelect.innerHTML = years.map(y => `<option value="${esc(y)}">${esc(y === 'all' ? 'All years' : y)}</option>`).join('');
    function folderCount(folder) { return rows.filter(i => i.folder === folder).length; }
    function selectFolder(folder, scroll) {
      state.folder = folder || 'all';
      drawFolders();
      draw();
      if (scroll) sections.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    function drawFolders() {
      wall.innerHTML = FOLDERS.map(([folder, note]) => `
        <button class="uoga-folder ${state.folder === folder ? 'active' : ''}" type="button" data-folder="${esc(folder)}">
          <strong>${esc(folder)}</strong>
          <span class="count">${folderCount(folder)} files</span>
          <span class="note">${esc(note)}</span>
        </button>`).join('');
      wall.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', () => selectFolder(button.dataset.folder, true));
      });
    }
    function filtered() {
      const q = String(search.value || '').trim().toLowerCase();
      return rows.filter(item => {
        if (state.folder !== 'all' && item.folder !== state.folder) return false;
        if (state.type !== 'all' && item.type !== state.type) return false;
        if (state.year !== 'all' && item.year !== state.year) return false;
        if (!q) return true;
        const hay = [item.publicTitle, item.publicRole, item.type, item.folder, item.year, item.scope, item.source, item.delivery].join(' ').toLowerCase();
        return hay.includes(q);
      });
    }
    function drawActive() {
      const bits = [];
      if (state.folder !== 'all') bits.push(['folder', 'Folder', state.folder]);
      if (state.type !== 'all') bits.push(['type', 'Type', state.type.toUpperCase()]);
      if (state.year !== 'all') bits.push(['year', 'Year', state.year]);
      if (search.value.trim()) bits.push(['search', 'Search', search.value.trim()]);
      chips.innerHTML = bits.map(([key, label, value]) => `<button type="button" data-clear="${esc(key)}"><b>${esc(label)}:</b> ${esc(value)} x</button>`).join('');
      chips.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
        const key = button.dataset.clear;
        if (key === 'folder') state.folder = 'all';
        if (key === 'type') { state.type = 'all'; typeSelect.value = 'all'; }
        if (key === 'year') { state.year = 'all'; yearSelect.value = 'all'; }
        if (key === 'search') search.value = '';
        drawFolders();
        draw();
      }));
    }
    function card(item) {
      const href = safeUrl(item.href);
      const delivery = item.delivery ? ` | ${item.delivery}` : '';
      return `<a class="uoga-file-card" href="${esc(href)}" target="_blank" rel="noopener noreferrer">
        <span class="uoga-file-type">${esc((item.type || 'file').slice(0, 4))}</span>
        <span class="uoga-file-title">${esc(item.publicTitle || item.title || 'Untitled File')}</span>
        <span class="uoga-file-sub">${esc(item.publicRole || item.subtitle || '')}</span>
        <span class="uoga-file-meta">${esc((item.type || '').toUpperCase())}${item.year ? ` | ${esc(item.year)}` : ''}${esc(delivery)}</span>
      </a>`;
    }
    function draw() {
      const list = filtered();
      count.textContent = `${list.length} of ${rows.length} public files`;
      drawActive();
      if (!list.length) {
        sections.innerHTML = '<div class="uoga-empty">No public files match this filter.</div>';
        return;
      }
      const byFolder = new Map();
      list.forEach(item => {
        if (!byFolder.has(item.folder)) byFolder.set(item.folder, []);
        byFolder.get(item.folder).push(item);
      });
      sections.innerHTML = [...byFolder.keys()].sort((a, b) => folderRank(a) - folderRank(b) || a.localeCompare(b)).map(folder => {
        const folderRows = byFolder.get(folder);
        const byYear = new Map();
        folderRows.forEach(item => {
          const year = item.year || 'Unknown year';
          if (!byYear.has(year)) byYear.set(year, []);
          byYear.get(year).push(item);
        });
        const yearBlocks = [...byYear.keys()].sort((a, b) => a === 'Unknown year' ? 1 : b === 'Unknown year' ? -1 : Number(b) - Number(a)).map((year, index) => {
          const yearRows = byYear.get(year).sort((a, b) => typeRank(a.type) - typeRank(b.type) || String(a.publicTitle || a.title || '').localeCompare(String(b.publicTitle || b.title || '')));
          const primary = state.year === 'all' ? yearRows.slice(0, 12) : yearRows;
          const extra = state.year === 'all' ? yearRows.slice(12) : [];
          return `<details class="uoga-year" ${index < 2 || state.year !== 'all' ? 'open' : ''}>
            <summary><span>${esc(year)}</span><span>${yearRows.length} files</span></summary>
            <div class="uoga-cards">${primary.map(card).join('')}</div>
            ${extra.length ? `<details class="library-more-files"><summary>Show ${extra.length} more files</summary><div class="uoga-cards">${extra.map(card).join('')}</div></details>` : ''}
          </details>`;
        }).join('');
        return `<section class="uoga-section"><div class="uoga-section-head"><h3>${esc(folder)}</h3><span class="uoga-section-count">${folderRows.length} public files</span></div>${yearBlocks}</section>`;
      }).join('');
    }
    search.addEventListener('input', draw);
    typeSelect.addEventListener('change', () => { state.type = typeSelect.value || 'all'; draw(); });
    yearSelect.addEventListener('change', () => { state.year = yearSelect.value || 'all'; draw(); });
    clear.addEventListener('click', () => {
      state.folder = 'all'; state.type = 'all'; state.year = 'all'; search.value = '';
      typeSelect.value = 'all'; yearSelect.value = 'all'; drawFolders(); draw();
    });
    drawFolders();
    draw();
  }
  Promise.all(MANIFESTS.map(loadManifest))
    .then(sets => render(sets.flat()))
    .catch(error => { byId('uogaLibrarySections').innerHTML = `<div class="uoga-empty">Could not load manifest: ${esc(error.message)}</div>`; });
})();