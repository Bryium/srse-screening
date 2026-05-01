# Partial-completion notes

The screening task asks (Part 5) for a record of where SMT translation
became hard, which constraint kinds resisted encoding, what
simplifying assumptions we made, and any scalability or performance
issues. All five of the original task's parts were completed for the
PBTs we ultimately selected; this document records the *deliberate
omissions* and the friction we hit during translation.

## What we explicitly did not translate

### `attrs.tests.test_funcs.test_change` (×2 occurrences)

These tests draw inputs from `simple_classes()`, a `@st.composite`
Hypothesis strategy that *constructs an `attrs` class*: it picks the
number of fields, the type of each field, optional defaults,
validators, frozen/slots flags, and so on, all at random.

A direct SMT encoding would have to model "a Python class with N
attributes" inside a first-order theory, which is not something any
standard SMT theory provides. We could approximate the shape by
hand-rolling a sum-of-products encoding for each attribute, but that
loses the polymorphism Hypothesis is exploiting (any value of any
type per attribute) and is, in our judgement, more complex than the
original property warrants. We therefore replaced this category with
the synthetic `test_sorted_unique`, which exercises the same family
of constraints (`min_size`, `max_size`, distinctness over a bounded
domain) without dragging in random class construction.

### `attrs.tests.test_make.test_empty_metadata_singleton` and friends

These three tests use `lists(simple_attrs_without_metadata, min_size=2,
max_size=5)`. The list-size constraint is encodable, but the element
strategy (`simple_attrs_without_metadata`) is again composite. The
useful constraint to translate would be the bound on the *list
length*, which is exactly what `gen_sorted_unique.py` demonstrates.
Translating these tests in full would require encoding `attrs.Attribute`
construction inside Z3.

## Constraint kinds that were hard to encode

| Constraint | What it is | Why it was hard |
| --- | --- | --- |
| Composite strategies (`@st.composite`) | Python function that draws sub-values and assembles them into a Python object | Z3 has no notion of "construct a Python object". One would have to enumerate the discrete-shape space outside the solver and feed each shape's leaves through Z3 separately. |
| Recursive strategies (`st.recursive`, `st.deferred`) | Self-referential generators (trees, JSON, ASTs) | Recursive sorts are possible in SMT (algebraic datatypes) but unsupported by `z3-solver`'s typical Python frontend in a way that is friendly for input enumeration. |
| `st.text()` with regex shape | Strings matching a regex | Z3 has the regex theory but performance is poor for non-trivial regexes; we did not need this, but it would have been a problem in `attrs` if we had picked tests that involve attribute names. |
| Floating-point strategies | `st.floats(allow_nan=False, ...)` | The FP theory is correct but slow and verbose. None of our chosen tests required floats. |
| Arbitrary Python `.filter(lambda)` | A user-defined predicate | The predicate must be re-implemented as an SMT formula. Detecting this from source is undecidable; we counted zero `.filter` uses in `attrs/tests/` so it did not block us. |

## Simplifying assumptions we made

1. **Bounded integer search.** `gen_division.py` adds
   `-50 <= x, y <= 50` even though the original test uses
   `st.integers()` (unbounded). Without this, Z3 would return small
   models repeatedly and the blocking-clause loop would degenerate
   into the same handful of pairs. The constraint is a
   diversity/scaling workaround; the property under test still holds
   without bounds because the constraints `y != 0 AND x % y == 0` are
   themselves unbounded.
2. **`min_size`/`max_size` family-of-solvers encoding.** Rather than
   modelling list length with a single integer variable inside one
   solver, we instantiate a *separate* solver per admissible length
   and round-robin between them. This is conceptually equivalent to
   Hypothesis's behaviour but does not extend to truly large size
   ranges (say, `min_size=0, max_size=10000`) without further work.
3. **Optional-boolean encoding via two booleans.** `OptBool` (None /
   True / False) is encoded as `(is_set, val)` with the constraint
   `not is_set => not val` to canonicalise the unused `val`. This
   adds 3 boolean constraints per variable and does not generalise
   to arbitrary algebraic datatypes — a more uniform approach would
   be to use Z3's `Datatype` builder, at the cost of more setup code.
4. **Exhaustive enumeration for small finite domains.**
   `gen_mix_attrs.py` enumerates all 24 satisfying assignments. This
   is sound only because the domain is tiny. Scaling to larger
   discrete spaces (say, 4 optional booleans = 81 raw assignments)
   would require either truncation or sampling.

## Performance / scalability observations

* The full `tests_with_smt/` suite runs in **0.54 s** on our machine,
  well under the typical Hypothesis budget. Z3 setup per test is
  cheap because the formulas are small.
* `gen_sorted_unique.py` rebuilds a solver per length on import. With
  `max_size = 8` this is invisible; with `max_size = 100` this
  approach would dominate runtime and we would push the length
  parameter into a single solver.
* The blocking-clause enumeration is **O(n)** in the number of
  distinct models requested: each new model adds one clause to the
  solver, and Z3's incremental solver re-checks satisfiability in
  near-constant time for our small problems. Past a few thousand
  models we would expect this to slow down noticeably; an MCMC-style
  sampler with random hyperplane cuts would be the next step.
* We did not observe any solver timeouts. Z3's default heuristics
  handle the linear arithmetic and propositional cases here with no
  tuning required.

## Things we deliberately scoped out

* No empirical comparison of *bug-finding ability*. SMT-driven inputs
  are valid by construction but, as discussed in `comparison.md` §2,
  they are not adversarial in the way Hypothesis's shrinking sampler
  is. Quantifying that gap would require seeding bugs into a target
  function and measuring detection rate.
* No automatic translation. The mapping from a Hypothesis test to a
  Z3 generator is performed by hand. Building an automated
  source-to-source translator (which is, we suspect, the larger
  research project this screening task is gauging interest in) was
  out of scope.
