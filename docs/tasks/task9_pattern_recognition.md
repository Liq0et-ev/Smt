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
    UP   AS NEW_CASES_7D_AVG > PREV(NEW_CASES_7D_AVG),
    DOWN AS NEW_CASES_7D_AVG <= PREV(NEW_CASES_7D_AVG)
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
    SURGE AS NEW_CASES_7D_AVG > 1.05 * PREV(NEW_CASES_7D_AVG)
```

3+ consecutive days of >5% day-over-day growth in the smoothed series —
flags the *onset* of rapid growth earlier than wave detection would
(wave detection only confirms a wave once it's already turned over into
decline).

## Results (fill in after running against the live account)

_To be completed with the actual detected waves/surges per country —
e.g. how many waves each core country experienced, which had the
sharpest surges — for the final report's insights section._
