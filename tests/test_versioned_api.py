from __future__ import annotations

import unittest

from mac_pipeline.versioned_api import (
    build_api_coverage,
    enrich_case_with_api_context,
    extract_api_usage,
)


class VersionedAPITests(unittest.TestCase):
    def test_extracts_public_constructors_scene_bases_and_typed_methods(self) -> None:
        code = """from manim import *

class Demo(Scene):
    def construct(self):
        axes = Axes().shift(LEFT)
        curve = axes.plot(lambda x: x**2)
        tracker = ValueTracker(0)
        marker = always_redraw(lambda: Dot(axes.c2p(tracker.get_value(), 0)))
        self.play(Create(curve))
"""

        usage = extract_api_usage(
            code,
            public_symbols={"Axes", "Create", "Dot", "Scene", "ValueTracker", "always_redraw"},
        )

        self.assertEqual(
            usage["api_symbols"],
            ["Axes", "Create", "Dot", "Scene", "ValueTracker", "always_redraw"],
        )
        self.assertIn("Axes.plot", usage["api_methods"])
        self.assertIn("Axes.c2p", usage["api_methods"])
        self.assertIn("ValueTracker.get_value", usage["api_methods"])

    def test_enrichment_replaces_unversioned_context_and_adds_runtime_metadata(self) -> None:
        case = {
            "case_id": "demo",
            "system": "Write Manim code.",
            "prompt": "Plot a curve.",
            "completion": "from manim import *\nclass Demo(Scene):\n    pass\n",
            "tags": ["docs", "longform"],
            "source_url": "https://docs.manim.community/en/v0.20.1/reference.html",
            "target_duration_seconds": 30,
        }

        enriched = enrich_case_with_api_context(
            case,
            manim_version="0.20.1",
            python_version="3.13",
            renderer="cairo",
            public_symbols={"Scene"},
        )

        self.assertIn("Manim Community Edition 0.20.1", enriched["system"])
        self.assertEqual(enriched["manim_version"], "0.20.1")
        self.assertEqual(enriched["renderers_tested"], ["cairo"])
        self.assertEqual(enriched["corpus_roles"], ["api_reference", "composite"])
        self.assertEqual(enriched["api_symbols"], ["Scene"])

    def test_coverage_counts_distinct_domains_roles_and_groups(self) -> None:
        cases = [
            {
                "case_id": "a",
                "api_symbols": ["Axes"],
                "api_methods": ["Axes.plot"],
                "source_domain": "math",
                "corpus_roles": ["pedagogical"],
                "split_group": "group-a",
            },
            {
                "case_id": "b",
                "api_symbols": ["Axes"],
                "api_methods": ["Axes.plot"],
                "source_domain": "physics",
                "corpus_roles": ["api_reference"],
                "split_group": "group-b",
            },
        ]

        coverage = build_api_coverage(cases, public_symbols={"Axes", "Circle"})

        self.assertEqual(coverage["symbols"]["Axes"]["examples"], 2)
        self.assertEqual(coverage["symbols"]["Axes"]["domains"], ["math", "physics"])
        self.assertEqual(coverage["symbols"]["Axes"]["split_groups"], 2)
        self.assertEqual(coverage["unused_public_symbols"], ["Circle"])


if __name__ == "__main__":
    unittest.main()
