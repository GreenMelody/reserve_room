import sqlite3

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

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
