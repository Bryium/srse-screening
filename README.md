# SRSE  Screening — Property-Based Testing meets SMT

This repository  investigates whether SMT solving
(via Z3) can replace the random input generation used by Hypothesis when a
test's constraints are tight enough to make random sampling impractical.

The work is structured as four artifacts:

1. **Empirical analysis** of the Hypothesis usage in a real Python project
   (`attrs`).
2. **Three original PBTs** that exercise different kinds of constraints
   (`assume`, bounded strategies, optional-boolean state space).
3. **Three Z3-based generators** that produce satisfying inputs directly,
   without rejection sampling.
4. A **comparison document** discussing feasibility, differences, and
   limitations of the SMT approach.

A small **warm-up** (`practice/`) reproduces the same PBT-vs-SMT contrast on
the classic Pythagorean-triples problem and is included as motivation.

---

## Quick start

```bash
python -m venv venv
# Windows: venv\Scripts\Activate.ps1
# Unix:    source venv/bin/activate
pip install -r requirements.txt
```

### 1. Run the empirical analysis

```bash
python analysis/count_pbts.py target_project/tests
```

This prints a per-file table and writes the summary numbers used in
`analysis/results.md`. (To regenerate the input data, clone
`https://github.com/python-attrs/attrs` into `./target_project`.)

### 2. Run the original Hypothesis PBTs

```bash
pytest -s --hypothesis-show-statistics original_tests/
```

Two of these tests are written in a way that *demonstrates the problem* the
research aims to solve: they exhaust Hypothesis's filter quota and trigger
`FailedHealthCheck`. That is intentional and is part of the comparison.

### 3. Run the Z3-driven property checks

```bash
pytest -s tests_with_smt/
```

Each test parametrises the property over inputs produced by the Z3 generator
in `smt_generators/`. Every generated input satisfies the original
constraints by construction, so no input is ever rejected.

### 4. Read the analysis & comparison

* `analysis/results.md` — empirical numbers and methodology.
* `comparison.md` — feasibility, PBT-vs-SMT differences, and limitations.
* `partial_completion.md` — notes on cases that were hard or skipped.

---

## Repository layout

```
.
├── README.md
├── requirements.txt
├── .gitignore
│
├── analysis/
│   ├── count_pbts.py         # AST scanner for PBT detection
│   └── results.md            # numbers + methodology write-up
│
├── original_tests/           # mocked PBTs (Hypothesis form)
│   ├── test_division.py
│   ├── test_sorted_unique.py
│   └── test_mix_attrs.py
│
├── smt_generators/           # Z3-based replacements
│   ├── __init__.py
│   ├── gen_division.py
│   ├── gen_sorted_unique.py
│   └── gen_mix_attrs.py
│
├── tests_with_smt/           # pytest harness for the Z3 generators
│   └── test_smt_runner.py
│
├── practice/                 # warm-up: Pythagorean triples
│   ├── pbt_pythagoras.py
│   └── smt_pythagoras.py
│
├── comparison.md             # the report (Part 4)
└── partial_completion.md     # notes on hard cases (Part 5)
```

---

## Target project

We chose [`python-attrs/attrs`](https://github.com/python-attrs/attrs) for the
empirical analysis: it is a popular, mature Python library with a
well-organised Hypothesis-based test suite (61 PBTs across the `tests/`
folder). For the SMT translation we use a mix of (a) one boolean-state PBT
modelled directly on `attrs`'s `test_mix`, and (b) two synthetic but
representative PBTs (integer division, sorted-unique lists). See
`comparison.md` for why we do not translate `attrs`'s composite-strategy
tests.
