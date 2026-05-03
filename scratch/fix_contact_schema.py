from db import get_db_connection

def fix_contact_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get existing columns
        cursor.execute("SHOW COLUMNS FROM contact_messages")
        existing_columns = [col[0] for col in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")

        # List of columns to ensure
        required_columns = {
            'subject': "VARCHAR(255) AFTER email",
            'status': "VARCHAR(50) DEFAULT 'Pending' AFTER message",
            'replied_at': "TIMESTAMP NULL AFTER status"
        }

        for col, definition in required_columns.items():
            if col not in existing_columns:
                print(f"Adding missing column: {col}")
                cursor.execute(f"ALTER TABLE contact_messages ADD COLUMN {col} {definition}")
            else:
                print(f"Column '{col}' already exists.")

        # Ensure 'date' exists (or created_at)
        # The user's previous code used 'date', but their request mentions 'created_at'.
        # I will add 'created_at' as an alias or ensure 'date' is there.
        if 'date' not in existing_columns and 'created_at' not in existing_columns:
            cursor.execute("ALTER TABLE contact_messages ADD COLUMN date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("Added 'date' column.")

        conn.commit()
        print("Database schema fix completed successfully.")
    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_contact_table()
