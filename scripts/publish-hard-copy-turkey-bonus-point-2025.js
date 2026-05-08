const fs = require('fs');
const path = require('path');

const repo = process.cwd();
const source = path.join(repo, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'pdf', 'draw_odds', '2025 Turkey Bonus Point Purchase.pdf');
const fileName = '2025-turkey-bonus-point-purchase-results.pdf';
const outputDir = path.join(repo, 'processed_data', 'hard_data_exports', 'source_pdfs', 'draw_odds', '2025');
const dest = path.join(outputDir, fileName);
const manifestPath = path.join(repo, 'processed_data', 'hard_data_exports', 'hard_copy_pdf_manifest.web.json');

if (!fs.existsSync(source)) throw new Error(`Missing source PDF: ${source}`);
fs.mkdirSync(outputDir, { recursive: true });
fs.copyFileSync(source, dest);

const title = '2025 Turkey Bonus Point Purchase Results';
const href = `./processed_data/hard_data_exports/source_pdfs/draw_odds/2025/${fileName}`;
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const filtered = manifest.filter((entry) => String(entry.title || '').trim().toLowerCase() !== title.toLowerCase() && String(entry.href || '') !== href);
const entry = {
  group: 'draw_odds',
  type: 'pdf',
  year: '2025',
  title,
  subtitle: 'Official Utah DWR turkey bonus-point purchase source PDF used for the 2026 model-year data library.',
  href,
  source_authority: 'Utah Division of Wildlife Resources',
  source_year: '2025',
  model_year_folder: '2026',
  source_role: 'official_source',
  parent_title: null
};
const next = [entry, ...filtered];
fs.writeFileSync(manifestPath, JSON.stringify(next, null, 2) + '\n');
console.log(JSON.stringify({ copied: { title, dest, bytes: fs.statSync(dest).size }, manifest_total: next.length }, null, 2));
