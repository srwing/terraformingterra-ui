from sentence_transformers import SentenceTransformer
import sqlite3
import json

def generate_embeddings(conn):
  model = SentenceTransformer('all-MiniLM-L6-v2')

  #conn = sqlite3.connect('/content/drive/MyDrive/globalwarming-arclein2/ai_ui/insights.db')
  conn.row_factory = sqlite3.Row

  posts = conn.execute("""
  SELECT id, title, summary, insight
  FROM posts
  """).fetchall()

  for post in posts:

      text = f"""
      {post['title']}
      {post['summary']}
      {post['insight']}
      """

      embedding = model.encode(text).tolist()

      conn.execute("""
      UPDATE posts
      SET embedding = ?
      WHERE id = ?
      """, (
          json.dumps(embedding),
          post['id']
      ))

  conn.commit()
  conn.close()

  print("Embeddings generated.")
