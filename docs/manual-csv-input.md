# Manual CSV input contract

The MVP accepts manually recorded Codex context-usage observations as CSV. One
row represents one reported context source within one named snapshot. Automatic
collection and persistence are outside this contract. The pure manual CSV
Transformer accepts complete in-memory text and atomically converts a valid
document into normalized application-owned Models.

## Columns

The header must contain these columns in this order:

| Column | Presence | Value |
| -- | -- | -- |
| `snapshot_id` | Required | Non-empty stable label for one captured observation set. Multiple source rows may share the same label. |
| `surface` | Required | Non-empty surface label supplied by the operator, such as `Codex Desktop` or `Codex CLI`. |
| `source` | Required | Non-empty source or category label supplied by the operator. |
| `tokens` | Required | Base-10 integer greater than or equal to zero, with at most 4,300 digits. |
| `captured_at` | Optional | ISO 8601 timestamp when known; otherwise blank. |
| `context_limit` | Optional | Base-10 integer greater than zero with at most 4,300 digits when known; otherwise blank. |
| `notes` | Optional | Free-text operator note; otherwise blank. |

Files must be UTF-8 encoded, may include one leading UTF-8 byte-order mark, and
must use standard CSV quoting for values containing commas, double quotes, or
newlines. Required values must not be blank. An empty optional field means that
the value was not supplied; consumers must preserve that distinction and must
not invent a default value.

## Input limits and text safety

The parser accepts at most 1,048,576 Unicode characters per document (including
any leading byte-order mark), 131,072 decoded characters per field, and 10,000
data records. A quoted multiline record counts once. Larger inputs produce a
clear validation error; the document limit is checked before quote scanning.
This in-memory API does not bound the caller's initial file read.

All fields must contain only XML 1.0 characters so imported labels can be used
in SVG output. Tab, carriage return, newline, and valid Unicode text are allowed;
prohibited controls, lone surrogates, U+FFFE, and U+FFFF are rejected with the row
and field identified. Labels containing dollar signs render literally.

## Capture timestamps

Nonblank timestamps use `YYYY-MM-DDTHH:MM:SS`, optionally followed by a fraction
of one to six digits (introduced by `.` or `,`) and `Z` or a `+HH:MM`/`-HH:MM`
offset. Calendar dates, times, and offsets must be valid. Examples:
`2026-08-30T14:00:00Z` and `2026-08-30T14:00:00.123456+05:30`.
Other date/time separators, date-only values, basic unseparated forms, and
fractions that would lose precision are rejected. A comma fraction needs CSV
quoting, just like any other field containing a comma.

## Label normalization and traceability

The input `surface` and `source` columns are raw operator-provided labels. In the
resulting `ContextUsageObservation` Model, `raw_surface` and `raw_source`
preserve those values exactly, including boundary whitespace and casing.
`surface` and `source` contain deterministic canonical labels for comparison.

The Transformer trims boundary whitespace before canonicalization and declares
these case-insensitive aliases:

| Model field | Accepted label forms | Canonical value |
| -- | -- | -- |
| `surface` | `codex desktop`, `codex-desktop` | `Codex Desktop` |
| `surface` | `codex cli`, `codex-cli` | `Codex CLI` |
| `source` | `system instructions`, `system-instructions` | `System instructions` |
| `source` | `user conversation`, `user-conversation` | `User conversation` |
| `source` | `tool output`, `tool-output` | `Tool output` |

Case differences within these declared forms normalize to the same canonical
value. An unknown nonblank label is boundary-trimmed but otherwise preserved as
its canonical value; the Transformer does not guess, group it, or collapse it
to a generic category.

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
