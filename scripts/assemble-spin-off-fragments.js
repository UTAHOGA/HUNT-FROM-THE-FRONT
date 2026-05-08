const fs = require('fs');
const path = require('path');

const repoRoot = process.cwd();

const sources = [
  {
    name: 'phase2_export',
    root: path.join(repoRoot, '_exports', 'spin_off_cleanup_phase2_20260508'),
    direct: true,
  },
  {
    name: 'bulk_pages_dist_export',
    root: path.join(repoRoot, '_exports', 'spin_off_cleanup_20260508', 'pages-dist'),
    direct: false,
  },
];

const directAllowPrefixes = [
  'canonical/',
  'data/',
  'generated/pages/',
  'schemas/',
  'lib/canonical/',
];

const pagesDistMap = [
  {
    src: 'data/hunt-master-canonical-2026-foundation.json',
    dst: 'data/hunt-master-canonical-2026-foundation.json',
  },
  {
    src: 'data/hunt-master-canonical-2026-source-of-truth.json',
    dst: 'data/hunt-master-canonical-2026-source-of-truth.json',
  },
];

function exists(p) {
  try {
    fs.accessSync(p, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function walkFiles(rootDir) {
  const out = [];
  if (!exists(rootDir)) return out;
  const stack = [rootDir];
  while (stack.length) {
    const cur = stack.pop();
    const ents = fs.readdirSync(cur, { withFileTypes: true });
    for (const ent of ents) {
      const abs = path.join(cur, ent.name);
      if (ent.isDirectory()) stack.push(abs);
      else if (ent.isFile()) out.push(abs);
    }
  }
  return out;
}

function fileHashQuick(abs) {
  const b = fs.readFileSync(abs);
  let h = 0;
  for (let i = 0; i < b.length; i++) h = (h * 31 + b[i]) >>> 0;
  return h.toString(16);
}

function parseJson(abs) {
  try {
    return { ok: true, value: JSON.parse(fs.readFileSync(abs, 'utf8')) };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
}

function validateCanonicalShape(dstRel, json) {
  if (dstRel === 'hunt-master-canonical-2026.json') {
    return !!(json && Array.isArray(json.hunt_catalog) && json.hunt_catalog.length >= 1300);
  }
  if (dstRel === 'canonical/hunt-planner-2026.json' || dstRel === 'generated/pages/hunt-planner.json') {
    return !!(json && Array.isArray(json.hunt_catalog) && json.hunt_catalog.length >= 1300);
  }
  if (dstRel.startsWith('data/hunt-master-canonical-2026-') && dstRel.endsWith('.json')) {
    return Array.isArray(json) && json.length >= 1300;
  }
  return true;
}

function shouldConsiderDirect(rel) {
  if (!rel.endsWith('.json') && !rel.endsWith('.js') && !rel.endsWith('.md')) return false;
  return directAllowPrefixes.some((p) => rel.startsWith(p));
}

function gatherCandidates() {
  const candidates = [];

  for (const src of sources) {
    if (!exists(src.root)) continue;
    if (src.direct) {
      const files = walkFiles(src.root);
      for (const abs of files) {
        const rel = path.relative(src.root, abs).replace(/\\/g, '/');
        if (!shouldConsiderDirect(rel)) continue;
        candidates.push({
          sourceName: src.name,
          sourceAbs: abs,
          sourceRel: rel,
          destRel: rel,
        });
      }
    } else {
      for (const m of pagesDistMap) {
        const abs = path.join(src.root, m.src);
        if (!exists(abs)) continue;
        candidates.push({
          sourceName: src.name,
          sourceAbs: abs,
          sourceRel: m.src,
          destRel: m.dst,
        });
      }
    }
  }
  return candidates;
}

function promote() {
  const now = new Date().toISOString();
  const candidates = gatherCandidates();
  const decisions = [];
  const byDest = new Map();

  for (const c of candidates) {
    if (!byDest.has(c.destRel)) byDest.set(c.destRel, []);
    byDest.get(c.destRel).push(c);
  }

  const promoted = [];
  const skipped = [];

  for (const [destRel, opts] of byDest.entries()) {
    let best = null;
    for (const o of opts) {
      const st = fs.statSync(o.sourceAbs);
      const p = parseJson(o.sourceAbs);
      const isJson = o.sourceAbs.toLowerCase().endsWith('.json');
      if (isJson && !p.ok) {
        skipped.push({
          destRel,
          source: o.sourceName,
          sourceRel: o.sourceRel,
          reason: `invalid_json: ${p.error}`,
        });
        continue;
      }
      if (isJson && !validateCanonicalShape(destRel, p.value)) {
        skipped.push({
          destRel,
          source: o.sourceName,
          sourceRel: o.sourceRel,
          reason: 'fails_shape_guardrail',
        });
        continue;
      }
      const cand = {
        ...o,
        mtimeMs: st.mtimeMs,
        size: st.size,
      };
      if (!best || cand.mtimeMs > best.mtimeMs) best = cand;
    }

    if (!best) continue;
    const dstAbs = path.join(repoRoot, destRel);
    const dstExists = exists(dstAbs);
    const srcHash = fileHashQuick(best.sourceAbs);
    let dstHash = null;
    if (dstExists) dstHash = fileHashQuick(dstAbs);

    if (dstExists && srcHash === dstHash) {
      decisions.push({
        destRel,
        action: 'already_identical',
        source: best.sourceName,
        sourceRel: best.sourceRel,
      });
      continue;
    }

    const dstMtimeMs = dstExists ? fs.statSync(dstAbs).mtimeMs : -1;
    if (dstExists && dstMtimeMs >= best.mtimeMs) {
      decisions.push({
        destRel,
        action: 'kept_root_newer',
        source: best.sourceName,
        sourceRel: best.sourceRel,
      });
      continue;
    }

    fs.mkdirSync(path.dirname(dstAbs), { recursive: true });
    fs.copyFileSync(best.sourceAbs, dstAbs);
    promoted.push({
      destRel,
      source: best.sourceName,
      sourceRel: best.sourceRel,
      sourceSize: best.size,
    });
    decisions.push({
      destRel,
      action: 'promoted_from_export',
      source: best.sourceName,
      sourceRel: best.sourceRel,
    });
  }

  const report = {
    generated_at: now,
    source_roots: sources.map((s) => ({ name: s.name, root: path.relative(repoRoot, s.root).replace(/\\/g, '/') })),
    candidates_total: candidates.length,
    promoted_count: promoted.length,
    skipped_count: skipped.length,
    promoted,
    skipped,
    decisions,
  };

  const jsonOut = path.join(repoRoot, 'canonical', 'spin-off-fragment-assembly-20260508.json');
  const mdOut = path.join(repoRoot, 'docs', 'spin-off-fragment-assembly-20260508.md');
  fs.mkdirSync(path.dirname(jsonOut), { recursive: true });
  fs.mkdirSync(path.dirname(mdOut), { recursive: true });
  fs.writeFileSync(jsonOut, JSON.stringify(report, null, 2) + '\n', 'utf8');

  const lines = [];
  lines.push('# Spin-Off Fragment Assembly (2026-05-08)');
  lines.push('');
  lines.push(`Generated: ${now}`);
  lines.push('');
  lines.push('## Summary');
  lines.push(`- Candidates considered: ${report.candidates_total}`);
  lines.push(`- Promoted from exports: ${report.promoted_count}`);
  lines.push(`- Skipped invalid/guardrail failures: ${report.skipped_count}`);
  lines.push('');
  lines.push('## Promoted Files');
  if (promoted.length === 0) lines.push('- None (root files already newer/authoritative).');
  for (const p of promoted) lines.push(`- \`${p.destRel}\` <= ${p.source}:\`${p.sourceRel}\``);
  lines.push('');
  lines.push('## Decision Notes');
  const noteCounts = {};
  for (const d of decisions) noteCounts[d.action] = (noteCounts[d.action] || 0) + 1;
  for (const [k, v] of Object.entries(noteCounts)) lines.push(`- ${k}: ${v}`);
  lines.push('');
  lines.push('See machine-readable report:');
  lines.push('- `canonical/spin-off-fragment-assembly-20260508.json`');
  fs.writeFileSync(mdOut, lines.join('\n') + '\n', 'utf8');

  console.log(JSON.stringify({
    ok: true,
    candidates_total: report.candidates_total,
    promoted_count: report.promoted_count,
    report_json: 'canonical/spin-off-fragment-assembly-20260508.json',
    report_md: 'docs/spin-off-fragment-assembly-20260508.md',
  }, null, 2));
}

promote();
