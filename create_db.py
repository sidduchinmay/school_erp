# update_db.py - run once
import sqlite3

conn = sqlite3.connect('school.db')

# Add role column if not exists
try:
    conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
except:
    pass

# Update existing users with roles
conn.execute("UPDATE users SET role='admin' WHERE username='admin'")
conn.execute("UPDATE users SET role='student' WHERE username='student1'")

# Add teacher
conn.execute("INSERT OR IGNORE INTO users (username, password, role, name, class_division) VALUES ('teacher1', 'teach123', 'teacher', 'Mrs. Sharma', 'Staff')")

# ERP data table for the full form
conn.execute('''
CREATE TABLE IF NOT EXISTS erp_data (
    id INTEGER PRIMARY KEY,
    fee_payment TEXT, attendance TEXT, academic_progress TEXT, accolades TEXT,
    applications TEXT, participation TEXT, schedules TEXT, view_calendar TEXT, downloads TEXT,
    discipline TEXT, parents_meetings TEXT, counselling TEXT
)
''')

# Insert default row
conn.execute("INSERT OR IGNORE INTO erp_data (id) VALUES (1)")

conn.commit()
conn.close()
print("DB updated for roles + ERP table")
