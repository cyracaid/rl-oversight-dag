"""Tests for the label-free contrastive pilot (no trained-model claims here)."""
import unittest

import numpy as np
import torch

from dag_role3 import contrastive as C


class ContrastiveTest(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.ds = C.build_dataset("real", tuple(range(5024, 5028)))

    def test_dataset_shapes(self):
        ds = self.ds
        n, fdim = ds.features.shape[1], ds.features.shape[2]
        self.assertEqual(ds.features.shape, (4, n, fdim))
        self.assertEqual(ds.labels.shape, (4, n))
        self.assertEqual(ds.prior.shape, (n,))
        self.assertEqual(len(ds.edge_prob), len(ds.edge_src))
        self.assertTrue(all(0.0 <= float(p) <= 1.0 for p in ds.edge_prob))

    def test_view_keeps_shape_and_masks_only_dynamic_columns(self):
        ds = self.ds
        k = ds.features.shape[2] - 7
        x, (src, dst, weight, m, n) = C._view(ds.features, ds, k, np.random.default_rng(0),
                                              augment=True)
        self.assertEqual(x.shape, (4 * n, n, ds.features.shape[2]))
        self.assertEqual(m, 4 * n)
        # Static columns (type one-hot, sink flag) must survive augmentation untouched.
        static = [c for c in range(ds.features.shape[2]) if c not in (k, k + 2, k + 3)]
        base = ds.features[0]
        got = x[0]
        self.assertTrue(torch.equal(got[:, static], base[:, static]))

    def test_rdm_is_bounded_and_deterministic(self):
        ds = self.ds
        emb = torch.rand(4, ds.features.shape[1], 32)
        emb = torch.nn.functional.normalize(emb, dim=-1)
        rho = C.rdm_spearman(emb, ds.labels)
        self.assertEqual(rho, C.rdm_spearman(emb, ds.labels))
        self.assertTrue(-1.0 <= rho <= 1.0)

    def test_one_training_step_moves_parameters(self):
        enc, info = C.train_contrastive(self.ds, epochs=1, batch=4)
        self.assertEqual(info["steps"], 1)
        self.assertTrue(all(torch.isfinite(p).all() for p in enc.parameters()))
        z = C.embed_clean(enc, self.ds)
        self.assertEqual(z.shape, (4, self.ds.features.shape[1], 32))
        self.assertAlmostEqual(float(z.norm(dim=-1).mean()), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
