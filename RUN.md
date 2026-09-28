# Running Assay

**Python 3.12+**, and nothing else — the pipeline and checks use only the standard
library; the three dependencies are for the tests and the measurement. No pandas,
no cloud, no paid service.

## One-click (devcontainer / Codespaces)

```bash
bash .devcontainer/run-project.sh
```

Installs the test deps, runs the suite, and runs the fault-injection scoring that
writes `reports/*.json`.

## Manual

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m pytest tests          # 18 tests: property-based transforms + check meta-tests
python scoring/score.py         # inject 15 defects, score 6 checks -> reports/*.json
```

`scoring/score.py` builds the (possibly defect-injected) source tables, runs the
ETL twice into one warehouse (so idempotency can be judged), and runs every check.
`catch_matrix.json` and `summary.json` are byte-reproducible — the data is seeded
and the whole run is in-process.

## Explore the pipeline

```python
from pipeline.generate import generate
from pipeline.run_etl import run
loaded, conn = run(generate())      # extract -> transform -> load
print(loaded[0])                    # an enriched warehouse row
```

## What you should see

- `18 passed`.
- `scoring/score.py` prints a per-defect matrix and a headline, and writes
  `reports/catch_matrix.json` + `summary.json` (identical on re-run).
