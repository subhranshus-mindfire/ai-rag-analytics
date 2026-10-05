"""
High-performance Test Coverage Analyzer for app/ codebase.
Measures line execution coverage across app/ modules during unit tests.
Zero external dependencies (uses standard library AST & sys.settrace).
"""
import ast
import os
import sys
import unittest
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

executed_lines = defaultdict(set)
APP_DIR_STR = str(PROJECT_ROOT / "app")


def trace_lines(frame, event, arg):
    if event == "line":
        executed_lines[frame.f_code.co_filename].add(frame.f_lineno)
    return trace_lines


def trace_calls(frame, event, arg):
    if event == "call":
        filename = frame.f_code.co_filename
        # Fast bail-out for third-party libraries
        if filename.startswith(APP_DIR_STR) and "/tests/" not in filename:
            return trace_lines
        return None
    return None


def get_executable_lines(file_path: Path):
    """Parses Python file AST to find all executable statement line numbers."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except Exception:
        return set()

    executable = set()
    for node in ast.walk(tree):
        if hasattr(node, "lineno"):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                ast.Assign, ast.AugAssign, ast.Return, ast.If,
                                ast.For, ast.While, ast.Try, ast.With, ast.Expr, ast.Raise)):
                executable.add(node.lineno)
    return executable


def main():
    print("=" * 68)
    print("🧪 RUNNING TEST SUITE WITH COVERAGE ANALYSIS")
    print("=" * 68)

    # 1. Start execution tracer
    sys.settrace(trace_calls)

    # 2. Run all tests
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(PROJECT_ROOT / "app/tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    # 3. Stop tracer
    sys.settrace(None)

    print(f"Tests Run: {result.testsRun} | Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    print("=" * 68)
    print(f"{'Module File':<44} {'Stmts':>7} {'Miss':>7} {'Cover':>8}")
    print("-" * 68)

    app_dir = PROJECT_ROOT / "app"
    total_executable = 0
    total_covered = 0

    py_files = sorted([
        f for f in app_dir.rglob("*.py")
        if "/tests/" not in str(f) and "__pycache__" not in str(f) and f.name != "__init__.py"
    ])

    for f in py_files:
        rel_path = str(f.relative_to(PROJECT_ROOT))
        exec_lines = get_executable_lines(f)
        if not exec_lines:
            continue

        hit_lines = executed_lines.get(str(f.resolve()), set())
        covered = len(exec_lines.intersection(hit_lines))
        total_stmt = len(exec_lines)
        missed = total_stmt - covered
        pct = (covered / total_stmt) * 100 if total_stmt > 0 else 100.0

        total_executable += total_stmt
        total_covered += covered

        print(f"{rel_path:<44} {total_stmt:>7} {missed:>7} {pct:>7.1f}%")

    print("=" * 68)
    overall_pct = (total_covered / total_executable) * 100 if total_executable > 0 else 0
    total_missed = total_executable - total_covered
    print(f"{'TOTAL':<44} {total_executable:>7} {total_missed:>7} {overall_pct:>7.1f}%")
    print("=" * 68)

    if result.failures or result.errors:
        print(f"❌ Test suite failed with {len(result.failures)} failures and {len(result.errors)} errors.")
        sys.exit(1)

    if overall_pct < 80.0:
        print(f"❌ Coverage {overall_pct:.1f}% is below required 80.0% threshold!")
        sys.exit(1)

    print(f"✅ All tests passed and coverage gate satisfied ({overall_pct:.1f}% >= 80.0%).")
    sys.exit(0)


if __name__ == "__main__":
    main()
