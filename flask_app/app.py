from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import numpy as np
import os
import threading
import subprocess

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

embedding_matrix = None
embedding_post_ids = None
# Initialize the model globally if it's going to be used multiple times
# This can be slow, consider lazy loading or a more robust solution for production
model = None

app = Flask(__name__)
CORS(app)


# 1. Initialize the Limiter
limiter = Limiter(
    get_remote_address,               # Identifies the visitor by their IP address
    app=app,
    default_limits=["200 per day"],   # Global limit for all routes
    storage_uri="memory://",          # Keeps track of hits in server memory
)
limiter.enabled = False
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "status": "error",
        "message": f"Too many requests! Slow down. Cooldown active: {e.description}"
    }), 429

# Database path changed for local environment
DATABASE = 'insights.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=30)
    #allocate morememory for SQLite caching (e.g., 10000 pages)
    conn.execute("PRAGMA cache_size = -10000;")
    conn.row_factory = sqlite3.Row
    return conn

def load_embeddings():
    global embedding_matrix
    global embedding_post_ids

    print("Loading binary BLOB embeddings into memory...")

    start = time.time()
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT id, embedding
        FROM posts
        WHERE embedding IS NOT NULL
    """).fetchall()
#removed ??          AND embedding != ''

    conn.close()

    embedding_post_ids = []
    vectors = []

    for row in rows:
        try:
            #vectors.append(
            #    json.loads(row["embedding"])
            #)
            blob_data = row["embedding"]
            if blob_data:
                vector = np.frombuffer(blob_data, dtype=np.float32)
                vectors.append(vector)  
                embedding_post_ids.append(
                    row["id"]
                )
        except Exception:
            print(f"Failed to load embedding for post ID {row['id']}. Skipping this entry.")
            pass
    if not vectors:
        print("No valid embeddings were successfully loaded. Matrix is empty.")
        embedding_matrix=None
        return

    embedding_matrix = np.array(
        vectors,
        dtype=np.float32
    )


    embedding_matrix = (
        embedding_matrix
        / np.linalg.norm(
            embedding_matrix,
            axis=1,
            keepdims=True
        )
    )
    elapsed = time.time() - start

    print(
        f"Loaded {len(vectors)} embeddings "
        f"in {elapsed:.2f} seconds"
    )

@app.route('/')
def home():
    return """
    <html>

    <head>

    <title>Insights Search</title>

    <style>

    body {
        font-family: "MS Sans Serif", Geneva, sans-serif; /* Matches typical vintage Blogspot typography layouts */
        background: transparent; /* Allows your blog's true background color to show through */
        max-width: 100%;
        margin: 0;
        padding: 10px;
        color: #333333;
   }

    input, select {
        width: 100%;
        padding: 12px;
        font-size: 18px;
        margin-bottom: 10px;
    }

    .card {
        border: 1px solid #e0e0e0;
        padding: 20px;
        margin-top: 15px;
        border-radius: 4px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    /* Match the exact blue anchor styling used in Blogger gadgets */
    .card h2 a {
        color: #2266bb; 
        text-decoration: none;
        font-weight: bold;
    }

    .card h2 a:hover {
        color: #33aaff;
        text-decoration: underline;
    }

    /* Style the custom AI summary badge beautifully */
    .insight {
        background: #f4f8ff;
        padding: 12px;
        border-left: 4px solid #2266bb;
        border-radius: 4px;
        font-size: 14px;
        margin-top: 10px;
    }
    .spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(0, 0, 0, 0.1);
        border-radius: 50%;
        border-top-color: #3498db; /* Matches your accent color */
        animation: spin 1s ease-in-out infinite;
        vertical-align: middle;
        margin-right: 8px;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    /* Container to pull the search box and dropdown side-by-side */
    .search-controls {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }

    /* 1. Make the search textbox stretch to fill all remaining room */
    .search-controls input {
        flex: 1; 
        margin-bottom: 0;
        box-sizing: border-box;
    }

    /* 2. Force the dropdown to only be as wide as its widest text option */
    .search-controls select {
        flex: 0 1 auto; /* Don't grow (0), allow shrinking (1), use natural width (auto) */
        width: auto;    /* Sizes the element strictly to its content */
        min-width: 160px; /* Optional: Sets a safe minimum width so it doesn't look squished on empty searches */
        margin-bottom: 0;
        box-sizing: border-box;
    }

    /* Wrapper for the checkbox to keep it neatly spaced below */
    .checkbox-container {
        margin-top: 10px;
        margin-bottom: 15px;
        display: block;
    }

    .checkbox-container input[type="checkbox"] {
        width: auto;
        margin-right: 5px;
        vertical-align: middle;
    }

    /* Mobile responsive tweak: stacks them vertically on small screens */
    @media (max-width: 600px) {
        .search-controls {
            flex-direction: column;
            gap: 10px;
        }
        /* Allow the dropdown to scale back to 100% width on mobile layouts */
        .search-controls select {
            width: 100%;
            flex: 1;
        }
    }

    </style>
    </head>
    <body>

    <h1>Insights Search</h1>

    <div class="search-controls">
        <input
            id='searchBox'
            placeholder='Search...'
        >

        <select id='categoryDropdown'>
            <option value=''>All Categories</option>
        </select>
    </div>

    <label class="checkbox-container">
        <input type='checkbox' id='semantic'>
        Semantic Search
    </label>
    <div class="update-section" style="margin-top: 20px; text-align: center;">
    <button id="updateBtn" class="search-btn" onclick="triggerUpdate()">
        Update Database
    </button>
    <p id="updateStatus" style="font-size: 14px; margin-top: 8px; color: #666; font-weight: 600;"></p>
</div>

    <div id="loader" style="display: none; text-align: center; margin: 15px 0;">
        <span class="spinner"></span> Loading...
    </div>
    <div id='results'><p>Enter a search term above.</p></div>
<script>
    // Global variable to keep track of the current request sequence ID
    let currentSearchId = 0;

    function toggleLoader(show) {
        document.getElementById('loader').style.display = show ? 'block' : 'none';
    }

    async function searchPosts() {
        const q = document.getElementById('searchBox').value.trim();
        const category = document.getElementById('categoryDropdown').value;
        const semantic = document.getElementById('semantic').checked;

        if (semantic && q.length > 0 && q.length < 3) {
            document.getElementById('results').innerHTML = '<p>Semantic search requires at least 3 characters.</p>';
            return;
        }

        if (!category && q.length === 1) {
            document.getElementById('results').innerHTML = '<p>Enter at least 2 characters or select a category.</p>';
            return;
        }

        toggleLoader(true);
        
        // Capture a unique ID for this specific search loop run
        const mySearchId = ++currentSearchId;

        try {
            const response = await fetch(
                `/search?q=${encodeURIComponent(q)}&semantic=${semantic}&category=${encodeURIComponent(category)}`
            );
            
            if (!response.ok) throw new Error("Network error");
            const posts = await response.json();

            // � FIX: If a newer search has already fired, discard this outdated payload response!
            if (mySearchId !== currentSearchId) return;

            let html = '';
            if (posts.length === 0) {
                html = '<p style="text-align:center; color:#999; margin-top:20px;">No matching articles found.</p>';
            } else {
                posts.forEach(post => {
                    html += `
                    <div class="card">
                        <h2><a href="${post.url}" target="_blank" rel="noopener noreferrer">${post.title}</a></h2>
                        <p>${post.summary || ''}</p>
                        <div class="insight">${post.insight || ''}</div>
                    </div>
                    `;
                });
            }
            document.getElementById('results').innerHTML = html;
        } catch (err) {
            console.error("Search failed:", err);
            if (mySearchId === currentSearchId) {
                document.getElementById('results').innerHTML = '<p>Error executing search.</p>';
            }
        } finally {
            if (mySearchId === currentSearchId) toggleLoader(false);
        }
    }

    async function loadCategories() {
        const q = document.getElementById('searchBox').value.trim();
        const dropdown = document.getElementById('categoryDropdown');
        const semantic = document.getElementById('semantic').checked;
        const currentSelection = dropdown.value;

        try {
            const response = await fetch(`/categories?q=${encodeURIComponent(q)}&semantic=${semantic}`);
            const categories = await response.json();
            
            dropdown.innerHTML = '<option value="">All Categories</option>';
            categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.name;
                option.textContent = cat.count > 0 ? `${cat.name} (${cat.count})` : cat.name;
                if (cat.name === currentSelection) option.selected = true;
                dropdown.appendChild(option);
            });
        } catch (err) {
            console.error("Failed to update categories:", err);
        }
    }

    // Event Listeners with optimized sequence loading
    let searchTimeout;
    document.getElementById('searchBox').addEventListener('input', () => {
        clearUpdateStatus();
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            await loadCategories();
            await searchPosts();
        }, 450);
    });

    document.getElementById('semantic').addEventListener('change', async () => {
        clearUpdateStatus();
        await loadCategories();
        await searchPosts();
    });

    document.getElementById('categoryDropdown').addEventListener('change', async () => {
        clearUpdateStatus();
        await searchPosts(); // Changing selection shouldn't loop-refresh its own menu structure
    });

    async function startSearchEngine() {
        await loadCategories();
        await searchPosts();
    }
    startSearchEngine();

    async function triggerUpdate() {
        const btn = document.getElementById('updateBtn');
        const statusText = document.getElementById('updateStatus');
        
        btn.disabled = true; // Disable button immediately to prevent double submissions
        toggleLoader(true); 
        statusText.textContent = "Triggering background update script... please wait.";
        statusText.style.color = "#333";

        try {
            const response = await fetch('/api/run-update', { method: 'POST' });
            const data = await response.json();
            
            if (response.status === 429) {
                statusText.textContent = "Blocked: " + (data.message || "Too many requests.");
                statusText.style.color = "red";
                btn.disabled = false;
                toggleLoader(false);
                return;
            }

            if (response.ok) {
                statusText.textContent = data.message;
                statusText.style.color = "orange"; // Indicate it's processing
                
                // Start polling the server to check when the thread actually finishes
                pollUpdateStatus();
            } else {
                statusText.textContent = "Failed: " + (data.message || "Unknown error");
                statusText.style.color = "red";
                btn.disabled = false;
                toggleLoader(false);
            }
        } catch (error) {
            statusText.textContent = "A network error occurred.";
            statusText.style.color = "red";
            btn.disabled = false;
            toggleLoader(false);
        }
    }

    // Helper function to poll the backend status
    function pollUpdateStatus() {
        const btn = document.getElementById('updateBtn');
        const statusText = document.getElementById('updateStatus');

        const interval = setInterval(async () => {
            try {
                const response = await fetch('/api/update-status');
                const data = await response.json();

                if (data.status === "success") {
                    clearInterval(interval); // Stop checking
                    statusText.textContent = "Success: " + data.message;
                    statusText.style.color = "green";
                    
                    // Re-enable UI components
                    toggleLoader(false);
                    btn.disabled = false;
                    
                    // Refresh the search view so the user sees any brand new items instantly
                    setTimeout(startSearchEngine, 1000);
                } else if (data.status === "error") {
                    clearInterval(interval); // Stop checking
                    statusText.textContent = "Failed: " + data.message;
                    statusText.style.color = "red";
                    
                    toggleLoader(false);
                    btn.disabled = false;
                } else {
                    // It is still "running", update the UI with whatever message the backend reports
                    statusText.textContent = data.message;
                }
            } catch (err) {
                console.error("Error polling update status:", err);
            }
        }, 2000); // Check every 2 seconds
    }
    function clearUpdateStatus() {
        const statusText = document.getElementById('updateStatus');
        // Only clear it if it's currently showing a final state (Success or Failed)
        // We don't want to clear it if it's actively "Running..."
        if (statusText.textContent.startsWith("Success") || statusText.textContent.startsWith("Failed")) {
            statusText.textContent = "";
        }
    }
    </script>
    </body>

    </html>
    """

@app.route('/categories')
def get_categories():
    conn = get_db_connection()
    query = request.args.get('q', '').strip()
    semantic = request.args.get('semantic', 'false')

    # Case 1: Semantic search is enabled and there is a query text
    if semantic == 'true' and query:
        # Instead of calculating embeddings all over again, we fetch the IDs 
        # from the global model or calculate them once. 
        # For an exact match with your /search results, we compute the matching IDs:
        if model is not None and embedding_matrix is not None:
            query_embedding = model.encode(query).astype(np.float32)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            similarities = cosine_similarity([query_embedding], embedding_matrix)[0]
            
            top_n = min(20, len(similarities))
            top_indices = np.argsort(similarities)[::-1][:top_n]
            top_post_ids = [int(embedding_post_ids[idx]) for idx in top_indices]
            
            if top_post_ids:
                placeholders = ",".join(["?"] * len(top_post_ids))
                sql = f"""
                    SELECT c.id, c.name, COUNT(pc.post_id) as post_count
                    FROM categories c
                    LEFT JOIN post_categories pc ON c.id = pc.category_id
                    WHERE pc.post_id IN ({placeholders})
                    GROUP BY c.id, c.name
                    ORDER BY c.name ASC
                """
                categories = conn.execute(sql, top_post_ids).fetchall()
            else:
                categories = []
        else:
            categories = []

    # Case 2: Standard keyword text search (FTS match)
    elif query:
        # Fetch the matching row IDs from FTS first
        fts_posts = conn.execute(
            "SELECT rowid FROM posts_fts WHERE posts_fts MATCH ?",
            (query + '*',)
        ).fetchall()
        fts_ids = [row["rowid"] for row in fts_posts]

        if fts_ids:
            placeholders = ",".join(["?"] * len(fts_ids))
            sql = f"""
                SELECT c.id, c.name, COUNT(pc.post_id) as post_count
                FROM categories c
                LEFT JOIN post_categories pc ON c.id = pc.category_id
                WHERE pc.post_id IN ({placeholders})
                GROUP BY c.id, c.name
                ORDER BY c.name ASC
            """
            categories = conn.execute(sql, fts_ids).fetchall()
        else:
            categories = []
    # Case 3: Empty search box / page initialization
    else:
        sql = """
            SELECT c.id, c.name, COUNT(pc.post_id) as post_count
            FROM categories c
            LEFT JOIN post_categories pc ON c.id = pc.category_id
            GROUP BY c.id, c.name
            ORDER BY c.name ASC
        """
        categories = conn.execute(sql).fetchall()

    conn.close()

    return jsonify([
        {'name': cat['name'], 'count': cat['post_count']} 
        for cat in categories
    ])

####################################
# update script 
# Global variable to track update state
UPDATE_STATUS = {
    "status": "idle",       # Can be: idle, running, success, error
    "message": ""
}
def run_script_in_background():
    global UPDATE_STATUS
    try:
        print("Background database update started...")
        subprocess.run(['python', 'update_database.py'], check=True)
        
        # � CRITICAL: Reload your embeddings into memory after the database updates!
        # Otherwise, semantic search will be using stale vector lengths.
        load_embeddings() 

# Update state to success[cite: 1]
        UPDATE_STATUS["status"] = "success"
        UPDATE_STATUS["message"] = "Database and embeddings successfully updated!"
        print("Database and global embeddings updated successfully!")
    except subprocess.CalledProcessError:
        UPDATE_STATUS["status"] = "error"
        UPDATE_STATUS["message"] = "Script execution failed."
        print("Background script execution failed.")
    except Exception as e:
        UPDATE_STATUS["status"] = "error"
        UPDATE_STATUS["message"] = f"Error reloading embeddings: {e}"
        print(f"Error reloading embeddings: {e}")

@app.route('/api/run-update', methods=['POST'])
@limiter.limit("3 per hour")
def run_update():
    global UPDATE_STATUS
# Don't start a new update if one is already running
    if UPDATE_STATUS["status"] == "running":
        return jsonify({"status": "error", "message": "An update is already in progress."}), 400

    # Reset status to running[cite: 1]
    UPDATE_STATUS["status"] = "running"
    UPDATE_STATUS["message"] = "Running background update script..."

    # Start the script safely in a separate thread[cite: 1]
    thread = threading.Thread(target=run_script_in_background)
    thread.start()
    
    return jsonify({
        "status": "success", 
        "message": "Database update triggered in background. This will take a moment."
    }), 200
# NEW ROUTE: Frontend will poll this endpoint to see if the thread is done
@app.route('/api/update-status', methods=['GET'])
def get_update_status():
    global UPDATE_STATUS
    return jsonify(UPDATE_STATUS)

@app.route('/search')
def search():
    conn = get_db_connection()

    query = request.args.get('q', '')
    semantic = request.args.get('semantic', 'false')
    category = request.args.get('category', '')
    # 1. Initialize variables cleanly
    posts = []
    params = []
    print(
        f"SEARCH CALLED: query='{query}' "
        f"semantic='{semantic}' "
        f"category='{category}'",
        flush=True
    )

    sql_query = """
    SELECT p.*
    FROM posts p
    LEFT JOIN categories c ON p.category = c.name
    WHERE 1=1
    """

    params = []

    #
    # SEMANTIC SEARCH
    #
    print(
        f"semantic={semantic}, "
        f"query='{query}', "
        f"model={model is not None}, "
        f"matrix={embedding_matrix is not None}",
        flush=True
    )
    if (
        semantic == 'true'
        and query
        and model is not None
        and embedding_matrix is not None
    ):
        # Generate embedding for the search term
        query_embedding = model.encode(query).astype(np.float32)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # Compute similarities
        similarities = cosine_similarity(
            [query_embedding], embedding_matrix
        )[0]

        # Get top matching database row IDs
        top_n = min(20, len(similarities))
        top_indices = np.argsort(similarities)[::-1][:top_n]
        top_post_ids = [int(embedding_post_ids[idx]) for idx in top_indices]

        if top_post_ids:
            placeholders = ",".join(["?"] * len(top_post_ids))

            # === YOUR NEW UPDATED CODE GOES RIGHT HERE ===
            if category:
                sql_query = f"""
                    SELECT p.*
                    FROM posts p
                    INNER JOIN post_categories pc ON p.id = pc.post_id
                    INNER JOIN categories c ON pc.category_id = c.id
                    WHERE p.id IN ({placeholders}) AND c.name = ?
                """
                params = top_post_ids + [category]
            else:
                sql_query = f"""
                    SELECT p.*
                    FROM posts p
                    WHERE p.id IN ({placeholders})
                """
                params = top_post_ids

            posts = conn.execute(sql_query, params).fetchall()
            # ============================================
        else:
            posts = []
  
    #
    # KEYWORD SEARCH (FTS)
    #
    elif query:

        fts_posts = conn.execute(
            """
            SELECT rowid
            FROM posts_fts
            WHERE posts_fts MATCH ?
            """,
            (query + '*',)
        ).fetchall()

        fts_ids = [
            row["rowid"]
            for row in fts_posts
        ]

        if fts_ids:
            fts_posts = conn.execute(
                "SELECT rowid FROM posts_fts WHERE posts_fts MATCH ?",
                (query + '*',)
            ).fetchall()

            fts_ids = [row["rowid"] for row in fts_posts]
            
            if fts_ids:
                placeholders = ",".join(
                    ["?"] * len(fts_ids)
                )

                sql_query = f"SELECT p.* FROM posts p "
                
                # If category dropdown is used alongside keyword search
                if category:
                    sql_query += """
                    INNER JOIN post_categories pc ON p.id = pc.post_id
                    INNER JOIN categories c ON pc.category_id = c.id
                    WHERE p.id IN ({placeholders}) AND c.name = ?
                    """.format(placeholders=placeholders)
                    params = fts_ids + [category]
                else:
                    sql_query += f"WHERE p.id IN ({placeholders})"
                    params = fts_ids
                    
                posts = conn.execute(sql_query, params).fetchall()
    elif category:
        #sql_query += " AND c.name = ?"
        sql_query = """
        SELECT p.* FROM posts p
        INNER JOIN post_categories pc ON p.id = pc.post_id
        INNER JOIN categories c ON pc.category_id = c.id
        WHERE c.name = ?
        """
        posts = conn.execute(sql_query, [category]).fetchall()

    # 5. NO QUERY / NO CATEGORY FALLBACK
    else:
        posts = []


    #
    # NO QUERY
    #

    conn.close()

    results = []

    for post in posts:
        results.append({
            'title': post['title'],
            'summary': post['summary'],
            'insight': post['insight'],
            'url': post['url'] if post['url'] else "#"
        })
#'url': f"/post/{post['id']}"
    return jsonify(results)    

print("Initializing global ML models and matrix dependencies...", flush=True)
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    load_embeddings()
    if embedding_matrix is not None:
        print(f"Success! Embedding matrix shape: {embedding_matrix.shape}", flush=True)
        print(f"Embedding IDs loaded: {len(embedding_post_ids)}", flush=True)
except Exception as e:
    print(f"CRITICAL: System failed to pre-load embeddings. Error: {e}", flush=True)
    
#################################
#if you are running this app using Gunicorn or another production WSGI server on your cloud instance, your initialization code block at the absolute bottom (if __name__ == '__main__':) won't be executed by the production worker processes.
if __name__ == '__main__':
# --------------------------------------------------------
# Production-Safe Startup Initialization 
# This runs immediately when Gunicorn or Python imports app.py
# --------------------------------------------------------    
    print("Server starting up: Pre-loading ML Model and Embeddings...", flush=True)
    try:
        # moved to before if __name__ == '__main__' block so it runs in production WSGI environments like Gunicorn
        #model = SentenceTransformer('all-MiniLM-L6-v2')
        #load_embeddings()
        print(
            f"Embedding matrix shape: "
            f"{embedding_matrix.shape}",
            flush=True
        )
        print(
            f"Embedding IDs loaded: {len(embedding_post_ids)}",
            flush=True
        )
    except Exception as e:
        print(f"Warning: Could not load SentenceTransformer model. Semantic search will not work. Error: {e}")
    # For local development, set debug=True
    # For production, use a WSGI server like Gunicorn or uWSGI
    app.run(debug=True,host='0.0.0.0', port=5000)
