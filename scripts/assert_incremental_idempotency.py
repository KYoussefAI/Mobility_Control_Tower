"""Assert two dbt reliability export directories are identical."""

from __future__ import annotations

import sys

from compare_reliability_outputs import main

if __name__ == "__main__":
    sys.exit(main())
