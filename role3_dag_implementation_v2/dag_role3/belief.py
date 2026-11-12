"""Sequential Monte Carlo over source errors and fixed per-episode edge coins."""
import numpy as np


class ParticleBelief:
    def __init__(self, graph, prior, edge_probability, count, seed):
        self.graph = graph
        self.rng = np.random.default_rng(seed)
        self.weights = np.full(count, 1 / count)
        self.base = self.rng.random((graph.n, count)) < prior[:, None]
        self.edges = self.rng.random((graph.edge_count, count)) < edge_probability[:, None]
        self.offsets = np.cumsum([0] + [len(x) for x in graph.parents])
        self.propagate()

    def propagate(self):
        self.effective = self.base.copy()
        for v in self.graph.topo:
            for j, parent in enumerate(self.graph.parents[v], self.offsets[v]):
                self.effective[v] |= self.effective[parent] & self.edges[j]

    def probabilities(self):
        return (np.einsum('ij,j->i', self.base, self.weights),
                np.einsum('ij,j->i', self.effective, self.weights))

    def update(self, node, flagged, catch):
        detect = catch * self.effective[node]
        weights = self.weights * (detect if flagged else 1 - detect)
        if weights.sum() == 0:
            # The finite sample missed every state compatible with the observation.
            return False
        self.weights = weights / weights.sum()
        if flagged:
            self.base[node] = False
        count = len(weights)
        if 1 / np.dot(self.weights, self.weights) < count / 2:
            positions = (np.arange(count) + self.rng.random()) / count
            cdf = np.cumsum(self.weights)
            cdf[-1] = 1.0
            selected = np.searchsorted(cdf, positions, side="right")
            self.base = self.base[:, selected]
            self.edges = self.edges[:, selected]
            self.weights.fill(1 / count)
        self.propagate()
        return True
