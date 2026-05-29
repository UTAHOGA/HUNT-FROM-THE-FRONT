from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import List, Tuple

from openpyxl import load_workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER")
SRC_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "XLXS"
OUT_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "PDF'S"


def norm(v) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v).strip())


def find_header_row(ws) -> int:
    probe_max = min(ws.max_row, 14)
    best_r, best_score = 1, -1
    for r in range(1, probe_max + 1):
        vals = [norm(c.value) for c in ws[r]]
        non = [v for v in vals if v]
        if not non:
            continue
        key = " | ".join(v.lower() for v in non)
        score = len(non)
        if "hunt_code" in key:
            score += 20
        if "hunt_name" in key or "hunt name" in key:
            score += 12
        if "species" in key:
            score += 6
        if score > best_score:
            best_score = score
            best_r = r
    return best_r


def extract(ws) -> Tuple[str, str, List[str], List[List[str]]]:
    hr = find_header_row(ws)
    title = norm(ws.cell(row=1, column=1).value) or ws.title
    subtitle = ""
    if hr > 1:
        subtitle = norm(ws.cell(row=2, column=1).value)

    # bounds from header row
    first_col = None
    last_col = None
    for c in range(1, ws.max_column + 1):
        v = norm(ws.cell(row=hr, column=c).value)
        if v:
            if first_col is None:
                first_col = c
            last_col = c
    if first_col is None:
        first_col, last_col = 1, ws.max_column

    headers = [norm(ws.cell(row=hr, column=c).value) or f"Column {c}" for c in range(first_col, last_col + 1)]
    rows: List[List[str]] = []
    for r in range(hr + 1, ws.max_row + 1):
        vals = [norm(ws.cell(row=r, column=c).value) for c in range(first_col, last_col + 1)]
        if any(vals):
            rows.append(vals)

    return title, subtitle, headers, rows


def fit_widths(headers: List[str], rows: List[List[str]], avail_w: float) -> List[float]:
    weights = []
    sample = rows[:350]
    for i, h in enumerate(headers):
        m = len(h)
        for row in sample:
            if i < len(row):
                m = max(m, len(row[i]))
        m = max(8, min(48, m))
        hl = h.lower()
        if "hunt name" in hl:
            m = max(m, 26)
        if "season" in hl:
            m = max(m, 24)
        if "note" in hl:
            m = max(m, 22)
        weights.append(m)

    total = sum(weights)
    widths = [(w / total) * avail_w for w in weights]
    min_w = 0.48 * inch
    max_w = 2.1 * inch
    widths = [max(min_w, min(max_w, w)) for w in widths]
    scale = avail_w / sum(widths)
    return [w * scale for w in widths]


def render_pdf(xlsx: Path, pdf: Path) -> Tuple[int, int]:
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    title, subtitle, headers, rows = extract(ws)
    wb.close()

    doc = SimpleDocTemplate(
        str(pdf),
        pagesize=landscape(letter),
        leftMargin=0.22 * inch,
        rightMargin=0.22 * inch,
        topMargin=0.28 * inch,
        bottomMargin=0.28 * inch,
    )

    styles = getSampleStyleSheet()
    st_title = ParagraphStyle("t", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#2f1b0f"), spaceAfter=4)
    st_sub = ParagraphStyle("s", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8.5, textColor=colors.HexColor("#5b3a25"), spaceAfter=6)
    data = [headers]
    data.extend(rows)

    widths = fit_widths(headers, rows, doc.width)
    tbl = Table(data, repeatRows=1, colWidths=widths, hAlign="CENTER")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4f2d1d")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8.1),
        ("LEADING", (0,0), (-1,0), 9.2),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,-1), 7.3),
        ("LEADING", (0,1), (-1,-1), 8.6),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#c7b59f")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#fbf6ef"), colors.HexColor("#f3e8da")]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))

    meta = f"Source workbook: {xlsx.name} | Rows: {len(rows)} | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    story = [Paragraph(title, st_title)]
    if subtitle:
        story.append(Paragraph(subtitle, st_sub))
    story.append(Paragraph(meta, st_sub))
    story.append(Spacer(1, 0.06 * inch))
    story.append(tbl)

    doc.build(story)
    return len(headers), len(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in SRC_DIR.glob("*.xlsx") if not p.name.startswith("~$")])
    if not files:
        raise SystemExit("No xlsx files found")

    ok = 0
    for x in files:
        out = OUT_DIR / (x.stem + ".pdf")
        try:
            cols, rows = render_pdf(x, out)
            print(f"OK {x.name} -> {out.name} cols={cols} rows={rows}")
            ok += 1
        except Exception as e:
            print(f"ERR {x.name}: {e}")

    print(f"DONE total={len(files)} ok={ok} out={OUT_DIR}")

if __name__ == '__main__':
    main()
