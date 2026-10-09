import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
CHART = ROOT / "charts/backend"
DEV = ROOT / "environments/dev/values.yaml"


def render(*args):
    return subprocess.check_output(
        ["helm", "template", "backend", str(CHART), "--namespace", "backend-dev", *args],
        text=True,
    )


class RdsCaTest(unittest.TestCase):
    def test_dev_mounts_public_bundle_without_owning_secret(self):
        output = render("-f", str(DEV))
        self.assertIn("kind: ConfigMap", output)
        self.assertIn("name: backend-rds-ca", output)
        self.assertIn("mountPath: /etc/rds-ca", output)
        self.assertIn("readOnly: true", output)
        self.assertIn("key: us-east-2-bundle.pem", output)
        self.assertIn("path: us-east-2-bundle.pem", output)
        bundle = (CHART / "files/us-east-2-bundle.pem").read_text()
        self.assertGreater(bundle.count("-----BEGIN CERTIFICATE-----"), 0)
        for line in bundle.splitlines():
            self.assertIn(line, output)
        self.assertNotIn("kind: Secret\n", output)
        self.assertIn('name: "backend-runtime"', output)

    def test_base_defaults_do_not_mount_ca(self):
        output = render("--set", "image.repository=example.invalid/backend",
                        "--set", "image.digest=sha256:test",
                        "--set", "existingSecret=runtime")
        self.assertNotIn("kind: ConfigMap", output)
        self.assertNotIn("/etc/rds-ca", output)
        self.assertNotIn("volumeMounts:", output)
        self.assertNotIn("volumes:", output)

    def test_dev_can_disable_ca(self):
        output = render("-f", str(DEV), "--set", "rdsCa.enabled=false")
        self.assertNotIn("kind: ConfigMap", output)
        self.assertNotIn("/etc/rds-ca", output)


if __name__ == "__main__":
    unittest.main()
