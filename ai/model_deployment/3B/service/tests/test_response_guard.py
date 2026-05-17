import unittest

from app.response_guard import ResponseGuardError, parse_summary


class ResponseGuardTests(unittest.TestCase):
    def test_accepts_dynamic_keypoint_count(self):
        result = parse_summary(
            '{"summary":"Clear summary.","keyPoints":["A.","B.","C."]}'
        )
        self.assertEqual(result.summary, "Clear summary.")
        self.assertEqual(result.key_points, ["A.", "B.", "C."])

    def test_accepts_training_schema_names(self):
        result = parse_summary(
            '{"main_idea":"Clear summary.","key_points":["A."]}'
        )
        self.assertEqual(result.summary, "Clear summary.")
        self.assertEqual(result.key_points, ["A."])

    def test_rejects_invalid_json(self):
        with self.assertRaises(ResponseGuardError):
            parse_summary("not json")


if __name__ == "__main__":
    unittest.main()
