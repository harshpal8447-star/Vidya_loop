import sqlite3
import bcrypt
import os

DB_PATH = "users.db"

def _connect():
    return sqlite3.connect(DB_PATH, timeout=15)

def init_db():
    conn = _connect()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, password):
    try:
        conn = _connect()
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute("INSERT INTO users VALUES (?, ?)", (username, hashed))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and check_password(password, result[0]):
        return True
    return False

# Initialize on import (safe with CREATE TABLE IF NOT EXISTS)
init_db()
