import os
import csv
import io
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] != role:
                flash('Access denied', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and user['password'] == password: # For now plain text. Change to check_hash later
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=session.get('name'), role=session.get('role'))

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
            header = next(csv_input) # skip header
        except:
            flash('Error reading file. Make sure it is a valid CSV with UTF-8 encoding', 'error')
            return redirect(request.url)

        conn = get_db()
        success = 0
        errors = []

        for i, row in enumerate(csv_input, start=2):
            # Skip completely empty rows
            if not any(cell.strip() for cell in row):
                continue
                
            row = [x.strip() for x in row]
            
            # Remove trailing empty columns
            while row and row[-1] == '':
                row.pop()

            if len(row) != 6:
                errors.append(f"Row {i}: Expected 6 columns, got {len(row)}. Data: {row}")
                continue
                    
            username, password, role, name, class_division, roll_no = row
            try:
                hashed_pw = generate_password_hash(password)
                conn.execute('''INSERT INTO users 
                    (username, password, role, name, class_division, roll_no) 
                    VALUES (?, ?, ?)''',
                    (username, hashed_pw, role, name, class_division, roll_no))
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

if __name__ == '__main__':
    app.run(debug=True)
