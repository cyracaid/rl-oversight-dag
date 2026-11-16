#!/usr/bin/env python3
"""Descriptive development controls; no training or confirmation data."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import random
import sys

import numpy as np
import torch
import proposal_gaps as P
from diagnose_proposal_gaps import digest, replay
from analyze_proposal_gaps import validate

CONTROLS = ('type belief greedy', 'type ranking')
REFERENCES = ('belief greedy', 'observed/nstep3', 'gain/nstep3')


def type_belief(env, graph):
    parents = [n['parents'] for n in env['nodes']]
    edges = {(p, i): P.SP.CFG['p_prop'] for i, ps in enumerate(parents) for p in ps}
    return P.ParticleBelief(parents, env['topo'], env['sinks'], edges,
                           [P.SP.P_TYPE[n['type']] for n in env['nodes']],
                           P.SP.CFG['p_catch'], P.SP.CFG['n_particles'], graph+10000)


def type_action(nodes, reviewed):
    return max((i for i, used in enumerate(reviewed) if not used),
               key=lambda i: (P.SP.P_TYPE[nodes[i]['type']], -i))


def control_rollout(graph, confidence, odds, policy):
    if policy not in CONTROLS:
        raise ValueError('unknown control')
    env = P.environment(graph, confidence, odds)
    belief = type_belief(env, graph) if policy == CONTROLS[0] else None
    base = list(env['base'])
    err = P.SP.compute_err(base, env['nodes'], env['topo'], env['coins'])
    initial = sum(bool(err[j]) for j in env['sinks'])
    reviewed, trace = [False]*P.M.N, []
    for step in range(P.M.R):
        action = (belief.best_action([not r for r in reviewed]) if belief is not None
                  else type_action(env['nodes'], reviewed))
        before = sum(bool(err[j]) for j in env['sinks'])
        deg = belief.n_degenerate if belief is not None else None
        row = dict(step=step, action=action, node_type=int(env['nodes'][action]['type']),
                   type_prior=P.SP.P_TYPE[env['nodes'][action]['type']],
                   p_error=float(belief.p_err()[action]) if belief is not None else None,
                   chosen_gain=belief.gain(action) if belief is not None else None,
                   error_support=belief.err[action].bit_count() if belief is not None else None,
                   true_base_before=bool(base[action]), true_error_before=bool(err[action]),
                   sink_errors_before=before)
        flagged, err = P.SP.review_step(action, base, err, env['nodes'], env['topo'],
                                        env['coins'], random.Random(0), env['catch_uniforms'])
        reviewed[action] = True
        if belief is not None:
            belief.observe(action, flagged)
        after = sum(bool(err[j]) for j in env['sinks'])
        row.update(flagged=bool(flagged), sink_errors_after=after,
                   realized_sink_reduction=before-after,
                   degenerate=belief.n_degenerate > deg if belief is not None else None)
        trace.append(row)
    return dict(initial_errors=initial, errors=after,
                degeneracies=belief.n_degenerate if belief is not None else None), trace


def summarize(rows):
    result = []
    for condition in sorted({r['condition'] for r in rows}):
        cell = [r for r in rows if r['condition']==condition]
        baselines = {p: {r['graph']: r['errors'] for r in cell if r['policy']==p}
                     for p in ('belief greedy',)+CONTROLS}
        for policy in REFERENCES+CONTROLS:
            selected = [r for r in cell if r['policy']==policy]
            if not selected:
                continue
            seeds = sorted({r['seed'] for r in selected}, key=str)
            for seed in seeds + (['all'] if seeds != [None] else []):
                rs = selected if seed=='all' else [r for r in selected if r['seed']==seed]
                if seed=='all':
                    counts = [sum(r['seed']==s for r in rs) for s in seeds]
                    if len(set(counts)) != 1:
                        raise ValueError('incomplete seed-by-graph matrix')
                n = len(rs)
                deg = [r['degeneracies'] for r in rs]
                row = dict(condition=condition, policy=policy, seed=seed, episodes=n,
                           errors=float(np.mean([r['errors'] for r in rs])),
                           degeneracies_per_episode=(float(np.mean(deg)) if all(v is not None for v in deg) else None),
                           degeneracies_per_review=(sum(deg)/(n*P.M.R) if all(v is not None for v in deg) else None),
                           flags_per_review=sum(r['flags'] for r in rs)/(n*P.M.R),
                           reduction_per_review=sum(r['reduction'] for r in rs)/(n*P.M.R))
                for p, label in [('belief greedy','greedy'), (CONTROLS[0],'type_belief'), (CONTROLS[1],'type_ranking')]:
                    row['delta_vs_'+label] = float(np.mean([r['errors']-baselines[p][r['graph']] for r in rs]))
                for t in range(P.M.K):
                    row[f'type_{t}_fraction'] = sum(r['type_counts'][t] for r in rs)/(n*P.M.R)
                result.append(row)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, default=Path('runs/proposal-gaps-full-v1'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--graphs', type=int, default=200)
    args = ap.parse_args()
    if not 1 <= args.graphs <= 200:
        ap.error('--graphs must be 1..200')
    torch.set_num_threads(1)
    data = json.loads((args.run/'results.json').read_text())
    validate(data, args.run)
    for name, expected in data['provenance']['source_sha256'].items():
        if digest(Path(__file__).parent/name) != expected:
            raise ValueError('original source mismatch: '+name)
    plan = Path(__file__).with_name('PROPOSAL_GAPS_NEXT_EXPERIMENT.md')
    manifest = dict(status='in_progress', evidence_level='descriptive development comparison',
                    results_sha256=digest(args.run/'results.json'), plan_sha256=digest(plan),
                    source_sha256=data['provenance']['source_sha256'],
                    checkpoint_sha256={k:v for k,v in data['checkpoints'].items()
                                       if '_nstep3_' in k},
                    script_sha256=digest(Path(__file__)),
                    replay_script_sha256=digest(Path(__file__).with_name('diagnose_proposal_gaps.py')),
                    graph_ids=data['graph_seeds'][:args.graphs], seeds=data['config']['seeds'],
                    python=sys.version, torch=torch.__version__, numpy=np.__version__)
    args.out.mkdir(parents=True, exist_ok=False)
    P.write_json(args.out/'manifest.json', manifest)
    episodes = []
    with torch.no_grad(), gzip.open(args.out/'steps.jsonl.gz', 'wt') as stream:
        for confidence in ('normal','noise','oracle'):
            models = {}
            for policy in REFERENCES[1:]:
                variant = policy.split('/')[0]
                for seed in data['config']['seeds']:
                    path = args.run/f'{confidence}_{variant}_nstep3_{seed}.pt'
                    model = P.Agent(variant)
                    model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
                    models[policy, seed] = model.eval()
            for schedule in ('matched','linear_odds_1_to_2'):
                condition = confidence+'/'+schedule
                for index, graph in enumerate(manifest['graph_ids']):
                    odds = 1. if schedule=='matched' else 1.+index/199
                    jobs = [('belief greedy',None,None)]+[(p,s,m) for (p,s),m in models.items()]
                    jobs += [(p,None,None) for p in CONTROLS]
                    for policy, seed, model in jobs:
                        if policy in CONTROLS:
                            outcome, trace = control_rollout(graph, confidence, odds, policy)
                        else:
                            variant = policy.split('/')[0] if model is not None else 'observed'
                            outcome, trace = replay(model, graph, confidence, variant, odds)
                            errors, deg = data['conditions'][condition][policy], data['degeneracies'][condition][policy]
                            if seed is not None:
                                si = data['config']['seeds'].index(seed)
                                errors, deg = errors[si], deg[si]
                            if (outcome['errors'],outcome['degeneracies']) != (errors[index],deg[index]):
                                raise ValueError(f'reference mismatch: {condition} {policy} {seed} {graph}')
                        meta = dict(condition=condition, graph=graph, odds=odds, policy=policy, seed=seed)
                        for row in trace:
                            stream.write(json.dumps(dict(meta, **row), allow_nan=False)+'\n')
                        episodes.append(dict(meta, **outcome, flags=sum(r['flagged'] for r in trace),
                                             reduction=sum(r['realized_sink_reduction'] for r in trace),
                                             type_counts=[sum(r['node_type']==t for r in trace) for t in range(P.M.K)]))
                    if (index+1)%20==0:
                        print(f'{condition}: {index+1}/{args.graphs} graphs; references verified', flush=True)
                print(condition+': complete', flush=True)
    summary = summarize(episodes)
    P.write_json(args.out/'episodes.json', episodes)
    P.write_json(args.out/'summary.json', summary)
    with (args.out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    lines = ['# Type-prior controls: descriptive development comparison','',
             'Post-result development study. No significance, equivalence, or confirmation claims.',
             'Differences are policy minus paired baseline; negative is fewer sink errors.',
             'All = equal-weight five-seed aggregate. Blank seed = one baseline trajectory per graph.',
             'Ranking has no posterior; null degeneracy means not applicable, not zero.','',
             '| Condition | Policy | Seed | Errors | Delta vs nominal | Delta vs type belief | Delta vs ranking |',
             '|---|---|---|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['condition']} | {r['policy']} | {r['seed']} | {r['errors']:.3f} | {r['delta_vs_greedy']:+.3f} | {r['delta_vs_type_belief']:+.3f} | {r['delta_vs_type_ranking']:+.3f} |")
    (args.out/'results.md').write_text('\n'.join(lines)+'\n')
    manifest.update(status='completed', reference_replay_verified=True,
                    episodes=len(episodes), steps=len(episodes)*P.M.R,
                    output_sha256={p.name:digest(p) for p in args.out.iterdir() if p.name!='manifest.json'})
    P.write_json(args.out/'manifest.json',manifest)
    print(f'PASS: {len(episodes)} episodes, {len(episodes)*P.M.R} steps. Output: {args.out}',flush=True)


if __name__ == '__main__':
    main()
