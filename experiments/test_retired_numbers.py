#!/usr/bin/env python3
"""Fail when a document quotes a number that a later run superseded.

`RETIRED_NUMBERS.md` holds the registry: a regex for the old value, the value that
replaced it, the commit that superseded it, and the paths where the old value may
legitimately survive (frozen run directories, amendments, pre-registrations).

The rerun that motivated this (`79fb5b1`) updated fourteen files and still left the
superseded P2 miss in three paper drafts. Per-document assertions cannot catch that
class of drift, because each rerun needs someone to remember which documents quoted
the old number. The registry puts that memory in one place and the test enforces it
everywhere.

Run: python3 experiments/test_retired_numbers.py
"""

import fnmatch
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "RETIRED_NUMBERS.md")
BEGIN, END = "<!-- retired:begin -->", "<!-- retired:end -->"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def registry():
    """Rows of (pattern, replacement, commit, allowed globs, why)."""
    body = read(REGISTRY)
    if BEGIN not in body or END not in body:
        raise SystemExit("RETIRED_NUMBERS.md lost its retired:begin/end markers")
    block = body.split(BEGIN, 1)[1].split(END, 1)[0]
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) != 5:
            raise SystemExit(f"malformed registry row ({len(cells)} cells): {line}")
        pattern, replacement, commit, allowed, why = cells
        rows.append((re.compile(pattern), replacement, commit,
                     [g.strip() for g in allowed.split(",") if g.strip()], why))
    if not rows:
        raise SystemExit("the registry is empty; an empty registry guards nothing")
    return rows


def documents():
    """Every tracked markdown file, relative to the repo root."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = ""
        for base, _, files in os.walk(ROOT):
            for name in files:
                if name.endswith(".md"):
                    rel = os.path.relpath(os.path.join(base, name), ROOT)
                    out += rel + "\0"
    return [p for p in out.split("\0") if p]


def allowed(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def test_no_document_quotes_a_retired_number():
    rows = registry()
    offenders = []
    for rel in documents():
        if rel == "RETIRED_NUMBERS.md":
            continue
        body = read(os.path.join(ROOT, rel)).replace("\u2212", "-")
        for pattern, replacement, commit, globs, _ in rows:
            if allowed(rel, globs):
                continue
            for number, line in enumerate(body.splitlines(), 1):
                if pattern.search(line):
                    offenders.append(
                        f"{rel}:{number}: still cites /{pattern.pattern}/ "
                        f"(retired by {commit}, now {replacement}): {line.strip()[:80]}")
    assert not offenders, "\n".join(offenders)


def test_every_replacement_is_actually_published():
    """A registry row whose successor appears nowhere is a typo or a stale row."""
    rows, corpus = registry(), []
    for rel in documents():
        if rel != "RETIRED_NUMBERS.md":
            corpus.append(read(os.path.join(ROOT, rel)))
    corpus = "\n".join(corpus).replace("\u2212", "-")
    missing = [replacement for _, replacement, _, _, _ in rows
               if replacement not in corpus]
    assert not missing, f"replacement values appear in no document: {missing}"


def test_the_registry_does_not_allowlist_living_documents():
    """Frozen evidence only. Allowing a paper draft would make the guard decorative."""
    living = ("PAPER_DRAFT.md", "PAPER_DRAFT_CN.md", "PAPER_DRAFT_KO.md",
              "README.md", "BENCHMARK_SPEC.md", "COURSE_FINAL_REPORT.md")
    for _, _, _, globs, _ in registry():
        for pattern in globs:
            for name in living:
                assert not fnmatch.fnmatch(name, pattern), (
                    f"allowlist pattern {pattern!r} covers the living document {name}")


def main():
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as error:
                failures += 1
                print(f"FAIL {name}\n{error}\n")
    print(f"{len([n for n in globals() if n.startswith('test_')]) - failures}"
          f"/{len([n for n in globals() if n.startswith('test_')])} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
