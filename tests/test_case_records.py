from __future__ import annotations

import unittest

from mac_pipeline.case_records import case_to_chat_record, normalize_case_record


class CaseRecordTests(unittest.TestCase):
    def test_chat_training_record_uses_messages_without_completion_column(self) -> None:
        case = normalize_case_record(
            {
                "case_id": "demo",
                "prompt": "Create a scene.",
                "completion": "from manim import *\n\nclass Demo(Scene):\n    pass\n",
                "tags": [],
                "must_contain": [],
                "must_not_contain": [],
            }
        )

        record = case_to_chat_record(case)

        self.assertNotIn("completion", record)
        self.assertEqual(record["messages"][0]["role"], "system")
        self.assertEqual(record["messages"][1]["role"], "user")
        self.assertEqual(record["messages"][2]["role"], "assistant")
        self.assertEqual(record["messages"][2]["content"], case["completion"])


if __name__ == "__main__":
    unittest.main()
