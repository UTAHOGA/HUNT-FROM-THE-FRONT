const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const SOURCE_DIR = 'pipeline/RAW/hunt_unit_database/2026/formatted_tables';
const DEST_DIR = 'processed_data/hard_data_exports/hunt_tables/2026';
const MANIFEST = 'processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json';
const YEAR = '2026';

function abs(file) {
  return path.join(REPO, file);
}

function titleFromFile(fileName) {
  return path.basename(fileName, path.extname(fileName))
    .replace(/_formatted$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function webHref(relativePath) {
  return `./${relativePath.replace(/\\/g, '/')}`;
}

function loadManifest() {
  if (!fs.existsSync(abs(MANIFEST))) return [];
  const parsed = JSON.parse(fs.readFileSync(abs(MANIFEST), 'utf8'));
  return Array.isArray(parsed) ? parsed : [];
}

function writeManifest(items) {
  fs.writeFileSync(abs(MANIFEST), `${JSON.stringify(items, null, 2)}\n`, 'utf8');
}

function main() {
  const sourceDir = abs(SOURCE_DIR);
  if (!fs.existsSync(sourceDir)) {
    throw new Error(`Missing formatted table source directory: ${SOURCE_DIR}`);
  }
  fs.mkdirSync(abs(DEST_DIR), { recursive: true });

  const sourceFiles = fs.readdirSync(sourceDir)
    .filter((name) => /\.(pdf|xlsx)$/i.test(name))
    .filter((name) => !/\.preview\./i.test(name))
    .sort();

  const copied = [];
  for (const name of sourceFiles) {
    const src = path.join(sourceDir, name);
    const destRelative = path.join(DEST_DIR, name);
    fs.copyFileSync(src, abs(destRelative));
    copied.push(destRelative);
  }

  const manifest = loadManifest();
  const byHref = new Map(manifest.map((item) => [item.href, item]));
  const addedOrUpdated = [];
  for (const destRelative of copied) {
    const ext = path.extname(destRelative).slice(1).toLowerCase();
    const href = webHref(destRelative);
    const base = path.basename(destRelative, path.extname(destRelative));
    const companionExt = ext === 'pdf' ? 'xlsx' : 'pdf';
    const companionRelative = path.join(DEST_DIR, `${base}.${companionExt}`);
    const companionHref = fs.existsSync(abs(companionRelative)) ? webHref(companionRelative) : '';
    const item = {
      group: 'hunt_tables',
      type: ext,
      year: YEAR,
      title: titleFromFile(destRelative),
      subtitle: ext === 'pdf'
        ? 'Formatted visitor hunt table PDF for review/download.'
        : 'Editable formatted hunt table workbook for download.',
      href,
    };
    if (companionHref) {
      item.companion_type = companionExt;
      item.companion_href = companionHref;
    }
    byHref.set(href, item);
    addedOrUpdated.push(href);
  }

  const groupOrder = {
    hunt_tables: 0,
    draw_odds: 1,
    harvest_report: 2,
    conservation_permits: 3,
    regulation: 4,
  };
  const sorted = Array.from(byHref.values()).sort((a, b) => {
    const groupDiff = (groupOrder[a.group] ?? 999) - (groupOrder[b.group] ?? 999);
    if (groupDiff) return groupDiff;
    const yearDiff = Number(b.year || 0) - Number(a.year || 0);
    if (yearDiff) return yearDiff;
    return String(a.title || '').localeCompare(String(b.title || ''));
  });
  writeManifest(sorted);

  console.log(JSON.stringify({
    ok: true,
    source_dir: SOURCE_DIR,
    dest_dir: DEST_DIR,
    copied_files: copied.length,
    manifest_items: sorted.length,
    added_or_updated: addedOrUpdated,
  }, null, 2));
}

main();
