from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import pdfplumber


PDF_PATH = Path(
    r"pipeline/RAW/hunt_unit_database/2025/pdf/harvest_report/ELK/2024 ELK ANTLERLESS GENERAL SEASON.pdf"
)
OUT_DIR = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/elk_antlerless_general_season_2024_extract"
)


ROW_RE = re.compile(
    r"^(?P<Unit>\S+)\s+"
    r"(?P<HuntNumber>EA\d{4})\s+"
    r"(?P<HuntName>.+?)\s+"
    r"(?P<CowHarvest>\d+)\s+"
    r"(?P<CalfHarvest>\d+)\s+"
    r"(?P<TotalHarvest>\d+)\s+"
    r"(?P<Permits>\d+)\s+"
    r"(?P<HuntersAfield>\d+)\s+"
    r"(?P<MeanDaysHunted>\d+(?:\.\d+)?)\s+"
    r"(?P<SuccessRate>\d+(?:\.\d+)?)$"
)


@dataclass
class ParsedRow:
    Unit: str
    Hunt_number: str
    Hunt_name: str
    Cow_harvest: int
    Calf_harvest: int
    Total_harvest: int
    Permits: int
    Hunters_afield: int
    Mean_days_hunted: float
    Success_rate_pct: float
    Sex_type: str
    Hunt_type: str
    Weapon: str
    hunt_codes_2026_elk: str
    hunt_code_count_2026: int
    matched_hunt_names_2026: str
    match_basis: str
    mapping_status: str
    table_title: str
    source_file: str
    source_page: int


def parse_page(page_text: str, page_num: int) -> list[ParsedRow]:
    rows: list[ParsedRow] = []
    table_title = "Limited-entry any legal weapon antlerless elk harvest, Utah 2024."
    for raw in (page_text or "").splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        row = ParsedRow(
            Unit=m.group("Unit"),
            Hunt_number=m.group("HuntNumber"),
            Hunt_name=m.group("HuntName"),
            Cow_harvest=int(m.group("CowHarvest")),
            Calf_harvest=int(m.group("CalfHarvest")),
            Total_harvest=int(m.group("TotalHarvest")),
            Permits=int(m.group("Permits")),
            Hunters_afield=int(m.group("HuntersAfield")),
            Mean_days_hunted=float(m.group("MeanDaysHunted")),
            Success_rate_pct=float(m.group("SuccessRate")),
            Sex_type="Antlerless",
            Hunt_type="Limited Entry",
            Weapon="Any Legal Weapon",
            hunt_codes_2026_elk=m.group("HuntNumber"),
            hunt_code_count_2026=1,
            matched_hunt_names_2026=m.group("HuntName"),
            match_basis="direct_hunt_number_from_pdf",
            mapping_status="mapped_to_2026_codes",
            table_title=table_title,
            source_file=str(PDF_PATH).replace("\\", "/"),
            source_page=page_num,
        )
        rows.append(row)
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[ParsedRow] = []
    page_counts: list[dict[str, int]] = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            page_rows = parse_page(page.extract_text() or "", idx)
            rows.extend(page_rows)
            page_counts.append({"source_page": idx, "rows": len(page_rows)})

    if not rows:
        raise RuntimeError("No data rows were extracted from ELK antlerless general season PDF.")

    data = [asdict(r) for r in rows]
    df = pd.DataFrame(data)
    df = df.rename(
        columns={
            "Hunt_number": "Hunt number",
            "Hunt_name": "Hunt name",
            "Cow_harvest": "Cow harvest",
            "Calf_harvest": "Calf harvest",
            "Total_harvest": "Total harvest",
            "Hunters_afield": "Hunters afield",
            "Mean_days_hunted": "Mean days hunted",
            "Success_rate_pct": "Success rate (%)",
        }
    )

    csv_path = OUT_DIR / "ELK_ANTLERLESS_GENERAL_SEASON_2024.csv"
    xlsx_path = OUT_DIR / "ELK_ANTLERLESS_GENERAL_SEASON_2024.xlsx"
    manifest_path = OUT_DIR / "elk_antlerless_general_season_2024_manifest.json"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    manifest = {
        "source_pdf": str(PDF_PATH).replace("\\", "/"),
        "output_csv": str(csv_path).replace("\\", "/"),
        "output_xlsx": str(xlsx_path).replace("\\", "/"),
        "rows_extracted": int(len(df)),
        "unique_hunt_codes": int(df["Hunt number"].nunique()),
        "page_row_counts": page_counts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {xlsx_path}")
    print(f"Wrote {manifest_path}")
    print(f"Rows extracted: {len(df)}")


if __name__ == "__main__":
    main()
