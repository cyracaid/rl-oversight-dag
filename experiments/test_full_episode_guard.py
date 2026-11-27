import unittest
import numpy as np
from belief import ParticleBelief
from diagnose_graph_32005 import replay
from run_full_episode_guard import continuation


class ContinuationTests(unittest.TestCase):
    def test_replay_matches_previous_audited_path(self):
        b=ParticleBelief([[],[0],[1]],range(3),[2],{(0,1):.6,(1,2):.6},[.2,.3,.4],.9,1024,5)
        for action in range(3):
            expected=[r['errors'] for r in replay(b,action,7,samples=16)]
            np.testing.assert_array_equal(continuation(b,[True]*3,3,action,7,16),expected)

    def test_remaining_budget_and_mask(self):
        b=ParticleBelief([[],[0]],range(2),[1],{(0,1):1.},[1.,0.],1.,1024,0)
        np.testing.assert_array_equal(continuation(b,[False,True],1,1,3,8),np.ones(8))
        np.testing.assert_array_equal(continuation(b,[True,True],1,0,3,8),np.zeros(8))


if __name__=='__main__':
    unittest.main()
