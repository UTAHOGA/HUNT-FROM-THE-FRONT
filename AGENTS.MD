###### AGENTS.md — HUNT-BUILDER Repo Execution Orders

###### Generated: 2026-05-29T01:25:36+00:00

###### Purpose Of This File

###### This file controls how Codex must work inside this repository.

###### Codex must read this file before making changes. This file exists because the project has lost time to half-finished rebuilds, context drift, placeholder files, unvalidated outputs, duplicated fragments, unreviewed generated outputs, and task switching.

###### The rule is simple:

###### **Finish the assigned step completely before moving to another step.**

No guessing.
No drifting.
No abstract scaffolding.
No starting over unless explicitly instructed.
No publishing broken outputs.
No modifying website feeds before truth-source databases are validated.
No treating management-plan policy context as raw harvest, draw, permit, or prediction truth.
---

###### \---

###### 1\. Non-Negotiable Mission

###### This repo is being rebuilt around verified truth-source databases first.

The current priority is not the website.
The current priority is not a black-box prediction model.
The current priority is not patching the old materializer.
The current priority is not creating a pretty output file that is secretly built on weak data.
---

###### The mission is:

1. ###### Build verified source inventories.
2. ###### Promote only trusted sources.
3. ###### Extract only promoted sources.
4. ###### Normalize draw and harvest truth databases.
5. ###### Validate every truth database.
6. ###### Build comparison engines.
7. ###### Build deterministic draw rules.
8. ###### Build reviewed feature layers only after source truth is validated.
9. ###### Only then consider prediction models.
10. ###### Only then feed or publish website-facing files.

###### The project must produce defensible, traceable data. Every final number must be explainable back to its original source.

###### \---

###### 2\. Repo Location

###### Local repo path:

```text
C:\\Users\\tyler\\Desktop\\GitHub\\HUNT-BUILDER
```
---

###### Related older/source repo paths may exist, but they are not automatically active runtime truth:

```text
C:\\Users\\tyler\\Desktop\\GitHub\\HUNTS
```
---

###### If Codex imports or compares from `HUNTS`, the task must explicitly identify the source path, hash or row count, promotion reason, and target path inside active `HUNT-BUILDER`.

###### \---

###### 3\. Required Codex Behavior

###### Codex is in coding mode.

###### When Codex is assigned a task, Codex must:

1. ###### implement the task
2. ###### run the task
3. ###### validate the result
4. ###### fix failures
5. ###### write required outputs
6. ###### update `WORK\_LOG.md`
7. ###### commit the changes when repository modification was requested
8. ###### stop

###### Codex must not merely draft plans.

###### Codex must not leave TODO-only files.

###### Codex must not create empty modules.

###### Codex must not create abstract scaffolding without executable code.

###### Codex must not create placeholder-only files, placeholder-only logic, or placeholder-only reports that merely make a phase look started.

###### Codex must carry the assigned project step through implementation, validation, artifact generation, and closeout before moving on.

###### Codex must not start over halfway through a task.

###### Codex must not switch tasks unless blocked.

###### Codex must not hide failures.

###### Codex must not mark a task complete unless the requested outputs exist and validation has run.

###### Codex must not claim success if validation was skipped.

###### Codex must not say a task is “ready” when it only created scaffolding.

###### Codex must not create multiple competing versions of the same pipeline.

###### If a task cannot be completed, Codex must stop and report:

* ###### exact blocker
* ###### exact file, line, or error
* ###### what was completed
* ###### what remains
* ###### safest next step

###### \---

###### 4\. Required Start Of Every Codex Session

###### Before coding, Codex must read this file and any relevant root project documents.

###### Codex must read these files if present:

* ###### `AGENTS.md`
* ###### `WORK\_LOG.md`
* ###### `Canonical JSON rules.md`
* ###### `HARVEST\_AND\_REPORT\_YEAR\_RULES.md`
* ###### `HYBRID\_ML\_V1.md`
* ###### `HYBRID\_ML\_V1\_ROLLOUT.md`
* ###### `LOCKED\_CANONICAL\_2026.md`
* ###### `docs/utah\_draw\_routing\_and\_algorithm\_v1.md`
* ###### `docs/utah\_draw\_system\_scope.md`
* ###### `docs/utah\_rules\_sources.md`
* ###### `mule\_deer\_statewide\_plan\_foundational\_reference.md`
* ###### `mule\_deer\_statewide\_plan\_foundational\_reference\_codex\_expanded.md`
* ###### `elk\_statewide\_plan\_foundational\_reference.md`
* ###### `elk\_statewide\_plan\_foundational\_reference\_codex\_expanded.md`

###### Then Codex must state:

* ###### Current completed step
* ###### Assigned step
* ###### Files Codex will modify
* ###### Files Codex will not modify
* ###### Validation Codex will run
* ###### Stop condition

###### Codex must not start coding until those items are clear.

###### If the user explicitly assigns a task, the assigned task controls. If no task is assigned, Codex must not invent a major phase. It must ask for confirmation or continue the last clearly assigned step from `WORK\_LOG.md`.

###### \---

###### 5\. Current Known Progress Baseline

###### The historical baseline below is retained so Codex understands the original rebuild order. The current chronological truth is `WORK\_LOG.md`.

###### Step 1 — Raw Source Inventory

###### Complete.

###### Tool created:

```text
engine/utah/quality/inventory\_raw\_pdfs.py
```
---

###### Outputs created:

```text
data\_model/quality/raw\_pdf\_inventory.csv
data\_model/quality/raw\_pdf\_inventory.json
data\_model/quality/raw\_pdf\_inventory\_report.json
```
---

###### Known result:

```text
Total inventoried files: 1286
```
---

###### Inventory included:

* ###### PDF page counts when readable
* ###### duplicate sha256 checks
* ###### same filename with different sha256 checks
* ###### missing inferred year checks
* ###### unknown report type checks
* ###### no value parsing

###### No values were parsed during Step 1.

###### Step 1B — Raw Inventory Audit

###### Complete.

###### Outputs created:

```text
data\_model/quality/raw\_pdf\_inventory\_audit.csv
data\_model/quality/raw\_pdf\_inventory\_audit\_report.json
```
---

###### Known result:

```text
Total files audited: 1286
Promoted quality sources: 253
Promoted draw sources: 204
Held/review sources: 829
Duplicate pressure: 296 files held as duplicates
Unreadable PDFs: 13
Review required: 489
Missing year inference: 27
```
---

###### No values were extracted during Step 1B.

###### Later Work

###### `WORK\_LOG.md` now contains the complete project chronology after these baseline steps, including:

* ###### source parity audits
* ###### draw truth hardening
* ###### harvest truth hardening
* ###### canonical data chain lock reports
* ###### public library work
* ###### youth reserve and preference ladder modeling
* ###### average-harvest-age extraction and review work
* ###### elk and mule deer plan guardrails

###### Codex must treat `WORK\_LOG.md` as the current chronology and must not revert the project to an obsolete phase.

###### \---

###### 6\. Default Next-Step Rule

###### The user’s explicit instruction always controls the assigned step.

###### If the user gives no explicit task, Codex must:

1. ###### read `WORK\_LOG.md`
2. ###### identify the last completed step
3. ###### report a recommended next step
4. ###### wait for confirmation unless the next step was already assigned

###### Codex must not automatically perform old Step 1C if later work has superseded it.

###### \---

###### 7\. Source Classification Rules

###### Required source classes:

* ###### `harvest\_results`
* ###### `draw\_results`
* ###### `permit\_data`
* ###### `biology\_population`
* ###### `age\_results`
* ###### `management\_plan`
* ###### `regulations`
* ###### `map\_or\_boundary`
* ###### `website\_runtime`
* ###### `public\_export`
* ###### `model\_output`
* ###### `audit\_validation\_report`
* ###### `unknown`

###### Required promotion statuses:

* ###### `PROMOTE`
* ###### `HOLD\_DUPLICATE`
* ###### `HOLD\_UNKNOWN\_YEAR`
* ###### `HOLD\_UNKNOWN\_TYPE`
* ###### `HOLD\_UNREADABLE\_PDF`
* ###### `HOLD\_NON\_HARVEST`
* ###### `REVIEW\_REQUIRED`
* ###### `SOURCE\_LABEL\_LINEAGE\_REVIEW`
* ###### `PROMOTED\_HISTORICAL\_TRUTH`
* ###### `REVIEW\_EVIDENCE\_ONLY`

###### Required engine-use flags:

```text
quality\_engine\_use: YES | NO | MAYBE
draw\_engine\_use: YES | NO | MAYBE
prediction\_engine\_use: YES | NO | MAYBE
website\_public\_use: YES | NO | MAYBE
```
---

###### Promotion rules:

* ###### Harvest reports, age reports, winter population reports, winter trend reports, and herd classification reports may be `quality\_engine\_use=YES`.
* ###### Draw results, draw odds, applicant reports, bonus point reports, and point ladder reports may be `draw\_engine\_use=YES`.
* ###### Permit files may be useful, but they must not be treated as harvest results or draw results unless the source data clearly supports that classification.
* ###### Regulations, maps, proclamations, boundary files, guidebooks, and general descriptive files should usually be `quality\_engine\_use=NO` and `draw\_engine\_use=NO`, unless the assigned task is public library curation.
* ###### Duplicate sha256 files must not all promote. Promote one canonical copy and hold duplicates.
* ###### Unknown report type must not auto-promote.
* ###### Missing year must not auto-promote unless the year can be inferred confidently from path, filename, report title, or page text.
* ###### Management plans are context sources, not raw truth rows.

###### \---

###### 8\. Year Rules

###### For draw odds, draw results, and harvest report files:

```text
reported\_hunt\_year = the year the hunt, draw, or harvest actually occurred
model\_target\_year = reported\_hunt\_year + 1
```
---

###### Folder year is storage/provenance context only.

###### Codex must always store:

* ###### `publish\_year`
* ###### `reported\_hunt\_year\_inferred`
* ###### `model\_target\_year`
* ###### `source\_file`
* ###### `source\_page` when applicable
* ###### `source\_table\_title` when applicable

###### Codex must flag true anomalies:

* ###### reported year cannot be inferred
* ###### reported year appears in the future relative to storage year
* ###### file label implies a different reported year than the internal report title
* ###### normalized row labels do not match anchored source files

###### Codex must not confuse legacy file names containing `draw\_odds` with prediction outputs. Many legacy files named `draw\_odds` are historical draw results inputs for the next prediction year.

###### \---

###### 9\. Truth Database Architecture

###### The final truth-source architecture is:

```text
data\_truth/
  draw\_results\_truth/
    raw\_inventory/
    extracted/
    normalized/
    validation/
  harvest\_results\_truth/
    raw\_inventory/
    extracted/
    normalized/
    validation/
  crosswalk\_truth/
    normalized/
    validation/
  comparison\_outputs/
    validation/
```
---

###### Codex must preserve the separation between:

* ###### harvest truth
* ###### draw truth
* ###### permit truth
* ###### crosswalk truth
* ###### management-plan context
* ###### website/public display files
* ###### predictive outputs

###### Codex must not combine harvest and draw truth unless the assigned step explicitly creates a reviewed feature-combine layer.

###### \---

###### 10\. Runtime / Reference CSV Roles

###### Codex must classify runtime/reference CSVs correctly.

###### `DATABASE.csv`

###### Use as:

* ###### current canonical hunt-code universe
* ###### current canonical boundary-id universe
* ###### current direct DWR Hunt Planner permit/allotment truth where populated
* ###### reviewed historical permit truth where source-lineage fields exist

###### Do not overwrite populated numeric permit/allotment cells from comparison files, inferred values, RAC files, or generated audits.

###### `hunt\_master\_enriched.csv`

###### Use as:

* ###### current enriched hunt reference
* ###### current hunt-code universe support
* ###### species/hunt name/weapon/hunt type/access reference
* ###### CWMU vs public reference
* ###### 2026 permit overlay reference
* ###### 2025 harvest enrichment reference

###### Do not use as raw harvest truth.

###### `point\_ladder\_view.csv`

###### Use as:

* ###### point ladder reference
* ###### hunt\_code + residency + points structure
* ###### 2026 permit/ladder validation reference

###### Do not use as raw draw truth.

###### `draw\_reality\_engine.csv`

###### Use as:

* ###### historical draw-results reference
* ###### draw truth/backtesting source candidate
* ###### source\_file/page\_number traceability source

###### Must be keyed by:

* ###### `hunt\_code`
* ###### `year`
* ###### `residency`
* ###### `points`

###### Do not use as current 2026 hunt-code universe without filtering.

###### `draw\_reality\_view.csv`

###### Use as:

* ###### frontend/display view only
* ###### sanity comparison only

###### Do not use as source truth.

###### Do not use as hunt-code universe.

###### Do not use for extraction validation.

###### `harvest\_master.csv`

###### Use as:

* ###### harvest reference surface
* ###### summary harvest evidence
* ###### current feature support where columns are validated

###### Do not use as the only raw harvest truth if normalized harvest truth packages exist.

###### `harvest\_quality\_features\_all\_years\_by\_hunt\_code.csv`

###### Use as:

* ###### historical harvest-quality feature evidence
* ###### cross-year feature support
* ###### source for rows where average-age fields are populated and validated

###### Do not assume blank age means age is unavailable in source PDFs; check annual report age tables.

###### `harvest\_age\_features\_by\_hunt\_code\_all\_years.csv`

###### Use as:

* ###### canonical reviewed age feature history once built and validated

###### Do not use to overwrite raw harvest truth.

###### `harvest\_age\_features\_by\_hunt\_code\_latest.csv`

###### Use as:

* ###### latest reviewed age feature layer for quality scoring

###### Do not use to modify draw odds or quotas.

###### \---

###### 11\. Research Library Mapping Law

###### Every research-library document or row created from this point forward must carry explicit hunt-code mapping fields.

###### Required columns:

* ###### `hunt\_code`
* ###### `boundary\_id`
* ###### `hunt\_code\_mapping\_status`
* ###### `boundary\_id\_mapping\_status`
* ###### `candidate\_hunt\_code`
* ###### `candidate\_boundary\_id`

###### Rules:

* ###### `hunt\_code` and `boundary\_id` are reviewed truth fields.
* ###### Candidate fields are evidence only and must not feed runtime, prediction, draw, harvest, or website outputs as truth.
* ###### Blank reviewed fields are allowed only when the mapping status explains why they are blank.
* ###### `DATABASE.csv` is the canonical current hunt-code and boundary-id source unless a later reviewed canonical database explicitly replaces it.
* ###### Populated numeric 2026 permit/allotment cells in canonical `DATABASE.csv` are direct Utah DWR Hunt Planner truth and must not be changed or overwritten by comparison files, inferred values, draw reports, RAC files, audit outputs, or rebuilt library/master documents.
* ###### Populated 2025 or older permit fields in `DATABASE.csv` are canonical historical source truth when they carry reviewed source-lineage fields such as `permits\_2025\_source` or `permits\_2025\_draw\_source`; they must not be changed or overwritten by newer comparison files, current-year RAC files, inferred values, audit outputs, or rebuilt library/master documents.
* ###### Populated 2025 or older permit fields without source lineage must be flagged for lineage repair before they are treated as canonical truth.
* ###### In current `DATABASE.csv`, `permits\_2025` is the full populated 2025 historical permit universe.
* ###### In current `DATABASE.csv`, `permits\_2025\_draw` is a narrower bonus-point draw-results subset and must not be described as the full 2025 draw/permit universe.
* ###### Feeder/reference files such as `hunt\_master\_enriched.csv`, `point\_ladder\_view.csv`, canonical JSON, and boundary GeoJSON must be registered as source rows with hashes before they can support alignment work.
* ###### Direct Utah DWR Hunt Planner CSV-folder files are source evidence only until a reviewed promotion step identifies source dates/year context.
* ###### Do not promote 2025 permit values into 2026 available allotment fields unless every imported source used in that promotion has reviewed source-date context.
* ###### Old-prefix, private-land, conservation, and document-level matches must flow through the current-to-historical crosswalk before promotion.
* ###### Fuzzy reconciliation output is review evidence, not a promoted mapping.
* ###### Document-level source rows must be extracted into per-hunt-code rows before promotion.

###### \---

###### 12\. Hunt Planner / ArcGIS Data Boundary

###### A Hunt Planner network/API audit was completed.

###### Codex must treat the finding as standing project knowledge unless a later audit proves otherwise:

```text
Public Hunt Planner / ArcGIS did not expose true average harvest age fields.
```
---

###### Known audit result:

* ###### no public endpoint exposing true `average\_harvest\_age`
* ###### age-term field hits: `0`
* ###### true animal-age fields: not found
* ###### boundary-related fields were present
* ###### false-context terms like `tooth` in JS/setup payloads are not usable data
* ###### no sampled ArcGIS `average days hunted` field either

###### Therefore:

###### Use Hunt Planner / ArcGIS for:

* ###### hunt\_code
* ###### hunt\_number
* ###### hunt\_name
* ###### boundary\_id
* ###### boundary\_name
* ###### geometry
* ###### public map metadata

###### Do not use Hunt Planner / ArcGIS for:

* ###### average\_harvest\_age
* ###### mean\_age
* ###### percent\_5plus
* ###### tooth/cementum age data
* ###### observed harvested-age metrics

###### Average harvest age must come from:

* ###### DWR annual reports
* ###### species annual reports
* ###### age-specific PDFs/tables
* ###### verified historical harvest feature rows with positive animal-age values

###### \---

###### 13\. Average Harvest Age / Age-Quality Feature Rules

###### Age data is a quality-score feature, not a draw-odds or permit-quota feature.

###### Codex must preserve these distinctions:

###### Valid Animal-Age Sources

###### Valid observed animal-age fields include:

* ###### `average\_harvest\_age`
* ###### `average\_age`
* ###### `mean\_age`
* ###### `avg\_age`
* ###### tooth-age / cementum-annuli age tables
* ###### percent 5+ / `% ≥ 5 years old` as a separate age-structure proxy
* ###### percent adult male/female only when clearly labeled as age-structure context

###### Invalid Animal-Age Sources

###### Never use these as animal age:

* ###### `average\_days`
* ###### `average\_days\_hunted`
* ###### `mean\_days`
* ###### `mean\_days\_hunted`
* ###### `hunter\_days`
* ###### `pursuit\_days`
* ###### `days\_afield`
* ###### `success\_rate`
* ###### `hunter\_satisfaction`
* ###### `buck\_to\_doe\_ratio`
* ###### `bull\_to\_cow\_ratio`
* ###### management objective age bands

###### Zero Rule

###### Codex must never fill missing age with `0`.

###### If a zero is discovered in an animal-age field:

* ###### blank the age value
* ###### set `age\_data\_available = false` unless another valid proxy exists
* ###### mark row `BLOCK` or `REVIEW`
* ###### add reason `ZERO\_AGE\_VALUE\_REMOVED`

###### Age Scope

###### Codex must label age source scope:

* ###### `hunt\_code\_direct`
* ###### `unit\_level\_repeated\_to\_hunt\_code`
* ###### `unit\_level\_needs\_hunt\_code\_crosswalk`
* ###### `management\_unit\_level`
* ###### `statewide\_only`
* ###### `source\_context\_review`

###### Age Review Rules

###### PASS only if:

* ###### hunt\_code exists or row is explicitly statewide/context-only
* ###### age value is positive numeric or proxy is clearly separated
* ###### source file/page/table exists
* ###### source scope is clear
* ###### crosswalk confidence is high/medium or unit\_level\_high/unit\_level\_medium
* ###### false age fields were not used

###### REVIEW if:

* ###### source is unit-level and repeated to multiple hunt codes
* ###### source is percent\_5plus only
* ###### crosswalk confidence is low or fuzzy
* ###### current DATABASE match is missing
* ###### historical/current crosswalk needs review

###### BLOCK if:

* ###### average\_harvest\_age is zero
* ###### average\_days or mean\_days was used as age
* ###### no source\_file
* ###### species cannot be identified
* ###### reported\_hunt\_year or model\_target\_year is missing
* ###### hunt\_code is missing without an explicit contextual scope

###### \---

###### 14\. Elk Statewide Plan Reference And Age-Quality Guardrails

###### This section is standing Codex instruction for elk management-plan context and elk age-quality work.

###### Codex must treat the elk statewide plan reference as a **management-policy / harvest-context / quality-structure reference**, not as raw hunt-code harvest truth, not permit truth, not draw-odds truth, and not a source that can directly overwrite `DATABASE.csv`.

###### Required reference files, if present:

* ###### `elk\_statewide\_plan\_foundational\_reference.md`
* ###### `elk\_statewide\_plan\_foundational\_reference\_codex\_expanded.md`
* ###### `elk\_plan\_foundational\_reference.csv`
* ###### `pipeline/RAW/hunt\_unit\_database/elk\_plan.pdf`

###### Codex must read the expanded elk reference before any task involving:

* ###### elk quality scoring
* ###### elk age-quality scoring
* ###### elk limited-entry or premium quality context
* ###### elk permit strategy interpretation
* ###### elk management-plan policy context
* ###### elk public research page explanations
* ###### elk feature engineering from management-plan values

###### Elk Plan Data Classification

###### The elk plan reference contains management-plan context, including:

* ###### general-season opportunity targets
* ###### limited-entry age objective categories
* ###### weapon allocation policy
* ###### demand pressure context
* ###### population objective context
* ###### survival and recruitment context
* ###### habitat treatment targets
* ###### permit-governance rules

###### These values are not raw harvest-result rows.

###### These values are not direct draw-odds truth.

###### These values are not current permit truth.

###### These values are not directly usable as `average\_harvest\_age`.

###### Elk Average-Age Rules

###### Codex must distinguish between:

1. ###### **Observed harvested-age data**

   * ###### Examples: annual report tables titled like `Average age of harvested bull elk on limited-entry units`.
   * ###### Can feed `average\_harvest\_age` when source year, species, unit, and hunt-code crosswalk are reviewed.
2. ###### **Management-plan age objectives**

   * ###### Examples: `6.5-7.0`, `6.0-6.5`, `5.5-6.0`.
   * ###### These are management targets.
   * ###### They must not be written as observed `average\_harvest\_age`.
   * ###### They can be used only as quality-context benchmarks or classification labels.
3. ###### **Average days hunted**

   * ###### This is hunter effort.
   * ###### It is never animal age.
   * ###### It must never populate `average\_harvest\_age`.

###### Elk Plan Values Must Not Override Runtime Truth

###### Codex must not use elk plan values to directly modify:

* ###### `DATABASE.csv`
* ###### 2026 permit fields
* ###### 2026 allotment fields
* ###### draw odds
* ###### `p\_draw`
* ###### max-point/random-pool probabilities
* ###### point-ladder numeric probability fields
* ###### `public\_client\_engine.csv`
* ###### website-facing runtime files

###### Plan values may support:

* ###### research-page explanatory text
* ###### management-context labels
* ###### quality-score context
* ###### policy/reference sidebars
* ###### validation checks
* ###### unit objective comparisons

###### Elk Quality Score Use

###### Age-related elk plan rules may support a quality-score enhancement only when clearly separated from observed harvest age.

###### Allowed derived context fields:

* ###### `elk\_age\_objective\_min`
* ###### `elk\_age\_objective\_max`
* ###### `elk\_age\_objective\_category`
* ###### `elk\_age\_objective\_source = ELK\_STATEWIDE\_PLAN`
* ###### `elk\_age\_objective\_context\_only = true`

###### Observed annual-report age fields must remain separate:

* ###### `average\_harvest\_age`
* ###### `average\_harvest\_age\_source\_file`
* ###### `average\_harvest\_age\_source\_page`
* ###### `average\_harvest\_age\_reported\_year`
* ###### `average\_harvest\_age\_crosswalk\_confidence`

###### If both objective and observed age are present, Codex may compare them, but must not collapse them into one field.

###### Elk Plan Demand And Permit Strategy Use

###### Demand-pressure values such as limited-entry applicants, draw odds, and sellout timing are context values.

###### Codex may use them to explain user demand and research-page demand pressure.

###### Codex must not use them as direct `p\_draw` values.

###### Permit strategy values such as statewide opportunity targets, age categories, weapon allocation percentages, and adaptive opportunity rules are policy context.

###### Codex must not use them to overwrite direct DWR permit truth unless a separate reviewed promotion step explicitly authorizes it.

###### Elk Plan Follow-Up Tasks Codex May Perform

###### Codex may create these files if specifically assigned:

* ###### `processed\_data/elk\_plan\_quality\_rules.json`
* ###### `processed\_data/elk\_plan\_context\_features.csv`
* ###### `processed\_data/elk\_plan\_reference\_audit.json`
* ###### `processed\_data/elk\_age\_objective\_context\_by\_unit.csv`
* ###### `docs/elk\_plan\_quality\_context.md`

###### Codex must keep these files separate from raw harvest truth and draw truth.

###### Required Validation For Elk Plan Integration

###### Any Codex task using the elk plan reference must validate:

* ###### no `DATABASE.csv` permit/allotment values changed
* ###### no `p\_draw` or probability fields changed directly from plan values
* ###### no management age objective was written into `average\_harvest\_age`
* ###### no `average\_days\_hunted` or `mean\_days\_hunted` was used as animal age
* ###### plan-context outputs carry `source\_file`, `source\_page`, `source\_table\_title`, and `data\_class`
* ###### observed age outputs identify annual-report source rows separately from plan objectives

###### Elk Plan Stop Condition

###### An elk-plan task is complete only when:

* ###### created outputs exist
* ###### validation confirms no runtime-truth overwrite
* ###### `WORK\_LOG.md` is updated
* ###### changes are committed if the task requested repository modification
* ###### Codex stops and reports the exact output files and validation commands

###### \---

###### 15\. Mule Deer Statewide Plan Reference And Harvest-Context Guardrails

###### This section is standing Codex instruction for mule deer management-plan context, harvest-context extraction, permit-policy interpretation, CWD context, and age-structure work.

###### Codex must treat the mule deer statewide plan reference as a **management-policy / harvest-context / quality-structure reference**, not as raw hunt-code harvest truth, not permit truth, not draw-odds truth, and not a source that can directly overwrite `DATABASE.csv`.

###### Required reference files, if present:

* ###### `mule\_deer\_statewide\_plan\_foundational\_reference.md`
* ###### `mule\_deer\_statewide\_plan\_foundational\_reference\_codex\_expanded.md`
* ###### `mule\_deer\_plan\_extracted.txt`
* ###### `pipeline/RAW/hunt\_unit\_database/mule\_deer\_plan.pdf`

###### Codex must read the expanded mule deer reference before any task involving:

* ###### mule deer quality scoring
* ###### mule deer age-quality scoring
* ###### premium limited-entry age-structure logic
* ###### mule deer permit strategy interpretation
* ###### mule deer management-plan policy context
* ###### mule deer public research page explanations
* ###### CWD management policy context
* ###### mule deer feature engineering from management-plan values

###### Mule Deer Plan Data Classification

###### The mule deer plan reference contains management-plan context, including:

* ###### plan scope and term
* ###### statewide population objective
* ###### current population estimate
* ###### buck-to-doe objective structure
* ###### limited-entry and premium limited-entry quality structure
* ###### permit-setting mechanics
* ###### weapon allocation policy
* ###### premium management buck and cactus buck policy
* ###### late muzzleloader policy
* ###### harvest and success baselines
* ###### monitoring and survival metrics
* ###### habitat treatment targets
* ###### draw-demand pressure context
* ###### CWD action and surveillance policy

###### These values are not raw harvest-result rows.

###### These values are not direct draw-odds truth.

###### These values are not current permit truth.

###### These values are not directly usable as `average\_harvest\_age`.

###### Core Mule Deer Plan Facts Codex Must Preserve

###### Codex must preserve these plan-context facts when building reference outputs:

* ###### Plan effective period: December 2024 through December 2030.
* ###### 2023 postseason population estimate: approximately 279,000 deer.
* ###### Statewide objective: 404,900 deer.
* ###### 2023 population level: approximately 69% of objective.
* ###### General-season objective structure: 15–17 or 18–20 bucks per 100 does.
* ###### Plan shifts more general units toward 15–17 for herd productivity and participation.
* ###### Limited-entry objective is truncated to 25–30 bucks per 100 does.
* ###### Premium limited-entry objective is truncated to 40–45 bucks per 100 does.
* ###### Annual permit changes up to ±20% may be automatic.
* ###### Annual permit changes greater than 20% require RAC + Wildlife Board process.
* ###### Standard weapon split: 20% archery / 20% muzzleloader / 60% any weapon.
* ###### Early any-weapon split: 20% archery / 20% muzzleloader / 20% early any / 40% late any.
* ###### Multi-season option on LE/PLE may be up to 3% of hunters, removed from any-weapon quota.
* ###### Premium management buck permits: 10–20% of premium permits.
* ###### Cactus buck permits may be recommended where appropriate.
* ###### Late muzzleloader on general units: up to 0.5% of general-season draw total, minimum 5 permits per unit.
* ###### 2024 general-season permits available: 71,525.
* ###### 10-year average buck harvest: 25,062 bucks per year.
* ###### 10-year buck harvest low/high in plan text: 17,042 in 2023 and 31,987 in 2016.
* ###### General any-weapon hunter success: 35.0% in 2023 versus 31.1% in 1998.
* ###### Premium LE quality expectation includes greater than 40% of harvested bucks age 5+ in a three-year average context.
* ###### Minimum postseason classification target: 400 does per unit.
* ###### 10-year adult female survival average: 79.8%.
* ###### 10-year fawn survival average: 52.1%.
* ###### Crucial mule deer range improvement target: minimum 600,000 acres by 2030.
* ###### Resident LE buck draw odds in 2024: 1 in 25.4.
* ###### General-season draw odds in 2024: approximately 1 in 2.3.
* ###### CWD strategy acts at detection rather than waiting for high prevalence.
* ###### CWD surveillance targets approximately 1% prevalence detection at 95% confidence.
* ###### CWD sample-size context includes approximately 304 deer and 346 elk.

###### Mule Deer Average-Age And Age-Structure Rules

###### Codex must distinguish between:

1. ###### **Observed harvested-age data**

   * ###### Examples: annual harvest report age tables, DWR tooth/cementum/check-station age tables, or verified average-age rows.
   * ###### Can feed `average\_harvest\_age` only when source year, species, unit, and hunt-code crosswalk are reviewed.
2. ###### **Management-plan age-structure thresholds**

   * ###### Example: premium LE expectation that more than 40% of harvested bucks are 5+ years old.
   * ###### This is a management signal.
   * ###### It must not be written as observed `average\_harvest\_age`.
   * ###### It can be used only as quality-context benchmark or classification label.
3. ###### **Average days hunted**

   * ###### This is hunter effort.
   * ###### It is never animal age.
   * ###### It must never populate `average\_harvest\_age`.

###### Mule Deer Plan Values Must Not Override Runtime Truth

###### Codex must not use mule deer plan values to directly modify:

* ###### `DATABASE.csv`
* ###### current permit fields
* ###### historical permit fields
* ###### 2026 allotment fields
* ###### draw odds
* ###### `p\_draw`
* ###### point-ladder probability fields
* ###### prediction probabilities
* ###### `public\_client\_engine.csv`
* ###### website-facing runtime files

###### Plan values may support:

* ###### research-page explanatory text
* ###### management-context labels
* ###### quality-score context
* ###### policy/reference sidebars
* ###### validation checks
* ###### unit objective comparisons
* ###### CWD management explanation
* ###### demand-pressure explanation

###### Mule Deer Quality Score Use

###### Age-related mule deer plan rules may support a quality-score context layer only when clearly separated from observed harvest age.

###### Allowed derived context fields:

* ###### `mule\_deer\_general\_buck\_doe\_objective\_min`
* ###### `mule\_deer\_general\_buck\_doe\_objective\_max`
* ###### `mule\_deer\_limited\_entry\_buck\_doe\_objective\_min`
* ###### `mule\_deer\_limited\_entry\_buck\_doe\_objective\_max`
* ###### `mule\_deer\_premium\_limited\_entry\_buck\_doe\_objective\_min`
* ###### `mule\_deer\_premium\_limited\_entry\_buck\_doe\_objective\_max`
* ###### `mule\_deer\_ple\_percent\_5plus\_threshold`
* ###### `mule\_deer\_ple\_percent\_5plus\_context\_only = true`
* ###### `mule\_deer\_permit\_auto\_change\_threshold\_pct`
* ###### `mule\_deer\_plan\_context\_only = true`

###### Observed annual-report age fields must remain separate:

* ###### `average\_harvest\_age`
* ###### `average\_harvest\_age\_source\_file`
* ###### `average\_harvest\_age\_source\_page`
* ###### `average\_harvest\_age\_reported\_year`
* ###### `average\_harvest\_age\_crosswalk\_confidence`

###### If both objective/threshold and observed age are present, Codex may compare them, but must not collapse them into one field.

###### Mule Deer Demand And Permit Strategy Use

###### Demand-pressure values such as resident LE draw odds and general-season draw odds are context values.

###### Codex may use them to explain demand pressure.

###### Codex must not use them as direct `p\_draw` values.

###### Permit strategy values such as weapon allocation percentages, automatic permit-change thresholds, late muzzleloader caps, management buck share, and multi-season share are policy context.

###### Codex must not use them to overwrite direct DWR permit truth unless a separate reviewed promotion step explicitly authorizes it.

###### Mule Deer Plan Follow-Up Tasks Codex May Perform

###### Codex may create these files if specifically assigned:

* ###### `processed\_data/mule\_deer\_plan\_quality\_rules.json`
* ###### `processed\_data/mule\_deer\_plan\_context\_features.csv`
* ###### `processed\_data/mule\_deer\_plan\_reference\_audit.json`
* ###### `processed\_data/mule\_deer\_age\_structure\_context\_by\_unit.csv`
* ###### `docs/mule\_deer\_plan\_quality\_context.md`

###### Codex must keep these files separate from raw harvest truth and draw truth.

###### Required Validation For Mule Deer Plan Integration

###### Any Codex task using the mule deer plan reference must validate:

* ###### no `DATABASE.csv` values changed
* ###### no permit/allotment values changed from plan context
* ###### no `p\_draw` or prediction probabilities changed directly from plan values
* ###### no plan age threshold was written into `average\_harvest\_age`
* ###### no `average\_days\_hunted` or `mean\_days\_hunted` was used as animal age
* ###### plan-context outputs carry `source\_file`, `source\_page` or section reference, `source\_table\_title` where applicable, and `data\_class`
* ###### observed age outputs identify annual-report source rows separately from plan thresholds

###### Mule Deer Plan Stop Condition

###### A mule-deer-plan task is complete only when:

* ###### created outputs exist
* ###### validation confirms no runtime-truth overwrite
* ###### `WORK\_LOG.md` is updated
* ###### changes are committed if the task requested repository modification
* ###### Codex stops and reports the exact output files and validation commands

###### \---

###### 16\. Prediction / Modeling Boundaries

###### Prediction outputs must be downstream of validated truth data.

###### Codex must not use incomplete or unvalidated fragments as if they are production truth.

###### Codex must distinguish:

* ###### deterministic rule simulation
* ###### modeled probability
* ###### historical observed probability
* ###### display odds
* ###### policy context
* ###### age-quality context
* ###### harvest quality context
* ###### current permit truth
* ###### historical draw truth

###### Codex must not use policy-plan values to directly change probability.

###### Codex must not use management-plan draw odds as live `p\_draw`.

###### Codex must not use age or quality metrics to alter permits or quotas.

###### Codex may use age metrics only as quality-score context after validation.

###### \---

###### 17\. Website / Public Output Rules

###### Website-facing files are downstream outputs.

###### Codex must not modify website/public output files until the data source feeding them is validated.

###### Public-facing outputs must not expose raw runtime or internal truth fragments unless specifically curated.

###### Public library files must remain curated.

###### Denylist protections must remain active for raw runtime/internal files.

###### If a public artifact is created, Codex must validate:

* ###### no raw runtime file exposure
* ###### public manifest file counts
* ###### build output path
* ###### `pages-dist` output
* ###### preview status where requested
* ###### file-size constraints such as Cloudflare limits

###### \---

###### 18\. Required Validation Commands

###### Codex must run validation appropriate to the task.

###### Common validations include:

```powershell
python -m py\_compile <changed\_python\_files>
node --check <changed\_js\_files>
npm.cmd run build
python -m pytest <targeted\_tests> -q
git diff --check
```
---

###### For CSV/data tasks, Codex must also validate:

* ###### output files exist
* ###### row counts are nonzero unless expected
* ###### required columns exist
* ###### no duplicate promoted source rows unless allowed
* ###### no invalid zero age values
* ###### no `average\_days\_hunted` or `mean\_days\_hunted` used as age
* ###### no non-promoted sources leaked into promoted manifests
* ###### no permit/allotment truth changed unless explicitly assigned
* ###### no `DATABASE.csv` changes unless explicitly assigned
* ###### no website files changed unless explicitly assigned

###### \---

###### 19\. Work Log Requirements

###### Every completed repository task must update `WORK\_LOG.md`.

###### Each entry must include:

* ###### timestamp UTC
* ###### scope
* ###### files changed
* ###### outputs created
* ###### key results
* ###### validation commands run
* ###### whether commit was made
* ###### commit hash if available

###### Codex must not treat a task as closed if `WORK\_LOG.md` is not updated.

###### \---

###### 20\. Commit Rules

###### If the task modifies repository files and the user asked Codex to make the change, Codex must commit after validation passes unless the user explicitly says not to commit.

###### Commit message must be specific.

###### Do not commit broken outputs.

###### Do not commit generated junk.

###### Do not commit local-only large artifacts unless they are intended project artifacts.

###### Do not commit raw temporary downloads unless the task explicitly requires source anchoring.

###### \---

###### 21\. Mandatory Mobile QA Final Pass

###### Every website, UI, public-output, or page-build task must finish with a mobile-first QA pass before closeout.

###### This is a standing final task, not an optional polish step.

###### Codex must validate, where relevant:

* ###### no horizontal page overflow at common mobile widths
* ###### primary navigation remains usable and visible
* ###### sticky headers do not cover critical controls
* ###### text has readable size and contrast on mobile
* ###### buttons and icons have usable tap targets
* ###### tables, ladders, maps, PDF viewers, and overlays remain accessible without hidden below-the-fold surprises
* ###### desktop layout is not broken by the mobile fix

###### For website tasks, Codex must include the mobile QA result in `WORK_LOG.md` and the final report.

###### \---

###### 22\. Final Report Format

###### When Codex finishes, it must report:

* ###### exact files changed
* ###### exact outputs created
* ###### validation commands run
* ###### key counts
* ###### blockers if any
* ###### commit hash if committed
* ###### stop condition satisfied

###### Codex must not continue to another task after reporting completion.
