import os
import csv
import io
import sqlite3
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
DATABASE = 'database.db'  

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session.get('role') != role:
                flash('Access denied', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    try:
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            class_division TEXT NOT NULL
        )''') # REMOVED roll_no
        
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
        
        admin = conn.execute('SELECT * FROM users WHERE username = "admin"').fetchone()
        if not admin:
            hashed_pw = generate_password_hash('admin123')
            conn.execute('INSERT INTO users (username, password, role, name, class_division) VALUES (?, ?, ?)',
                         ('admin', hashed_pw, 'admin', 'Administrator', 'N/A'))
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"DB Init Error: {e}")
        traceback.print_exc()

def get_student_data(user_id):
    try:
        conn = get_db_connection()
        conn.execute('INSERT OR IGNORE INTO student_data (user_id) VALUES (?)', (user_id,))
        conn.commit()
        data = conn.execute('SELECT * FROM student_data WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(data) if data else {}
    except Exception as e:
        print(f"get_student_data error: {e}")
        return {}

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not role or not username or not password:
            return render_template('login.html', error='All fields required')
            
        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND role = ?', 
                               (username, role)).fetchone()
            conn.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['name'] = user['name']
                session['class_division'] = user['class_division']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid credentials or role')
        except Exception as e:
            print(f"Login error: {e}")
            return render_template('login.html', error=f'Database error: {str(e)}')
            
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if not user:
            session.clear()
            return redirect(url_for('login'))
        
        erp_data = get_student_data(session['user_id'])
        
        return render_template('student_dashboard.html', 
                               user=dict(user), 
                               erp_data=erp_data,
                               is_admin=(session.get('role') == 'admin'),
                               editing_student_id=session.get('editing_student_id'))
    except Exception as e:
        print(f"Dashboard error: {e}")
        traceback.print_exc()
        return f"Dashboard Error: {str(e)}", 500

@app.route('/bulk_upload', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def bulk_upload():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            next(csv_input) # skip header
        except:
            flash('Error reading file. Make sure it is a valid CSV with UTF-8 encoding', 'error')
            return redirect(request.url)

        conn = get_db_connection()
        success = 0
        errors = []

        for i, row in enumerate(csv_input, start=2):
            if not any(cell.strip() for cell in row):
                continue
                
            row = [x.strip() for x in row]

            if len(row) != 5: # CHANGED TO 5
                errors.append(f"Row {i}: Expected 5 columns, got {len(row)}. Data: {row}")
                continue
                    
            username, password, role, name, class_division = row # REMOVED roll_no
            try:
                hashed_pw = generate_password_hash(password)
                conn.execute('''INSERT INTO users 
                    (username, password, role, name, class_division) 
                    VALUES (?, ?, ?)''', # 5 ? 
                    (username, hashed_pw, role, name, class_division))
                success += 1
            except sqlite3.IntegrityError:
                errors.append(f"Row {i}: Username '{username}' already exists")
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
        
        conn.commit()
        conn.close()

        if success > 0:
            flash(f'✅ Success: {success} users added', 'success')
        for error in errors:
            flash(f'❌ {error}', 'error')
            
        return redirect(url_for('bulk_upload'))

    return render_template('bulk_upload.html')

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    try:
        data = request.json
        username = data['username']
        password = data['password']
        role = data['role']
        name = data['name']
        class_division = data['class_division']
        
        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        conn.execute('''INSERT INTO users (username, password, role, name, class_division) 
                        VALUES (?, ?, ?, ?, ?)''', # 5 ?
                     (username, hashed_pw, role, name, class_division))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}, 400
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
