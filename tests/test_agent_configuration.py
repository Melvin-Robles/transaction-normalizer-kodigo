"""Validación estructural de la personalización local de Codex."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_ROOT = ROOT / ".codex"


class AgentConfigurationTests(unittest.TestCase):
    def test_project_config_uses_supported_agent_settings(self) -> None:
        with (CODEX_ROOT / "config.toml").open("rb") as file:
            config = tomllib.load(file)

        self.assertEqual(config["agents"]["enabled"], True)
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 2)
        self.assertNotIn("default_subagent_model", config["agents"])

    def test_custom_agents_have_required_fields_and_route_to_existing_skills(self) -> None:
        expected = {
            "transaction_reviewer.toml": ["transaction-auditor", "normalization-rules"],
            "quality_guardian.toml": ["regression-validator"],
        }

        for filename, skill_names in expected.items():
            with (CODEX_ROOT / "agents" / filename).open("rb") as file:
                agent = tomllib.load(file)
            self.assertIsInstance(agent.get("name"), str)
            self.assertIsInstance(agent.get("description"), str)
            instructions = agent.get("developer_instructions")
            self.assertIsInstance(instructions, str)
            for skill_name in skill_names:
                self.assertIn(skill_name, instructions)
                self.assertTrue((ROOT / ".agents" / "skills" / skill_name / "SKILL.md").is_file())

    def test_agent_names_are_distinct_and_do_not_set_unsupported_session_controls(self) -> None:
        agents = []
        for path in sorted((CODEX_ROOT / "agents").glob("*.toml")):
            with path.open("rb") as file:
                data = tomllib.load(file)
            agents.append(data["name"])
            self.assertNotIn("sandbox_mode", data)
            self.assertNotIn("approval_policy", data)
            self.assertNotIn("mcp_servers", data)
        self.assertEqual(len(agents), len(set(agents)))


if __name__ == "__main__":
    unittest.main()
