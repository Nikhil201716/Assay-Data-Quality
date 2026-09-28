"""Property-based tests (Hypothesis) for the pure transform helpers. These check
the functions over a wide input space, not a handful of examples -- which is the
right tool for the kind of value-format bug the pipeline must handle."""

from hypothesis import given
from hypothesis import strategies as st

from pipeline.transform import compute_line_total, is_iso_date, is_valid_email


@given(st.integers(min_value=0, max_value=100000),
       st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_line_total_is_product_rounded(q, p):
    assert compute_line_total(q, p) == round(q * p, 2)


@given(st.integers(min_value=0, max_value=1000),
       st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False))
def test_line_total_bug_path_adds(q, p):
    assert compute_line_total(q, p, bug=True) == round(q + p, 2)


def test_line_total_handles_none():
    assert compute_line_total(None, 5.0) is None
    assert compute_line_total(3, None) is None


@given(st.integers(1900, 2100), st.integers(1, 12), st.integers(1, 28))
def test_valid_iso_dates_accepted(y, m, d):
    assert is_iso_date(f"{y:04d}-{m:02d}-{d:02d}")


@given(st.integers(13, 99))
def test_impossible_month_rejected(m):
    assert not is_iso_date(f"2020-{m:02d}-01")


@given(st.sampled_from(["", "not-a-date", "2020/01/01", "31/12/2020", "2020-1-1", None, 42]))
def test_non_iso_rejected(s):
    assert not is_iso_date(s)


@given(st.sampled_from(["a@b.com", "x.y@sub.domain.co", "user+tag@ex.com"]))
def test_valid_emails_accepted(s):
    assert is_valid_email(s)


@given(st.sampled_from(["", "no-at", "a@b", "a b@c.com", None, 5]))
def test_invalid_emails_rejected(s):
    assert not is_valid_email(s)
