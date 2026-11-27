#!/usr/bin/env python3
"""Second Bellman solver plus deterministic regeneration of saved policy actions."""
import copy
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from policy_leaf_audit import WorldTable


def solve(table, budget, catch=.9):
    """Normalized posteriors rebuilt from history; not original weight recursion."""
    def state(history):
        weights = table.weights.copy(); cleared = set()
        for action, flag in history:
            positive = catch*table.errors(cleared)[:, action]
            weights *= positive if flag else 1.-positive
            if flag:
                cleared.add(action)
        mass = float(weights.sum())
        return weights/mass, cleared

    def visit(history):
        posterior, cleared = state(history)
        cost = table.errors(cleared)[:, table.sinks].sum(axis=1)
        current = float(posterior@cost)
        if len(history) == budget:
            return current, current, None
        available = [i for i in range(len(table.parents)) if i not in [a for a, f in history]]
        q_opt = {}; q_greedy = {}; next_errors = {}; probabilities = {}
        for action in available:
            positive = catch*table.errors(cleared)[:, action]
            chance = float(posterior@positive)
            probabilities[action] = float(posterior@table.errors(cleared)[:, action])
            immediate = 0.; opt = greedy = 0.
            for flag, probability in [(0, 1.-chance), (1, chance)]:
                if probability <= 0.:
                    continue
                next_history = history+((action, flag),)
                child_p, child_cleared = state(next_history)
                immediate += probability*float(child_p@table.errors(child_cleared)[:, table.sinks].sum(axis=1))
                child_opt, child_greedy, _ = visit(next_history)
                opt += probability*child_opt; greedy += probability*child_greedy
            q_opt[action] = opt; q_greedy[action] = greedy
            next_errors[action] = immediate
        improvements = {a: current-next_errors[a] for a in available}
        maximum = max(improvements.values())
        if maximum <= 1e-12:
            chosen = max(available, key=lambda a: (probabilities[a], -a))
        else:
            chosen = next(a for a in available if maximum-improvements[a] <= 1e-12)
        first = min(available, key=lambda a: (q_opt[a], a))
        return q_opt[first], q_greedy[chosen], first
    optimal, greedy, first = visit(())
    return dict(optimal=optimal, greedy=greedy, optimal_first=first)


def saved_detail_equal(detail, saved):
    """JSON stores integer dictionary keys as strings; preserve exact values."""
    return json.loads(json.dumps(detail)) == saved


def replay(case, row, method, policy, run):
    # Same production chooser is deliberately used: tests deterministic replay,
    # not independent correctness of the chooser implementation.
    from belief import ParticleBelief
    from integrate_particle_policy import decision
    from run_policy_cost import selector_for
    from outcome_averaged_rollout import selector
    prior = case['conditioned_prior'] if case['profile'] == 'normal-confidence' else case['type_prior']
    edges = {(p, i): .6 for i, ps in enumerate(case['parents']) for p in ps}
    initial = ParticleBelief(case['parents'], range(6), case['sinks'], edges, prior, .9, 1024, row['seed']+50000)
    nodes = {tuple(map(tuple, node['history'])): node for node in policy['tree']}
    count = 0

    def visit(history, posterior, mask):
        nonlocal count
        node = nodes[history]
        if 'action' not in node:
            return
        if run == 'exact-particle-policy-v1':
            action, detail = decision(posterior, mask, 3-len(history), len(history), row['seed'], method)
        elif run == 'policy-cost-v1':
            action, detail = selector_for(row['samples'])(posterior, mask, 3-len(history), len(history), row['seed'], 'rollout')
        else:
            action, detail = selector(posterior, mask, 3-len(history), len(history), row['seed'], method)
        assert action == node['action'], (run, row['graph'], row['profile'], row['seed'], method, history, 'action')
        assert saved_detail_equal(detail, node['detail']), (run, row['graph'], row['profile'], row['seed'], method, history, 'detail')
        count += 1
        for flag in [0, 1]:
            child_history = history+((action, flag),)
            if child_history in nodes:
                child = copy.deepcopy(posterior); child.observe(action, bool(flag))
                child_mask = list(mask); child_mask[action] = False
                visit(child_history, child, child_mask)
    visit((), initial, [True]*6)
    assert count == sum('action' in n for n in policy['tree'])
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out; out.mkdir(parents=True, exist_ok=False)
    runs = ['exact-particle-policy-v1', 'policy-cost-v1', 'outcome-averaged-v1-retry1']
    inputs = [Path('runs/small-graph-conditioned-v1/cases.json')]+[Path('runs')/r/'cases.json' for r in runs]
    for p in inputs:
        receipt = json.loads(p.with_name('manifest.json').read_text())
        assert receipt['status'] == 'completed'
        assert hashlib.sha256(p.read_bytes()).hexdigest() == receipt['output_sha256']['cases.json']
    root = Path(__file__).parent
    names = ['solver_action_audit.py', 'policy_leaf_audit.py', 'belief.py',
             'integrate_particle_policy.py', 'sampled_planning.py', 'run_policy_cost.py',
             'run_full_episode_guard.py', 'validate_selection_guard.py', 'outcome_averaged_rollout.py']
    manifest = dict(status='in_progress',
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        source_sha256={n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names})
    exact_rows = []; replay_rows = []; started = time.perf_counter()

    def save():
        (out/'solver.json').write_text(json.dumps(exact_rows, indent=2)+'\n')
        (out/'replay.json').write_text(json.dumps(replay_rows, indent=2)+'\n')
        manifest.update(seconds=time.perf_counter()-started, solver_cases=len(exact_rows), policy_trees=len(replay_rows),
                        replayed_decisions=sum(r['decisions'] for r in replay_rows))
        manifest['output_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name != 'manifest.json'}
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    save()
    try:
        cases = json.loads(inputs[0].read_text()); tables = {}
        for c in cases:
            key = c['seed'], c['profile']
            if key not in tables:
                prior = c['conditioned_prior'] if c['profile'] == 'normal-confidence' else c['type_prior']
                tables[key] = WorldTable(c['parents'], prior, c['sinks'])
            result = solve(tables[key], c['budget'])
            assert abs(result['optimal']-c['optimal']) < 1e-10
            assert abs(result['greedy']-c['greedy']) < 1e-10
            exact_rows.append(dict(graph=c['seed'], profile=c['profile'], budget=c['budget'],
                                   optimal_error=abs(result['optimal']-c['optimal']),
                                   greedy_error=abs(result['greedy']-c['greedy']), **result))
        assert len(exact_rows) == 72
        save(); print('72 solver cases verified', flush=True)
        case_map = {(c['seed'], c['profile']): c for c in cases if c['budget'] == 3}
        for source in inputs[1:]:
            for row in json.loads(source.read_text()):
                policies = row['results'].items() if 'results' in row else [(row.get('method', str(row.get('samples'))), row)]
                for method, policy in policies:
                    count = replay(case_map[row['graph'], row['profile']], row, method, policy, source.parent.name)
                    replay_rows.append(dict(run=source.parent.name, graph=row['graph'], profile=row['profile'],
                                            seed=row['seed'], method=method, decisions=count))
                save()
            print(source.parent.name, 'actions and full decision details replayed', flush=True)
        assert len(replay_rows) == 672
        manifest['status'] = 'completed'; save()
        print(json.dumps({k: manifest[k] for k in ['status', 'solver_cases', 'policy_trees', 'replayed_decisions', 'seconds']}, indent=2))
    except Exception as error:
        manifest.update(status='failed', error=repr(error)); save(); raise


if __name__ == '__main__':
    main()
