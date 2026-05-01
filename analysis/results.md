# PBT analysis of `target_project\tests`

| metric | count |
| --- | ---: |
| total `@given` tests | 59 |
| tests with at least one constraint | 7 |
| - using `assume(...)` | 4 |
| - using `min_*/max_*` strategy kwargs | 3 |
| - using `.filter(...)` | 0 |

## Per-file breakdown

| file | PBTs | constrained |
| --- | ---: | ---: |
| `test_3rd_party.py` | 1 | 0 |
| `test_dunders.py` | 9 | 0 |
| `test_funcs.py` | 29 | 2 |
| `test_functional.py` | 2 | 0 |
| `test_make.py` | 18 | 5 |

## Constrained tests (one row each)

| file:line | name | bounds | assume | filter |
| --- | --- | :---: | :---: | :---: |
| `test_funcs.py:613` | `test_change` |  | X |  |
| `test_funcs.py:687` | `test_change` |  | X |  |
| `test_make.py:1994` | `test_empty_metadata_singleton` | X |  |  |
| `test_make.py:2003` | `test_empty_countingattr_metadata_independent` | X |  |  |
| `test_make.py:2011` | `test_not_none_metadata` | X |  |  |
| `test_make.py:2620` | `test_mix` |  | X |  |
| `test_make.py:2687` | `test_mix` |  | X |  |
