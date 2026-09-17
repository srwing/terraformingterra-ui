import sqlite3
import numpy as np
from collections import defaultdict
from sklearn.cluster import KMeans

# Define the database path
DB_PATH = "/content/drive/MyDrive/globalwarming-arclein.blogspot/Data/insights.db"

# Database connection helper
def connect():
    return sqlite3.connect(DB_PATH)

# Function to load posts and embeddings
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

# Function to perform clustering
def cluster_posts(posts, n_clusters=20):
    embeddings = np.array([
        p["embedding"]
        for p in posts
    ])

    print(f"Running KMeans clustering with {n_clusters} clusters...")

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10 # Added to suppress future warning
    )

    cluster_ids = kmeans.fit_predict(
        embeddings
    )

    conn = connect()
    cur = conn.cursor()

    # Clear existing post_clusters to avoid duplicates if run multiple times
    cur.execute("DELETE FROM post_clusters")
    cur.execute("DELETE FROM clusters")
    conn.commit()

    # Insert cluster labels (optional, but good practice)
    for i in range(n_clusters):
        cur.execute("INSERT OR IGNORE INTO clusters (id, label) VALUES (?, ?)", (i, f"Cluster {i}"))
    conn.commit()

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

# Function to inspect clusters
def inspect_clusters(posts, cluster_ids):
    grouped = defaultdict(list)
    for i, cid in enumerate(cluster_ids):
        grouped[cid].append(
            posts[i]["title"]
        )

    print("\n================ CLUSTERS ================\n")

    for cid, titles in sorted(grouped.items()):
        print(f"\nCLUSTER {cid} (contains {len(titles)} posts)")
        for t in titles[:5]: # Display top 5 titles for brevity
            print("  -", t[:120])


def run_clustering_script():
    print("\nLOADING POSTS...\n")
    posts = load_posts()
    print(f"Loaded {len(posts)} posts")

    # Adjust n_clusters as needed
    cluster_ids = cluster_posts(posts, n_clusters=20)

    inspect_clusters(posts, cluster_ids)
    print("\nClustering script finished.\n")

    ###########
    #find_related_posts(

if __name__ == "__main__":
    run_clustering_script()