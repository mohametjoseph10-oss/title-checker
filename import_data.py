import pandas as pd
from db import get_db_connection

# Read your CSV
df = pd.read_csv("project_titles.csv")

# Make sure column name is correct
df.columns = ['title']

conn, db_type = get_db_connection()
cursor = conn.cursor()

# Clear old data and reset sequence
if db_type == 'mysql':
    cursor.execute("TRUNCATE TABLE project_titles")
else:
    cursor.execute("DELETE FROM project_titles")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='project_titles'")

# Insert new data
for title in df['title']:
    if db_type == 'mysql':
        cursor.execute("INSERT INTO project_titles (title) VALUES (%s)", (title,))
    else:
        cursor.execute("INSERT INTO project_titles (title) VALUES (?)", (title,))

conn.commit()
cursor.close()
conn.close()

print("✅ Dataset imported successfully with reset IDs!")