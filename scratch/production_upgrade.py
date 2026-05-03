import mysql.connector
from db import get_db_connection

def production_threading_upgrade():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 0. Ensure subject_key exists
        print("Checking for subject_key column...")
        cursor.execute("SHOW COLUMNS FROM contact_messages LIKE 'subject_key'")
        if not cursor.fetchone():
            print("Adding subject_key column...")
            cursor.execute("ALTER TABLE contact_messages ADD COLUMN subject_key VARCHAR(255) AFTER subject")
            conn.commit()
            
        # Populate subject_key if empty
        cursor.execute("UPDATE contact_messages SET subject_key = LOWER(TRIM(subject)) WHERE subject_key IS NULL")
        conn.commit()

        # 1. Clean up duplicates if any exist
        print("Checking for duplicate threads...")
        cursor.execute("""
            SELECT email, subject_key, GROUP_CONCAT(id ORDER BY id ASC) as ids, COUNT(*) as count 
            FROM contact_messages 
            GROUP BY email, subject_key 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        for dup in duplicates:
            ids = [int(i) for i in dup['ids'].split(',')]
            primary_id = ids[0]
            redundant_ids = ids[1:]
            
            print(f"Merging duplicates for {dup['email']} - {dup['subject_key']} (Primary: {primary_id}, Duplicates: {redundant_ids})")
            
            # Move replies to primary thread
            for rid in redundant_ids:
                cursor.execute("UPDATE message_replies SET message_id = %s WHERE message_id = %s", (primary_id, rid))
                try:
                    cursor.execute("UPDATE admin_notes SET message_id = %s WHERE message_id = %s", (primary_id, rid))
                except:
                    pass # admin_notes might not exist yet or have different schema
            
            # Delete redundant threads
            format_strings = ','.join(['%s'] * len(redundant_ids))
            cursor.execute(f"DELETE FROM contact_messages WHERE id IN ({format_strings})", tuple(redundant_ids))
        
        conn.commit()

        # 2. Add Unique Constraint
        print("Adding unique constraint (email, subject_key)...")
        try:
            cursor.execute("ALTER TABLE contact_messages ADD UNIQUE KEY uniq_thread (email, subject_key)")
            conn.commit()
        except mysql.connector.Error as err:
            if err.errno == 1061: # Duplicate key name
                print("Unique key already exists.")
            else: raise

        # 3. Add Indexes
        print("Adding performance indexes...")
        try:
            cursor.execute("CREATE INDEX idx_last_activity ON contact_messages (last_activity DESC)")
            conn.commit()
        except mysql.connector.Error as err:
            if err.errno == 1061: print("Index idx_last_activity already exists.")
            else: raise

        print("Production upgrade complete!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    production_threading_upgrade()
