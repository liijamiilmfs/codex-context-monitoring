# Controlled experiment input

Scope and acceptance criteria belong to the [accepted ADR](https://linear.app/rule0softworks/document/adr-compare-controlled-desktop-and-cli-context-readings-aae4bc10842d) and RUL-2829 through RUL-2831 in Linear.

One UTF-8 text file describes one model at Medium. Use `[experiment]`, then
`[desktop]`, then `[cli]`, once each, in that order. Blank lines and surrounding
whitespace are accepted; an initial UTF-8 BOM is accepted. There are no comments,
extra fields, alternate schema versions, or unrelated status lines.

The eight required, nonblank `name = value` fields are:

| Field | Value |
| --- | --- |
| `date` | Valid calendar date, `YYYY-MM-DD` |
| `model` | `Luna`, `Sol`, or `Astra` |
| `reasoning` | `Medium` |
| `operating_system` | Operator-supplied OS description |
| `desktop_version` | Operator-supplied Desktop version |
| `cli_version` | Operator-supplied CLI version |
| `conditions` | Sanitized description of the shared, unchanged setup |
| `summary` | Short text copied into the report; full metadata stays in the input |

Names and model/settings are case-sensitive. Metadata order is flexible.
Values occupy one line; an equals sign within a value is literal.

Each surface contains one reading per line, in collection order:

```text
Context: 93% left (18.7K used / 258K)
Context window: 96% left (10,100 used / 258,000)
```

Use `Context:` only in `[desktop]` and `Context window:` only in `[cli]`.
One or more spaces may separate the label from the percentage; display alignment
spaces are preserved in the original reading.
Counts accept nonnegative whole numbers, correctly grouped commas, and uppercase
`K` with up to three decimals. `18.7K` normalizes to approximately 18,700; its
display increment is 100 tokens. K notation always retains its rounded flag,
including capacities. Original lines, spaces, and displayed percentages remain
available as evidence. Capacity comparisons use normalized counts.

Each group must contain at least three readings, with equal counts across groups.
Every capacity must be positive and equal; tokens used cannot exceed capacity.
Displayed percentage left must be a decimal from 0 to 100. Invalid or missing
tokens used identify the input line to fix. Unknown fields and structures fail
validation; values are never invented.

Limits: 1,048,576 characters, 131,072 characters per line, 10,000 readings total,
and counts no greater than 999,999,999,999,999 tokens. Percentage text is limited
to 128 characters. XML-prohibited characters are rejected so evidence can safely
reach SVG output. The command also bounds the bytes read from disk.

See [the synthetic sample](../examples/controlled-comparison.sample.txt).
It contains invented readings only.

## Results and uncertainty

Each surface has a separate count, average, minimum, and maximum. The difference
is Desktop average minus CLI average, in tokens. There is no combined average or
percentage comparison. These totals do not identify what consumed context or
explain why surfaces differ.

Calculations retain exact rational arithmetic. Exact fractional averages are
shown as fractions so they are not silently rounded. If a group's tokens-used
input includes K notation, its statistics are conservatively labeled approximate;
the average difference is approximate if either group is approximate. Approximate
results are displayed to whole tokens, without implying added measurement
precision. Original readings retain the source display precision. Rounded
capacity alone does not make token statistics approximate.

Displayed percentage left is checked against `100 × (1 − used / capacity)` using
normalized counts. Only discrepancies greater than one percentage point warn;
warnings never block output. The threshold uses exact arithmetic before display
rounding. Displayed percentages remain unchanged in the original readings.

The Markdown has exactly five sections: test summary, individual readings grouped
by surface, summary statistics, warnings, and a relative chart link. The SVG has
two average bars and the labeled token difference. For collection steps and the
command, see the [README](../README.md#controlled-comparison-mvp).
