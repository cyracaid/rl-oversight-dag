#!/usr/bin/env python3
"""Post-hoc replay of the two negative frozen-check decisions on graph 32005."""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from belief import ParticleBelief
from calibrate_sampled_planning import first_values
from exact_small_graph import ExactReview
from sampled_planning import world_errors


def replay(belief, action, seed, samples=1024):
    rng=np.random.default_rng(seed)
    worlds=rng.integers(belief.M,size=samples)
    catches=rng.random((samples,belief.N)) < belief.p_catch
    rows=[]
    for trial,world in enumerate(worlds):
        posterior=copy.deepcopy(belief)
        posterior.rng=np.random.default_rng(seed+trial+100000)
        base=belief.B[:,world].copy()
        initial=base.copy()
        coins=belief.C[:,world].copy()
        mask=[True]*belief.N
        a=action
        history=[]
        for step in range(3):
            err=world_errors(base,coins,belief)
            flag=bool(err[a] and catches[trial,a])
            history.append([a,int(flag)])
            if flag:
                base[a]=False
            posterior.observe(a,flag)
            mask[a]=False
            if step<2:
                a=posterior.best_action(mask)
        errors=sum(bool(world_errors(base,coins,belief)[i]) for i,s in enumerate(belief.is_sink) if s)
        rows.append(dict(world=int(world),base_nodes=np.flatnonzero(initial).tolist(),
                         history=history,errors=errors,degeneracies=posterior.n_degenerate))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    frozen=Path('runs/sampled-frozen-check-v1/cases.json')
    original=Path('runs/small-graph-conditioned-v1/cases.json')
    for p in [frozen,original]:
        receipt=json.loads(p.with_name('manifest.json').read_text())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['output_sha256']['cases.json']
    cases={c['profile']:c for c in json.loads(original.read_text()) if c['seed']==32005 and c['budget']==3}
    failures=[r for r in json.loads(frozen.read_text()) if r['graph']==32005 and r['gain_over_exact_greedy'] < -1e-9]
    assert len(failures)==2
    args.out.mkdir(parents=True,exist_ok=False)
    output=[]
    for failure in failures:
        c=cases[failure['profile']]
        prior=c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
        edges={(p,i):.6 for i,ps in enumerate(c['parents']) for p in ps}
        belief=ParticleBelief(c['parents'],range(6),c['sinks'],edges,prior,.9,1024,failure['seed']+50000)
        seed=failure['seed']*100000+1024
        traces={a:replay(belief,a,seed) for a in range(6)}
        for a,rows in traces.items():
            assert float(np.mean([r['errors'] for r in rows]))==failure['detail']['candidate_values'][str(a)]
        chosen=failure['action'];greedy=failure['detail']['greedy']
        selected=traces[chosen];reference=traces[greedy]
        differences=np.array([a['errors']-b['errors'] for a,b in zip(selected,reference)])
        groups={}
        for a,b,d in zip(selected,reference,differences):
            if d==0:
                continue
            key=json.dumps(dict(selected_history=a['history'],greedy_history=b['history']))
            g=groups.setdefault(key,dict(selected_history=a['history'],greedy_history=b['history'],
                                         count=0,net_error_difference=0,base_patterns={}))
            g['count']+=1;g['net_error_difference']+=int(d)
            pattern=str(a['base_nodes'])
            g['base_patterns'][pattern]=g['base_patterns'].get(pattern,0)+1
        # Exact greedy completion under empirical particle-world distribution.
        empirical=ExactReview(c['parents'],prior,sinks=c['sinks'])
        bits=np.concatenate([belief.B,belief.C],axis=0).astype(np.uint32)
        ids=(bits*(1<<np.arange(len(bits),dtype=np.uint32))[:,None]).sum(axis=0).astype(int)
        empirical.weights=np.bincount(ids,minlength=len(empirical.weights))/belief.M
        empirical_values=first_values(empirical,3)
        exact_values={int(a):v for a,v in failure['exact_first_values'].items()}
        record=dict(profile=c['profile'],seed=failure['seed'],chosen=chosen,greedy=greedy,
                    exact_values=exact_values,empirical_exact_greedy_values=empirical_values,
                    exact_difference=exact_values[chosen]-exact_values[greedy],
                    empirical_difference=empirical_values[chosen]-empirical_values[greedy],
                    sampled_difference=float(differences.mean()),
                    paired_standard_error=float(differences.std(ddof=1)/np.sqrt(len(differences))),
                    difference_counts=dict(collections.Counter(map(int,differences))),
                    particle_base_counts=belief.B.sum(axis=1).tolist(),
                    expected_base_counts=(np.array(prior)*1024).tolist(),
                    distinct_sampled_worlds=len({r['world'] for r in selected}),
                    discrepancy_groups=sorted(groups.values(),key=lambda g:-g['count']),traces=traces)
        output.append(record)
        print(json.dumps({k:v for k,v in record.items() if k not in ['traces','discrepancy_groups']},indent=2),flush=True)
    (args.out/'cases.json').write_text(json.dumps(output,indent=2)+'\n')
    root=Path(__file__).parent
    names=['diagnose_graph_32005.py','sampled_planning.py','belief.py','exact_small_graph.py','calibrate_sampled_planning.py']
    manifest=dict(status='completed',evidence='post-hoc failure diagnosis, no tuning',
                  input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [frozen,original]},
                  source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
                  output_sha256={'cases.json':hashlib.sha256((args.out/'cases.json').read_bytes()).hexdigest()})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    main()
