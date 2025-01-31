import sqlite3
import os

def connect_to_database():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'zensprout.db')
    return sqlite3.connect(db_path)

def display_users(cursor):
    print("\n=== USERS TABLE CONTENTS ===")
    cursor.execute("SELECT id, username, email, password FROM users")
    users = cursor.fetchall()
    
    if not users:
        print("No users found in the database!")
        return
    
    print("\nID | Username | Email | Password")
    print("-" * 60)
    for user in users:
        print(f"{user[0]:<3}| {user[1]:<9}| {user[2]:<20}| {user[3]}")

def main():
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        display_users(cursor)
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 