from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = 'reserve'

# DB 연결 함수
def get_db_connection():
    conn = sqlite3.connect('reservation_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# 사용자 로그인
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
            session['expires_at'] = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            return redirect(url_for('index'))
        else:
            return '아이디 또는 비밀번호가 올바르지 않습니다.'

    return render_template('login.html')

# 로그아웃
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 예약 시스템 메인 페이지
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('index.html')

# 예약 현황 조회 API
@app.route('/reservations', methods=['GET'])
def get_reservations():
    selected_date = request.args.get('date')

    if not selected_date:
        return jsonify({'error': '날짜가 지정되지 않았습니다.'}), 400

    conn = get_db_connection()

    # 모든 회의실 리스트 가져오기
    rooms = conn.execute('SELECT * FROM rooms').fetchall()

    # 예약 데이터를 회의실별로 가져오기
    reservations_by_room = {}
    for room in rooms:
        reservations = conn.execute('''
            SELECT * FROM reservations 
            WHERE room_id = ? AND date = ?
        ''', (room['id'], selected_date)).fetchall()

        # Row 객체를 딕셔너리로 변환 (user_id 포함)
        reservations_by_room[room['id']] = [dict(reservation) for reservation in reservations]

    conn.close()

    # 회의실 리스트와 각 회의실의 예약 데이터를 반환
    return jsonify({
        'rooms': [{'id': room['id'], 'name': room['room_name']} for room in rooms],
        'reservations_by_room': reservations_by_room,
        'current_user_id': session['user_id']  # 현재 로그인한 사용자 ID를 함께 반환
    })


# 예약 요청 처리
@app.route('/reservations', methods=['POST'])
def create_reservation():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 403

    date = request.form['date']
    start_time = int(request.form['start_time'])
    end_time = int(request.form['end_time'])
    room_name = request.form['room_name']
    user_id = session['user_id']  # 현재 로그인한 사용자의 user_id 가져오기

    conn = get_db_connection()
    room = conn.execute('SELECT id FROM rooms WHERE room_name = ?', (room_name,)).fetchone()

    if room:
        room_id = room['id']

        # 예약 중복 여부 확인
        overlapping_reservations = conn.execute('''
            SELECT * FROM reservations
            WHERE room_id = ? AND date = ? AND 
                  ((start_time <= ? AND end_time > ?) OR (start_time < ? AND end_time >= ?))
        ''', (room_id, date, end_time, start_time, start_time, end_time)).fetchall()

        if overlapping_reservations:
            return jsonify({'error': '중복된 예약이 있습니다.'})

        # 예약 생성 (user_id 추가)
        conn.execute('''
            INSERT INTO reservations (user_id, room_id, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, '예약요청')
        ''', (user_id, room_id, date, start_time, end_time))
        conn.commit()
        conn.close()

        return jsonify({'message': '예약 요청이 완료되었습니다.'})
    else:
        return jsonify({'error': '회의실을 찾을 수 없습니다.'}), 404

# 예약 취소 처리
@app.route('/reservations/<int:id>', methods=['DELETE'])
def delete_reservation(id):
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 403

    conn = get_db_connection()
    reservation = conn.execute('SELECT * FROM reservations WHERE id = ?', (id,)).fetchone()

    if not reservation:
        return jsonify({'error': '해당 예약이 존재하지 않습니다.'}), 404

    if reservation['user_id'] != session['user_id']:
        return jsonify({'error': '자신의 예약만 취소할 수 있습니다.'}), 403

    conn.execute('DELETE FROM reservations WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    return jsonify({'message': '예약이 취소되었습니다.'})

# 사용자 관리 페이지 (관리자 전용)
@app.route('/manage-users')
def manage_users():
    if 'role' not in session or session['role'] != '관리자':
        return redirect(url_for('login'))

    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()

    return render_template('manage-user.html', users=users)

# 사용자 생성 API (관리자 전용)
@app.route('/users', methods=['POST'])
def create_user():
    if 'role' not in session or session['role'] != '관리자':
        return jsonify({'error': '관리자만 접근 가능합니다.'}), 403

    username = request.form['username']
    password = generate_password_hash(request.form['password'])
    name_korean = request.form['name_korean']
    name_english = request.form['name_english']
    role = request.form['role']

    conn = get_db_connection()

    try:
        conn.execute('INSERT INTO users (username, password, name_korean, name_english, role) VALUES (?, ?, ?, ?, ?)',
                     (username, password, name_korean, name_english, role))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': '이미 존재하는 사용자입니다.'}), 400
    finally:
        conn.close()

    return jsonify({'message': '사용자가 성공적으로 생성되었습니다.'})

# 회의실 관리 페이지 (관리자 전용)
@app.route('/manage-rooms')
def manage_rooms():
    if 'role' not in session or session['role'] != '관리자':
        return redirect(url_for('login'))

    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms').fetchall()
    conn.close()

    return render_template('manage-room.html', rooms=rooms)

# 회의실 생성 API (관리자 전용)
@app.route('/rooms', methods=['POST'])
def create_room():
    if 'role' not in session or session['role'] != '관리자':
        return jsonify({'error': '관리자만 접근 가능합니다.'}), 403

    room_name = request.form['room_name']

    conn = get_db_connection()

    try:
        conn.execute('INSERT INTO rooms (room_name) VALUES (?)', (room_name,))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': '이미 존재하는 회의실입니다.'}), 400
    finally:
        conn.close()

    return jsonify({'message': '회의실이 성공적으로 생성되었습니다.'})

if __name__ == '__main__':
    app.run(debug=True, port=8888)
