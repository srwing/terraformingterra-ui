import sqlite3
import json
import numpy as np

def repair_database():
    # Connect to your database (adjust the path to your actual DB file)
    #conn = sqlite3.connect("~/flask_app/insights.db")
    conn = sqlite3.connect("../insights.db")
    cur = conn.cursor()
    
    # 1. Fetch only the rows where the embedding is stored as text
    cur.execute("""
        SELECT id, embedding 
        FROM posts 
        WHERE typeof(embedding) = 'text'
    """)
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} rows to repair.")
    
    repaired_count = 0
    for post_id, text_emb in rows:
        try:
            # Parse the JSON string string into a Python list
            emb_list = json.loads(text_emb)
            
            # Convert the list into a NumPy float32 array, then extract raw bytes
            blob_emb = np.array(emb_list, dtype=np.float32).tobytes()
            
            # 2. Update the row back into the database as a true BLOB
            cur.execute("""
                UPDATE posts 
                SET embedding = ? 
                WHERE id = ?
            """, (sqlite3.Binary(blob_emb), post_id))
            
            repaired_count += 1
        except Exception as e:
            print(f"Failed to repair row ID {post_id}: {e}")
            
    # Commit changes and close
    conn.commit()
    conn.close()
    print(f"Successfully repaired {repaired_count} rows!")

if __name__ == "__main__":
    repair_database()
