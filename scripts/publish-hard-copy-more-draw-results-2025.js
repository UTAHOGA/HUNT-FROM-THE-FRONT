const fs = require('fs');
const path = require('path');

const repo = process.cwd();
const manifestPath = path.join(repo, 'processed_data', 'hard_data_exports', 'hard_copy_pdf_manifest.web.json');
const outputDir = path.join(repo, 'processed_data', 'hard_data_exports', 'source_pdfs', 'draw_odds', '2025');

const pdfs = [
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Black Bear Draw odds.pdf'),
    fileName: '2025-black-bear-draw-odds.pdf',
    title: '2025 Black Bear Draw Odds',
    subtitle: 'Official Utah DWR black bear draw odds/results source PDF used for the 2026 model-year data library.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Buck Deer General Season.pdf'),
    fileName: '2025-buck-deer-general-season-draw-results.pdf',
    title: '2025 Buck Deer General Season Draw Results',
    subtitle: 'Official Utah DWR general-season buck deer draw-results source PDF used for preference-point draw review.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Dedicated Hunter Draw Results.pdf'),
    fileName: '2025-dedicated-hunter-draw-results.pdf',
    title: '2025 Dedicated Hunter Draw Results',
    subtitle: 'Official Utah DWR Dedicated Hunter draw-results source PDF.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Turkey Draw Results.pdf'),
    fileName: '2025-turkey-draw-results.pdf',
    title: '2025 Turkey Draw Results',
    subtitle: 'Official Utah DWR turkey draw-results source PDF.'
  }
];

fs.mkdirSync(outputDir, { recursive: true });
const copied = [];
for (const item of pdfs) {
  if (!fs.existsSync(item.source)) throw new Error(`Missing source PDF: ${item.source}`);
  const dest = path.join(outputDir, item.fileName);
  fs.copyFileSync(item.source, dest);
  copied.push({ title: item.title, dest, bytes: fs.statSync(dest).size });
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const normalizedTitles = new Set(pdfs.map((item) => item.title.toLowerCase()));
const normalizedHrefs = new Set(pdfs.map((item) => `./processed_data/hard_data_exports/source_pdfs/draw_odds/2025/${item.fileName}`));
const filtered = manifest.filter((entry) => {
  const title = String(entry.title || '').trim().toLowerCase();
  const href = String(entry.href || '');
  return !normalizedTitles.has(title) && !normalizedHrefs.has(href);
});

const entries = pdfs.map((item) => ({
  group: 'draw_odds',
  type: 'pdf',
  year: '2025',
  title: item.title,
  subtitle: item.subtitle,
  href: `./processed_data/hard_data_exports/source_pdfs/draw_odds/2025/${item.fileName}`,
  source_authority: 'Utah Division of Wildlife Resources',
  source_year: '2025',
  model_year_folder: '2026',
  source_role: 'official_source',
  parent_title: null
}));

const next = [...entries, ...filtered];
fs.writeFileSync(manifestPath, JSON.stringify(next, null, 2) + '\n');
console.log(JSON.stringify({ copied, manifest_entries_added: entries.length, manifest_total: next.length }, null, 2));
