import unittest
import torch
from dag_role3.models import GNNScorer, GraphDQN, masked_action, torch_obs
from dag_role3 import gen_spike, OversightEnv


class ModelTest(unittest.TestCase):
    def test_shapes_backward(self):
        env=OversightEnv.from_seed(gen_spike(11),seed=44)
        obs=env.observation()
        x,edges,mask=torch_obs(obs)
        for model in (GNNScorer(x.shape[1]),GraphDQN(x.shape[1])):
            scores=model(x,edges)
            self.assertEqual(scores.shape,(80,))
            action,lp=masked_action(scores,mask,sample=True)
            self.assertTrue(0<=action<80)
            (-lp).backward()
            self.assertTrue(any(p.grad is not None for p in model.parameters()))

if __name__=='__main__':unittest.main()
