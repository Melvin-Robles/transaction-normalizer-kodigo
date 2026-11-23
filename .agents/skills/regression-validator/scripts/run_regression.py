"""Run bounded regression checks for the transaction normalizer."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from transaction_normalizer.config import load_rules  # noqa: E402
from transaction_normalizer.models import NormalizerError  # noqa: E402
from transaction_normalizer.service import TransactionProcessingService  # noqa: E402


def run_command(args: Sequence[str], timeout: float) -> dict[str, Any]:
    """Run a fixed executable argument list without invoking a shell."""

    try:
        completed = subprocess.run(
            list(args),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return {
            "passed": False,
            "returncode": 124,
            "timed_out": True,
            "output": output[-4000:],
        }
    return {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "timed_out": False,
        "output": (completed.stdout + completed.stderr)[-4000:],
    }


def check_integrated_example() -> dict[str, Any]:
    """Compare the actual integrated example with the frozen contract."""

    rules = load_rules(REPO_ROOT / "config" / "rules.json")
    payload = (REPO_ROOT / "data" / "transacciones_ejemplo.json").read_bytes()
    batch = TransactionProcessingService(rules).process_document(payload)
    actual = {
        "processed": len(batch.records),
        "valid": len(batch.result.valid),
        "invalid": len(batch.result.invalid),
        "usd": format(batch.metrics["all_valid_totals_by_currency"].get("USD", 0), ".2f"),
        "eur": format(batch.metrics["all_valid_totals_by_currency"].get("EUR", 0), ".2f"),
    }
    expected = {"processed": 3, "valid": 3, "invalid": 0, "usd": "201.00", "eur": "99.99"}
    return {"passed": actual == expected, "expected": expected, "actual": actual}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ejecuta regresión segura del proyecto.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Tiempo máximo por subprocess, en segundos")
    parser.add_argument("--test-pattern", default="test*.py", help="Patrón de unittest discover")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.timeout <= 0:
        print(json.dumps({"error": "--timeout debe ser positivo"}), file=sys.stderr)
        return 2
    if not args.test_pattern or any(char in args.test_pattern for char in "&|;<>$`"):
        print(json.dumps({"error": "--test-pattern contiene caracteres no permitidos"}), file=sys.stderr)
        return 2

    try:
        unittest_result = run_command(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", args.test_pattern, "-v"],
            args.timeout,
        )
        compile_result = run_command(
            [sys.executable, "-m", "compileall", "-q", "app.py", "src", "tests"],
            args.timeout,
        )
        example_result = check_integrated_example()
    except (OSError, NormalizerError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    report = {
        "checks": {
            "unittest": unittest_result,
            "compileall": compile_result,
            "integrated_example": example_result,
        }
    }
    report["overall_passed"] = all(check["passed"] for check in report["checks"].values())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
