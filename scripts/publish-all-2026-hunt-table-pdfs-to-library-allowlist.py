from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER")
PDF_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "PDF'S"
ALLOWLIST = ROOT / "processed_data" / "hard_data_exports" / "library" / "public_library_allowlist.json"
AUDIT_JSON = ROOT / "processed_data" / "audits" / "public_library_hunt_table_pdf_allowlist_2026_audit.json"


def title_from_pdf(path: Path) -> str:
    return path.stem


def href(path: Path) -> str:
    return "./" + path.relative_to(ROOT).as_posix()


def main() -> None:
    items = json.loads(ALLOWLIST.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list):
        raise SystemExit("Public library allowlist is not a JSON array")

    original_count = len(items)
    kept = [
        item
        for item in items
        if not (
            isinstance(item, dict)
            and item.get("source") == "2026_hunt_table_pdf_all"
            and item.get("folderId") == "units2026"
        )
    ]

    pdfs = sorted(path for path in PDF_DIR.glob("*.pdf") if path.is_file())
    added = []
    for index, pdf in enumerate(pdfs, start=1):
        item = {
            "id": f"units2026-hunt-table-pdf-{pdf.stem.lower().replace(' ', '-').replace('.', '')}",
            "folderId": "units2026",
            "title": title_from_pdf(pdf),
            "subtitle": "2026 public hunt table PDF with permit counts and reviewed hard-data harvest-quality fields.",
            "href": href(pdf),
            "type": "pdf",
            "year": "2026",
            "delivery": "generated-pdf",
            "public_role": "2026 Hunt Table",
            "source": "2026_hunt_table_pdf_all",
            "sort_order": 9000 + index,
        }
        kept.append(item)
        added.append(item)

    ALLOWLIST.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "allowlist": str(ALLOWLIST.relative_to(ROOT)),
        "pdf_dir": str(PDF_DIR.relative_to(ROOT)),
        "original_items": original_count,
        "removed_previous_generated_hunt_table_pdf_items": original_count - len(kept) + len(added),
        "hunt_table_pdf_items_added": len(added),
        "final_items": len(kept),
        "pdf_titles": [item["title"] for item in added],
    }
    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"original_items={summary['original_items']}")
    print(f"hunt_table_pdf_items_added={summary['hunt_table_pdf_items_added']}")
    print(f"final_items={summary['final_items']}")
    print(f"audit_json={AUDIT_JSON}")


if __name__ == "__main__":
    main()
