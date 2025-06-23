import os
import uuid
import math
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secretkey'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["syllabusdb"]
courses_col = db["syllabus"]
users_col = db["users"]

# Initialize default admin
def initialize_admin():
    if not users_col.find_one({'username': 'pratham'}):
        users_col.insert_one({
            'username': 'pratham',
            'password': generate_password_hash('pvrathod003'),
            'role': 'admin'
        })

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('role') == 'admin'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_pdf_file(pdf_file):
    ext = pdf_file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    pdf_file.save(filepath)
    return unique_filename

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/courses')
def index():
    page = int(request.args.get('page', 1))
    per_page = 6
    skip = (page - 1) * per_page

    total_courses = courses_col.count_documents({})
    total_pages = math.ceil(total_courses / per_page)

    courses = list(courses_col.find().skip(skip).limit(per_page))
    return render_template('index.html', courses=courses, current_page=page, total_pages=total_pages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_col.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
def add():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        credits = int(request.form.get('credits', 0))
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = ''
        if pdf_file and allowed_file(pdf_file.filename):
            filename = save_pdf_file(pdf_file)

        courses_col.insert_one({
            'course_name': course_name,
            'instructor': instructor,
            'semester': semester,
            'credits': credits,
            'topics': topics,
            'pdf_filename': filename
        })

        flash('Course added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add.html')

@app.route('/edit/<string:id>', methods=['GET', 'POST'])
def edit(id):
    if not is_logged_in():
        return redirect(url_for('login'))

    try:
        course = courses_col.find_one({'_id': ObjectId(id)})
    except:
        flash('Invalid course ID.', 'danger')
        return redirect(url_for('index'))

    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        credits = int(request.form.get('credits', 0))
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = course.get('pdf_filename', '')
        if pdf_file and allowed_file(pdf_file.filename):
            if filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = save_pdf_file(pdf_file)

        courses_col.update_one({'_id': ObjectId(id)}, {
            '$set': {
                'course_name': course_name,
                'instructor': instructor,
                'semester': semester,
                'credits': credits,
                'topics': topics,
                'pdf_filename': filename
            }
        })

        flash('Course updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('edit.html', course=course)

@app.route('/delete/<string:id>')
def delete(id):
    if not is_logged_in() or not is_admin():
        flash('Only admin can delete courses.', 'danger')
        return redirect(url_for('index'))

    try:
        course = courses_col.find_one({'_id': ObjectId(id)})
    except:
        flash('Invalid course ID.', 'danger')
        return redirect(url_for('index'))

    if course:
        if course.get('pdf_filename'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], course['pdf_filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        courses_col.delete_one({'_id': ObjectId(id)})
        flash('Course deleted successfully!', 'success')
    else:
        flash('Course not found.', 'danger')

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

import os
import uuid
import math
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secretkey'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["syllabusdb"]
courses_col = db["syllabus"]
users_col = db["users"]

# Initialize default admin
def initialize_admin():
    if not users_col.find_one({'username': 'pratham'}):
        users_col.insert_one({
            'username': 'pratham',
            'password': generate_password_hash('pvrathod003'),
            'role': 'admin'
        })

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('role') == 'admin'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_pdf_file(pdf_file):
    ext = pdf_file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    pdf_file.save(filepath)
    return unique_filename

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/courses')
def index():
    page = int(request.args.get('page', 1))
    per_page = 6
    skip = (page - 1) * per_page

    total_courses = courses_col.count_documents({})
    total_pages = math.ceil(total_courses / per_page)

    courses = list(courses_col.find().skip(skip).limit(per_page))
    return render_template('index.html', courses=courses, current_page=page, total_pages=total_pages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_col.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
def add():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        credits = int(request.form.get('credits', 0))
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = ''
        if pdf_file and allowed_file(pdf_file.filename):
            filename = save_pdf_file(pdf_file)

        courses_col.insert_one({
            'course_name': course_name,
            'instructor': instructor,
            'semester': semester,
            'credits': credits,
            'topics': topics,
            'pdf_filename': filename
        })

        flash('Course added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add.html')

@app.route('/edit/<string:id>', methods=['GET', 'POST'])
def edit(id):
    if not is_logged_in():
        return redirect(url_for('login'))

    try:
        course = courses_col.find_one({'_id': ObjectId(id)})
    except:
        flash('Invalid course ID.', 'danger')
        return redirect(url_for('index'))

    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        credits = int(request.form.get('credits', 0))
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = course.get('pdf_filename', '')
        if pdf_file and allowed_file(pdf_file.filename):
            if filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = save_pdf_file(pdf_file)

        courses_col.update_one({'_id': ObjectId(id)}, {
            '$set': {
                'course_name': course_name,
                'instructor': instructor,
                'semester': semester,
                'credits': credits,
                'topics': topics,
                'pdf_filename': filename
            }
        })

        flash('Course updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('edit.html', course=course)

@app.route('/delete/<string:id>')
def delete(id):
    if not is_logged_in() or not is_admin():
        flash('Only admin can delete courses.', 'danger')
        return redirect(url_for('index'))

    try:
        course = courses_col.find_one({'_id': ObjectId(id)})
    except:
        flash('Invalid course ID.', 'danger')
        return redirect(url_for('index'))

    if course:
        if course.get('pdf_filename'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], course['pdf_filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        courses_col.delete_one({'_id': ObjectId(id)})
        flash('Course deleted successfully!', 'success')
    else:
        flash('Course not found.', 'danger')

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    initialize_admin()
    port = int(os.environ.get("PORT", 10000))  # Render sets PORT env variable
    app.run(host='0.0.0.0', port=port)

