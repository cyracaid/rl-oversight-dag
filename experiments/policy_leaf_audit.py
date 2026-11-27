#!/usr/bin/env python3
"""Second evaluator: scalar hidden-world construction and direct leaf likelihoods.

No imports from original environment, particle belief, planner or integrator.
Audits saved actions, not their generation or the optimal reference solver.
"""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np


class WorldTable:
    def __init__(self, parents, prior, sinks, propagation=.6):
        self.parents = parents; self.sinks = sinks
        self.edges = [(p, i) for i, ps in enumerate(parents) for p in ps]
        self.worlds = []; self.weights = []; self.cache = {}
        probabilities = list(prior)+[propagation]*len(self.edges)
        for bits in itertools.product([False, True], repeat=len(probabilities)):
            weight = 1.
            for bit, probability in zip(bits, probabilities):
                weight *= probability if bit else 1.-probability
            if weight:
                self.worlds.append(bits); self.weights.append(weight)
        self.weights = np.asarray(self.weights)

    def errors(self, cleared):
        cleared = frozenset(cleared)
        if cleared not in self.cache:
            result = []
            for bits in self.worlds:
                errors = []
                for i in range(len(self.parents)):
                    wrong = bool(bits[i] and i not in cleared)
                    for edge, (parent, child) in enumerate(self.edges):
                        if child == i and errors[parent] and bits[len(self.parents)+edge]:
                            wrong = True
                    errors.append(wrong)
                result.append(errors)
            self.cache[cleared] = np.asarray(result)
        return self.cache[cleared]


def evaluate(table, tree, expected, catch=.9):
    actions = {tuple(map(tuple, node['history'])): node['action']
               for node in tree if 'action' in node}
    leaves = [node for node in tree if 'action' not in node]
    total_mass = total_cost = max_mass_error = max_cost_error = 0.
    for leaf in leaves:
        likelihood = np.ones(len(table.weights)); cleared = set(); prefix = []
        for action, flag in leaf['history']:
            assert actions[tuple(prefix)] == action
            assert action not in [a for a, f in prefix]
            positive = catch*table.errors(cleared)[:, action]
            likelihood *= positive if flag else 1.-positive
            if flag:
                cleared.add(action)
            prefix.append((action, flag))
        weight = table.weights*likelihood
        mass = float(weight.sum())
        cost = float(weight@table.errors(cleared)[:, table.sinks].sum(axis=1))
        max_mass_error = max(max_mass_error, abs(mass-leaf['mass']))
        max_cost_error = max(max_cost_error, abs(cost-leaf['weighted_errors']))
        assert abs(mass-leaf['mass']) < 1e-10
        assert abs(cost-leaf['weighted_errors']) < 1e-10
        total_mass += mass; total_cost += cost
    assert abs(total_mass-1.) < 1e-10
    assert abs(total_cost-expected) < 1e-10
    return dict(errors=total_cost, leaves=len(leaves), max_mass_error=max_mass_error,
                max_cost_error=max_cost_error, value_error=abs(total_cost-expected))


def main():
    out = Path('runs/policy-leaf-audit-v1'); out.mkdir(exist_ok=False)
    inputs = [Path('runs/small-graph-conditioned-v1/cases.json')]+[
        Path('runs')/run/'cases.json' for run in
        ['exact-particle-policy-v1', 'policy-cost-v1', 'outcome-averaged-v1-retry1']]
    for p in inputs:
        receipt = json.loads(p.with_name('manifest.json').read_text())
        assert receipt['status'] == 'completed'
        assert hashlib.sha256(p.read_bytes()).hexdigest() == receipt['output_sha256']['cases.json']
    cases = {(c['seed'], c['profile']): c for c in json.loads(inputs[0].read_text()) if c['budget'] == 3}
    tables = {}
    for key, c in cases.items():
        prior = c['conditioned_prior'] if c['profile'] == 'normal-confidence' else c['type_prior']
        tables[key] = WorldTable(c['parents'], prior, c['sinks'])
    results = []
    for source in inputs[1:]:
        for row in json.loads(source.read_text()):
            policies = row['results'].items() if 'results' in row else [(row.get('method', str(row.get('samples'))), row)]
            for method, policy in policies:
                result = evaluate(tables[row['graph'], row['profile']], policy['tree'], policy['errors'])
                results.append(dict(run=source.parent.name, graph=row['graph'], profile=row['profile'],
                                    seed=row['seed'], method=method, **result))
        print(source.parent.name, 'verified', flush=True)
    assert len(results) == 672
    summary = dict(policy_trees=len(results), leaves=sum(r['leaves'] for r in results),
                   max_mass_error=max(r['max_mass_error'] for r in results),
                   max_cost_error=max(r['max_cost_error'] for r in results),
                   max_value_error=max(r['value_error'] for r in results))
    (out/'cases.json').write_text(json.dumps(results, indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    manifest = dict(status='completed',
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        source_sha256={str(Path(__file__)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
