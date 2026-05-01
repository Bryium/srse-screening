"""Make the project root importable so `smt_generators` and
`original_tests` resolve when pytest is launched from the repo root."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
