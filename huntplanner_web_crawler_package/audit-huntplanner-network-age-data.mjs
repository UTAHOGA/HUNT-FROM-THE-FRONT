#!/usr/bin/env node
/**
 * Utah DWR Hunt Planner network / ArcGIS age-data crawler
 *
 * Purpose:
 * - Opens https://dwrapps.utah.gov/huntboundary/
 * - Captures network calls
 * - Probes ArcGIS FeatureServer / MapServer endpoints
 * - Searches for average-harvest-age / mean-age / percent-5+ / tooth-age style fields
 * - Separates animal-age terms from "average days hunted" false positives
 *
 * Usage:
 *   cd C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER
 *   npm install -D playwright
 *   npx playwright install chromium
 *   node .\scripts\audit-huntplanner-network-age-data.mjs
 *
 * Outputs:
 *   processed_data/audits/huntplanner_network_age_audit.json
 *   processed_data/audits/huntplanner_network_age_audit.csv
 *   processed_data/audits/huntplanner_arcgis_services.csv
 *   processed_data/audits/huntplanner_age_field_hits.csv
 *   processed_data/audits/huntplanner_network_urls.txt
 */

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const ROOT = process.cwd();
const OUT_DIR = path.join(ROOT, "processed_data", "audits");
fs.mkdirSync(OUT_DIR, { recursive: true });

const TARGET = "https://dwrapps.utah.gov/huntboundary/";

const AGE_TERMS = [
  "average age",
  "avg age",
  "mean age",
  "harvest age",
  "age harvested",
  "average_harvest_age",
  "mean_age",
  "avg_age",
  "percent_5plus",
  "percent 5",
  "% ≥ 5",
  "% >= 5",
  "adult male",
  "adult female",
  "cementum",
  "annuli",
  "tooth",
  "teeth"
];

const FALSE_POSITIVE_AGE_TERMS = [
  "average days",
  "avg days",
  "mean days",
  "days hunted",
  "hunter days",
  "pursuit days"
];

const HARVEST_TERMS = [
  "harvest",
  "success",
  "hunters afield",
  "hunters",
  "mean days",
  "average days",
  "satisfaction",
  "permits",
  "quota",
  "hunt number",
  "hunt_code",
  "hunt code",
  "boundary",
  "unit name",
  "species"
];

const INTERACTION_TARGETS = [
  "Find a hunt",
  "Hunts as table view",
  "Add map data layers",
  "CWMU areas",
  "Species Habitat Layers",
  "Wildlife management areas",
  "Walk-in access areas",
  "Land ownership",
  "Administrative boundaries",
  "Draw odds",
  "Harvest",
  "Boundaries",
  "About"
];

function norm(value) {
  return String(value ?? "").toLowerCase();
}

function csvEscape(value) {
  const s = String(value ?? "");
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function writeCsv(file, rows, fields) {
  const lines = [];
  lines.push(fields.map(csvEscape).join(","));
  for (const row of rows) {
    lines.push(fields.map((f) => csvEscape(row[f])).join(","));
  }
  fs.writeFileSync(file, lines.join("\n"), "utf8");
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function termHits(text, terms) {
  const lower = norm(text);
  return terms.filter((term) => lower.includes(norm(term)));
}

function maybeArcgis(url) {
  return /arcgis|FeatureServer|MapServer|\/query\b/i.test(url);
}

function stripQuery(url) {
  try {
    const u = new URL(url);
    return `${u.origin}${u.pathname}`;
  } catch {
    return String(url).split("?")[0];
  }
}

function serviceRoot(url) {
  const clean = stripQuery(url);
  const m = clean.match(/^(.*?(?:FeatureServer|MapServer))(?:\/(\d+))?/i);
  if (!m) return null;
  return {
    root: m[1],
    layerId: m[2] ?? null,
    type: /FeatureServer/i.test(m[1]) ? "FeatureServer" : "MapServer"
  };
}

async function fetchJson(url) {
  try {
    const res = await fetch(url);
    const text = await res.text();
    try {
      return { ok: res.ok, status: res.status, text, json: JSON.parse(text) };
    } catch {
      return { ok: res.ok, status: res.status, text, json: null };
    }
  } catch (err) {
    return { ok: false, status: "", text: String(err), json: null };
  }
}

async function safeClick(page, label) {
  const locators = [
    page.getByText(label, { exact: false }),
    page.locator(`text=${label}`)
  ];

  for (const locator of locators) {
    try {
      const count = await locator.count();
      if (count > 0) {
        await locator.first().click({ timeout: 3500 });
        await page.waitForTimeout(1500);
        return true;
      }
    } catch {
      // keep trying other selector strategies
    }
  }
  return false;
}

async function collectClickableText(page) {
  try {
    return await page.evaluate(() => {
      const nodes = [...document.querySelectorAll("button, a, [role='button'], .esri-widget, .mat-button, .mat-list-item")];
      return nodes
        .map((el) => (el.innerText || el.textContent || "").trim())
        .filter(Boolean)
        .slice(0, 500);
    });
  } catch {
    return [];
  }
}

const captured = [];
const responseBodies = [];
const urlSet = new Set();

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1200 },
  ignoreHTTPSErrors: true,
  userAgent: "Mozilla/5.0 HuntBuilderAudit/1.0"
});
const page = await context.newPage();

page.on("response", async (response) => {
  const url = response.url();
  urlSet.add(url);

  const headers = response.headers();
  const contentType = headers["content-type"] || "";
  const row = {
    url,
    status: response.status(),
    content_type: contentType,
    arcgis_like: maybeArcgis(url) ? "true" : "false",
    age_term_hits: "",
    false_positive_age_hits: "",
    harvest_term_hits: "",
    body_sample: ""
  };

  try {
    if (
      /json|text|javascript|html|csv|xml/i.test(contentType) ||
      maybeArcgis(url) ||
      /hunt|boundary|query|table|map|layer|feature/i.test(url)
    ) {
      const body = await response.text();
      row.age_term_hits = termHits(body, AGE_TERMS).join("|");
      row.false_positive_age_hits = termHits(body, FALSE_POSITIVE_AGE_TERMS).join("|");
      row.harvest_term_hits = termHits(body, HARVEST_TERMS).join("|");
      row.body_sample = body.replace(/\s+/g, " ").slice(0, 1000);

      responseBodies.push({
        url,
        content_type: contentType,
        body,
        age_hits: row.age_term_hits,
        false_positive_age_hits: row.false_positive_age_hits,
        harvest_hits: row.harvest_term_hits
      });
    }
  } catch {
    // Some responses cannot be read because of browser internals / CORS / binary bodies.
  }

  captured.push(row);
});

await page.goto(TARGET, { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(4000);

const clickableTextBefore = await collectClickableText(page);

for (const label of INTERACTION_TARGETS) {
  await safeClick(page, label);
}

await page.mouse.wheel(0, 2000);
await page.waitForTimeout(3000);

const clickableTextAfter = await collectClickableText(page);

await browser.close();

const urls = unique([...urlSet]).sort();
const arcgisObjects = urls.map(serviceRoot).filter(Boolean);
const serviceRoots = unique(arcgisObjects.map((x) => x.root));

const serviceRows = [];
const fieldHitRows = [];
const layerRows = [];

for (const root of serviceRoots) {
  const metaUrl = `${root}?f=json`;
  const meta = await fetchJson(metaUrl);

  const serviceInfo = {
    service_root: root,
    metadata_status: meta.status,
    service_type: /FeatureServer/i.test(root) ? "FeatureServer" : "MapServer",
    service_name: meta.json?.serviceDescription || meta.json?.name || meta.json?.documentInfo?.Title || "",
    layer_count: Array.isArray(meta.json?.layers) ? meta.json.layers.length : "",
    table_count: Array.isArray(meta.json?.tables) ? meta.json.tables.length : "",
    age_term_hits: termHits(meta.text, AGE_TERMS).join("|"),
    false_positive_age_hits: termHits(meta.text, FALSE_POSITIVE_AGE_TERMS).join("|"),
    harvest_term_hits: termHits(meta.text, HARVEST_TERMS).join("|")
  };
  serviceRows.push(serviceInfo);

  const layers = [
    ...(Array.isArray(meta.json?.layers) ? meta.json.layers : []),
    ...(Array.isArray(meta.json?.tables) ? meta.json.tables : [])
  ];

  for (const layer of layers) {
    const layerId = layer.id;
    if (layerId === undefined || layerId === null) continue;

    const layerUrl = `${root}/${layerId}?f=json`;
    const layerMeta = await fetchJson(layerUrl);
    const fields = Array.isArray(layerMeta.json?.fields) ? layerMeta.json.fields : [];

    layerRows.push({
      service_root: root,
      layer_id: layerId,
      layer_name: layer.name || layerMeta.json?.name || "",
      field_count: fields.length,
      metadata_status: layerMeta.status,
      age_term_hits: termHits(layerMeta.text, AGE_TERMS).join("|"),
      false_positive_age_hits: termHits(layerMeta.text, FALSE_POSITIVE_AGE_TERMS).join("|"),
      harvest_term_hits: termHits(layerMeta.text, HARVEST_TERMS).join("|")
    });

    for (const f of fields) {
      const combined = `${f.name || ""} ${f.alias || ""} ${f.type || ""}`;
      const ageHits = termHits(combined, AGE_TERMS);
      const falsePositiveHits = termHits(combined, FALSE_POSITIVE_AGE_TERMS);
      const harvestHits = termHits(combined, HARVEST_TERMS);

      if (ageHits.length || falsePositiveHits.length || harvestHits.length) {
        fieldHitRows.push({
          service_root: root,
          layer_id: layerId,
          layer_name: layer.name || layerMeta.json?.name || "",
          field_name: f.name || "",
          field_alias: f.alias || "",
          field_type: f.type || "",
          hit_source: "field_metadata",
          age_term_hits: ageHits.join("|"),
          false_positive_age_hits: falsePositiveHits.join("|"),
          harvest_term_hits: harvestHits.join("|"),
          sample_value: "",
          sample_url: layerUrl
        });
      }
    }

    const sampleUrl = `${root}/${layerId}/query?where=1%3D1&outFields=*&returnGeometry=false&resultRecordCount=10&f=json`;
    const sample = await fetchJson(sampleUrl);
    const features = Array.isArray(sample.json?.features) ? sample.json.features : [];

    for (const feature of features) {
      const attrs = feature.attributes || {};
      for (const [k, v] of Object.entries(attrs)) {
        const combined = `${k} ${v}`;
        const ageHits = termHits(combined, AGE_TERMS);
        const falsePositiveHits = termHits(combined, FALSE_POSITIVE_AGE_TERMS);
        const harvestHits = termHits(combined, HARVEST_TERMS);

        if (ageHits.length || falsePositiveHits.length || harvestHits.length) {
          fieldHitRows.push({
            service_root: root,
            layer_id: layerId,
            layer_name: layer.name || layerMeta.json?.name || "",
            field_name: k,
            field_alias: "",
            field_type: "sample_attribute",
            hit_source: "sample_attribute",
            age_term_hits: ageHits.join("|"),
            false_positive_age_hits: falsePositiveHits.join("|"),
            harvest_term_hits: harvestHits.join("|"),
            sample_value: String(v ?? "").slice(0, 300),
            sample_url: sampleUrl
          });
        }
      }
    }
  }
}

const ageResponseHits = responseBodies
  .filter((x) => x.age_hits)
  .map((x) => ({
    url: x.url,
    content_type: x.content_type,
    age_term_hits: x.age_hits,
    false_positive_age_hits: x.false_positive_age_hits,
    harvest_term_hits: x.harvest_hits,
    body_sample: x.body.slice(0, 1000).replace(/\s+/g, " ")
  }));

const harvestResponseHits = responseBodies
  .filter((x) => x.harvest_hits)
  .map((x) => ({
    url: x.url,
    content_type: x.content_type,
    age_term_hits: x.age_hits,
    false_positive_age_hits: x.false_positive_age_hits,
    harvest_term_hits: x.harvest_hits,
    body_sample: x.body.slice(0, 1000).replace(/\s+/g, " ")
  }));

const trueAgeFieldHits = fieldHitRows.filter((r) => r.age_term_hits);
const falsePositiveOnlyAgeHits = fieldHitRows.filter((r) => !r.age_term_hits && r.false_positive_age_hits);

const likelyAnimalAgeHits = trueAgeFieldHits.filter((r) => {
  const hay = `${r.field_name} ${r.field_alias} ${r.sample_value}`.toLowerCase();
  return !FALSE_POSITIVE_AGE_TERMS.some((t) => hay.includes(t));
});

const audit = {
  created_at: new Date().toISOString(),
  target: TARGET,
  captured_url_count: urls.length,
  captured_response_count: captured.length,
  captured_age_response_hits: ageResponseHits.length,
  captured_harvest_response_hits: harvestResponseHits.length,
  arcgis_service_count: serviceRoots.length,
  arcgis_layer_or_table_count: layerRows.length,
  arcgis_field_or_sample_hit_count: fieldHitRows.length,
  true_age_field_hit_count: trueAgeFieldHits.length,
  likely_animal_age_hit_count: likelyAnimalAgeHits.length,
  false_positive_average_days_hit_count: falsePositiveOnlyAgeHits.length,
  interaction_targets_attempted: INTERACTION_TARGETS,
  clickable_text_before_sample: clickableTextBefore.slice(0, 100),
  clickable_text_after_sample: clickableTextAfter.slice(0, 100),
  conclusion: likelyAnimalAgeHits.length
    ? "Potential animal-age fields were found. Review huntplanner_age_field_hits.csv before using any field."
    : "No likely public average-harvest-age field was found in captured Hunt Planner network calls or sampled ArcGIS layer fields.",
  outputs: {
    audit_json: "huntplanner_network_age_audit.json",
    audit_csv: "huntplanner_network_age_audit.csv",
    arcgis_services_csv: "huntplanner_arcgis_services.csv",
    arcgis_layers_csv: "huntplanner_arcgis_layers.csv",
    age_field_hits_csv: "huntplanner_age_field_hits.csv",
    network_urls_txt: "huntplanner_network_urls.txt"
  }
};

fs.writeFileSync(
  path.join(OUT_DIR, "huntplanner_network_age_audit.json"),
  JSON.stringify(
    {
      audit,
      age_response_hits: ageResponseHits,
      harvest_response_hits: harvestResponseHits.slice(0, 250),
      service_roots: serviceRoots
    },
    null,
    2
  ),
  "utf8"
);

writeCsv(path.join(OUT_DIR, "huntplanner_network_age_audit.csv"), captured, [
  "url",
  "status",
  "content_type",
  "arcgis_like",
  "age_term_hits",
  "false_positive_age_hits",
  "harvest_term_hits",
  "body_sample"
]);

writeCsv(path.join(OUT_DIR, "huntplanner_arcgis_services.csv"), serviceRows, [
  "service_root",
  "metadata_status",
  "service_type",
  "service_name",
  "layer_count",
  "table_count",
  "age_term_hits",
  "false_positive_age_hits",
  "harvest_term_hits"
]);

writeCsv(path.join(OUT_DIR, "huntplanner_arcgis_layers.csv"), layerRows, [
  "service_root",
  "layer_id",
  "layer_name",
  "field_count",
  "metadata_status",
  "age_term_hits",
  "false_positive_age_hits",
  "harvest_term_hits"
]);

writeCsv(path.join(OUT_DIR, "huntplanner_age_field_hits.csv"), fieldHitRows, [
  "service_root",
  "layer_id",
  "layer_name",
  "field_name",
  "field_alias",
  "field_type",
  "hit_source",
  "age_term_hits",
  "false_positive_age_hits",
  "harvest_term_hits",
  "sample_value",
  "sample_url"
]);

fs.writeFileSync(path.join(OUT_DIR, "huntplanner_network_urls.txt"), urls.join("\n"), "utf8");

console.log(JSON.stringify(audit, null, 2));
