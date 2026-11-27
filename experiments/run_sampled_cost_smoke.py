#!/usr/bin/env python3
"""One development graph: sampled planning execution cost, not efficacy evidence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import time

import proposal_gaps as P
from sampled_planning import choose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    env = P.environment(1000, 'normal', 1.)
    rows = []
    for method in ['greedy', 'sampled']:
        belief = copy.deepcopy(env['belief'])
        base = list(env['base'])
        err = P.SP.compute_err(base, env['nodes'], env['topo'], env['coins'])
        mask = [True]*len(base)
        actions, decisions, reviews = [], [], 0
        start = time.perf_counter()
        for step in range(P.M.R):
            tick = time.perf_counter()
            if method == 'sampled':
                action, detail = choose(belief, mask, P.M.R-step, 2, 2, 3000000+step)
                reviews += detail['simulated_reviews']
            else:
                action = belief.best_action(mask)
            decisions.append(time.perf_counter()-tick)
            flag, err = P.SP.review_step(action, base, err, env['nodes'], env['topo'],
                                         env['coins'], random.Random(0), env['catch_uniforms'])
            belief.observe(action, flag)
            mask[action] = False
            actions.append(action)
        rows.append(dict(method=method, errors=sum(bool(err[i]) for i in env['sinks']),
                         seconds=time.perf_counter()-start, decision_seconds=decisions,
                         actions=actions, simulated_reviews=reviews,
                         degeneracies=belief.n_degenerate))
        print(json.dumps(rows[-1]), flush=True)
    (args.out/'cases.json').write_text(json.dumps(rows, indent=2)+'\n')
    root = Path(__file__).parent
    sources = ['run_sampled_cost_smoke.py', 'sampled_planning.py', 'belief.py',
               'proposal_gaps.py', 'spike_active_selection.py', 'rl_gnn_multiseed.py',
               'rl_boundary.py', 'SAMPLED_PLANNING_PROTOCOL.md']
    manifest = dict(status='completed', seed=1000, confidence='normal', odds=1.,
                    n=len(env['base']), budget=P.M.R, particles=env['belief'].M,
                    samples=2, candidates=2, evidence='single development execution-cost smoke',
                    source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                                   for name in sources},
                    output_sha256={'cases.json':hashlib.sha256((args.out/'cases.json').read_bytes()).hexdigest()})
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
