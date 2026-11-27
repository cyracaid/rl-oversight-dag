#!/usr/bin/env python3
"""Fixed half-confidence prior diagnostic; no training or coefficient selection."""
import argparse
import gzip
import json
from pathlib import Path
import random
import time
import numpy as np
import torch
import proposal_gaps as P
from compare_type_priors import control_rollout
from diagnose_proposal_gaps import digest, replay


def make_belief(env, graph, alpha=.5):
    if not 0 <= alpha <= 1:
        raise ValueError('alpha outside [0,1]')
    parents = [n['parents'] for n in env['nodes']]
    p = np.array([P.SP.P_TYPE[n['type']] for n in env['nodes']])
    q = np.array([P.conf_posterior(min(1-1e-6,max(1e-6,c)),t) for c,t in zip(env['conf'],p)])
    return P.ParticleBelief(parents,env['topo'],env['sinks'],
        {(parent,i):P.SP.CFG['p_prop'] for i,ps in enumerate(parents) for parent in ps},
        (1-alpha)*p+alpha*q,P.SP.CFG['p_catch'],P.SP.CFG['n_particles'],graph+10000)


def episode(graph, confidence, odds):
    env=P.environment(graph,confidence,odds)
    visible={k:env[k] for k in ['nodes','topo','sinks','conf']}
    b=make_belief(visible,graph)
    base=list(env['base']);err=P.SP.compute_err(base,env['nodes'],env['topo'],env['coins'])
    initial=sum(bool(err[i]) for i in env['sinks']);mask=[True]*P.M.N;trace=[]
    started=time.perf_counter()
    for step in range(P.M.R):
        a=b.best_action(mask);before=sum(bool(err[i]) for i in env['sinks']);deg=b.n_degenerate
        gain=b.gain(a);pe=float(b.p_err()[a])
        flag,err=P.SP.review_step(a,base,err,env['nodes'],env['topo'],env['coins'],random.Random(0),env['catch_uniforms'])
        b.observe(a,flag);mask[a]=False
        after=sum(bool(err[i]) for i in env['sinks'])
        trace.append(dict(step=step,action=a,node_type=int(env['nodes'][a]['type']),
            flagged=bool(flag),chosen_gain=gain,p_error=pe,degenerate=b.n_degenerate>deg,
            sink_errors_before=before,sink_errors_after=after,realized_sink_reduction=before-after))
    return dict(initial_errors=initial,errors=after,degeneracies=b.n_degenerate,
        seconds=time.perf_counter()-started,flags=sum(t['flagged'] for t in trace),
        type_counts=[sum(t['node_type']==i for t in trace) for i in range(P.M.K)]),trace


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();torch.set_num_threads(1)
    original=Path('runs/proposal-gaps-full-v1');controls=Path('runs/proposal-gaps-type-priors-v1')
    data=json.loads((original/'results.json').read_text());receipt=json.loads((controls/'manifest.json').read_text())
    assert receipt['status']=='completed' and digest(original/'results.json')==receipt['results_sha256']
    assert data['graph_seeds']==list(range(1000,1200))
    for n,h in data['provenance']['source_sha256'].items():
        assert digest(Path(__file__).parent/n)==h,('source',n)
    for n,h in receipt['output_sha256'].items(): assert digest(controls/n)==h,n
    for n,h in receipt['checkpoint_sha256'].items(): assert digest(original/n)==h,n
    references=json.loads((controls/'episodes.json').read_text())
    lookup={(r['condition'],r['graph'],r['policy'],r['seed']):r for r in references}
    args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent
    names=['confidence_shrinkage.py','compare_type_priors.py','diagnose_proposal_gaps.py',
           'belief.py','proposal_gaps.py','CONFIDENCE_SHRINKAGE_PROTOCOL.md','test_confidence_shrinkage.py']
    manifest=dict(status='in_progress',alpha=.5,graphs=list(range(1000,1200)),
        input_sha256={str(p):digest(p) for p in [original/'results.json',controls/'episodes.json',controls/'manifest.json']},
        source_sha256={n:digest(root/n) for n in names},reference_replay_verified=False)
    rows=[];summaries=[]
    def save():
        P.write_json(args.out/'episodes.json',rows);P.write_json(args.out/'summary.json',summaries)
        manifest['episodes']=len(rows)
        manifest['output_sha256']={p.name:digest(p) for p in args.out.iterdir() if p.name!='manifest.json'}
        P.write_json(args.out/'manifest.json',manifest)
    save()
    try:
        with torch.no_grad(),gzip.open(args.out/'steps.jsonl.gz','wt') as stream:
            for confidence in ['normal','noise','oracle']:
                for schedule in ['matched','linear_odds_1_to_2']:
                    condition=confidence+'/'+schedule
                    for index,graph in enumerate(data['graph_seeds']):
                        odds=1. if schedule=='matched' else 1.+index/199
                        nominal,_=replay(None,graph,confidence,'observed',odds)
                        typ,_=control_rollout(graph,confidence,odds,'type belief greedy')
                        for policy,outcome in [('belief greedy',nominal),('type belief greedy',typ)]:
                            ref=lookup[condition,graph,policy,None]
                            assert all(outcome[k]==ref[k] for k in ['errors','degeneracies','initial_errors']), (condition,graph,policy)
                        result,trace=episode(graph,confidence,odds)
                        assert result['initial_errors']==nominal['initial_errors']
                        meta=dict(condition=condition,graph=graph,odds=odds)
                        rows.append(dict(meta,**result))
                        for t in trace: stream.write(json.dumps(dict(meta,**t),allow_nan=False)+'\n')
                    cell=[r for r in rows if r['condition']==condition]
                    summary=dict(condition=condition,episodes=len(cell),
                        **{k:float(np.mean([r[k] for r in cell])) for k in ['errors','seconds','degeneracies']},
                        type_fractions=[sum(r['type_counts'][i] for r in cell)/(200*P.M.R) for i in range(P.M.K)],
                        comparisons=[])
                    for policy in ['belief greedy','type belief greedy','observed/nstep3','gain/nstep3']:
                        seeds=[None] if 'greedy' in policy else data['config']['seeds']
                        for seed in seeds:
                            deltas=[r['errors']-lookup[condition,r['graph'],policy,seed]['errors'] for r in cell]
                            summary['comparisons'].append(dict(policy=policy,seed=seed,delta=float(np.mean(deltas)),
                                wins=sum(d<0 for d in deltas),ties=sum(d==0 for d in deltas),losses=sum(d>0 for d in deltas)))
                    summaries.append(summary);stream.flush();save();print(condition,'verified and complete',flush=True)
        assert len(rows)==1200
        manifest.update(status='completed',reference_replay_verified=True,steps=1200*P.M.R)
        save();print(json.dumps(summaries,indent=2),flush=True)
    except Exception as error:
        manifest.update(status='failed',error=repr(error));save();raise


if __name__=='__main__':
    main()
