# init_db.py
import sqlite3

conn = sqlite3.connect('school.db')

# Users table
conn.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    name TEXT NOT NULL,
    class_division TEXT,
    scholar_type TEXT,
    father_mobile TEXT,
    mother_mobile TEXT,
    emergency_no TEXT,
    photo_url TEXT
)
''')

# ERP data table - this was missing
conn.execute('''
CREATE TABLE IF NOT EXISTS erp_data (
    id INTEGER PRIMARY KEY,
    fee_payment TEXT, attendance TEXT, academic_progress TEXT, accolades TEXT,
    applications TEXT, participation TEXT, schedules TEXT, view_calendar TEXT, downloads TEXT,
    discipline TEXT, parents_meetings TEXT, counselling TEXT
)
''')

# Insert default users if not exist
conn.execute("INSERT OR IGNORE INTO users (username, password, role, name, class_division) VALUES ('admin', 'admin123', 'admin', 'Principal', 'All')")
conn.execute("INSERT OR IGNORE INTO users (username, password, role, name, class_division) VALUES ('student1', 'pass123', 'student', 'John Doe', '10-A')")
conn.execute("INSERT OR IGNORE INTO users (username, password, role, name, class_division) VALUES ('teacher1', 'teach123', 'teacher', 'Mrs. Sharma', 'Staff')")

# Insert default ERP row if not exist
conn.execute("INSERT OR IGNORE INTO erp_data (id) VALUES (1)")

conn.commit()
conn.close()
print("Database initialized successfully")
