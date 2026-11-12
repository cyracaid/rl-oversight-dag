"""Replay-buffer + target-network DQN baseline using only public observations."""
import argparse
import copy
import csv
import random
from collections import deque
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from dag_role3 import OversightEnv, generate_graph
from dag_role3.models import GraphDQN, torch_obs


def q_values(net, obs):
    x,edges,mask=torch_obs(obs)
    return net(x,edges),mask


def optimize(net,target,optimizer,replay,rng,batch_size):
    if len(replay)<batch_size: return None
    batch=rng.sample(list(replay),batch_size)
    losses=[]
    for obs,a,r,next_obs,done in batch:
        qs,mask=q_values(net,obs)
        pred=qs[a]
        with torch.no_grad():
            if done: y=torch.tensor(float(r))
            else:
                qs_next, mask_next=q_values(target,next_obs)
                y=torch.tensor(float(r))+0.98*qs_next.masked_fill(~mask_next,-1e9).max()
        losses.append(F.smooth_l1_loss(pred,y))
    loss=torch.stack(losses).mean()
    optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),5.0)
    optimizer.step()
    return float(loss.item())


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--family',choices=['spike','modular','ba','er','real'],default='spike')
    ap.add_argument('--episodes',type=int,default=80)
    ap.add_argument('--seed',type=int,default=1)
    ap.add_argument('--eval-seeds',type=int,default=10)
    ap.add_argument('--out',type=Path,default=Path('outputs'))
    args=ap.parse_args()
    args.out.mkdir(exist_ok=True,parents=True)
    torch.set_num_threads(1)
    rng=random.Random(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    g=generate_graph(args.family,1)
    budget=16 if args.family=='spike' else 8 if args.family=='real' else 50
    net=GraphDQN(len(g.rates)+7)
    target=copy.deepcopy(net)
    optimizer=torch.optim.Adam(net.parameters(),lr=0.001)
    replay=deque(maxlen=5000)
    n_steps=0;history=[]
    for ep in range(args.episodes):
        graph=generate_graph(args.family,args.seed*1_000_000+ep)
        env=OversightEnv.from_seed(graph,seed=10_000+args.seed*1_000_000+ep,budget=budget)
        obs=env.observation()
        done=env._done
        epsilon=max(.05,1.0-0.95*ep/max(1,args.episodes-1))
        while not done:
            if rng.random()<epsilon:
                a=rng.choice(np.flatnonzero(obs['mask']).tolist())
            else:
                with torch.no_grad():
                    scores,mask=q_values(net,obs)
                    a=int(scores.masked_fill(~mask,-1e9).argmax().item())
            nxt,reward,done,info=env.step(a)
            replay.append((obs,a,reward,nxt,done))
            optimize(net,target,optimizer,replay,rng,batch_size=8)
            n_steps+=1
            if n_steps%200==0:
                target.load_state_dict(net.state_dict())
            obs=nxt
        history.append({'episode':ep+1,'sink_errors':env.final_audit()['final_sink_errors'],
                        'epsilon':epsilon})
        if (ep+1)%max(1,args.episodes//5)==0:
            print(f'train {ep+1:4d}/{args.episodes}: sink errors={history[-1]["sink_errors"]}')
    target.load_state_dict(net.state_dict())
    scores=[]
    with torch.no_grad():
        for s in range(1000,1000+args.eval_seeds):
            env=OversightEnv.from_seed(generate_graph(args.family,s),seed=50000+s,budget=budget)
            obs=env.observation();done=env._done
            while not done:
                qs,mask=q_values(net,obs)
                a=int(qs.masked_fill(~mask,-1e9).argmax().item())
                obs,_,done,_=env.step(a)
            scores.append(env.final_audit()['final_sink_errors'])
    name=f'dqn_{args.family}'
    torch.save({'state_dict':net.state_dict(),'family':args.family,
                'input_dim':len(g.rates)+7, 'seed':args.seed,'episodes':args.episodes},args.out/f'{name}.pt')
    with open(args.out/f'{name}_train.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
    print(f'Evaluation (held-out {len(scores)} graphs) mean final sink errors: '
          f'{np.mean(scores):.3f} (not a validated performance claim)')
    print('Saved model and training CSV to',args.out)


if __name__=='__main__':main()
