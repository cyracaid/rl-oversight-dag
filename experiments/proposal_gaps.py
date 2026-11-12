#!/usr/bin/env python3
"""Opt-in proposal experiments. Importing this module never runs experiments."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
import torch

import rl_boundary as B
import rl_gnn_multiseed as M
import spike_active_selection as SP
from belief import ParticleBelief, conf_posterior, sample_conf
from rl_cmdp_gnn import GNNPolicy


def environment(seed, confidence, odds):
    """Policy-independent graph, truth and review draws; nominal model stays frozen."""
    rng = random.Random(seed)
    env = M.build_env(rng, 10000 + seed, with_belief=False)
    truth_rng = random.Random(seed + 2**40)
    env['base'] = [truth_rng.random() < B.odds_scale(SP.P_TYPE[n['type']], odds)
                   for n in env['nodes']]
    signal_rng = random.Random(seed + 2**41)
    noise_rng = random.Random(seed + 2**42)
    conf = [sample_conf(v, SP.P_TYPE[n['type']], signal_rng)
            for v, n in zip(env['base'], env['nodes'])]
    if confidence == 'noise':
        conf = [noise_rng.random() for _ in conf]
    elif confidence == 'oracle':
        conf = [0. if v else 1. for v in env['base']]
    elif confidence != 'normal':
        raise ValueError('unknown confidence condition')
    env['conf'] = conf
    env['S'][:, M.K] = torch.tensor(conf)
    parents = [n['parents'] for n in env['nodes']]
    edges = {(p, i): SP.CFG['p_prop'] for i, ps in enumerate(parents) for p in ps}
    prior = [conf_posterior(min(1-1e-6, max(1e-6, c)), SP.P_TYPE[n['type']])
             for c, n in zip(conf, env['nodes'])]
    env['belief'] = ParticleBelief(parents, env['topo'], env['sinks'], edges,
                                  prior, SP.CFG['p_catch'], SP.CFG['n_particles'],
                                  seed + 10000)
    env['catch_uniforms'] = SP.episode_uniforms(random.Random(seed + 2**43), M.N)
    return env


def features(env, variant, reviewed, flagged, remaining):
    x = M.features(env, 'observed', reviewed, flagged, remaining)
    if variant == 'gain':
        gains = torch.tensor([env['belief'].gain(i) / len(env['sinks'])
                              for i in range(M.N)])
        x = torch.cat([x, gains[:, None]], dim=1)
    return x


def targets(rewards, values, n):
    """Undiscounted n-step targets, terminal bootstrap exactly zero."""
    result = []
    for t in range(len(rewards)):
        end = min(t + n, len(rewards))
        target = sum(rewards[t:end])
        if end < len(rewards):
            target += float(values[end].detach())
        result.append(target)
    return torch.tensor(result, dtype=values.dtype)


class Agent(torch.nn.Module):
    def __init__(self, variant):
        super().__init__()
        dim = M.K + 7 + (variant == 'gain')
        self.policy = GNNPolicy(d=dim)
        self.critic = torch.nn.Sequential(torch.nn.Linear(dim, 32), torch.nn.Tanh(),
                                          torch.nn.Linear(32, 1))


def rollout(model, seed, confidence, variant, method, train=False, odds=1., baseline=0., temperature=1.):
    env = environment(seed, confidence, odds)
    base = list(env['base'])
    err = SP.compute_err(base, env['nodes'], env['topo'], env['coins'])
    reviewed, flagged = [False] * M.N, [False] * M.N
    logps, values = [], []
    for t in range(M.R):
        if model is None:
            a = env['belief'].best_action([not r for r in reviewed])
        else:
            x = features(env, variant, reviewed, flagged, M.R-t)
            mask = torch.tensor(reviewed)
            scores = model.policy.score(x, env['A']).masked_fill(mask, -float('inf'))
            if train:
                dist = torch.distributions.Categorical(logits=scores / temperature)
                action = dist.sample()
                a = int(action)
                logps.append(dist.log_prob(action))
                values.append(model.critic(x[~mask].mean(0)).squeeze())
            else:
                a = int(scores.argmax())
        f, err = SP.review_step(a, base, err, env['nodes'], env['topo'], env['coins'],
                                random.Random(0), env['catch_uniforms'])
        reviewed[a], flagged[a] = True, f
        env['belief'].observe(a, f)
    errors = sum(bool(err[j]) for j in env['sinks'])
    loss = None
    if train:
        value = torch.stack(values)
        n = {'reinforce': M.R, 'ac': M.R, 'nstep3': 3, 'nstep5': 5}[method]
        returns = targets([0.] * (M.R-1) + [-float(errors)], value, n)
        advantage = returns - (baseline if method == 'reinforce' else value.detach())
        loss = -(torch.stack(logps) * advantage).sum()
        if method != 'reinforce':
            loss = loss + .5 * (value - returns).square().mean()
    return loss, errors, env['belief'].n_degenerate


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--methods', nargs='+', choices=['reinforce', 'ac', 'nstep3', 'nstep5'], default=['reinforce', 'ac', 'nstep3', 'nstep5'])
    ap.add_argument('--features', nargs='+', choices=['observed', 'gain'], default=['observed', 'gain'])
    ap.add_argument('--confidence', nargs='+', choices=['normal', 'noise', 'oracle'], default=['normal'])
    ap.add_argument('--seeds', nargs='+', type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument('--episodes', type=int, default=20000)
    ap.add_argument('--eval-start', type=int, default=1000)
    ap.add_argument('--graphs', type=int, default=200)
    ap.add_argument('--bootstrap', type=int, default=10000)
    ap.add_argument('--lr', type=float, default=.003)
    args = ap.parse_args()
    if min(args.episodes, args.graphs, args.bootstrap) < 1 or not math.isfinite(args.lr) or args.lr <= 0:
        ap.error('episodes, graphs, bootstrap and lr must be positive and finite')
    if args.eval_start < 0 or any(s < 0 for s in args.seeds):
        ap.error('seed values must be nonnegative')
    for field in ['methods', 'features', 'confidence', 'seeds']:
        if len(set(getattr(args, field))) != len(getattr(args, field)):
            ap.error('duplicate entries in ' + field)
    torch.set_num_threads(1)
    args.out.mkdir(parents=True, exist_ok=False)
    config = vars(args).copy(); config['out'] = str(args.out)
    result = {'config': config, 'provenance': B.provenance(), 'status': 'in_progress',
              'evidence_level': 'smoke' if args.episodes < 20000 or len(args.seeds) < 5 or args.graphs < 200 else 'development',
              'graph_seeds': list(range(args.eval_start, args.eval_start+args.graphs)),
              'conditions': {}, 'degeneracies': {}, 'checkpoints': {}, 'training': {}}
    path = args.out / 'results.json'
    write_json(path, result)
    started = time.monotonic()
    for confidence in args.confidence:
        models = {}
        for variant in args.features:
            for method in args.methods:
                for seed in args.seeds:
                    torch.manual_seed(seed)
                    model = Agent(variant)
                    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
                    rng = random.Random(seed)
                    baseline, errors = 0., []
                    for ep in range(args.episodes):
                        loss, error, _ = rollout(model, rng.randrange(10**9), confidence, variant,
                                                 method, train=True, baseline=baseline,
                                                 temperature=max(.3, 2.*(.9993**ep)))
                        optimizer.zero_grad(); loss.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.)
                        optimizer.step()
                        baseline = .95*baseline - .05*error
                        errors.append(error)
                    name = f'{confidence}_{variant}_{method}_{seed}'
                    checkpoint = args.out / (name + '.pt')
                    torch.save(model.state_dict(), checkpoint)
                    result['checkpoints'][checkpoint.name] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
                    result['training'][name] = {'sink_errors': errors}
                    models[variant, method, seed] = model.eval()
                    write_json(path, result)
                    print('trained', name, flush=True)
        for schedule in ['matched', 'linear_odds_1_to_2']:
            condition = confidence + '/' + schedule
            rows, degeneracies = {'belief greedy': []}, {'belief greedy': []}
            for variant in args.features:
                for method in args.methods:
                    key = variant + '/' + method
                    rows[key] = [[] for _ in args.seeds]
                    degeneracies[key] = [[] for _ in args.seeds]
            with torch.no_grad():
                for index, graph in enumerate(result['graph_seeds']):
                    odds = 1. if schedule == 'matched' else 1. + index/max(1, args.graphs-1)
                    _, error, deg = rollout(None, graph, confidence, 'observed', 'reinforce', odds=odds)
                    rows['belief greedy'].append(error); degeneracies['belief greedy'].append(deg)
                    for (variant, method, seed), model in models.items():
                        _, error, deg = rollout(model, graph, confidence, variant, method, odds=odds)
                        k, s = variant + '/' + method, args.seeds.index(seed)
                        rows[k][s].append(error); degeneracies[k][s].append(deg)
            result['conditions'][condition] = rows
            result['degeneracies'][condition] = degeneracies
            write_json(path, result)
    result['status'] = 'completed'
    result['seconds'] = time.monotonic()-started
    write_json(path, result)
    # Read saved arrays to produce summaries; never hand-edit scientific tables.
    saved = json.loads(path.read_text())
    lines = ['# Proposal extension results', '', 'Evidence level: ' + saved['evidence_level'], '',
             '| condition | policy | mean sink errors | paired delta | 95% CI |',
             '|---|---|---:|---:|---|']
    for condition, rows in saved['conditions'].items():
        for policy, vals in rows.items():
            matrix = vals if isinstance(vals[0], list) else [vals]
            ci = B.paired_bootstrap(matrix, rows['belief greedy'], args.bootstrap)
            lines.append(f"| {condition} | {policy} | {np.mean(vals):.3f} | {ci['mean']:+.3f} | [{ci['low']:+.3f}, {ci['high']:+.3f}] |")
    (args.out/'results.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
