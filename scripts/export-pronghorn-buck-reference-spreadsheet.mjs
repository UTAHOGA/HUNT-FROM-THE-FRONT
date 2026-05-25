import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const REPO_ROOT = process.cwd();
const SOURCE_CSV = path.join(
  REPO_ROOT,
  "processed_data",
  "pronghorn_buck_limited_entry_reference_export.csv",
);
const OUTPUT_XLSX = path.join(
  REPO_ROOT,
  "processed_data",
  "pronghorn_buck_limited_entry_reference_export.xlsx",
);
const OUTPUT_REPORT = path.join(
  REPO_ROOT,
  "processed_data",
  "pronghorn_buck_limited_entry_reference_export_xlsx_report.json",
);

const csvText = await fs.readFile(SOURCE_CSV, "utf8");
const workbook = await Workbook.fromCSV(csvText, {
  sheetName: "Pronghorn Buck Reference",
});

const sheet = workbook.worksheets.getItem("Pronghorn Buck Reference");
sheet.freezePanes.freezeRows(1);
sheet.showGridLines = false;

const used = sheet.getUsedRange();
used.format = {
  font: { name: "Aptos", size: 10, color: "#2D251A" },
  wrapText: true,
};

sheet.getRange("A1:N1").format = {
  fill: "#6B3F18",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};

sheet.getRange("H:J").format = {
  numberFormat: "0",
};
sheet.getRange("A:A").format.columnWidthPx = 240;
sheet.getRange("B:B").format.columnWidthPx = 90;
sheet.getRange("C:E").format.columnWidthPx = 115;
sheet.getRange("F:F").format.columnWidthPx = 220;
sheet.getRange("G:G").format.columnWidthPx = 235;
sheet.getRange("H:J").format.columnWidthPx = 80;
sheet.getRange("K:M").format.columnWidthPx = 160;
sheet.getRange("N:N").format.columnWidthPx = 420;

const preview = await workbook.render({
  sheetName: "Pronghorn Buck Reference",
  range: "A1:N18",
  scale: 1,
  format: "png",
});
await preview.arrayBuffer();

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 20 },
  summary: "final formula error scan",
});

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(OUTPUT_XLSX);

const report = {
  status: "PASS",
  source_csv: path.relative(REPO_ROOT, SOURCE_CSV),
  output_xlsx: path.relative(REPO_ROOT, OUTPUT_XLSX),
  formula_error_scan: errors.ndjson,
};
await fs.writeFile(OUTPUT_REPORT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
