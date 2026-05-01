# PBT vs. SMT — Comparison Report

Submission for the SRSE 2026 screening task, Part 4. This document
discusses (i) the feasibility of replacing Hypothesis's random
generation with Z3-based input construction, (ii) the qualitative
differences between the two strategies, and (iii) the limitations and
mismatches we encountered while doing the translation.

The empirical numbers below come from running this repository's two
test suites on a Windows 11 laptop with Python 3.14.2,
`hypothesis 6.152.4`, `z3-solver 4.13.x`, and `pytest 9.0.3`.

---

## 1. Feasibility of SMT-based generation

For all three PBTs in `original_tests/`, we successfully wrote a Z3
generator in `smt_generators/` that produces inputs satisfying the
original constraints by construction. The matching pytest harness in
`tests_with_smt/test_smt_runner.py` runs every property assertion that
appears in the original test on every Z3-generated input, with **zero**
rejected examples.

| PBT | Hypothesis result | Z3 result |
| --- | --- | --- |
| `test_division_property` | `FailedHealthCheck` (50 inputs filtered, 2 generated) | 20 / 20 inputs accepted, all properties hold |
| `test_sort_preserves_set_and_order` | 100 generated, 30 invalid (≈23% rejection) | 24 / 24 inputs accepted, all properties hold |
| `test_mix` | 24 generated, 3 invalid (≈11% rejection) | 24 / 24 inputs accepted, all properties hold (the entire constrained state space) |

Three quick observations:

* **Tight `assume()`s break PBT.** `test_division_property` is a
  textbook case: the constraint `y != 0 AND x % y == 0` is so narrow
  on the unbounded integer domain that Hypothesis triggers
  `FailedHealthCheck` and refuses to run the property at all. SMT
  produces 20 valid pairs in milliseconds.
* **Even when PBT works, it wastes effort.** `test_sort_*` and
  `test_mix` *do* pass under Hypothesis, but with measurable
  rejection: 23% and 11% respectively. The SMT versions waste
  nothing — every model returned satisfies every constraint.
* **SMT can be exhaustive on small finite domains.** The `test_mix`
  state space has 27 raw assignments and the `assume()` rules out 3
  of them. Z3 enumerates exactly the remaining 24 with no duplicates,
  giving a guarantee Hypothesis cannot offer in practice.

We conclude that **SMT-backed input generation is feasible for the
constraint patterns we examined** — namely, linear integer
constraints, range bounds, distinctness, and propositional formulas
over finite-domain enumerations. These are the patterns that drive
most `min_value/max_value/min_size/max_size/assume(...)` usage we
counted in `attrs/tests/` (see `analysis/results.md`).

## 2. Differences between PBT and SMT-based strategies

The two approaches solve the same problem from opposite directions.

### Generation paradigm

| | Hypothesis | Z3 |
| --- | --- | --- |
| Style | Random + reject | Solve + construct |
| Worst-case behaviour | Quotas exhausted, `FailedHealthCheck` | `unsat` (proof of impossibility) |
| Typical bias | Smaller / structurally simpler values first ("shrinking") | Lexicographically "first" model under the solver's internal heuristic |
| Diversity | Statistical, driven by `random_module` | Manual: requires explicit blocking clauses |
| Coverage guarantee | None (probabilistic) | Exact, on finite domains |

### Failure-finding behaviour

Hypothesis is designed for *bug discovery*: it deliberately produces
adversarial inputs (e.g. `0`, `-1`, `2**31`, empty containers) and
shrinks counter-examples for readability. Z3 has no equivalent
notion. To replicate Hypothesis's "look for trouble" attitude under
SMT we would have to (a) bias the search by adding constraints like
"`x` near a power of two" and (b) drive the solver from a list of
edge-case templates. The Z3 generators in this repo make **no such
attempt** and so the inputs they produce are diverse but bland —
mostly small magnitudes near the search bounds.

### Code shape

The translations cost roughly the same number of lines as the
originals, but the lines look different. A `@given(st.lists(...,
unique=True))` becomes a *family* of solver instances, one per
admissible length. An `assume(eq is not None or order is not None)`
becomes an explicit `Or(eq_set, order_set)` after we encode each
optional-bool as `(is_set, val)`.

### Performance

For the constrained workloads in this repo, Z3 is **dramatically
faster** end-to-end. The full `tests_with_smt/` suite — 68 cases
across the three properties — runs in 0.5 s. The Hypothesis suite,
which sees only the same property assertions on the *passing* slice
of its inputs, takes about 0.3 s for `test_mix` + `test_sort` alone
and *cannot run at all* for `test_division`. Crucially, Hypothesis's
runtime is dominated by the rejected attempts; Z3 has none.

We do not draw the conclusion that Z3 is always faster. Z3 will lose
when the constraint is loose (random sampling has nothing to
discard), when the variable domain is large and unconstrained
(Z3's blocking-clause loop is linear in the number of distinct
solutions wanted), or when the strategy is structural (see §3).

## 3. Limitations and mismatches encountered

### 3.1 Composite Hypothesis strategies

The two `test_change` PBTs in `attrs/tests/test_funcs.py` and the three
list-bounded PBTs in `attrs/tests/test_make.py` all consume custom
strategies built with `@st.composite` (`simple_classes()`,
`simple_attrs_with_metadata()`, etc.). Those strategies construct
*Python class objects* whose shape is itself randomised.

This is the principal limitation we hit: SMT theories quantify over
mathematical objects (integers, reals, strings, arrays), not over
Python class definitions. Encoding "an `attrs` class with N fields,
each of a randomly chosen type, each with a randomly chosen default
and validator" as a single SMT formula is not just hard — it is
outside the scope of any standard first-order theory. We therefore
chose **not** to translate these tests, and replaced them with a
synthetic but representative test (`test_sorted_unique`) that
captures the same `min_size/max_size + uniqueness` flavour.

### 3.2 The `min_size`/`max_size` mismatch

Hypothesis treats list size as a *strategy parameter*; Z3 treats list
size as a *separate first-order signature*. Our generator works
around this by materialising one solver per admissible length and
round-robin'ing through them. This is fine when `max_size` is small
(8 in our test) but does not scale to the hundreds. For larger
sizes one would switch to Z3's `ArrayRef` plus a bounded length
variable, which is doable but markedly more complex.

### 3.3 Unbounded integer domains

`@given(st.integers())` corresponds to `Z = ...` — Z3 will happily
work with unbounded integers, but in practice the model it returns
is biased toward 0, which is the same input over and over once
blocking clauses kick in. Our `gen_division.py` adds an explicit
`-bound <= x <= bound` to keep the search productive. This is a
diversity workaround, not a correctness compromise.

### 3.4 Distribution and bias

Hypothesis biases samples toward "interesting" values. Z3's models
follow whatever heuristic the solver was tuned for, which for `Int`
sorts is "small absolute value, lex order". Our blocking-clause
loop therefore yields a fairly monotonic sequence of inputs. This is
a real qualitative difference: the SMT-driven test sees a less
adversarial input distribution than the Hypothesis-driven one. To
recover variety we would have to layer a randomised search on top of
the solver (e.g. by sampling random hyperplanes that cut off whole
regions of the model space).

### 3.5 Strategies we did not translate

The following Hypothesis strategies have no clean Z3 counterpart and
were deliberately skipped:

* `st.text()`, `st.binary()` — Z3 has a string theory, but generating
  *realistic* strings is awkward and slow.
* `st.floats()` — encodable in the IEEE-754 FP theory but performance
  drops sharply.
* `st.recursive()`, custom `@st.composite` — recursive or
  data-shape-randomised generators do not fit a fixed-arity formula.
* `.filter(lambda x: ...)` with arbitrary Python predicates — the
  predicate has to be re-implemented as an SMT formula by hand,
  which is the very work this project is investigating; we counted
  zero `.filter(...)` uses in `attrs/tests/` so this did not bite us.

## 4. Take-away

For the slice of PBTs that use linear arithmetic, range bounds,
distinctness, and finite-domain propositional constraints —
which is the slice that hurts most under random sampling — Z3 is a
clean drop-in replacement that produces only valid inputs and, on
small finite domains, can be exhaustive. For PBTs that consume
custom data-shape-randomising strategies, an SMT translation is
either prohibitively complex or outright impossible without
abandoning first-order logic; for those, Hypothesis remains the
right tool.

A practical hybrid would: (i) keep Hypothesis as the front end,
(ii) detect strategies that are pure linear-arithmetic /
range-bounded / `assume(...)`-driven, and (iii) hand those to a Z3
back-end while letting the rest stay on Hypothesis's random sampler.
That is, in our reading, the natural research direction this
screening task points at.
