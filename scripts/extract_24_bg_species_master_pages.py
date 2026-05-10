from __future__ import annotations

import json
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter


SRC = Path(r"pipeline/RAW/hunt_unit_database/2025/pdf/draw_odds/24_bg-odds.pdf")
OUT_DIR = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/24_bg_master_species_pages"
)

TARGET_SPECIES = {
    "LIMITED ENTRY ELK": "ELK",
    "LIMITED ENTRY PRONGHORN": "PRONGHORN",
    "BULL MOOSE": "MOOSE",
    "ROCKY MTN SHEEP": "ROCKY_MTN_SHEEP",
}


def find_species_pages() -> list[dict[str, str | int]]:
    matches: list[dict[str, str | int]] = []
    with pdfplumber.open(SRC) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            low = txt.lower()
            if "species:" not in low or "hunt:" in low:
                continue
            species_line = ""
            for line in txt.splitlines():
                line_s = line.strip()
                if line_s.lower().startswith("species:"):
                    species_line = line_s
                    break
            if not species_line:
                continue
            for key, short in TARGET_SPECIES.items():
                if key.lower() in species_line.lower():
                    matches.append(
                        {
                            "species_key": key,
                            "species_short": short,
                            "page_number": i,
                            "species_line": species_line,
                        }
                    )
                    break
    return matches


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matches = find_species_pages()

    # Keep only one page per target species, first hit.
    by_species: dict[str, dict[str, str | int]] = {}
    for m in matches:
        key = str(m["species_key"])
        by_species.setdefault(key, m)

    missing = [k for k in TARGET_SPECIES.keys() if k not in by_species]
    if missing:
        raise RuntimeError(f"Missing species pages: {missing}")

    reader = PdfReader(str(SRC))
    combined = PdfWriter()
    outputs: list[dict[str, str | int]] = []

    for key in TARGET_SPECIES.keys():
        m = by_species[key]
        page_num = int(m["page_number"])
        short = str(m["species_short"])
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])
        out_pdf = OUT_DIR / f"24_BG_MASTER_{short}_PAGE_{page_num}.pdf"
        with out_pdf.open("wb") as f:
            writer.write(f)
        combined.add_page(reader.pages[page_num - 1])
        outputs.append(
            {
                "species": key,
                "species_short": short,
                "page_number": page_num,
                "species_line": m["species_line"],
                "output_pdf": str(out_pdf).replace("\\", "/"),
            }
        )

    combined_pdf = OUT_DIR / "24_BG_MASTER_SPECIES_TOTALS_ELK_PRONGHORN_MOOSE_ROCKY_MTN_SHEEP.pdf"
    with combined_pdf.open("wb") as f:
        combined.write(f)

    csv_path = OUT_DIR / "24_bg_master_species_pages_index.csv"
    json_path = OUT_DIR / "24_bg_master_species_pages_index.json"

    csv_lines = ["species,species_short,page_number,species_line,output_pdf"]
    for r in outputs:
        csv_lines.append(
            f"\"{r['species']}\",\"{r['species_short']}\",{r['page_number']},\"{str(r['species_line']).replace('\"','\"\"')}\",\"{r['output_pdf']}\""
        )
    csv_path.write_text("\n".join(csv_lines), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "source_pdf": str(SRC).replace("\\", "/"),
                "combined_pdf": str(combined_pdf).replace("\\", "/"),
                "rows": outputs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {combined_pdf}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    for r in outputs:
        print(r)


if __name__ == "__main__":
    main()

