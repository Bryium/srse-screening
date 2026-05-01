"""SMT-based generator for the `attrs.test_mix` PBT.

Original constraints (see `original_tests/test_mix_attrs.py`):

    @given(cmp=optional_bool, eq=optional_bool, order=optional_bool)
    def test_mix(cmp, eq, order):
        assume(eq is not None or order is not None)
        ...

Translation:

Each variable has the value space {None, True, False}. We encode it
as two Z3 booleans per variable:

    is_set    -- True iff the variable is not None
    val       -- the boolean value, only meaningful when is_set

Then the assume(...) becomes a hard constraint:

    eq.is_set OR order.is_set

The full state space has 3^3 = 27 assignments. With the assume in
place, exactly 3 * (3^2 - 1) = 24 of those survive. We enumerate them
all using blocking clauses so the generator behaves deterministically
and exhausts the constrained domain. (Hypothesis would discard the
3 invalid assignments by retrying; we never visit them at all.)
"""

from __future__ import annotations

from typing import Iterator, Optional

from z3 import And, Bool, Implies, Not, Or, Solver, sat


OptBool = Optional[bool]


def _model_to_optbool(m, is_set, val) -> OptBool:
    if not bool(m[is_set]):
        return None
    return bool(m[val])


def mix_assignments(n: int = 24) -> Iterator[tuple[OptBool, OptBool, OptBool]]:
    """Yield up to `n` distinct (cmp, eq, order) tuples where eq or order is not None."""
    cmp_set, cmp_val = Bool("cmp_set"), Bool("cmp_val")
    eq_set, eq_val = Bool("eq_set"), Bool("eq_val")
    order_set, order_val = Bool("order_set"), Bool("order_val")

    s = Solver()
    s.add(Or(eq_set, order_set))
    s.add(Implies(Not(cmp_set), Not(cmp_val)))
    s.add(Implies(Not(eq_set), Not(eq_val)))
    s.add(Implies(Not(order_set), Not(order_val)))

    for _ in range(n):
        if s.check() != sat:
            return
        m = s.model()
        cmp_ = _model_to_optbool(m, cmp_set, cmp_val)
        eq_ = _model_to_optbool(m, eq_set, eq_val)
        order_ = _model_to_optbool(m, order_set, order_val)
        yield cmp_, eq_, order_

        s.add(
            Or(
                cmp_set != bool(m[cmp_set]),
                cmp_val != bool(m[cmp_val]),
                eq_set != bool(m[eq_set]),
                eq_val != bool(m[eq_val]),
                order_set != bool(m[order_set]),
                order_val != bool(m[order_val]),
            )
        )


if __name__ == "__main__":
    seen = set()
    for i, t in enumerate(mix_assignments()):
        assert t[1] is not None or t[2] is not None
        seen.add(t)
        print(f"  {i:>2}: cmp={t[0]!s:>5}  eq={t[1]!s:>5}  order={t[2]!s:>5}")
    print(f"\n  total distinct assignments enumerated: {len(seen)}")
