import sqlite3

def add_column():
    try:
        conn = sqlite3.connect('backend/sql_app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(quizzes)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'signature' not in columns:
            print("Adding signature column...")
            cursor.execute("ALTER TABLE quizzes ADD COLUMN signature VARCHAR")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
