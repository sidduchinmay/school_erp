import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # ← FIXED THIS TYPO
from flask import Flask, render_template, request, redirect, url_for, session

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')  # <-- This line
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)
login_manager.init_app(app)

# -------------------- MODELS --------------------
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
    class_division = db.Column(db.String(50))
    day_scholar_hostel = db.Column(db.String(20))
    father_mobile = db.Column(db.String(15))
    mother_mobile = db.Column(db.String(15))
    emergency_number = db.Column(db.String(15))
    email = db.Column(db.String(120))
    aadhaar_number = db.Column(db.String(20))
    siblings_in_school = db.Column(db.String(10))
    current_address = db.Column(db.Text)
    permanent_address = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# -------------------- ROUTES --------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role!= 'admin':
        flash('Access denied')
        return redirect(url_for('index'))
    return render_template('admin_dashboard.html')

@app.route('/admin/student-control', methods=['GET', 'POST'])
@login_required
def admin_student_page_control():
    if current_user.role!= 'admin':
        flash('Access denied')
        return redirect(url_for('index'))
    if request.method == 'POST':
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
        if photo and photo.filename!= '' and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_user = User(username=username, password=generate_password_hash(password), role='student')
        db.session.add(new_user)
        db.session.flush()

        new_student = Student(
            name=name, roll_no=roll_no, photo=filename, class_division=class_division,
            day_scholar_hostel=day_scholar_hostel, father_mobile=father_mobile,
            mother_mobile=mother_mobile, emergency_number=emergency_number, email=email,
            aadhaar_number=aadhaar_number, siblings_in_school=siblings_in_school,
            current_address=current_address, permanent_address=permanent_address,
            user_id=new_user.id
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Student added successfully')
        return redirect(url_for('admin_student_page_control'))

    students = Student.query.all()
    return render_template('admin_student_page_control.html', students=students)



@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch student data from DB
    student = get_student_by_id(session['user_id'])  # your DB function
    is_admin = session.get('role') == 'admin'
    
    return render_template('student_dashboard.html', 
                           student=student, 
                           is_admin=is_admin)

@app.route('/admin/update_erp_data', methods=['POST'])
def update_erp_data():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    
    data = request.json  # table data from JS
    # Save to DB here
    return {"status": "success"}

# -------------------- CREATE DB + ADMIN --------------------
def create_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
            db.session.commit()
            print('Default admin created: username=admin, password=admin123')

# Run this on startup for Render/Gunicorn
with app.app_context():
    create_admin()

if __name__ == '__main__':
    app.run(debug=True)
