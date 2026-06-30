from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import csv
from io import StringIO

if os.path.exists('school.db'):
    os.remove('school.db')  # Delete old DB
app = Flask(__name__)
app.secret_key = 'aps-erp-secret-key-2025-26'
DB_PATH = 'school.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            class_division TEXT
        )
    ''')

    # Add roll_no column if it doesn't exist - fixes your error
    try:
        conn.execute('ALTER TABLE users ADD COLUMN roll_no TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.execute('''
        CREATE TABLE IF NOT EXISTS student_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            fee_payment TEXT, attendance TEXT, academic_progress TEXT, accolades TEXT,
            applications TEXT, participation TEXT, schedules TEXT, view_calendar TEXT, downloads TEXT,
            discipline TEXT, parents_meetings TEXT, counselling TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.execute("INSERT OR IGNORE INTO users (username, password, role, name, class_division) VALUES ('admin', 'admin123', 'admin', 'Principal', 'All')")
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_user(username, password, role):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username =? AND password =? AND role =?',(username, password, role)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id =?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_student_data(user_id):
    conn = get_db_connection()
    data = conn.execute('SELECT * FROM student_data WHERE user_id =?', (user_id,)).fetchone()
    conn.close()
    return dict(data) if data else {}

def get_all_students():
    conn = get_db_connection()
    # Don't order by roll_no yet - column might not exist
    students = conn.execute("SELECT * FROM users WHERE role='student' ORDER BY class_division").fetchall()
    conn.close()
    return [dict(s) for s in students]

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        user = check_user(username, password, role)
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials or role")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    is_admin = session.get('role') == 'admin'

    if is_admin:
        students = get_all_students()
        return render_template('admin_dashboard.html', user=user, students=students)
    else:
        erp_data = get_student_data(session['user_id'])
        return render_template('student_dashboard.html', user=user, erp_data=erp_data, is_admin=False)

@app.route('/admin/student/<int:student_id>')
def edit_student(student_id):
    if session.get('role')!= 'admin':
        return "Unauthorized", 403
    student = get_user_by_id(student_id)
    erp_data = get_student_data(student_id)
    return render_template('student_dashboard.html', user=student, erp_data=erp_data, is_admin=True, editing_student_id=student_id)

@app.route('/admin/update_student/<int:student_id>', methods=['POST'])
def update_student(student_id):
    if session.get('role')!= 'admin':
        return "Unauthorized", 403
    data = request.json
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO student_data (user_id) VALUES (?)', (student_id,))
    conn.execute('''
        UPDATE student_data SET
        fee_payment=?, attendance=?, academic_progress=?, accolades=?,
        applications=?, participation=?, schedules=?, view_calendar=?, downloads=?,
        discipline=?, parents_meetings=?, counselling=?
        WHERE user_id =?
    ''', (
        data.get('fee_payment'), data.get('attendance'), data.get('academic_progress'),
        data.get('accolades'), data.get('applications'), data.get('participation'),
        data.get('schedules'), data.get('view_calendar'), data.get('downloads'),
        data.get('discipline'), data.get('parents_meetings'), data.get('counselling'),
        student_id
    ))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.route('/admin/bulk_upload', methods=['POST'])
def bulk_upload():
    if session.get('role')!= 'admin':
        return "Unauthorized", 403

    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.DictReader(stream)

    conn = get_db_connection()
    count = 0
    for row in csv_input:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO users (username, password, role, name, class_division, roll_no)
                VALUES (?,?, 'student',?,?,?)
            ''', (row['username'], row['password'], row['name'], row['class_division'], row['roll_no']))
            count += 1
        except Exception as e:
            print(f"Error on row {row}: {e}")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "added": count})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
