# Database Hunt-Code Model Gap Audit

## Summary

- Canonical database file used: `pipeline\RAW\hunt_unit_database\2026\csv\DATABASE.csv`
- Database unique hunt-code count: `1394`
- Modeled target hunt-code count: `1021`
- Database-to-modeled gap count: `373`
- Coverage target-scope hunt-code count: `1668`
- Coverage-to-database overage count: `274`

## Bucket Counts

- `in_database_and_modeled`: `961`
- `in_database_not_modeled`: `433`
- `modeled_not_in_database`: `60`
- `coverage_seen_not_in_database`: `274`
- `historical_or_observed_only`: `601`
- `pending_or_non_probability_status`: `447`
- `out_of_scope_or_excluded`: `2`

## Top Gap Reasons

- `OBSERVED_HISTORY_ONLY`: `387`
- `IN_SCOPE_MODEL_PENDING`: `44`
- `EXCLUDED_NOT_PREDICTIVE_DRAW`: `2`

## Count Note

- No canonical database candidate in the current repo produced 1,294 unique hunt codes; selected canonical source reports 1394 unique hunt codes.
