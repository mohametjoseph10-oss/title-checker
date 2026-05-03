from app import get_db_connection

def update_schema():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    try:
        if db_type == 'mysql':
            cursor.execute("ALTER TABLE admin_users ADD COLUMN role VARCHAR(50) DEFAULT 'Admin'")
        else:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN role TEXT DEFAULT 'Admin'")
        conn.commit()
        print("Column 'role' added successfully.")
    except Exception as e:
        print(f"Note: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_schema()
