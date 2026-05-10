from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def normalize_weapon_category(title: str) -> str:
    t = (title or "").lower()
    if "archery" in t and "extended" not in t:
        return "ARCHERY"
    if "muzzleloader" in t:
        return "MUZZLELOADER"
    if "early any legal weapon" in t:
        return "EARLY_ANY_LEGAL_WEAPON"
    if "any legal weapon" in t:
        return "ANY_LEGAL_WEAPON"
    if "extended archery" in t:
        return "EXTENDED_ARCHERY"
    return "UNSPECIFIED"


def load_manifest(manifest_path: Path) -> pd.DataFrame:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    df = pd.read_csv(manifest_path)
    if "adobe_page" not in df.columns:
        raise RuntimeError("Manifest missing adobe_page column.")
    return df


def load_section_lines(section_csv: Path) -> pd.DataFrame:
    if not section_csv.exists():
        return pd.DataFrame(columns=["line_number", "text"])
    try:
        df = pd.read_csv(section_csv)
    except Exception:
        return pd.DataFrame(columns=["line_number", "text"])
    if "line_number" not in df.columns:
        df["line_number"] = range(1, len(df) + 1)
    if "text" not in df.columns:
        # Fallback for unexpected structure
        first_col = df.columns[0]
        df = df.rename(columns={first_col: "text"})
        df["line_number"] = range(1, len(df) + 1)
    return df[["line_number", "text"]]


def build_group_rows(manifest: pd.DataFrame, pages: list[int], group_name: str, apply_weapon: bool = False) -> pd.DataFrame:
    subset = manifest[manifest["adobe_page"].astype(int).isin(pages)].copy()
    subset = subset.sort_values(["adobe_page", "section_index"])

    rows = []
    for _, m in subset.iterrows():
        src = Path(str(m["csv_file"]))
        section_df = load_section_lines(src)
        weapon_category = normalize_weapon_category(str(m.get("title", ""))) if apply_weapon else ""
        for _, r in section_df.iterrows():
            rows.append(
                {
                    "group_name": group_name,
                    "adobe_page": int(m["adobe_page"]),
                    "section_index": int(m["section_index"]),
                    "section_title": str(m.get("title", "")),
                    "weapon_category": weapon_category,
                    "line_number": int(r["line_number"]) if pd.notna(r["line_number"]) else None,
                    "text": str(r["text"]) if pd.notna(r["text"]) else "",
                }
            )
    return pd.DataFrame(rows)


def write_group(df: pd.DataFrame, out_dir: Path, base_name: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{base_name}.csv"
    xlsx_path = out_dir / f"{base_name}.xlsx"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="combined")
        # page-wise tabs for easier manual review
        if not df.empty:
            for page in sorted(df["adobe_page"].dropna().unique()):
                page_df = df[df["adobe_page"] == page].copy()
                sheet = f"page_{int(page)}"
                page_df.to_excel(writer, index=False, sheet_name=sheet[:31])
    return csv_path, xlsx_path


def main():
    parser = argparse.ArgumentParser(description="Group Adobe-page section splits from Pages from 24_bg_report-2.")
    parser.add_argument(
        "--manifest",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/pages_from_24_bg_report_2_adobe_section_splits/section_split_manifest.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/pages_from_24_bg_report_2_grouped_sections",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    out_dir = Path(args.out_dir).resolve()
    manifest = load_manifest(manifest_path)

    groups = {
        "GENERAL_SEASON_DEER_WEAPON_CATEGORIES_ADOBE_PAGES_1_3_4_5": {
            "pages": [1, 3, 4, 5],
            "apply_weapon": True,
        },
        "CWMU_BUCK_AND_ANTLERLESS_REQUESTED_ADOBE_PAGES_13_14_15_17": {
            "pages": [13, 14, 15, 17],
            "apply_weapon": False,
        },
        "POSTSEASON_FAWN_DEER_MULTI_PAGE_SINGLE_TABLE_ADOBE_PAGES_23_24": {
            "pages": [23, 24],
            "apply_weapon": False,
        },
    }

    report = {
        "manifest": str(manifest_path),
        "out_dir": str(out_dir),
        "groups": {},
    }

    for group_name, cfg in groups.items():
        df = build_group_rows(manifest, cfg["pages"], group_name, apply_weapon=cfg["apply_weapon"])
        csv_path, xlsx_path = write_group(df, out_dir, group_name)
        report["groups"][group_name] = {
            "pages": cfg["pages"],
            "rows": int(len(df)),
            "csv": str(csv_path),
            "xlsx": str(xlsx_path),
        }

    # Optional context file to flag semantic page/title mismatches.
    page_titles = (
        manifest[["adobe_page", "section_index", "title"]]
        .sort_values(["adobe_page", "section_index"])
        .to_dict(orient="records")
    )
    report["page_titles_snapshot"] = page_titles

    report_json = out_dir / "group_build_report.json"
    report_md = out_dir / "group_build_report.md"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with report_md.open("w", encoding="utf-8") as f:
        f.write("# Pages-from-24_bg_report-2 grouped files\n\n")
        f.write(f"Manifest: `{manifest_path}`\n\n")
        for name, meta in report["groups"].items():
            f.write(f"## {name}\n")
            f.write(f"- Pages: {meta['pages']}\n")
            f.write(f"- Rows: {meta['rows']}\n")
            f.write(f"- CSV: `{meta['csv']}`\n")
            f.write(f"- XLSX: `{meta['xlsx']}`\n\n")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
