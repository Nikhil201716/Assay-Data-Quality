#!/usr/bin/env bash
# What Codespaces runs on attach: a stranger opening this repo sees the real
# measurement -- which data-quality check catches which defect -- not a README
# claiming it. Python only; the pipeline and checks use just the standard library.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=============================================================="
echo " Assay - an ETL pipeline, and which data-quality check catches what"
echo "=============================================================="

echo
echo "[1/2] tests: property-based transforms + check meta-tests"
pip install -q -r requirements.txt
python -m pytest tests

echo
echo "[2/2] fault injection: score every check against the defect catalog"
python scoring/score.py

echo
echo "=============================================================="
echo " 'The pipeline ran' catches nothing. Expectations are the"
echo " workhorse; reconciliation alone catches silent row-drops and"
echo " non-idempotent loads; referential catches orphans; distribution"
echo " catches scale drift a loose range misses - and a valid-but-wrong"
echo " value slips past every check. Numbers in reports/*.json."
echo "=============================================================="
