## Canonical JSON rules

When working on `hunt-master-canonical-2026.json`:

- Treat it as production source-of-truth data.
- Never create partial placeholder-only output.
- Never create placeholder-only files, placeholder-only logic, or placeholder-only reports to simulate progress.
- Start the assigned project step and move it through implementation, validation, and finished output before switching tasks.
- Always update or create a JSON Schema.
- Always validate JSON before finishing.
- Unknown values must use `needs_owner_input`, not guesses.
- Regulatory/legal facts must include source fields or be marked `source_needed`.
- Stable IDs are required for reusable records.
- Run canonical validation before final response.
