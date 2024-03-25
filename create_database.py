import sqlite3

from config import DB_PATH

def create_database():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
    CREATE TABLE IF NOT EXISTS devices
    (
        id        INTEGER PRIMARY KEY autoincrement,
        userId    INTEGER,
        minerName TEXT,
        host      TEXT,
        user      TEXT,
        password  INTEGER
    )""")
    db.close()


if __name__ == '__main__':
    create_database()
