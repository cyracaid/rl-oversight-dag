#!/usr/bin/env python3
"""Compare first-action estimates with exact-belief greedy continuation values."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from exact_small_graph import ExactReview


def first_values(env, budget):
    def value(weights, reviewed, cleared, left):
        if not left:
            return float(weights @ env.state(cleared)[1])
        available = [a for a in range(env.n) if a not in reviewed]
        err, cost = env.state(cleared)
        current = float(weights @ cost)
        gains = {a:current-sum(float(w @ env.state(c)[1])
                              for w, c in env.branches(weights, cleared, a)) for a in available}
        tolerance = 1e-12*float(weights.sum())
        maximum = max(gains.values())
        if maximum <= tolerance:
            action = max(available, key=lambda a:(float(weights @ err[:, a]), -a))
        else:
            action = next(a for a in available if maximum-gains[a] <= tolerance)
        return sum(value(w, reviewed+[action], c, left-1)
                   for w, c in env.branches(weights, cleared, action) if w.sum() > 0)
    return {a:sum(value(w, [a], c, budget-1)
                  for w, c in env.branches(env.weights, 0, a) if w.sum() > 0)
            for a in range(env.n)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    pilot = Path('runs/small-graph-sampled-v1/cases.json')
    frozen = Path('runs/small-graph-conditioned-v1/cases.json')
    cases = {(c['seed'], c['profile']):c for c in json.loads(frozen.read_text()) if c['budget']==3}
    exact = {}
    rows = []
    for row in json.loads(pilot.read_text()):
        key = row['graph'], row['profile']
        if key not in exact:
            c = cases[key]
            prior = c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
            exact[key] = first_values(ExactReview(c['parents'], prior, sinks=c['sinks']), 3)
        values = exact[key]
        d = row['diagnostics'][0]
        errors = [estimate-values[int(a)] for a, estimate in d['search']['candidate_values'].items()]
        check_errors = [estimate-values[int(a)] for a, estimate in d['independent']['candidate_values'].items()]
        rows.append(dict(graph=key[0], profile=key[1], samples=row['samples'], seed=row['seed'],
                         exact_first_values=values, squared_errors=[e*e for e in errors],
                         independent_squared_errors=[e*e for e in check_errors],
                         selected_excess=values[d['selected']]-min(values.values()),
                         shortlist_excess=min(values[int(a)] for a in d['search']['candidate_values'])-min(values.values())))
    summary = []
    for profile in ['normal-confidence', 'type-prior']:
        for samples in [4,16]:
            cell = [r for r in rows if r['profile']==profile and r['samples']==samples]
            summary.append(dict(profile=profile, samples=samples,
                                rmse=float(np.sqrt(np.mean([e for r in cell for e in r['squared_errors']]))),
                                independent_rmse=float(np.sqrt(np.mean([e for r in cell for e in r['independent_squared_errors']]))),
                                selected_excess=float(np.mean([r['selected_excess'] for r in cell])),
                                shortlist_excess=float(np.mean([r['shortlist_excess'] for r in cell]))))
    args.out.mkdir(parents=True, exist_ok=False)
    for name, data in [('cases.json',rows),('summary.json',summary)]:
        (args.out/name).write_text(json.dumps(data,indent=2)+'\n')
    root = Path(__file__).parent
    manifest = dict(status='completed', caveat='Exact-belief continuation differs from simulated particle-greedy continuation; RMSE includes posterior and policy approximation.',
                    input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pilot,frozen]},
                    source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['calibrate_sampled_planning.py','exact_small_graph.py']},
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir()})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
