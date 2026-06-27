from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ================= MODELS =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100))
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # admin, teacher, student
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False)

class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    course = db.Column(db.String(100))
    batch = db.Column(db.String(50))
    section = db.Column(db.String(10))
    photo = db.Column(db.String(200))
    fees = db.relationship('Fee', backref='student', lazy=True, cascade="all, delete-orphan")

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    name = db.Column(db.String(100))
    academic_year = db.Column(db.String(20))
    amount = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')

        if not role:
            flash('Please select a role')
            return redirect(url_for('login'))

        # Find user by username AND role
        user = User.query.filter_by(username=username, role=role).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials or wrong role selected')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# -------- ADMIN ROUTES --------
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role!= 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/student_page_control', methods=['GET', 'POST'])
@login_required
def admin_student_page_control():
    if current_user.role!= 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        roll_no = request.form.get('roll_no')
        password = request.form.get('password')
        course = request.form.get('course')
        batch = request.form.get('batch')
        section = request.form.get('section')
        email = request.form.get('email')
        photo = request.files.get('photo')

        if User.query.filter_by(username=roll_no).first():
            flash('Roll No already exists!', 'danger')
            return redirect(url_for('admin_student_page_control'))

        filename = None
        if photo and photo.filename!= '':
            filename = secure_filename(f"{roll_no}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Create login account
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=roll_no,
            email=email,
            password_hash=hashed_pw,
            role='student'
        )
        db.session.add(new_user)
        db.session.commit()

        # Create student profile
        new_student = StudentProfile(
            user_id=new_user.id,
            name=name,
            roll_no=roll_no,
            course=course,
            batch=batch,
            section=section,
            photo=filename
        )
        db.session.add(new_student)
        db.session.commit()

        flash('Student added successfully!', 'success')
        return redirect(url_for('admin_student_page_control'))

    students = StudentProfile.query.all()
    return render_template('admin_student_page_control.html', students=students)

# -------- TEACHER ROUTES --------
@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role!= 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher_dashboard.html')

# -------- STUDENT ROUTES --------
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role!= 'student':
        return redirect(url_for('login'))
    student = StudentProfile.query.filter_by(user_id=current_user.id).first()
    return render_template('student_dashboard.html', student=student)

# ================= INIT DB =================
def create_default_users():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
    if not User.query.filter_by(username='teacher1').first():
        teacher = User(
            username='teacher1',
            password_hash=generate_password_hash('teach123'),
            role='teacher'
        )
        db.session.add(teacher)
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        create_default_users()
    app.run(debug=True)
