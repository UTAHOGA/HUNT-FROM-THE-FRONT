# Hunt Planner Network / ArcGIS Age-Data Crawler

This package contains a Playwright-based crawler for:

`https://dwrapps.utah.gov/huntboundary/`

It captures network calls, probes ArcGIS FeatureServer/MapServer endpoints, samples layer fields and attributes, and searches for animal-age terms such as:

- average age
- mean age
- harvest age
- average_harvest_age
- mean_age
- percent_5plus
- adult male / adult female
- cementum / annuli / tooth / teeth

It also flags likely false positives such as:

- average days
- mean days hunted
- hunter days

## Install

From your repo root:

```powershell
cd C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER

npm install -D playwright
npx playwright install chromium
```

Copy the script into:

```text
scripts/audit-huntplanner-network-age-data.mjs
```

Run:

```powershell
node .\scripts\audit-huntplanner-network-age-data.mjs
```

## Outputs

```text
processed_data/audits/huntplanner_network_age_audit.json
processed_data/audits/huntplanner_network_age_audit.csv
processed_data/audits/huntplanner_arcgis_services.csv
processed_data/audits/huntplanner_arcgis_layers.csv
processed_data/audits/huntplanner_age_field_hits.csv
processed_data/audits/huntplanner_network_urls.txt
```

## Interpretation

If `likely_animal_age_hit_count` is `0`, the Hunt Planner/ArcGIS endpoints sampled by the crawler did not expose usable average-harvest-age data.

If hits only appear in `false_positive_age_hits`, they are probably things like `Average Days Hunted`, not animal age.

Do not populate `average_harvest_age` from `average days`, `mean days`, or `days hunted`.
