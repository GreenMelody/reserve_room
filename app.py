import os
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

dotenv_path = os.path.abspath(os.path.join('sharedworkspace/','.env'))
load_dotenv(dotenv_path)

app_db_path = os.getenv('DB_PATH')
app_db_file = os.getenv('DB_FILE')
app_db_file_path = os.path.join(app_db_path, app_db_file)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# DB 연결 함수
def get_db_connection():
    conn = sqlite3.connect(app_db_file_path)
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
    room_id = request.args.get('room_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not room_id or not start_date or not end_date:
        return jsonify({'error': '회의실과 날짜 범위가 지정되지 않았습니다.'}), 400

    conn = get_db_connection()

    # 선택한 회의실의 예약 현황을 날짜 범위 내에서 가져오기 (상태가 '거절됨'인 예약은 제외)
    reservations = conn.execute('''
        SELECT * FROM reservations 
        WHERE room_id = ? AND date BETWEEN ? AND ?
        AND status != '거절됨'
    ''', (room_id, start_date, end_date)).fetchall()

    conn.close()

    return jsonify({
        'reservations': [dict(reservation) for reservation in reservations],
        'room_id': room_id,
        'start_date': start_date,
        'end_date': end_date,
        'current_user_id': session.get('user_id'),
        'current_user_role': session.get('role')  # 사용자의 역할(role) 정보 추가
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
    requested_at = datetime.now()  # 현재 시간 저장

    conn = get_db_connection()
    room = conn.execute('SELECT id FROM rooms WHERE room_name = ?', (room_name,)).fetchone()

    if room:
        room_id = room['id']

        # 예약 중복 여부 확인 (겹치는 시간대가 있는지 확인)
        overlapping_reservations = conn.execute('''
            SELECT * FROM reservations
            WHERE room_id = ? AND date = ?
            AND (
                (start_time < ? AND end_time > ?) OR  -- 새로운 예약 시작 시간이 기존 예약과 겹치는지 확인
                (start_time < ? AND end_time > ?) OR  -- 새로운 예약 끝 시간이 기존 예약과 겹치는지 확인
                (start_time >= ? AND end_time <= ?)   -- 새로운 예약이 기존 예약 내에 완전히 포함되는지 확인
            )
        ''', (room_id, date, start_time, start_time, end_time, end_time, start_time, end_time)).fetchall()

        if overlapping_reservations:
            return jsonify({'error': '중복된 예약이 있습니다.'})

        # 예약 생성 (user_id 및 requested_at 추가)
        conn.execute('''
            INSERT INTO reservations (user_id, room_id, date, start_time, end_time, status, requested_at)
            VALUES (?, ?, ?, ?, ?, '예약요청', ?)
        ''', (user_id, room_id, date, start_time, end_time, requested_at))
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

# 예약 승인 처리 API
@app.route('/reservations/<int:id>/approve', methods=['POST'])
def approve_reservation(id):
    if 'role' not in session or session['role'] not in ['승인자', '관리자']:
        return jsonify({'error': '승인 권한이 없습니다.'}), 403

    conn = get_db_connection()
    reservation = conn.execute('SELECT * FROM reservations WHERE id = ?', (id,)).fetchone()

    if not reservation:
        return jsonify({'error': '해당 예약이 존재하지 않습니다.'}), 404

    # 승인한 사람 (현재 로그인한 사용자)
    approved_by_user_id = session['user_id']

    # 승인된 예약을 approved_reservations 테이블에 저장
    conn.execute('''
        INSERT INTO approved_reservations (original_reservation_id, user_id, room_id, date, start_time, end_time, approved_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (id, reservation['user_id'], reservation['room_id'], reservation['date'], reservation['start_time'], reservation['end_time'], approved_by_user_id))

    # 예약 상태를 '예약완료'로 업데이트
    conn.execute('UPDATE reservations SET status = "예약완료" WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    return jsonify({'message': '예약이 승인되었습니다.'})


# 예약 거절 처리 API
@app.route('/reservations/<int:id>/reject', methods=['POST'])
def reject_reservation(id):
    if 'role' not in session or session['role'] not in ['승인자', '관리자']:
        return jsonify({'error': '거절 권한이 없습니다.'}), 403

    conn = get_db_connection()
    reservation = conn.execute('SELECT * FROM reservations WHERE id = ?', (id,)).fetchone()

    if not reservation:
        return jsonify({'error': '해당 예약이 존재하지 않습니다.'}), 404

    # 거절한 사람 (현재 로그인한 사용자)
    rejected_by_user_id = session['user_id']

    # 거절된 예약을 rejected_reservations 테이블에 저장
    conn.execute('''
        INSERT INTO rejected_reservations (original_reservation_id, user_id, room_id, date, start_time, end_time, rejected_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id, reservation['user_id'], reservation['room_id'], reservation['date'], reservation['start_time'], reservation['end_time'], rejected_by_user_id))

    # 예약 삭제 처리 (거절된 예약은 DB에서 삭제)
    conn.execute('DELETE FROM reservations WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    return jsonify({'message': '예약이 거절되었습니다.'})

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

# 회의실 리스트를 반환하는 API
@app.route('/rooms', methods=['GET'])
def get_rooms():
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms').fetchall()
    conn.close()

    # 회의실 리스트를 JSON으로 반환
    return jsonify({
        'rooms': [{'id': room['id'], 'room_name': room['room_name']} for room in rooms]
    })

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
