import os
import uuid
import math
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secretkey'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('syllabus.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS syllabus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            instructor TEXT,
            semester TEXT,
            credits INTEGER,
            topics TEXT,
            pdf_filename TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                     ('admin', generate_password_hash('admin123'), 'admin'))
    conn.commit()
    conn.close()

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('role') == 'admin'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/courses')
def index():
    page = int(request.args.get('page', 1))
    per_page = 6
    offset = (page - 1) * per_page

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM syllabus")
    total_courses = c.fetchone()[0]
    total_pages = math.ceil(total_courses / per_page)

    c.execute("SELECT * FROM syllabus LIMIT ? OFFSET ?", (per_page, offset))
    courses = [dict(zip([column[0] for column in c.description], row)) for row in c.fetchall()]
    conn.close()

    return render_template('index.html', courses=courses, current_page=page, total_pages=total_pages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
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
        credits = request.form.get('credits')
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = ''
        if pdf_file and pdf_file.filename != '' and allowed_file(pdf_file.filename):
            filename = save_pdf_file(pdf_file)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO syllabus (course_name, instructor, semester, credits, topics, pdf_filename)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (course_name, instructor, semester, credits, topics, filename))
        conn.commit()
        conn.close()
        flash('Course added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = get_db_connection()
    course = conn.execute('SELECT * FROM syllabus WHERE id = ?', (id,)).fetchone()

    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        credits = request.form.get('credits')
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = course['pdf_filename']
        if pdf_file and pdf_file.filename != '' and allowed_file(pdf_file.filename):
            if filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = save_pdf_file(pdf_file)

        conn.execute('''
            UPDATE syllabus
            SET course_name = ?, instructor = ?, semester = ?, credits = ?, topics = ?, pdf_filename = ?
            WHERE id = ?
        ''', (course_name, instructor, semester, credits, topics, filename, id))
        conn.commit()
        conn.close()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', course=course)

@app.route('/delete/<int:id>')
def delete(id):
    if not is_logged_in() or not is_admin():
        flash('Only admin can delete courses.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    course = conn.execute('SELECT * FROM syllabus WHERE id = ?', (id,)).fetchone()

    if course:
        if course['pdf_filename']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], course['pdf_filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        conn.execute('DELETE FROM syllabus WHERE id = ?', (id,))
        conn.commit()
        flash('Course deleted successfully!', 'success')
    else:
        flash('Course not found.', 'danger')
    conn.close()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def save_pdf_file(pdf_file):
    ext = pdf_file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    pdf_file.save(filepath)
    return unique_filename

# This will run both locally and on Render (under gunicorn)
initialize_database()
