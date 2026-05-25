# AGENTS.md — HUNTS Repo Execution Orders

## Purpose Of This File

This file controls how Codex must work inside this repository.

Codex must read this file before making changes. This file exists because the project has lost time to half-finished rebuilds, context drift, placeholder files, unvalidated outputs, and task switching.

The rule is simple:

**Finish the assigned step completely before moving to another step.**

No guessing.  
No drifting.  
No abstract scaffolding.  
No starting over unless explicitly instructed.  
No publishing broken outputs.  
No modifying website feeds before the truth-source databases are validated.

---

# 1. Non-Negotiable Mission

This repo is being rebuilt around verified truth-source databases first.

The current priority is not the website.  
The current priority is not a black-box prediction model.  
The current priority is not patching the old materializer.  
The current priority is not creating a pretty output file that is secretly built on weak data.

The mission is:

1. Build verified source inventories.
2. Promote only trusted sources.
3. Extract only promoted sources.
4. Normalize draw and harvest truth databases.
5. Validate every truth database.
6. Build comparison engines.
7. Build deterministic draw rules.
8. Only then consider prediction models.
9. Only then feed or publish website-facing files.

The project must produce defensible, traceable data. Every final number must be explainable back to its original source.

# 2. Repo Location

Local repo path:

`C:\Users\tyler\Desktop\GitHub\HUNTS`

---

# 3. Required Codex Behavior

Codex is in coding mode.

When Codex is assigned a task, Codex must:

- implement the task
- run the task
- validate the result
- fix failures
- write required outputs
- update `WORK_LOG.md`
- commit the changes
- stop

Codex must not merely draft plans.

Codex must not leave TODO-only files.

Codex must not create empty modules.

Codex must not create abstract scaffolding without executable code.

Codex must not create placeholder-only files, placeholder-only logic, or placeholder-only reports that merely make a phase look started.

Codex must carry the assigned project step through implementation, validation, artifact generation, and closeout before moving on.

Codex must not start over halfway through a task.

Codex must not switch tasks unless blocked.

Codex must not hide failures.

Codex must not mark a task complete unless the requested outputs exist and validation has run.

Codex must not claim success if validation was skipped.

Codex must not say a task is “ready” when it only created scaffolding.

Codex must not create multiple competing versions of the same pipeline.

If a task cannot be completed, Codex must stop and report:

- exact blocker
- exact file, line, or error
- what was completed
- what remains
- safest next step

---

# 4. Required Start Of Every Codex Session

Before coding, Codex must read this file and any relevant root project documents.

Codex must read these files if present:

- `AGENTS.md`
- `WORK_LOG.md`
- `Canonical JSON rules.md`
- `HARVEST_AND_REPORT_YEAR_RULES.md`
- `HYBRID_ML_V1.md`
- `HYBRID_ML_V1_ROLLOUT.md`
- `LOCKED_CANONICAL_2026.md`

Then Codex must state:

- Current completed step
- Assigned step
- Files Codex will modify
- Files Codex will not modify
- Validation Codex will run
- Stop condition

Codex must not start coding until those items are clear.

---

# 5. Current Known Progress

## Step 1 — Raw Source Inventory

Complete.

Tool created:

- `engine/utah/quality/inventory_raw_pdfs.py`

Outputs created:

- `data_model/quality/raw_pdf_inventory.csv`
- `data_model/quality/raw_pdf_inventory.json`
- `data_model/quality/raw_pdf_inventory_report.json`

Known result:

- Total inventoried files: 1286

Inventory included:

- PDF page counts when readable
- duplicate sha256 checks
- same filename with different sha256 checks
- missing inferred year checks
- unknown report type checks
- no value parsing

No values were parsed during Step 1.

## Step 1B — Raw Inventory Audit

Complete.

Outputs created:

- `data_model/quality/raw_pdf_inventory_audit.csv`
- `data_model/quality/raw_pdf_inventory_audit_report.json`

Known result:

- Total files audited: 1286
- Promoted quality sources: 253
- Promoted draw sources: 204
- Held/review sources: 829
- Duplicate pressure: 296 files held as duplicates
- Unreadable PDFs: 13
- Review required: 489
- Missing year inference: 27

No values were extracted during Step 1B.

---

# 6. Current Next Required Step

## Step 1C — Promoted Source Manifests

Unless the user explicitly assigns a different task, Codex must proceed with Step 1C next.

Input:

- `data_model/quality/raw_pdf_inventory_audit.csv`

Codex must create:

- `data_model/quality/promoted_quality_sources.csv`
- `data_model/quality/promoted_draw_sources.csv`
- `data_model/quality/promoted_source_summary.json`

For `promoted_quality_sources.csv`, include only rows where:

- `promotion_status = PROMOTE`
- `quality_engine_use = YES`

For `promoted_draw_sources.csv`, include only rows where:

- `promotion_status = PROMOTE`
- `draw_engine_use = YES`

Required output columns:

- `source_file`
- `source_sha256`
- `inferred_species`
- `inferred_year`
- `source_class`
- `report_type`
- `file_size_bytes`
- `page_count`
- `extraction_priority`
- `extraction_strategy`
- `confidence`
- `reason`

Allowed `extraction_priority` values:

- `HIGH`
- `MEDIUM`
- `LOW`

Allowed `extraction_strategy` values:

- `structured_table`
- `wide_year_table`
- `text_parse`
- `manual_review_needed`

Allowed `confidence` values:

- `HIGH`
- `MEDIUM`
- `LOW`

Step 1C must not:

- extract values
- parse PDFs
- normalize truth databases
- build prediction outputs
- modify website files
- modify `public_client_engine.csv`
- modify `engine/utah/materialize_engine.py`

Step 1C is not complete unless:

- all three requested output files exist
- row counts match the promoted source counts from the audit
- validation confirms no duplicate source rows
- validation confirms no non-promoted sources leaked into the manifests
- `WORK_LOG.md` is updated
- changes are committed

---

# 7. Source Classification Rules

Required source classes:

- `harvest_results`
- `draw_results`
- `permit_data`
- `biology_population`
- `regulations`
- `map_or_boundary`
- `unknown`

Required promotion statuses:

- `PROMOTE`
- `HOLD_DUPLICATE`
- `HOLD_UNKNOWN_YEAR`
- `HOLD_UNKNOWN_TYPE`
- `HOLD_UNREADABLE_PDF`
- `HOLD_NON_HARVEST`
- `REVIEW_REQUIRED`

Required engine-use flags:

- `quality_engine_use: YES | NO | MAYBE`
- `draw_engine_use: YES | NO | MAYBE`

Promotion rules:

- Harvest reports, age reports, winter population reports, winter trend reports, and herd classification reports may be `quality_engine_use=YES`.
- Draw results, draw odds, applicant reports, bonus point reports, and point ladder reports may be `draw_engine_use=YES`.
- Permit files may be useful, but they must not be treated as harvest results or draw results unless the source data clearly supports that classification.
- Regulations, maps, proclamations, boundary files, guidebooks, and general descriptive files should usually be `quality_engine_use=NO` and `draw_engine_use=NO`.
- Duplicate sha256 files must not all promote. Promote one canonical copy and hold duplicates.
- Unknown report type must not auto-promote.
- Missing year must not auto-promote unless the year can be inferred confidently from path, filename, or report title.

---

# 8. Year Rules

For draw odds, draw results, and harvest report files:

- `reported_hunt_year` = the year the hunt or harvest actually occurred
- `model_target_year` = `reported_hunt_year + 1`

Folder year is storage/provenance context only.

Codex must always store:

- `publish_year`
- `reported_hunt_year_inferred`
- `model_target_year`

Codex must flag true anomalies:

- reported year cannot be inferred
- reported year appears in the future relative to storage year

Codex must not confuse legacy file names containing `draw_odds` with prediction outputs. Many legacy files named `draw_odds` are actually historical draw results inputs for the next prediction year.

---

# 9. Truth Database Architecture

The final truth-source architecture is:

```text
data_truth/
  draw_results_truth/
    raw_inventory/
    extracted/
    normalized/
    validation/
  harvest_results_truth/
    raw_inventory/
    extracted/
    normalized/
    validation/
  crosswalk_truth/
    normalized/
    validation/
  comparison_outputs/
    validation/

---

# Runtime / Reference CSV Roles

Codex must classify runtime/reference CSVs correctly.

## hunt_master_enriched.csv

Use as:

- current enriched hunt reference
- current hunt-code universe
- species/hunt name/weapon/hunt type/access reference
- CWMU vs Public reference
- 2026 permit overlay reference
- 2025 harvest enrichment reference

Do not use as raw harvest truth.

## point_ladder_view.csv

Use as:

- point ladder reference
- hunt_code + residency + points structure
- 2026 permit/ladder validation reference

Do not use as raw draw truth.

## draw_reality_engine.csv

Use as:

- historical draw-results reference
- draw truth/backtesting source candidate
- source_file/page_number traceability source

Must be keyed by:

- hunt_code
- year
- residency
- points

Do not use as current 2026 hunt-code universe without filtering.

## draw_reality_view.csv

Use as:

- frontend/display view only
- sanity comparison only

Do not use as source truth.
Do not use as hunt-code universe.
Do not use for extraction validation.

---

# Research Library Mapping Law

Every research-library document or row created from this point forward must carry explicit hunt-code mapping fields.

Required columns:

- `hunt_code`
- `boundary_id`
- `hunt_code_mapping_status`
- `boundary_id_mapping_status`
- `candidate_hunt_code`
- `candidate_boundary_id`

Rules:

- `hunt_code` and `boundary_id` are reviewed truth fields.
- Candidate fields are evidence only and must not feed runtime, prediction, draw, harvest, or website outputs as truth.
- Blank reviewed fields are allowed only when the mapping status explains why they are blank.
- Old-prefix, private-land, conservation, and document-level matches must flow through the current-to-historical crosswalk before promotion.
- Fuzzy reconciliation output is review evidence, not a promoted mapping.
- Document-level source rows must be extracted into per-hunt-code rows before promotion.




