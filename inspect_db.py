import sqlite3
import uuid

def inspect_db():
    conn = sqlite3.connect('backend/sql_app.db')
    cursor = conn.cursor()
    
    print("--- Users ---")
    try:
        cursor.execute("SELECT * FROM users")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error reading users: {e}")

    print("\n--- Stakes ---")
    try:
        cursor.execute("SELECT hex(stake_id), user_id, amount_eth FROM stakes")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error reading stakes: {e}")

    print("\n--- Quizzes ---")
    try:
        cursor.execute("SELECT hex(quiz_id), hex(stake_id), is_passed, score FROM quizzes")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Error reading quizzes: {e}")
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
