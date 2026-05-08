const fs = require('fs');
const path = require('path');

const repo = process.cwd();
const manifestPath = path.join(repo, 'processed_data', 'hard_data_exports', 'hard_copy_pdf_manifest.web.json');
const outputDir = path.join(repo, 'processed_data', 'hard_data_exports', 'source_pdfs', 'draw_odds', '2025');

const pdfs = [
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Youth Dedicated Hunter Draw Results.pdf'),
    fileName: '2025-youth-dedicated-hunter-draw-results.pdf',
    title: '2025 Youth Dedicated Hunter Draw Results',
    subtitle: 'Official Utah DWR youth Dedicated Hunter draw-results source PDF.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Youth G.S.. Mature Bull Draw.pdf'),
    fileName: '2025-youth-general-season-mature-bull-draw-results.pdf',
    title: '2025 Youth G.S. Mature Bull Draw Results',
    subtitle: 'Official Utah DWR youth general-season mature bull elk draw-results source PDF.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Youth G.S. Deer Draw Results.pdf'),
    fileName: '2025-youth-general-season-deer-draw-results.pdf',
    title: '2025 Youth G.S. Deer Draw Results',
    subtitle: 'Official Utah DWR youth general-season deer draw-results source PDF.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Youth Antlerless Draw.pdf'),
    fileName: '2025-youth-antlerless-draw-results.pdf',
    title: '2025 Youth Antlerless Draw Results',
    subtitle: 'Official Utah DWR youth antlerless draw-results source PDF.'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Antlerless Draw Results.pdf'),
    fileName: '2025-antlerless-draw-results.pdf',
    title: '2025 Antlerless Draw Results',
    subtitle: 'Official Utah DWR antlerless draw-results source PDF.'
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
