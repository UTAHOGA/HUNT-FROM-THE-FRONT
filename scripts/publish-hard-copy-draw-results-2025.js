const fs = require('fs');
const path = require('path');

const repo = process.cwd();
const manifestPath = path.join(repo, 'processed_data', 'hard_data_exports', 'hard_copy_pdf_manifest.web.json');
const outputDir = path.join(repo, 'processed_data', 'hard_data_exports', 'source_pdfs', 'draw_odds', '2025');

const pdfs = [
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Big Game Draw Results.pdf'),
    fileName: '2025-big-game-draw-results.pdf',
    title: '2025 Big Game Draw Results',
    subtitle: 'Official Utah DWR parent source PDF for 2025 big-game limited-entry draw results. Sub-files below are split from this source for easier review.',
    source_role: 'parent_source'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 LE Deer Draw Results.pdf'),
    fileName: '2025-le-deer-draw-results.pdf',
    title: '2025 LE Deer Draw Results',
    subtitle: 'Official Utah DWR limited-entry deer draw-results sub-file derived from the 2025 Big Game Draw Results source.',
    source_role: 'derived_subfile',
    parent_title: '2025 Big Game Draw Results'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 LE Elk Draw Results.pdf'),
    fileName: '2025-le-elk-draw-results.pdf',
    title: '2025 LE Elk Draw Results',
    subtitle: 'Official Utah DWR limited-entry elk draw-results sub-file derived from the 2025 Big Game Draw Results source.',
    source_role: 'derived_subfile',
    parent_title: '2025 Big Game Draw Results'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 LE Pronghorn Draw Results.pdf'),
    fileName: '2025-le-pronghorn-draw-results.pdf',
    title: '2025 LE Pronghorn Draw Results',
    subtitle: 'Official Utah DWR limited-entry pronghorn draw-results sub-file derived from the 2025 Big Game Draw Results source.',
    source_role: 'derived_subfile',
    parent_title: '2025 Big Game Draw Results'
  },
  {
    source: path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 O.I.L. Draw Results.pdf'),
    fileName: '2025-oil-draw-results.pdf',
    title: '2025 O.I.L. Draw Results',
    subtitle: 'Official Utah DWR once-in-a-lifetime draw-results sub-file derived from the 2025 Big Game Draw Results source.',
    source_role: 'derived_subfile',
    parent_title: '2025 Big Game Draw Results'
  }
];

fs.mkdirSync(outputDir, { recursive: true });
const copied = [];
for (const item of pdfs) {
  if (!fs.existsSync(item.source)) {
    throw new Error(`Missing source PDF: ${item.source}`);
  }
  const dest = path.join(outputDir, item.fileName);
  fs.copyFileSync(item.source, dest);
  copied.push({ title: item.title, dest, bytes: fs.statSync(dest).size });
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const removeHrefs = new Set(pdfs.flatMap((item) => [
  `./processed_data/hard_data_exports/source_pdfs/draw_odds/2025/${item.fileName}`,
  `./pipeline/RAW/hunt_unit_database/2026/pdf/draw_odds/${path.basename(item.source).replace(/ /g, '_')}`,
  `./pipeline/RAW/hunt_unit_database/2026/pdf/draw_odds/${path.basename(item.source)}`
]));
const filtered = manifest.filter((entry) => {
  const title = String(entry.title || '').trim().toLowerCase();
  const href = String(entry.href || '');
  if (removeHrefs.has(href)) return false;
  return !pdfs.some((item) => title === item.title.toLowerCase());
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
  source_role: item.source_role,
  parent_title: item.parent_title || null
}));

const next = [...entries, ...filtered];
fs.writeFileSync(manifestPath, JSON.stringify(next, null, 2) + '\n');
console.log(JSON.stringify({ copied, manifest_entries_added: entries.length, manifest_total: next.length }, null, 2));
