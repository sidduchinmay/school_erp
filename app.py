from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'aps-erp-secret-key-2025-26' # Change this

def get_db_connection():
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_user(username, password, role):
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username =? AND password =? AND role =?',
        (username, password, role)
    ).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id =?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_erp_data():
    conn = get_db_connection()
    data = conn.execute('SELECT * FROM erp_data WHERE id = 1').fetchone()
    conn.close()
    return dict(data) if data else {}

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
        role = request.form['role'] # admin, student, teacher

        user = check_user(username, password, role)
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials or role")

    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    erp_data = get_all_erp_data()
    is_admin = session.get('role') == 'admin'

    return render_template('student_dashboard.html',
                           user=user,
                           erp_data=erp_data,
                           is_admin=is_admin)

@app.route('/admin/update_erp', methods=['POST'])
def update_erp():
    if session.get('role')!= 'admin':
        return "Unauthorized", 403

    data = request.json
    conn = get_db_connection()
    conn.execute('''
        UPDATE erp_data SET
        fee_payment=?, attendance=?, academic_progress=?, accolades=?,
        applications=?, participation=?, schedules=?, view_calendar=?, downloads=?,
        discipline=?, parents_meetings=?, counselling=?
        WHERE id = 1
    ''', (
        data.get('fee_payment'), data.get('attendance'), data.get('academic_progress'),
        data.get('accolades'), data.get('applications'), data.get('participation'),
        data.get('schedules'), data.get('view_calendar'), data.get('downloads'),
        data.get('discipline'), data.get('parents_meetings'), data.get('counselling')
    ))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
