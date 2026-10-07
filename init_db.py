import sqlite3

connection = sqlite3.connect("jobtrack.db")

connection.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    position TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

connection.commit()
connection.close()

print("Database initialized")