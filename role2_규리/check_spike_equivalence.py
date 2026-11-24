"""Show that the uncommitted ticket additions do not change spike-family graphs.

`generate_graph("spike", seed)` is the only generator the corruption and verify
sweeps use. The working tree adds a ticket family to ``dag_role3/graphs.py`` and
``dag_role3/__init__.py``; this script imports the package twice - once from the
working tree, once with those two files replaced by their ``HEAD`` contents - and
compares the full structural output on the seeds the sweeps actually used.

    python3 check_spike_equivalence.py
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
PACKAGE = ROOT / "role3 improvement" / "dag_role3"
OVERRIDES = ("graphs.py", "__init__.py")
RECORD = HERE.parent / "results" / "verify-v1" / "spike_path_equivalence.json"
SEEDS = (3200, 3219)

PROBE = '''
import hashlib, json, sys
sys.path.insert(0, sys.argv[1])
from dag_role3 import generate_graph
out = []
for seed in range(%d, %d + 1):
    g = generate_graph("spike", seed)
    out.append({"seed": seed, "n": g.n, "layers": list(map(int, g.layers)),
                "sinks": sorted(map(int, g.sinks)), "topo": list(map(int, g.topo)),
                "edges": sorted((int(a), int(b)) for a, b in zip(*g.edge_index())),
                "types": list(map(int, g.types)), "rates": list(map(float, g.rates)),
                "lambda": round(float(g.spike_probability), 12), "names": list(g.names)})
print(hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest())
''' % SEEDS


def head_bytes(name):
    return subprocess.run(["git", "show", f"HEAD:role3 improvement/dag_role3/{name}"],
                          capture_output=True, check=True, cwd=ROOT).stdout


def structure_hash(clean_head):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        shutil.copytree(PACKAGE, target / "dag_role3")
        if clean_head:
            for name in OVERRIDES:
                (target / "dag_role3" / name).write_bytes(head_bytes(name))
        (target / "probe.py").write_text(PROBE)
        done = subprocess.run(["python3", str(target / "probe.py"), str(target)],
                              capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(done.stderr[-2000:])
    return done.stdout.strip()


def main():
    work = structure_hash(clean_head=False)
    head = structure_hash(clean_head=True)
    record = {
        "claim": "the uncommitted ticket additions (graphs.py, __init__.py) do not change spike-family graphs",
        "scope": f"generate_graph('spike', seed) for seeds {SEEDS[0]}-{SEEDS[1]} "
                 "(topology, types, rates, names, lambda)",
        "head_graphs_sha256": hashlib.sha256(head_bytes("graphs.py")).hexdigest(),
        "worktree_graphs_sha256": hashlib.sha256((PACKAGE / "graphs.py").read_bytes()).hexdigest(),
        "structure_sha256_head": head,
        "structure_sha256_worktree": work,
        "identical": head == work,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    if not record["identical"]:
        raise SystemExit("spike graphs differ between HEAD and the working tree")


if __name__ == "__main__":
    main()
