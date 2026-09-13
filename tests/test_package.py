"""Smoke tests for the citywalk2d skeleton.

Verifies the package imports cleanly, exposes its version, and that the
entrypoint runs without error — nothing more, since game logic lands later.
"""

import contextlib
import io
import unittest

import citywalk2d
from citywalk2d import __main__ as entrypoint


class TestPackageMetadata(unittest.TestCase):
    def test_imports_and_exposes_version(self):
        self.assertTrue(citywalk2d.__version__)
        self.assertEqual(citywalk2d.__title__, "citywalk2d")

    def test_config_defaults_present(self):
        from citywalk2d import config

        self.assertIsInstance(config.DEFAULT_WIDTH, int)
        self.assertIsInstance(config.DEFAULT_HEIGHT, int)


class TestEntrypoint(unittest.TestCase):
    def test_main_returns_zero(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = entrypoint.main()
        self.assertEqual(code, 0)
        self.assertIn("citywalk2d", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
