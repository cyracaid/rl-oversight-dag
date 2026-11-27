import unittest
from run_outcome_averaged import summarize


class SummaryTests(unittest.TestCase):
    def row(self, graph, gain, reference_gain):
        return dict(graph=graph, profile='normal-confidence', seed=0,
                    method='averaged', errors=.1-gain, greedy_errors=.1,
                    reference_1024_errors=.1-reference_gain,
                    expected_simulated_reviews=100., expected_posterior_updates=120.,
                    expected_posterior_copies=150., tree_seconds=.1)

    def test_zero_reference_gain_in_partial_summary_is_undefined(self):
        result = summarize([self.row(32000, 0., 0.)], False)
        self.assertIsNone(result['cells'][0]['retained_gain'])
        self.assertIsNone(result['engineering_gate_passed'])

    def test_nonzero_aggregate_reference_gain_after_partial_zero(self):
        result = summarize([self.row(32000, 0., 0.), self.row(32001, .01, .02)], False)
        self.assertAlmostEqual(result['cells'][0]['retained_gain'], .5)

    def test_incomplete_case_set_cannot_pass_gate(self):
        result = summarize([self.row(32000, 0., 0.)], True)
        self.assertFalse(result['engineering_gate_passed'])


if __name__ == '__main__':
    unittest.main()
