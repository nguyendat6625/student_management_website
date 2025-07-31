from flask import Flask, render_template, request, jsonify, redirect, url_for
import pyodbc
import json
from datetime import datetime

app = Flask(__name__)

# Cấu hình kết nối SQL Server
# Thay đổi thông tin kết nối theo database của bạn
def get_db_connection():
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=localhost\\NGUYENDAT;'  # Thay bằng server của bạn
            'DATABASE=StudentDB;'  # Thay bằng tên database
            'UID=nguyendat;'  # Username
            'PWD=12345'  # Password
        )
        return conn
    except Exception as e:
        print(f"Lỗi kết nối database: {e}")
        return None

# Tạo bảng students nếu chưa tồn tại
def init_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='students' AND xtype='U')
            CREATE TABLE students (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL,
                email NVARCHAR(100) UNIQUE NOT NULL,
                age INT,
                major NVARCHAR(100),
                created_at DATETIME DEFAULT GETDATE()
            )
        ''')
        conn.commit()
        conn.close()

# Routes

@app.route('/')
def index():
    """Trang chủ hiển thị danh sách sinh viên"""
    return render_template('index.html')

@app.route('/add_student')
def add_student_page():
    """Trang thêm sinh viên mới"""
    return render_template('add_student.html')

# API Routes

@app.route('/api/students', methods=['GET'])
def get_students():
    """API lấy danh sách tất cả sinh viên"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Không thể kết nối database'}), 500
    
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students ORDER BY created_at DESC')
    students = []
    
    for row in cursor.fetchall():
        students.append({
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'age': row[3],
            'major': row[4],
            'created_at': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None
        })
    
    conn.close()
    return jsonify(students)

@app.route('/api/students', methods=['POST'])
def add_student():
    """API thêm sinh viên mới"""
    data = request.get_json()
    
    # Validate dữ liệu
    if not data or not data.get('name') or not data.get('email'):
        return jsonify({'error': 'Tên và email là bắt buộc'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Không thể kết nối database'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students (name, email, age, major)
            VALUES (?, ?, ?, ?)
        ''', (data['name'], data['email'], data.get('age'), data.get('major')))
        
        conn.commit()
        
        # Lấy ID của record vừa thêm
        cursor.execute('SELECT @@IDENTITY')
        new_id = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'message': 'Thêm sinh viên thành công',
            'id': new_id
        }), 201
        
    except pyodbc.IntegrityError:
        conn.close()
        return jsonify({'error': 'Email đã tồn tại'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Lỗi: {str(e)}'}), 500

@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """API lấy thông tin một sinh viên"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Không thể kết nối database'}), 500
    
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Không tìm thấy sinh viên'}), 404
    
    student = {
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'age': row[3],
        'major': row[4],
        'created_at': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None
    }
    
    conn.close()
    return jsonify(student)

@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """API cập nhật thông tin sinh viên"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Không có dữ liệu'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Không thể kết nối database'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE students 
            SET name = ?, email = ?, age = ?, major = ?
            WHERE id = ?
        ''', (data.get('name'), data.get('email'), 
              data.get('age'), data.get('major'), student_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Không tìm thấy sinh viên'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Cập nhật thành công'})
        
    except pyodbc.IntegrityError:
        conn.close()
        return jsonify({'error': 'Email đã tồn tại'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Lỗi: {str(e)}'}), 500

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """API xóa sinh viên"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Không thể kết nối database'}), 500
    
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Không tìm thấy sinh viên'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Xóa sinh viên thành công'})

# API thống kê cho Data Science
@app.route('/api/stats')
def get_stats():
    """API lấy thống kê sinh viên theo chuyên ngành"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Không thể kết nối database'}), 500
    
    cursor = conn.cursor()
    
    # Thống kê số lượng sinh viên theo chuyên ngành
    cursor.execute('''
        SELECT major, COUNT(*) as count, AVG(CAST(age as FLOAT)) as avg_age
        FROM students 
        WHERE major IS NOT NULL
        GROUP BY major
        ORDER BY count DESC
    ''')
    
    stats = []
    for row in cursor.fetchall():
        stats.append({
            'major': row[0],
            'count': row[1],
            'avg_age': round(row[2], 1) if row[2] else 0
        })
    
    # Tổng số sinh viên
    cursor.execute('SELECT COUNT(*) FROM students')
    total_students = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_students': total_students,
        'by_major': stats
    })

if __name__ == '__main__':
    init_db()  # Khởi tạo database
    app.run(debug=True, host='0.0.0.0', port=5000)