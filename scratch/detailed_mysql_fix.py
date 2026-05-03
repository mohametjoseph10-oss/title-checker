import mysql.connector
import sys

def run_fix():
    try:
        print("Connecting to MySQL...")
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="title_checker"
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM admin_users LIKE 'role'")
        result = cursor.fetchone()
        
        if not result:
            print("Executing ALTER TABLE to add 'role' column...")
            try:
                cursor.execute("ALTER TABLE admin_users ADD COLUMN role VARCHAR(50) DEFAULT 'admin'")
                conn.commit()
                print("ALTER SUCCESS")
            except mysql.connector.Error as err:
                print(f"ALTER ERROR: {err}")
        else:
            print("Column 'role' already exists in MySQL.")
            
        # Optional: Ensure at least one Super Admin if updating existing
        print("Setting Super Admin role for ID 1...")
        try:
            cursor.execute("UPDATE admin_users SET role = 'Super Admin' WHERE id = 1")
            conn.commit()
            print(f"UPDATE SUCCESS. Rows affected: {cursor.rowcount}")
        except mysql.connector.Error as err:
            print(f"UPDATE ERROR: {err}")
            
        conn.close()
        print("Done.")
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    run_fix()
