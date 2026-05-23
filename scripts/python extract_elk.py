import re
import pdfplumber
import json

PDF_PATH = "24_bg-odds.pdf"

def extract_hunts():
    hunts = []

    with pdfplumber.open(PDF_PATH) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    blocks = full_text.split("Hunt:")

    for block in blocks:
        if "Elk" not in block:
            continue

        # Hunt code
        match = re.search(r'(EB\d{4})', block)
        if not match:
            continue

        hunt_code = match.group(1)

        # Weapon detection
        if "Archery" in block:
            weapon = "archery"
        elif "Muzzleloader" in block:
            weapon = "muzzleloader"
        else:
            weapon = "rifle"

        # Unit extraction (rough)
        unit_match = re.search(r'- ([A-Za-z ]+)', block)
        unit = unit_match.group(1).strip() if unit_match else None

        # Extract rows
        rows = re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', block)

        parsed_rows = []
        for r in rows:
            points = int(r[0])
            applicants = int(r[1])
            permits = int(r[3])

            parsed_rows.append({
                "points": points,
                "applicants": applicants,
                "permits": permits
            })

        hunts.append({
            "hunt_code": hunt_code,
            "weapon": weapon,
            "unit": unit,
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