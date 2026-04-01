import sqlite3

def upgrade_schema():
    conn = sqlite3.connect("safestep.db")
    try:
        conn.execute("ALTER TABLE vitals ADD COLUMN blood_sugar REAL")
        print("Added blood_sugar column.")
    except sqlite3.OperationalError:
        print("blood_sugar column already exists or table doesn't exist.")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade_schema()
