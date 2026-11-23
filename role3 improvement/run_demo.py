"""Single interactive-free walkthrough of one oversight episode."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx

from dag_role3 import generate_graph, OversightEnv
from dag_role3.policies import choose
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', choices=['spike','modular','ba','er','real'], default='real')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--policy', choices=['random', 'confidence','structural','hub','marginal'], default='structural')
    ap.add_argument('--budget', type=int, default=None)
    ap.add_argument('--out', type=Path, default=Path('outputs'))
    ap.add_argument("--particles", type=int, default=0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    graph = generate_graph(args.family, seed=args.seed)
    env = OversightEnv.from_seed(graph, args.seed+10_000, budget=args.budget, particles=args.particles)
    obs = env.observation()
    rng = random.Random(args.seed+33)
    done = env.done
    while not done:
        a = choose(obs, args.policy, rng)
        obs, _, done, _ = env.step(a)
    audit = env.final_audit()
    print(f'Family={graph.family}; nodes={graph.n}; edges={graph.edge_count}; sinks={len(graph.sinks)}')
    print(f'Policy={args.policy}; budget={env.budget}; catch probability={env.p_catch}')
    print(f'Sink errors before={audit["initial_sink_errors"]}; after={audit["final_sink_errors"]}')
    path = args.out / f'demo_{args.family}_{args.policy}.csv'
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['step','node','node_name','flagged',
                                               'sink_errors_before','sink_errors_after'])
        writer.writeheader()
        writer.writerows(audit['trace'])
    print('Review trace:', path)
    print('Particle fallback:', audit['particle_fallback'])
    if graph.n <= 80:
        selected = {r['node'] for r in audit['trace']}
        fig, ax = plt.subplots(figsize=(21, 8) if graph.family == 'real' else (10, 8))
        if graph.family == 'real':
            from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
            # 4 clear columns of dependency nodes; labels never overlap shapes.
            grouped = {layer:[i for i in range(graph.n) if graph.layers[i]==layer]
                       for layer in sorted(set(graph.layers))}
            pos = {}
            for layer, ids in grouped.items():
                for idx, node in enumerate(ids):
                    pos[node] = (layer*3.5, (len(ids)-1)/2-idx)
            for v, ps in enumerate(graph.parents):
                for u in ps:
                    sx,sy=pos[u];tx,ty=pos[v]
                    ax.add_patch(FancyArrowPatch((sx+1.05,sy),(tx-1.05,ty),
                                arrowstyle='-|>', mutation_scale=10, lw=0.8,
                                color='0.5', alpha=0.50, zorder=1))
            for i, (x,y) in pos.items():
                face = '#F7C792' if i in selected else '#D9E6F3'
                ax.add_patch(FancyBboxPatch((x-1.02,y-.25),2.04,.5,
                                           boxstyle='round,pad=0.04,rounding_size=0.11',
                                           facecolor=face,edgecolor='#76869A',lw=.8,zorder=2))
                ax.text(x,y,graph.names[i],ha='center',va='center',fontsize=8,zorder=3)
            ax.set_xlim(-1.3, max(graph.layers)*3.5+1.4); ax.set_ylim(-4.4,4.4)
        else:
            G = nx.DiGraph()
            G.add_nodes_from(range(graph.n))
            for v, ps in enumerate(graph.parents):
                G.add_edges_from((u, v) for u in ps)
            pos = nx.spring_layout(G, seed=args.seed)
            colors = ['tab:orange' if i in selected else 'tab:blue' for i in G.nodes()]
            nx.draw_networkx(G, pos, ax=ax, node_size=95,
                             arrows=True, arrowsize=7, with_labels=False,
                             node_color=colors, width=0.6)
        ax.set_title(f'{graph.family.upper()} DAG | orange = reviewed, blue = not reviewed')
        ax.axis('off')
        fig.tight_layout()
        p = args.out / f'dag_{args.family}.png'
        fig.savefig(p, dpi=160)
        plt.close(fig)
        print('Graph image:', p)



if __name__ == '__main__':
    main()
