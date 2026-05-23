HYBRID_ML_V1.md — Utah Predictive Draw Forecasting Layer
Purpose
This document defines the forecasting layer for the Utah predictive hunt draw engine.

It answers this question:

Given historical Utah draw behavior, hunt metadata, harvest/quality signals, point banks, permit trends, and possibly current application-level data, how do we forecast next year's applicant pool, quota environment, point creep, and draw probabilities?

The deterministic Utah draw mechanics are defined in UTAH\_DRAW\_MODEL\_V1.md.

The hybrid ML layer must forecast inputs to the simulator. It must not replace the simulator.

High-level pipeline
historical/public data + true feed where available
        ↓
normalization + validation
        ↓
feature engineering
        ↓
applicant demand forecast
        ↓
quota forecast or approved quota ingestion
        ↓
Utah draw simulator from UTAH\_DRAW\_MODEL\_V1.md
        ↓
Monte Carlo probability distribution
        ↓
backtest + calibration
        ↓
materialized processed CSVs for existing frontend
Current frontend bridge
The current HUNTS frontend consumes four processed CSVs:

processed\_data/draw\_reality\_engine.csv
processed\_data/point\_ladder\_view.csv
processed\_data/hunt\_master\_enriched.csv
processed\_data/hunt\_unit\_reference\_linked.csv
The hybrid ML layer should not force a frontend redesign. It should produce materialized predictions that preserve legacy fields and add modeled fields.

This file is the active canonical contract for the Utah hybrid ML layer. `HYBRID_ML_V1_ROLLOUT.md`, when present, is a detailed companion document and should be read with this file rather than replacing it.

Rows must remain keyed by:

(hunt\_code, residency, points)
Model stages
The predictive engine has four distinct stages.

Stage 1 — Deterministic rules simulator
Owned by UTAH\_DRAW\_MODEL\_V1.md.

Inputs:

applications
applicants
groups
points
hunt choices
quotas
residency
youth flags
eligibility flags
rule config
Output:

per-application draw result
aggregate probabilities
reason codes
Stage 2 — Applicant demand forecast
Forecasts who applies where.

Outputs forecasted application units by:

draw\_year
hunt\_code
residency
point bucket
youth flag
group size distribution
choice rank distribution
rule system
Stage 3 — Quota forecast
Forecasts available permits when final approved quota is not yet available.

Outputs:

hunt\_code
total\_public\_permits
resident\_quota
nonresident\_quota
youth\_reserved\_quota
reserved\_quota
random\_quota
preference\_quota
quota\_source
quota\_uncertainty
When final approved quotas are available, use them instead of forecasting.

Stage 4 — Monte Carlo probability forecast
Combines demand uncertainty and quota uncertainty, then repeatedly runs the deterministic simulator.

Outputs:

p\_draw\_mean
p\_draw\_p10
p\_draw\_p50
p\_draw\_p90
p\_reserved\_mean
p\_random\_mean
p\_preference\_mean
p\_youth\_mean
expected\_cutoff\_points
cutoff\_bucket\_probability
guaranteed\_probability
reason\_codes
Data source levels
The model must explicitly mark which data level was used.

Fixture mode
Used for tests and initial development.

applicant\_pool\_source = fixture
quota\_source = fixture
data\_quality\_grade = F or TEST\_ONLY
Never present fixture results as real predictions.

Public-data MVP mode
Uses public historical data.

Possible sources:

Utah DWR big game drawing odds and point reports
Utah DWR current draw odds platform exports if available
Utah DWR guidebooks and hunt tables
Utah DWR permit recommendations and final approvals
Utah DWR harvest/survey reports
Hunt Planner metadata
Limitations:

public reports may expose only first-choice odds;
group composition may be unavailable;
current-year applicant pool may be unavailable;
second-through-fifth choices may be unavailable;
eligibility/waiting-period status may be unavailable.
Use labels:

applicant\_pool\_source = public\_historical\_proxy
quota\_source = approved | proposed | forecast
data\_quality\_grade = A | B | C | D depending on completeness
reason\_codes includes FIRST\_CHOICE\_ONLY\_PUBLIC\_DATA or INSUFFICIENT\_TRUE\_FEED where applicable
True-feed mode
Uses application-level or equivalent administrative data.

Required for a true predictive draw engine:

current and historical application choices by rank;
group ID and group size;
effective group points;
applicant residency;
youth eligibility;
eligibility/waiting-period flags;
points before and after draw;
quota partitions;
draw stage/result;
current-year applicant pool where available.
Use labels:

applicant\_pool\_source = application\_level\_feed | current\_application\_feed
quota\_source = approved | proposed | forecast
data\_quality\_grade = A when data is complete
Required raw feed contract
Create schemas and fixture CSVs for the following feed tables.

applications_raw.csv
Required columns:

draw\_year
draw\_type
application\_id
group\_id
hashed\_customer\_id
species
hunt\_choices
choice\_rank
hunt\_code
weapon
submitted\_at
edited\_flag
withdrawn\_flag
valid\_flag
eligible\_flag
Notes:

hunt\_choices should store ordered choices when available.
choice\_rank can be present for exploded one-row-per-choice format.
Public MVP may only contain first-choice records.
applicants_raw.csv
Required columns:

hashed\_customer\_id
draw\_year
residency
youth\_flag
youth\_eligibility\_flag
lifetime\_license\_flag
dedicated\_hunter\_flag
waiting\_period\_status
license\_valid\_flag
Do not store names, addresses, emails, phone numbers, exact dates of birth, SSNs, raw customer IDs, or payment data.

groups_raw.csv
Required columns:

draw\_year
group\_id
group\_size
member\_ids\_hashed
same\_choices\_flag
youth\_only\_flag
residency\_mix
effective\_points\_floor
points_raw.csv
Required columns:

draw\_year
hashed\_customer\_id
species
point\_type
points\_before\_draw
points\_after\_draw
point\_only\_purchase\_flag
forfeited\_flag
restored\_or\_surrender\_flag
quotas_raw.csv
Required columns:

draw\_year
hunt\_code
species
total\_public\_permits
resident\_quota
nonresident\_quota
youth\_reserved\_quota
reserved\_quota
random\_quota
preference\_quota
quota\_source
final\_approved\_flag
draw_results_raw.csv
Required columns:

draw\_year
application\_id
group\_id
hashed\_customer\_id
hunt\_code
drawn\_flag
draw\_stage
choice\_rank\_drawn
permit\_issued\_flag
alternate\_or\_reallocated\_flag
surrendered\_flag
remaining\_after\_draw
hunt_metadata_raw.csv
Required columns:

draw\_year
hunt\_code
unit\_id
unit\_name
species
permit\_type
hunt\_type
rule\_system
weapon
season\_start
season\_end
active\_flag
new\_renamed\_discontinued\_flag
boundary\_version
harvest_quality_raw.csv
Required columns:

draw\_year
hunt\_code
permits\_afield
harvest
harvest\_success
avg\_days\_hunted
hunter\_satisfaction
buck\_doe\_ratio
bull\_cow\_ratio
population\_estimate
winter\_survival
fawn\_doe\_ratio
drought\_or\_habitat\_index
Normalized data tables
After raw ingestion, normalize into:

ut\_hunts
ut\_hunt\_years
ut\_permit\_quotas
ut\_applications
ut\_application\_choices
ut\_applicants
ut\_groups
ut\_points
ut\_draw\_results
ut\_point\_bank
ut\_harvest\_quality
ut\_demand\_features
ut\_quota\_features
ut\_predictions
ut\_prediction\_backtests
ut\_rule\_versions
Feature engineering
Demand features
Use these features when available:

historical\_applicants\_by\_hunt\_residency\_points
historical\_first\_choice\_applicants
historical\_choice\_rank\_distribution
historical\_group\_size\_distribution
historical\_youth\_share
historical\_resident\_nonresident\_share
historical\_draw\_success\_by\_point\_bucket
historical\_point\_only\_purchases
historical\_point\_bank\_size
historical\_drawn\_applicant\_removal
new\_entrant\_count
returning\_unsuccessful\_count
hunt\_code\_change\_flag
hunt\_discontinued\_flag
hunt\_new\_flag
unit\_boundary\_change\_flag
weapon\_type
season\_timing
Hunt-quality features
Use these features when available:

harvest\_success
harvest\_count
permits\_afield
avg\_days\_hunted
hunter\_satisfaction
buck\_doe\_ratio
bull\_cow\_ratio
fawn\_doe\_ratio
population\_estimate
winter\_survival
drought\_or\_habitat\_index
public\_access\_score
unit\_reputation\_score
recent\_tag\_change\_pct
Quota features
Use these features when available:

prior\_year\_total\_public\_permits
prior\_year\_resident\_quota
prior\_year\_nonresident\_quota
prior\_year\_youth\_quota
prior\_year\_reserved\_quota
prior\_year\_random\_quota
permit\_change\_1yr
permit\_change\_3yr
permit\_recommendation\_status
final\_approved\_flag
population\_objective\_gap
harvest\_management\_signal
winter\_survival\_signal
Baseline demand model
Do not start with complex ML. First implement a baseline that can be tested and backtested.

Inputs
historical applications by hunt/residency/point bucket
historical draw results by hunt/residency/point bucket
point-only purchase counts where available
drawn applicant removal
new entrant estimates
hunt metadata
Basic algorithm
For each (hunt\_code, residency, point\_bucket):

Estimate retained applicants from prior year.
Remove applicants likely drawn in prior year.
Move unsuccessful applicants up one point bucket when point accumulation applies.
Add point-only purchasers into the point bank when applicable.
Add estimated new entrants at low point buckets.
Smooth year-over-year demand using historical trend.
Apply hunt-change adjustments for new, renamed, discontinued, or quota-changed hunts.
Produce a forecasted count and uncertainty interval.
Suggested formulas:

retained\_unsuccessful = prior\_applicants - prior\_drawn
advanced\_bucket\_count\[p+1] += retained\_unsuccessful\[p] \* retention\_rate\[p]
new\_entrants\[0] = smoothed\_recent\_new\_entrants
forecast\_count = alpha \* recent\_count + (1 - alpha) \* trend\_adjusted\_prior
Start with configurable alpha, such as 0.60, then tune through backtesting.

Hierarchical smoothing
Sparse hunt/point buckets should borrow strength from broader levels:

hunt\_code + residency + points
unit + species + residency + points
species + residency + points
statewide + species + points
Use fallback smoothing when the exact bucket has insufficient history.

Reason codes:

EXACT\_BUCKET\_HISTORY\_USED
UNIT\_LEVEL\_SMOOTHING\_USED
SPECIES\_LEVEL\_SMOOTHING\_USED
STATEWIDE\_SMOOTHING\_USED
SPARSE\_HISTORY
NEW\_HUNT\_CODE
RENAMED\_HUNT\_CODE
DISCONTINUED\_HUNT\_CODE
Group-size forecast
If true group data exists, model group size distribution by:

hunt\_type
species
residency
point\_bucket
youth\_flag
If public data lacks group composition, use a configurable proxy distribution and emit:

GROUP\_DISTRIBUTION\_PROXY\_USED
Suggested initial proxy:

group\_size\_1: high default share
group\_size\_2: small share
group\_size\_3: smaller share
group\_size\_4: smaller share
Do not hardcode final values without backtesting or documented assumptions.

Choice-rank forecast
If true feed exists, model first-through-fifth choice distributions.

If public data only has first-choice odds:

Use first-choice only for public MVP.
Emit FIRST\_CHOICE\_ONLY\_PUBLIC\_DATA.
Do not claim complete second-through-fifth-choice accuracy.
When true feed exists, estimate:

P(choice\_rank = r | hunt\_code, species, residency, points, youth\_flag, group\_size)
Quota forecast model
Use final approved quotas when available.

If quotas are not final, use a forecast.

Baseline quota forecast
For each hunt:

Use prior-year approved quota.
Apply recent quota trend.
Apply permit recommendation/proposed quota if available.
Apply harvest and population indicators where available.
Produce uncertainty interval.
Suggested output:

quota\_mean
quota\_p10
quota\_p50
quota\_p90
quota\_source
quota\_reason\_codes
Reason codes:

APPROVED\_QUOTA\_USED
PROPOSED\_QUOTA\_USED
FORECAST\_QUOTA\_USED
PRIOR\_YEAR\_QUOTA\_USED
QUOTA\_TREND\_ADJUSTED
HARVEST\_SIGNAL\_ADJUSTED
POPULATION\_SIGNAL\_ADJUSTED
Hybrid Monte Carlo design
Each Monte Carlo iteration should sample:

Forecasted applicant counts by bucket.
Group size assignments.
Choice-rank assignments when available.
Quota values if quota is forecasted.
Random draw order/tickets according to Utah rules.
Then run the deterministic simulator.

Pseudo-flow:

for iteration in range(n\_iterations):
    sampled\_applicant\_pool = demand\_model.sample(seed\_i)
    sampled\_quotas = quota\_model.sample(seed\_i)
    draw\_state = build\_draw\_state(sampled\_applicant\_pool, sampled\_quotas, hunts, rules)
    sim\_result = utah\_simulator.run\_once(draw\_state, seed\_i)
    collect\_results(sim\_result)

aggregate\_results()
calibrate\_probabilities()
materialize\_rows()
Production default:

n\_iterations = 10000
Development/test default:

n\_iterations = 100 or lower with seeded fixtures
Output predictions
Each materialized prediction row should include:

prediction\_year
hunt\_code
residency
points
p\_draw\_mean
p\_draw\_p10
p\_draw\_p50
p\_draw\_p90
p\_reserved\_mean
p\_random\_mean
p\_preference\_mean
p\_youth\_mean
expected\_cutoff\_points
cutoff\_bucket\_probability
guaranteed\_probability
point\_creep\_1yr
point\_creep\_3yr
quota\_source
applicant\_pool\_source
model\_version
rule\_version
data\_cutoff\_date
data\_quality\_grade
reason\_codes
display\_odds\_pct
Field rules:

p\_\* fields are decimal probabilities from 0 to 1.
display\_odds\_pct is a percentage from 0 to 100.
reason\_codes may be pipe-delimited in CSV output.
model\_version must change when demand/quota/model logic changes.
rule\_version must change when simulator rules/config changes.

UI presentation rules:

- model fields stay numeric internally;
- user-facing draw odds should render in combined `~1 in X or Y%` format;
- this is a display-only rule and not a model or probability-math change;
- an optional display-only materialized field such as `display_odds_one_in_or_pct` may be added later, but it must not replace numeric `display_odds_pct`.

Point creep
Point creep should be computed from modeled cutoff movement.

Suggested fields:

expected\_cutoff\_points\_current
expected\_cutoff\_points\_prior\_year
expected\_cutoff\_points\_3yr\_avg
point\_creep\_1yr = current - prior\_year
point\_creep\_3yr = current - 3yr\_avg
Reason codes:

POINT\_CREEP\_POSITIVE
POINT\_CREEP\_FLAT
POINT\_CREEP\_NEGATIVE
POINT\_CREEP\_OUTRUNNING\_APPLICANT
POINT\_CREEP\_CATCHABLE
Do not use point creep as a replacement for probability. It is an explanatory feature.

Data quality grading
Use a data-quality grade on every prediction row.

Suggested grading:

A
True application-level feed is available for relevant years and current/proposed pool, including groups, choices, points, residency, youth status, eligibility, quotas, and results.

B
Historical application-level feed is available, but current-year pool is forecasted.

C
Public DWR historical draw/point reports are available with strong quota/harvest metadata, but group and multi-choice data are inferred.

D
Sparse public data, new/renamed hunt code, missing group/choice data, or missing quota history.

F / TEST_ONLY
Synthetic fixture data only.

Backtesting
Backtesting is mandatory before calling predictions reliable.

Backtest procedure
For each target year N:

Train/fit using years <= N-1.
Forecast applicant pool for N.
Use approved quotas for N if testing demand-only; use forecast quotas for full pre-approval simulation.
Run Monte Carlo simulator.
Compare predicted outputs to actual N draw results.
Store metrics by hunt type, species, residency, and point bucket.
Required metrics
mean\_absolute\_error\_probability
brier\_score
log\_loss\_if\_safe
calibration\_by\_probability\_band
expected\_calibration\_error
cutoff\_point\_error
false\_guaranteed\_count
resident\_mae
nonresident\_mae
limited\_entry\_mae
once\_in\_lifetime\_mae
general\_deer\_mae
antlerless\_mae
high\_demand\_hunt\_mae
low\_demand\_hunt\_mae
Calibration bands
Suggested bands:

0.00
0.01-0.05
0.05-0.10
0.10-0.25
0.25-0.50
0.50-0.75
0.75-0.90
0.90-0.99
0.99-1.00
Track actual draw rate within each band.

False guarantee rule
A false guarantee occurs when:

guaranteed\_probability >= 0.999
but the historical result shows the applicant bucket was not fully guaranteed.

Any false guarantee is severe and should fail calibration review.

Leakage prevention
Do not train on data from the target year that would not have been available before the prediction date.

Examples:

Do not use final draw results to predict the same year.
Do not use final approved quota if the intended use case is pre-approval prediction.
Do not use harvest results from after the target draw date.
Do not use post-draw point balances to forecast pre-draw applicant pools.
Every prediction run should include:

data\_cutoff\_date
quota\_source
applicant\_pool\_source
model\_version
rule\_version
Materialization contract
The materializer should write enhanced CSVs without breaking the existing frontend.

Primary target:

processed\_data/draw\_reality\_engine.csv
Required legacy-compatible fields:

hunt\_code
residency
points
odds\_2026\_projected
max\_pool\_projection\_2026
random\_draw\_odds\_2026
random\_draw\_projection\_2026
draw\_outlook
trend
status
Required modeled fields:

prediction\_year
p\_draw\_mean
p\_draw\_p10
p\_draw\_p50
p\_draw\_p90
p\_reserved\_mean
p\_random\_mean
p\_preference\_mean
p\_youth\_mean
expected\_cutoff\_points
cutoff\_bucket\_probability
guaranteed\_probability
point\_creep\_1yr
point\_creep\_3yr
quota\_source
applicant\_pool\_source
model\_version
rule\_version
data\_cutoff\_date
data\_quality\_grade
reason\_codes
display\_odds\_pct
Legacy mapping:

odds\_2026\_projected = display\_odds\_pct
max\_pool\_projection\_2026 = p\_reserved\_mean \* 100
random\_draw\_odds\_2026 = p\_random\_mean \* 100
random\_draw\_projection\_2026 = p\_random\_mean \* 100
Important:

status = MAX POOL
is descriptive only. It must not imply guaranteed draw odds.

Frontend probability selection
The frontend should prefer modeled fields.

Suggested function:

function getModeledDisplayOdds(row) {
  const displayPct = toNumber(row.display\_odds\_pct);
  if (Number.isFinite(displayPct)) return displayPct;

  const pDrawMean = toNumber(row.p\_draw\_mean);
  if (Number.isFinite(pDrawMean)) return pDrawMean * 100;

  const projected = toNumber(row.odds\_2026\_projected);
  if (Number.isFinite(projected)) return projected;

  const maxPool = toNumber(row.max\_pool\_projection\_2026);
  if (Number.isFinite(maxPool)) return maxPool;

  const randomOdds = toNumber(row.random\_draw\_odds\_2026);
  if (Number.isFinite(randomOdds)) return randomOdds;

  const randomProjection = toNumber(row.random\_draw\_projection\_2026);
  if (Number.isFinite(randomProjection)) return randomProjection;

  return null;
}
Do not include logic equivalent to:

if (row.status === "MAX POOL") return 100;

All user-facing draw-odds displays should then format the selected numeric percent into combined `~1 in X or Y%` text.

Model versioning
Version fields:

model\_version = hybrid\_ml\_v1.0.0
rule\_version = utah\_draw\_model\_v1.0.0
Increment model\_version when changing:

demand model;
quota model;
feature set;
calibration method;
Monte Carlo sampling method;
materialized probability calculation.
Increment rule\_version when changing:

Utah simulator mechanics;
rule config;
group handling;
youth pool handling;
residency/crossover handling;
bonus/preference draw algorithm.
Implementation modules
Suggested modules:

engine/utah/features.py
  Build feature tables from normalized data.

engine/utah/demand.py
  Forecast applicant demand and point-bucket movement.

engine/utah/quota\_forecast.py
  Forecast quota values when approved quotas are unavailable.

engine/utah/simulator.py
  Deterministic simulator from UTAH\_DRAW\_MODEL\_V1.md.

engine/utah/calibration.py
  Probability calibration and reliability reporting.

engine/utah/backtest.py
  Train-through-year N-1, predict N, compare to actual N.

engine/utah/materialize.py
  Write enhanced and legacy-compatible processed CSVs.

engine/utah/validators.py
  Validate raw and normalized feed tables.
Minimum baseline before ML expansion
Before adding complex ML, implement:

Deterministic simulator.
Fixture data.
CSV materializer.
Frontend probability-selection patch.
Baseline historical smoothing demand model.
Simple quota trend model.
Backtest harness.
Calibration report.
Only after those are stable should the repo add:

gradient boosted models;
Bayesian hierarchical models;
probabilistic programming;
neural models;
external ML pipelines.
Acceptance criteria
The hybrid ML layer is acceptable when:

It can run from fixture data.
It can run from public-data normalized tables when available.
It outputs all required modeled fields.
It labels source quality correctly.
It does not claim true predictive status without true feed data.
It passes backtest tests on synthetic data.
It produces calibrated probability reports.
It writes frontend-compatible processed CSVs.
It preserves legacy columns.
It never reintroduces MAX POOL = 100%.
Required tests
test\_demand\_baseline\_advances\_unsuccessful\_applicants
test\_demand\_baseline\_removes\_drawn\_applicants
test\_demand\_baseline\_adds\_new\_entrants
test\_sparse\_bucket\_uses\_hierarchical\_smoothing
test\_group\_distribution\_proxy\_reason\_code
test\_first\_choice\_only\_public\_data\_reason\_code
test\_quota\_approved\_overrides\_forecast
test\_quota\_forecast\_reason\_codes
test\_monte\_carlo\_outputs\_probability\_quantiles
test\_backtest\_false\_guaranteed\_count
test\_calibration\_band\_summary
test\_materializer\_preserves\_legacy\_fields
test\_materializer\_probability\_units\_decimal\_vs\_pct
test\_model\_version\_present
test\_rule\_version\_present
test\_data\_quality\_grade\_present
Known limitations
A public-data MVP can be useful, but it is not the same as a true application-level draw engine.

Public-data limitations:

group behavior must often be inferred;
second-through-fifth choices may be missing;
true current-year application pool may be missing;
eligibility/waiting periods may be missing;
application withdrawals/edits may be missing;
point-only purchases may be incomplete or aggregated;
CWMU/public/private interactions may require explicit feed support.
The engine should surface limitations in:

data\_quality\_grade
applicant\_pool\_source
quota\_source
reason\_codes
frontend source modal
One-sentence summary
The hybrid ML layer predicts the future applicant and quota environment; the Utah draw simulator determines what those forecasts mean under Utah's actual draw mechanics.
