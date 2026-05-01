"""SMT-based generator for the integer-division PBT.

Original constraints (see `original_tests/test_division.py`):

    @given(st.integers(), st.integers())
    def test_division_property(x, y):
        assume(y != 0)
        assume(x % y == 0)
        assert (x // y) * y == x

Translation:

    Variables:
        x : Int    -- mathematical integer
        y : Int    -- mathematical integer

    Hard constraints (must hold by construction):
        y != 0
        x % y == 0

    Search-bounded constraints (added so Z3 returns "interesting" inputs
    rather than always picking 0):
        -BOUND <= x <= BOUND
        -BOUND <= y <= BOUND

The generator yields up to `n` distinct (x, y) pairs that all satisfy
the hard constraints. Distinctness across calls is enforced with
blocking clauses (`Or(x != mx, y != my)`).
"""

from __future__ import annotations

from typing import Iterator

from z3 import Int, Or, Solver, sat


DEFAULT_BOUND = 50


def divisible_pairs(n: int = 20, bound: int = DEFAULT_BOUND) -> Iterator[tuple[int, int]]:
    """Yield up to `n` distinct (x, y) with y != 0 and x % y == 0."""
    x, y = Int("x"), Int("y")
    s = Solver()
    s.add(y != 0)
    s.add(x % y == 0)
    s.add(x >= -bound, x <= bound)
    s.add(y >= -bound, y <= bound)

    for _ in range(n):
        if s.check() != sat:
            return
        m = s.model()
        mx, my = m[x].as_long(), m[y].as_long()
        yield mx, my
        s.add(Or(x != mx, y != my))


if __name__ == "__main__":
    for i, (x, y) in enumerate(divisible_pairs(n=10)):
        assert y != 0 and x % y == 0
        print(f"  {i:>2}: x = {x:>4}, y = {y:>4}")
