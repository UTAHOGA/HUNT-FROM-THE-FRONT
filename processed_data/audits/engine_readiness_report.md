# Engine Readiness Report

Generated: 2026-05-29T16:52:28.194Z

| Engine/Page | Status | Can Populate | Confidence | Critical Holes | Next Fix |
|---|---:|---:|---:|---|---|
| Hunt Builder selection/filter/map | READY | yes | HIGH | None flagged in top audit | Keep DATABASE/reference/boundary IDs aligned. |
| Hunt Research core summary | READY | yes | HIGH | None flagged in top audit | Maintain Cloudflare-first runtime CSV delivery. |
| Point ladder | READY | yes | HIGH | None flagged in top audit | Review current hunts missing ladder/status rows. |
| Predictive draw odds | READY | yes | MEDIUM | None flagged in top audit | Resolve pending families after source sync; do not change formulas in audit task. |
| Comparable hunts | READY | yes | MEDIUM | None flagged in top audit | Improve comparable scoring after field consistency audit. |
| Harvest quality | READY | yes | MEDIUM | None flagged in top audit | Continue annual harvest crosswalk lineage repair. |
| Age quality | READY | yes | MEDIUM | None flagged in top audit | Keep observed average_harvest_age separate from days and 3-year current age. |
| State management objective | NEEDS_SOURCE_SYNC | yes | MEDIUM | EB3024<br>EB3025<br>DB1000<br>DB1001<br>DB1500 | Render benchmark-only unless observed comparison exists. |
| Outfitter matching | BLOCKED | no | MEDIUM | None flagged in top audit | Add reviewed coverage/boundary links. |
| Public library | READY | yes | MEDIUM | None flagged in top audit | Keep library mapping statuses explicit and audit moved PDFs. |

## Summary Counts

- inventory_files: 7641
- sync_edges: 10
- data_holes: 120
- year_to_year_flags: 2562
- runtime_sources_tested: 15
- runtime_sources_ok: 10
- engines_ready: 8
- engines_partial: 0
- engines_blocked: 1
- engines_placeholder_only: 0
- engines_needs_source_sync: 1
