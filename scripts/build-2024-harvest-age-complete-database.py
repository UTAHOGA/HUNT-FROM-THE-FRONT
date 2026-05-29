from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2025" / "pdf" / "harvest_report" / "24_bg_HARVEST_report.pdf"
BASE_2024_LONG = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2025"
    / "csv"
    / "harvest data"
    / "harvest_results_2024_for_2025_all_long.csv"
)
DATABASE_PATH = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"

OUT_DIR = ROOT / "data_model" / "harvest_quality"
OUT_AGE_ROWS = OUT_DIR / "harvest_results_2024_age_rows_from_24_bg.csv"
OUT_AGE_ROWS_EXPANDED = OUT_DIR / "harvest_results_2024_age_rows_hunt_code_expanded.csv"
OUT_COMPLETE_DB = OUT_DIR / "harvest_results_2024_complete_database.csv"
OUT_SUMMARY = OUT_DIR / "harvest_results_2024_complete_database_summary.json"

PAGE_DEER_HENRY = 32
PAGE_DEER_PAUNS = 33
PAGE_ELK_LE = 102
PAGE_PRONGHORN_LE = 141
PAGE_MOOSE = 168
PAGE_GOAT = 211

OBJECTIVE_RE = re.compile(r"^\d+(?:\.\d+)?[–-]\d+(?:\.\d+)?$")
PCT_RE = re.compile(r"^\d+%$")
NUM_RE = re.compile(r"^\d+(?:\.\d+)?$")
MISSING_TOKENS = {"—", "-", "--", ""}


def clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def norm(text: str) -> str:
    value = clean(text).lower()
    value = value.replace("&", " and ").replace("/", " ")
    value = value.replace("–", "-")
    value = value.replace("mtns", "mountains").replace("mtn", "mountain")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def num_or_blank(token: str) -> str:
    token = clean(token).replace("*", "")
    token = token.replace("—", "-")
    if token in MISSING_TOKENS:
        return ""
    return token if NUM_RE.match(token) else ""


def extract_page_lines(reader: PdfReader, page_num: int) -> list[str]:
    text = reader.pages[page_num - 1].extract_text() or ""
    lines = [clean(x) for x in text.splitlines() if clean(x)]
    out: list[str] = []
    for line in lines:
        # Skip trailing page-number line if present.
        if re.fullmatch(r"\d{1,3}", line):
            continue
        out.append(line)
    return out


def parse_deer_henry(lines: list[str]) -> list[dict[str, str]]:
    pairs: list[tuple[str, str]] = []
    three_year_age = ""
    three_year_pct = ""
    for line in lines:
        m_pair = re.fullmatch(r"(\d+(?:\.\d+)?)\s+(\d+%)", line)
        if m_pair:
            pairs.append((m_pair.group(1), m_pair.group(2)))
            continue
        m_avg = re.fullmatch(r"3-yr average\s+(\d+(?:\.\d+)?)\s+(\d+%)", line)
        if m_avg:
            three_year_age, three_year_pct = m_avg.group(1), m_avg.group(2)
    if len(pairs) < 20:
        raise RuntimeError(f"Expected 20 Henry deer age rows, found {len(pairs)}")
    age_2024, pct_2024 = pairs[-1]
    return [
        {
            "reported_hunt_year": "2024",
            "model_target_year": "2025",
            "species": "Mule Deer",
            "unit": "",
            "unit_name": "Henry Mtns",
            "objective": "",
            "avg_age_2024": age_2024,
            "avg_age_3yr_average": three_year_age,
            "percent_5yr_plus_2024": pct_2024,
            "percent_5yr_plus_3yr_average": three_year_pct,
            "source_file": "24_bg_HARVEST_report.pdf",
            "source_page": str(PAGE_DEER_HENRY),
            "source_table": "Average age of harvested buck deer from Henry Mtns unit, Utah 2005-2024",
            "table_id": "deer_henry_age",
        }
    ]


def parse_deer_pauns(lines: list[str]) -> list[dict[str, str]]:
    age_2024 = ""
    pct_2024 = ""
    age_3yr = ""
    pct_3yr = ""
    for line in lines:
        m_2024 = re.fullmatch(r"2024\s+(\d+(?:\.\d+)?)\s+(\d+%)", line)
        if m_2024:
            age_2024, pct_2024 = m_2024.group(1), m_2024.group(2)
        m_3yr = re.fullmatch(r"3-yr average\s+(\d+(?:\.\d+)?)\s+(\d+%)", line)
        if m_3yr:
            age_3yr, pct_3yr = m_3yr.group(1), m_3yr.group(2)
    if not age_2024:
        raise RuntimeError("Failed to parse 2024 Paunsaugunt deer age row")
    return [
        {
            "reported_hunt_year": "2024",
            "model_target_year": "2025",
            "species": "Mule Deer",
            "unit": "",
            "unit_name": "Paunsaugunt",
            "objective": "",
            "avg_age_2024": age_2024,
            "avg_age_3yr_average": age_3yr,
            "percent_5yr_plus_2024": pct_2024,
            "percent_5yr_plus_3yr_average": pct_3yr,
            "source_file": "24_bg_HARVEST_report.pdf",
            "source_page": str(PAGE_DEER_PAUNS),
            "source_table": "Average age of harvested buck deer on Paunsaugunt unit, Utah 2005-2024",
            "table_id": "deer_paunsaugunt_age",
        }
    ]


def parse_objective_table(
    lines: list[str],
    species: str,
    table_id: str,
    source_page: int,
    value_count: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in lines:
        if line.lower().startswith("average age of harvested"):
            continue
        if line.lower().startswith("unit unit name"):
            continue
        tokens = line.split()
        if len(tokens) < 5:
            continue

        # "Statewide average ..." rows have no unit code/objective fit.
        if line.lower().startswith("statewide average"):
            tail = tokens[-value_count:]
            if len(tail) != value_count:
                continue
            rows.append(
                {
                    "reported_hunt_year": "2024",
                    "model_target_year": "2025",
                    "species": species,
                    "unit": "",
                    "unit_name": "Statewide average",
                    "objective": "",
                    "avg_age_2024": num_or_blank(tail[-2]),
                    "avg_age_3yr_average": num_or_blank(tail[-1]),
                    "percent_5yr_plus_2024": "",
                    "percent_5yr_plus_3yr_average": "",
                    "source_file": "24_bg_HARVEST_report.pdf",
                    "source_page": str(source_page),
                    "source_table": table_id,
                    "table_id": table_id,
                }
            )
            continue

        objective_idx = None
        for i, tok in enumerate(tokens):
            if OBJECTIVE_RE.match(tok):
                objective_idx = i
                break
        if objective_idx is None or objective_idx < 2:
            continue

        unit = tokens[0]
        unit_name = " ".join(tokens[1:objective_idx]).strip()
        objective = tokens[objective_idx]
        tail = tokens[objective_idx + 1 :]
        if len(tail) < value_count:
            continue
        tail = tail[:value_count]

        rows.append(
            {
                "reported_hunt_year": "2024",
                "model_target_year": "2025",
                "species": species,
                "unit": unit,
                "unit_name": unit_name,
                "objective": objective,
                "avg_age_2024": num_or_blank(tail[-2]),
                "avg_age_3yr_average": num_or_blank(tail[-1]),
                "percent_5yr_plus_2024": "",
                "percent_5yr_plus_3yr_average": "",
                "source_file": "24_bg_HARVEST_report.pdf",
                "source_page": str(source_page),
                "source_table": table_id,
                "table_id": table_id,
            }
        )
    return rows


def parse_goat_table(lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in lines:
        if line.lower().startswith("average age of harvested"):
            continue
        if line.lower().startswith("unit unit name"):
            continue
        tokens = line.split()
        if len(tokens) < 5:
            continue
        if line.lower().startswith("statewide average"):
            tail = tokens[-11:]
            rows.append(
                {
                    "reported_hunt_year": "2024",
                    "model_target_year": "2025",
                    "species": "Mountain Goat",
                    "unit": "",
                    "unit_name": "Statewide average",
                    "objective": "",
                    "avg_age_2024": num_or_blank(tail[-2]),
                    "avg_age_3yr_average": num_or_blank(tail[-1]),
                    "percent_5yr_plus_2024": "",
                    "percent_5yr_plus_3yr_average": "",
                    "source_file": "24_bg_HARVEST_report.pdf",
                    "source_page": str(PAGE_GOAT),
                    "source_table": "Average age of harvested mountain goats, by management unit, Utah 2015-2024",
                    "table_id": "goat_age",
                }
            )
            continue

        if len(tokens) < 13:
            continue
        unit = tokens[0]
        tail = tokens[-11:]
        unit_name = " ".join(tokens[1:-11]).strip()
        rows.append(
            {
                "reported_hunt_year": "2024",
                "model_target_year": "2025",
                "species": "Mountain Goat",
                "unit": unit,
                "unit_name": unit_name,
                "objective": "",
                "avg_age_2024": num_or_blank(tail[-2]),
                "avg_age_3yr_average": num_or_blank(tail[-1]),
                "percent_5yr_plus_2024": "",
                "percent_5yr_plus_3yr_average": "",
                "source_file": "24_bg_HARVEST_report.pdf",
                "source_page": str(PAGE_GOAT),
                "source_table": "Average age of harvested mountain goats, by management unit, Utah 2015-2024",
                "table_id": "goat_age",
            }
        )
    return rows


def extract_age_rows_from_pdf(pdf_path: Path) -> pd.DataFrame:
    reader = PdfReader(str(pdf_path))
    age_rows: list[dict[str, str]] = []

    age_rows.extend(parse_deer_henry(extract_page_lines(reader, PAGE_DEER_HENRY)))
    age_rows.extend(parse_deer_pauns(extract_page_lines(reader, PAGE_DEER_PAUNS)))
    age_rows.extend(
        parse_objective_table(
            extract_page_lines(reader, PAGE_ELK_LE),
            species="Elk",
            table_id="elk_limited_entry_age",
            source_page=PAGE_ELK_LE,
            value_count=11,
        )
    )
    age_rows.extend(
        parse_objective_table(
            extract_page_lines(reader, PAGE_PRONGHORN_LE),
            species="Pronghorn",
            table_id="pronghorn_limited_entry_age",
            source_page=PAGE_PRONGHORN_LE,
            value_count=4,
        )
    )
    age_rows.extend(
        parse_objective_table(
            extract_page_lines(reader, PAGE_MOOSE),
            species="Moose",
            table_id="moose_age",
            source_page=PAGE_MOOSE,
            value_count=11,
        )
    )
    age_rows.extend(parse_goat_table(extract_page_lines(reader, PAGE_GOAT)))

    df = pd.DataFrame(age_rows).fillna("")
    # keep only rows with a parsed 2024 age value
    df = df[df["avg_age_2024"].astype(str).str.strip() != ""].copy()
    return df


def species_norm(species: str) -> str:
    s = norm(species)
    if s in {"deer", "mule deer"}:
        return "mule deer"
    return s


def table_filter(db: pd.DataFrame, table_id: str) -> pd.DataFrame:
    out = db.copy()
    hunt_type = out["hunt_type"].astype(str).str.lower()
    if table_id in {"elk_limited_entry_age", "pronghorn_limited_entry_age", "deer_henry_age", "deer_paunsaugunt_age"}:
        out = out[hunt_type.str.contains("limited entry", na=False)]
    if table_id in {"deer_henry_age", "deer_paunsaugunt_age"}:
        sex_type = out["sex_type"].astype(str).str.lower()
        out = out[
            sex_type.str.contains("antlered|buck", na=False)
            | out["hunt_name"].astype(str).str.lower().str.contains("buck", na=False)
        ]
    return out


def map_age_rows(age_df: pd.DataFrame, base_df: pd.DataFrame, db_df: pd.DataFrame) -> pd.DataFrame:
    unit_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, r in base_df.iterrows():
        code = str(r.get("hunt_code", "")).strip().upper()
        if not code:
            continue
        key = (species_norm(str(r.get("species", ""))), norm(str(r.get("unit_context", ""))))
        if key[1]:
            unit_map[key].add(code)

    expanded: list[dict[str, str]] = []
    for _, row in age_df.iterrows():
        species_key = species_norm(str(row["species"]))
        unit_key = norm(str(row.get("unit", "")))
        unit_name_key = norm(str(row.get("unit_name", "")))
        table_id = str(row.get("table_id", ""))

        candidates = set()
        if unit_key and unit_name_key != "statewide average":
            candidates |= unit_map.get((species_key, unit_key), set())

        if not candidates and unit_name_key and unit_name_key != "statewide average":
            db_sub = table_filter(db_df[db_df["species_norm"] == species_key], table_id)
            for _, drow in db_sub.iterrows():
                hunt_name = norm(str(drow.get("hunt_name", "")))
                if unit_name_key and (unit_name_key in hunt_name or hunt_name in unit_name_key):
                    code = str(drow.get("hunt_code", "")).strip().upper()
                    if code:
                        candidates.add(code)

        candidate_list = sorted(candidates)
        if unit_name_key == "statewide average":
            status = "statewide_no_hunt_code"
        elif len(candidate_list) == 0:
            status = "no_hunt_code_match_found"
        elif len(candidate_list) == 1:
            status = "mapped_unique"
        else:
            status = "ambiguous_multi_hunt_code_candidate"

        base_out = dict(row)
        base_out["candidate_hunt_code"] = ";".join(candidate_list)
        base_out["hunt_code_candidate_count"] = str(len(candidate_list))
        base_out["hunt_code_mapping_status"] = status

        if candidate_list:
            for idx, c in enumerate(candidate_list, start=1):
                out = dict(base_out)
                out["hunt_code"] = c
                out["expanded_candidate_index"] = f"{idx}/{len(candidate_list)}"
                out["expanded_mapping_status"] = (
                    "expanded_from_multi_candidate" if len(candidate_list) > 1 else "mapped_unique"
                )
                expanded.append(out)
        else:
            out = dict(base_out)
            out["hunt_code"] = ""
            out["expanded_candidate_index"] = ""
            out["expanded_mapping_status"] = status
            expanded.append(out)

    return pd.DataFrame(expanded).fillna("")


def build_complete_database(base_df: pd.DataFrame, age_expanded_df: pd.DataFrame) -> pd.DataFrame:
    out = base_df.copy()
    out["average_age_2024_from_24_bg"] = ""
    out["average_age_3yr_from_24_bg"] = ""
    out["age_source_table_24_bg"] = ""
    out["age_mapping_status_24_bg"] = ""

    age_rows = age_expanded_df[age_expanded_df["hunt_code"].astype(str).str.strip() != ""].copy()
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for _, r in age_rows.iterrows():
        code = str(r["hunt_code"]).strip().upper()
        if code:
            by_code[code].append(r.to_dict())

    for idx, row in out.iterrows():
        if str(row.get("reported_hunt_year", "")).strip() != "2024":
            continue
        code = str(row.get("hunt_code", "")).strip().upper()
        if not code:
            continue
        hits = by_code.get(code, [])
        if not hits:
            continue
        age_vals = sorted({str(h.get("avg_age_2024", "")).strip() for h in hits if str(h.get("avg_age_2024", "")).strip()})
        age3_vals = sorted(
            {str(h.get("avg_age_3yr_average", "")).strip() for h in hits if str(h.get("avg_age_3yr_average", "")).strip()}
        )
        tables = sorted({str(h.get("table_id", "")).strip() for h in hits if str(h.get("table_id", "")).strip()})
        statuses = sorted(
            {str(h.get("hunt_code_mapping_status", "")).strip() for h in hits if str(h.get("hunt_code_mapping_status", "")).strip()}
        )

        out.at[idx, "average_age_2024_from_24_bg"] = age_vals[0] if len(age_vals) == 1 else ""
        out.at[idx, "average_age_3yr_from_24_bg"] = age3_vals[0] if len(age3_vals) == 1 else ""
        out.at[idx, "age_source_table_24_bg"] = ";".join(tables)
        out.at[idx, "age_mapping_status_24_bg"] = ";".join(statuses) if statuses else "mapped"

    return out


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing source PDF: {PDF_PATH}")
    if not BASE_2024_LONG.exists():
        raise FileNotFoundError(f"Missing base 2024 harvest long CSV: {BASE_2024_LONG}")
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Missing DATABASE.csv: {DATABASE_PATH}")

    age_df = extract_age_rows_from_pdf(PDF_PATH)
    base_df = pd.read_csv(BASE_2024_LONG, dtype=str, low_memory=False).fillna("")
    base_24bg = base_df[base_df["source_file"].astype(str).str.lower().eq("24_bg_report.pdf")].copy()
    db_df = pd.read_csv(DATABASE_PATH, dtype=str, low_memory=False).fillna("")
    db_df["species_norm"] = db_df["species"].astype(str).map(species_norm)

    age_expanded = map_age_rows(age_df, base_24bg, db_df)
    complete = build_complete_database(base_df, age_expanded)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    age_df.to_csv(OUT_AGE_ROWS, index=False, encoding="utf-8-sig")
    age_expanded.to_csv(OUT_AGE_ROWS_EXPANDED, index=False, encoding="utf-8-sig")
    complete.to_csv(OUT_COMPLETE_DB, index=False, encoding="utf-8-sig")

    expanded_no_blank = age_expanded[age_expanded["hunt_code"].astype(str).str.strip() != ""]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf": str(PDF_PATH).replace("\\", "/"),
        "base_2024_harvest_source": str(BASE_2024_LONG).replace("\\", "/"),
        "age_rows_extracted": int(len(age_df)),
        "age_rows_by_species": age_df["species"].value_counts().to_dict(),
        "age_rows_mapped_unique": int((age_expanded["hunt_code_mapping_status"] == "mapped_unique").sum()),
        "age_rows_mapped_ambiguous": int((age_expanded["hunt_code_mapping_status"] == "ambiguous_multi_hunt_code_candidate").sum()),
        "age_rows_unmatched": int((age_expanded["hunt_code_mapping_status"] == "no_hunt_code_match_found").sum()),
        "age_rows_statewide": int((age_expanded["hunt_code_mapping_status"] == "statewide_no_hunt_code").sum()),
        "age_expanded_rows_total": int(len(age_expanded)),
        "age_expanded_rows_with_hunt_code": int(len(expanded_no_blank)),
        "complete_database_rows": int(len(complete)),
        "complete_database_rows_with_24bg_age": int(
            (complete["average_age_2024_from_24_bg"].astype(str).str.strip() != "").sum()
        ),
        "outputs": {
            "age_rows": str(OUT_AGE_ROWS).replace("\\", "/"),
            "age_rows_hunt_code_expanded": str(OUT_AGE_ROWS_EXPANDED).replace("\\", "/"),
            "complete_database": str(OUT_COMPLETE_DB).replace("\\", "/"),
        },
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
