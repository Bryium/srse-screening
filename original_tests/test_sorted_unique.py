"""Original Hypothesis-style PBT for a sorted-unique list invariant.

Property: when we sort a list of distinct integers from a bounded
range, the result is monotone non-decreasing AND a permutation of the
input.

The constraints exercised here are:

* `min_size` and `max_size` on `st.lists(...)` — bounds on length.
* `min_value` and `max_value` on `st.integers(...)` — bounds on each element.
* `unique=True` on `st.lists(...)` — pairwise distinctness.

Hypothesis can satisfy these constraints on its own, but uniqueness in a
narrow integer window starts to behave like a tight `assume()` once the
list size approaches the window's cardinality. This test is therefore
representative of "moderately constrained" PBTs — distinct from the
fully-tight `test_division_property`.
"""

from hypothesis import given
import hypothesis.strategies as st


LO = 1
HI = 20
MIN_LEN = 3
MAX_LEN = 8


@given(
    st.lists(
        st.integers(min_value=LO, max_value=HI),
        min_size=MIN_LEN,
        max_size=MAX_LEN,
        unique=True,
    )
)
def test_sort_preserves_set_and_order(xs):
    s = sorted(xs)
    assert all(s[i] <= s[i + 1] for i in range(len(s) - 1))
    assert sorted(s) == sorted(xs)
    assert len(set(s)) == len(s)
    assert all(LO <= v <= HI for v in s)
