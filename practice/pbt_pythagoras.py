from hypothesis import given, assume, settings
import hypothesis.strategies as st

@settings(max_examples=200)
@given(
    st.integers(min_value=1, max_value=100),
    st.integers(min_value=1, max_value=100),
    st.integers(min_value=1, max_value=100),
)
def test_pythagoras(a, b, c):
    assume(a * a + b * b == c * c)
    print(f"  found triple: ({a}, {b}, {c})")
    assert c > a and c > b