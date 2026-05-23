import pandas as pd

INPUT = "processed_data/draw_reality_engine.csv"
OUTPUT = "processed_data/draw_reality_engine_clean.csv"

df = pd.read_csv(INPUT, low_memory=False)

# remove rows with no applicants AND no permits
df = df[
    ~(
        (df["eligible_applicants"] <= 0) &
        (df["total_permits"] <= 0)
    )
]

# normalize status
df["status"] = df["status"].fillna("")

# compute draw odds
df["p_draw_percent"] = (
    df["total_drawn"] / df["eligible_applicants"]
) * 100

# clamp to 100%
df["p_draw_percent"] = df["p_draw_percent"].clip(upper=100)

# remove impossible rows
df = df[df["eligible_applicants"] >= 0]

# sort nicely
df = df.sort_values(
    ["hunt_code", "residency", "points"],
    ascending=[True, True, False]
)

df.to_csv(OUTPUT, index=False)

print()
print("WROTE:", OUTPUT)
print("ROWS:", len(df))
print("HUNTS:", df["hunt_code"].nunique())
print()

print(df.head(30).to_string())