import unittest

from scripts.check_knowledge_triggers import run_cases


class RealKnowledgeLibraryTests(unittest.TestCase):
    def test_real_questions_reach_request_bodies(self):
        for row in run_cases():
            with self.subTest(question=row["question"]):
                self.assertTrue(row["passed"], row)
