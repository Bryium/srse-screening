"""Original Hypothesis-style PBT for integer division.

Property: for any two integers x, y where y != 0 and y divides x,
the floor-division identity (x // y) * y == x must hold.

This test is taken essentially verbatim from the screening task
description and is the canonical example of a *tightly constrained*
PBT: random sampling almost never produces pairs that satisfy
`y != 0 AND x % y == 0`, so Hypothesis spends most of its quota on
rejected inputs and frequently aborts with FailedHealthCheck.

Running this test is meant to fail (with a health-check error) on
purpose. The matching SMT-based version in `tests_with_smt/` produces
only valid pairs by construction.
"""

import pytest
from hypothesis import given, assume
from hypothesis.errors import FailedHealthCheck
import hypothesis.strategies as st


@pytest.mark.xfail(
    strict=True,
    raises=FailedHealthCheck,
    reason=(
        "Hypothesis filters out almost every random (x, y) pair because "
        "the constraints `y != 0 AND x % y == 0` are tight in the unbounded "
        "integer domain. This `xfail` is intentional: it is the empirical "
        "evidence cited in `comparison.md`. The matching SMT version in "
        "`tests_with_smt/test_smt_runner.py` produces only valid pairs."
    ),
)
@given(st.integers(), st.integers())
def test_division_property(x, y):
    assume(y != 0)
    assume(x % y == 0)
    assert (x // y) * y == x
