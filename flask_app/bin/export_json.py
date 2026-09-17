import sqlite3
import json

DB_PATH = "../data/insights.db"

conn = sqlite3.connect(DB_PATH)

cur = conn.cursor()

cur.execute("""
SELECT
    id,
    url,
    title,
    date,
    summary,
    insight,
    tags
FROM posts
""")

rows = cur.fetchall()

data = []

for r in rows:

    data.append({

        "id": r[0],

        "url": r[1],

        "title": r[2],

        "date": r[3],

        "summary": r[4],

        "insight": r[5],

        "tags": r[6].split(",") if r[6] else []
    })

with open(
    "../exports/posts.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False
    )

print("Exported posts.json")
