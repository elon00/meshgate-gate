"""Implementation-coupled offline graph and CLI regression tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mesh_topology_gate import TopologyError, validate  # noqa: E402


class MeshTopologyTests(unittest.TestCase):
    def good(self):
        return {"nodes": ["a", "b", "c"], "links": [["a", "b"], ["b", "c"]]}

    def fails(self, value, error):
        with self.assertRaisesRegex(TopologyError, error):
            validate(value)

    def test_connected(self):
        self.assertEqual(validate(self.good())["link_count"], 2)

    def test_single_node(self):
        self.assertEqual(validate({"nodes": ["solo"], "links": []})["node_count"], 1)

    def test_canonical_fingerprint_is_order_independent(self):
        first = validate(self.good())["topology_sha256"]
        second = validate({"nodes": ["c", "a", "b"], "links": [["c", "b"], ["b", "a"]]})["topology_sha256"]
        self.assertEqual(first, second)

    def test_partition(self):
        self.fails({"nodes": ["a", "b", "c"], "links": [["a", "b"]]}, "PARTITION_DETECTED")

    def test_empty_nodes(self):
        self.fails({"nodes": [], "links": []}, "INVALID_NODE_COUNT")

    def test_duplicate_nodes(self):
        self.fails({"nodes": ["a", "a"], "links": []}, "DUPLICATE_NODE")

    def test_duplicate_link_reverse(self):
        self.fails({"nodes": ["a", "b"], "links": [["a", "b"], ["b", "a"]]}, "DUPLICATE_LINK")

    def test_self_link(self):
        self.fails({"nodes": ["a"], "links": [["a", "a"]]}, "SELF_LINK")

    def test_unknown_endpoint(self):
        self.fails({"nodes": ["a"], "links": [["a", "missing"]]}, "UNKNOWN_ENDPOINT")

    def test_invalid_node_id(self):
        self.fails({"nodes": ["../unsafe"], "links": []}, "INVALID_NODE_ID")

    def test_non_string_node(self):
        self.fails({"nodes": [1], "links": []}, "INVALID_NODE_ID")

    def test_wrong_link_shape(self):
        self.fails({"nodes": ["a", "b"], "links": [["a", "b", "c"]]}, "INVALID_LINK")

    def test_unexpected_schema(self):
        self.fails({"nodes": ["a"], "links": [], "verified": True}, "EXPECTED_NODES_AND_LINKS")

    def test_too_many_nodes(self):
        self.fails({"nodes": [str(i) for i in range(1001)], "links": []}, "INVALID_NODE_COUNT")

    def test_wrong_links_type(self):
        self.fails({"nodes": ["a"], "links": "none"}, "INVALID_LINK_COUNT")

    def run_cli(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.json"
            path.write_text(data, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "src" / "mesh_topology_gate.py"), str(path)],
                capture_output=True, text=True, timeout=10, check=False,
            )

    def test_cli_accepts_real_connected_input(self):
        result = self.run_cli(json.dumps(self.good()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS_OFFLINE_TOPOLOGY_ONLY")

    def test_cli_rejects_partition(self):
        result = self.run_cli(json.dumps({"nodes": ["a", "b"], "links": []}))
        self.assertEqual(result.returncode, 2)
        self.assertIn("PARTITION_DETECTED", result.stderr)

    def test_cli_rejects_duplicate_json_keys(self):
        result = self.run_cli('{"nodes":["a"],"links":[],"links":[]}')
        self.assertEqual(result.returncode, 2)
        self.assertIn("DUPLICATE_JSON_KEY", result.stderr)

    def test_cli_rejects_malformed_json(self):
        result = self.run_cli("{")
        self.assertEqual(result.returncode, 2)

    def test_cli_rejects_nonstandard_nan(self):
        result = self.run_cli('{"nodes":["a"],"links":[],"extra":NaN}')
        self.assertEqual(result.returncode, 2)
        self.assertIn("NONSTANDARD_JSON_NUMBER", result.stderr)

    def test_cli_rejects_oversized_input(self):
        result = self.run_cli(" " * 1_000_001)
        self.assertEqual(result.returncode, 2)
        self.assertIn("INPUT_TOO_LARGE", result.stderr)


if __name__ == "__main__":
    unittest.main()
