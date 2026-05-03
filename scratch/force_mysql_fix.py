import mysql.connector

def force_mysql_fix():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="title_checker"
        )
        cursor = conn.cursor()
        
        print("1. Adding 'role' column to admin_users...")
        try:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN role VARCHAR(50) DEFAULT 'Admin'")
            conn.commit()
            print("   Success: Column added.")
        except Exception as e:
            print(f"   Note: {e}")

        print("2. Verifying table structure...")
        cursor.execute("DESCRIBE admin_users")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   Field: {col[0]}, Type: {col[1]}")

        print("3. Promoting Admin ID 1 to Super Admin...")
        cursor.execute("UPDATE admin_users SET role = 'Super Admin' WHERE id = 1")
        conn.commit()
        print(f"   Success: Rows affected: {cursor.rowcount}")

        cursor.close()
        conn.close()
        print("\nAll tasks completed.")
    except Exception as e:
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    force_mysql_fix()
