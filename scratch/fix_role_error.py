from app import get_db_connection

def fix_admin_users_role():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    try:
        # Add role column if it doesn't exist
        print("Checking/Adding 'role' column...")
        try:
            if db_type == 'mysql':
                cursor.execute("ALTER TABLE admin_users ADD COLUMN role VARCHAR(50) DEFAULT 'Admin'")
            else:
                cursor.execute("ALTER TABLE admin_users ADD COLUMN role TEXT DEFAULT 'Admin'")
            conn.commit()
            print("Column 'role' added successfully.")
        except Exception as e:
            print(f"Note (adding column): {e}")

        # Update main admin account
        print("Updating admin@test.com to Super Admin...")
        if db_type == 'mysql':
            cursor.execute("UPDATE admin_users SET role = 'Super Admin' WHERE email = %s", ('admin@test.com',))
        else:
            cursor.execute("UPDATE admin_users SET role = 'Super Admin' WHERE email = ?", ('admin@test.com',))
        conn.commit()
        print("Admin account updated successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_admin_users_role()
