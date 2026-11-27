import unittest
import numpy as np
from confidence_shrinkage import make_belief
from compare_type_priors import type_belief
import proposal_gaps as P


class ShrinkageTests(unittest.TestCase):
    def test_endpoints_midpoint_and_no_hidden_inputs(self):
        env = P.environment(1000, 'normal', 1.)
        for alpha, expected in [(0., type_belief(env, 1000)), (1., env['belief'])]:
            actual = make_belief(env, 1000, alpha)
            np.testing.assert_array_equal(actual.B, expected.B)
            np.testing.assert_array_equal(actual.C, expected.C)
        prior = np.array([P.SP.P_TYPE[n['type']] for n in env['nodes']])
        q = np.array([P.conf_posterior(min(1-1e-6,max(1e-6,c)),p) for c,p in zip(env['conf'],prior)])
        b = make_belief(env,1000,.5)
        rng = np.random.default_rng(11000)
        np.testing.assert_array_equal(b.B,rng.random(b.B.shape)<((prior+q)/2)[:,None])
        visible={k:env[k] for k in ['nodes','topo','sinks','conf']}
        np.testing.assert_array_equal(make_belief(visible,1000,.5).B,b.B)


if __name__ == '__main__':
    unittest.main()
