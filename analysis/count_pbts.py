"""
PBT detector for Hypothesis-based test suites.

Walks every `.py` file under the given directory and reports, per file:
    * Number of @given-decorated tests.
    * How many of those tests declare at least one constraint, where a
      "constraint" is any of:
          - a strategy argument named min_value / max_value /
            min_size / max_size / min_magnitude / max_magnitude
          - a call to assume(...) inside the test body
          - a .filter(...) chain on a strategy used by the test
    * The breakdown by constraint kind (a single test may use several).

Run:
    python analysis/count_pbts.py target_project/tests

The script writes a markdown summary to stdout and (optionally) to a file.
"""

from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


CONSTRAINT_KW = {
    "min_value",
    "max_value",
    "min_size",
    "max_size",
    "min_magnitude",
    "max_magnitude",
}


@dataclass
class TestStats:
    """Per-test record."""

    name: str
    file: str
    line: int
    has_bound_kw: bool = False
    has_assume: bool = False
    has_filter: bool = False

    @property
    def is_constrained(self) -> bool:
        return self.has_bound_kw or self.has_assume or self.has_filter


@dataclass
class FileStats:
    path: str
    tests: list[TestStats] = field(default_factory=list)

    @property
    def n_pbts(self) -> int:
        return len(self.tests)

    @property
    def n_constrained(self) -> int:
        return sum(1 for t in self.tests if t.is_constrained)


def _is_given_decorator(node: ast.expr) -> bool:
    """`@given(...)` or `@hypothesis.given(...)` style."""
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id == "given"
    if isinstance(node, ast.Attribute):
        return node.attr == "given"
    return False


def _decorator_uses_bound_kw(dec: ast.expr) -> bool:
    """True if a @given(...) decorator's strategies pass min_*/max_* kwargs."""
    if not isinstance(dec, ast.Call):
        return False
    for sub in ast.walk(dec):
        if isinstance(sub, ast.Call):
            for kw in sub.keywords:
                if kw.arg in CONSTRAINT_KW:
                    return True
    return False


def _decorator_uses_filter(dec: ast.expr) -> bool:
    """True if any strategy inside @given(...) is followed by .filter(...)."""
    if not isinstance(dec, ast.Call):
        return False
    for sub in ast.walk(dec):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "filter"
        ):
            return True
    return False


def _body_calls_assume(body: list[ast.stmt]) -> bool:
    """True if the test body calls assume(...) anywhere (incl. nested)."""
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Call):
                fn = sub.func
                if isinstance(fn, ast.Name) and fn.id == "assume":
                    return True
                if isinstance(fn, ast.Attribute) and fn.attr == "assume":
                    return True
    return False


def _body_uses_filter(body: list[ast.stmt]) -> bool:
    """True if the body chains .filter(...) onto a strategy."""
    for stmt in body:
        for sub in ast.walk(stmt):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "filter"
            ):
                return True
    return False


def _analyse_func(func: ast.FunctionDef | ast.AsyncFunctionDef, path: str) -> TestStats | None:
    """Return a TestStats if `func` is decorated with @given, else None."""
    given_decs = [d for d in func.decorator_list if _is_given_decorator(d)]
    if not given_decs:
        return None

    rec = TestStats(name=func.name, file=path, line=func.lineno)
    for dec in given_decs:
        if _decorator_uses_bound_kw(dec):
            rec.has_bound_kw = True
        if _decorator_uses_filter(dec):
            rec.has_filter = True
    if _body_calls_assume(func.body):
        rec.has_assume = True
    if _body_uses_filter(func.body):
        rec.has_filter = True
    return rec


def analyse_file(path: str) -> FileStats:
    fs = FileStats(path=path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
    except (SyntaxError, UnicodeDecodeError):
        return fs

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rec = _analyse_func(node, path)
            if rec is not None:
                fs.tests.append(rec)
    return fs


def analyse_tree(root: str) -> list[FileStats]:
    out: list[FileStats] = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in files:
            if fname.endswith(".py"):
                fs = analyse_file(os.path.join(dirpath, fname))
                if fs.n_pbts:
                    out.append(fs)
    return sorted(out, key=lambda f: f.path)


def render_report(stats: list[FileStats], root: str) -> str:
    total_pbts = sum(f.n_pbts for f in stats)
    total_constr = sum(f.n_constrained for f in stats)
    n_assume = sum(1 for f in stats for t in f.tests if t.has_assume)
    n_bounds = sum(1 for f in stats for t in f.tests if t.has_bound_kw)
    n_filter = sum(1 for f in stats for t in f.tests if t.has_filter)

    lines: list[str] = []
    lines.append(f"# PBT analysis of `{root}`")
    lines.append("")
    lines.append("| metric | count |")
    lines.append("| --- | ---: |")
    lines.append(f"| total `@given` tests | {total_pbts} |")
    lines.append(f"| tests with at least one constraint | {total_constr} |")
    lines.append(f"| - using `assume(...)` | {n_assume} |")
    lines.append(f"| - using `min_*/max_*` strategy kwargs | {n_bounds} |")
    lines.append(f"| - using `.filter(...)` | {n_filter} |")
    lines.append("")
    lines.append("## Per-file breakdown")
    lines.append("")
    lines.append("| file | PBTs | constrained |")
    lines.append("| --- | ---: | ---: |")
    for fs in stats:
        rel = os.path.relpath(fs.path, start=root)
        lines.append(f"| `{rel}` | {fs.n_pbts} | {fs.n_constrained} |")
    lines.append("")
    lines.append("## Constrained tests (one row each)")
    lines.append("")
    lines.append("| file:line | name | bounds | assume | filter |")
    lines.append("| --- | --- | :---: | :---: | :---: |")
    for fs in stats:
        rel = os.path.relpath(fs.path, start=root)
        for t in fs.tests:
            if not t.is_constrained:
                continue
            lines.append(
                f"| `{rel}:{t.line}` | `{t.name}` | "
                f"{'X' if t.has_bound_kw else ''} | "
                f"{'X' if t.has_assume else ''} | "
                f"{'X' if t.has_filter else ''} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: count_pbts.py <tests-dir> [output.md]", file=sys.stderr)
        return 2
    root = argv[1]
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    stats = analyse_tree(root)
    report = render_report(stats, root)
    print(report)
    if len(argv) >= 3:
        Path(argv[2]).write_text(report, encoding="utf-8")
        print(f"\nwrote: {argv[2]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
