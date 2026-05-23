import re
import pdfplumber
import json

PDF_PATH = "25_bg-odds.pdf"

def extract_hunts():
    hunts = []

    with pdfplumber.open(PDF_PATH) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    blocks = full_text.split("Hunt:")

    for block in blocks:
        if "Elk" not in block:
            continue

        match = re.search(r'(EB\d{4})', block)
        if not match:
            continue

        hunt_code = match.group(1)

        if "Archery" in block:
            weapon = "archery"
        elif "Muzzleloader" in block:
            weapon = "muzzleloader"
        else:
            weapon = "rifle"

        rows = re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', block)

        parsed_rows = []
        for r in rows:
            parsed_rows.append({
                "points": int(r[0]),
                "applicants": int(r[1]),
                "permits": int(r[3])
            })

        hunts.append({
            "hunt_code": hunt_code,
            "weapon": weapon,
            "data": parsed_rows
        })

    return hunts


def group_by_weapon(hunts):
    grouped = {
        "archery": [],
        "rifle": [],
        "muzzleloader": []
    }

    for h in hunts:
        grouped[h["weapon"]].append(h)

    return grouped


if __name__ == "__main__":
    hunts = extract_hunts()
    grouped = group_by_weapon(hunts)

    with open("elk_hunts_grouped.json", "w") as f:
        json.dump(grouped, f, indent=2)

    print("DONE: elk_hunts_grouped.json created")