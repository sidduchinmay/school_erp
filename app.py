from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'aps-erp-secret-key-2025-26'

# Use /tmp on Render - always writable
DB_PATH = '/tmp/school.db'

def init_db():
    conn = get_db_connection()
    # Drop old table if schema changed - CAUTION: deletes data
    # conn.execute('DROP TABLE IF EXISTS student_data')  # Uncomment only if you want to wipe data
    
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        class_division TEXT NOT NULL,
        roll_no TEXT
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS student_data (
        user_id INTEGER PRIMARY KEY,
        fee_payment TEXT, attendance TEXT, academic_progress TEXT,
        accolades TEXT, applications TEXT, participation TEXT,
        schedules TEXT, view_calendar TEXT, downloads TEXT,
        discipline TEXT, parents_meetings TEXT, counselling TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS fee_structure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        academic_year TEXT NOT NULL,
        arrears REAL DEFAULT 0,
        term1_fee REAL DEFAULT 0,
        term1_paid REAL DEFAULT 0,
        term2_fee REAL DEFAULT 0,
        term2_paid REAL DEFAULT 0,
        programme_fee REAL DEFAULT 0,
        programme_paid REAL DEFAULT 0,
        remarks TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    conn.commit()
    conn.close()

# Call this immediately after defining it
init_db()

# Force run on import - works with gunicorn on Render
init_db()

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
    # Auto-create row if missing
    conn.execute('INSERT OR IGNORE INTO student_data (user_id) VALUES (?)', (user_id,))
    conn.commit()
    
    data = conn.execute('SELECT * FROM student_data WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(data) if data else {}

def get_all_students():
    conn = get_db_connection()
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
    
    # Build update query dynamically for whatever field was sent
    for field, value in data.items():
        conn.execute(f'UPDATE student_data SET {field}=? WHERE user_id=?', (value, student_id))
    
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.route('/admin/update_erp', methods=['POST'])
def update_erp():
    if 'user_id' not in session:
        return "Unauthorized", 403
    data = request.json
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO student_data (user_id) VALUES (?)', (session['user_id'],))
    # Build update dynamically for whatever field was sent
    field = list(data.keys())[0]
    value = data[field]
    conn.execute(f'UPDATE student_data SET {field}=? WHERE user_id=?', (value, session['user_id']))
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

@app.route('/admin/update_fee/<int:student_id>', methods=['POST'])
def update_fee(student_id):
    if session.get('role')!= 'admin':
        return "Unauthorized", 403
    data = request.json
    conn = get_db_connection()
    # Delete old record for that year and insert new
    conn.execute('DELETE FROM fee_structure WHERE user_id=? AND academic_year=?', 
                 (student_id, data['academic_year']))
    conn.execute('''INSERT INTO fee_structure 
        (user_id, academic_year, arrears, term1_fee, term1_paid, term2_fee, term2_paid, programme_fee, programme_paid, remarks) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (student_id, data['academic_year'], data['arrears'], data['term1_fee'], data['term1_paid'], 
         data['term2_fee'], data['term2_paid'], data['programme_fee'], data['programme_paid'], data['remarks']))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.route('/get_fee_details/<int:student_id>')
def get_fee_details(student_id):
    conn = get_db_connection()
    fees = conn.execute('SELECT * FROM fee_structure WHERE user_id=? ORDER BY academic_year DESC', 
                       (student_id,)).fetchall()
    conn.close()
    return {"fees": [dict(row) for row in fees]}



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
