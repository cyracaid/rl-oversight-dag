#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from belief import ParticleBelief
from sampled_planning import choose, world_errors


def episode(parents, sinks, prior, budget, seed, samples, candidates=3):
    n = len(parents)
    edges = {(p, i): .6 for i, ps in enumerate(parents) for p in ps}
    posterior = ParticleBelief(parents, range(n), sinks, edges, prior, .9, 256, seed+50000)
    rng = np.random.default_rng(seed+90000)
    base = rng.random(n) < prior
    coins = rng.random(len(edges)) < .6
    catches = rng.random(n) < .9
    mask = [True]*n
    initial = sum(world_errors(base, coins, posterior)[sinks])
    start = time.perf_counter()
    choices, search, diagnostics = [], 0, []
    for step in range(budget):
        if samples:
            a, detail = choose(posterior, mask, budget-step, samples, candidates, seed*100+step)
            search += detail['simulated_reviews']
            if step == 0:
                # Diagnostic only: fresh draws, no action reselection.
                _, check = choose(posterior, mask, budget-step, 64, candidates,
                                  seed*100+step+2000000)
                diagnostics.append(dict(selected=a, search=detail,
                                        independent=check,
                                        independent_selected_minus_greedy=(
                                            check['candidate_values'][a]-
                                            check['candidate_values'][check['greedy']])))
        else:
            a = posterior.best_action(mask)
        err = world_errors(base, coins, posterior)
        flag = bool(err[a] and catches[a])
        if flag:
            base[a] = False
        posterior.observe(a, flag)
        mask[a] = False
        choices.append(a)
    return dict(errors=int(sum(world_errors(base, coins, posterior)[sinks])),
                initial=int(initial), actions=choices, seconds=time.perf_counter()-start,
                simulated_reviews=search, degeneracies=posterior.n_degenerate,
                diagnostics=diagnostics)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    source = Path('runs/small-graph-conditioned-v1/cases.json')
    cases = [c for c in json.loads(source.read_text()) if c['budget']==3 and c['seed']<32004]
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = dict(status='in_progress', input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                   [Path(__file__),Path(__file__).with_name('sampled_planning.py'),
                                    Path(__file__).with_name('belief.py'),Path(__file__).with_name('SAMPLED_PLANNING_PROTOCOL.md')]})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows=[]
    for c in cases:
        prior = c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
        for seed in range(8):
            reference=episode(c['parents'],c['sinks'],prior,3,seed,0)
            for samples in [4,16]:
                result=episode(c['parents'],c['sinks'],prior,3,seed,samples)
                rows.append(dict(graph=c['seed'],profile=c['profile'],seed=seed,samples=samples,
                                 exact_optimal=c['optimal'],exact_greedy=c['greedy'],
                                 reference=reference,delta=result['errors']-reference['errors'],**result))
        print(c['seed'],c['profile'],'complete',flush=True)
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        for samples in [4,16]:
            cell=[r for r in rows if r['profile']==profile and r['samples']==samples]
            summary.append(dict(profile=profile,samples=samples,episodes=len(cell),
                                **{k:float(np.mean([r[k] for r in cell])) for k in ['errors','delta','seconds','degeneracies']},
                                greedy_errors=float(np.mean([r['reference']['errors'] for r in cell])),
                                greedy_seconds=float(np.mean([r['reference']['seconds'] for r in cell]))))
    for name,value in [('cases.json',rows),('summary.json',summary)]:
        (args.out/name).write_text(json.dumps(value,indent=2)+'\n')
    manifest.update(status='completed',cases=len(rows),output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.name!='manifest.json'})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
