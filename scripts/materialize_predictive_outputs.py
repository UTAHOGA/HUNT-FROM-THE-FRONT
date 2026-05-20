from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.utah_bonus_predictive.materialize",
            "--output-dir",
            str(REPO / "processed_data"),
            "--forecast-year",
            "2026",
            "--history-years",
            "2021,2022,2023,2024,2025",
        ],
        cwd=REPO,
        check=True,
    )


if __name__ == "__main__":
    main()
