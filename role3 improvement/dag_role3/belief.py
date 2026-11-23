"""Sequential particles with bounded recovery from the full observation history."""
import numpy as np


class ParticleBelief:
    def __init__(self, graph, prior, edge_probability, count, seed):
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be a positive integer")
        self.graph = graph
        self.prior = np.asarray(prior, dtype=float).copy()
        self.edge_probability = np.asarray(edge_probability, dtype=float).copy()
        for vector, size in ((self.prior, graph.n), (self.edge_probability, graph.edge_count)):
            if vector.shape != (size,) or not np.all(np.isfinite(vector)) or np.any((vector < 0) | (vector > 1)):
                raise ValueError("invalid probability vector")
        self.rng = np.random.default_rng(seed)
        self.count = count
        self.history = []
        self.recoveries = 0
        self.resamples = 0
        self.offsets = np.cumsum([0] + [len(x) for x in graph.parents])
        self._draw()

    def _draw(self):
        self.weights = np.full(self.count, 1 / self.count)
        self.base = self.rng.random((self.graph.n, self.count)) < self.prior[:, None]
        self.edges = self.rng.random((self.graph.edge_count, self.count)) < self.edge_probability[:, None]
        self.propagate()

    def propagate(self):
        self.effective = self.base.copy()
        for v in self.graph.topo:
            for j, parent in enumerate(self.graph.parents[v], self.offsets[v]):
                self.effective[v] |= self.effective[parent] & self.edges[j]

    def probabilities(self):
        return (np.einsum('ij,j->i', self.base, self.weights),
                np.einsum('ij,j->i', self.effective, self.weights))

    def _condition(self, node, flagged, catch):
        detect = catch * self.effective[node]
        weights = self.weights * (detect if flagged else 1 - detect)
        if weights.sum() == 0:
            return False
        self.weights = weights / weights.sum()
        if flagged:
            self.base[node] = False
        self.propagate()
        return True

    def _resample(self):
        positions = (np.arange(self.count) + self.rng.random()) / self.count
        cdf = np.cumsum(self.weights)
        cdf[-1] = 1.0
        selected = np.searchsorted(cdf, positions, side="right")
        self.base = self.base[:, selected]
        self.edges = self.edges[:, selected]
        self.weights.fill(1 / self.count)
        self.resamples += 1
        self.propagate()

    def update(self, node, flagged, catch):
        if not 0 <= node < self.graph.n or not 0 <= catch <= 1:
            raise ValueError("invalid review")
        history = self.history + [(node, flagged, catch)]
        if not self._condition(node, flagged, catch):
            # Fresh prior particles, conditioned on ALL observations and past fixes.
            # No resampling during replay, so intermediate diversity is preserved.
            previous = self.base, self.edges, self.effective, self.weights
            for _ in range(8):
                self._draw()
                if all(self._condition(*event) for event in history):
                    self.recoveries += 1
                    break
            else:
                self.base, self.edges, self.effective, self.weights = previous
                return False
        self.history = history
        if 1 / np.dot(self.weights, self.weights) < self.count / 2:
            self._resample()
        return True
