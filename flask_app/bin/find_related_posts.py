# This script load all posts and their embeddings directly from the database and then calculate related posts.

import sqlite3
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Define the database path
DB_PATH = "/content/drive/MyDrive/globalwarming-arclein2/clustering/insights.db"

# Database connection helper
def connect():
    return sqlite3.connect(DB_PATH)

# Function to initialize all necessary tables (copied for self-contained script)
def init_db_tables():
    conn = connect()
    cur = conn.cursor()

    # Create posts table (required for loading data)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        embedding BLOB
    )
    """)

    # Create categories table (needed if using other functions, but good to have complete init)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        parent_id INTEGER
    )
    """)

    # Create post_categories table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_categories (
        post_id INTEGER,
        category_id INTEGER,
        UNIQUE(post_id, category_id)
    )
    """)

    conn.commit()
    conn.close()
    print("Database tables initialized (or already exist).")

# Function to load posts and embeddings (copied for self-contained script)
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

# Function to find related posts (copied from previous cell)
def find_related_posts(posts, top_k=5):
    if not posts:
        return {}

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

        # Sort by similarity score in descending order
        scores = sorted(
            scores,
            key=lambda x: x[1],
            reverse=True
        )

        related_posts = []

        # Skip the first element as it's the post itself (score 1.0)
        for idx, score in scores[1:top_k+1]:

            related_posts.append({
                "post_id": posts[idx]["id"],
                "title": posts[idx]["title"],
                "score": float(score)
            })

        related[p["id"]] = related_posts

    return related

def run_related_posts_script():
    print("\nINITIALIZING DATABASE TABLES...\n")
    #init_db_tables() # Ensure tables exist

    print("\nLOADING POSTS...\n")
    posts = load_posts()
    print(f"Loaded {len(posts)} posts with embeddings.")

    if posts:
        print("\nGENERATING RELATED POSTS...\n")
        related = find_related_posts(
            posts,
            top_k=5
        )

        if related:
            print("\nEXAMPLE RELATED POSTS FOR A RANDOM POST:\n")
            # Get a random post ID to show related posts
            first_post_id = list(related.keys())[0]
            original_post_title = next(p['title'] for p in posts if p['id'] == first_post_id)
            print(f"Original Post: {original_post_title}\n")

            for r in related[first_post_id]:
                print(
                    f"  - Related: {r['title']}\n    SCORE: {round(r['score'], 3)}"
                )
        else:
            print("No related posts found (possibly due to lack of posts or embeddings).")
    else:
        print("No posts loaded from the database to find related items.")

    print("\nRelated posts script finished.\n")

if __name__ == "__main__":
    run_related_posts_script()