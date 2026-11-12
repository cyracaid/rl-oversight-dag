"""Independent graph episodes and paired comparison with per-node CRN."""
import argparse
import csv
import math
import statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dag_role3 import generate_graph, sample_episode
from dag_role3.policies import run_public_policy

POLICIES = ('none','random','confidence','hub','structural')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--families', nargs='+', choices=['spike','modular','ba','er','real'],
                    default=['spike','modular','ba','er','real'])
    ap.add_argument('--seeds', type=int, default=10,
                    help='Independent graph environments, NOT number of review actions')
    ap.add_argument('--out', type=Path, default=Path('outputs'))
    args = ap.parse_args()
    if args.seeds <= 0:
        ap.error('--seeds must be positive')
    args.out.mkdir(exist_ok=True, parents=True)
    data = []
    for family in args.families:
        for j in range(args.seeds):
            seed = 1000+j  # held-out graphs; same environment for all policies
            graph = generate_graph(family, seed=seed)
            snapshot = sample_episode(graph, seed=20000+seed)
            budget = 16 if family=='spike' else 8 if family=='real' else 50
            for policy in POLICIES:
                errors, order = run_public_policy(graph, snapshot, policy, budget)
                data.append({'family':family,'graph_seed':seed,'episode_seed':20000+seed,
                             'n':graph.n,'edges':graph.edge_count,'budget':budget,
                             'policy':policy,'sink_errors':errors})
        print('Completed:', family, args.seeds, 'independent environments')
    csv_path = args.out / 'benchmark_role3.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    summary = []
    print('\nMean sink errors (lower is better; these are freshly simulated, NOT published):')
    for family in args.families:
        print('\n', family)
        for policy in POLICIES:
            xs = [x['sink_errors'] for x in data if x['family']==family and x['policy']==policy]
            mean = statistics.mean(xs)
            se = statistics.stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else float('nan')
            ci95 = (1.96*se) if len(xs)>1 else float('nan')
            summary.append({'family':family, 'policy':policy,'mean_sink_errors':mean,
                            'n_episodes':len(xs),'ci95_normal_approx':ci95})
            print(f'  {policy:12s} {mean:7.3f}  (approx. ±{ci95:.3f})')
    with open(args.out/'benchmark_summary.csv','w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f, fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    fig, axes = plt.subplots(1,len(args.families),figsize=(4.2*len(args.families), 4.8), squeeze=False)
    for ax, fam in zip(axes[0], args.families):
        x = [z for z in summary if z['family']==fam]
        ax.bar([z['policy'] for z in x], [z['mean_sink_errors'] for z in x])
        ax.set_title(f'{fam} (independent episodes: {args.seeds})')
        ax.set_ylabel('Mean final sink errors')
        ax.tick_params(axis='x',rotation=55)
    fig.tight_layout()
    fig.savefig(args.out/'benchmark_summary.png', dpi=150)
    plt.close(fig)
    print('\nSaved:',csv_path,args.out/'benchmark_summary.csv',args.out/'benchmark_summary.png')


if __name__=='__main__':
    main()
