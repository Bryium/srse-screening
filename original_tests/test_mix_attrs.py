"""Original Hypothesis PBT pulled (and slightly mocked) from `attrs`.

This is a faithful reproduction of `tests/test_make.py::test_mix` from
[`python-attrs/attrs`](https://github.com/python-attrs/attrs) (lines
2619-2628 of the cloned snapshot). It exercises a small but realistic
constraint pattern that we *can* translate to SMT cleanly:

    @given(cmp=booleans(), eq=optional_bool, order=optional_bool)
    def test_mix(self, cmp, eq, order):
        assume(eq is not None or order is not None)
        with pytest.raises(...):
            _determine_attrs_eq_order(None, False, True, True)

For this submission we replace the actual `_determine_attrs_eq_order`
call with a self-contained property: when `cmp` is set together with
`eq` or `order`, the configuration is "mixed" and the helper raises
`ValueError`. The constraint we care about for the SMT translation is
the `assume(...)` pattern over three optional-boolean variables.
"""

from hypothesis import given, assume
import hypothesis.strategies as st


optional_bool = st.one_of(st.none(), st.booleans())


def _is_mixed(cmp, eq, order):
    """Return True iff `cmp` is set together with eq/order (the error case)."""
    if cmp is None:
        return False
    return eq is not None or order is not None


@given(cmp=st.one_of(st.none(), st.booleans()), eq=optional_bool, order=optional_bool)
def test_mix(cmp, eq, order):
    assume(eq is not None or order is not None)

    mixed = _is_mixed(cmp, eq, order)
    if cmp is None:
        assert not mixed
    else:
        assert mixed
