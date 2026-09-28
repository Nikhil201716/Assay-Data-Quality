# Assay — an ETL pipeline, and which data-quality check catches which defect

**"The pipeline ran" catches 0 of 14 injected data defects. A green ETL job tells
you nothing about the data. Across the check layers: schema catches 1,
expectations (the Great-Expectations-style workhorse) catch 8, referential
integrity 2, reconciliation 7, distribution 1 — and 2 defects slip past every
check. The layers are complementary: reconciliation *alone* catches a silent row
drop, a non-idempotent load, and a scale error that the per-row expectation suite
is structurally blind to; referential *alone* catches an orphaned key; and a
valid-but-wrong value (a country silently changed to a different real country)
escapes everything.**

Assay is a small retail-orders ETL — extract three seeded source tables, join and
derive an enriched warehouse table, load into SQLite — plus a suite of
data-quality checks. A harness injects a catalog of 15 realistic defects (14 real,
1 benign) one at a time and measures which check catches which.

| Check | Defects caught (of 14) | What it uniquely owns |
|---|---|---|
| `pipeline_ran` (the baseline) | **0** | nothing — a job that loads garbage still "succeeds" |
| schema | 1 | missing / mistyped required columns |
| **expectations** (GE-style) | **8** | per-row value rules: not-null, unique, range, regex, in-set, computed-field |
| referential integrity | 2 | foreign keys that don't resolve (orphans) |
| reconciliation | 7 | counts, aggregate sum, idempotency vs source of truth |
| distribution | 1 | numeric drift where every row is individually valid |
| **caught by ≥1** | **12** | |
| **slip past all** | **2** | a valid-but-wrong value; encoding mojibake |

Every number is read from [`reports/`](reports/), written by a real run and
**byte-reproducible** (verified by re-running and diffing). Everything runs on
Python's standard library — no pandas, no cloud, no paid service.

## The point: the checks are complementary, not ranked

- **Expectations are the workhorse but blind to aggregate defects.** Per-row rules
  catch nulls, bad ranges, malformed emails, unknown countries and computed-field
  errors — 8 of 14. But if the transform silently **drops 12% of valid rows**, the
  rows that remain are all perfectly valid, so every per-row check passes.
- **Reconciliation catches what per-row checks can't** (D10, D11, D12): it
  compares the loaded row count and aggregate sum against a known-good source of
  truth, and re-runs the load to check idempotency. It alone catches the silent
  drop, the non-idempotent load, and a 100× scale error.
- **Referential integrity catches the orphan** (D03): a foreign key pointing at a
  customer that doesn't exist — invisible to a value-range check.
- **Distribution catches drift a loose range misses** (D11): a 100× price inflation
  keeps every value a valid positive number inside the range check, but the mean
  jumps far outside its baseline band.
- **Two defects escape everything.** A country silently changed to a *different
  real country* (valid type, valid set, referentially fine, no aggregate effect)
  and an encoding-corrupted name (still a non-null string) slip past all six
  checks — genuine silent-corruption gaps that need row-level reconciliation
  against the source of truth, or a charset/regex expectation, to close.

## What is real, and what is honest about it

- [`pipeline/`](pipeline/) — the ETL: seeded generation, pure transforms, a SQLite
  load. The transform is deliberately *mechanical* (it maps and loads, it does not
  validate or repair) — the honest model of most pipelines, where quality is a
  separate gate.
- [`checks/`](checks/) — the six mechanisms, each a small readable module. The
  expectation suite's vocabulary mirrors Great Expectations
  (`expect_column_values_to_not_be_null`, `_to_be_unique`, `_to_be_between`,
  `_to_be_in_set`, `_to_match_regex`) so the skill transfers to GE / Soda /
  dbt-tests directly.
- [`scoring/`](scoring/) — the defect catalog and the fault-injection harness.
- [`tests/`](tests/) — **18 tests**: property-based (Hypothesis) tests of the pure
  transforms, and meta-tests that pin each check against the defect it owns.

The catch *counts* are illustrative of each check's reach, not an estimate of any
dataset's defect rate — the 15 defects are curated to span classes cleanly. What
is robust is the structure: expectations own per-row values, reconciliation owns
aggregates, referential owns keys, distribution owns drift, and some corruption
escapes automated checking entirely.

## Reproduce it

See [RUN.md](RUN.md). In short:

```bash
pip install -r requirements.txt
python -m pytest tests          # 18 tests (property-based + check meta-tests)
python scoring/score.py         # the finding -> reports/*.json (byte-reproducible)
```

## The notebook

[`docs/Assay-Notebook.pdf`](docs/) is a ~60-page write-up: the ETL, each check
mechanism with its listing, the full catch matrix by defect class, a chapter
tracing four defects (one only reconciliation catches, one only referential, one
only distribution, one nothing catches) through every check, and the map from
these hand-rolled checks to Great Expectations, dbt tests and Soda.
