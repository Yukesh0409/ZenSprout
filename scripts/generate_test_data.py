import sqlite3
import random
from datetime import datetime, timedelta, date
import os
from werkzeug.security import generate_password_hash

def connect_to_database():
    # Get the absolute path to the database file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'instance', 'zensprout.db')
    
    # Create instance directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return sqlite3.connect(db_path)

def create_tables(cursor):
    # Create users table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    )
    ''')
    
    # Create sessions table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        timestamp DATETIME NOT NULL,
        duration INTEGER NOT NULL,
        session_type TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

def create_test_user(cursor):
    # Complete test user profile
    test_user = {
        'username': 'sarah_dev',
        'email': 'sarah@example.com',
        'password': generate_password_hash('test123'),  # Hash the password
        'age': 28,
        'gender': 'female',
        'goals': 'Improve coding skills, maintain work-life balance, complete personal projects',
        'distractions': 'Social media, phone notifications, email checking',
        'occupation': 'Software Developer'
    }
    
    # First, check if user exists
    cursor.execute("SELECT id FROM user WHERE email = ? OR username = ?", 
                  (test_user['email'], test_user['username']))
    existing_user = cursor.fetchone()
    
    if existing_user:
        print(f"User already exists with ID: {existing_user[0]}")
        return existing_user[0]
    
    print("Creating new user...")
    try:
        cursor.execute("""
            INSERT INTO user (username, email, password, age, gender, goals, distractions, occupation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_user['username'],
            test_user['email'],
            test_user['password'],  # Now using hashed password
            test_user['age'],
            test_user['gender'],
            test_user['goals'],
            test_user['distractions'],
            test_user['occupation']
        ))
        user_id = cursor.lastrowid
        print(f"Created new user with ID: {user_id}")
        return user_id
    except sqlite3.Error as e:
        print(f"Error creating user: {e}")
        # Let's see what's in the user table
        cursor.execute("SELECT * FROM user")
        users = cursor.fetchall()
        print("\nCurrent users in database:")
        for user in users:
            print(user)
        raise

def generate_test_data(user_id, days=30):
    current_date = datetime.now()
    test_data = []
    
    # Generate sessions starting from today and going back 'days' days
    for day in range(days):
        date_for_session = current_date - timedelta(days=day)
        
        # Generate 4-8 sessions per day
        num_sessions = random.randint(4, 8)
        
        for _ in range(num_sessions):
            session_type = 'work' if random.random() < 0.8 else 'break'
            
            # Work: 25-50 minutes, Break: 5-15 minutes
            if session_type == 'work':
                duration = random.randint(25, 50) * 60  # Convert to seconds
            else:
                duration = random.randint(5, 15) * 60  # Convert to seconds
            
            # Create sessions during working hours (9 AM - 7 PM)
            hour = random.randint(9, 19)
            minute = random.randint(0, 59)
            
            # Create proper datetime object
            timestamp = date_for_session.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            
            test_data.append({
                'user_id': user_id,
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration,
                'session_type': session_type
            })
    
    # Sort the data by timestamp
    test_data.sort(key=lambda x: x['timestamp'])
    return test_data

def insert_test_data(cursor, data):
    cursor.executemany(
        "INSERT INTO session (user_id, timestamp, duration, session_type) VALUES (?, ?, ?, ?)",
        [(d['user_id'], d['timestamp'], d['duration'], d['session_type']) for d in data]
    )

def verify_data(cursor, user_id):
    cursor.execute("""
        SELECT s.*, u.username 
        FROM session s 
        JOIN user u ON s.user_id = u.id 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 5
    """, (user_id,))
    recent_entries = cursor.fetchall()
    print("\nRecent entries in database:")
    for entry in recent_entries:
        print(entry)

def display_table_contents(cursor, user_id):
    print("\n=== USER INFORMATION ===")
    cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user is None:
        print(f"No user found with ID: {user_id}")
        return
        
    print(f"User ID: {user[0]}")
    print(f"Username: {user[1]}")
    print(f"Email: {user[2]}")

    print("\n=== SESSION STATISTICS ===")
    cursor.execute("SELECT COUNT(*) FROM session WHERE user_id = ?", (user_id,))
    total_sessions = cursor.fetchone()[0]
    print(f"Total sessions: {total_sessions}")

    # Get sessions by type with proper date handling
    cursor.execute("""
        SELECT 
            session_type, 
            COUNT(*) as count,
            SUM(duration) as total_duration,
            MIN(date(timestamp)) as first_date,
            MAX(date(timestamp)) as last_date
        FROM session 
        WHERE user_id = ?
        GROUP BY session_type
    """, (user_id,))
    
    print("\nSession breakdown:")
    for session_type, count, total_duration, first_date, last_date in cursor.fetchall():
        minutes = total_duration // 60
        print(f"{session_type.capitalize()} sessions: {count}")
        print(f"Total duration: {minutes} minutes")
        print(f"Date range: {first_date} to {last_date}\n")

    print("\n=== RECENT SESSIONS (Last 10) ===")
    cursor.execute("""
        SELECT 
            timestamp,
            session_type,
            duration
        FROM session 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    """, (user_id,))
    
    print("\nTimestamp               | Type  | Duration (mins)")
    print("-" * 45)
    for timestamp, session_type, duration in cursor.fetchall():
        duration_minutes = duration // 60
        print(f"{timestamp:<22} | {session_type:<6} | {duration_minutes}")

def main():
    print("Connecting to database...")
    conn = connect_to_database()
    cursor = conn.cursor()
    
    print("Creating tables if not exist...")
    create_tables(cursor)
    
    print("Creating/getting test user...")
    user_id = create_test_user(cursor)
    conn.commit()
    
    print("Generating test data...")
    test_data = generate_test_data(user_id, 30)
    
    print(f"Generated {len(test_data)} test sessions")
    print("\nTest user credentials:")
    print("Username: sarah_dev")
    print("Password: test123")  # Show the plain text password for login
    print("Email: sarah@example.com")
    
    print("\nSample of generated data:")
    for entry in test_data[:3]:
        print(entry)
    
    response = input("\nWould you like to insert this test data? (y/n): ")
    if response.lower() == 'y':
        print("Inserting test data...")
        insert_test_data(cursor, test_data)
        conn.commit()
        print("Data inserted successfully!")
        
        # Display the table contents
        display_table_contents(cursor, user_id)
    else:
        print("Operation cancelled.")
    
    conn.close()
    print("\nDatabase connection closed.")

if __name__ == "__main__":
    main() 