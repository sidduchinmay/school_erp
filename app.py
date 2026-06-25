from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import csv
from io import StringIO
from sqlalchemy.orm import joinedload

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aps-erp-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aps_erp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# === MODELS ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    student_profile = db.relationship('Student', backref='user_account', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('student', uselist=False))
    roll_no = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(20))
    division = db.Column(db.String(10))
    
    academic_year = db.Column(db.String(20))
    hostel_status = db.Column(db.String(20))  # Day Scholar / Hostel
    father_mobile = db.Column(db.String(15))
    mother_mobile = db.Column(db.String(15))
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    user = db.relationship('User', backref=db.backref('student', uselist=False))
    
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
    # DO NOT PUT ANY relationship LINE HERE



class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    month = db.Column(db.String(20))  # April, May, June...
    present_days = db.Column(db.Integer, default=0)
    total_days = db.Column(db.Integer, default=0)
    student = db.relationship('Student', backref='attendance_records')

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    term = db.Column(db.String(20))  # MT-1, MT-2, Mid-Term, Annual
    subject = db.Column(db.String(50))
    marks_obtained = db.Column(db.Float)
    max_marks = db.Column(db.Float, default=100)
    student = db.relationship('Student', backref='exam_records')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    activity_name = db.Column(db.String(100))  # Gavel Club, Sports, Dance
    level = db.Column(db.String(50))  # School, Inter-school, State, National
    category = db.Column(db.String(50))  # Co/Extra Curricular, Talent Hunt
    student = db.relationship('Student', backref='activities')

class Discipline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    report_type = db.Column(db.String(50))  # White Report, Yellow Report, Red Report
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

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

    attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
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
    profile = TeacherProfile.query.filter_by(teacher_id=teacher.id).first()
    return render_template('teacher_dashboard_full.html', teacher=teacher, profile=profile)


@app.route('/admin/student/preview/<int:student_id>')
@login_required
def admin_student_preview(student_id):
    if current_user.role != 'admin': abort(403)
    
    student_obj = db.session.get(Student, student_id)
    if not student_obj:
        abort(404)
    
    class PreviewUser:
        def __init__(self, student):
            self.student = student
            # Use username if your User model has username, not email
            self.username = student.user.username if student.user else ''
            self.role = 'student'
    
    preview_user = PreviewUser(student_obj)
    return render_template('student_dashboard.html', current_user=preview_user)




@app.route('/admin/settings/update', methods=['POST'])
@login_required
def update_settings():
    if current_user.role!= 'admin':
        abort(403)
    for key in request.form:
        if key.startswith('setting_'):
            setting_key = key.replace('setting_', '')
            setting = Settings.query.filter_by(key=setting_key).first()
            if setting:
                setting.value = request.form[key]
    db.session.commit()
    flash('Settings updated')
    return redirect(url_for('admin_student_page_control'))

@app.route('/bulk_upload', methods=['GET', 'POST'])
@login_required
def bulk_upload():
    if current_user.role!= 'admin':
        abort(403)

    if request.method == 'GET':
        return render_template('bulk_upload.html')

    file = request.files['file']
    if not file:
        flash('No file selected')
        return redirect(request.url)

    stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_data = csv.DictReader(stream)

    count = 0
    for row in csv_data:
        roll_no = row['roll_no'].strip()

        if Student.query.filter_by(roll_no=roll_no).first():
            continue

        user = User(
            username=row['roll_no'].strip(),
            password_hash=generate_password_hash('1234'),
            role='student'
        )
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            roll_no=roll_no,
            name=row['name'].strip(),
            class_name=row['class_name'].strip(),
            division=row['division'].strip(),
            father_mobile=row.get('father_mobile', '').strip(),
            mother_mobile=row.get('mother_mobile', '').strip(),
            academic_year=row['academic_year'].strip()
        )
        db.session.add(student)
        count += 1

    db.session.commit()
    flash(f'{count} students uploaded successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/students')
@login_required
def admin_students_list():
    if current_user.role!= 'admin':
        abort(403)
    students = Student.query.all()
    return render_template('admin_students_list.html', students=students)

@app.route('/admin/add_teacher', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if current_user.role!= 'admin':
        abort(403)
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form['username']).first():
            user = User(
                username=request.form['username'],
                password_hash=generate_password_hash(request.form['password']),
                role='teacher'
            )
            db.session.add(user)
            db.session.flush()
            teacher = Teacher(
                user_id=user.id,
                name=request.form['name'],
                assigned_class=request.form['assigned_class'],
                assigned_division=request.form['assigned_division']
            )
            db.session.add(teacher)
            db.session.commit()
            flash('Teacher created successfully')
            return redirect(url_for('admin_dashboard'))
        flash('Username already exists')
    return render_template('add_teacher.html')

@app.route('/teacher/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role!= 'teacher':
        abort(403)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.assigned_class, division=teacher.assigned_division).all()
    if request.method == 'POST':
        for student in students:
            status = request.form.get(f'status_{student.id}', 'Present')
            att = Attendance(student_id=student.id, date=date.today(), status=status)
            db.session.add(att)
            if status == 'Absent':
                msg = f"Dear Parent, Your ward {student.name} is absent today {date.today()}. - APS"
                send_sms(student.father_mobile, msg)
        db.session.commit()
        flash('Attendance marked and SMS sent')
        return redirect(url_for('teacher_dashboard'))
    return render_template('mark_attendance.html', students=students, teacher=teacher, date=date)

@app.route('/teacher/enter_marks', methods=['GET', 'POST'])
@login_required
def enter_marks():
    if current_user.role!= 'teacher':
        abort(403)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.assigned_class, division=teacher.assigned_division).all()
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        subject = request.form['subject']
        max_marks = float(request.form['max_marks'])
        for student in students:
            marks = request.form.get(f'marks_{student.id}')
            if marks:
                exam = Exam(
                    student_id=student.id,
                    exam_name=exam_name,
                    subject=subject,
                    marks=int(marks),
                    date=date.today()
                )
                db.session.add(exam)
        db.session.commit()
        flash(f'{exam_name} marks saved')
        return redirect(url_for('teacher_dashboard'))
    return render_template('enter_marks.html', students=students, teacher=teacher)

@app.route('/admin/student/<int:student_id>')
@login_required
def admin_student_view(student_id):
    if current_user.role!= 'admin':
        abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    attendance = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc()).all()
    exams = Exam.query.filter_by(student_id=student_id).all()
    return render_template('admin_student_view.html', student=student, attendance=attendance, exams=exams)

from sqlalchemy.orm import joinedload

@app.route('/admin/student_page_control', methods=['GET', 'POST'])
@login_required
def admin_student_page_control():
    if current_user.role!= 'admin':
        abort(403)
    
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        course = request.form['course']
        batch = request.form['batch']
        section = request.form['section']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('admin_student_page_control'))
            
        # Create user first
        new_user = User(email=email, role='student')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()  # Get new_user.id
        
        # Handle photo
        filename = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Create student and link to user
        new_student = Student(
            name=name, 
            roll_no=roll_no, 
            course=course, 
            batch=batch, 
            section=section, 
            photo=filename,
            user_id=new_user.id  # THIS LINE LINKS THEM
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Student added successfully')
        return redirect(url_for('admin_student_page_control'))

    settings = Settings.query.all()
    # Use joinedload to prevent N+1 queries for student.user.email
    students = Student.query.options(joinedload(Student.user)).all()
    return render_template('admin_student_page_control.html', settings=settings, students=students)

@app.route('/admin/toggle_section', methods=['POST'])
@login_required
def toggle_section():
    if current_user.role!= 'admin':
        abort(403)
    setting = db.session.get(Settings, request.form['id'])
    setting.value = 'false' if setting.value == 'true' else 'true'
    db.session.commit()
    return redirect(url_for('admin_student_page_control'))

@app.route('/admin/student/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def admin_student_edit(student_id):
    if current_user.role!= 'admin':
        abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        for field in request.form:
            if hasattr(student, field):
                setattr(student, field, request.form[field])
        db.session.commit()
        flash('Student updated')
        return redirect(url_for('admin_student_page_control'))
    return render_template('admin_student_edit.html', student=student)
@app.route('/admin/student/delete/<int:student_id>')
@login_required
def admin_student_delete(student_id):
    if current_user.role!= 'admin':
        abort(403)
    
    student = db.session.get(Student, student_id) or abort(404)
    
    # Delete linked user account too
    if student.user:
        db.session.delete(student.user)
    
    # Delete student photo file if exists
    if student.photo:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], student.photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)
    
    db.session.delete(student)
    db.session.commit()
    flash(f'Student {student.name} deleted')
    return redirect(url_for('admin_student_page_control'))


@app.route('/admin/fee/add/<int:student_id>', methods=['GET', 'POST'])
@login_required
def admin_fee_add(student_id):
    if current_user.role!= 'admin':
        abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        fee = Fee(
            name=request.form['name'],
            amount=float(request.form['amount']),
            paid_amount=float(request.form.get('paid_amount', 0)),
            academic_year=request.form['academic_year'],
            arrears=float(request.form.get('arrears', 0)),
            term1=float(request.form.get('term1', 0)),
            term2=float(request.form.get('term2', 0)),
            student_id=student.id
        )
        db.session.add(fee)
        db.session.commit()
        flash('Fee added')
        return redirect(url_for('admin_student_page_control'))
    return render_template('admin_fee_add.html', student=student)

@app.route('/admin/fee/delete/<int:fee_id>')
@login_required
def admin_fee_delete(fee_id):
    if current_user.role!= 'admin':
        abort(403)
    fee = db.session.get(Fee, fee_id) or abort(404)
    db.session.delete(fee)
    db.session.commit()
    return redirect(request.referrer or url_for('admin_student_page_control'))

@app.route('/create_student', methods=['GET', 'POST'])
@login_required
def create_student():
    if current_user.role!= 'admin':
        abort(403)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('create_student'))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='student'
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'Student {username} created')
        return redirect(url_for('admin_dashboard'))

    return render_template('create_student.html')

@app.route('/setup')
def setup():
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return "Admin created successfully. Found in DB. Now go to /login"
        else:
            return "Admin already exists. Try login."
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/admin/student/<int:student_id>/attendance', methods=['GET','POST'])
@login_required
def admin_attendance(student_id):
    if current_user.role != 'admin': abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        for month in ['April','May','June','July','August','September','October','November','December','January','February','March']:
            present = request.form.get(f'{month}_present', 0)
            total = request.form.get(f'{month}_total', 0)
            att = Attendance.query.filter_by(student_id=student_id, month=month).first()
            if not att:
                att = Attendance(student_id=student_id, month=month)
                db.session.add(att)
            att.present_days = int(present)
            att.total_days = int(total)
        db.session.commit()
        flash('Attendance updated')
        return redirect(url_for('admin_student_page_control'))
    return render_template('admin_attendance.html', student=student)







@app.route('/admin/student/<int:student_id>/exam', methods=['GET','POST'])
@login_required
def admin_exam(student_id):
    if current_user.role != 'admin': abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        term = request.form['term']
        subject = request.form['subject']
        marks = request.form['marks']
        exam = Exam(student_id=student_id, term=term, subject=subject, marks_obtained=marks)
        db.session.add(exam)
        db.session.commit()
        flash('Exam marks added')
    return render_template('admin_exam.html', student=student)


@app.route('/check_users')
def check_users():
    users = User.query.all()
    return "<br>".join([f"{u.username} - {u.role}" for u in users]) or "No users found"

# === INIT DB - MUST BE LAST ===
# === INIT DB - MUST BE LAST ===
with app.app_context():
    db.create_all()
    init_settings()
    
    # AUTO-CREATE ADMIN IF NO USERS EXIST
    if User.query.count() == 0:
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(">>> ADMIN CREATED: username=admin password=admin123 <<<")
    else:
        print(f">>> Found {User.query.count()} users in database <<<")
    
    print(app.url_map)

@app.route('/')
def home():
    return "School app working!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
=======
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import csv
from io import StringIO
from sqlalchemy.orm import joinedload

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aps-erp-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aps_erp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# === MODELS ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    student_profile = db.relationship('Student', backref='user_account', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('student', uselist=False))
    roll_no = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(20))
    division = db.Column(db.String(10))
    
    academic_year = db.Column(db.String(20))
    hostel_status = db.Column(db.String(20))  # Day Scholar / Hostel
    father_mobile = db.Column(db.String(15))
    mother_mobile = db.Column(db.String(15))
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    user = db.relationship('User', backref=db.backref('student', uselist=False))
    
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
    # DO NOT PUT ANY relationship LINE HERE



class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    month = db.Column(db.String(20))  # April, May, June...
    present_days = db.Column(db.Integer, default=0)
    total_days = db.Column(db.Integer, default=0)
    student = db.relationship('Student', backref='attendance_records')

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    term = db.Column(db.String(20))  # MT-1, MT-2, Mid-Term, Annual
    subject = db.Column(db.String(50))
    marks_obtained = db.Column(db.Float)
    max_marks = db.Column(db.Float, default=100)
    student = db.relationship('Student', backref='exam_records')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    activity_name = db.Column(db.String(100))  # Gavel Club, Sports, Dance
    level = db.Column(db.String(50))  # School, Inter-school, State, National
    category = db.Column(db.String(50))  # Co/Extra Curricular, Talent Hunt
    student = db.relationship('Student', backref='activities')

class Discipline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    report_type = db.Column(db.String(50))  # White Report, Yellow Report, Red Report
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

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

    attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
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
    profile = TeacherProfile.query.filter_by(teacher_id=teacher.id).first()
    return render_template('teacher_dashboard_full.html', teacher=teacher, profile=profile)


@app.route('/admin/student/preview/<int:student_id>')
@login_required
def admin_student_preview(student_id):
    if current_user.role != 'admin': abort(403)
    
    student_obj = db.session.get(Student, student_id)
    if not student_obj:
        abort(404)
    
    class PreviewUser:
        def __init__(self, student):
            self.student = student
            # Use username if your User model has username, not email
            self.username = student.user.username if student.user else ''
            self.role = 'student'
    
    preview_user = PreviewUser(student_obj)
    return render_template('student_dashboard.html', current_user=preview_user)




@app.route('/admin/settings/update', methods=['POST'])
@login_required
def update_settings():
    if current_user.role!= 'admin':
        abort(403)
    for key in request.form:
        if key.startswith('setting_'):
            setting_key = key.replace('setting_', '')
            setting = Settings.query.filter_by(key=setting_key).first()
            if setting:
                setting.value = request.form[key]
    db.session.commit()
    flash('Settings updated')
    return redirect(url_for('admin_student_page_control'))

@app.route('/bulk_upload', methods=['GET', 'POST'])
@login_required
def bulk_upload():
    if current_user.role!= 'admin':
        abort(403)

    if request.method == 'GET':
        return render_template('bulk_upload.html')

    file = request.files['file']
    if not file:
        flash('No file selected')
        return redirect(request.url)

    stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_data = csv.DictReader(stream)

    count = 0
    for row in csv_data:
        roll_no = row['roll_no'].strip()

        if Student.query.filter_by(roll_no=roll_no).first():
            continue

        user = User(
            username=row['roll_no'].strip(),
            password_hash=generate_password_hash('1234'),
            role='student'
        )
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            roll_no=roll_no,
            name=row['name'].strip(),
            class_name=row['class_name'].strip(),
            division=row['division'].strip(),
            father_mobile=row.get('father_mobile', '').strip(),
            mother_mobile=row.get('mother_mobile', '').strip(),
            academic_year=row['academic_year'].strip()
        )
        db.session.add(student)
        count += 1

    db.session.commit()
    flash(f'{count} students uploaded successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/students')
@login_required
def admin_students_list():
    if current_user.role!= 'admin':
        abort(403)
    students = Student.query.all()
    return render_template('admin_students_list.html', students=students)

@app.route('/admin/add_teacher', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if current_user.role!= 'admin':
        abort(403)
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form['username']).first():
            user = User(
                username=request.form['username'],
                password_hash=generate_password_hash(request.form['password']),
                role='teacher'
            )
            db.session.add(user)
            db.session.flush()
            teacher = Teacher(
                user_id=user.id,
                name=request.form['name'],
                assigned_class=request.form['assigned_class'],
                assigned_division=request.form['assigned_division']
            )
            db.session.add(teacher)
            db.session.commit()
            flash('Teacher created successfully')
            return redirect(url_for('admin_dashboard'))
        flash('Username already exists')
    return render_template('add_teacher.html')

@app.route('/teacher/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role!= 'teacher':
        abort(403)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.assigned_class, division=teacher.assigned_division).all()
    if request.method == 'POST':
        for student in students:
            status = request.form.get(f'status_{student.id}', 'Present')
            att = Attendance(student_id=student.id, date=date.today(), status=status)
            db.session.add(att)
            if status == 'Absent':
                msg = f"Dear Parent, Your ward {student.name} is absent today {date.today()}. - APS"
                send_sms(student.father_mobile, msg)
        db.session.commit()
        flash('Attendance marked and SMS sent')
        return redirect(url_for('teacher_dashboard'))
    return render_template('mark_attendance.html', students=students, teacher=teacher, date=date)

@app.route('/teacher/enter_marks', methods=['GET', 'POST'])
@login_required
def enter_marks():
    if current_user.role!= 'teacher':
        abort(403)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.assigned_class, division=teacher.assigned_division).all()
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        subject = request.form['subject']
        max_marks = float(request.form['max_marks'])
        for student in students:
            marks = request.form.get(f'marks_{student.id}')
            if marks:
                exam = Exam(
                    student_id=student.id,
                    exam_name=exam_name,
                    subject=subject,
                    marks=int(marks),
                    date=date.today()
                )
                db.session.add(exam)
        db.session.commit()
        flash(f'{exam_name} marks saved')
        return redirect(url_for('teacher_dashboard'))
    return render_template('enter_marks.html', students=students, teacher=teacher)

@app.route('/admin/student/<int:student_id>')
@login_required
def admin_student_view(student_id):
    if current_user.role!= 'admin':
        abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    attendance = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc()).all()
    exams = Exam.query.filter_by(student_id=student_id).all()
    return render_template('admin_student_view.html', student=student, attendance=attendance, exams=exams)

from sqlalchemy.orm import joinedload

@app.route('/admin/student_page_control', methods=['GET', 'POST'])
@login_required
def admin_student_page_control():
    if current_user.role!= 'admin':
        abort(403)
    
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        course = request.form['course']
        batch = request.form['batch']
        section = request.form['section']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('admin_student_page_control'))
            
        # Create user first
        new_user = User(email=email, role='student')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()  # Get new_user.id
        
        # Handle photo
        filename = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Create student and link to user
        new_student = Student(
            name=name, 
            roll_no=roll_no, 
            course=course, 
            batch=batch, 
            section=section, 
            photo=filename,
            user_id=new_user.id  # THIS LINE LINKS THEM
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Student added successfully')
        return redirect(url_for('admin_student_page_control'))

    settings = Settings.query.all()
    # Use joinedload to prevent N+1 queries for student.user.email
    students = Student.query.options(joinedload(Student.user)).all()
    return render_template('admin_student_page_control.html', settings=settings, students=students)

@app.route('/admin/toggle_section', methods=['POST'])
@login_required
def toggle_section():
    if current_user.role!= 'admin':
        abort(403)
    setting = db.session.get(Settings, request.form['id'])
    setting.value = 'false' if setting.value == 'true' else 'true'
    db.session.commit()
    return redirect(url_for('admin_student_page_control'))

@app.route('/admin/student/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def admin_student_edit(student_id):
    if current_user.role!= 'admin':
        abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        for field in request.form:
            if hasattr(student, field):
                setattr(student, field, request.form[field])
        db.session.commit()
        flash('Student updated')
        return redirect(url_for('admin_student_page_control'))
    return render_template('admin_student_edit.html', student=student)
@app.route('/admin/student/delete/<int:student_id>')
@login_required
def admin_student_delete(student_id):
    if current_user.role!= 'admin':
        abort(403)
    
    student = db.session.get(Student, student_id) or abort(404)
    
    # Delete linked user account too
    if student.user:
        db.session.delete(student.user)
    
    # Delete student photo file if exists
    if student.photo:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], student.photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)
    
    db.session.delete(student)
    db.session.commit()
    flash(f'Student {student.name} deleted')
    return redirect(url_for('admin_student_page_control'))


@app.route('/admin/fee/add/<int:student_id>', methods=['GET', 'POST'])
@login_required
def admin_fee_add(student_id):
    if current_user.role!= 'admin':
        abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        fee = Fee(
            name=request.form['name'],
            amount=float(request.form['amount']),
            paid_amount=float(request.form.get('paid_amount', 0)),
            academic_year=request.form['academic_year'],
            arrears=float(request.form.get('arrears', 0)),
            term1=float(request.form.get('term1', 0)),
            term2=float(request.form.get('term2', 0)),
            student_id=student.id
        )
        db.session.add(fee)
        db.session.commit()
        flash('Fee added')
        return redirect(url_for('admin_student_page_control'))
    return render_template('admin_fee_add.html', student=student)

@app.route('/admin/fee/delete/<int:fee_id>')
@login_required
def admin_fee_delete(fee_id):
    if current_user.role!= 'admin':
        abort(403)
    fee = db.session.get(Fee, fee_id) or abort(404)
    db.session.delete(fee)
    db.session.commit()
    return redirect(request.referrer or url_for('admin_student_page_control'))

@app.route('/create_student', methods=['GET', 'POST'])
@login_required
def create_student():
    if current_user.role!= 'admin':
        abort(403)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('create_student'))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='student'
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'Student {username} created')
        return redirect(url_for('admin_dashboard'))

    return render_template('create_student.html')

@app.route('/setup')
def setup():
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return "Admin created successfully. Found in DB. Now go to /login"
        else:
            return "Admin already exists. Try login."
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/admin/student/<int:student_id>/attendance', methods=['GET','POST'])
@login_required
def admin_attendance(student_id):
    if current_user.role != 'admin': abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        for month in ['April','May','June','July','August','September','October','November','December','January','February','March']:
            present = request.form.get(f'{month}_present', 0)
            total = request.form.get(f'{month}_total', 0)
            att = Attendance.query.filter_by(student_id=student_id, month=month).first()
            if not att:
                att = Attendance(student_id=student_id, month=month)
                db.session.add(att)
            att.present_days = int(present)
            att.total_days = int(total)
        db.session.commit()
        flash('Attendance updated')
        return redirect(url_for('admin_student_page_control'))
    return render_template('admin_attendance.html', student=student)







@app.route('/admin/student/<int:student_id>/exam', methods=['GET','POST'])
@login_required
def admin_exam(student_id):
    if current_user.role != 'admin': abort(403)
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == 'POST':
        term = request.form['term']
        subject = request.form['subject']
        marks = request.form['marks']
        exam = Exam(student_id=student_id, term=term, subject=subject, marks_obtained=marks)
        db.session.add(exam)
        db.session.commit()
        flash('Exam marks added')
    return render_template('admin_exam.html', student=student)


@app.route('/check_users')
def check_users():
    users = User.query.all()
    return "<br>".join([f"{u.username} - {u.role}" for u in users]) or "No users found"

# === INIT DB - MUST BE LAST ===
# === INIT DB - MUST BE LAST ===
with app.app_context():
    db.create_all()
    init_settings()
    
    # AUTO-CREATE ADMIN IF NO USERS EXIST
    if User.query.count() == 0:
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(">>> ADMIN CREATED: username=admin password=admin123 <<<")
    else:
        print(f">>> Found {User.query.count()} users in database <<<")
    
    print(app.url_map)

@app.route('/')
def home():
    return "School app working!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
>>>>>>> aeb331e123aa175af404568fbea9eb5603cad545
