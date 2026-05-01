"""SMT-based generator for the sorted-unique-list PBT.

Original constraints (see `original_tests/test_sorted_unique.py`):

    @given(
        st.lists(
            st.integers(min_value=LO, max_value=HI),
            min_size=MIN_LEN,
            max_size=MAX_LEN,
            unique=True,
        )
    )
    def test_sort_preserves_set_and_order(xs): ...

Translation:

For each list length L in [MIN_LEN, MAX_LEN] we materialise an SMT
instance with L integer variables x_0, ..., x_{L-1}, and add:

    LO <= x_i <= HI               (range bound)
    Distinct(x_0, ..., x_{L-1})   (uniqueness)

This is a *family* of SMT problems (one per length), which is the
natural way to encode `min_size`/`max_size` in a fixed-arity solver.
We round-robin through the lengths so we exercise all of them.

Distinctness across calls is enforced with a blocking clause on the
multiset of values (`Or(x_i != m_i for i in range(L))`).
"""

from __future__ import annotations

from typing import Iterator

from z3 import Distinct, Int, Or, Solver, sat


def unique_sorted_lists(
    n: int = 20,
    lo: int = 1,
    hi: int = 20,
    min_len: int = 3,
    max_len: int = 8,
) -> Iterator[list[int]]:
    """Yield up to `n` distinct lists of distinct ints in [lo, hi]."""
    if max_len < min_len:
        return
    if hi - lo + 1 < max_len:
        raise ValueError(
            f"the window [{lo}, {hi}] has only {hi - lo + 1} values, "
            f"cannot fit a list of length {max_len}"
        )

    solvers: dict[int, tuple[Solver, list]] = {}
    for length in range(min_len, max_len + 1):
        xs = [Int(f"x_{length}_{i}") for i in range(length)]
        s = Solver()
        for v in xs:
            s.add(v >= lo, v <= hi)
        s.add(Distinct(*xs))
        solvers[length] = (s, xs)

    yielded = 0
    while yielded < n:
        progressed_in_round = False
        for length in range(min_len, max_len + 1):
            if yielded >= n:
                return
            s, xs = solvers[length]
            if s.check() != sat:
                continue
            m = s.model()
            values = [m[v].as_long() for v in xs]
            yield sorted(values)
            yielded += 1
            progressed_in_round = True
            s.add(Or(*[xs[i] != values[i] for i in range(length)]))
        if not progressed_in_round:
            return


if __name__ == "__main__":
    for i, xs in enumerate(unique_sorted_lists(n=8)):
        assert len(set(xs)) == len(xs)
        assert xs == sorted(xs)
        print(f"  {i:>2}: {xs}")
