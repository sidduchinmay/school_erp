from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
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
        
        admin = conn.execute('SELECT * FROM users WHERE username = "admin"').fetchone()
        if not admin:
            conn.execute('INSERT INTO users (username, password, role, name, class_division) VALUES (?, ?, ?, ?, ?)',
                         ('admin', 'admin123', 'admin', 'Administrator', 'N/A'))
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

@app.errorhandler(500)
def internal_error(error):
    return f"Server Error: {str(error)}", 500

@app.route('/')
def index():
    return redirect(url_for('login'))

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
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ? AND role = ?', 
                               (username, password, role)).fetchone()
            conn.close()
            
            if user:
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
@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''INSERT INTO users (username, password, role, name, class_division, roll_no) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (data['username'], data['password'], data['role'], 
                      data['name'], data['class_division'], data.get('roll_no')))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}, 400
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500






@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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

@app.route('/admin/update_fee/<int:student_id>', methods=['POST'])
def update_fee(student_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('DELETE FROM fee_structure WHERE user_id=? AND academic_year=?', 
                     (student_id, data['academic_year']))
        conn.execute('''INSERT INTO fee_structure 
            (user_id, academic_year, arrears, term1_fee, term1_paid, term2_fee, term2_paid, programme_fee, programme_paid, remarks) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (student_id, data['academic_year'], data.get('arrears',0), data.get('term1_fee',0), data.get('term1_paid',0), 
             data.get('term2_fee',0), data.get('term2_paid',0), data.get('programme_fee',0), data.get('programme_paid',0), data.get('remarks','')))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/get_fee_details/<int:student_id>')
def get_fee_details(student_id):
    try:
        conn = get_db_connection()
        fees = conn.execute('SELECT * FROM fee_structure WHERE user_id=? ORDER BY academic_year DESC', 
                           (student_id,)).fetchall()
        conn.close()
        return {"fees": [dict(row) for row in fees]}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
