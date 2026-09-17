# export database to posts.json
# this script exports categories and clusters

import sqlite3
import json
import numpy as np
from collections import defaultdict

#DB_PATH = "../data/insights.db"
DB_PATH = "post_cluster_insights.db"

# ============================================================
# DATABASE
# ============================================================

def connect():
    return sqlite3.connect(DB_PATH)


# ============================================================
# LOAD CATEGORY MAP
# ============================================================

def load_categories():

    conn = connect()

    cur = conn.cursor()

    cur.execute("""

    SELECT
        pc.post_id,
        c.name

    FROM post_categories pc

    JOIN categories c
        ON pc.category_id = c.id

    """)

    rows = cur.fetchall()

    conn.close()

    category_map = defaultdict(list)

    for post_id, category in rows:

        category_map[post_id].append(category)

    return category_map


# ============================================================
# LOAD CLUSTERS
# ============================================================

def load_clusters():

    conn = connect()

    cur = conn.cursor()

    cur.execute("""

    SELECT
        pc.post_id,
        pc.cluster_id,
        c.label

    FROM post_clusters pc

    LEFT JOIN clusters c
        ON pc.cluster_id = c.id

    """)

    rows = cur.fetchall()

    conn.close()

    cluster_map = {}

    for post_id, cluster_id, label in rows:

        cluster_map[post_id] = {
            "id": cluster_id,
            "label": label
        }

    return cluster_map


# ============================================================
# LOAD RELATED POSTS
# ============================================================

def load_related_posts():

    conn = connect()

    cur = conn.cursor()

    # OPTIONAL TABLE:
    # related_posts(
    #   post_id,
    #   related_post_id,
    #   similarity
    # )

    try:

        cur.execute("""

        SELECT
            rp.post_id,
            rp.related_post_id,
            rp.similarity,
            p.title

        FROM related_posts rp

        JOIN posts p
            ON rp.related_post_id = p.id

        """)

        rows = cur.fetchall()

    except:

        rows = []

    conn.close()

    related_map = defaultdict(list)

    for post_id, related_id, sim, title in rows:

        related_map[post_id].append({

            "id": related_id,

            "title": title,

            "similarity": round(sim, 3)
        })

    return related_map


# ============================================================
# SIMPLE SUBTOPIC EXTRACTION
# ============================================================

def generate_subtopics(tags):

    # For now:
    # reuse top tags as subtopics

    return tags[:3]


# ============================================================
# WORD COUNT
# ============================================================

def word_count(text):

    return len(text.split())


# ============================================================
# READING TIME
# ============================================================

def reading_time_minutes(text):

    wc = word_count(text)

    return max(1, round(wc / 250))


# ============================================================
# EXPORT JSON
# ============================================================

def export_json():

    print("\nLOADING SUPPORTING DATA...\n")

    category_map = load_categories()

    cluster_map = load_clusters()

    related_map = load_related_posts()

    print("\nLOADING POSTS...\n")

    conn = connect()

    cur = conn.cursor()

    cur.execute("""

    SELECT
        id,
        url,
        title,
        date,
        content,
        summary,
        insight,
        tags,
        embedding

    FROM posts

    """)

    rows = cur.fetchall()

    conn.close()

    data = []

    total = len(rows)

    print(f"PROCESSING {total} POSTS...\n")

    for i, r in enumerate(rows):
        post_id = r[0]
        url = r[1]
        title = r[2]
        date = r[3]
        content = r[4] or ""
        summary = r[5] or ""
        insight = r[6] or ""
        tags_str = r[7] or ""
        embedding_blob = r[8]

        tags = [
            t.strip()
            for t in tags_str.split(",")
            if t.strip()
        ]

        categories = category_map.get(
            post_id,
            []
        )

        cluster = cluster_map.get(
            post_id,
            {
                "id": None,
                "label": None
            }
        )

        related_posts = related_map.get(
            post_id,
            []
        )

        subtopics = generate_subtopics(
            tags
        )

        # embedding metadata only
        embedding_dimension = None

        if embedding_blob:

            emb = np.frombuffer(
                embedding_blob,
                dtype=np.float32
            )

            embedding_dimension = len(emb)

        post_json = {
            "id": post_id,
            "url": url,
            "title": title,
            "date": date,
            "summary": summary,
            "insight": insight,
            "categories": categories,
            "subtopics": subtopics,
            "tags": tags,
            "cluster": {
                "id": cluster["id"],
                "label": cluster["label"]
            },
            "related_posts": related_posts,
            "entities": {
                "locations": [],
                "organizations": [],
                "people": [],
                "technologies": []
            },
            "metrics": {
                "word_count": word_count(
                    content
                ),
                "reading_time_minutes":
                    reading_time_minutes(
                        content
                    )
            },
            "search": {
                "embedding_model":
                    "all-MiniLM-L6-v2",
                "embedding_dimension":
                    embedding_dimension
            },
            "pipeline": {
                "version": "2.0"
            }
        }
        data.append(post_json)

        if i % 1000 == 0 and i > 0:
            print(
                f"Processed {i}/{total}"
            )

    print("\nWRITING JSON FILE...\n")

    #"../exports/posts.json",
    with open(
        "posts.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"\nEXPORTED {len(data)} POSTS"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    export_json()
