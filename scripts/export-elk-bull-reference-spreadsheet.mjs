import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const REPO_ROOT = process.cwd();
const SOURCE_CSV = path.join(
  REPO_ROOT,
  "data",
  "utah",
  "official_downloads_2026",
  "hunt_master_canonical_2026.csv",
);
const OUTPUT_DIR = path.join(REPO_ROOT, "processed_data");
const OUTPUT_CSV = path.join(OUTPUT_DIR, "elk_bull_reference_hunt_planner_reference.csv");
const OUTPUT_XLSX = path.join(OUTPUT_DIR, "elk_bull_reference_hunt_planner_reference.xlsx");
const OUTPUT_REPORT = path.join(OUTPUT_DIR, "elk_bull_reference_hunt_planner_reference_report.json");

const CODES = [
  "EB1000",
  "EB1001",
  "EB1002",
  "EB1003",
  "EB1004",
  "EB1005",
  "EB1007",
  "EB1009",
  "EB1010",
  "EB1011",
  "EB1012",
  "EB3128",
  "EB3209",
];

const COLUMNS = [
  "Hunt Name",
  "Hunt Code",
  "Sex",
  "Species",
  "Weapon",
  "Hunt Type",
  "Season",
  "Non Res",
  "Res",
  "Total",
  "Source Authority",
  "Permit Status",
  "Data Status",
  "Notes",
];

const HUNT_NAME_OVERRIDES = new Map([
  ["EB1011", "Youth General Season Bull Elk"],
]);

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        field += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += char;
  }

  if (field.length > 0 || row.length > 0) row.push(field);
  if (row.length) rows.push(row);

  const [header, ...body] = rows.filter((entry) => entry.some((value) => value !== ""));
  return body.map((values) =>
    Object.fromEntries(header.map((name, index) => [name, values[index] ?? ""])),
  );
}

function toCsv(rows) {
  const escape = (value) => {
    const text = String(value ?? "");
    if (/[",\r\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
    return text;
  };
  return [
    COLUMNS.map(escape).join(","),
    ...rows.map((row) => COLUMNS.map((column) => escape(row[column])).join(",")),
  ].join("\r\n");
}

function cleanNumber(value) {
  const text = String(value ?? "").trim();
  if (!text) return "";
  const number = Number(text);
  if (!Number.isFinite(number)) return text;
  return Number.isInteger(number) ? String(number) : String(number);
}

function sortByCode(left, right) {
  return Number(left["Hunt Code"].slice(2)) - Number(right["Hunt Code"].slice(2));
}

function buildRows(sourceRows) {
  const byCode = new Map(sourceRows.map((row) => [row.hunt_code, row]));
  const missing = CODES.filter((code) => !byCode.has(code));
  if (missing.length) {
    throw new Error(`Missing canonical EB source rows: ${missing.join(", ")}`);
  }

  return CODES.map((code) => {
    const row = byCode.get(code);
    const total = row.permit_status === "TOTAL_ONLY" ? cleanNumber(row.permits_2026_total) : "";
    const permitStatus = total ? "TOTAL_ONLY" : "NO_QUOTA_PUBLISHED";
    return {
      "Hunt Name": HUNT_NAME_OVERRIDES.get(row.hunt_code) ?? row.hunt_name,
      "Hunt Code": row.hunt_code,
      Sex: row.sex_type,
      Species: row.species,
      Weapon: row.weapon,
      "Hunt Type": row.hunt_type,
      Season: row.season,
      "Non Res": "",
      Res: "",
      Total: total,
      "Source Authority": "Utah DWR Hunt Planner",
      "Permit Status": permitStatus,
      "Data Status": permitStatus === "TOTAL_ONLY"
        ? "SOURCE_CONFIRMED_TOTAL_ONLY"
        : "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
      Notes: row.permit_note || "Current Utah DWR Hunt Planner reference row.",
    };
  }).sort(sortByCode);
}

function validate(rows) {
  const duplicateCodes = rows
    .map((row) => row["Hunt Code"])
    .filter((code, index, codes) => codes.indexOf(code) !== index);
  const totalOnlyRows = rows.filter((row) => row["Permit Status"] === "TOTAL_ONLY");
  const noQuotaRows = rows.filter((row) => row["Permit Status"] === "NO_QUOTA_PUBLISHED");
  const staleQuotaLeaks = noQuotaRows.filter((row) => row.Total || row.Res || row["Non Res"]);
  const missingRequired = rows.filter((row) =>
    [
      "Hunt Name",
      "Hunt Code",
      "Sex",
      "Species",
      "Weapon",
      "Hunt Type",
      "Season",
      "Source Authority",
      "Permit Status",
      "Data Status",
    ].some((column) => !row[column]),
  );

  const failures = [];
  if (rows.length !== 13) failures.push(`Expected 13 EB rows, found ${rows.length}.`);
  if (totalOnlyRows.length !== 5) failures.push(`Expected 5 TOTAL_ONLY rows, found ${totalOnlyRows.length}.`);
  if (noQuotaRows.length !== 8) failures.push(`Expected 8 NO_QUOTA_PUBLISHED rows, found ${noQuotaRows.length}.`);
  if (duplicateCodes.length) failures.push(`Duplicate hunt codes: ${duplicateCodes.join("; ")}`);
  if (staleQuotaLeaks.length) failures.push(`NO_QUOTA_PUBLISHED rows have quota values: ${staleQuotaLeaks.map((row) => row["Hunt Code"]).join("; ")}`);
  if (missingRequired.length) failures.push(`Rows missing required values: ${missingRequired.length}.`);

  return {
    status: failures.length ? "FAIL" : "PASS",
    failures,
    row_count: rows.length,
    total_only_row_count: totalOnlyRows.length,
    no_quota_published_row_count: noQuotaRows.length,
    duplicate_code_count: duplicateCodes.length,
    stale_quota_leak_count: staleQuotaLeaks.length,
    total_only_codes: totalOnlyRows.map((row) => row["Hunt Code"]),
    no_quota_published_codes: noQuotaRows.map((row) => row["Hunt Code"]),
    required_quota_columns: ["Non Res", "Res", "Total"],
    source_authority: "Utah DWR Hunt Planner",
    output_csv: path.relative(REPO_ROOT, OUTPUT_CSV),
    output_xlsx: path.relative(REPO_ROOT, OUTPUT_XLSX),
  };
}

const sourceText = await fs.readFile(SOURCE_CSV, "utf8");
const outputRows = buildRows(parseCsv(sourceText));
const report = validate(outputRows);

if (report.status !== "PASS") {
  console.error(JSON.stringify(report, null, 2));
  process.exit(1);
}

await fs.mkdir(OUTPUT_DIR, { recursive: true });
const csvText = `${toCsv(outputRows)}\r\n`;
await fs.writeFile(OUTPUT_CSV, csvText, "utf8");

const workbook = await Workbook.fromCSV(csvText, {
  sheetName: "Elk Bull Reference",
});
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(OUTPUT_XLSX);

await fs.writeFile(OUTPUT_REPORT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
