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
const OUTPUT_CSV = path.join(
  OUTPUT_DIR,
  "elk_bull_private_lands_hunt_planner_reference.csv",
);
const OUTPUT_XLSX = path.join(
  OUTPUT_DIR,
  "elk_bull_private_lands_hunt_planner_reference.xlsx",
);
const OUTPUT_REPORT = path.join(
  OUTPUT_DIR,
  "elk_bull_private_lands_hunt_planner_reference_report.json",
);

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

const LO_OVERRIDES = new Map([
  [
    "LO0011",
    {
      huntName: "Diamond Mtn Landowner Association",
      weapon: "Archery",
      season:
        "Aug 15 2026 - Sept 15 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
    },
  ],
  [
    "LO0012",
    {
      huntName: "Diamond Mtn Landowner Association",
      weapon: "Any Legal Weapon",
      season:
        "Sept 16 - Sept 20, 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
    },
  ],
  [
    "LO0013",
    {
      huntName: "Diamond Mtn Landowner Association",
      weapon: "Any Legal Weapon",
      season:
        "Oct 3, 2026 - Oct 15, 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
    },
  ],
  [
    "LO0014",
    {
      huntName: "Diamond Mtn Landowner Association",
      weapon: "Muzzleloader",
      season:
        "Sept 21, 2026 - Oct 2, 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
    },
  ],
  [
    "LO0015",
    {
      huntName: "Diamond Mtn Landowner Association",
      weapon: "Any Legal Weapon",
      season:
        "Nov 07 2026 - Nov 15 2026 - Valid only on property enrolled in the Diamond Mtn LOA",
    },
  ],
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
      if (char === "\r" && next === "\n") {
        i += 1;
      }
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += char;
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  const [header, ...body] = rows.filter((entry) =>
    entry.some((value) => value !== ""),
  );
  return body.map((values) =>
    Object.fromEntries(header.map((name, index) => [name, values[index] ?? ""])),
  );
}

function toCsv(rows) {
  const escape = (value) => {
    const text = String(value ?? "");
    if (/[",\r\n]/.test(text)) {
      return `"${text.replaceAll('"', '""')}"`;
    }
    return text;
  };

  return [
    COLUMNS.map(escape).join(","),
    ...rows.map((row) => COLUMNS.map((column) => escape(row[column])).join(",")),
  ].join("\r\n");
}

function sortByCode(left, right) {
  const leftPrefix = left["Hunt Code"].slice(0, 2);
  const rightPrefix = right["Hunt Code"].slice(0, 2);
  if (leftPrefix !== rightPrefix) {
    return leftPrefix.localeCompare(rightPrefix);
  }
  return Number(left["Hunt Code"].slice(2)) - Number(right["Hunt Code"].slice(2));
}

function buildRows(sourceRows) {
  const selected = sourceRows.filter(
    (row) => row.hunt_code.startsWith("EL") || LO_OVERRIDES.has(row.hunt_code),
  );

  return selected
    .map((row) => {
      const override = LO_OVERRIDES.get(row.hunt_code);
      return {
        "Hunt Name": override?.huntName ?? row.hunt_name,
        "Hunt Code": row.hunt_code,
        Sex: row.sex_type,
        Species: row.species,
        Weapon: override?.weapon ?? row.weapon,
        "Hunt Type": "Limited Entry - Private Land Only",
        Season: override?.season ?? row.season,
        "Non Res": "",
        Res: "",
        Total: "",
        "Source Authority": "Utah DWR Hunt Planner",
        "Permit Status": "NO_QUOTA_PUBLISHED",
        "Data Status": "SOURCE_CONFIRMED_NO_QUOTA_PUBLISHED",
        Notes:
          "DWR Hunt Planner source confirmed; no resident, nonresident or total permit allotment published for this private-land hunt.",
      };
    })
    .sort(sortByCode);
}

function validate(rows) {
  const failures = [];
  const codes = rows.map((row) => row["Hunt Code"]);
  const duplicateCodes = codes.filter((code, index) => codes.indexOf(code) !== index);
  const elCount = rows.filter((row) => row["Hunt Code"].startsWith("EL")).length;
  const loCount = rows.filter((row) => row["Hunt Code"].startsWith("LO")).length;
  const quotaLeakCount = rows.filter(
    (row) => row["Non Res"] !== "" || row.Res !== "" || row.Total !== "",
  ).length;
  const missingRequiredValueCount = rows.filter((row) =>
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
  ).length;

  if (rows.length !== 131) failures.push(`Expected 131 rows, found ${rows.length}.`);
  if (elCount !== 126) failures.push(`Expected 126 EL rows, found ${elCount}.`);
  if (loCount !== 5) failures.push(`Expected 5 LO rows, found ${loCount}.`);
  if (duplicateCodes.length) failures.push(`Duplicate hunt codes: ${duplicateCodes.join("; ")}`);
  if (quotaLeakCount) failures.push(`Expected blank quota columns, found ${quotaLeakCount} populated rows.`);
  if (missingRequiredValueCount) failures.push(`Rows missing required values: ${missingRequiredValueCount}.`);

  return {
    status: failures.length ? "FAIL" : "PASS",
    failures,
    row_count: rows.length,
    el_row_count: elCount,
    lo_row_count: loCount,
    duplicate_code_count: duplicateCodes.length,
    blank_quota_columns_confirmed: quotaLeakCount === 0,
    source_authority: "Utah DWR Hunt Planner",
    output_csv: path.relative(REPO_ROOT, OUTPUT_CSV),
    output_xlsx: path.relative(REPO_ROOT, OUTPUT_XLSX),
  };
}

const sourceText = await fs.readFile(SOURCE_CSV, "utf8");
const sourceRows = parseCsv(sourceText);
const outputRows = buildRows(sourceRows);
const report = validate(outputRows);

if (report.status !== "PASS") {
  console.error(JSON.stringify(report, null, 2));
  process.exit(1);
}

await fs.mkdir(OUTPUT_DIR, { recursive: true });
const csvText = `${toCsv(outputRows)}\r\n`;
await fs.writeFile(OUTPUT_CSV, csvText, "utf8");

const workbook = await Workbook.fromCSV(csvText, {
  sheetName: "Elk Bull Private Lands",
});
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(OUTPUT_XLSX);

await fs.writeFile(OUTPUT_REPORT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
