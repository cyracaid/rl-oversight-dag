"""One-hop GNN scorer and graph-aware per-node DQN policy (PyTorch)."""
from __future__ import annotations
import torch
from torch import nn


def child_mean(x: torch.Tensor, edge_index: torch.Tensor):
    """Matches the reference A[parent,child] normalized by parent's child count."""
    n = x.shape[0]
    result = torch.zeros_like(x)
    if edge_index.numel():
        src, dst = edge_index[0], edge_index[1]
        result.index_add_(0, src, x[dst])
        counts = torch.bincount(src, minlength=n).clamp(min=1).to(x.dtype).unsqueeze(1)
        result = result / counts
    return result


class GNNScorer(nn.Module):
    """GNN + REINFORCE scorer, 1 child-to-parent message passing layer."""
    def __init__(self, input_dim: int, hidden_dim: int = 32):
        super().__init__()
        self.self_layer = nn.Linear(input_dim, hidden_dim, bias=True)
        self.neigh_layer = nn.Linear(input_dim, hidden_dim, bias=False)
        self.out = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor):
        agg = child_mean(x, edge_index)
        h = torch.tanh(self.self_layer(x) + self.neigh_layer(agg))
        return self.out(h).squeeze(1)


class GraphDQN(nn.Module):
    """Shared Q network over candidate nodes; graph context and global pool."""
    def __init__(self, input_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim * 3, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor):
        neighborhood = child_mean(x, edge_index)
        global_state = x.mean(dim=0, keepdim=True).expand_as(x)
        return self.network(torch.cat([x, neighborhood, global_state], dim=-1)).squeeze(1)


def torch_obs(obs, device="cpu", static=False):
    x = torch.as_tensor(obs["features"], dtype=torch.float32, device=device)
    if static:
        x = x[:, :x.shape[1]-5]
    edges = torch.as_tensor(obs["edge_index"], dtype=torch.long, device=device)
    mask = torch.as_tensor(obs["mask"], dtype=torch.bool, device=device)
    return x, edges, mask


def masked_action(scores, mask, sample=False, temperature=1.0):
    scores = scores.masked_fill(~mask, -1e9)
    if sample:
        dist = torch.distributions.Categorical(logits=scores / temperature)
        action = dist.sample()
        return int(action.item()), dist.log_prob(action)
    return int(torch.argmax(scores).item()), None
