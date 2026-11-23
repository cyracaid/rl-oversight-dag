#!/usr/bin/env python3
"""Read-only development checkpoint replay. Never trains or uses confirmation graphs."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys

import numpy as np
import torch
import proposal_gaps as P


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(model, graph, confidence, variant, odds):
    env = P.environment(graph, confidence, odds)
    belief = env['belief']
    base = list(env['base'])
    err = P.SP.compute_err(base, env['nodes'], env['topo'], env['coins'])
    reviewed, flagged = [False] * P.M.N, [False] * P.M.N
    trace = []
    initial_errors = sum(bool(err[j]) for j in env['sinks'])
    for step in range(P.M.R):
        gains = np.array([belief.gain(i) for i in range(P.M.N)])
        pe, pb = belief.p_err(), belief.p_base()
        available = [not r for r in reviewed]
        greedy = belief.best_action(available)
        if model is None:
            action = greedy
        else:
            x = P.features(env, variant, reviewed, flagged, P.M.R-step)
            scores = model.policy.score(x, env['A']).masked_fill(
                torch.tensor(reviewed), -float('inf'))
            action = int(scores.argmax())
        support = belief.err[action].bit_count()
        before = sum(bool(err[j]) for j in env['sinks'])
        deg_before = belief.n_degenerate
        row = dict(step=step, action=action, same_history_greedy=greedy,
                   agrees_greedy=action == greedy,
                   chosen_gain=float(gains[action]), greedy_gain=float(gains[greedy]),
                   gain_gap=float(gains[greedy]-gains[action]),
                   greedy_zero_gain_fallback=bool(max(gains[available]) == 0),
                   p_error=float(pe[action]), p_base=float(pb[action]),
                   error_support=support, particles=belief.M,
                   zero_support_available=int(np.sum(pe[available] == 0)),
                   confidence=float(env['conf'][action]),
                   node_type=int(env['nodes'][action]['type']),
                   sink_reach=sum(belief.is_sink[j] for j in belief.desc[action])
                              + int(belief.is_sink[action]),
                   is_sink=bool(belief.is_sink[action]),
                   true_base_before=bool(base[action]), true_error_before=bool(err[action]),
                   expected_sink_errors=float(sum(pe[j] for j in env['sinks'])),
                   sink_errors_before=before, degeneracies_before=deg_before)
        f, err = P.SP.review_step(action, base, err, env['nodes'], env['topo'],
                                 env['coins'], random.Random(0), env['catch_uniforms'])
        # Observation likelihood and pre-resampling ESS, not particle-diversity ESS.
        weights = np.full(belief.M, 1.0)
        has_error = belief._bits_to_bool(belief.err[action])
        if f:
            weights = has_error.astype(float)
        else:
            weights -= belief.p_catch * has_error
        likelihood = float(weights.mean())
        row['observation_probability'] = likelihood
        row['likelihood_ess'] = (float(weights.sum()**2 / np.square(weights).sum())
                                 if likelihood > 0 else 0.0)
        reviewed[action], flagged[action] = True, f
        belief.observe(action, f)
        after = sum(bool(err[j]) for j in env['sinks'])
        row.update(flagged=bool(f), degenerate=belief.n_degenerate > deg_before,
                   sink_errors_after=after, realized_sink_reduction=before-after)
        trace.append(row)
    return dict(initial_errors=initial_errors, errors=after,
                degeneracies=belief.n_degenerate), trace


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, default=Path('runs/proposal-gaps-full-v1'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--graphs', type=int, default=200,
                    help='First N original development graphs; 200 for full diagnosis.')
    args = ap.parse_args()
    torch.set_num_threads(1)
    raw = args.run / 'results.json'
    data = json.loads(raw.read_text())
    if data['status'] != 'completed' or data['graph_seeds'] != list(range(1000, 1200)):
        ap.error('requires completed full-v1 development run, graph IDs 1000-1199')
    if not 1 <= args.graphs <= 200:
        ap.error('--graphs must be between 1 and 200')
    for name, expected in data['provenance']['source_sha256'].items():
        path = Path(__file__).parent / name
        if digest(path) != expected:
            raise ValueError('Original source hash mismatch: ' + name)
    selected = ('observed/nstep3', 'gain/nstep3')
    checks = {}
    models = {}
    for confidence in ('normal', 'noise', 'oracle'):
        for policy in selected:
            variant, method = policy.split('/')
            for seed in data['config']['seeds']:
                name = f'{confidence}_{variant}_{method}_{seed}.pt'
                path = args.run / name
                checks[name] = digest(path)
                if checks[name] != data['checkpoints'][name]:
                    raise ValueError('Checkpoint hash mismatch: ' + name)
                model = P.Agent(variant)
                model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
                models[confidence, policy, seed] = model.eval()
    args.out.mkdir(parents=True, exist_ok=False)
    provenance = dict(status='in_progress', evidence_level='exploratory development diagnosis',
                      results_sha256=digest(raw), script_sha256=digest(Path(__file__)),
                      source_sha256=data['provenance']['source_sha256'], checkpoint_sha256=checks,
                      graph_ids=data['graph_seeds'][:args.graphs], policies=list(selected),
                      seeds=data['config']['seeds'], python=sys.version,
                      torch=torch.__version__, numpy=np.__version__)
    P.write_json(args.out/'manifest.json', provenance)
    episodes, summaries = [], []
    with torch.no_grad(), gzip.open(args.out/'steps.jsonl.gz', 'wt') as stream:
        for condition in data['conditions']:
            confidence, schedule = condition.split('/')
            start = len(episodes)
            for index, graph in enumerate(data['graph_seeds'][:args.graphs]):
                odds = 1.0 if schedule == 'matched' else 1.0 + index/199
                jobs = [('belief greedy', None, None)] + [
                    (policy, seed, models[confidence, policy, seed])
                    for policy in selected for seed in data['config']['seeds']]
                for policy, seed, model in jobs:
                    variant = 'observed' if model is None else policy.split('/')[0]
                    outcome, trace = replay(model, graph, confidence, variant, odds)
                    expected_error = data['conditions'][condition][policy]
                    expected_deg = data['degeneracies'][condition][policy]
                    if seed is not None:
                        si = data['config']['seeds'].index(seed)
                        expected_error, expected_deg = expected_error[si], expected_deg[si]
                    if (outcome['errors'], outcome['degeneracies']) != (expected_error[index], expected_deg[index]):
                        raise ValueError(f'Replay mismatch: {condition} {policy} seed={seed} graph={graph}')
                    meta = dict(condition=condition, policy=policy, seed=seed, graph=graph, odds=odds)
                    for row in trace:
                        stream.write(json.dumps(dict(meta, **row), allow_nan=False)+'\n')
                    greedy_error = data['conditions'][condition]['belief greedy'][index]
                    episodes.append(dict(meta, **outcome, delta_vs_greedy=outcome['errors']-greedy_error,
                                         agreement=float(np.mean([r['agrees_greedy'] for r in trace])),
                                         mean_gain_gap=float(np.mean([r['gain_gap'] for r in trace])),
                                         flags=sum(r['flagged'] for r in trace),
                                         zero_gain_steps=sum(r['greedy_zero_gain_fallback'] for r in trace)))
                if (index+1) % 20 == 0:
                    print(f'{condition}: {index+1}/{args.graphs} graphs verified', flush=True)
            cell = episodes[start:]
            for policy in ('belief greedy',) + selected:
                seeds = [None] if policy == 'belief greedy' else data['config']['seeds']
                for seed in seeds:
                    rows = [r for r in cell if r['policy'] == policy and r['seed'] == seed]
                    for subset in ('all', 'with_degeneracy', 'without_degeneracy'):
                        rs = [r for r in rows if subset == 'all' or
                              (r['degeneracies'] > 0) == (subset == 'with_degeneracy')]
                        summaries.append(dict(condition=condition, policy=policy, seed=seed, subset=subset,
                                              episodes=len(rs), degeneracies=sum(r['degeneracies'] for r in rs),
                                              **{k: float(np.mean([r[k] for r in rs])) if rs else None
                                                 for k in ('errors', 'delta_vs_greedy', 'agreement',
                                                           'mean_gain_gap', 'flags', 'zero_gain_steps')}))
            print(f'{condition}: complete; all outcomes and degeneracies match originals', flush=True)
    for name, rows in [('episodes.csv', episodes), ('summary.csv', summaries)]:
        with (args.out/name).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    P.write_json(args.out/'summary.json', summaries)
    provenance.update(status='completed', replay_verified=True, episodes=len(episodes),
                      steps=len(episodes)*P.M.R,
                      output_sha256={p.name: digest(p) for p in args.out.iterdir() if p.name != 'manifest.json'})
    P.write_json(args.out/'manifest.json', provenance)
    (args.out/'README.md').write_text(
        '# Checkpoint replay diagnosis\n\n'
        'Exploratory development-only analysis. Every replayed final error and degeneracy count '
        'matches its original saved cell. No training or confirmation graphs used.\n\n'
        '`summary.csv` reports each condition/policy/seed and all/with/without-degeneracy subsets. '
        '`episodes.csv` retains graph-level outcomes. `steps.jsonl.gz` retains action traces. '
        '`manifest.json` records hashes and completion.\n\n'
        'Degeneracy means an unsupported positive observation, not every particle-collapse mode. '
        'Likelihood ESS measures observation weights before resampling, not unique latent particles. '
        'Truth fields are diagnostic only and never supplied to the policy. '
        'Same-history greedy is a one-step comparator, not optimal planning. '
        'Degeneracy subsets depend on policy; their outcome differences are observational, not causal. '
        'Greedy has one trajectory per graph; learned policies have five seeds. Compare rates, '
        'not raw event totals. A nonzero gain gap is under the nominal belief, not true regret.\n')
    print(f'PASS: {len(episodes)} episodes, {len(episodes)*P.M.R} steps. Output: {args.out}', flush=True)


if __name__ == '__main__':
    main()
