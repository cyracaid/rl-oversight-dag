import unittest
from validate_selection_guard import accept


class GuardTests(unittest.TestCase):
    def test_sparse_lucky_event_rejected(self):
        self.assertFalse(accept([-2]+[0]*1023))

    def test_no_advantage_rejected(self):
        self.assertFalse(accept([0]*1024))
        self.assertFalse(accept([-1,1]*512))

    def test_consistent_advantage_accepted(self):
        self.assertTrue(accept([-1]*64+[0]*960))

    def test_minimum_event_requirement(self):
        self.assertFalse(accept([-1]*31+[0]*993))


if __name__=='__main__':
    unittest.main()
