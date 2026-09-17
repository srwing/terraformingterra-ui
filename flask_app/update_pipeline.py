#This script performs a full incremental update pipeline:
#    discovers new blog posts
#    skips existing posts
#    scrapes only new URLs
#    generates summaries/tags/embeddings
#    assigns categories
#    assigns clusters
#    generates related posts
#    updates exports
#    rebuilds clean_labels.json

import json
import numpy as np
import joblib

from sklearn.metrics.pairwise import cosine_similarity
from sitemap import discover_all_urls
from scraper import scrape_all_posts
from processor import process_post
from database import (
    init_db,
    url_exists,
    insert_post,
    assign_post_category,
    assign_post_cluster,
    insert_related_post,
    connect
)
#from export_json import export_json
#from build_clean_labels import main as build_clean_labels

# ============================================================
# CATEGORY RULES
# ============================================================
CATEGORY_RULES = {
    "Climate Science": [
        "climate", "warming",
        "temperature", "carbon",
        "co2", "ice", "glacier"
    ],

    "Energy": [
        "energy", "oil",
        "gas", "solar",
        "wind", "battery",
        "nuclear"
    ],

    "Economics": [
        "economy", "inflation",
        "finance", "bank",
        "market"
    ],

    "Technology": [
        "technology", "ai",
        "software", "computer"
    ],

    "Environment": [
        "forest", "water",
        "pollution",
        "ecosystem"
    ]
}

# ============================================================
# LOAD EXISTING POSTS
# ============================================================
def load_existing_embeddings():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT
        id,
        title,
        embedding
    FROM posts
    WHERE embedding IS NOT NULL
    """)
    rows = cur.fetchall()
    conn.close()
    posts = []
    for r in rows:
        emb = np.frombuffer(
            r[2],
            dtype=np.float32
        )
        posts.append({
            "id": r[0],
            "title": r[1],
            "embedding": emb
        })
    return posts

# ============================================================
# RULE-BASED CATEGORIES
# ============================================================

def classify_categories(text):
    text = text.lower()
    matched = []
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in text:
                matched.append(category)
                break
    return matched

# ============================================================
# ASSIGN CATEGORIES
# ============================================================

def assign_categories(post_id, content):
    categories = classify_categories(
        content
    )
    for c in categories:
        assign_post_category(
            post_id,
            c
        )
    return categories

# ============================================================
# LOAD CLUSTER MODEL
# ============================================================

def load_cluster_model():
    try:
        model = joblib.load(
            "../models/kmeans.pkl"
        )
        print("Cluster model loaded.")
        return model
    except:
        print(
            "No cluster model found."
        )
        return None

# ============================================================
# ASSIGN CLUSTER
# ============================================================

def assign_cluster(
    post_id,
    embedding,
    kmeans
):
    if not kmeans:
        return None

    cluster_id = int(
        kmeans.predict([embedding])[0]
    )

    assign_post_cluster(
        post_id,
        cluster_id
    )
    return cluster_id

# ============================================================
# RELATED POSTS
# ============================================================

def generate_related_posts(
    new_post,
    existing_posts,
    top_k=5
):
    if not existing_posts:
        return

    new_emb = np.array([
        new_post["embedding_array"]
    ])

    existing_embs = np.array([
        p["embedding"]
        for p in existing_posts
    ])

    sims = cosine_similarity(
        new_emb,
        existing_embs
    )[0]

    ranked = sorted(
        zip(existing_posts, sims),
        key=lambda x: x[1],
        reverse=True
    )[:top_k]

    for post, score in ranked:
        insert_related_post(
            new_post["id"],
            post["id"],
            float(score)
        )

# ============================================================
# FETCH INSERTED POST ID
# ============================================================

def get_post_id(url):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM posts WHERE url=?",
        (url,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

# ============================================================
# MAIN UPDATE PIPELINE
# ============================================================

def main():
    print("\n===================================")
    print("INCREMENTAL UPDATE PIPELINE")
    print("===================================\n")

    # ========================================================
    # INIT DB
    # ========================================================

    init_db()
    # ========================================================
    # DISCOVER URLS
    # ========================================================

    print("Discovering blog URLs...\n")
    urls = discover_all_urls()
    print(
        f"Discovered {len(urls)} URLs"
    )

    # ========================================================
    # FIND NEW URLS
    # ========================================================

    new_urls = []
    for url in urls:
        if not url_exists(url):
            new_urls.append(url)
    print(
        f"\nNEW POSTS FOUND: {len(new_urls)}"
    )

    if not new_urls:
        print("\nNo updates needed.")
        return

    # ========================================================
    # SCRAPE NEW POSTS
    # ========================================================

    print("\nScraping new posts...\n")

    raw_posts = scrape_all_posts(
        new_urls,
        workers=10
    )

    print(
        f"Scraped {len(raw_posts)} posts"
    )

    # ========================================================
    # LOAD EXISTING EMBEDDINGS
    # ========================================================

    existing_posts = load_existing_embeddings()

    print(
        f"Loaded {len(existing_posts)} "
        f"existing embeddings"
    )

    # ========================================================
    # LOAD CLUSTER MODEL
    # ========================================================

    kmeans = load_cluster_model()

    # ========================================================
    # PROCESS POSTS
    # ========================================================

    processed = 0

    for raw in raw_posts:
        try:
            # ================================================
            # NLP PROCESSING
            # ================================================

            enriched = process_post(raw)

            # embedding array version

            embedding_array = np.frombuffer(
                enriched["embedding"],
                dtype=np.float32
            )

            enriched["embedding_array"] = (
                embedding_array
            )

            # ================================================
            # INSERT POST
            # ================================================

            insert_post(enriched)

            post_id = get_post_id(
                enriched["url"]
            )

            if not post_id:
                continue

            enriched["id"] = post_id

            # ================================================
            # ASSIGN CATEGORIES
            # ================================================

            categories = assign_categories(
                post_id,
                enriched["content"]
            )

            # ================================================
            # ASSIGN CLUSTER
            # ================================================

            cluster_id = assign_cluster(
                post_id,
                embedding_array,
                kmeans
            )

            # ================================================
            # RELATED POSTS
            # ================================================

            generate_related_posts(
                enriched,
                existing_posts
            )

            # ================================================
            # ADD TO EXISTING EMBEDDINGS
            # ================================================

            existing_posts.append({
                "id": post_id,
                "title": enriched["title"],
                "embedding":
                    embedding_array
            })

            processed += 1
            print(
                f"\nProcessed: "
                f"{enriched['title']}"
            )
            print(
                f"Categories: {categories}"
            )
            print(
                f"Cluster: {cluster_id}"
            )
        except Exception as e:
            print(
                f"\nERROR PROCESSING POST:\n{e}"
            )

    # ========================================================
    # EXPORT JSON
    # ========================================================

    #print("\nExporting posts.json...\n")
    #export_json()

    # ========================================================
    # BUILD CLEAN LABELS
    # ========================================================

    #print("\nBuilding clean_labels.json...\n")
    #build_clean_labels()

    print("\n===================================")
    print("UPDATE COMPLETE")
    print("===================================\n")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    main()
