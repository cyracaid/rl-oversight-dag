import unittest
import numpy as np

from dag_role3 import DAG, generate_graph, EpisodeSnapshot, OversightEnv, propagate, sample_episode


class GraphTests(unittest.TestCase):
    def test_generators_are_dags_and_deterministic(self):
        for family in ('spike','modular','ba','er','real'):
            g1 = generate_graph(family, 3)
            g2 = generate_graph(family, 3)
            self.assertEqual(g1.parents, g2.parents)
            self.assertEqual(len(g1.topo), g1.n)
            self.assertTrue(g1.edge_count >= 0)
            pos = {v:i for i,v in enumerate(g1.topo)}
            for v,ps in enumerate(g1.parents):
                self.assertTrue(all(pos[u]<pos[v] for u in ps))
            self.assertTrue(all(0<=s<g1.n for s in g1.sinks))
        self.assertEqual(generate_graph('spike',1).n,80)
        self.assertEqual(generate_graph('ba',1).n,500)
        self.assertEqual(generate_graph('real',1).n,21)
        self.assertEqual(len(generate_graph('real',1).sinks),4)

    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):
            DAG(parents=((1,),(0,)),types=(0,0),rates=(.2,))

    def test_sink_reach_unique_ancestors(self):
        g=DAG(parents=((),(0,),(0,),(1,2)),types=(0,0,0,0),rates=(.3,))
        self.assertEqual(g.sinks,(3,))
        self.assertEqual(g.sink_reach,(1,1,1,1))


class SemanticsTests(unittest.TestCase):
    def setUp(self):
        self.g=DAG(parents=((),(0,),(1,)),types=(0,0,0),rates=(.5,))
        self.snapshot=EpisodeSnapshot(
            source_errors=(True,False,False),
            edge_coins={(0,1):True,(1,2):True},
            edge_probs={(0,1):.7,(1,2):.7},
            confidence=(.2,.9,.9),review_uniforms=(.1,.1,.1),seed=1)

    def test_inherited_error_persists(self):
        env=OversightEnv(self.g,self.snapshot,budget=2,p_catch=1)
        self.assertEqual(env.no_review_score(),1)
        obs,reward,done,info=env.step(1)
        self.assertTrue(info['flagged'])
        self.assertFalse(done)
        self.assertEqual(reward,0.)
        self.assertNotIn('sink_errors',info) # no reward leak to policies
        obs,reward,done,info=env.step(0)
        self.assertEqual(reward,0.)
        self.assertTrue(done)
        self.assertEqual(env.final_audit()['final_sink_errors'],0)

    def test_clearing_source_and_fixed_coins(self):
        base=[True,False,False]
        self.assertEqual(propagate(self.g,base,self.snapshot.edge_coins),(True,True,True))
        base[0]=False
        self.assertEqual(propagate(self.g,base,self.snapshot.edge_coins),(False,False,False))

    def test_reviewer_miss(self):
        snap=EpisodeSnapshot(self.snapshot.source_errors,self.snapshot.edge_coins,
                             self.snapshot.edge_probs,self.snapshot.confidence,
                             (.95,.1,.1),1)
        env=OversightEnv(self.g,snap,budget=1,p_catch=.9)
        _,reward,done,info=env.step(0)
        self.assertFalse(info['flagged'])
        self.assertEqual(reward,-1.)

    def test_reset_and_mask(self):
        env=OversightEnv(self.g,self.snapshot,budget=2)
        obs=env.observation()
        self.assertEqual(obs['features'].shape,(3,8))
        self.assertEqual(set(obs.keys()),{'features','mask','edge_index','sink_ids',
                                           'budget_left','family','node_names'})
        self.assertEqual(sum(obs['mask']),3)
        env.step(0)
        with self.assertRaises(ValueError):env.step(0)
        new=env.reset()
        self.assertEqual(sum(new['mask']),3)
        with self.assertRaises(RuntimeError):env.final_audit()

    def test_strict_crn_per_node(self):
        # Isolated nodes: review outcome for each node never depends on order.
        g=DAG(parents=((),()),types=(0,0),rates=(.5,))
        snap=EpisodeSnapshot((True,True),{}, {},(.2,.2),(.2,.95),1)
        flags=[]
        for order in ((0,1),(1,0)):
            env=OversightEnv(g,snap,budget=2,p_catch=.9)
            outcome={}
            for a in order:
                _,_,_,info=env.step(a)
                outcome[a]=info['flagged']
            flags.append(outcome)
        self.assertEqual(flags[0],flags[1])
        self.assertEqual(flags[0],{0:True,1:False})

    def test_not_expose_truth(self):
        graph=generate_graph('spike',100)
        snap=sample_episode(graph,500)
        env=OversightEnv(graph,snap)
        obs=env.observation()
        self.assertNotIn('base',obs)
        self.assertNotIn('errors',obs)
        self.assertNotIn('coins',obs)
        self.assertEqual(obs['features'].shape,(80,12))
        self.assertTrue(np.all(obs['features']>=0))


if __name__=='__main__':unittest.main()
