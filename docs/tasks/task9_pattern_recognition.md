# Task 9 — Pattern Recognition (`MATCH_RECOGNIZE`)

## Why `MATCH_RECOGNIZE` instead of plain aggregate SQL

Detecting a "wave" (cases rising for a while, then falling for a while)
is fundamentally about the *shape* of a sequence over time — it can't be
expressed as a `GROUP BY`/aggregate, because it depends on the
relationship between each row and the ones around it, over a variable,
unknown-in-advance number of rows. `MATCH_RECOGNIZE` (Snowflake's
row-pattern-matching SQL extension, the assignment's suggested starting
point) is built exactly for this: define row "symbols" based on
conditions relative to neighboring rows, then match sequences of those
symbols like a regular expression over rows instead of characters.

## Platform note: `PREV()` vs. `LAG()`

Standard row-pattern-matching SQL (and most engines that implement it,
e.g. Oracle) use `PREV()`/`NEXT()` as the "previous/next row" navigation
functions inside `DEFINE`. On this Snowflake account, `PREV()` compiled
to `Unknown function` — verified against Snowflake's own documented
canonical example (a stock-price up/down pattern), not just this
project's query, confirming it's an account/platform behavior rather
than a mistake in the SQL. `LAG()` (an ordinary window function) works
as a drop-in replacement inside `DEFINE` — Snowflake implicitly applies
it over the `MATCH_RECOGNIZE` `PARTITION BY`/`ORDER BY`, the same way
`PREV()` would in the standard syntax.

## What was built

Both in [`sql/06_pattern_recognition_match_recognize.sql`](../../sql/06_pattern_recognition_match_recognize.sql),
against `JHU_COVID_19`, self-contained (no dbt/Python dependency):

### 1. Wave detection
Smooths daily new-case counts with a 7-day trailing average first
(necessary — raw daily deltas are dominated by weekly reporting-cadence
noise, which would otherwise register as dozens of fake single-day
"waves"). Then:

```sql
PATTERN (UP{5,} DOWN{5,})
DEFINE
    UP   AS NEW_CASES_7D_AVG > LAG(NEW_CASES_7D_AVG),
    DOWN AS NEW_CASES_7D_AVG <= LAG(NEW_CASES_7D_AVG)
```

Reads almost like English: "5 or more rising days, immediately followed
by 5 or more falling days" = one wave. Requiring 5+ days on each side
(rather than 1+) filters out small wobbles given the input is already
smoothed. Output: one row per detected wave per country, with its start
date, peak date, end date, and peak smoothed new-case level —
`MATCH_NUMBER()` numbers each country's waves in order (wave 1, wave 2,
"second wave", etc.), directly answering "how many distinct waves did
each country experience and when did they peak."

### 2. Rapid surge detection
A different pattern shape, showing `DEFINE` isn't limited to simple
greater-than comparisons:

```sql
PATTERN (SURGE{3,})
DEFINE
    SURGE AS NEW_CASES_7D_AVG > 1.05 * LAG(NEW_CASES_7D_AVG)
```

3+ consecutive days of >5% day-over-day growth in the smoothed series —
flags the *onset* of rapid growth earlier than wave detection would
(wave detection only confirms a wave once it's already turned over into
decline).

## Results

Verified against the live account:

- **Wave detection**: **416 distinct waves** detected across all
  countries in `JHU_COVID_19`. Example: United Arab Emirates alone shows
  **7 separate waves** between 2020-2022 — wave 4 (2022-01-14 to
  2022-03-16, 7 rising days then 55 falling days, peaking at a 7-day
  average of ~2,993 new cases) lines up with the globally-known Omicron
  wave timing, and wave 6 (2022-05-30 to 2022-09-14, a 36-day rise then
  72-day decline) shows a long, slow-moving wave distinct from the sharp
  Omicron spike — the kind of shape difference that would be hard to
  characterize from aggregate stats alone but falls straight out of
  `RISING_DAYS`/`FALLING_DAYS`.
- **Surge detection**: **2,986 surges** detected. The highest-magnitude
  surges cluster tightly around **December 2021 – March 2022** (France,
  South Korea, Vietnam, Argentina, Taiwan, Israel, Turkey, Indonesia all
  appear in the top 16 by end-level) — this is exactly the global
  Omicron wave window, a real, independently-verifiable signal rather
  than an artifact of the smoothing/threshold choices. South Korea shows
  a standout **39-day sustained surge** (2022-01-19 to 2022-02-26, rising
  from a 7-day average of ~4,782 to ~147,429 new cases) — one of the
  longest and steepest sustained growth periods in the dataset.

These are strong candidates for the final report's insights section —
the pattern-recognition approach independently rediscovered the
well-known Omicron wave timing purely from the shape of the case-count
series, without being told when it happened.
