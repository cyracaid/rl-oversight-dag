#!/usr/bin/env python3
"""Copy the SciForge injection result into this repo, with provenance.

The audit's numbers are produced in the SciForge repository and measured there; this
repo only reports them. Rather than re-deriving them, the aggregate is copied verbatim
together with the commit it came from and a digest over the payload, so
``run_layered_report.py`` can tell a stale copy from an edited one.

Run it again whenever the SciForge artifact changes:

    python3 triage_bench/sync_sciforge_injection.py

The SciForge checkout is `$SCIFORGE_DIR` (default `~/Documents/SciForge`). Nothing here
touches the sleep data, so this works on a machine without it.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from bench import config

SOURCE_REL = "packages/domains/evidence-dag/eval-cases/injection/injection.v1.json"
SOURCE_COMMAND = "npm run injection"
DEFAULT_SOURCE_DIR = Path.home() / "Documents" / "SciForge"
SOURCE_DIR_ENV = "SCIFORGE_DIR"
OUT_NAME = "sciforge_injection.json"


def payload_digest(payload: dict) -> str:
    """Digest over the numbers only, so provenance cannot mask a changed result."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source_dir() -> Path:
    raw = os.environ.get(SOURCE_DIR_ENV)
    return Path(raw).expanduser().resolve() if raw else DEFAULT_SOURCE_DIR.resolve()


def _commit(directory: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def build(directory: Path) -> dict:
    source = directory / SOURCE_REL
    payload = json.loads(source.read_text(encoding="utf-8"))
    return {
        "provenance": {
            "repository": "SciForge",
            "path": SOURCE_REL,
            "commit": _commit(directory),
            "command": SOURCE_COMMAND,
            "sha256": payload_digest(payload),
        },
        "payload": payload,
    }


def main() -> int:
    directory = _source_dir()
    if not (directory / SOURCE_REL).is_file():
        print(f"not found: {directory / SOURCE_REL}")
        print(f"set {SOURCE_DIR_ENV} to a SciForge checkout that has run `{SOURCE_COMMAND}`.")
        return 1
    document = build(directory)
    (config.OUT_DIR / OUT_NAME).write_text(json.dumps(document, indent=2) + "\n")
    print(f"wrote {config.OUT_DIR / OUT_NAME} from {directory} at {document['provenance']['commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
