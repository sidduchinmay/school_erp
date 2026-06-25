from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import csv
from io import StringIO
from sqlalchemy.orm import joinedload
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aps-erp-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aps_erp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# === MODELS ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    user = db.relationship('User', backref=db.backref('student', uselist=False))
    roll_no = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(20))
    division = db.Column(db.String(10))
    academic_year = db.Column(db.String(20))
    hostel_status = db.Column(db.String(20))
    father_mobile = db.Column(db.String(15))
    mother_mobile = db.Column(db.String(15))
    photo = db.Column(db.String(300))

    fees = db.relationship('Fee', backref='student', lazy=True)

    # Accolades/Certificate
    accolades_school_level = db.Column(db.Text)
    accolades_inter_school = db.Column(db.Text)
    accolades_state = db.Column(db.Text)
    accolades_national = db.Column(db.Text)
    accolades_international = db.Column(db.Text)

    # Applications
    application_gavel_club = db.Column(db.String(10), default='No')
    application_talent_hunt = db.Column(db.String(10), default='No')
    application_photography = db.Column(db.String(10), default='No')
    application_chess = db.Column(db.String(10), default='No')
    application_sports_yoga = db.Column(db.String(10), default='No')
    application_literary_cultural = db.Column(db.String(10), default='No')
    application_clubs_leadership = db.Column(db.String(10), default='No')
    application_social_work = db.Column(db.String(10), default='No')
    application_dance_music = db.Column(db.String(10), default='No')
    application_quiz_exhibition = db.Column(db.String(10), default='No')

    # Participation
    activity_sports = db.Column(db.String(10), default='No')
    activity_gavel_club = db.Column(db.String(10), default='No')
    activity_talent_hunt = db.Column(db.String(10), default='No')
    activity_photograph = db.Column(db.String(10), default='No')
    activity_yoga = db.Column(db.String(10), default='No')
    activity_dance_music = db.Column(db.String(10), default='No')
    activity_ncc_scouts = db.Column(db.String(10), default='No')

    # Discipline
    discipline_white_report = db.Column(db.Text)
    discipline_yellow_report = db.Column(db.Text)
    discipline_red_report = db.Column(db.Text)
    discipline_actions_taken = db.Column(db.Text)
    parents_meetings = db.Column(db.Text)
    counselling_attended = db.Column(db.Text)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0)
    academic_year = db.Column(db.String(20))
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    arrears = db.Column(db.Float, default=0)
    term1 = db.Column(db.Float, default=0)
    term2 = db.Column(db.Float, default=0)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    month = db.Column(db.String(20))
    present_days = db.Column(db.Integer, default=0)
    total_days = db.Column(db.Integer, default=0)
    student = db.relationship('Student', backref='attendance_records')

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    term = db.Column(db.String(20))
    subject = db.Column(db.String(50))
    marks_obtained = db.Column(db.Float)
    max_marks = db.Column(db.Float, default=100)
    student = db.relationship('Student', backref='exam_records')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    activity_name = db.Column(db.String(100))
    level = db.Column(db.String(50))
    category = db.Column(db.String(50))
    student = db.relationship('Student', backref='activities')

class Discipline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    report_type = db.Column(db.String(50))
    incident_date = db.Column(db.Date)
    description = db.Column(db.Text)
    action_taken = db.Column(db.Text)
    student = db.relationship('Student', backref='discipline_records')

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), nullable=False)
    assigned_class = db.Column(db.String(10))
    assigned_division = db.Column(db.String(5))

class TeacherProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    full_name = db.Column(db.String(100))
    current_address = db.Column(db.Text)
    permanent_address = db.Column(db.Text)
    aadhar_card = db.Column(db.String(20))
    husband_father_name = db.Column(db.String(100))
    cbse_no = db.Column(db.String(30))
    phone_number = db.Column(db.String(15))
    emergency_phone_1 = db.Column(db.String(15))
    emergency_phone_2 = db.Column(db.String(15))
    photo_url = db.Column(db.String(300))
    resume_url = db.Column(db.String(300))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(10), default='true')
    label = db.Column(db.String(100))

def init_settings():
    defaults = [
        ('show_profile', 'Profile Box'),
        ('show_attendance_graph', 'Attendance - Graph'),
        ('show_attendance_absence', 'Attendance - Absence Details'),
        ('show_attendance_previous', 'Attendance - Previous Years'),
        ('show_attendance_monthwise', 'Attendance - Month Wise'),
        ('show_attendance_exam', 'Attendance - Exam Attendance'),
        ('show_attendance_total', 'Attendance - Total %'),
        ('show_attendance_mandatory', 'Attendance - Mandatory Activity'),
        ('show_term_marks', 'Term-wise Marks MT-1 to MT-6'),
        ('show_accolades', 'Accolades/Certificate Box'),
        ('show_applications', 'Applications Box'),
        ('show_participation', 'Participation in Co/Extra Curricular'),
        ('show_discipline', 'Discipline Box'),
        ('show_fees', 'Fee Details Box'),
        ('show_schedules', 'Schedules Box'),
        ('show_calendar', 'View Calendar Box'),
        ('show_downloads', 'View/Downloads Box')
    ]
    for key, label in defaults:
        if not Settings.query.filter_by(key=key).first():
            db.session.add(Settings(key=key, value='true', label=label))
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def send_sms(mobile, message):
    print(f"SMS to {mobile}: {message}")

# === ROUTES ===
@app.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif current_user.role == 'student':
        return redirect(url_for('student_dashboard'))
    return "Role not recognized"

# General login for admin/teacher
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.role == 'student':
                flash('Students must use Student Login page')
                return redirect(url_for('student_login'))
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

# NEW: Separate student login page
@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username'] # Usually roll_no
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.role!= 'student':
                flash('This login is for students only')
                return redirect(url_for('student_login'))
            login_user(user)
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid Roll No or Password')

    return render_template('student_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/whoami')
@login_required
def whoami():
    return f"Username: {current_user.username} <br> Role: {current_user.role}"

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role!= 'admin':
        abort(403)

    stats = {
        'total_students': Student.query.count(),
        'total_teachers': Teacher.query.count(),
        'total_users': User.query.count()
    }
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            flash('Student profile not found')
            return redirect(url_for('logout'))
    elif current_user.role == 'admin':
        student_id = request.args.get('id', type=int)
        if student_id:
            student = db.session.get(Student, student_id)
        else:
            student = Student.query.first()
        if not student:
            return "No students in database"
    else:
        abort(403)

    attendance = Attendance.query.filter_by(student_id=student.id).all()
    exams = Exam.query.filter_by(student_id=student.id).all()
    fees = Fee.query.filter_by(student_id=student.id).all()
    settings = {s.key: s.value for s in Settings.query.all()}

    return render_template('student_dashboard.html',
                           student=student,
                           attendance=attendance,
                           exams=exams,
                           fees=fees,
                           settings=settings)

@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role!= 'teacher':
        abort(403)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Teacher profile not found')
        return redirect(url_for('logout'))
    profile = TeacherProfile.query.filter_by(teacher_id=teacher.id).first()
    return render_template('teacher_dashboard_full.html', teacher=teacher, profile=profile)

# Keep all your other admin routes here...
# [I'll skip them for brevity, but keep them from your original code]

@app.route('/setup')
def setup():
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return "Admin created. Go to /login"
        else:
            return "Admin already exists. Try login."
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/check_users')
def check_users():
    users = User.query.all()
    return "<br>".join([f"{u.username} - {u.role}" for u in users]) or "No users found"

# === INIT DB ===
with app.app_context():
    db.create_all()
    init_settings()

    if User.query.count() == 0:
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(">>> ADMIN CREATED: username=admin password=admin123 <<<")

    print(app.url_map)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
