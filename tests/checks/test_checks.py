"""Meta-tests: the checks themselves must pass on clean data and each must catch
the defect class it owns. A check that always fires (or never does) would make
the whole study meaningless, so these pin the checks before they are trusted."""

from checks import suite
from checks.context import build_profile
from pipeline.generate import generate
from pipeline.run_etl import run
from scoring.score import run_defect


def _profile():
    clean, _ = run(generate())
    return build_profile(clean)


def test_clean_data_passes_every_check():
    prof = _profile()
    assert suite.run(run_defect(None, prof)) == {
        "pipeline_ran": False, "schema": False, "expectations": False,
        "referential": False, "reconciliation": False, "distribution": False,
    }


def test_expectations_catch_range_and_regex():
    prof = _profile()
    assert suite.run(run_defect("D04", prof))["expectations"]      # out-of-range qty
    assert suite.run(run_defect("D07", prof))["expectations"]      # bad email
    assert suite.run(run_defect("D08", prof))["expectations"]      # unknown country


def test_referential_catches_orphan():
    prof = _profile()
    assert suite.run(run_defect("D03", prof))["referential"]


def test_reconciliation_uniquely_catches_silent_drop():
    prof = _profile()
    res = suite.run(run_defect("D10", prof))
    assert res["reconciliation"] and not res["expectations"]       # per-row checks are blind


def test_reconciliation_catches_non_idempotent_load():
    prof = _profile()
    assert suite.run(run_defect("D12", prof))["reconciliation"]


def test_distribution_catches_scale_error_expectations_miss():
    prof = _profile()
    res = suite.run(run_defect("D11", prof))
    assert res["distribution"] and not res["expectations"]         # loose range misses it


def test_valid_but_wrong_value_slips_past_every_check():
    prof = _profile()
    assert not any(suite.run(run_defect("D13", prof)).values())    # the honest gap


def test_additive_change_is_no_false_positive():
    prof = _profile()
    assert not any(suite.run(run_defect("D15", prof)).values())
