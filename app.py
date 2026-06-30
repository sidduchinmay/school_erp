from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-real-random-key-12345'  # Important for sessions

# ========== DATABASE HELPER ==========
def get_db_connection():
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn

def check_user(username, password):
    """
    Check if user exists. 
    TODO: Replace with real password hashing later.
    """
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ? AND password = ?', 
        (username, password)
    ).fetchone()
    conn.close()
    if user:
        return dict(user)  # Convert Row to dict
    return None

def get_student_by_id(user_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(student) if student else None

# ========== ROUTES ==========
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = check_user(username, password)
        
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('student_dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")
    
    # GET request
    if 'user_id' in session:
        return redirect(url_for('student_dashboard'))
    return render_template('login.html')

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student = get_student_by_id(session['user_id'])
    if not student:
        session.clear()
        return redirect(url_for('login'))
    
    is_admin = session.get('role') == 'admin'
    
    return render_template('student_dashboard.html', 
                           student=student, 
                           is_admin=is_admin)

@app.route('/admin/update_erp_data', methods=['POST'])
def update_erp_data():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    
    data = request.json
    # TODO: Save 'data' to DB here
    print("Admin saved:", data)  # For Render logs
    
    return {"status": "success", "message": "Data updated"}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ========== RUN ==========
if __name__ == '__main__':
    # For local testing only. Render uses gunicorn
    app.run(debug=True, host='0.0.0.0', port=5000)
