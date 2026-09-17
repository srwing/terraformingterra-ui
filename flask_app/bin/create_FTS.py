import sqlite3
def create_FTS5_table(conn):
  #/content/drive/MyDrive/globalwarming-arclein2/ai_ui/insights.db
  conn = sqlite3.connect('/content/drive/MyDrive/globalwarming-arclein2/ai_ui/insights.db')

  conn.execute("""
  CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
      title,
      content,
      summary,
      insight,
      tags,
      content='posts',
      content_rowid='id'
  )
  """)

  conn.execute("""
  INSERT INTO posts_fts(rowid, title, content, summary, insight, tags)
  SELECT id, title, content, summary, insight, tags
  FROM posts
  """)

  conn.commit()
  conn.close()

  print("FTS5 table ready.")
