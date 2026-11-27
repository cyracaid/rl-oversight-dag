#!/usr/bin/env python3
"""Full-candidate first-action calibration with paired difference diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from belief import ParticleBelief
from calibrate_sampled_planning import first_values
from exact_small_graph import ExactReview
from sampled_planning import choose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = Path('runs/small-graph-conditioned-v1/cases.json')
    original = json.loads(source.with_name('manifest.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original['output_sha256']['cases.json']
    cases = [c for c in json.loads(source.read_text()) if c['budget']==3 and c['seed']<32004]
    args.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).parent
    names = ['run_sampled_stability.py','sampled_planning.py','belief.py',
             'calibrate_sampled_planning.py','exact_small_graph.py','SAMPLED_STABILITY_PROTOCOL.md']
    manifest = dict(status='in_progress', python=sys.version, numpy=np.__version__,
                    input_sha256={str(source):hashlib.sha256(source.read_bytes()).hexdigest()},
                    source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
                    samples=[16,64,256,1024], seeds=list(range(4)), particles=256,
                    budget=3, candidates=6)
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    rows=[]
    for c in cases:
        prior=c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
        exact=ExactReview(c['parents'],prior,sinks=c['sinks'])
        values=first_values(exact,3)
        exact_greedy=exact.solve(3)['greedy_first']
        for seed in manifest['seeds']:
            edges={(p,i):.6 for i,ps in enumerate(c['parents']) for p in ps}
            belief=ParticleBelief(c['parents'],range(6),c['sinks'],edges,prior,.9,256,seed+50000)
            for samples in manifest['samples']:
                start=time.perf_counter()
                action,detail=choose(belief,[True]*6,3,samples,6,
                                     seed*100000+samples,paired_diagnostics=True)
                greedy=detail['greedy']
                paired_errors=[d['mean']-(values[a]-values[greedy])
                               for a,d in detail['paired_vs_greedy'].items() if a!=greedy]
                rows.append(dict(graph=c['seed'],profile=c['profile'],seed=seed,samples=samples,
                                 action=action,seconds=time.perf_counter()-start,detail=detail,
                                 exact_first_values=values,exact_greedy=exact_greedy,
                                 paired_squared_errors=[e*e for e in paired_errors],
                                 selected_excess=values[action]-min(values.values()),
                                 gain_over_exact_greedy=values[exact_greedy]-values[action],
                                 gain_over_particle_greedy=values[greedy]-values[action]))
        print(c['seed'],c['profile'],'complete',flush=True)
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        for samples in manifest['samples']:
            cell=[r for r in rows if r['profile']==profile and r['samples']==samples]
            frequencies={str(graph):{str(a):sum(r['action']==a for r in cell if r['graph']==graph)
                                    for a in range(6)} for graph in sorted({r['graph'] for r in cell})}
            summary.append(dict(profile=profile,samples=samples,decisions=len(cell),
                                paired_rmse=float(np.sqrt(np.mean([e for r in cell for e in r['paired_squared_errors']]))),
                                **{k:float(np.mean([r[k] for r in cell])) for k in
                                   ['selected_excess','gain_over_exact_greedy','gain_over_particle_greedy','seconds']},
                                worse_than_exact_greedy=sum(r['gain_over_exact_greedy'] < -1e-9 for r in cell),
                                action_frequencies=frequencies))
    for name,data in [('cases.json',rows),('summary.json',summary)]:
        (args.out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    manifest.update(status='completed',decisions=len(rows),
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in args.out.iterdir() if p.name!='manifest.json'})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in s.items() if k!='action_frequencies'} for s in summary],indent=2))


if __name__=='__main__':
    main()
