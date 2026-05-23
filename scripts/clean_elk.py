import json

with open("elk_hunts_grouped.json") as f:
    data = json.load(f)

cleaned = {
    "archery": [],
    "rifle": [],
    "muzzleloader": []
}

def clean_rows(rows):
    seen = set()
    cleaned_rows = []

    for r in rows:
        key = (r["points"], r["applicants"], r["permits"])
        if key in seen:
            continue
        seen.add(key)

        odds = None
        if r["permits"] > 0:
            odds = round(r["applicants"] / r["permits"], 2)

        cleaned_rows.append({
            "points": r["points"],
            "applicants": r["applicants"],
            "permits": r["permits"],
            "odds": odds
        })

    return sorted(cleaned_rows, key=lambda x: -x["points"])


for weapon in data:
    for hunt in data[weapon]:

        cleaned[weapon].append({
            "hunt_code": hunt["hunt_code"],
            "data": clean_rows(hunt["data"])
        })


with open("elk_hunts_clean.json", "w") as f:
    json.dump(cleaned, f, indent=2)

print("DONE: elk_hunts_clean.json created")