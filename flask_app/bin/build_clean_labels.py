import json

INPUT_FILE = "../exports/posts.json"
OUTPUT_FILE = "../site/clean_labels.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    posts = json.load(f)

clean = {}

for post in posts:

    clean[post["url"]] = {

        "summary":
            post.get("summary", ""),

        "insight":
            post.get("insight", ""),

        "categories":
            post.get("categories", []),

        "tags":
            post.get("tags", [])
    }

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        clean,
        f,
        indent=2,
        ensure_ascii=False
    )

print("Built clean_labels.json")
