
# crawler/category_pipeline.py

import sqlite3
import numpy as np
import re
from collections import defaultdict

from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

DB_PATH = "../data/insights.db"
#DB_PATH = "/home/wing/Desktop/TerraFormingTerra/Python code and database/1_major_update/data/insights051826.db"
# ============================================================
# TOP-LEVEL CATEGORY RULES
# ============================================================

CATEGORY_RULES = {

    "Climate Science": [
        "climate", "warming", "temperature",
        "co2", "carbon", "glacier",
        "ice", "arctic", "atmosphere"
    ],

    "Energy": [
        "energy", "oil", "gas",
        "solar", "wind", "battery",
        "nuclear", "fusion", "reactor"
    ],

    "Agriculture": [
        "agriculture", "crop", "soil",
        "farm", "food", "fertility",
        "irrigation"
    ],

    "Economics": [
        "economy", "economic", "market",
        "finance", "inflation", "debt",
        "trade", "bank"
    ],

    "Geopolitics": [
        "war", "china", "russia",
        "military", "government",
        "conflict", "nato"
    ],

    "Technology": [
        "technology", "ai", "robot",
        "computer", "software",
        "internet", "automation"
    ],

    "Health": [
        "health", "disease", "virus",
        "medical", "vaccine",
        "nutrition"
    ],

    "Environment": [
        "pollution", "forest", "water",
        "ecosystem", "species",
        "biodiversity"
    ],

    "Archaeology": [
        "ancient", "civilization",
        "archaeology", "pyramid",
        "artifact", "historical"
    ],

    "Future Forecasting": [
        "future", "prediction",
        "forecast", "scenario",
        "collapse", "transition"
    ]
}

# ============================================================
# DATABASE HELPERS
# ============================================================

def connect():
    return sqlite3.connect(DB_PATH)


def init_category_tables():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        parent_id INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_categories (
        post_id INTEGER,
        category_id INTEGER,
        UNIQUE(post_id, category_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clusters (
        id INTEGER PRIMARY KEY,
        label TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_clusters (
        post_id INTEGER,
        cluster_id INTEGER
    )
    """)

    conn.commit()
    conn.close()


# ============================================================
# CATEGORY INSERTION
# ============================================================

def get_or_create_category(name):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM categories WHERE name=?",
        (name,)
    )
    row = cur.fetchone()
    if row:
        conn.close()
        return row[0]

    cur.execute(
        "INSERT INTO categories (name) VALUES (?)",
        (name,)
    )

    category_id = cur.lastrowid
    conn.commit()
    conn.close()
    return category_id


def assign_post_category(post_id, category_name):
    category_id = get_or_create_category(
        category_name
    )

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO post_categories (
        post_id,
        category_id
    )
    VALUES (?, ?)
    """, (
        post_id,
        category_id
    ))

    conn.commit()
    conn.close()


# ============================================================
# RULE-BASED CLASSIFICATION
# ============================================================

def classify_categories(text):
    text_lower = text.lower()
    matched = []

    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(category)
                break

    return matched


# ============================================================
# LOAD POSTS + EMBEDDINGS
# ============================================================

def load_posts():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        id,
        title,
        content,
        embedding
    FROM posts
    WHERE embedding IS NOT NULL
    """)

    rows = cur.fetchall()
    conn.close()
    posts = []

    for r in rows:
        emb = np.frombuffer(
            r[3],
            dtype=np.float32
        )

        posts.append({
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "embedding": emb
        })

    return posts


# ============================================================
# APPLY RULE-BASED CATEGORIES
# ============================================================

def categorize_posts(posts):

    for p in posts:

        categories = classify_categories(
            p["content"]
        )

        for c in categories:

            assign_post_category(
                p["id"],
                c
            )

    print("Rule-based categories assigned.")


# ============================================================
# CLUSTERING
# ============================================================

def cluster_posts(posts, n_clusters=20):

    embeddings = np.array([
        p["embedding"]
        for p in posts
    ])

    print("Running KMeans clustering...")

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42
    )

    cluster_ids = kmeans.fit_predict(
        embeddings
    )

    conn = connect()

    cur = conn.cursor()

    for i, post in enumerate(posts):

        cluster_id = int(cluster_ids[i])

        cur.execute("""
        INSERT INTO post_clusters (
            post_id,
            cluster_id
        )
        VALUES (?, ?)
        """, (
            post["id"],
            cluster_id
        ))

    conn.commit()

    conn.close()

    print("Clusters assigned.")

    return cluster_ids


# ============================================================
# CLUSTER INSPECTION
# ============================================================

def inspect_clusters(posts, cluster_ids):

    grouped = defaultdict(list)

    for i, cid in enumerate(cluster_ids):

        grouped[cid].append(
            posts[i]["title"]
        )

    print("\n================ CLUSTERS ================\n")

    for cid, titles in grouped.items():

        print(f"\nCLUSTER {cid}")

        for t in titles[:10]:

            print("  ", t[:120])


# ============================================================
# RELATED POSTS
# ============================================================

def find_related_posts(posts, top_k=5):

    embeddings = np.array([
        p["embedding"]
        for p in posts
    ])

    sim = cosine_similarity(
        embeddings
    )

    related = {}

    for i, p in enumerate(posts):

        scores = list(
            enumerate(sim[i])
        )

        scores = sorted(
            scores,
            key=lambda x: x[1],
            reverse=True
        )

        related_posts = []

        for idx, score in scores[1:top_k+1]:

            related_posts.append({
                "post_id": posts[idx]["id"],
                "title": posts[idx]["title"],
                "score": float(score)
            })

        related[p["id"]] = related_posts

    return related


# ============================================================
# MAIN
# ============================================================

def main():
    print("\nINITIALIZING CATEGORY TABLES...\n")
    init_category_tables()
    print("\nLOADING POSTS...\n")
    posts = load_posts()
    print(f"Loaded {len(posts)} posts")
    print("\nASSIGNING RULE-BASED CATEGORIES...\n")
    categorize_posts(posts)

    print("\nCLUSTERING POSTS...\n")

    #Clustering is currently disabled to save time during development. You can re-enable it by uncommenting the lines below.
    #cluster_ids = cluster_posts(
    #    posts,
    #    n_clusters=20
    #)
    #
    #inspect_clusters(
    #    posts,
    #    cluster_ids
    #)
    #print("\nGENERATING RELATED POSTS...\n")
    #related = find_related_posts(
    #    posts,
    #    top_k=5
    #)
    #print("\nEXAMPLE RELATED POSTS:\n")
    #first_key = next(iter(related))
    #for r in related[first_key]:
    #    print(
    #        r["title"],
    #        " SCORE:",
    #        round(r["score"], 3)
    #    )

    print("\nDONE.\n")

if __name__ == "__main__":
    main()
