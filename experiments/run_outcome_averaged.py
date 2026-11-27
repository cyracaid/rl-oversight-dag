#!/usr/bin/env python3
"""Fixed catch-averaged versus matched sampled-control actual-policy study."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from belief import ParticleBelief
from exact_small_graph import ExactReview
from integrate_particle_policy import integrate
from outcome_averaged_rollout import selector


def summarize(rows, complete):
    summaries = []
    for profile in ['normal-confidence', 'type-prior']:
        for method in ['averaged', 'sampled-control']:
            cell = [r for r in rows if r['profile'] == profile and r['method'] == method]
            if not cell:
                continue
            gains = [r['greedy_errors']-r['errors'] for r in cell]
            ref_gain = float(np.mean([r['greedy_errors']-r['reference_1024_errors'] for r in cell]))
            summaries.append(dict(profile=profile, method=method, cases=len(cell),
                **{k: float(np.mean([r[k] for r in cell])) for k in
                   ['errors', 'expected_simulated_reviews', 'expected_posterior_updates',
                    'expected_posterior_copies', 'tree_seconds']},
                gain=float(np.mean(gains)), reference_gain=ref_gain,
                retained_gain=float(np.mean(gains))/ref_gain if ref_gain != 0. else None,
                wins=sum(g > 1e-9 for g in gains), ties=sum(abs(g) <= 1e-9 for g in gains),
                losses=sum(g < -1e-9 for g in gains),
                per_graph_gain={str(g): float(np.mean([r['greedy_errors']-r['errors'] for r in cell if r['graph'] == g]))
                                for g in sorted({r['graph'] for r in cell})}))
    gate = None
    if complete:
        averaged = [s for s in summaries if s['method'] == 'averaged']
        gate = (len(averaged) == 2 and all(s['cases'] == 48 and s['gain'] > 0 and s['retained_gain'] is not None and s['retained_gain'] >= .5 for s in averaged)
                and all(r['expected_simulated_reviews'] <= 8192 for r in rows if r['method'] == 'averaged'))
    paired = []
    for profile in ['normal-confidence', 'type-prior']:
        grouped = {}
        for r in rows:
            if r['profile'] == profile:
                grouped.setdefault((r['graph'], r['seed']), {})[r['method']] = r
        diffs = [p['sampled-control']['errors']-p['averaged']['errors'] for p in grouped.values() if len(p) == 2]
        if diffs:
            paired.append(dict(profile=profile, pairs=len(diffs), averaged_gain_over_control=float(np.mean(diffs))))
    return dict(cells=summaries, paired=paired, engineering_gate_passed=gate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    inputs = [Path('runs/small-graph-conditioned-v1/cases.json'),
              Path('runs/exact-particle-policy-v1/cases.json')]
    for p in inputs:
        receipt = json.loads(p.with_name('manifest.json').read_text())
        if hashlib.sha256(p.read_bytes()).hexdigest() != receipt['output_sha256']['cases.json']:
            raise ValueError('input hash mismatch')
    cases = {(c['seed'], c['profile']): c for c in json.loads(inputs[0].read_text()) if c['budget'] == 3}
    references = json.loads(inputs[1].read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).parent
    names = ['run_outcome_averaged.py', 'outcome_averaged_rollout.py', 'belief.py',
             'sampled_planning.py', 'exact_small_graph.py', 'integrate_particle_policy.py',
             'run_full_episode_guard.py', 'validate_selection_guard.py',
             'OUTCOME_AVERAGED_PROTOCOL.md', 'OUTCOME_AVERAGED_ROLLOUT_DESIGN.md',
             'test_outcome_averaged_rollout.py', 'test_outcome_averaged_runner.py']
    manifest = dict(status='in_progress', expected_trees=192, samples=128, particles=1024,
                    budget=3, seeds=list(range(4)), wall_limit_seconds=1800,
                    input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                    source_sha256={n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names})
    rows = []; started = time.perf_counter()

    def save():
        (args.out/'cases.json').write_text(json.dumps(rows, indent=2)+'\n')
        (args.out/'summary.json').write_text(json.dumps(summarize(rows, manifest['status'] == 'completed'), indent=2)+'\n')
        manifest['trees'] = len(rows)
        manifest['runner_seconds'] = time.perf_counter()-started
        manifest['output_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in args.out.iterdir() if p.name != 'manifest.json'}
        (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')

    save()
    try:
        for reference in references:
            c = cases[reference['graph'], reference['profile']]; seed = reference['seed']
            prior = c['conditioned_prior'] if c['profile'] == 'normal-confidence' else c['type_prior']
            env = ExactReview(c['parents'], prior, sinks=c['sinks'])
            edges = {(p, i): .6 for i, ps in enumerate(c['parents']) for p in ps}
            belief = ParticleBelief(c['parents'], range(6), c['sinks'], edges, prior, .9, 1024, seed+50000)
            for method in ['averaged', 'sampled-control']:
                if time.perf_counter()-started >= 1800:
                    manifest['status'] = 'incomplete_timeout'; save(); return
                result = integrate(env, belief, 3, seed, method, selector)
                leaves = [n for n in result['tree'] if 'action' not in n]
                assert abs(sum(n['mass'] for n in leaves)-1.) < 1e-10
                assert abs(sum(n['weighted_errors'] for n in leaves)-result['errors']) < 1e-10
                assert result['errors'] >= c['optimal']-1e-9
                for field in ['posterior_updates', 'posterior_copies']:
                    result['expected_'+field] = sum(n['mass']*n['detail']['search'][field]
                                                   for n in result['tree'] if 'action' in n)
                assert result['expected_simulated_reviews'] <= (7808 if method == 'averaged' else 4096)+1e-8
                rows.append(dict(graph=c['seed'], profile=c['profile'], seed=seed, method=method,
                                 exact_optimal=c['optimal'], greedy_errors=reference['results']['greedy']['errors'],
                                 reference_1024_errors=reference['results']['rollout']['errors'], **result))
                save()
            if seed == 3:
                print(c['seed'], c['profile'], 'complete', flush=True)
        assert len(rows) == len({(r['graph'], r['profile'], r['seed'], r['method']) for r in rows}) == 192
        manifest['status'] = 'completed'; save()
        print(json.dumps(summarize(rows, True), indent=2), flush=True)
    except Exception as error:
        manifest.update(status='failed', error=repr(error), trees=len(rows),
                        runner_seconds=time.perf_counter()-started)
        # Failure receipt must not depend on the summary that may have failed.
        (args.out/'cases.json').write_text(json.dumps(rows, indent=2)+'\n')
        manifest['output_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in args.out.iterdir() if p.name != 'manifest.json'}
        (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
