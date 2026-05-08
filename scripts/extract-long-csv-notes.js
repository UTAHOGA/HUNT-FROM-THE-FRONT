const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const CSV_DIR = path.join(REPO, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'csv');
const NOTES_DIR = path.join(REPO, 'pipeline', 'RAW', 'hunt_unit_database', '2026', 'notes');
const REPORT_JSON = path.join(REPO, 'processed_data', 'csv_notes_link_report_20260508.json');
const REPORT_MD = path.join(REPO, 'processed_data', 'csv_notes_link_report_20260508.md');
const LONG_NOTE_THRESHOLD = 120;

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n') {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
    } else if (ch !== '\r') {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\r\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function writeCsv(rows) {
  return `${rows.map(row => row.map(csvEscape).join(',')).join('\r\n')}\r\n`;
}

function slug(value, fallback) {
  const cleaned = String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return cleaned || fallback;
}

function titleFromRow(headers, row) {
  const codeIndex = headers.findIndex(h => /^(hunt_code|hunt_number)$/i.test(h));
  const nameIndex = headers.findIndex(h => /^(hunt_name|unit|name)$/i.test(h));
  const code = codeIndex >= 0 ? row[codeIndex] : '';
  const name = nameIndex >= 0 ? row[nameIndex] : '';
  return { code: String(code || '').trim(), name: String(name || '').trim() };
}

function alreadyLink(value) {
  return /^(\.\/|\.\.\/|https?:\/\/).+/i.test(String(value || '').trim());
}

function processFile(file) {
  const raw = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');
  const rows = parseCsv(raw);
  if (rows.length < 2) return { changes: [], skipped: null };
  const headers = rows[0].map(h => String(h || '').trim());
  const noteIndexes = headers
    .map((header, index) => ({ header, index }))
    .filter(item => /^notes?$/i.test(item.header))
    .map(item => item.index);
  if (!noteIndexes.length) return { changes: [], skipped: null };

  const csvName = path.basename(file, '.csv');
  const noteSubdir = path.join(NOTES_DIR, csvName);
  const changed = [];

  for (let rowIndex = 1; rowIndex < rows.length; rowIndex += 1) {
    const row = rows[rowIndex];
    for (const noteIndex of noteIndexes) {
      const note = String(row[noteIndex] || '').trim();
      if (!note || note.length <= LONG_NOTE_THRESHOLD || alreadyLink(note)) continue;
      const { code, name } = titleFromRow(headers, row);
      const noteId = slug(code, `ROW-${rowIndex}`);
      const noteFile = path.join(noteSubdir, `${noteId}-notes.md`);
      const relativeFromCsv = path.relative(path.dirname(file), noteFile).replace(/\\/g, '/');
      fs.mkdirSync(path.dirname(noteFile), { recursive: true });
      fs.writeFileSync(noteFile, [
        `# ${code || noteId} Notes`,
        '',
        `- Source CSV: ${path.relative(REPO, file).replace(/\\/g, '/')}`,
        `- Source row: ${rowIndex + 1}`,
        name ? `- Hunt name: ${name}` : null,
        code ? `- Hunt code: ${code}` : null,
        '',
        '## Notes',
        '',
        note,
        '',
      ].filter(Boolean).join('\n'), 'utf8');
      row[noteIndex] = relativeFromCsv;
      changed.push({
        source_csv: path.relative(REPO, file).replace(/\\/g, '/'),
        row_number: rowIndex + 1,
        hunt_code: code || noteId,
        hunt_name: name,
        note_column: headers[noteIndex],
        original_length: note.length,
        note_file: path.relative(REPO, noteFile).replace(/\\/g, '/'),
        csv_value: relativeFromCsv,
      });
    }
  }

  if (changed.length) {
    try {
      fs.writeFileSync(file, writeCsv(rows), 'utf8');
    } catch (error) {
      return {
        changes: [],
        skipped: {
          source_csv: path.relative(REPO, file).replace(/\\/g, '/'),
          reason: error.code || error.message,
          note_files_prepared: changed.map(change => change.note_file),
        },
      };
    }
  }
  return { changes: changed, skipped: null };
}

const changes = [];
const skipped = [];
for (const entry of fs.readdirSync(CSV_DIR).sort()) {
  if (!entry.toLowerCase().endsWith('.csv')) continue;
  const result = processFile(path.join(CSV_DIR, entry));
  changes.push(...result.changes);
  if (result.skipped) skipped.push(result.skipped);
}

fs.mkdirSync(path.dirname(REPORT_JSON), { recursive: true });
fs.writeFileSync(REPORT_JSON, `${JSON.stringify({
  generated_at: new Date().toISOString(),
  threshold_characters: LONG_NOTE_THRESHOLD,
  changes,
  skipped,
}, null, 2)}\n`, 'utf8');

const lines = [
  '# CSV Notes Link Report',
  '',
  `Generated: ${new Date().toISOString()}`,
  '',
  `Long-note threshold: ${LONG_NOTE_THRESHOLD} characters`,
  '',
  `Linked notes created: ${changes.length}`,
  '',
  `Skipped locked files: ${skipped.length}`,
  '',
  '| Source CSV | Row | Hunt code | Note file | Original length |',
  '| --- | ---: | --- | --- | ---: |',
  ...changes.map(change => `| ${change.source_csv} | ${change.row_number} | ${change.hunt_code} | ${change.note_file} | ${change.original_length} |`),
  '',
  '## Skipped Files',
  '',
  ...(skipped.length ? skipped.map(item => `- ${item.source_csv}: ${item.reason}`) : ['None.']),
  '',
];
fs.writeFileSync(REPORT_MD, lines.join('\n'), 'utf8');

console.log(JSON.stringify({
  ok: true,
  changed_notes: changes.length,
  skipped_files: skipped.length,
  report_json: path.relative(REPO, REPORT_JSON).replace(/\\/g, '/'),
  report_md: path.relative(REPO, REPORT_MD).replace(/\\/g, '/'),
}, null, 2));
