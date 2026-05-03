import mysql.connector
from mysql.connector import Error
import os

def get_db_connection():
    """
    Creates a fresh MySQL database connection for each request.
    Strictly uses MySQL as requested.
    """
    try:
        # Create a brand new connection with stability parameters
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="title_checker",
            # Connection settings to prevent stale handles
            connection_timeout=10,
            buffered=True,
            autocommit=True
        )
        
        if conn.is_connected():
            return conn
            
    except Error as e:
        print(f"CRITICAL: MySQL Connection Error: {e}")
        raise e # Let the application handle the failure instead of falling back to SQLite
    
    return None

def init_db():
    """
    Initializes the MySQL database by creating all required tables if they don't exist.
    """
    conn = get_db_connection()
    if not conn:
        print("Could not initialize database: Connection failed.")
        return
        
    try:
        cursor = conn.cursor()
        
        # Create tables for MySQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_titles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                entered_title VARCHAR(255),
                matched_title VARCHAR(255),
                similarity_score FLOAT,
                result VARCHAR(50),
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255),
                role VARCHAR(50) DEFAULT 'Admin'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                subject VARCHAR(255),
                subject_key VARCHAR(255),
                message TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'Pending',
                is_read BOOLEAN DEFAULT FALSE,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_preview TEXT,
                replied_at TIMESTAMP NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_thread (email, subject_key)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_replies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id INT NOT NULL,
                sender_type ENUM('user', 'admin') NOT NULL,
                sender_email VARCHAR(255) NOT NULL,
                reply_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES contact_messages(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id INT NOT NULL,
                admin_email VARCHAR(255) NOT NULL,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES contact_messages(id) ON DELETE CASCADE
            )
        ''')

        # Group Members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                student_id VARCHAR(50) NOT NULL,
                department VARCHAR(255) NOT NULL,
                whatsapp VARCHAR(50) NOT NULL,
                email VARCHAR(255) NOT NULL,
                photo VARCHAR(255) NOT NULL
            )
        ''')

        # Seed 5 group members (only if table is empty)
        cursor.execute('SELECT COUNT(*) as cnt FROM group_members')
        row = cursor.fetchone()
        if row[0] == 0:
            members = [
                ('Mohamed Yusuf Omar',    '26166', 'Information Technology', '252611146598', 'mohametjoseph10@gmail.com',     'uploads/member1.jpeg'),
                ('Abuukar Abdullahi Ahmed','26986', 'Information Technology', '252617759993', 'abuubakarabdulaahi61@gmail.com', 'uploads/member2.jpeg'),
                ('Mohamed Abdullahi Hasan','26212', 'Information Technology', '252616168060', 'roraye2002@gmail.com',           'uploads/member3.jpeg'),
                ('Usaame Mohamed Hassan',  '26933', 'Information Technology', '252618137189', 'usaamemohamedhassan@gmail.com',  'uploads/member4.jpeg'),
                ('Usaame Hassan Ali',      '27186', 'Information Technology', '252612894509', 'usaamaxasancali@gmail.com',      'uploads/member5.jpeg'),
            ]
            cursor.executemany(
                'INSERT INTO group_members (full_name, student_id, department, whatsapp, email, photo) VALUES (%s, %s, %s, %s, %s, %s)',
                members
            )

        conn.commit()

        # ── Photo-adjustment columns (added safely so existing installs upgrade automatically) ──
        for col_def in [
            "ALTER TABLE group_members ADD COLUMN image_scale FLOAT DEFAULT 1 AFTER photo",
            "ALTER TABLE group_members ADD COLUMN image_pos_x FLOAT DEFAULT 0 AFTER image_scale",
            "ALTER TABLE group_members ADD COLUMN image_pos_y FLOAT DEFAULT 0 AFTER image_pos_x",
        ]:
            try:
                cursor.execute(col_def)
                conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore
        print("MySQL Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing MySQL database: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
