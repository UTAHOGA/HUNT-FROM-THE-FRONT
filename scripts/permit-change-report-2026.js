const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const input = path.join(repo, 'pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv');
const outDir = path.join(repo, 'processed_data/permit_change_review_2026');

function parseCsv(s) {
  const rows = [];
  let r = [];
  let c = '';
  let q = false;
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    const n = s[i + 1];
    if (q) {
      if (ch === '"' && n === '"') {
        c += '"';
        i += 1;
      } else if (ch === '"') q = false;
      else c += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') {
      r.push(c);
      c = '';
    } else if (ch === '\n') {
      r.push(c);
      rows.push(r);
      r = [];
      c = '';
    } else if (ch !== '\r') c += ch;
  }
  if (c.length || r.length) {
    r.push(c);
    rows.push(r);
  }
  const h = (rows.shift() || []).map((x) => String(x || '').trim());
  return rows
    .filter((v) => v.some((x) => String(x || '').trim()))
    .map((v) => Object.fromEntries(h.map((k, i) => [k, v[i] || '']).filter(([k]) => k)));
}

function esc(v) {
  const s = String(v ?? '');
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function num(v) {
  const s = String(v ?? '').trim().replace(/,/g, '');
  return /^-?\d+(\.\d+)?$/.test(s) ? Number(s) : null;
}

function val(v) {
  return v == null ? '' : String(v);
}

function firstValue(row, keys) {
  for (const key of keys) {
    const value = row[key];
    if (value != null && String(value).trim() !== '') return value;
  }
  return '';
}

function d(n, o) {
  return n == null || o == null ? '' : n - o;
}

function pct(n, o) {
  return n == null || o == null || o === 0 ? '' : `${(((n - o) / o) * 100).toFixed(1)}%`;
}

const rows = parseCsv(fs.readFileSync(input, 'utf8').replace(/^\uFEFF/, ''));
const out = rows
  .map((r) => {
    const oT = num(firstValue(r, ['permits_2025_total', 'permits_2025_draw_total']));
    const nT = num(r.permits_2026_total);
    const oR = num(firstValue(r, ['permits_2025_res', 'permits_2025_draw_res']));
    const nR = num(r.permits_2026_res);
    const oN = num(firstValue(r, ['permits_2025_nr', 'permits_2025_draw_nr']));
    const nN = num(r.permits_2026_nr);
    const changed = [oT, nT, oR, nR, oN, nN].some((x) => x != null)
      && (
        (d(nT, oT) !== '' && d(nT, oT) !== 0)
        || (d(nR, oR) !== '' && d(nR, oR) !== 0)
        || (d(nN, oN) !== '' && d(nN, oN) !== 0)
      );
    return {
      hunt_code: String(r.hunt_code || '').trim().toUpperCase(),
      hunt_name: r.hunt_name || '',
      species: r.species || '',
      sex_type: r.sex_type || '',
      hunt_type: r.hunt_type || '',
      season: r.season || '',
      permits_2025_res: val(oR),
      permits_2026_res: val(nR),
      delta_res: d(nR, oR),
      permits_2025_nr: val(oN),
      permits_2026_nr: val(nN),
      delta_nr: d(nN, oN),
      permits_2025_total: val(oT),
      permits_2026_total: val(nT),
      delta_total: d(nT, oT),
      pct_change_total: pct(nT, oT),
      change_status: changed ? 'CHANGED' : 'UNCHANGED_OR_INCOMPLETE',
    };
  })
  .filter((r) => r.hunt_code);

out.sort((a, b) => {
  const ad = typeof a.delta_total === 'number' ? Math.abs(a.delta_total) : -1;
  const bd = typeof b.delta_total === 'number' ? Math.abs(b.delta_total) : -1;
  return bd - ad || a.hunt_code.localeCompare(b.hunt_code);
});

const changed = out.filter((r) => r.change_status === 'CHANGED');
const headers = Object.keys(out[0] || {});
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'same_hunt_code_permit_comparison_all.csv'), [headers.join(','), ...out.map((r) => headers.map((h) => esc(r[h])).join(','))].join('\n') + '\n');
fs.writeFileSync(path.join(outDir, 'same_hunt_code_permit_changes_only.csv'), [headers.join(','), ...changed.map((r) => headers.map((h) => esc(r[h])).join(','))].join('\n') + '\n');
fs.writeFileSync(
  path.join(outDir, 'same_hunt_code_permit_changes_summary.json'),
  `${JSON.stringify({
    source: path.relative(repo, input),
    rows: rows.length,
    compared: out.length,
    changed: changed.length,
    previous_year_fields: ['permits_2025_res', 'permits_2025_nr', 'permits_2025_total', 'permits_2025_draw_res', 'permits_2025_draw_nr', 'permits_2025_draw_total'],
    current_year_fields: ['permits_2026_res', 'permits_2026_nr', 'permits_2026_total'],
    outputs: ['same_hunt_code_permit_comparison_all.csv', 'same_hunt_code_permit_changes_only.csv'],
  }, null, 2)}\n`,
);
console.log(JSON.stringify({ ok: true, changed: changed.length, outDir: path.relative(repo, outDir) }, null, 2));
