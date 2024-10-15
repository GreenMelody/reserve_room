import sqlite3
from werkzeug.security import generate_password_hash

def create_tables():
    conn = sqlite3.connect('reservation_system.db')
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
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id)
                    )''')

    # 세션 테이블 생성
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id INTEGER,
                        expiration_date TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )''')

    # 관리자 계정 추가
    add_admin_user(cursor)

    conn.commit()
    conn.close()

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

if __name__ == "__main__":
    create_tables()
