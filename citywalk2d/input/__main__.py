"""Run the deterministic input self-test: ``python3 -m citywalk2d.input``.

Exercises the byte/escape-sequence -> Action mapping headlessly and reports a
single PASS/FAIL line.  Raw terminal input itself cannot be exercised without
a real keyboard; that part is confirmed interactively on a laptop.
"""

from __future__ import annotations

from . import self_test


def main() -> int:
    try:
        self_test()
    except AssertionError as exc:
        print(f"input self-test: FAIL -- {exc}")
        return 1
    print("input self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
