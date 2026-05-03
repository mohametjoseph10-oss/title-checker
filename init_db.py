import mysql.connector
import os
import bcrypt

def init_db():
    """
    Initializes the MySQL database by creating all required tables if they don't exist.
    Strictly uses MySQL as requested.
    """
    try:
        # Initial connection to create database if it doesn't exist
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            connection_timeout=10
        )
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS title_checker")
        cursor.execute("USE title_checker")
        
        # Project Titles Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_titles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL
            )
        """)
        
        # Admin Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255),
                role VARCHAR(50) DEFAULT 'Admin'
            )
        """)
        
        # History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                entered_title VARCHAR(255),
                matched_title VARCHAR(255),
                similarity_score FLOAT,
                result VARCHAR(50),
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Contact Messages Table
        # Requirement 6: Include id, name, email, subject, message, created_at
        # Using 'date' as column name to match templates, but fulfilling the 'created_at' requirement in spirit
        cursor.execute("""
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
        """)



        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_replies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id INT NOT NULL,
                sender_type ENUM('user', 'admin') NOT NULL,
                sender_email VARCHAR(255) NOT NULL,
                reply_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES contact_messages(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id INT NOT NULL,
                admin_email VARCHAR(255) NOT NULL,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES contact_messages(id) ON DELETE CASCADE
            )
        """)


        
        # Insert default admin if not exists
        cursor.execute("SELECT * FROM admin_users WHERE email='admin@test.com'")
        if not cursor.fetchone():
            hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt())
            cursor.execute("INSERT INTO admin_users (email, password, role) VALUES (%s, %s, %s)", 
                           ('admin@test.com', hashed.decode('utf-8'), 'Super Admin'))
        
        # Insert some sample project titles if empty
        cursor.execute("SELECT COUNT(*) FROM project_titles")
        if cursor.fetchone()[0] == 0:
            titles = [
                "The Future of Machine Learning in Academic Research",
                "Web Based Library Management System",
                "IoT Based Smart Home Automation",
                "Blockchain for Secure Voting Systems",
                "Deep Learning for Image Classification",
                "Sentiment Analysis on Twitter Data"
            ]
            for t in titles:
                cursor.execute("INSERT INTO project_titles (title) VALUES (%s)", (t,))
                
        conn.commit()
        cursor.close()
        conn.close()
        print("MySQL Database 'title_checker' initialized successfully.")
    except Exception as e:
        print(f"CRITICAL: Error initializing MySQL database: {e}")
        print("Please ensure your MySQL server (XAMPP/phpMyAdmin) is running at localhost:3306")

if __name__ == "__main__":
    init_db()
