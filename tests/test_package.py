"""Smoke tests for the citywalk2d package.

Verifies the package imports cleanly, exposes its version, and that the
entrypoint runs without error.  Interactive play needs a terminal, so the
entrypoint is exercised here through its non-interactive ``--demo`` mode.
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
        self.assertIsInstance(config.CITY_WIDTH, int)
        self.assertIsInstance(config.CITY_HEIGHT, int)
        self.assertIsInstance(config.CITY_SEED, int)


class TestEntrypoint(unittest.TestCase):
    def test_demo_returns_zero(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = entrypoint.main(["--demo"])
        self.assertEqual(code, 0)
        self.assertIn("citywalk2d", buf.getvalue())
        self.assertIn("#", buf.getvalue())  # building glyphs in the ASCII city


if __name__ == "__main__":
    unittest.main()
