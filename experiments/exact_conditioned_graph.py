#!/usr/bin/env python3
"""Exact planning on confidence-conditioned, final-layer-output small graphs."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch

import numpy as np
from belief import conf_posterior
from exact_small_graph import ExactReview
import spike_active_selection as S


def case(seed):
    rng = random.Random(seed)
    with patch.dict(S.CFG, N=6, L=3, K=5):
        nodes, _, _, sinks, _ = S.build_graph(rng)
        base = [rng.random() < S.P_TYPE[n['type']] for n in nodes]
        confidence = S.make_conf(nodes, base, rng)
    type_prior = [S.P_TYPE[n['type']] for n in nodes]
    return dict(seed=seed, parents=[n['parents'] for n in nodes],
                types=[n['type'] for n in nodes], sinks=sorted(sinks),
                confidence=confidence, type_prior=type_prior,
                conditioned_prior=[conf_posterior(c, p) for c, p in zip(confidence, type_prior)])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    root = Path(__file__).parent
    names = ['exact_conditioned_graph.py', 'exact_small_graph.py', 'belief.py',
             'spike_active_selection.py', 'SMALL_GRAPH_CONDITIONED_PROTOCOL.md']
    manifest = dict(status='in_progress', source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
                    python=sys.version, numpy=np.__version__, n=6, layers=3,
                    seeds=list(range(32000, 32012)), budgets=[1, 2, 3],
                    propagation=.6, catch=.9, evidence='conditional exact development expectations')
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    rows = []
    for seed in manifest['seeds']:
        c = case(seed)
        for profile, key in [('normal-confidence', 'conditioned_prior'), ('type-prior', 'type_prior')]:
            env = ExactReview(c['parents'], c[key], sinks=c['sinks'])
            for budget in manifest['budgets']:
                rows.append(dict(**c, profile=profile, budget=budget, **env.solve(budget)))
            print(f'{seed}/{profile}: complete', flush=True)
    summary = []
    for profile in ['normal-confidence', 'type-prior']:
        for budget in manifest['budgets']:
            cell = [r for r in rows if r['profile'] == profile and r['budget'] == budget]
            summary.append(dict(profile=profile, budget=budget, graphs=len(cell),
                                **{k:float(np.mean([r[k] for r in cell])) for k in
                                   ['initial', 'optimal', 'greedy', 'fixed', 'gap', 'tie_aware_gap', 'adaptivity_gap', 'gap_fraction_initial']},
                                max_gap=max(r['gap'] for r in cell),
                                positive_gaps=sum(r['gap'] > 1e-9 for r in cell)))
    for name, value in [('cases.json', rows), ('summary.json', summary)]:
        (args.out/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    manifest.update(status='completed', cases=len(rows), seconds=time.monotonic()-start,
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.name != 'manifest.json'})
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
