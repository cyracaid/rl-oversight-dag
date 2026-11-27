import itertools
import unittest
import numpy as np
from belief import ParticleBelief
from exact_small_graph import ExactReview
from integrate_particle_policy import integrate
from sampled_planning import world_errors


class IntegrationTests(unittest.TestCase):
    def test_independent_scalar_world_catch_enumeration(self):
        parents=[[],[0],[1]];prior=[.2,.3,.4]
        b=ParticleBelief(parents,range(3),[2],{(0,1):.6,(1,2):.6},prior,.9,1024,4)
        result=integrate(ExactReview(parents,prior,sinks=[2]),b,3,0,'greedy')
        policy={tuple(map(tuple,r['history'])):r['action'] for r in result['tree'] if 'action' in r}
        expected=0.
        probabilities=prior+[.6,.6]+[.9]*3
        for bits in itertools.product([False,True],repeat=8):
            weight=np.prod([p if x else 1-p for x,p in zip(bits,probabilities)])
            base=np.array(bits[:3]);coins=np.array(bits[3:5]);catches=bits[5:]
            history=[]
            for _ in range(3):
                a=policy[tuple(history)]
                flag=bool(world_errors(base,coins,b)[a] and catches[a])
                if flag:
                    base[a]=False
                history.append((a,int(flag)))
            expected+=weight*int(world_errors(base,coins,b)[2])
        self.assertAlmostEqual(result['errors'],expected,places=12)
        self.assertAlmostEqual(result['leaf_mass'],1.)

    def test_feedback_branches_update_particle_state(self):
        b=ParticleBelief([[],[]],range(2),[0,1],{},[.5,.5],1.,1024,3)
        seen=[]
        def selector(posterior,available,remaining,step,seed,method):
            if step==1:
                seen.append(float(posterior.p_base()[0]))
            return available.index(True),{'simulated_reviews':0}
        integrate(ExactReview([[],[]],[.5,.5],catch=1.),b,2,0,'test',selector)
        self.assertEqual(seen,[0.,0.])
        self.assertGreater(b.p_base()[0],0.)

    def test_deterministic_repair(self):
        b=ParticleBelief([[],[0]],range(2),[1],{(0,1):1.},[1.,0.],1.,1024,0)
        for method in ['greedy','rollout','guarded']:
            result=integrate(ExactReview([[],[0]],[1.,0.],1.,1.),b,1,0,method)
            self.assertEqual(result['errors'],0.)


if __name__=='__main__':
    unittest.main()
