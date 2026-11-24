"""Instance-level contrastive representation of review states (pilot).

Frozen design: ``PREREGISTER_CONTRASTIVE.md``. The encoder never sees a label;
labels enter only the linear probe and the supervised twin used as a control.

An *instance* is an ``(episode, node)`` pair. A *view* is the same episode with a
random corruption of the public features: node ``j`` in the view centred on node
``i`` has its dynamic columns (confidence, belief, effective) reset to the type
prior with probability 0.3 when ``j != i`` and 0.5 when ``j == i``; 20 % of edges
are dropped. Positives are two views of the same pair, negatives every other pair
in the batch.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .graphs import DAG, generate_graph
from .environment import OversightEnv, sample_episode


@dataclass
class Dataset:
    family: str
    graph: DAG
    seeds: tuple[int, ...]
    features: torch.Tensor      # (E, n, F) public features at t=0
    labels: torch.Tensor        # (E, n) hidden local source error, probe target only
    edge_src: torch.Tensor      # (E_edges,)
    edge_dst: torch.Tensor
    edge_prob: torch.Tensor     # (E_edges,)
    prior: torch.Tensor         # (n,) type prior, the value a masked column takes


def build_dataset(family: str, seeds, confidence_mode: str = "normal") -> Dataset:
    graph = generate_graph(family)
    feats, labels = [], []
    for seed in seeds:
        snapshot = sample_episode(graph, seed, confidence_mode)
        env = OversightEnv(graph, snapshot, budget=1, p_catch=0.9)
        feats.append(torch.as_tensor(env.observation()["features"], dtype=torch.float32))
        labels.append(torch.as_tensor(np.asarray(snapshot.source_errors, dtype=np.float32)))
    src, dst = graph.edge_index()
    prob = sample_episode(graph, seeds[0], confidence_mode).edge_probs
    edge_prob = torch.tensor([float(prob[u, v]) for u, v in zip(src.tolist(), dst.tolist())])
    prior = torch.tensor([graph.rates[t] for t in graph.types], dtype=torch.float32)
    return Dataset(family, graph, tuple(seeds), torch.stack(feats), torch.stack(labels),
                   torch.as_tensor(src), torch.as_tensor(dst), edge_prob, prior)


def _view(feats, ds: Dataset, k: int, rng, *, augment: bool):
    """Build ``B*n`` centred views plus their edge tensors.

    ``feats``: (B, n, F). Returns (x (B*n, n, F), edges) with
    ``edges = (src, dst, weight, M, n)`` in flat ``instance*n + node`` indexing.
    """
    b, n, fdim = feats.shape
    if augment:
        threshold = torch.where(torch.eye(n, dtype=torch.bool),
                                torch.tensor(0.5), torch.tensor(0.3))
        mask = torch.rand(b, n, n) < threshold.unsqueeze(0)
        x = feats.unsqueeze(1).repeat(1, n, 1, 1).clone()
        for col in (k, k + 2, k + 3):
            x[..., col] = torch.where(mask, ds.prior.view(1, 1, n), x[..., col])
        x = x.reshape(b * n, n, fdim)
    else:
        x = feats.unsqueeze(1).repeat(1, n, 1, 1).reshape(b * n, n, fdim)
    m, edges = b * n, len(ds.edge_prob)
    inst = torch.arange(m).repeat_interleave(edges)
    src = inst * n + ds.edge_src.repeat(m)
    dst = inst * n + ds.edge_dst.repeat(m)
    keep = (torch.rand(m, edges) >= 0.2).reshape(-1).float() if augment else torch.ones(m * edges)
    weight = keep * ds.edge_prob.repeat(m)
    return x, (src, dst, weight, m, n)


class Encoder(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, dim: int = 32, rounds: int = 2):
        super().__init__()
        self.inp = nn.Linear(in_dim, hidden)
        self.blocks = nn.ModuleList(nn.Linear(3 * hidden, hidden) for _ in range(rounds))
        self.out = nn.Linear(hidden, dim)

    def forward(self, x, edges):
        src, dst, weight, m, n = edges
        h = F.relu(self.inp(x))
        for block in self.blocks:
            flat = h.reshape(m * n, -1)
            parents = torch.zeros_like(flat).index_add_(
                0, dst, weight.unsqueeze(-1) * flat[src])
            children = torch.zeros_like(flat).index_add_(
                0, src, weight.unsqueeze(-1) * flat[dst])
            deg_in = torch.zeros(m * n, 1).index_add_(
                0, dst, weight.unsqueeze(-1)).clamp(min=1.0)
            deg_out = torch.zeros(m * n, 1).index_add_(
                0, src, weight.unsqueeze(-1)).clamp(min=1.0)
            h = F.relu(block(torch.cat([flat, parents / deg_in, children / deg_out], -1)))
            h = h.reshape(m, n, -1)
        return F.normalize(self.out(h), dim=-1)


def train_contrastive(ds: Dataset, *, epochs=60, batch=None, lr=3e-3, temperature=0.2,
                      seed=20261125):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    k = ds.features.shape[2] - 7
    enc = Encoder(ds.features.shape[2])
    opt = torch.optim.Adam(enc.parameters(), lr=lr)
    episodes = len(ds.seeds)
    batch = min(batch or episodes, episodes)
    steps = 0
    enc.train()
    for _ in range(epochs):
        order = rng.permutation(episodes)
        for start in range(0, episodes, batch):
            idx = torch.as_tensor(order[start:start + batch])
            projected = []
            for _view_id in range(2):
                x, edges = _view(ds.features[idx], ds, k, rng, augment=True)
                out = enc(x, edges)
                m, n = out.shape[0], out.shape[1]
                projected.append(out[torch.arange(m), torch.arange(m) % n])
            sim = projected[0] @ projected[1].T / temperature
            loss = F.cross_entropy(sim, torch.arange(sim.shape[0]))
            opt.zero_grad()
            loss.backward()
            opt.step()
            steps += 1
    enc.eval()
    return enc, {"steps": steps, "epochs": epochs, "batch": batch, "temperature": temperature}


def train_supervised(ds: Dataset, *, epochs=60, batch=None, lr=3e-3, seed=20261125):
    """Same encoder, labels instead of the contrastive objective — the control."""
    torch.manual_seed(seed + 1)
    rng = np.random.default_rng(seed + 1)
    k = ds.features.shape[2] - 7
    enc = Encoder(ds.features.shape[2])
    head = nn.Linear(32, 1)
    opt = torch.optim.Adam(list(enc.parameters()) + list(head.parameters()), lr=lr)
    episodes = len(ds.seeds)
    batch = min(batch or episodes, episodes)
    enc.train()
    for _ in range(epochs):
        order = rng.permutation(episodes)
        for start in range(0, episodes, batch):
            idx = torch.as_tensor(order[start:start + batch])
            x, edges = _view(ds.features[idx], ds, k, rng, augment=True)
            out = enc(x, edges)
            m, n = out.shape[0], out.shape[1]
            diag = out[torch.arange(m), torch.arange(m) % n]
            loss = F.binary_cross_entropy_with_logits(head(diag),
                                                      ds.labels[idx].reshape(-1).unsqueeze(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
    enc.eval()
    head.eval()
    return enc, head


@torch.no_grad()
def embed_clean(enc, ds: Dataset):
    """(E, n, D) embeddings of un-augmented states, one per node."""
    k = ds.features.shape[2] - 7
    x, edges = _view(ds.features, ds, k, None, augment=False)
    out = enc(x, edges)
    m, n, d = out.shape
    return out.reshape(len(ds.seeds), n, n, d)[:, 0]


def own_features(ds: Dataset):
    k = ds.features.shape[2] - 7
    cols = list(range(k)) + [k, k + 1, k + 2, k + 3]
    return ds.features[..., cols]


def auc_of(prob, labels):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(labels, prob))


def rdm_spearman(emb, labels):
    """Spearman between the embedding RDM and the latent error RDM (node level)."""
    from scipy.stats import spearmanr
    mean_emb = emb.mean(0).numpy()
    gram = mean_emb / np.linalg.norm(mean_emb, axis=1, keepdims=True)
    cos = 1.0 - gram @ gram.T
    truth = labels.numpy().T
    ham = np.abs(truth[:, None, :] - truth[None, :, :]).mean(-1)
    iu = np.triu_indices(cos.shape[0], k=1)
    return float(spearmanr(cos[iu], ham[iu]).statistic)


def time_node_concentration(emb):
    """Mean cosine similarity among the four time nodes, plus its rank among all pairs."""
    mean_emb = emb.mean(0).numpy()
    gram = mean_emb / np.linalg.norm(mean_emb, axis=1, keepdims=True)
    sim = gram @ gram.T
    names = ["time_bed", "time_sleep", "time_awake", "time_getup"]
    idx = [names.index(x) for x in names]
    inner = float(np.mean([sim[a, b] for a in idx for b in idx if a < b]))
    iu = np.triu_indices(sim.shape[0], k=1)
    pairs = sim[iu]
    return inner, float(pairs.mean()), float((pairs < inner).mean())


def run_policy(graph, snapshot, scorer, budget, p_catch=0.9):
    env = OversightEnv(graph, snapshot, budget=budget, p_catch=p_catch)
    obs = env.observation()
    done = env.done
    while not done:
        obs, _, done, _ = env.step(scorer(obs))
    return env.final_audit()["final_sink_errors"]
