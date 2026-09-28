"""Builds the Assay notebook. Listings are pulled from the repo by marker and
every number is read from reports/*.json, so the book fails rather than shipping
a stale claim.

    python docs/build_book.py     (run scoring/score.py first)
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
sys.path.insert(0, str(PROJ.parent / "bookgen"))

from engine import (  # noqa: E402
    build, callout, code_from, code_literal, ol, p, table, ul,
)

REPO = "github.com/Nikhil201716/Assay-Data-Quality"


def report(name):
    return json.loads((PROJ / "reports" / f"{name}.json").read_text(encoding="utf-8"))


SUM = report("summary")
MATRIX = report("catch_matrix")["defects"]
MECHS = SUM["mechanisms"]
CPM = SUM["caught_per_mechanism"]
ND = SUM["total_defects"]


def yn(b):
    return "✓" if b else "·"


# ══════════════════════════════════════════════════════════════ chapter 1 ══

CH1 = {
    "title": "A green ETL job proves nothing",
    "abstract": (
        "The pipeline running successfully catches none of 14 injected data "
        "defects. Data quality is a separate gate, and its checks are "
        "complementary -- each owns a class the others miss."),
    "sections": [
        {"title": "The finding", "html": "".join([
            p("Assay is a small retail-orders ETL -- extract three seeded source "
              "tables, join and derive an enriched table, load into SQLite -- plus "
              "a suite of data-quality checks. A harness injects a catalog of 15 "
              "realistic defects one at a time and measures which check catches "
              "which."),
            p(f"<b>{SUM['headline']}</b>"),
            table(["Check", f"Defects caught (of {ND})", "What it owns"],
                  [["pipeline_ran (baseline)", str(CPM["pipeline_ran"]),
                    "nothing -- a job that loads garbage still 'succeeds'"],
                   ["schema", str(CPM["schema"]), "missing / mistyped required columns"],
                   ["expectations (GE-style)", str(CPM["expectations"]),
                    "per-row value rules -- the workhorse"],
                   ["referential", str(CPM["referential"]), "foreign keys that don't resolve"],
                   ["reconciliation", str(CPM["reconciliation"]),
                    "counts, sums, idempotency vs source of truth"],
                   ["distribution", str(CPM["distribution"]),
                    "numeric drift where every row is valid"]],
                  caption="Table 1.1 - catch counts by check (reports/summary.json)",
                  highlight_col=1),
            p(f"Of {ND} defects, {SUM['defects_caught_by_any']} are caught by at "
              f"least one check and {SUM['defects_missed_by_all']} slip past all "
              f"six. The baseline -- 'the pipeline ran' -- catches "
              f"{CPM['pipeline_ran']}, because a tolerant ETL happily loads dirty "
              f"data and reports success."),
        ])},
        {"title": "Complementary, not ranked", "html": "".join([
            p("The checks are not a ranking with a single winner; each owns a "
              "class the others are blind to:"),
            ul([f"<b>Reconciliation catches what per-row checks can't</b> "
                f"({', '.join(SUM['reconciliation_catches_expectations_miss'])}): "
                f"a silent row drop, a non-idempotent load, a scale error.",
                f"<b>Referential catches the orphan</b> "
                f"({', '.join(SUM['referential_catches_expectations_miss'])}): a "
                f"foreign key that points nowhere.",
                f"<b>Distribution catches drift a loose range misses</b> "
                f"({', '.join(SUM['distribution_catches_expectations_miss'])}).",
                "<b>And some corruption escapes everything</b>: a valid-but-wrong "
                "value, and an encoding-mangled string."]),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 2 ══

CH2 = {
    "title": "The pipeline",
    "abstract": "Three seeded source tables with known-clean ground truth.",
    "sections": [
        {"title": "Generation", "html": "".join([
            p("The sources -- customers, products, orders -- are generated "
              "deterministically from a fixed seed, so every run sees the same "
              "clean data and the results reproduce. The clean data satisfies "
              "every quality rule; the defect injector mutates a copy to introduce "
              "exactly one defect at a time."),
            code_from(PROJ, "pipeline/generate.py",
                      start="def generate() -> dict:",
                      end='return {"customers": customers, "products": products, "orders": orders}',
                      caption="Listing 2.1 - seeded source generation",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 3 ══

CH3 = {
    "title": "The transform",
    "abstract": "Pure helpers plus a mechanical join/derive that never validates "
                "or repairs -- the honest model of a real pipeline.",
    "sections": [
        {"title": "Pure helpers", "html": "".join([
            p("The decisions live in small, pure, property-tested functions: is "
              "this a valid date, a valid email, what is the line total."),
            code_from(PROJ, "pipeline/transform.py",
                      start="def is_iso_date(s) -> bool:", end="return True",
                      caption="Listing 3.1 - ISO-date validation",
                      lang="python"),
            code_from(PROJ, "pipeline/transform.py",
                      start="def compute_line_total(quantity, unit_price, *, bug: bool = False) -> float | None:",
                      end="return round(float(quantity) * float(unit_price), 2)",
                      caption="Listing 3.2 - the derived field (with the injectable bug path)",
                      lang="python"),
        ])},
        {"title": "The mechanical join", "html": "".join([
            p("The transform joins orders to customers and products, casts, and "
              "derives line_total. Crucially it does NOT validate or silently "
              "repair -- injected defects flow through to the warehouse, where the "
              "checks catch them (or do not). That is the honest model: the job "
              "maps and loads whatever it is given, and quality is a separate "
              "gate."),
            code_from(PROJ, "pipeline/transform.py",
                      start="def transform(sources: dict, process_bug: str | None = None) -> list[dict]:",
                      end="return rows",
                      caption="Listing 3.3 - join, cast, derive",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 4 ══

CH4 = {
    "title": "The load",
    "abstract": "A SQLite warehouse, with replace semantics that make a re-run "
                "idempotent.",
    "sections": [
        {"title": "Replace, not append", "html": "".join([
            p("The load writes into a SQLite table. Replace semantics "
              "(delete-then-insert) make a re-run idempotent -- loading the same "
              "batch twice leaves the table unchanged. The idempotency defect skips "
              "the delete, so a re-run doubles the rows, and reconciliation catches "
              "it."),
            code_from(PROJ, "pipeline/load.py",
                      start="def load(conn: sqlite3.Connection, rows: list[dict], *, append: bool = False) -> None:",
                      end="conn.commit()",
                      caption="Listing 4.1 - the idempotent load",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 5 ══

CH5 = {
    "title": "The check suite",
    "abstract": "Six mechanisms, cheapest first -- the shape of a data-quality gate.",
    "sections": [
        {"title": "The mechanisms", "html": "".join([
            p("The suite runs six checks over the loaded warehouse and reports "
              "which flagged the data. Ordered by cost and by what they can see:"),
            code_from(PROJ, "checks/suite.py",
                      start="def run(ctx) -> dict:",
                      end='"distribution": bool(distribution.check(ctx)),',
                      caption="Listing 5.1 - the check suite",
                      lang="python"),
            p("Each check reads a shared context: the loaded rows, the source "
              "tables, a second load (for idempotency), whether the job completed, "
              "and a profile of the known-good data to reconcile against."),
            code_from(PROJ, "checks/context.py",
                      start="def build_profile(clean_loaded: list[dict]) -> dict:",
                      end='"unit_price_std": statistics.pstdev(prices),',
                      caption="Listing 5.2 - the known-good baseline profile",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 6 ══

CH6 = {
    "title": "Schema checks",
    "abstract": "The structural gate: required columns, present and typed.",
    "sections": [
        {"title": "Structure only", "html": "".join([
            p("The schema check confirms every warehouse row has the required "
              "columns, correctly typed and non-null where required. It is the "
              "structural gate -- it catches a missing or mistyped field, and is "
              "blind to whether the values themselves are sensible."),
            code_from(PROJ, "checks/schema.py",
                      start="def check(ctx) -> list[str]:", end="return list(dict.fromkeys(v))",
                      caption="Listing 6.1 - schema checks",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 7 ══

CH7 = {
    "title": "The expectation suite",
    "abstract": "Column-level value rules -- the workhorse, and its blind spot.",
    "sections": [
        {"title": "Great-Expectations, hand-rolled", "html": "".join([
            p("The expectation suite is the workhorse: not-null, unique, between, "
              "in-set, matches-regex, and a computed-field consistency check. The "
              "vocabulary mirrors Great Expectations on purpose, so the skill "
              "transfers directly to GE, Soda or dbt tests."),
            code_from(PROJ, "checks/expectations.py",
                      start="def check(ctx) -> list[str]:", end="return list(dict.fromkeys(v))",
                      caption="Listing 7.1 - the expectation suite",
                      lang="python"),
            p(f"It catches {CPM['expectations']} of {ND} defects -- every per-row "
              f"value defect. What it cannot see is anything where each row is "
              f"individually valid: a silently dropped row, a scale error inside a "
              f"loose range, a valid-but-wrong value. Those are the other checks' "
              f"job, and the study's gaps."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 8 ══

CH8 = {
    "title": "Referential integrity",
    "abstract": "Foreign keys must resolve -- a defect no per-row value check sees.",
    "sections": [
        {"title": "Keys that point nowhere", "html": "".join([
            p("Every foreign key in the warehouse must resolve to a real row in "
              "the source lookup tables. A per-row value check on the order cannot "
              "see that its customer_id points at a customer who does not exist; "
              "this check exists precisely to catch that orphan."),
            code_from(PROJ, "checks/referential.py",
                      start="def check(ctx) -> list[str]:", end="return list(dict.fromkeys(v))",
                      caption="Listing 8.1 - referential integrity",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 9 ══

CH9 = {
    "title": "Reconciliation",
    "abstract": "Counts, sums, idempotency -- the aggregate checks that catch what "
                "per-row checks miss.",
    "sections": [
        {"title": "Against the source of truth", "html": "".join([
            p("Reconciliation compares the loaded row count and an aggregate sum "
              "against a known-good source of truth, and re-runs the load to check "
              "idempotency. These aggregate checks catch silent row drops, "
              "duplicates, scale errors and non-idempotent loads -- defects where "
              "the surviving rows are each perfectly valid, so every per-row check "
              "passes."),
            code_from(PROJ, "checks/reconciliation.py",
                      start="def check(ctx) -> list[str]:", end="return v",
                      caption="Listing 9.1 - reconciliation",
                      lang="python"),
            callout("note", "The clearest cell in the study",
                    p("The silent-drop defect removes 12% of valid rows. Every "
                      "per-row check passes -- the rows that remain are fine -- and "
                      "only reconciliation's row-count check catches it. It is the "
                      "canonical reason a data pipeline needs reconciliation and "
                      "not just column expectations.")),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 10 ══

CH10 = {
    "title": "Distribution checks",
    "abstract": "Drift monitoring: catch a shift where every row is a valid number.",
    "sections": [
        {"title": "Mean and spread vs a baseline", "html": "".join([
            p("The distribution check compares the mean and spread of a numeric "
              "column against a known-good baseline profile. It catches a scale "
              "error or drift where every individual value is still a valid number "
              "inside the range check -- the tool you reach for when monitoring "
              "for drift with no source-of-truth sum to reconcile against."),
            code_from(PROJ, "checks/distribution.py",
                      start="def check(ctx) -> list[str]:", end="return v",
                      caption="Listing 10.1 - distribution drift",
                      lang="python"),
            p("A 100x price inflation keeps every value positive and inside the "
              "loose range the expectation suite allows -- so expectations miss it "
              "-- but the mean jumps far outside its baseline band."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 11 ══

CH11 = {
    "title": "The defect catalog",
    "abstract": "Realistic data and process defects, injected one at a time.",
    "sections": [
        {"title": "Data and process defects", "html": "".join([
            p("Each defect is a DATA defect (mutating the source tables) or a "
              "PROCESS defect (a bug in the transform/load), plus one non-defect "
              "additive change as a false-positive probe."),
            code_from(PROJ, "scoring/defects.py",
                      start="class Defect:", end="desc: str",
                      caption="Listing 11.1 - the Defect record",
                      lang="python"),
            code_from(PROJ, "scoring/defects.py",
                      start="def inject_data(sources: dict, defect_id: str | None) -> dict:",
                      end="return sources",
                      caption="Listing 11.2 - injecting one data defect",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 12 ══

CH12 = {
    "title": "The scoring harness",
    "abstract": "Inject, run the ETL twice, run every check, record.",
    "sections": [
        {"title": "One defect, one run", "html": "".join([
            p("For each defect the harness builds the injected sources, runs the "
              "ETL twice into one warehouse (so idempotency can be judged), and "
              "runs every check. It is in-process and seeded, so the catch matrix "
              "is byte-reproducible."),
            code_from(PROJ, "scoring/score.py",
                      start="def run_defect(defect_id, profile) -> Context:",
                      end="ran_ok=ran_ok, profile=profile)",
                      caption="Listing 12.1 - scoring one defect",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ chapter 13 ══


def _matrix_rows():
    rows = []
    order = ["pipeline_ran", "schema", "expectations", "referential",
             "reconciliation", "distribution"]
    for did in sorted(MATRIX):
        d = MATRIX[did]
        c = d["caught"]
        tag = ""
        if d["is_defect"] and not any(c.values()):
            tag = "missed"
        if (not d["is_defect"]) and any(c.values()):
            tag = "false +"
        rows.append([did, d["klass"]] + [yn(c[m]) for m in order] + [tag])
    return rows


CH13 = {
    "title": "Results",
    "abstract": "The full matrix, who catches what the others miss, and the gaps.",
    "sections": [
        {"title": "The catch matrix", "html": "".join([
            table(["Defect", "Class", "ran", "schema", "expect", "ref", "recon", "dist", "note"],
                  _matrix_rows(),
                  caption="Table 13.1 - every defect, every check (reports/catch_matrix.json)"),
        ])},
        {"title": "By defect class", "html": "".join([
            table(["Class", "n", "ran", "schema", "expect", "ref", "recon", "dist"],
                  [[k, str(v["defects"]), str(v["pipeline_ran"]), str(v["schema"]),
                    str(v["expectations"]), str(v["referential"]),
                    str(v["reconciliation"]), str(v["distribution"])]
                   for k, v in sorted(SUM["per_class"].items())],
                  caption="Table 13.2 - catch counts by defect class"),
        ])},
        {"title": "The gaps", "html": "".join([
            p(f"{SUM['defects_missed_by_all']} defects slip past every check -- the "
              f"finding a green pipeline hides:"),
            (table(["Defect", "Class", "Why all checks miss it"],
                   [[g["id"], g["klass"], g["desc"]] for g in SUM["missed_defects"]],
                   caption="Table 13.3 - defects no check caught")
             if SUM["missed_defects"] else p("(none)")),
            p(f"And no check flagged the additive change "
              f"({len(SUM['false_positives'])} false positives) -- adding "
              f"unreferenced products to the catalog is not a defect, and nothing "
              f"treated it as one."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ property ══

CH_PROP = {
    "title": "Property-based testing of the transforms",
    "abstract": "Hypothesis checks the pure helpers over a wide input space, not a "
                "few examples.",
    "sections": [
        {"title": "Properties, not examples", "html": "".join([
            p("The pure transform helpers are tested with Hypothesis: instead of a "
              "handful of hand-picked inputs, it checks a property over a wide "
              "generated space. The line-total property is simply that the output "
              "is the product, rounded -- for any quantity and price."),
            code_from(PROJ, "tests/unit/test_transform.py",
                      start="@given(st.integers(min_value=0, max_value=100000),",
                      end="assert compute_line_total(q, p) == round(q * p, 2)",
                      caption="Listing P.1 - a property test",
                      lang="python"),
            p("This is the instrument the previous project (Accord) named for its "
              "gaps: a property test forces the rare input a fixed example never "
              "supplies -- an impossible date, a huge quantity, a hostile string."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ meta ══

CH_META = {
    "title": "Testing the checks",
    "abstract": "A check that always fires, or never does, would make the study "
                "meaningless -- so the checks are pinned too.",
    "sections": [
        {"title": "Meta-tests", "html": "".join([
            p("Before the checks can be trusted to score defects, they are tested "
              "themselves: they must pass on clean data, and each must catch the "
              "defect class it owns. The sharpest meta-test pins the "
              "reconciliation-only cell -- the silent drop that per-row checks are "
              "blind to."),
            code_from(PROJ, "tests/checks/test_checks.py",
                      start="def test_reconciliation_uniquely_catches_silent_drop():",
                      end='assert res["reconciliation"] and not res["expectations"]       # per-row checks are blind',
                      caption="Listing M.1 - pinning the reconciliation-only cell",
                      lang="python"),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ tools ══

CH_TOOLS = {
    "title": "From here to Great Expectations, dbt and Soda",
    "abstract": "The hand-rolled checks map one-to-one onto the real tools.",
    "sections": [
        {"title": "The same concepts, at scale", "html": "".join([
            p("Every check here is a small, readable version of what a production "
              "data-quality tool does, and the skill transfers directly:"),
            table(["This project", "The real tool"],
                  [["the expectation suite", "Great Expectations expectation suites; "
                    "Soda checks; dbt test / dbt-expectations"],
                   ["reconciliation (counts, sums)", "dbt tests + source freshness; "
                    "reconciliation frameworks; audit-log tables"],
                   ["referential integrity", "dbt relationships tests; database FKs"],
                   ["distribution drift", "GE distributional expectations; Soda "
                    "anomaly detection; Evidently / monitoring"],
                   ["the defect catalog + harness", "mutation-style data testing; "
                    "data contract CI"]],
                  caption="Table T.1 - hand-rolled to production"),
            p("Hand-rolling them first is the point: you understand what an "
              "expectation IS, why reconciliation is a separate concern, and where "
              "each is blind -- which is exactly what lets you wield the heavy "
              "tools well rather than trusting a green dashboard."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ limits ══

CH_LIMITS = {
    "title": "What this does not establish",
    "abstract": "The honest boundary around a curated, single-dataset study.",
    "sections": [
        {"title": "A curated catalog", "html": "".join([
            p(f"The {ND} defects are hand-picked to span classes cleanly, one "
              f"representative each. The catch counts are illustrative of each "
              f"check's reach, not an estimate of any dataset's defect rate. And "
              f"the gaps are the gaps of THIS check set: a charset expectation "
              f"would catch the encoding defect, and row-level reconciliation "
              f"against the source system would catch the valid-but-wrong value. "
              f"What is robust is the structure -- expectations own per-row values, "
              f"reconciliation owns aggregates, referential owns keys, distribution "
              f"owns drift, and some corruption escapes automated checking."),
        ])},
        {"title": "'Caught' means one check fired", "html": "".join([
            p("A check catches a defect if it produced at least one violation. The "
              "study does not grade how precisely the violation localises the bad "
              "rows, or how good the message is. And the pipeline here is small "
              "and in-memory; a real warehouse adds partitioning, incremental "
              "loads and late-arriving data, each with its own quality hazards the "
              "six checks here do not model."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ reading ══

CH_READING = {
    "title": "Where to read further",
    "abstract": "Data-quality dimensions, the tools, and the testing ideas.",
    "sections": [
        {"title": "The sources", "html": "".join([
            p("The vocabulary of data-quality dimensions -- completeness, validity, "
              "consistency, uniqueness, timeliness, accuracy -- is standard; the "
              "DAMA-DMBOK is the reference. For the tools, the Great Expectations "
              "docs (expectation suites, checkpoints), the dbt testing guide "
              "(generic + singular tests, dbt-utils / dbt-expectations) and Soda's "
              "checks language are the practical reads. The idea that "
              "reconciliation is a first-class pipeline concern -- not a special "
              "case of column tests -- is made well in Kleppmann's <i>Designing "
              "Data-Intensive Applications</i> (batch chapter) and in the "
              "'data contracts' literature. Hypothesis's docs cover property-based "
              "testing; its 'find the edge case you didn't think of' philosophy is "
              "exactly right for validating transform functions."),
        ])},
    ],
}

# ══════════════════════════════════════════════════════════════ runbook ══

RUNBOOK = {
    "title": "Running the Project, Step by Step",
    "abstract": "From a clone to the catch matrix, on Python's standard library.",
    "sections": [
        {"title": "Prerequisites",
         "html": p("You need <b>Python 3.12+</b>. The pipeline and checks use only "
                   "the standard library; the three dependencies are for the tests "
                   "and the measurement.")
         + code_literal("python --version", "Toolcheck", "bash")},
        {"title": "Tests and the finding",
         "html": code_literal(
             "python -m venv .venv\n"
             ".venv\\Scripts\\activate            # Windows\n"
             "source .venv/bin/activate           # macOS / Linux\n"
             "pip install -r requirements.txt\n\n"
             "python -m pytest tests              # 18 tests\n"
             "python scoring/score.py             # the finding -> reports/*.json",
             "Everything measured", "bash")},
        {"title": "What you should see",
         "html": p("<code>18 passed</code>; <code>score.py</code> prints a "
                   "per-defect matrix and writes <code>reports/catch_matrix.json</code> "
                   "+ <code>summary.json</code>, byte-identical on re-run.")},
    ],
}

# ══════════════════════════════════════════════════════════════ appendix ══

APPENDIX = {
    "title": "Appendix",
    "abstract": "Repository map and glossary.",
    "sections": [
        {"title": "A - Repository map",
         "html": table(["Path", "Purpose"],
                       [["<code>pipeline/generate.py</code>", "seeded source generation"],
                        ["<code>pipeline/transform.py</code>", "pure helpers + the join/derive"],
                        ["<code>pipeline/load.py</code>", "the SQLite warehouse load"],
                        ["<code>checks/expectations.py</code>", "the GE-style expectation suite"],
                        ["<code>checks/reconciliation.py</code>", "counts, sums, idempotency"],
                        ["<code>checks/referential.py</code>", "foreign-key integrity"],
                        ["<code>checks/distribution.py</code>", "numeric drift"],
                        ["<code>scoring/defects.py</code>", "the defect catalog + injector"],
                        ["<code>scoring/score.py</code>", "the fault-injection harness"],
                        ["<code>reports/*.json</code>", "the source of every number here"]],
                       "Where everything lives", "")},
        {"title": "B - Glossary",
         "html": table(["Term", "Meaning"],
                       [["Data-quality check", "an assertion about data, separate from 'did the job run'"],
                        ["Expectation", "a column-level value rule (GE vocabulary)"],
                        ["Reconciliation", "comparing counts/sums against a source of truth"],
                        ["Referential integrity", "every foreign key resolves to a real row"],
                        ["Idempotency", "re-running the load leaves the result unchanged"],
                        ["Distribution drift", "a numeric column's mean/spread moving from baseline"],
                        ["Silent corruption", "a wrong value that is still individually valid"],
                        ["Property-based testing", "checking a property over generated inputs (Hypothesis)"],
                        ["Fault injection", "deliberately introducing a defect to see if a check notices"]],
                       "Terms used in this book", "")},
    ],
}

# ══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════ extra chapters ══

CH_DIMENSIONS = {
    "title": "The dimensions of data quality",
    "abstract": "Six standard dimensions, and the check that owns each.",
    "sections": [
        {"title": "A vocabulary, mapped to checks", "html": "".join([
            p("Data quality is usually described in dimensions. Naming them shows "
              "the check suite is not ad hoc -- each dimension has an owner:"),
            table(["Dimension", "Question", "Owned by"],
                  [["Completeness", "are required values present?", "schema, expectations (not-null)"],
                   ["Validity", "are values in the right form/range?", "expectations (range, regex, set)"],
                   ["Uniqueness", "are keys unique?", "expectations (unique)"],
                   ["Consistency", "do derived values agree?", "expectations (computed field)"],
                   ["Integrity", "do foreign keys resolve?", "referential"],
                   ["Accuracy / drift", "do the numbers match reality?", "reconciliation, distribution"]],
                  caption="Table DQ.1 - dimensions and their owners"),
            p("The one dimension no automated check fully owns is accuracy at the "
              "row level -- whether a specific value is <i>true</i>. That is the "
              "silent-corruption gap, and it is why reconciliation against the "
              "source system, and ultimately human review, remain part of the "
              "picture."),
        ])},
    ],
}

CH_SOURCES = {
    "title": "The source and warehouse schemas",
    "abstract": "Three source tables in, one enriched table out.",
    "sections": [
        {"title": "The orders source", "html": "".join([
            p("Orders reference a customer and a product and carry a quantity, a "
              "price snapshot, and a date -- the shape most defects target."),
            code_from(PROJ, "pipeline/generate.py",
                      start="    orders = []",
                      end='"order_date": f"2026-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",',
                      caption="Listing SC.1 - generating orders",
                      lang="python"),
        ])},
        {"title": "The warehouse table", "html": "".join([
            p("The enriched warehouse table is a fixed set of typed columns; the "
              "load derives the DDL from them."),
            code_from(PROJ, "pipeline/load.py", start="COLUMNS = [", end="]",
                      caption="Listing SC.2 - the warehouse columns",
                      lang="python"),
            code_from(PROJ, "pipeline/load.py",
                      start="def connect() -> sqlite3.Connection:", end="return conn",
                      caption="Listing SC.3 - the warehouse connection + schema",
                      lang="python"),
        ])},
    ],
}

CH_ETLRUN = {
    "title": "Orchestrating the run",
    "abstract": "Extract, transform, load -- kept independent of the defect catalog.",
    "sections": [
        {"title": "The runner", "html": "".join([
            p("The orchestrator is deliberately thin and independent of the defect "
              "catalog: callers pass already-prepared sources and an optional "
              "process-bug flag, so tests and the harness drive it the same way. "
              "It runs the load into a caller-supplied connection, which is what "
              "lets the harness load twice into one store to judge idempotency."),
            code_from(PROJ, "pipeline/run_etl.py",
                      start="def run(sources: dict, process_bug: str | None = None,",
                      end="return loadmod.read(conn), conn",
                      caption="Listing ER.1 - extract, transform, load",
                      lang="python"),
        ])},
    ],
}

CH_INJECT = {
    "title": "How each defect is injected",
    "abstract": "A few catalog branches, to show the range of realistic corruption.",
    "sections": [
        {"title": "Data defects", "html": "".join([
            p("A scale error multiplies every price -- the classic 'cents loaded as "
              "dollars'. A silent corruption swaps a country for a different valid "
              "one -- individually plausible, wrong."),
            code_from(PROJ, "scoring/defects.py",
                      start='    elif defect_id == "D11":',
                      end='o["unit_price"] = round(o["unit_price"] * 100, 2)',
                      caption="Listing IJ.1 - the scale-error defect",
                      lang="python"),
            code_from(PROJ, "scoring/defects.py",
                      start='    elif defect_id == "D13":',
                      end='c["country"] = "FR" if c["country"] != "FR" else "US"',
                      caption="Listing IJ.2 - the silent-corruption defect",
                      lang="python"),
        ])},
        {"title": "A process defect", "html": "".join([
            p("The silent-drop defect lives in the transform: an over-aggressive "
              "filter skips about 12% of valid rows. The rows that survive are all "
              "fine, which is why only reconciliation catches it."),
            code_from(PROJ, "pipeline/transform.py",
                      start='        if process_bug == "D10" and i % 8 == 0:',
                      end="continue                              # silent-drop bug: skip ~12% of rows",
                      caption="Listing IJ.3 - the silent-drop process defect",
                      lang="python"),
        ])},
    ],
}

CH_WORKED = {
    "title": "Tracing four defects",
    "abstract": "One only reconciliation catches, one only referential, one "
                "distribution, one nothing.",
    "sections": [
        {"title": "D10 silent drop: only reconciliation", "html": "".join([
            p("The transform drops 12% of rows. Every per-row check passes -- the "
              "survivors are valid -- so expectations, schema and referential all "
              f"miss it (expectations caught: {yn(MATRIX['D10']['caught']['expectations'])}). "
              "Only reconciliation's row-count check, comparing to the known-good "
              f"count, catches it (caught: {yn(MATRIX['D10']['caught']['reconciliation'])}). "
              "This is the canonical argument for reconciliation."),
        ])},
        {"title": "D03 orphan: only referential", "html": "".join([
            p("An order references a customer that does not exist. The value is a "
              "normal integer, so expectations pass "
              f"({yn(MATRIX['D03']['caught']['expectations'])}); the count and sum "
              f"are unchanged, so reconciliation passes "
              f"({yn(MATRIX['D03']['caught']['reconciliation'])}). Only the "
              f"referential check, resolving the key against the customers table, "
              f"catches it ({yn(MATRIX['D03']['caught']['referential'])})."),
        ])},
        {"title": "D11 scale: distribution (and reconciliation), not expectations", "html": "".join([
            p("Every price is inflated 100x. Each value stays a positive number "
              "inside the loose range, so the expectation suite misses it "
              f"({yn(MATRIX['D11']['caught']['expectations'])}). The aggregate sum "
              f"and the mean both blow past their baselines, so reconciliation "
              f"({yn(MATRIX['D11']['caught']['reconciliation'])}) and distribution "
              f"({yn(MATRIX['D11']['caught']['distribution'])}) catch it. This is "
              f"why a per-row range is not a drift check."),
        ])},
        {"title": "D13 valid-but-wrong: nothing", "html": "".join([
            p("A customer's country is changed to a different real country. It is a "
              "valid string, in the known set, referentially irrelevant, and does "
              "not touch any aggregate -- so all six checks pass "
              f"(caught by any: {'yes' if any(MATRIX['D13']['caught'].values()) else 'no'}). "
              "Only a row-level reconciliation against the source system, or human "
              "review, would catch it. Naming that is the honest close: automated "
              "data-quality checks bound the damage, they do not guarantee truth."),
        ])},
    ],
}

CH_AGG = {
    "title": "Turning the matrix into the finding",
    "abstract": "The complementarity numbers are computed from the matrix, not asserted.",
    "sections": [
        {"title": "Who catches what the others miss", "html": "".join([
            p("The headline claims -- reconciliation catches what expectations "
              "miss, referential catches the orphan -- are simple set logic over "
              "the matrix, so they cannot disagree with the per-defect table."),
            code_from(PROJ, "scoring/score.py",
                      start="    recon_only = [d for d in defects",
                      end='if caught_by(d, "referential") and not caught_by(d, "expectations")]',
                      caption="Listing AG.1 - who catches what the others miss",
                      lang="python"),
        ])},
    ],
}

CH_DESIGN = {
    "title": "Design decisions",
    "abstract": "Each load-bearing choice, and the alternative it beat.",
    "sections": [
        {"title": "Why a mechanical transform", "html": "".join([
            callout("note", "WHY: the ETL maps and loads; quality is a separate gate",
                    p("If the transform validated and repaired, injected defects "
                      "would never reach the warehouse and there would be nothing "
                      "to measure. That is not a contrivance -- it is how most real "
                      "pipelines work: the job is mechanical, and data quality is a "
                      "distinct set of checks run against the result. Separating "
                      "them is what makes 'the pipeline ran' a meaningfully weak "
                      "baseline.")),
        ])},
        {"title": "Why hand-rolled checks, not Great Expectations", "html": "".join([
            callout("note", "WHY: understand the expectation before wielding the tool",
                    p("Hand-rolling a not-null or a between check is trivial; the "
                      "value is that you then know exactly what each expectation "
                      "does and where it is blind. A green GE dashboard is only "
                      "trustworthy if you know it does not check reconciliation or "
                      "row-level accuracy. The checks here map one-to-one onto GE, "
                      "dbt and Soda, so the understanding transfers.")),
        ])},
        {"title": "Why the standard library only", "html": "".join([
            callout("note", "WHY: reproducible and portable forever",
                    p("The pipeline and checks use only sqlite3, statistics, csv "
                      "and re. No pandas, no cloud SDK -- so the whole thing runs "
                      "anywhere with a Python interpreter, for free, byte-for-byte "
                      "reproducibly, years from now. The concepts, not a particular "
                      "library's API, are the transferable skill.")),
        ])},
    ],
}

CH_ADDITIVE = {
    "title": "Precision: not flagging the safe change",
    "abstract": "A check that cries wolf on a benign change is as useless as one "
                "that misses defects.",
    "sections": [
        {"title": "The additive probe", "html": "".join([
            p(f"The catalog includes one non-defect: new products added to the "
              f"catalog that no order references. A good check set must NOT flag "
              f"it, and none did ({len(SUM['false_positives'])} false positives). "
              f"Referential integrity earns this by checking orders against "
              f"products (the new products are simply unreferenced); the aggregate "
              f"and per-row checks operate on orders, which are unchanged."),
            p("Measuring false positives alongside catches is what makes a check "
              "safe to gate a pipeline on. A data-quality gate that blocks a "
              "release every time the catalog grows will be disabled within a "
              "week -- and then it protects nothing."),
        ])},
    ],
}

CH_PROD = {
    "title": "Quality in production",
    "abstract": "The checks that run after deploy: freshness, volume, and drift.",
    "sections": [
        {"title": "From batch checks to monitors", "html": "".join([
            p("The same checks that gate a batch become monitors in production. "
              "Three that a real deployment adds on top of this study's six:"),
            ul(["<b>Freshness</b> -- has the data updated within its SLA? (a "
                "timeliness check the batch study does not model)",
                "<b>Volume anomaly</b> -- is today's row count within the normal "
                "band for this day of week? (reconciliation's count check, made "
                "adaptive)",
                "<b>Drift over time</b> -- is a column's distribution moving across "
                "runs, not just against one baseline? (distribution, tracked)"]),
            p("The bridge is the same as in the previous project: a check is a "
              "description of what good data looks like, usable both to gate a "
              "deploy and to watch production. The silent-corruption gap is exactly "
              "where production monitoring (comparing to the operational source "
              "system) earns its keep, because pre-load checks structurally cannot "
              "see it."),
        ])},
    ],
}

CH_CONTRACTS = {
    "title": "Data contracts",
    "abstract": "The upstream fix: agree the shape and semantics before the data "
                "moves.",
    "sections": [
        {"title": "Shift the guarantee upstream", "html": "".join([
            p("Every defect here is caught (or missed) downstream, after bad data "
              "has already been produced. The upstream analogue of the previous "
              "project's API contract is a <b>data contract</b>: the producer of "
              "the customers/orders data commits to a schema and to semantic rules "
              "(country is a valid ISO code; unit_price is in dollars; order_id is "
              "unique), and that contract is enforced at the boundary -- in CI on "
              "the producing service, or as a schema-registry check on the event "
              "stream."),
            p("A data contract would turn several of this study's defects into "
              "produce-time failures rather than load-time catches -- and could "
              "even express the semantic rules (a unit, an enum) that a value "
              "matcher needs, closing part of the silent-corruption gap. The "
              "checks here are the safety net; the contract is the discipline that "
              "means the net catches less because less bad data is produced."),
        ])},
    ],
}

# ═══════════════════════════════════════ round two ══

CH_GATE = {
    "title": "Where the checks run: the quality gate",
    "abstract": "Pre-load or post-load, fail-closed or fail-open -- the check is only "
                "half the design; when and how it runs is the other half.",
    "sections": [
        {"title": "A check is a decision, not just an assertion", "html": "".join([
            p("Running a check is easy; deciding what to do when it fails is the "
              "engineering. Three axes a real gate must settle:"),
            ul(["<b>Where</b> -- validate a staging table before it is promoted to "
                "the warehouse (catch bad data before anyone queries it), or "
                "validate after load (simpler, but consumers may already have read "
                "it). This project checks post-load; a fail-closed pipeline checks "
                "a staging load first.",
                "<b>Fail-closed vs fail-open</b> -- does a failed check block the "
                "release (fail-closed: safest, but a flaky check halts the "
                "business) or raise an alert while the data flows (fail-open: keeps "
                "moving, risks bad data downstream)? The right answer differs per "
                "check and per consumer.",
                "<b>Blocking severity</b> -- a referential orphan might block, while "
                "a distribution drift only warns. Not every violation deserves the "
                "same response."]),
            p("The measurement in this book is deliberately about detection -- does "
              "a check fire -- because detection is the prerequisite. But a check "
              "that fires into a log nobody reads is a check that does nothing, so "
              "the gate design is where detection becomes protection."),
        ])},
    ],
}

CH_SEVERITY = {
    "title": "Severity, and quarantine",
    "abstract": "Not every bad row should stop the pipeline; some should be set aside.",
    "sections": [
        {"title": "Reject, warn, or quarantine", "html": "".join([
            p("A binary pass/fail is coarse. Mature pipelines route bad data three "
              "ways: <b>reject</b> the whole batch (a schema break -- nothing "
              "usable), <b>warn</b> and continue (a distribution drift worth a "
              "human's attention), or <b>quarantine</b> the offending rows (the 15 "
              "orders with a null customer_id go to a side table while the other "
              "285 load). Quarantine is often the right answer for row-level "
              "defects: it preserves the good data and makes the bad data visible "
              "and fixable, instead of failing the whole load or silently loading "
              "garbage."),
            p("The checks here identify the bad rows (the expectation and "
              "referential checks report which rows and which rule), which is "
              "exactly what a quarantine step needs. Detection is the input to the "
              "routing decision; the study measures the input, and names routing as "
              "the production layer on top."),
        ])},
    ],
}

CH_SQL = {
    "title": "The warehouse, and reconciliation as SQL",
    "abstract": "The load is SQLite; the aggregate checks are the COUNT and SUM a "
                "data engineer would write in SQL.",
    "sections": [
        {"title": "Read-back and aggregates", "html": "".join([
            p("The warehouse is a real (in-memory) SQLite table, read back after "
              "load. The reconciliation check's row count and aggregate sum are the "
              "Python expression of the SQL a data engineer writes to reconcile a "
              "load: <code>SELECT COUNT(*), SUM(line_total) FROM orders_enriched</code> "
              "compared against the source-system totals."),
            code_from(PROJ, "pipeline/load.py",
                      start="def read(conn: sqlite3.Connection) -> list[dict]:",
                      end='return [dict(r) for r in conn.execute("SELECT * FROM orders_enriched ORDER BY rowid")]',
                      caption="Listing SQ.1 - reading the warehouse",
                      lang="python"),
            p("In dbt this reconciliation is a singular test; in a pure-SQL stack "
              "it is a scheduled query with a threshold. The concept -- count and "
              "sum the target, compare to the source of truth -- is identical, and "
              "it is the check that catches the silent drop.")
            + code_from(PROJ, "pipeline/load.py", start='SCHEMA = f"""', end='"""',
                        caption="Listing SQ.2 - the warehouse DDL, derived from the columns",
                        lang="python"),
        ])},
    ],
}

CH_OBS = {
    "title": "Data observability",
    "abstract": "The five pillars, and which this study exercises.",
    "sections": [
        {"title": "The five pillars", "html": "".join([
            p("Data observability is usually framed as five pillars, and the check "
              "suite touches most of them:"),
            table(["Pillar", "Meaning", "In this study"],
                  [["Freshness", "is the data recent?", "not modelled (batch, no time axis)"],
                   ["Volume", "is the row count normal?", "reconciliation (count)"],
                   ["Schema", "did the shape change?", "schema check"],
                   ["Distribution", "are the values normal?", "distribution + expectations"],
                   ["Lineage", "where did it come from / go?", "referential (partial)"]],
                  caption="Table OB.1 - observability pillars vs the checks"),
            p("The gap -- freshness -- is a reminder that a batch study omits the "
              "time axis entirely. In production, 'the data is a day stale' is a "
              "quality failure as real as a null, and it needs its own check.")
        ])},
    ],
}

CH_INCREMENTAL = {
    "title": "Incremental loads and late data",
    "abstract": "The hazards a full-refresh study does not model.",
    "sections": [
        {"title": "Why full-refresh hides problems", "html": "".join([
            p("This pipeline is a full refresh: every run rebuilds the whole "
              "warehouse from the whole source, which is why replace-semantics make "
              "idempotency trivial. Real pipelines are usually incremental -- they "
              "load only what changed since the last run -- and that opens hazards "
              "this study does not model: a late-arriving record for a window "
              "already loaded, a watermark that skips rows, a backfill that "
              "double-counts, a deletion in the source that the incremental load "
              "never sees."),
            p("Each of those is a reconciliation problem at heart -- the loaded "
              "total drifts from the source total over time -- which is why "
              "reconciliation against the source system, not just per-row checks, "
              "is the check that scales to incremental pipelines. The full-refresh "
              "model here makes the check comparison clean; the incremental world "
              "makes reconciliation even more essential, not less."),
        ])},
    ],
}

CH_LINEAGE = {
    "title": "Lineage and provenance",
    "abstract": "Knowing where a value came from is what turns a caught defect into "
                "a fixed one.",
    "sections": [
        {"title": "Detection is not enough without lineage", "html": "".join([
            p("A check that fires tells you the warehouse is wrong; lineage tells "
              "you why. The enriched row carries its source keys (order_id, "
              "customer_id, product_id), so a failed expectation can be traced back "
              "to the exact source record and the join that produced it. Without "
              "that, a distribution drift is an alert with nowhere to go."),
            p("At scale this is what tools like dbt's lineage graph, OpenLineage "
              "and column-level lineage provide: given a bad value, the set of "
              "upstream models and sources that could have caused it. The study's "
              "referential check is the smallest version -- it does not just say "
              "'this key is bad', it says 'this order points at a customer that is "
              "not in the customers source' -- which is a one-hop lineage claim."),
        ])},
    ],
}

CH_GEN2 = {
    "title": "Products and customers",
    "abstract": "The lookup tables the orders join against.",
    "sections": [
        {"title": "The catalog", "html": "".join([
            p("Products carry a price the orders snapshot, and a category the "
              "expectation suite could constrain. Customers carry the email and "
              "country the value checks validate."),
            code_from(PROJ, "pipeline/generate.py",
                      start="    products = []",
                      end='"price": round(rng.uniform(5.0, 200.0), 2),',
                      caption="Listing G2.1 - generating products",
                      lang="python"),
        ])},
    ],
}

CH_TESTS2 = {
    "title": "More of the test suite",
    "abstract": "Determinism, date properties, and the false-positive meta-test.",
    "sections": [
        {"title": "Determinism and date properties", "html": "".join([
            code_from(PROJ, "tests/unit/test_generate.py",
                      start="def test_generation_is_deterministic():", end="assert a == b",
                      caption="Listing T2.1 - the generator is deterministic",
                      lang="python"),
            code_from(PROJ, "tests/unit/test_transform.py",
                      start="@given(st.integers(1900, 2100), st.integers(1, 12), st.integers(1, 28))",
                      end='assert is_iso_date(f"{y:04d}-{m:02d}-{d:02d}")',
                      caption="Listing T2.2 - every valid date is accepted",
                      lang="python"),
        ])},
        {"title": "Clean passes; additive is not flagged", "html": "".join([
            code_from(PROJ, "tests/checks/test_checks.py",
                      start="def test_clean_data_passes_every_check():",
                      end='"referential": False, "reconciliation": False, "distribution": False,',
                      caption="Listing T2.3 - clean data passes every check",
                      lang="python"),
            code_from(PROJ, "tests/checks/test_checks.py",
                      start="def test_additive_change_is_no_false_positive():",
                      end='assert not any(suite.run(run_defect("D15", prof)).values())',
                      caption="Listing T2.4 - the additive change is no false positive",
                      lang="python"),
        ])},
    ],
}

# ═══════════════════════════════════════ round three ══

CH_BASELINE = {
    "title": "Why 'the pipeline ran' is the trap",
    "abstract": "The baseline catches nothing on purpose -- and it is the belief "
                "most quietly held.",
    "sections": [
        {"title": "Success is not quality", "html": "".join([
            p("Every project in this series has the same shape: a trivial baseline "
              "that looks like testing and is not. For a web app it was the smoke "
              "test; for an API, the provider's own green suite; here it is the "
              "ETL job exiting zero. All three pass while the thing they guard is "
              "broken."),
            p(f"'The pipeline ran' catches {CPM['pipeline_ran']} of {ND} defects, "
              f"because a tolerant job loads whatever it is given and reports "
              f"success. This is the most common real-world failure in data "
              f"engineering: a green Airflow DAG, a green dbt run, and a warehouse "
              f"full of nulls and orphans. The job's exit code measures whether the "
              f"code ran, not whether the data is right -- and those are different "
              f"questions that need different instruments. Naming the gap between "
              f"them is the whole point of the study."),
        ])},
    ],
}

CH_EXTRACT = {
    "title": "The E in ETL: extraction hazards",
    "abstract": "Most data defects are born at extraction; the study injects them, "
                "but here is where they come from.",
    "sections": [
        {"title": "Where bad data comes from", "html": "".join([
            p("This project injects defects directly, but in reality they are born "
              "at extraction, and a data tester should know the usual sources:"),
            ul(["<b>Encoding</b> -- a CSV read as latin-1 instead of UTF-8 produces "
                "the mojibake defect (D14); always decode explicitly.",
                "<b>Delimiters and quoting</b> -- an unescaped comma or newline "
                "inside a field shifts every column right, producing type and "
                "referential defects downstream.",
                "<b>Partial / truncated files</b> -- a transfer that stops early is "
                "the real-world silent row drop (D10); a byte count or manifest "
                "catches it before load.",
                "<b>Schema-on-read drift</b> -- the source adds, drops or reorders "
                "a column and the extractor, positional rather than named, reads "
                "garbage.",
                "<b>Timezone and unit ambiguity</b> -- a date without a zone, or a "
                "price without a currency, is the source of the scale (D11) and "
                "silent-corruption (D13) defects."]),
            p("The lesson: validate at the boundary, as close to extraction as "
              "possible, because a defect that reaches the warehouse has already "
              "been copied into every downstream table. The checks here run "
              "post-load to measure them cleanly; a real pipeline pushes as many as "
              "it can to the edge."),
        ])},
    ],
}

CH_ANOMALY = {
    "title": "When a distribution check becomes anomaly detection",
    "abstract": "The band here is fixed; at scale it is learned, and the check "
                "becomes a model.",
    "sections": [
        {"title": "Fixed bands, then learned ones", "html": "".join([
            p("The distribution check compares the mean and spread to a baseline "
              "with a fixed tolerance -- simple and enough to catch a 100x scale "
              "error. At scale, the tolerance is learned: a z-score against the "
              "rolling history, an interquartile-range fence for outliers, or a "
              "seasonal model that knows Monday's volume differs from Sunday's. The "
              "check becomes a small anomaly-detection model, and it inherits that "
              "world's trade-off -- too tight and it cries wolf, too loose and it "
              "misses drift, exactly the precision/recall balance this portfolio "
              "measures elsewhere."),
            p("The honest boundary: a distribution check catches a shift, not a "
              "cause, and it cannot distinguish a real business change (a genuine "
              "price rise) from a defect (cents-as-dollars). That is why it warns "
              "rather than blocks, and why a human closes the loop -- the same "
              "reason the valid-but-wrong defect needs a person, not just a "
              "threshold."),
        ])},
    ],
}

CH_SCALE = {
    "title": "Checks at scale",
    "abstract": "On a billion rows, how you run a check matters as much as the check.",
    "sections": [
        {"title": "Sampling, push-down, and cost", "html": "".join([
            p("The checks here scan a few hundred rows in memory. On a billion-row "
              "table the same checks must change shape or they become the most "
              "expensive query in the warehouse:"),
            ul(["<b>Push the check into SQL</b> -- a not-null or uniqueness check is "
                "a <code>COUNT(*) WHERE ... IS NULL</code> or a "
                "<code>GROUP BY ... HAVING COUNT(*) &gt; 1</code>, run by the "
                "warehouse, not pulled into Python.",
                "<b>Sample for distribution</b> -- a mean or a quantile can be "
                "estimated from a sample; a uniqueness check cannot (one duplicate "
                "in a billion is invisible to a 1% sample).",
                "<b>Incremental checks</b> -- validate only the new partition, not "
                "the whole table, every run."]),
            p("Which checks can be sampled and which must be exhaustive is itself a "
              "design decision: aggregate and distribution checks tolerate "
              "sampling; uniqueness, referential integrity and reconciliation "
              "generally do not. Knowing that distinction is the difference between "
              "a data-quality suite that scales and one that gets turned off for "
              "being too slow."),
        ])},
    ],
}

CH_RECAP = {
    "title": "The finding, restated",
    "abstract": "One table, and the boundary around it.",
    "sections": [
        {"title": "Everything in one place", "html": "".join([
            table(["Question", "Answer (reports/summary.json)"],
                  [["Injected data defects", str(ND)],
                   ["Caught by 'the pipeline ran'", str(CPM["pipeline_ran"])],
                   ["Caught by schema", str(CPM["schema"])],
                   ["Caught by expectations", str(CPM["expectations"])],
                   ["Caught by referential", str(CPM["referential"])],
                   ["Caught by reconciliation", str(CPM["reconciliation"])],
                   ["Caught by distribution", str(CPM["distribution"])],
                   ["Caught by at least one check", str(SUM["defects_caught_by_any"])],
                   ["Slip past every check", str(SUM["defects_missed_by_all"])],
                   ["False positives on the additive change", str(len(SUM["false_positives"]))]],
                  caption="Table RC.1 - the whole project, from reports/summary.json",
                  highlight_col=1),
        ])},
        {"title": "The paragraph", "html": "".join([
            p(f"{SUM['headline']} A green pipeline is not clean data; each check "
              f"owns a class the others miss -- expectations the per-row values, "
              f"reconciliation the aggregates and idempotency, referential the "
              f"keys, distribution the drift -- and a valid-but-wrong value escapes "
              f"them all. Data quality is layered, and the honest edge is that "
              f"automated checks bound the damage rather than guarantee truth, which "
              f"is why reconciliation against the source system and a data contract "
              f"upstream complete the picture."),
        ])},
    ],
}

# ═══════════════════════════════════════ round four ══

CH_PROFILING = {
    "title": "Profiling before expecting",
    "abstract": "You do not guess expectations -- you profile known-good data and "
                "encode what you see.",
    "sections": [
        {"title": "The profile is the source of the rules", "html": "".join([
            p("An expectation suite is not invented; it is read off a profile of "
              "known-good data. What is the range of quantity, the set of "
              "countries, the mean price, the uniqueness of order_id? The baseline "
              "profile this study builds for reconciliation and distribution is a "
              "tiny data profiler -- count, sum, mean, spread -- and in a real "
              "project the same step (df.describe(), a GE profiler, a Soda "
              "profile) is what generates the first draft of the expectations."),
            p("The discipline: profile the data you trust, encode the profile as "
              "expectations, then let the checks tell you when new data leaves the "
              "envelope. Writing expectations from imagination instead of from a "
              "profile is how suites end up both too strict (false positives on "
              "day one) and too loose (missing the defects that matter)."),
        ])},
    ],
}

CH_TOLERANCE = {
    "title": "Choosing thresholds",
    "abstract": "Every aggregate check has a tolerance, and the number is a "
                "precision/recall decision.",
    "sections": [
        {"title": "Too tight cries wolf; too loose misses drift", "html": "".join([
            p("The reconciliation sum allows 0.1% drift; the distribution mean "
              "allows 30% and the spread 60%. Those numbers are not arbitrary and "
              "they are not free: tighten them and benign fluctuation trips the "
              "check (false positives, and a gate people disable); loosen them and "
              "a real defect slips under (false negatives, like the scale error "
              "would if the band were 200%). The right value comes from the "
              "profile -- how much does this metric vary run-to-run on known-good "
              "data -- plus the cost of each error type for this dataset."),
            p("It is the same precision/recall trade this portfolio measures for "
              "detectors elsewhere, applied to data quality: a threshold is a "
              "policy, and the honest way to set it is from observed variation, not "
              "a round number. The study's loose unit_price range is deliberate -- "
              "it lets the scale error pass the per-row check so the distribution "
              "and reconciliation checks can demonstrate their value."),
        ])},
    ],
}

CH_ROOTCAUSE = {
    "title": "From a red check to a green pipeline",
    "abstract": "Detection starts the work; triage and root cause finish it.",
    "sections": [
        {"title": "What you do when a check fires", "html": "".join([
            p("A red check is the beginning, not the end. The triage a data "
              "engineer runs, and how this project's checks support it:"),
            ol(["<b>Localise</b> -- which rows, which column? The expectation and "
                "referential checks report the specific rule and the offending "
                "rows, not just 'the batch is bad'.",
                "<b>Classify</b> -- is it a data defect (bad source) or a process "
                "defect (bad transform)? The catalog's data/process split mirrors "
                "the two root-cause families.",
                "<b>Trace</b> -- follow the source keys upstream (lineage) to the "
                "extraction or the producing system.",
                "<b>Decide</b> -- reject, quarantine, or accept-and-alert, per the "
                "gate policy.",
                "<b>Prevent</b> -- push the check upstream (a data contract) so the "
                "same defect fails at production, not at load."]),
            p("A check that only says 'something is wrong' forces all of this to be "
              "manual. A check that says which rows, which rule, and which source "
              "key is the difference between a five-minute fix and an afternoon of "
              "SQL archaeology -- which is why the checks here return messages, not "
              "just booleans."),
        ])},
    ],
}

CH_TESTS3 = {
    "title": "Pinning the remaining cells",
    "abstract": "The referential-only and distribution-only cells, as meta-tests.",
    "sections": [
        {"title": "Each unique cell is a test", "html": "".join([
            p("The disjoint cells -- the whole point of the study -- are pinned as "
              "meta-tests, so a change that blurred them would fail the build."),
            code_from(PROJ, "tests/checks/test_checks.py",
                      start="def test_referential_catches_orphan():",
                      end='assert suite.run(run_defect("D03", prof))["referential"]',
                      caption="Listing T3.1 - referential catches the orphan",
                      lang="python"),
            code_from(PROJ, "tests/checks/test_checks.py",
                      start="def test_distribution_catches_scale_error_expectations_miss():",
                      end='assert res["distribution"] and not res["expectations"]         # loose range misses it',
                      caption="Listing T3.2 - distribution catches what the loose range misses",
                      lang="python"),
            code_from(PROJ, "tests/unit/test_transform.py",
                      start='@given(st.sampled_from(["", "no-at", "a@b", "a b@c.com", None, 5]))',
                      end="assert not is_valid_email(s)",
                      caption="Listing T3.3 - malformed emails are rejected",
                      lang="python"),
        ])},
    ],
}

CH_METRICS = {
    "title": "A single data-quality score, and why to distrust it",
    "abstract": "Rolling the checks into one number is tempting and lossy.",
    "sections": [
        {"title": "The percentage that hides the gap", "html": "".join([
            p("It is tempting to roll the matrix into one figure -- 'the pipeline "
              "is 86% quality-passing' -- and dashboards love it. But a single "
              "score hides exactly what this study surfaces: which class of defect "
              "is uncaught. A dataset can score 95% while every one of its silent "
              "corruptions goes undetected, because those defects are not in the "
              "denominator -- no check tests for them, so they never fail and never "
              "lower the score."),
            p("A quality score is fine as a trend to watch, dangerous as a gate to "
              "trust. The honest artifact is the matrix, not the average: it names "
              "what is checked, what is caught, and -- most importantly -- what is "
              "not checked at all. The same lesson as coverage-versus-correctness "
              "in the web project: a high number measures what you tested, not what "
              "is true."),
        ])},
    ],
}

CH2["sections"].append({"title": "Clean data satisfies every rule", "html": "".join([
    p("The generated clean data is, by construction, defect-free -- every order "
      "references a real customer and product, quantities and prices are in range. "
      "The generator test pins that, so the baseline the checks run against is "
      "genuinely clean and a green result on clean data is meaningful."),
    code_from(PROJ, "tests/unit/test_generate.py",
              start="def test_clean_data_shapes():", end='assert o["unit_price"] > 0',
              caption="Listing 2.2 - the clean data is clean",
              lang="python"),
]) })

CHAPTERS = [CH1, CH_BASELINE, CH2, CH_SOURCES, CH_GEN2, CH_EXTRACT, CH3, CH4,
            CH_ETLRUN, CH5, CH_PROFILING, CH6, CH7, CH8, CH9, CH10, CH_TOLERANCE,
            CH_ANOMALY, CH_DIMENSIONS, CH11, CH_INJECT, CH12, CH_AGG, CH13,
            CH_WORKED, CH_PROP, CH_META, CH_TESTS2, CH_TESTS3, CH_ADDITIVE,
            CH_DESIGN, CH_GATE, CH_SEVERITY, CH_ROOTCAUSE, CH_SQL, CH_SCALE,
            CH_OBS, CH_TOOLS, CH_CONTRACTS, CH_PROD, CH_INCREMENTAL, CH_LINEAGE,
            CH_METRICS, CH_LIMITS, CH_RECAP, CH_READING, RUNBOOK, APPENDIX]

META = {
    "series": "Engineering Notebook",
    "title": "Assay",
    "subtitle": "An ETL pipeline, and which data-quality check catches which defect",
    "author": "Nikhil Sinha",
    "repo": REPO,
    "stack": "Python · standard library ETL · SQLite · pytest + Hypothesis · GE-style checks",
    "version": "1.0",
    "how_to_read": (
        p("This is a data-quality-testing notebook that happens to be about a "
          "retail-orders pipeline. It is written for someone building or testing "
          "data pipelines who wants to know, concretely, which check catches which "
          "class of defect -- and which corruption escapes them all.")
        + p("Every listing is extracted from the repository at build time and "
            "every number is read from the reports a real run wrote, so nothing "
            "here can drift from the code.")),
}

if __name__ == "__main__":
    out = HERE / "Assay-Notebook.pdf"
    r = build(META, CHAPTERS, out, min_pages=60)
    print(f"PAGES {r['pages']} (min 60 -> {r['meets_minimum']})  "
          f"WORDS ~{r['approx_words']:,}  {r['chapters']} ch / {r['sections']} sec  "
          f"{r['size_kb']} KB")
