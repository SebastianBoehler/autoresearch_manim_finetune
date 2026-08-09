from __future__ import annotations

import unittest

from mac_pipeline.grouped_split import assign_split_groups, split_grouped_cases
from mac_pipeline.types import SplitConfig


class GroupedSplitTests(unittest.TestCase):
    def test_near_duplicate_concepts_share_a_group(self) -> None:
        cases = [
            {
                "case_id": "fraction_a",
                "prompt": "Explain three fourths on a number line with four equal intervals.",
                "tags": ["fraction", "number-line", "tier:gold"],
            },
            {
                "case_id": "fraction_b",
                "prompt": "Show why three fourths means three of four equal number-line parts.",
                "tags": ["round13", "fraction", "number-line"],
            },
            {
                "case_id": "wave",
                "prompt": "Show interference between two waves.",
                "tags": ["physics", "waves"],
            },
        ]

        grouped = assign_split_groups(cases)
        by_id = {case["case_id"]: case for case in grouped}

        self.assertEqual(by_id["fraction_a"]["split_group"], by_id["fraction_b"]["split_group"])
        self.assertNotEqual(by_id["fraction_a"]["split_group"], by_id["wave"]["split_group"])

    def test_split_keeps_groups_intact_and_is_deterministic(self) -> None:
        cases = [
            {
                "case_id": f"case_{index}",
                "split_group": f"group_{index // 2}",
            }
            for index in range(12)
        ]
        config = SplitConfig(train_fraction=0.5, valid_fraction=0.25, seed=7)

        first = split_grouped_cases(cases, config)
        second = split_grouped_cases(list(reversed(cases)), config)

        self.assertEqual(
            {name: sorted(case["case_id"] for case in rows) for name, rows in first.items()},
            {name: sorted(case["case_id"] for case in rows) for name, rows in second.items()},
        )
        group_splits: dict[str, set[str]] = {}
        for split_name, rows in first.items():
            self.assertTrue(rows)
            for row in rows:
                group_splits.setdefault(row["split_group"], set()).add(split_name)
        self.assertTrue(all(len(names) == 1 for names in group_splits.values()))


if __name__ == "__main__":
    unittest.main()
