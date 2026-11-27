#!/usr/bin/env python3
"""Fixed paired three-policy evaluation on frozen small development graphs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from belief import ParticleBelief
from sampled_planning import choose, world_errors
from validate_selection_guard import accept


def continuation(belief, available, remaining, action, seed, samples=1024):
    rng=np.random.default_rng(seed)
    worlds=rng.integers(belief.M,size=samples)
    catches=rng.random((samples,belief.N)) < belief.p_catch
    errors=[]
    for trial,world in enumerate(worlds):
        posterior=copy.deepcopy(belief)
        posterior.rng=np.random.default_rng(seed+trial+100000)
        base=belief.B[:,world].copy();coins=belief.C[:,world].copy()
        mask=list(available);a=action
        for step in range(remaining):
            flag=bool(world_errors(base,coins,belief)[a] and catches[trial,a])
            if flag:
                base[a]=False
            posterior.observe(a,flag);mask[a]=False
            if step+1<remaining:
                a=posterior.best_action(mask)
        err=world_errors(base,coins,belief)
        errors.append(sum(bool(err[i]) for i,s in enumerate(belief.is_sink) if s))
    return np.asarray(errors)


def episode(case, seed, method):
    prior=case['conditioned_prior'] if case['profile']=='normal-confidence' else case['type_prior']
    parents=case['parents'];n=len(parents)
    edges={(p,i):.6 for i,ps in enumerate(parents) for p in ps}
    belief=ParticleBelief(parents,range(n),case['sinks'],edges,prior,.9,1024,seed+50000)
    rng=np.random.default_rng(seed+90000+case['seed']*100)
    base=rng.random(n)<prior;coins=rng.random(len(edges))<.6;catches=rng.random(n)<.9
    available=[True]*n
    initial=int(sum(world_errors(base,coins,belief)[case['sinks']]))
    tick=time.perf_counter();history=[];search_reviews=validation_reviews=0
    for step in range(3):
        remaining=3-step;detail=None;validation=None
        greedy=belief.best_action(available);a=greedy
        if method!='greedy':
            a,detail=choose(belief,available,remaining,1024,n,seed*100000+1024+step*1000000)
            search_reviews+=detail['simulated_reviews']
        proposed=a
        if method=='guarded' and a!=greedy:
            validation_seed=7000000+seed*100000+step*1000000
            d=continuation(belief,available,remaining,a,validation_seed)-continuation(belief,available,remaining,greedy,validation_seed)
            passed=accept(d)
            validation=dict(passed=passed,mean=float(d.mean()),
                            standard_error=float(d.std(ddof=1)/np.sqrt(len(d))),
                            discordant=int(np.count_nonzero(d)))
            validation_reviews+=2*1024*remaining
            if not passed:
                a=greedy
        err=world_errors(base,coins,belief)
        flag=bool(err[a] and catches[a])
        if flag:
            base[a]=False
        belief.observe(a,flag);available[a]=False
        history.append(dict(action=a,flag=flag,greedy=greedy,proposed=proposed,
                            search=detail,validation=validation))
    return dict(method=method,initial=initial,
                errors=int(sum(world_errors(base,coins,belief)[case['sinks']])),
                seconds=time.perf_counter()-tick,history=history,
                search_reviews=search_reviews,validation_reviews=validation_reviews,
                degeneracies=belief.n_degenerate)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    source=Path('runs/small-graph-conditioned-v1/cases.json')
    original=json.loads(source.with_name('manifest.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original['output_sha256']['cases.json']
    cases=[c for c in json.loads(source.read_text()) if c['budget']==3]
    args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent
    names=['run_full_episode_guard.py','sampled_planning.py','belief.py',
           'validate_selection_guard.py','FULL_EPISODE_GUARD_PROTOCOL.md']
    manifest=dict(status='in_progress',input_sha256={str(source):hashlib.sha256(source.read_bytes()).hexdigest()},
                  source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
                  seeds=list(range(4)),particles=1024,samples=1024,budget=3)
    def save_manifest():
        (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save_manifest();rows=[]
    for c in cases:
        for seed in manifest['seeds']:
            results={method:episode(c,seed,method) for method in ['greedy','rollout','guarded']}
            assert len({r['initial'] for r in results.values()})==1
            rows.append(dict(graph=c['seed'],profile=c['profile'],seed=seed,results=results))
        (args.out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(c['seed'],c['profile'],'complete',flush=True)
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        cell=[r for r in rows if r['profile']==profile]
        for method in ['greedy','rollout','guarded']:
            deltas=[r['results'][method]['errors']-r['results']['greedy']['errors'] for r in cell]
            summary.append(dict(profile=profile,method=method,episodes=len(cell),
                                **{k:float(np.mean([r['results'][method][k] for r in cell])) for k in
                                   ['errors','seconds','search_reviews','validation_reviews','degeneracies']},
                                delta=float(np.mean(deltas)),wins=sum(d<0 for d in deltas),
                                ties=sum(d==0 for d in deltas),losses=sum(d>0 for d in deltas)))
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    manifest.update(status='completed',paired_triples=len(rows),
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.name!='manifest.json'})
    save_manifest();print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
