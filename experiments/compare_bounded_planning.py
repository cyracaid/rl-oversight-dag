#!/usr/bin/env python3
"""Receding-horizon exact-belief planning on frozen small development cases."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from exact_small_graph import ExactReview


def evaluate(env, budget, depth):
    """Depth-limited search uses adaptive greedy completion as leaf value.

    A fresh depth-limited choice is made after each real feedback branch.
    All values are integrated exactly, including the greedy completion.
    """
    calls = 0

    def greedy(weights, reviewed, cleared):
        err, cost = env.state(cleared)
        current = float(weights @ cost)
        available = [a for a in range(env.n) if not reviewed & (1 << a)]
        gains = []
        for a in available:
            value = sum(float(w @ env.state(c)[1]) for w, c in env.branches(weights, cleared, a))
            gains.append(current-value)
        tolerance = 1e-12*float(weights.sum())
        maximum = max(gains)
        if maximum <= tolerance:
            return max(available, key=lambda a: (float(weights @ err[:, a]), -a))
        return next(a for a, gain in zip(available, gains) if maximum-gain <= tolerance)

    def search(weights, reviewed, cleared, left, horizon):
        nonlocal calls
        calls += 1
        if not left:
            return float(weights @ env.state(cleared)[1]), None
        available = ([greedy(weights, reviewed, cleared)] if horizon == 0 else
                     [a for a in range(env.n) if not reviewed & (1 << a)])
        candidates = []
        for a in available:
            value = sum(search(w, reviewed | (1 << a), c, left-1, max(0, horizon-1))[0]
                        for w, c in env.branches(weights, cleared, a) if w.sum() > 0)
            candidates.append((value, a))
        # Use scaled tolerance and index tie breaking, matching exact greedy.
        minimum = min(v for v, _ in candidates)
        return next((v, a) for v, a in candidates
                    if v-minimum <= 1e-12*float(weights.sum()))

    def rollout(weights, reviewed, cleared, left):
        if not left:
            return float(weights @ env.state(cleared)[1])
        _, a = search(weights, reviewed, cleared, left, min(depth, left))
        return sum(rollout(w, reviewed | (1 << a), c, left-1)
                   for w, c in env.branches(weights, cleared, a) if w.sum() > 0)

    if not 1 <= depth <= env.n:
        raise ValueError('depth outside node count')
    start = time.perf_counter()
    value = rollout(env.weights, 0, 0, budget)
    return dict(errors=value, search_calls=calls, seconds=time.perf_counter()-start)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=Path('runs/small-graph-conditioned-v1'))
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads((args.input/'manifest.json').read_text())
    if manifest['status'] != 'completed':
        raise ValueError('input incomplete')
    for name, digest in manifest['output_sha256'].items():
        if hashlib.sha256((args.input/name).read_bytes()).hexdigest() != digest:
            raise ValueError('input hash mismatch: '+name)
    cases = json.loads((args.input/'cases.json').read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for c in cases:
        key = 'conditioned_prior' if c['profile'] == 'normal-confidence' else 'type_prior'
        env = ExactReview(c['parents'], c[key], sinks=c['sinks'])
        for depth in [1, 2, 3]:
            result = evaluate(env, c['budget'], depth)
            if result['errors'] < c['optimal']-1e-9:
                raise AssertionError('below exact optimal')
            if depth >= c['budget'] and abs(result['errors']-c['optimal']) > 1e-9:
                raise AssertionError('full horizon differs from exact optimal')
            rows.append(dict(seed=c['seed'], profile=c['profile'], budget=c['budget'], depth=depth,
                             optimal=c['optimal'], greedy=c['greedy'],
                             remaining_gap=result['errors']-c['optimal'],
                             improvement_over_greedy=c['greedy']-result['errors'], **result))
    summary = []
    for profile in ['normal-confidence', 'type-prior']:
        for budget in [1, 2, 3]:
            for depth in [1, 2, 3]:
                cell = [r for r in rows if (r['profile'], r['budget'], r['depth']) == (profile, budget, depth)]
                summary.append(dict(profile=profile, budget=budget, depth=depth,
                                    **{k:sum(r[k] for r in cell)/len(cell) for k in
                                       ['errors', 'remaining_gap', 'improvement_over_greedy', 'search_calls', 'seconds']},
                                    optimal_cases=sum(abs(r['remaining_gap']) < 1e-9 for r in cell),
                                    worse_than_greedy=sum(r['improvement_over_greedy'] < -1e-9 for r in cell)))
    for name, value in [('cases.json', rows), ('summary.json', summary)]:
        (args.out/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    receipt = dict(status='completed', cases=len(rows),
                   input_manifest_sha256=hashlib.sha256((args.input/'manifest.json').read_bytes()).hexdigest(),
                   source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                  [Path(__file__), Path(__file__).with_name('exact_small_graph.py'),
                                   Path(__file__).with_name('BOUNDED_PLANNING_PROTOCOL.md')]},
                   output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in args.out.iterdir()})
    (args.out/'manifest.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
