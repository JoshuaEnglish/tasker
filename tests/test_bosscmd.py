import unittest

from tasker import minioncmd


class MinionCmdTestCase(unittest.TestCase):
    def test_default_prompt(self):
        b = minioncmd.BossCmd()
        self.assertEqual(b.prompt, 'Boss> ')

    def test_empty_queue(self):
        b = minioncmd.BossCmd()
        self.assertListEqual(b.cmdqueue, [])


class MinionCmdQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.boss = minioncmd.BossCmd()

    def tearDown(self):
        del self.boss


if __name__ == '__main__':
    unittest.main()
