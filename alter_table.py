import sqlite3

def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def add_pdf_column():
    conn = sqlite3.connect('syllabus.db')
    cursor = conn.cursor()

    if not column_exists(cursor, 'syllabus', 'pdf_filename'):
        cursor.execute('ALTER TABLE syllabus ADD COLUMN pdf_filename TEXT')
        conn.commit()
        print("✅ Column 'pdf_filename' added successfully.")
    else:
        print("ℹ️ Column 'pdf_filename' already exists.")

    conn.close()

if __name__ == '__main__':
    add_pdf_column()
