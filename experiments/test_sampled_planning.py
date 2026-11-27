import copy
import unittest
import numpy as np
from belief import ParticleBelief
from sampled_planning import choose


class SampledTests(unittest.TestCase):
    def test_paired_diagnostics_preserve_decision(self):
        b=ParticleBelief([[],[0]],range(2),[1],{(0,1):1.},[1.,0.],1.,256,0)
        a,d=choose(b,[True,True],1,8,2,7,paired_diagnostics=True)
        plain,detail=choose(b,[True,True],1,8,2,7)
        self.assertEqual(a,plain)
        self.assertEqual(d['candidate_values'],detail['candidate_values'])
        self.assertEqual(d['paired_vs_greedy'][1],{'mean':1.,'standard_error':0.})
        self.assertEqual(d['paired_vs_greedy'][0],{'mean':0.,'standard_error':0.})

    def test_no_mutation_reproducible_and_budget(self):
        b=ParticleBelief([[],[0],[0]],range(3),[1,2],{(0,1):.6,(0,2):.6},[.2,.1,.3],.9,256,3)
        original=copy.deepcopy(b)
        a,d=choose(b,[True]*3,2,4,2,5)
        self.assertEqual((a,d),choose(b,[True]*3,2,4,2,5))
        np.testing.assert_array_equal(b.B,original.B)
        np.testing.assert_array_equal(b.C,original.C)
        self.assertEqual(b.rng.bit_generator.state,original.rng.bit_generator.state)
        self.assertEqual(d['simulated_reviews'],16)
        self.assertIn(d['greedy'],d['candidate_values'])

    def test_deterministic_upstream_repair(self):
        b=ParticleBelief([[],[0]],range(2),[1],{(0,1):1.},[1.,0.],1.,256,0)
        a,d=choose(b,[True,True],1,4,2,0)
        self.assertEqual(a,0)
        self.assertEqual(d['candidate_values'],{0:0.,1:1.})

    def test_invalid_remaining_budget(self):
        b=ParticleBelief([[]],[0],[0],{},[.5],.9,256,0)
        with self.assertRaises(ValueError):
            choose(b,[True],2)

    def test_single_review_values_match_particle_expectation(self):
        b=ParticleBelief([[],[0]],range(2),[1],{(0,1):.6},[.2,.3],.9,256,1)
        _,d=choose(b,[True,True],1,4096,2,9)
        initial=b.p_err()[1]
        for action,value in d['candidate_values'].items():
            self.assertAlmostEqual(value,initial-b.gain(action),delta=.03)


if __name__=='__main__': unittest.main()
