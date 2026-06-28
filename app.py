from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



# ------------------ MODELS ------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    student = db.relationship('Student', backref='user', uselist=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(200))
    class_division = db.Column(db.String(50))  # Class & Division
    day_scholar_hostel = db.Column(db.String(20))  # Day Scholar / Hostel
    father_mobile = db.Column(db.String(15))
    mother_mobile = db.Column(db.String(15))
    emergency_number = db.Column(db.String(15))
    email = db.Column(db.String(120))
    aadhaar_number = db.Column(db.String(20))
    siblings_in_school = db.Column(db.String(10))  # Yes/No
    current_address = db.Column(db.Text)
    permanent_address = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # ← This field is required

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    month = db.Column(db.String(20), nullable=False)
    total_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20))
    arrears = db.Column(db.Float, default=0.0)
    term1 = db.Column(db.Float, default=0.0)
    term2 = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)

class Discipline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    report_type = db.Column(db.String(50))  # White, Yellow, Red Report Card
    action_taken = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ CREATE DEFAULT USERS ------------------
def create_default_users():
    if User.query.filter_by(role='admin').first():
        return
    
    # Admin
    admin = User(
        username='admin',
        email='admin@college.com',
        password_hash=generate_password_hash('admin123'),
        role='admin'
    )
    
    # Teacher
    teacher = User(
        username='teacher1',
        email='teacher1@college.com',
        password_hash=generate_password_hash('teach123'),
        role='teacher'
    )
    
    db.session.add_all([admin, teacher])
    db.session.commit()
    print("Default users created: admin/admin123, teacher1/teach123")

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        print(f"Login attempt: username={username}, role={role}")  # Debug
        
        user = User.query.filter_by(username=username, role=role).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome {user.username}!')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials or wrong role selected')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully')
    return redirect(url_for('login'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match')
            return redirect(url_for('change_password'))

        if len(new_password) < 6:
            flash('Password must be at least 6 characters')
            return redirect(url_for('change_password'))

        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Password changed successfully')
        
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    return render_template('change_password.html')

# ------------------ DASHBOARDS ------------------
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))
    
    # Get counts for dashboard
    stats = {
        'students': Student.query.count(),
        'teachers': User.query.filter_by(role='teacher').count(),
        'users': User.query.count()
    }
    
    return render_template('admin_dashboard.html', user=current_user, stats=stats)

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Access denied')
        return redirect(url_for('index'))
    return render_template('teacher_dashboard.html')

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied')
        return redirect(url_for('index'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Student profile not found')
        return redirect(url_for('logout'))
    
    return render_template('student_dashboard.html', student=student)


UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/admin/student-control', methods=['GET', 'POST'])
@login_required
def admin_student_page_control():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # 1. Get all form data
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        roll_no = request.form.get('roll_no')
        class_division = request.form.get('class_division')
        day_scholar_hostel = request.form.get('day_scholar_hostel')
        father_mobile = request.form.get('father_mobile')
        mother_mobile = request.form.get('mother_mobile')
        emergency_number = request.form.get('emergency_number')
        email = request.form.get('email')
        aadhaar_number = request.form.get('aadhaar_number')
        siblings_in_school = request.form.get('siblings_in_school')
        current_address = request.form.get('current_address')
        permanent_address = request.form.get('permanent_address')
        photo = request.files.get('photo')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('admin_student_page_control'))
        
        filename = None
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # 2. Create User
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role='student'
        )
        db.session.add(new_user)
        db.session.flush()
        
        # 3. Create Student with all fields
        new_student = Student(
            name=name, 
            roll_no=roll_no,
            photo=filename,
            class_division=class_division,
            day_scholar_hostel=day_scholar_hostel,
            father_mobile=father_mobile,
            mother_mobile=mother_mobile,
            emergency_number=emergency_number,
            email=email,
            aadhaar_number=aadhaar_number,
            siblings_in_school=siblings_in_school,
            current_address=current_address,
            permanent_address=permanent_address,
            user_id=new_user.id
        )
        db.session.add(new_student)
        db.session.commit()
        
        flash('Student added successfully')
        return redirect(url_for('admin_student_page_control'))
    
    students = Student.query.all()
    return render_template('admin_student_page_control.html', students=students)

@app.route('/admin/delete-student/<int:student_id>')
@login_required
def delete_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(student_id)
    user = User.query.get(student.user_id)
    
    # Delete photo file
    if student.photo:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], student.photo)
        if os.path.exists(photo_path):
            os.remove(photo_path)
    
    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()
    flash('Student deleted', 'success')
    return redirect(url_for('admin_student_page_control'))



# ------------------ MAIN ------------------
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
        create_default_users()
    app.run(debug=True)
