# Meshgate Gate — offline topology invariant checker

QMOOSA-1000 canonical component QMOOSA-0950 / Batch 190 / TESTS.

This draft implementation checks an offline, undirected mesh graph supplied as JSON. It rejects duplicate nodes/links, self-links, unknown endpoints, malformed inputs and disconnected graphs. The output includes a deterministic SHA-256 digest of canonical graph data for comparison; it is not a cryptographic proof or network security assessment.

## Run

Python 3.11+; no third-party packages, network calls or credentials.

~~~bash
python -m compileall -q src tests
python -m unittest discover -s tests -p 'test_*.py' -v
python src/mesh_topology_gate.py topology.json
~~~

Example topology.json:

~~~json
{"nodes":["node-a","node-b","node-c"],"links":[["node-a","node-b"],["node-b","node-c"]]}
~~~

A valid connected graph returns exit code 0 and status PASS_OFFLINE_TOPOLOGY_ONLY. Invalid or partitioned graphs return exit code 2. The input is limited to 1 MB, 1,000 nodes and 10,000 undirected links.

Explicit limitations: No live network discovery, routing, packet forwarding, partition recovery, cryptographic authentication, PQC, FIPS validation, RPC, consensus, escrow, or deployment readiness. The Rust executable is deliberately fail-closed because no Rust mesh runtime has been implemented. No 100/100 production score is asserted.

CI runs Python compilation, implementation-coupled positive/adversarial regressions, Rust formatting/build checks and Python CodeQL. A green workflow does not imply complete product implementation or independent security acceptance. Keep the PR draft pending review.
