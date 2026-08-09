from __future__ import annotations

import types
import unittest

from mac_pipeline.api_surface import snapshot_public_api


class APISurfaceTests(unittest.TestCase):
    def test_snapshot_keeps_public_manim_callables_only(self) -> None:
        public_class = type("PublicClass", (), {"__module__": "manim.scene"})

        def public_function() -> None:
            return None

        public_function.__module__ = "manim.utils"
        external = type("External", (), {"__module__": "numpy"})
        module = types.SimpleNamespace(
            __version__="0.20.1",
            PublicClass=public_class,
            public_function=public_function,
            External=external,
            _Private=public_class,
            CONSTANT=1,
        )

        snapshot = snapshot_public_api(module, python_version="3.13")

        self.assertEqual(snapshot["manim_version"], "0.20.1")
        self.assertEqual(snapshot["python_version"], "3.13")
        self.assertEqual(snapshot["public_symbols"], ["PublicClass", "public_function"])

    def test_snapshot_rejects_unexpected_runtime_version(self) -> None:
        module = types.SimpleNamespace(__version__="0.21.0")

        with self.assertRaisesRegex(ValueError, "0.20.1"):
            snapshot_public_api(module, python_version="3.13", expected_version="0.20.1")


if __name__ == "__main__":
    unittest.main()
