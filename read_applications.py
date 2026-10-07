import sqlite3

connection = sqlite3.connect("jobtrack.db")

cursor = connection.execute(
    "SELECT id, company, position, status FROM applications"
)

applications = cursor.fetchall()

connection.close()

for application in applications:
    print(application)