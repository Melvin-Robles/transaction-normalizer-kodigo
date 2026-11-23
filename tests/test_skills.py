"""Pruebas automatizadas de estructura y comportamiento de las Agent Skills."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
AUDITOR = SKILLS_ROOT / "transaction-auditor" / "scripts" / "audit_batch.py"
RULES_VALIDATOR = SKILLS_ROOT / "normalization-rules" / "scripts" / "validate_rules.py"
REGRESSION = SKILLS_ROOT / "regression-validator" / "scripts" / "run_regression.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=30,
    )


class AgentSkillsTests(unittest.TestCase):
    def test_skill_metadata_and_resources_are_present(self) -> None:
        names = ["transaction-auditor", "normalization-rules", "regression-validator"]
        descriptions: list[str] = []
        for name in names:
            skill_dir = SKILLS_ROOT / name
            skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(skill_text.startswith("---\n"))
            frontmatter = skill_text.split("---\n", 2)[1].splitlines()
            metadata = {
                key: value.strip()
                for line in frontmatter
                if ":" in line
                for key, value in [line.split(":", 1)]
            }
            self.assertEqual(metadata.get("name"), name)
            self.assertTrue(name == name.lower())
            self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertTrue(metadata.get("description"))
            descriptions.append(metadata["description"])
            self.assertTrue(any((skill_dir / "scripts").iterdir()))
            self.assertTrue(any((skill_dir / "references").iterdir()))
        self.assertEqual(len(set(descriptions)), len(descriptions))

    def test_auditor_is_reproducible_safe_and_handles_document_errors(self) -> None:
        example = ROOT / "data" / "transacciones_ejemplo.json"
        malformed = ROOT / "data" / "pruebas_ui" / "transacciones_malformadas.json"
        before = sha256(example)

        first = run_script(AUDITOR, str(example))
        second = run_script(AUDITOR, str(example))
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))
        report = json.loads(first.stdout)
        self.assertEqual(report["summary"], {"total_processed": 3, "valid_count": 3, "invalid_count": 0, "quality_percent": 100.0})
        self.assertEqual(report["totals_by_currency"], {"EUR": "99.99", "USD": "201.00"})
        self.assertNotIn("tx_001", first.stdout)
        self.assertEqual(before, sha256(example))

        failed = run_script(AUDITOR, str(malformed))
        self.assertEqual(failed.returncode, 2)
        self.assertIn("error", json.loads(failed.stderr))

    def test_rules_validator_reports_valid_configuration_without_writing_it(self) -> None:
        rules = ROOT / "config" / "rules.json"
        before = sha256(rules)
        completed = run_script(RULES_VALIDATOR, "--rules", str(rules))

        self.assertEqual(completed.returncode, 0)
        report = json.loads(completed.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual([source["name"] for source in report["sources"]], ["A", "B", "C"])
        self.assertEqual(before, sha256(rules))

        with tempfile.TemporaryDirectory() as temporary:
            invalid_rules = Path(temporary) / "rules.json"
            invalid_rules.write_text("{}", encoding="utf-8")
            failed = run_script(RULES_VALIDATOR, "--rules", str(invalid_rules))
            self.assertEqual(failed.returncode, 2)
            self.assertIn("error", json.loads(failed.stderr))

    def test_regression_runner_executes_project_checks(self) -> None:
        completed = run_script(
            REGRESSION,
            "--test-pattern",
            "test_characterization.py",
            "--timeout",
            "30",
        )

        self.assertEqual(completed.returncode, 0)
        report = json.loads(completed.stdout)
        self.assertTrue(report["overall_passed"])
        self.assertTrue(report["checks"]["unittest"]["passed"])
        self.assertTrue(report["checks"]["compileall"]["passed"])
        self.assertTrue(report["checks"]["integrated_example"]["passed"])


if __name__ == "__main__":
    unittest.main()
