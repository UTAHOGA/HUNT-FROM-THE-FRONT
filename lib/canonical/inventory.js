const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');

const PAGES = [
  { key: 'hunt-planner', label: 'Hunt Planner', html: 'index.html', path: './index.html', title: 'U.O.G.A. Builder' },
  { key: 'hunt-research', label: 'Hunt Research', html: 'research.html', path: './research.html', title: 'U.O.G.A. Hunt Research' },
  { key: 'hard-copies', label: 'Hard Copies', html: 'hard-copy.html', path: './hard-copy.html', title: 'U.O.G.A. Hard Data' },
  { key: 'outfitter-verification', label: 'Outfitter Verification', html: 'verify.html', path: './verify.html', title: 'Outfitter Verification' },
];

const SOURCE_FILES = [
  'index.html',
  'research.html',
  'hard-copy.html',
  'verify.html',
  'config.js',
  'app.js',
  'data.js',
  'boundary-resolver.js',
  'hunt-research.js',
  'ui.js',
  'header-layout.js',
  'google-basemap.js',
  'map-engine.js',
  'style.css',
  'data/hunt-master-canonical-2026-foundation.json',
  'data/hunt-master-canonical-2026-database-candidate.json',
  'data/hunt-master-canonical-2026-source-of-truth.json',
  'processed_data/draw_reality_engine.csv',
  'processed_data/point_ladder_view.csv',
  'processed_data/hunt_master_enriched.csv',
  'processed_data/hunt_unit_reference_linked.csv',
  'processed_data/display-boundary-index-2026.json',
  'processed_data/boundary-manifest-2026.json',
  'processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json',
  'data/outfitters-public.json',
  'data/outfitters.json',
  'processed_data/outfitter-federal-unit-coverage-review.json',
];

const CONSUMER_FILES = [
  'index.html',
  'research.html',
  'hard-copy.html',
  'verify.html',
  'config.js',
  'app.js',
  'data.js',
  'boundary-resolver.js',
  'hunt-research.js',
  'ui.js',
  'header-layout.js',
];

function abs(file = '') {
  return path.join(REPO, file);
}

function ensureDir(dir) {
  fs.mkdirSync(abs(dir), { recursive: true });
}

function readText(file) {
  const full = abs(file);
  return fs.existsSync(full) ? fs.readFileSync(full, 'utf8').replace(/^\uFEFF/, '') : '';
}

function readJson(file, fallback = null) {
  const text = readText(file);
  return text ? JSON.parse(text) : fallback;
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(abs(file)), { recursive: true });
  fs.writeFileSync(abs(file), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
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
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map(v => String(v || '').trim());
  const records = rows
    .filter(values => values.some(v => String(v || '').trim()))
    .map(values => Object.fromEntries(headers.map((header, index) => [header, values[index] || '']).filter(([header]) => header)));
  return { headers, records };
}

function readCsv(file) {
  const text = readText(file);
  return text ? parseCsv(text) : { headers: [], records: [] };
}

function arrayFromJson(value) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== 'object') return [];
  for (const key of ['hunts', 'records', 'items', 'outfitters', 'features']) {
    if (Array.isArray(value[key])) return value[key];
  }
  return [];
}

function rowsFor(file) {
  if (file.endsWith('.csv')) return readCsv(file).records;
  if (file.endsWith('.json')) return arrayFromJson(readJson(file, null));
  return [];
}

function fieldsForRows(rows) {
  const fields = new Set();
  rows.slice(0, 5000).forEach(row => {
    if (row && typeof row === 'object') Object.keys(row).forEach(key => fields.add(key));
  });
  return [...fields].sort();
}

function stripHtml(value) {
  return String(value || '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}

function slug(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'item';
}

function htmlContract(file) {
  const text = readText(file);
  const ids = [...text.matchAll(/id="([^"]+)"/g)].map(match => match[1]);
  const dataAttributes = [...text.matchAll(/\s(data-[a-zA-Z0-9_-]+)(?:=|\s|>)/g)].map(match => match[1]);
  const links = [...text.matchAll(/href="([^"]+)"/g)].map(match => match[1]);
  const title = (text.match(/<title>(.*?)<\/title>/i) || [null, ''])[1];
  const options = [...text.matchAll(/<option\s+value="([^"]*)"[^>]*>(.*?)<\/option>/g)].map(match => ({
    value: match[1],
    label: stripHtml(match[2]),
  }));
  return { title, ids: [...new Set(ids)], data_attributes: [...new Set(dataAttributes)], links: [...new Set(links)], options };
}

function verifyStandards() {
  const text = readText('verify.html');
  const standards = [];
  for (const match of text.matchAll(/<article[^>]*class="card[^>]*>[\s\S]*?<h4>([\s\S]*?)<\/h4>[\s\S]*?<h3>([\s\S]*?)<\/h3>[\s\S]*?<\/article>/g)) {
    const block = match[0];
    standards.push({
      id: slug(stripHtml(match[1])),
      kicker: stripHtml(match[1]),
      title: stripHtml(match[2]),
      bullets: [...block.matchAll(/<li>([\s\S]*?)<\/li>/g)].map(item => stripHtml(item[1])),
    });
  }
  return standards;
}

function sourceSummary(file) {
  if (file.endsWith('.csv')) {
    const parsed = readCsv(file);
    return { file, exists: true, kind: 'csv', row_count: parsed.records.length, fields: parsed.headers };
  }
  if (file.endsWith('.json')) {
    const rows = rowsFor(file);
    return { file, exists: true, kind: 'json', row_count: rows.length, fields: fieldsForRows(rows) };
  }
  const text = readText(file);
  return { file, exists: true, kind: path.extname(file).replace('.', '') || 'text', byte_count: Buffer.byteLength(text), fields: [] };
}

function consumersFor(field) {
  if (field.startsWith('#') || field.startsWith('data-')) return [];
  const consumers = [];
  for (const file of CONSUMER_FILES) {
    const text = readText(file);
    const escaped = field.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (new RegExp(`(^|[^A-Za-z0-9_])${escaped}([^A-Za-z0-9_]|$)`).test(text)) consumers.push(file);
  }
  return consumers;
}

function pageTools(file, consumers) {
  const tools = new Set();
  if (file.includes('hunt-master') || file.includes('boundary') || file.includes('conservation') || consumers.some(v => ['index.html', 'app.js', 'data.js', 'boundary-resolver.js'].includes(v))) tools.add('Hunt Planner');
  if (file.includes('draw_reality') || file.includes('point_ladder') || file.includes('hunt_master_enriched') || file.includes('hunt_unit_reference') || consumers.some(v => ['research.html', 'hunt-research.js'].includes(v))) tools.add('Hunt Research');
  if (file.includes('hard_copy') || consumers.includes('hard-copy.html')) tools.add('Hard Copies');
  if (file.includes('outfitter') || consumers.includes('verify.html')) tools.add('Outfitter Verification');
  return [...tools];
}

function sourceFiles() {
  return SOURCE_FILES.filter(file => fs.existsSync(abs(file)));
}

module.exports = {
  REPO,
  PAGES,
  abs,
  ensureDir,
  readText,
  readJson,
  writeJson,
  readCsv,
  rowsFor,
  fieldsForRows,
  htmlContract,
  verifyStandards,
  sourceSummary,
  consumersFor,
  pageTools,
  sourceFiles,
  stripHtml,
};
