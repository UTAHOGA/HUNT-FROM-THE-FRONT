const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const DATABASE_FILE = 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv';
const RAW_GROUPED_FILE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_raw_workbook_grouped_2026.csv';
const CROSSWALK_FILE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_area_crosswalk_2026.csv';
const REPORT_FILE = 'pipeline/RAW/hunt_unit_database/2026/reports/conservation_permit_backfill_2026_report.json';

const DIRECT_MAPPINGS = [
  { hunt_code: 'RS1001', species: 'Rocky Mountain Bighorn Sheep', area: 'Book Cliffs, South', condition: 'Any Legal Weapon' },
  { hunt_code: 'RS1003', species: 'Rocky Mountain Bighorn Sheep', area: 'Box Elder, Newfoundland Mtns', condition: 'Any Legal Weapon', area_prefix: true },
  { hunt_code: 'RS1006', species: 'Rocky Mountain Bighorn Sheep', area: 'Nine Mile, Gray Canyon', condition: 'Any Legal Weapon' },

  { hunt_code: 'TK1012', species: 'Turkey', area: 'Central Area', condition: 'Multiseason' },
  { hunt_code: 'TK1013', species: 'Turkey', area: 'Northeastern Area', condition: 'Multiseason' },
  { hunt_code: 'TK1014', species: 'Turkey', area: 'Northern Area', condition: 'Multiseason' },
  { hunt_code: 'TK1015', species: 'Turkey', area: 'Southeastern Area', condition: 'Multiseason' },
  { hunt_code: 'TK1016', species: 'Turkey', area: 'Southern Area', condition: 'Multiseason' },

  { hunt_code: 'EB3128', species: 'Elk', area: 'Box Elder, Grouse Creek', condition: 'Multiseason' },
  { hunt_code: 'EB3209', species: 'Elk', area: 'Box Elder, Pilot Mtn', condition: 'Multiseason' },

  { hunt_code: 'DS1002', species: 'Desert Bighorn Sheep', area: 'Kaiparowits, East', condition: 'Any Legal Weapon' },
  { hunt_code: 'DS1003', species: 'Desert Bighorn Sheep', area: 'Kaiparowits, Escalante', condition: 'Any Legal Weapon' },
  { hunt_code: 'DS1004', species: 'Desert Bighorn Sheep', area: 'San Rafael, Dirty Devil', condition: 'Any Legal Weapon' },
  { hunt_code: 'DS1006', species: 'Desert Bighorn Sheep', area: 'Kaiparowits, West', condition: 'Any Legal Weapon' },
  { hunt_code: 'DS1007', species: 'Desert Bighorn Sheep', area: 'San Rafael, South', condition: 'Any Legal Weapon' },
  { hunt_code: 'DS6605', species: 'Desert Bighorn Sheep', area: 'Pine Valley, Beaver Dam', condition: 'Any Legal Weapon' },

  { hunt_code: 'DB1056', species: 'Deer', area: 'Book Cliffs', condition: "Hunter's Choice" },
  { hunt_code: 'DB1075', species: 'Deer', area: 'Book Cliffs', condition: 'Archery' },
  { hunt_code: 'DB1076', species: 'Deer', area: 'Book Cliffs', condition: 'Muzzleloader' },
  { hunt_code: 'DB1118', species: 'Deer', area: 'La Sal, Dolores Triangle', condition: 'Multiseason' },

  { hunt_code: 'BR7307', species: 'Bear', area: 'La Sal', condition: 'Multiseason' },
  { hunt_code: 'BR7324', species: 'Bear', area: 'Chalk Creek/East Canyon/Morgan-South Rich', condition: 'Multiseason' },
];

function abs(file) {
  return path.join(REPO, file);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (ch === '"') quoted = false;
      else value += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') {
      row.push(value);
      value = '';
    } else if (ch === '\n') {
      row.push(value);
      rows.push(row);
      row = [];
      value = '';
    } else if (ch !== '\r') value += ch;
  }
  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }
  const headers = (rows.shift() || []).map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
  return {
    headers,
    records: rows
      .filter((r) => r.some((cell) => String(cell || '').trim()))
      .map((r) => Object.fromEntries(headers.map((header, idx) => [header, r[idx] || '']))),
  };
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function writeCsv(headers, records) {
  return `${[headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))]
    .map((row) => row.map(csvEscape).join(','))
    .join('\r\n')}\r\n`;
}

function clean(value) {
  return String(value ?? '').trim();
}

function norm(value) {
  return clean(value)
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/\bmtns\b/g, 'mountains')
    .replace(/\bmtn\b/g, 'mountain')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function rawMatches(row, mapping) {
  if (norm(row.species) !== norm(mapping.species)) return false;
  if (norm(row.condition) !== norm(mapping.condition)) return false;
  if (mapping.area_prefix) return norm(row.area).startsWith(norm(mapping.area));
  return norm(row.area) === norm(mapping.area);
}

function sumRaw(rawRows, mapping) {
  const matches = rawRows.filter((row) => rawMatches(row, mapping));
  const count = matches.reduce((sum, row) => sum + Number(row.permits_2026_conservation || 0), 0);
  return { count, matches };
}

function describeCondition(condition) {
  const text = clean(condition);
  if (text.toLowerCase() === "hunter's choice") {
    return "Hunter's Choice - winning bidder chooses one eligible season for that unit/species; not a multiseason permit";
  }
  return text;
}

function ensureHeaders(headers, fields) {
  const next = [...headers];
  for (const field of fields) if (!next.includes(field)) next.push(field);
  return next;
}

function main() {
  const db = parseCsv(fs.readFileSync(abs(DATABASE_FILE), 'utf8').replace(/^\uFEFF/, ''));
  const rawGrouped = parseCsv(fs.readFileSync(abs(RAW_GROUPED_FILE), 'utf8').replace(/^\uFEFF/, ''));
  const crosswalk = fs.existsSync(abs(CROSSWALK_FILE)) ? parseCsv(fs.readFileSync(abs(CROSSWALK_FILE), 'utf8').replace(/^\uFEFF/, '')) : { records: [] };
  const headers = ensureHeaders(db.headers, [
    'permits_2026_conservation',
    'permits_2026_expo',
    'permits_2026_sportsman',
    'special_permit_area_id',
    'special_permit_category',
    'special_permit_note',
    'special_permit_overlay_source',
  ]);
  const byCode = new Map(db.records.map((row) => [clean(row.hunt_code).toUpperCase(), row]));
  const changes = [];
  const misses = [];

  function update(row, values, sourceLabel) {
    for (const [field, value] of Object.entries(values)) {
      const before = clean(row[field]);
      const after = clean(value);
      if (before !== after) {
        row[field] = after;
        changes.push({ hunt_code: row.hunt_code, field, before, after, source: sourceLabel });
      }
    }
  }

  for (const mapping of DIRECT_MAPPINGS) {
    const row = byCode.get(mapping.hunt_code);
    if (!row) {
      misses.push({ ...mapping, reason: 'hunt_code_missing_from_database' });
      continue;
    }
    const { count, matches } = sumRaw(rawGrouped.records, mapping);
    if (!count || !matches.length) {
      misses.push({ ...mapping, reason: 'source_count_not_found' });
      continue;
    }
    const sourceAreas = matches.map((item) => `${item.area} (${describeCondition(item.condition)})`).join('; ');
    update(row, {
      permits_2026_conservation: String(count),
      special_permit_category: 'CONSERVATION',
      special_permit_area_id: `CONSERVATION_${mapping.species}_${mapping.area}_2026`.toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/_+$/g, ''),
      special_permit_note: `2026 conservation permit count from 2025-2027 conservation workbook source area: ${sourceAreas}. Kept outside normal public draw quota.`,
      special_permit_overlay_source: RAW_GROUPED_FILE,
    }, 'direct_raw_workbook_mapping');
  }

  for (const cw of crosswalk.records) {
    if (cw.review_status !== 'READY_FOR_OWNER_REVIEW') continue;
    const row = byCode.get(clean(cw.primary_hunt_code).toUpperCase());
    if (!row) {
      misses.push({ hunt_code: cw.primary_hunt_code, reason: 'crosswalk_primary_hunt_code_missing' });
      continue;
    }
    update(row, {
      permits_2026_conservation: clean(cw.permits_2026_conservation),
      special_permit_category: 'CONSERVATION',
      special_permit_area_id: clean(cw.conservation_area_id),
      special_permit_note: `Conservation permit area ${cw.conservation_area} covers ${cw.included_hunt_code_count} applicable hunt codes; see conservation_area_crosswalk_2026.csv. Kept outside normal public draw quota.`,
      special_permit_overlay_source: CROSSWALK_FILE,
    }, 'reviewed_area_crosswalk');
  }

  fs.writeFileSync(abs(DATABASE_FILE), writeCsv(headers, db.records), 'utf8');
  const report = {
    generated_at: new Date().toISOString(),
    database_file: DATABASE_FILE,
    raw_grouped_file: RAW_GROUPED_FILE,
    crosswalk_file: CROSSWALK_FILE,
    changed_cells: changes.length,
    changed_hunt_codes: [...new Set(changes.map((item) => item.hunt_code))].sort(),
    misses,
    changes,
  };
  fs.writeFileSync(abs(REPORT_FILE), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    ok: misses.length === 0,
    changed_cells: changes.length,
    changed_hunt_codes: report.changed_hunt_codes,
    misses: misses.length,
    report: REPORT_FILE,
  }, null, 2));
  if (misses.length) process.exitCode = 1;
}

main();
