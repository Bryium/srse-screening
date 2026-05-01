"""SMT-driven replacements for the PBTs in `original_tests/`.

For each original PBT we pull inputs from the matching Z3 generator
under `smt_generators/` and call the *same property assertion* the
Hypothesis version uses. Because the inputs are produced by an SMT
solver, every input satisfies the original constraints by construction
and no rejection is required.
"""

from __future__ import annotations

import pytest

from original_tests.test_mix_attrs import _is_mixed
from original_tests.test_sorted_unique import HI, LO, MAX_LEN, MIN_LEN
from smt_generators.gen_division import divisible_pairs
from smt_generators.gen_mix_attrs import mix_assignments
from smt_generators.gen_sorted_unique import unique_sorted_lists


@pytest.mark.parametrize("x,y", list(divisible_pairs(n=20)))
def test_division_property_smt(x, y):
    assert y != 0
    assert x % y == 0
    assert (x // y) * y == x


@pytest.mark.parametrize(
    "xs", list(unique_sorted_lists(n=24, lo=LO, hi=HI, min_len=MIN_LEN, max_len=MAX_LEN))
)
def test_sort_preserves_set_and_order_smt(xs):
    assert MIN_LEN <= len(xs) <= MAX_LEN
    assert all(LO <= v <= HI for v in xs)
    assert len(set(xs)) == len(xs)
    s = sorted(xs)
    assert all(s[i] <= s[i + 1] for i in range(len(s) - 1))
    assert sorted(s) == sorted(xs)


@pytest.mark.parametrize("cmp,eq,order", list(mix_assignments(n=24)))
def test_mix_smt(cmp, eq, order):
    assert eq is not None or order is not None
    mixed = _is_mixed(cmp, eq, order)
    if cmp is None:
        assert not mixed
    else:
        assert mixed
