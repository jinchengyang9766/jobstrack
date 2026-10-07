import sqlite3

connection = sqlite3.connect("jobtrack.db")

connection.execute(
    """
    INSERT INTO applications (company, position, status)
    VALUES (?, ?, ?)
    """,
    ("Acme", "Developer", "applied"),
)

connection.commit()
connection.close()

print("Application saved")