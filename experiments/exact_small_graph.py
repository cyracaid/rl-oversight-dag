#!/usr/bin/env python3
"""Exact finite-belief planning; development diagnostics, no learning."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
import time

import numpy as np


class ExactReview:
    def __init__(self, parents, prior, propagation=0.6, catch=0.9, sinks=None):
        self.parents = parents
        self.n = len(parents)
        if not 1 <= self.n <= 8 or len(prior) != self.n:
            raise ValueError('require 1..8 nodes and one prior per node')
        if any(p < 0 or p >= i for i, ps in enumerate(parents) for p in ps):
            raise ValueError('parents must be earlier nodes in topological order')
        self.edges = [(p, i) for i, ps in enumerate(parents) for p in ps]
        if self.n + len(self.edges) > 16:
            raise ValueError('exact enumeration limited to 16 hidden bits')
        if any(not 0 <= p <= 1 for p in list(prior)+[propagation, catch]):
            raise ValueError('invalid probability')
        self.catch = catch
        self.sinks = ([i for i in range(self.n) if not any(i in ps for ps in parents)]
                      if sinks is None else list(sinks))
        if not self.sinks or len(set(self.sinks)) != len(self.sinks) or any(
                not 0 <= i < self.n for i in self.sinks):
            raise ValueError('require distinct valid output nodes')
        probs = np.array(list(prior)+[propagation]*len(self.edges))
        worlds = np.arange(1 << len(probs), dtype=np.uint32)
        bits = (worlds[:, None] >> np.arange(len(probs))) & 1
        weights = np.prod(np.where(bits, probs, 1-probs), axis=1)
        keep = weights > 0
        self.weights = weights[keep]
        self.bits = bits[keep].astype(bool)
        self.errors = {}
        self.costs = {}
        self.nodes_evaluated = 0

    def state(self, cleared):
        if cleared not in self.errors:
            err = self.bits[:, :self.n].copy()
            for i in range(self.n):
                if cleared & (1 << i):
                    err[:, i] = False
                for e, (p, child) in enumerate(self.edges):
                    if child == i:
                        err[:, i] |= err[:, p] & self.bits[:, self.n+e]
            self.errors[cleared] = err
            self.costs[cleared] = err[:, self.sinks].sum(axis=1)
        return self.errors[cleared], self.costs[cleared]

    def branches(self, weights, cleared, action):
        err, _ = self.state(cleared)
        positive = weights * (self.catch * err[:, action])
        return ((weights-positive, cleared), (positive, cleared | (1 << action)))

    def solve(self, budget):
        if not 0 <= budget <= self.n:
            raise ValueError('budget outside node count')
        self.nodes_evaluated = 0

        def visit(weights, reviewed, cleared, left):
            self.nodes_evaluated += 1
            err, cost = self.state(cleared)
            current = float(weights @ cost)
            if left == 0:
                return (current, current, current, None, None)
            available = [i for i in range(self.n) if not reviewed & (1 << i)]
            candidates = []
            immediate = []
            for a in available:
                values = np.zeros(3)
                next_cost = 0.
                for branch, next_cleared in self.branches(weights, cleared, a):
                    if branch.sum() == 0:
                        continue
                    _, terminal = self.state(next_cleared)
                    next_cost += float(branch @ terminal)
                    values += visit(branch, reviewed | (1 << a), next_cleared, left-1)[:3]
                candidates.append(values)
                immediate.append(next_cost)
            best = min(range(len(available)), key=lambda j: (candidates[j][0], available[j]))
            gains = current - np.array(immediate)
            maximum = float(gains.max())
            tolerance = 1e-12 * float(weights.sum())
            if maximum <= tolerance:
                pe = [float(weights @ err[:, a]) for a in available]
                greedy = max(range(len(available)), key=lambda j: (pe[j], -available[j]))
                # Tie-aware variant retains the same fallback rule when all gains vanish.
                tied = [j for j in range(len(available)) if abs(pe[j]-max(pe)) <= tolerance]
            else:
                tied = [j for j in range(len(available)) if maximum-gains[j] <= tolerance]
                greedy = tied[0]
            tie_best = min(tied, key=lambda j: candidates[j][2])
            return (float(candidates[best][0]), float(candidates[greedy][1]),
                    float(candidates[tie_best][2]), available[best], available[greedy])

        optimal, greedy, tie_greedy, first_opt, first_greedy = visit(self.weights, 0, 0, budget)
        fixed = min((self.fixed_value(order), list(order))
                    for order in itertools.combinations(range(self.n), budget))
        initial = float(self.weights @ self.state(0)[1])
        result = dict(initial=initial, optimal=optimal, greedy=greedy,
                      tie_aware_greedy=tie_greedy, fixed=fixed[0], fixed_nodes=fixed[1],
                      optimal_first=first_opt, greedy_first=first_greedy,
                      gap=greedy-optimal, tie_aware_gap=tie_greedy-optimal,
                      adaptivity_gap=fixed[0]-optimal,
                      gap_fraction_initial=(greedy-optimal)/initial if initial else 0.,
                      relative_gap=(greedy-optimal)/optimal if optimal > 1e-12 else None,
                      recursion_nodes=self.nodes_evaluated)
        if min(result['gap'], result['tie_aware_gap'], result['adaptivity_gap']) < -1e-9:
            raise AssertionError('optimality invariant failed')
        return result

    def fixed_value(self, order):
        # Sum feedback branches, without normalizing away their probabilities.
        states = {0: self.weights}
        for a in order:
            after = {}
            for cleared, weights in states.items():
                for branch, nc in self.branches(weights, cleared, a):
                    after[nc] = after.get(nc, 0) + branch
            states = after
        return sum(float(w @ self.state(c)[1]) for c, w in states.items())


def suite():
    motifs = [('chain', [[], [0], [1], [2], [3], [4]]),
              ('fork', [[], [0], [0], [0], [0], [0]]),
              ('diamond', [[], [0], [0], [1, 2], [3], [3]]),
              ('disconnected', [[], [0], [1], [], [3], [4]])]
    for seed in range(31000, 31012):
        rng = random.Random(seed)
        parents = [[], [], [], [], [], []]
        for i in range(2, 6):
            candidates = list(range(2)) if i < 4 else [2, 3]
            parents[i] = sorted(rng.sample(candidates, rng.choice([1, 2])))
        # Construction may have 8 edges; retain a deterministic six-edge maximum.
        while sum(map(len, parents)) > 6:
            parents[max(i for i, ps in enumerate(parents) if len(ps) > 1)].pop()
        motifs.append((f'layered-{seed}', parents))
    return motifs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    rows = []
    source = Path(__file__)
    protocol = source.with_name('SMALL_GRAPH_PLANNING_PROTOCOL.md')
    manifest = dict(status='in_progress', evidence='descriptive small-graph development',
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
                    propagation=0.6, catch=0.9, budgets=[1, 2, 3], numpy=np.__version__)
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    for index, (name, parents) in enumerate(suite()):
        for profile in ['type-prior', 'heterogeneous']:
            prior = ([.01, .03, .08, .15, .25]*2)[index % 5:index % 5+6] if profile == 'type-prior' else [.05, .15, .30, .50, .70, .90]
            env = ExactReview(parents, prior)
            for budget in [1, 2, 3]:
                row = dict(graph=name, profile=profile, parents=parents, prior=prior, budget=budget,
                           **env.solve(budget))
                rows.append(row)
                if budget == 1 and abs(row['gap']) > 1e-9:
                    raise AssertionError('budget-one equality failed')
            print(f'{name}/{profile}: complete', flush=True)
    (args.out/'cases.json').write_text(json.dumps(rows, indent=2, allow_nan=False)+'\n')
    summary = []
    for profile in ['type-prior', 'heterogeneous']:
        for budget in [1, 2, 3]:
            cell = [r for r in rows if r['profile'] == profile and r['budget'] == budget]
            summary.append(dict(profile=profile, budget=budget, graphs=len(cell),
                                **{key:float(np.mean([r[key] for r in cell])) for key in
                                   ['initial', 'optimal', 'greedy', 'fixed', 'gap', 'tie_aware_gap', 'adaptivity_gap', 'gap_fraction_initial']},
                                max_gap=max(r['gap'] for r in cell),
                                positive_gaps=sum(r['gap'] > 1e-9 for r in cell)))
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    manifest.update(status='completed', cases=len(rows), seconds=time.monotonic()-start,
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in args.out.iterdir() if p.name != 'manifest.json'})
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
