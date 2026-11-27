#!/usr/bin/env python3
"""Post-hoc development evaluation of independent paired validation guard."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from belief import ParticleBelief
from diagnose_graph_32005 import replay


def accept(differences):
    differences=np.asarray(differences,dtype=float)
    if differences.size<2:
        return False
    se=float(differences.std(ddof=1)/np.sqrt(differences.size))
    return bool(np.count_nonzero(differences)>=32 and differences.mean()+2*se<0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    paths=[Path('runs/particle-rollout-grid-v1/cases.json'),
           Path('runs/sampled-frozen-check-v1/cases.json'),
           Path('runs/small-graph-conditioned-v1/cases.json')]
    for p in paths:
        receipt=json.loads(p.with_name('manifest.json').read_text())
        if hashlib.sha256(p.read_bytes()).hexdigest()!=receipt['output_sha256']['cases.json']:
            raise ValueError('input hash mismatch')
    rows=[r for p in paths[:2] for r in json.loads(p.read_text())
          if r['particles']==r['samples']==1024]
    assert len(rows)==96
    cases={(c['seed'],c['profile']):c for c in json.loads(paths[2].read_text()) if c['budget']==3}
    args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent
    names=['validate_selection_guard.py','diagnose_graph_32005.py','sampled_planning.py',
           'belief.py','GUARDED_SELECTION_PROTOCOL.md','calibrate_sampled_planning.py','exact_small_graph.py']
    manifest=dict(status='in_progress',input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
                  samples=1024,minimum_discordant=32,standard_error_multiplier=2)
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    output=[]
    for row in rows:
        selected=row['action'];greedy=row['detail']['greedy']
        tick=time.perf_counter();check=None;passed=False
        if selected!=greedy:
            c=cases[row['graph'],row['profile']]
            prior=c['conditioned_prior'] if row['profile']=='normal-confidence' else c['type_prior']
            edges={(p,i):.6 for i,ps in enumerate(c['parents']) for p in ps}
            belief=ParticleBelief(c['parents'],range(6),c['sinks'],edges,prior,.9,1024,row['seed']+50000)
            seed=7000000+row['seed']*100000
            a=replay(belief,selected,seed);b=replay(belief,greedy,seed)
            d=np.array([x['errors']-y['errors'] for x,y in zip(a,b)])
            passed=accept(d)
            check=dict(mean=float(d.mean()),standard_error=float(d.std(ddof=1)/np.sqrt(len(d))),
                       discordant=int(np.count_nonzero(d)),
                       difference_counts={str(int(v)):int(np.sum(d==v)) for v in np.unique(d)})
        guarded=selected if passed else greedy
        values=row['exact_first_values'];exact_greedy=row['exact_greedy']
        raw_gain=values[str(greedy)]-values[str(selected)]
        output.append(dict(graph=row['graph'],profile=row['profile'],seed=row['seed'],
                           selected=selected,particle_greedy=greedy,guarded=guarded,passed=passed,
                           validation=check,validation_seconds=time.perf_counter()-tick,
                           raw_gain_over_particle_greedy=raw_gain,
                           guarded_gain_over_particle_greedy=values[str(greedy)]-values[str(guarded)],
                           raw_gain_over_exact_greedy=values[str(exact_greedy)]-values[str(selected)],
                           guarded_gain_over_exact_greedy=values[str(exact_greedy)]-values[str(guarded)],
                           harmful_prevented=bool(raw_gain < -1e-9 and not passed),
                           harmful_retained=bool(raw_gain < -1e-9 and passed),
                           beneficial_lost=bool(raw_gain > 1e-9 and not passed),
                           beneficial_retained=bool(raw_gain > 1e-9 and passed)))
        if row['seed']==3:
            print(row['graph'],row['profile'],'complete',flush=True)
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        cell=[r for r in output if r['profile']==profile]
        summary.append(dict(profile=profile,decisions=len(cell),
                            **{k:sum(r[k] for r in cell) for k in ['passed','harmful_prevented','harmful_retained','beneficial_lost','beneficial_retained']},
                            **{k:float(np.mean([r[k] for r in cell])) for k in ['raw_gain_over_particle_greedy','guarded_gain_over_particle_greedy','raw_gain_over_exact_greedy','guarded_gain_over_exact_greedy','validation_seconds']}))
    for name,data in [('cases.json',output),('summary.json',summary)]:
        (args.out/name).write_text(json.dumps(data,indent=2)+'\n')
    manifest.update(status='completed',decisions=len(output),output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.name!='manifest.json'})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
