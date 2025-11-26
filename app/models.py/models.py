import sqlite3

DB_PATH = 'cvpa.db'

def get_partits():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM partits")
    result = cursor.fetchall()
    conn.close()
    return result
