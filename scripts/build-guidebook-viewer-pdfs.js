const fs = require("fs/promises");
const path = require("path");
const { PDFDocument } = require("pdf-lib");

const ROOT = path.resolve(__dirname, "..");
const REG_DIR = path.join(ROOT, "public", "hard-copy", "regulations", "2026");
const MANUAL_ITEMS_PATH = path.join(
  ROOT,
  "processed_data",
  "hard_data_exports",
  "library",
  "public_library_manual_items.json",
);

function toAbsFromRepoPath(relPath) {
  const cleaned = String(relPath || "")
    .trim()
    .replace(/^\.\//, "")
    .replace(/^\/+/, "")
    .replace(/\//g, path.sep);
  return path.join(ROOT, cleaned);
}

async function exists(absPath) {
  try {
    await fs.access(absPath);
    return true;
  } catch {
    return false;
  }
}

async function readJson(absPath) {
  const raw = await fs.readFile(absPath, "utf8");
  return JSON.parse(raw.replace(/^\uFEFF/, ""));
}

async function buildPairMap() {
  const pairMap = new Map();

  if (!(await exists(REG_DIR))) return pairMap;

  const entries = await fs.readdir(REG_DIR, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    if (!entry.name.toLowerCase().endsWith(".corrections-updates.pdf")) continue;
    const baseName = entry.name.replace(/\.corrections-updates\.pdf$/i, "");
    const updatesAbs = path.join(REG_DIR, entry.name);
    const originalAbs = path.join(REG_DIR, `${baseName}.pdf`);
    if (!(await exists(originalAbs))) continue;
    pairMap.set(baseName, { baseName, updatesAbs, originalAbs, source: "folder-scan" });
  }

  if (await exists(MANUAL_ITEMS_PATH)) {
    const items = await readJson(MANUAL_ITEMS_PATH);
    if (Array.isArray(items)) {
      for (const item of items) {
        const href = String(item?.href || "").trim();
        const companionHref = String(item?.companion_href || "").trim();
        if (!href.toLowerCase().endsWith(".pdf")) continue;
        if (!companionHref.toLowerCase().endsWith(".pdf")) continue;
        const originalAbs = toAbsFromRepoPath(href);
        const updatesAbs = toAbsFromRepoPath(companionHref);
        if (!(await exists(originalAbs)) || !(await exists(updatesAbs))) continue;
        const baseName = path.basename(originalAbs, ".pdf");
        if (!pairMap.has(baseName)) {
          pairMap.set(baseName, { baseName, updatesAbs, originalAbs, source: "manual-manifest" });
        }
      }
    }
  }

  return pairMap;
}

async function mergePdfPair({ baseName, updatesAbs, originalAbs }) {
  const merged = await PDFDocument.create();
  for (const src of [updatesAbs, originalAbs]) {
    const bytes = await fs.readFile(src);
    const srcDoc = await PDFDocument.load(bytes);
    const copied = await merged.copyPages(srcDoc, srcDoc.getPageIndices());
    copied.forEach((page) => merged.addPage(page));
  }
  const outBytes = await merged.save();
  const viewerAbs = path.join(REG_DIR, `${baseName}.viewer.pdf`);
  await fs.writeFile(viewerAbs, outBytes);
  return viewerAbs;
}

async function main() {
  const pairMap = await buildPairMap();
  const pairs = Array.from(pairMap.values());

  if (!pairs.length) {
    console.log("No guidebook update+original PDF pairs found. Nothing to merge.");
    return;
  }

  const created = [];
  for (const pair of pairs) {
    const viewerAbs = await mergePdfPair(pair);
    created.push({
      baseName: pair.baseName,
      viewerRel: path.relative(ROOT, viewerAbs).replace(/\\/g, "/"),
      source: pair.source,
    });
  }

  console.log(`Generated ${created.length} guidebook viewer PDF(s):`);
  created.forEach((item) => console.log(`- ${item.viewerRel} (${item.source})`));
}

main().catch((error) => {
  console.error("Failed to build guidebook viewer PDFs.");
  console.error(error);
  process.exit(1);
});
