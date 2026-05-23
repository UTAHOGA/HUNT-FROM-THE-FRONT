from __future__ import annotations


CALIBRATION_BANDS = [
    "0.00",
    "0.01-0.05",
    "0.05-0.10",
    "0.10-0.25",
    "0.25-0.50",
    "0.50-0.75",
    "0.75-0.90",
    "0.90-0.99",
    "0.99-1.00",
]


def backtest_summary() -> dict[str, object]:
    return {
        "backtest_years": [2022, 2023, 2024, 2025],
        "status": "STRUCTURE_DEFINED_PUBLIC_DATA_BACKTEST_PENDING",
        "calibration_bands": CALIBRATION_BANDS,
        "false_guaranteed_count": 0,
    }
