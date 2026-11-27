#!/usr/bin/env python3
"""Development sensitivity grid: particle posterior size by rollout count."""
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--frozen-check',action='store_true',
                        help='Fixed 1024/1024 on remaining development graphs 32004..32011')
    args=parser.parse_args()
    source=Path('runs/small-graph-conditioned-v1/cases.json')
    receipt=json.loads(source.with_name('manifest.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=receipt['output_sha256']['cases.json']:
        raise ValueError('frozen input hash mismatch')
    cases=[c for c in json.loads(source.read_text()) if c['budget']==3 and
           (32004<=c['seed']<=32011 if args.frozen_check else c['seed']<32004)]
    args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent
    names=['run_particle_rollout_grid.py','sampled_planning.py','belief.py',
           'calibrate_sampled_planning.py','exact_small_graph.py','PARTICLE_ROLLOUT_GRID_PROTOCOL.md']
    if args.frozen_check:
        names.append('SAMPLED_FROZEN_CHECK_PROTOCOL.md')
    manifest=dict(status='in_progress',python=sys.version,numpy=np.__version__,
                  input_sha256={str(source):hashlib.sha256(source.read_bytes()).hexdigest()},
                  source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
                  particles=[1024] if args.frozen_check else [256,1024,4096],
                  samples=[1024] if args.frozen_check else [64,256,1024],seeds=list(range(4)),
                  mode='frozen-development-check' if args.frozen_check else 'development-grid',
                  graph_seeds=sorted({c['seed'] for c in cases}),
                  budget=3,candidates=6)
    def save_manifest():
        (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save_manifest()
    rows=[]
    for c in cases:
        prior=c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
        exact=ExactReview(c['parents'],prior,sinks=c['sinks'])
        values=first_values(exact,3)
        exact_greedy=exact.solve(3)['greedy_first']
        edges={(p,i):.6 for i,ps in enumerate(c['parents']) for p in ps}
        for particles in manifest['particles']:
            for seed in manifest['seeds']:
                belief=ParticleBelief(c['parents'],range(6),c['sinks'],edges,prior,.9,particles,seed+50000)
                for samples in manifest['samples']:
                    tick=time.perf_counter()
                    action,detail=choose(belief,[True]*6,3,samples,6,
                                         seed*100000+samples,paired_diagnostics=True)
                    elapsed=time.perf_counter()-tick
                    greedy=detail['greedy']
                    residuals=[d['mean']-(values[a]-values[greedy])
                               for a,d in detail['paired_vs_greedy'].items() if a!=greedy]
                    rows.append(dict(graph=c['seed'],profile=c['profile'],particles=particles,
                                     samples=samples,seed=seed,action=action,detail=detail,seconds=elapsed,
                                     exact_first_values=values,exact_greedy=exact_greedy,
                                     paired_squared_errors=[e*e for e in residuals],
                                     selected_excess=values[action]-min(values.values()),
                                     gain_over_exact_greedy=values[exact_greedy]-values[action],
                                     gain_over_particle_greedy=values[greedy]-values[action]))
            print(c['seed'],c['profile'],'particles',particles,'complete',flush=True)
        (args.out/'cases.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        for particles in manifest['particles']:
            for samples in manifest['samples']:
                cell=[r for r in rows if (r['profile'],r['particles'],r['samples'])==(profile,particles,samples)]
                summary.append(dict(profile=profile,particles=particles,samples=samples,decisions=len(cell),
                                    paired_rmse=float(np.sqrt(np.mean([e for r in cell for e in r['paired_squared_errors']]))),
                                    **{k:float(np.mean([r[k] for r in cell])) for k in
                                       ['selected_excess','gain_over_exact_greedy','gain_over_particle_greedy','seconds']},
                                    worse_than_exact_greedy=sum(r['gain_over_exact_greedy'] < -1e-9 for r in cell),
                                    optimal_choices=sum(r['selected_excess'] < 1e-9 for r in cell)))
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    manifest.update(status='completed',decisions=len(rows),
                    output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in args.out.iterdir() if p.name!='manifest.json'})
    save_manifest()
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
