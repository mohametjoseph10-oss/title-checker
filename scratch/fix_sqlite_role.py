import sqlite3

def add_role_column():
    db_path = 'd:/Tittle_Checker/title_checker.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(admin_users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'role' not in columns:
            print("Adding 'role' column to 'admin_users' table...")
            cursor.execute("ALTER TABLE admin_users ADD COLUMN role TEXT DEFAULT 'Admin'")
            conn.commit()
            print("Column 'role' added successfully.")
        else:
            print("Column 'role' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_role_column()
