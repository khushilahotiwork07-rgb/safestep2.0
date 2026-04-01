import sqlite3

def upgrade_alerts_schema():
    conn = sqlite3.connect("safestep.db")
    columns_to_add = [
        ("trigger_reasons", "TEXT"),
        ("recommended_action", "TEXT"),
        ("risk_score", "INTEGER"),
        ("responded_at", "DATETIME"),
        ("responded_by", "TEXT")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            conn.execute(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} column.")
        except sqlite3.OperationalError:
            print(f"{col_name} column already exists.")
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade_alerts_schema()
