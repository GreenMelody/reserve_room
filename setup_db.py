import os
import sqlite3
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

dotenv_path = os.path.abspath(os.path.join('sharedworkspace/','.env'))
load_dotenv(dotenv_path)

app_db_path = os.getenv('DB_PATH')
app_db_file = os.getenv('DB_FILE')
app_db_file_path = os.path.join(app_db_path, app_db_file)

def create_tables():
    conn = sqlite3.connect(app_db_file_path)
    cursor = conn.cursor()

    # 사용자 테이블 생성
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        name_korean TEXT NOT NULL,
                        name_english TEXT NOT NULL,
                        role TEXT NOT NULL
                    )''')

    # 회의실 테이블 생성
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        room_name TEXT UNIQUE NOT NULL
                    )''')

    # 예약 테이블 생성
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        room_id INTEGER,
                        date TEXT NOT NULL,
                        start_time INTEGER NOT NULL,
                        end_time INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        requested_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 요청 시간
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id)
                    )''')

    # 거절 테이블 생성
    cursor.execute('''CREATE TABLE IF NOT EXISTS rejected_reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_reservation_id INTEGER,
                        user_id INTEGER,  -- 예약한 사람
                        room_id INTEGER,
                        date TEXT NOT NULL,
                        start_time INTEGER NOT NULL,
                        end_time INTEGER NOT NULL,
                        rejected_by_user_id INTEGER,  -- 거절한 사람
                        rejected_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 거절 시간
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id),
                        FOREIGN KEY (rejected_by_user_id) REFERENCES users(id)
                    )''')

    # 승인 테이블 생성
    cursor.execute('''CREATE TABLE IF NOT EXISTS approved_reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_reservation_id INTEGER,
                        user_id INTEGER,  -- 예약한 사람
                        room_id INTEGER,
                        date TEXT NOT NULL,
                        start_time INTEGER NOT NULL,
                        end_time INTEGER NOT NULL,
                        approved_by_user_id INTEGER,  -- 승인한 사람
                        approved_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 승인 시간
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id),
                        FOREIGN KEY (approved_by_user_id) REFERENCES users(id)
                    )''')

    # 관리자 계정 추가
    add_admin_user(cursor)

    # 기본 회의실(room1) 추가
    add_default_room(cursor)

    conn.commit()
    conn.close()

# 관리자 계정 추가 함수
def add_admin_user(cursor):
    username = 'root'
    password = generate_password_hash('root')  # 비밀번호 암호화
    name_korean = '관리자'
    name_english = 'admin'
    role = '관리자'

    # 이미 관리자 계정이 존재하는지 확인
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    admin = cursor.fetchone()

    if not admin:
        cursor.execute('''
            INSERT INTO users (username, password, name_korean, name_english, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password, name_korean, name_english, role))
        print("관리자 계정이 생성되었습니다.")
    else:
        print("관리자 계정이 이미 존재합니다.")

# 기본 회의실 추가 함수
def add_default_room(cursor):
    room_name = 'room1'

    # 이미 room1 회의실이 존재하는지 확인
    cursor.execute('SELECT * FROM rooms WHERE room_name = ?', (room_name,))
    room = cursor.fetchone()

    if not room:
        cursor.execute('INSERT INTO rooms (room_name) VALUES (?)', (room_name,))
        print("room1 회의실이 생성되었습니다.")
    else:
        print("room1 회의실이 이미 존재합니다.")

if __name__ == "__main__":
    create_tables()
