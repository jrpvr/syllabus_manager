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
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

DB_FILE = 'syllabus.db'

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS syllabus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT,
            instructor TEXT,
            semester TEXT,
            credits INTEGER,
            topics TEXT,
            pdf_filename TEXT
        )
    ''')
    # Default admin account
    c.execute('SELECT * FROM users WHERE username = ?', ('pratham',))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (
            'pratham',
            generate_password_hash('pvrathod003'),
            'admin'
        ))
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = dict_factory  # Enable dictionary-style row access
    return conn

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
    offset = (page - 1) * per_page

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as count FROM syllabus')
    total_courses = c.fetchone()['count']
    total_pages = math.ceil(total_courses / per_page)

    c.execute('SELECT * FROM syllabus LIMIT ? OFFSET ?', (per_page, offset))
    courses = c.fetchall()
    conn.close()

    return render_template('index.html', courses=courses, current_page=page, total_pages=total_pages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
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

        conn = get_db()
        c = conn.cursor()
        c.execute('''
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

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM syllabus WHERE id=?', (id,))
    course = c.fetchone()

    if not course:
        flash('Course not found.', 'danger')
        conn.close()
        return redirect(url_for('index'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        instructor = request.form.get('instructor')
        semester = request.form.get('semester')
        credits = int(request.form.get('credits', 0))
        topics = request.form.get('topics')
        pdf_file = request.files.get('pdf_file')

        filename = course['pdf_filename']
        if pdf_file and allowed_file(pdf_file.filename):
            if filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = save_pdf_file(pdf_file)

        c.execute('''
            UPDATE syllabus
            SET course_name=?, instructor=?, semester=?, credits=?, topics=?, pdf_filename=?
            WHERE id=?
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

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT pdf_filename FROM syllabus WHERE id=?', (id,))
    result = c.fetchone()

    if result:
        if result['pdf_filename']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], result['pdf_filename'])
            if os.path.exists(file_path):
                os.remove(file_path)

        c.execute('DELETE FROM syllabus WHERE id=?', (id,))
        conn.commit()

    conn.close()
    flash('Course deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
@app.before_first_request
def initialize():
    init_db()
