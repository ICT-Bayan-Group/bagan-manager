import sqlite3

def init_db():
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    
    # Tabel untuk menyimpan data pertandingan dan skor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            kategori TEXT,
            babak TEXT,
            p1 TEXT,
            p2 TEXT,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            winner TEXT,
            pemenang_ke TEXT
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()