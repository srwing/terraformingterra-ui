import sqlite3

DB_PATH = "insights.db"

def connect():
    return sqlite3.connect(DB_PATH)

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    conn = connect()
    cur = conn.cursor()

    # ========================================================
    # POSTS
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        date TEXT,
        content TEXT,
        summary TEXT,
        insight TEXT,
        tags TEXT,
        embedding BLOB,
        created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ========================================================
    # CATEGORIES
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        parent_id INTEGER
    )
    """)

    # ========================================================
    # POST CATEGORIES
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_categories (
        post_id INTEGER,
        category_id INTEGER,
        UNIQUE(post_id, category_id)
    )
    """)

    # ========================================================
    # CLUSTERS
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clusters (
        id INTEGER PRIMARY KEY,
        label TEXT
    )
    """)

    # ========================================================
    # POST CLUSTERS
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_clusters (
        post_id INTEGER,
        cluster_id INTEGER,
        UNIQUE(post_id, cluster_id)
    )
    """)

    # ========================================================
    # RELATED POSTS
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS related_posts (
        post_id INTEGER,
        related_post_id INTEGER,
        similarity REAL,
        UNIQUE(post_id, related_post_id)
    )
    """)

    # ========================================================
    # ENTITIES
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
        UNIQUE(name, type)
    )
    """)

    # ========================================================
    # POST ENTITIES
    # ========================================================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_entities (
        post_id INTEGER,
        entity_id INTEGER,
        UNIQUE(post_id, entity_id)
    )
    """)

    # ========================================================
    # INDEXES
    # ========================================================

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_date
    ON posts(date)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_posts_url
    ON posts(url)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_categories_name
    ON categories(name)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_entities_name
    ON entities(name)
    """)

    conn.commit()
    conn.close()
    print("Database initialized.")

# ============================================================
# POST HELPERS
# ============================================================

def url_exists(url):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM posts WHERE url=?",
        (url,)
    )
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def insert_post(post):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO posts (
        url,
        title,
        date,
        content,
        summary,
        insight,
        tags,
        embedding
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post["url"],
        post["title"],
        post["date"],
        post["content"],
        post["summary"],
        post["insight"],
        post["tags"],
        post["embedding"]
    ))
    conn.commit()
    conn.close()

# ============================================================
# CATEGORY HELPERS
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
        "INSERT INTO categories(name) VALUES(?)",
        (name,)
    )
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return cid

def assign_post_category(
    post_id,
    category_name
):

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
# CLUSTER HELPERS
# ============================================================

def save_cluster_label(
    cluster_id,
    label
):

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO clusters (
        id,
        label
    )
    VALUES (?, ?)
    """, (
        cluster_id,
        label
    ))
    conn.commit()
    conn.close()

def assign_post_cluster(
    post_id,
    cluster_id
):

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO post_clusters (
        post_id,
        cluster_id
    )
    VALUES (?, ?)
    """, (
        post_id,
        cluster_id
    ))
    conn.commit()
    conn.close()

# ============================================================
# RELATED POSTS
# ============================================================

def insert_related_post(
    post_id,
    related_post_id,
    similarity
):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO related_posts (
        post_id,
        related_post_id,
        similarity
    )
    VALUES (?, ?, ?)
    """, (
        post_id,
        related_post_id,
        similarity
    ))

    conn.commit()
    conn.close()

# ============================================================
# ENTITY HELPERS
# ============================================================

def get_or_create_entity(
    name,
    entity_type
):

    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT id
    FROM entities
    WHERE name=?
    AND type=?
    """, (
        name,
        entity_type
    ))
    row = cur.fetchone()
    if row:
        conn.close()
        return row[0]
    cur.execute("""
    INSERT INTO entities (
        name,
        type
    )
    VALUES (?, ?)

    """, (
        name,
        entity_type
    ))

    entity_id = cur.lastrowid
    conn.commit()
    conn.close()
    return entity_id

def assign_post_entity(
    post_id,
    entity_name,
    entity_type
):

    entity_id = get_or_create_entity(
        entity_name,
        entity_type
    )
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO post_entities (
        post_id,
        entity_id
    )
    VALUES (?, ?)
    """, (
        post_id,
        entity_id
    ))

    conn.commit()
    conn.close()

# ============================================================
# QUERY HELPERS
# ============================================================

def fetch_recent_posts(limit=50):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    SELECT
        id,
        title,
        date,
        summary
    FROM posts
    ORDER BY date DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def search_posts(query):
    conn = connect()
    cur = conn.cursor()
    q = f"%{query}%"
    cur.execute("""
    SELECT
        id,
        title,
        summary
    FROM posts
    WHERE
        title LIKE ?
        OR content LIKE ?
        OR summary LIKE ?
        OR tags LIKE ?
    LIMIT 100
    """, (
        q,
        q,
        q,
        q
    ))

    rows = cur.fetchall()
    conn.close()
    return rows

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    init_db()
