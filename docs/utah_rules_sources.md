# Utah Rules Sources

This file records the rule assumptions and source anchors for the Utah draw engine.

Detailed formula contract:

- `docs/utah_draw_routing_and_algorithm_v1.md`

## Mechanical anchors

- Utah DWR drawing odds pages and draw-result pages are informational.
- Bonus and preference point behavior is deterministic at the rule level.
- Group behavior is atomic when a group is allowed.
- Youth, residency, and crossover handling must be explicit in code.

## Assumptions

- If a rule is not public or not fully exposed in the feed, the engine should treat it as configuration rather than hiding the assumption.
- `MAX POOL` is not a guarantee unless the modeled guarantee threshold is met.

