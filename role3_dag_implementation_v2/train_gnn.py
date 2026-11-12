"""Small, runnable GNN + REINFORCE demonstration, matching reference scorer.

For publication-level runs increase --episodes and use multiple training seeds.
No claim of reproducing existing repo metrics is made.
"""
import argparse
import csv
import random
from pathlib import Path
import numpy as np
import torch
from dag_role3 import OversightEnv, generate_graph
from dag_role3.models import GNNScorer, torch_obs, masked_action


def play(policy, family, graph_seed, episode_seed, budget, static=False,
         training=False, temperature=1.0):
    graph = generate_graph(family, graph_seed)
    env = OversightEnv.from_seed(graph, episode_seed, budget)
    obs = env.observation()
    done = env.done
    logps = []
    while not done:
        x, edges, mask = torch_obs(obs, static=static)
        logits = policy(x, edges)
        action, lp = masked_action(logits,mask,sample=training,temperature=temperature)
        if lp is not None:
            logps.append(lp)
        obs, reward, done, info = env.step(action)
    return -env.final_audit()['final_sink_errors'], logps


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--family',choices=['spike','modular','ba','er','real'],default='spike')
    ap.add_argument('--episodes',type=int,default=100)
    ap.add_argument('--seed',type=int,default=1)
    ap.add_argument('--variant',choices=['static','observed'],default='observed')
    ap.add_argument('--eval-seeds',type=int,default=10)
    ap.add_argument('--out',type=Path,default=Path('outputs'))
    args=ap.parse_args()
    if args.eval_seeds < 1 or args.episodes < 1: ap.error("episode counts must be positive")
    if args.episodes<=0: ap.error('--episodes must be positive')
    args.out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    graph=generate_graph(args.family,seed=1)
    budget=16 if args.family=='spike' else 8 if args.family=='real' else 50
    input_dim=len(graph.rates)+(2 if args.variant=='static' else 7)
    model=GNNScorer(input_dim)
    optim=torch.optim.Adam(model.parameters(), lr=0.003)
    ema=0.0
    history=[]
    for e in range(args.episodes):
        # Keep train graph/episode seeds separate from held-out 1000+
        gseed = args.seed*1_000_000+e
        temperature=max(0.3, 2.0*0.9993**e)
        reward, logps=play(model,args.family,gseed, 40_000+gseed,budget,
                           static=args.variant=='static', training=True, temperature=temperature)
        loss=-(reward-ema)*torch.stack(logps).sum()
        ema=.95*ema+.05*reward
        optim.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.0);optim.step()
        history.append({'episode':e+1,'sink_errors':-reward, 'temperature':temperature})
        if (e+1)%max(1,args.episodes//5)==0:
            print(f'train {e+1:4d}/{args.episodes}: sink errors={-reward:.0f}')
    eval_errors=[]
    with torch.no_grad():
        for seed in range(1000,1000+args.eval_seeds):
            r,_=play(model,args.family,seed,50_000+seed,budget,
                     static=args.variant=='static',training=False)
            eval_errors.append(-r)
    name=f'gnn_{args.family}_{args.variant}'
    torch.save({'state_dict':model.state_dict(),'family':args.family,'input_dim':input_dim,
                'seed':args.seed,'episodes':args.episodes},args.out/f'{name}.pt')
    with open(args.out/f'{name}_train.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
    print(f'Evaluation (held-out {len(eval_errors)} graphs) mean final sink errors: '
          f'{np.mean(eval_errors):.3f} (not a validated performance claim)')
    print('Saved model and training CSV to',args.out)


if __name__=='__main__':main()
