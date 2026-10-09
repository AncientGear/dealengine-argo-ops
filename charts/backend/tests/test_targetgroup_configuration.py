"""Offline Helm render checks; no cluster access."""
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CHART = ROOT / "charts/backend"
DEV = ROOT / "environments/dev/values.yaml"


def render(*args):
    return subprocess.run(
        [
            "helm", "template", "backend", str(CHART),
            "--namespace", "backend-dev", *args,
        ],
        capture_output=True,
        text=True,
    )


def configurations(output):
    return [
        doc for doc in yaml.safe_load_all(output)
        if doc and doc.get("kind") == "TargetGroupConfiguration"
    ]


class TargetGroupConfigurationTest(unittest.TestCase):
    def test_dev_configures_backend_readiness(self):
        result = render("-f", str(DEV))
        self.assertEqual(result.returncode, 0, result.stderr)
        docs = configurations(result.stdout)
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc["apiVersion"], "gateway.k8s.aws/v1")
        self.assertEqual(doc["metadata"]["name"], "backend")
        self.assertEqual(doc["spec"]["targetReference"], {
            "group": "", "kind": "Service", "name": "backend",
        })
        self.assertEqual(doc["spec"]["defaultConfiguration"]["healthCheckConfig"], {
            "healthCheckPath": "/readyz",
            "healthCheckPort": "traffic-port",
            "healthCheckProtocol": "HTTP",
            "matcher": {"httpCode": "200"},
        })

    def test_base_defaults_disable_configuration(self):
        result = render(
            "--set-string", "image.repository=example.invalid/backend",
            "--set-string", "image.digest=sha256:test",
            "--set-string", "existingSecret=runtime",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(configurations(result.stdout), [])

    def test_path_can_be_overridden(self):
        result = render(
            "-f", str(DEV),
            "--set-string", "targetGroupConfiguration.healthCheckPath=/custom-ready",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        docs = configurations(result.stdout)
        self.assertEqual(len(docs), 1)
        health = docs[0]["spec"]["defaultConfiguration"]["healthCheckConfig"]
        self.assertEqual(health["healthCheckPath"], "/custom-ready")

    def test_enabled_configuration_rejects_empty_path(self):
        result = render(
            "-f", str(DEV),
            "--set-string", "targetGroupConfiguration.healthCheckPath=",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "targetGroupConfiguration.healthCheckPath is required",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()