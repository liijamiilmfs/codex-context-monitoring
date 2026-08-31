# Manual CSV input contract

The MVP accepts manually recorded Codex context-usage observations as CSV. One
row represents one reported context source within one named snapshot. Automatic
collection, normalization, and persistence are outside this contract. The pure
manual CSV Transformer accepts complete in-memory text and atomically converts a
valid document into application-owned Models.

## Columns

The header must contain these columns in this order:

| Column | Presence | Value |
| -- | -- | -- |
| `snapshot_id` | Required | Non-empty stable label for one captured observation set. Multiple source rows may share the same label. |
| `surface` | Required | Non-empty raw surface label supplied by the operator, such as `Codex Desktop` or `Codex CLI`. |
| `source` | Required | Non-empty raw source or category label supplied by the operator. |
| `tokens` | Required | Base-10 integer greater than or equal to zero. |
| `captured_at` | Optional | ISO 8601 timestamp when known; otherwise blank. |
| `context_limit` | Optional | Base-10 integer greater than zero when known; otherwise blank. |
| `notes` | Optional | Free-text operator note; otherwise blank. |

Files must be UTF-8 encoded and use standard CSV quoting for values containing
commas, double quotes, or newlines. Required values must not be blank. An empty
optional field means that the value was not supplied; consumers must preserve
that distinction and must not invent a default value.

The input boundary preserves `surface` and `source` exactly as supplied. It does
not trim, rename, group, or otherwise normalize either value.

## Architecture classification

Under R0S-ARCH-LAYERS `2.0.0-rc.2`, the row schema is the serialized form of a
Contract owned by the local manual-input boundary. `ContextUsageObservation` is
the behavior-free application Model. `parse_manual_csv` is a stateless
Transformer from the CSV representation into those Models; its narrow
validation issue and aggregate error types are Transformer-local structural
support. The Transformer performs no filesystem, network, process, telemetry,
or other external I/O. The checked-in CSV is non-production example data.

## Valid sample

[`examples/manual-context-usage.sample.csv`](../examples/manual-context-usage.sample.csv)
is a synthetic, public-safe sample. It contains two snapshots, Desktop and CLI
surface labels, multiple source rows per snapshot, and blank optional values.
Its token counts and timestamps are illustrative and do not represent a real
Codex session or user content.
