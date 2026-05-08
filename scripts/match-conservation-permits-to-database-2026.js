const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const CSV_DIR = path.join('pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv');
const REPORT_DIR = path.join('pipeline', 'RAW', 'hunt_unit_database', '2026', 'reports');
const DATABASE_FILE = path.join(CSV_DIR, 'DATABASE.csv');
const CONSERVATION_GROUPED = path.join(REPORT_DIR, 'conservation_permits_2025_2027_grouped.csv');
const OUT_CSV = path.join(REPORT_DIR, 'conservation_permits_2025_2027_database_match.csv');
const OUT_JSON = path.join(REPORT_DIR, 'conservation_permits_2025_2027_database_match_report.json');

function abs(relativePath) {
  return path.join(REPO, relativePath);
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
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows.shift().map((header) => String(header || '').trim().replace(/^\uFEFF/, ''));
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

function writeCsv(relativePath, headers, records) {
  const lines = [headers, ...records.map((record) => headers.map((header) => record[header] ?? ''))]
    .map((row) => row.map(csvEscape).join(','));
  fs.writeFileSync(abs(relativePath), `${lines.join('\r\n')}\r\n`, 'utf8');
}

function clean(value) {
  return String(value ?? '').trim();
}

function norm(value) {
  return clean(value)
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/\bmt\b/g, 'mount')
    .replace(/\bmtns\b/g, 'mountains')
    .replace(/\bmtn\b/g, 'mountain')
    .replace(/\ble\b/g, '')
    .replace(/\bconservation\b/g, '')
    .replace(/\bexpo\b/g, '')
    .replace(/\bstatewide permit\b/g, 'statewide')
    .replace(/\bhunter's choice\b/g, 'hunters choice')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokens(value) {
  return new Set(norm(value).split(/\s+/).filter((token) => token && !['the', 'only', 'permit'].includes(token)));
}

function jaccard(a, b) {
  const left = tokens(a);
  const right = tokens(b);
  if (!left.size || !right.size) return 0;
  let intersection = 0;
  for (const token of left) if (right.has(token)) intersection += 1;
  return intersection / new Set([...left, ...right]).size;
}

function speciesMatch(pdfSpecies, dbSpecies, dbSex) {
  const p = norm(pdfSpecies);
  const d = norm(dbSpecies);
  const s = norm(dbSex);
  if (p === d) return true;
  if (p === 'deer' && d === 'deer') return true;
  if (p === 'elk' && d === 'elk' && s !== 'antlerless') return true;
  if (p === 'antlerless elk' && d === 'elk' && s === 'antlerless') return true;
  if (p === 'bear' && d === 'black bear') return true;
  if (p === 'mountain goat' && d === 'mountain goat') return true;
  if (p === 'desert bighorn sheep' && d === 'desert bighorn sheep') return true;
  if (p === 'rocky mountain bighorn sheep' && d === 'rocky mountain bighorn sheep') return true;
  return false;
}

function conditionMatch(pdfCondition, dbWeapon) {
  const pc = norm(pdfCondition);
  const dw = norm(dbWeapon);
  if (!pc || !dw) return true;
  if (pc === dw) return true;
  if (pc.includes('any legal weapon') && dw.includes('any legal weapon')) return true;
  if (pc.includes('hunters choice') && (dw.includes('hunters choice') || dw.includes('any legal weapon'))) return true;
  if (pc.includes('multiseason') && dw.includes('multiseason')) return true;
  if (pc.includes('archery') && dw.includes('archery')) return true;
  if (pc.includes('muzzleloader') && dw.includes('muzzleloader')) return true;
  return false;
}

function main() {
  const database = parseCsv(fs.readFileSync(abs(DATABASE_FILE), 'utf8').replace(/^\uFEFF/, '')).records;
  const grouped = parseCsv(fs.readFileSync(abs(CONSERVATION_GROUPED), 'utf8').replace(/^\uFEFF/, '')).records;
  const dbSpecialRows = database.filter((row) => /conservation|statewide|expo/i.test([row.hunt_name, row.hunt_type, row.weapon, row.NOTES].join(' ')));

  const matches = grouped.map((permit) => {
    const candidates = dbSpecialRows
      .filter((row) => speciesMatch(permit.species, row.species, row.sex_type))
      .filter((row) => conditionMatch(permit.condition, row.weapon))
      .map((row) => {
        const score = Math.max(jaccard(permit.area, row.hunt_name), jaccard(`${permit.area} ${permit.condition}`, `${row.hunt_name} ${row.weapon}`));
        return { row, score };
      })
      .filter((item) => item.score >= 0.36 || norm(permit.area) === norm(item.row.hunt_name))
      .sort((a, b) => b.score - a.score);
    const best = candidates[0];
    const second = candidates[1];
    let status = 'unmatched';
    if (best && best.score >= 0.74 && (!second || best.score - second.score >= 0.1)) status = 'matched_high_confidence';
    else if (best) status = 'manual_review';

    return {
      species: permit.species,
      area: permit.area,
      condition: permit.condition,
      conservation_permit_count_2025_2027: permit.conservation_permit_count_2025_2027,
      permits_2026_conservation: permit.permits_2026_conservation || permit.conservation_permit_count_2025_2027,
      organizations: permit.organizations,
      total_value: permit.total_value,
      match_status: status,
      match_score: best ? best.score.toFixed(3) : '',
      hunt_code: best?.row.hunt_code || '',
      hunt_name: best?.row.hunt_name || '',
      database_species: best?.row.species || '',
      database_sex_type: best?.row.sex_type || '',
      database_weapon: best?.row.weapon || '',
      database_hunt_type: best?.row.hunt_type || '',
      source_pdf: permit.source_pdf,
    };
  });

  const summary = matches.reduce((acc, row) => {
    acc[row.match_status] = (acc[row.match_status] || 0) + 1;
    return acc;
  }, {});
  const report = {
    source_grouped_csv: CONSERVATION_GROUPED.replace(/\\/g, '/'),
    database_file: DATABASE_FILE.replace(/\\/g, '/'),
    output_csv: OUT_CSV.replace(/\\/g, '/'),
    summary,
    note: 'High-confidence rows can be reviewed for special-permit overlay fields. Manual/unmatched rows should not be promoted automatically.',
  };

  writeCsv(OUT_CSV, [
    'species',
    'area',
    'condition',
    'conservation_permit_count_2025_2027',
    'permits_2026_conservation',
    'organizations',
    'total_value',
    'match_status',
    'match_score',
    'hunt_code',
    'hunt_name',
    'database_species',
    'database_sex_type',
    'database_weapon',
    'database_hunt_type',
    'source_pdf',
  ], matches);
  fs.writeFileSync(abs(OUT_JSON), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(report, null, 2));
}

main();
