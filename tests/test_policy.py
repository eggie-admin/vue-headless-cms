from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.models import AgentDecision
from app.policy import apply_policy
from app.telemetry import sanitize_properties


class PolicyTests(unittest.TestCase):
    def test_model_cannot_downgrade_cleanup_risk(self):
        raw = AgentDecision(
            intent="cleanup.expired",
            tool="cleanup_cache",
            lane="local",
            risk="low",
            requires_confirmation=False,
        )
        decision = apply_policy(raw)
        self.assertEqual(decision.risk, "high")
        self.assertTrue(decision.requires_confirmation)

    def test_upload_escalates_to_cloud_and_confirmation(self):
        raw = AgentDecision(intent="upload.final", tool="upload_final", lane="local")
        decision = apply_policy(raw)
        self.assertEqual(decision.lane, "cloud")
        self.assertTrue(decision.requires_confirmation)

    def test_telemetry_strips_sensitive_fields(self):
        safe = sanitize_properties({
            "provider": "local",
            "prompt_text": "secret scene",
            "filesystem_path": "/private/file.mp4",
            "latency_ms": 12,
        })
        self.assertEqual(safe, {"provider": "local", "latency_ms": 12})


if __name__ == "__main__":
    unittest.main()
