#run this once on the database - make sure the database is not in use by any other processes else you might get
#'database locked' errors. 
# To run close anything using the database and pkill -f app.py. Then run this script
import sqlite3
DATABASE='/home/ubuntu/flask_app/insights.db'

def apply_indexes():
    print("Connecting to database...")
    conn = sqlite3.connect(DATABASE)
    try:
        print("Creating indexes... please wait...")
        # Running these sequentially inside a dedicated connection
        conn.execute("CREATE INDEX IF NOT EXISTS idx_post_categories_post ON post_categories(post_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_post_categories_cat ON post_categories(category_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);")
        
        conn.commit()
        print("Indexes successfully created!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    apply_indexes()
