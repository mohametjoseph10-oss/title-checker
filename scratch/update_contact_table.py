from db import get_db_connection

def update_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if status column exists
        cursor.execute("SHOW COLUMNS FROM contact_messages LIKE 'status'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE contact_messages ADD COLUMN status VARCHAR(50) DEFAULT 'Pending'")
            print("Successfully added 'status' column.")
            
        cursor.execute("SHOW COLUMNS FROM contact_messages LIKE 'replied_at'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE contact_messages ADD COLUMN replied_at TIMESTAMP NULL")
            print("Successfully added 'replied_at' column.")
            
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_table()
