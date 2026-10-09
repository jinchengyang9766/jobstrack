import sqlite3

from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "project": "JobTrack",
    }

@app.get("/applications")
def list_applications(company: str = None):
    connection = sqlite3.connect("jobtrack.db")
    connection.row_factory = sqlite3.Row

    if company is None:
        cursor = connection.execute(
            "SELECT id, company, position, status FROM applications"
        )
    else:
        cursor = connection.execute(
            "SELECT id, company, position, status FROM applications WHERE company = ?",
            (company,),
        )

    rows = cursor.fetchall()
    connection.close()

    results = []
    for row in rows:
        results.append(dict(row))

    return results

@app.post("/applications")
def create_application(company: str, position: str):
    connection = sqlite3.connect("jobtrack.db")

    cursor = connection.execute(
        """
        INSERT INTO applications (company, position, status)
        VALUES (?, ?, ?)
        """,
        (company, position, "applied"),
    )

    connection.commit()
    application_id = cursor.lastrowid
    connection.close()

    return {
        "id": application_id,
        "company": company,
        "position": position,
        "status": "applied",
    }

@app.get("/applications/{application_id}")
def get_application(application_id: int):
    connection = sqlite3.connect("jobtrack.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.execute(
        "SELECT id, company, position, status FROM applications WHERE id = ?",
        (application_id,),
    )
    application = cursor.fetchone()
    connection.close()

    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    return dict(application)

@app.patch("/applications/{application_id}")
def update_application(application_id: int, status: str):
    connection = sqlite3.connect("jobtrack.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
        (status, application_id),
    )

    if cursor.rowcount == 0:
        connection.close()
        raise HTTPException(status_code=404, detail="Application not found")

    connection.commit()

    cursor = connection.execute(
        "SELECT id, company, position, status FROM applications WHERE id = ?",
        (application_id,),
    )
    application = cursor.fetchone()
    connection.close()

    return dict(application)

@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    connection = sqlite3.connect("jobtrack.db")

    cursor = connection.execute(
        "DELETE FROM applications WHERE id = ?",
        (application_id,),
    )

    if cursor.rowcount == 0:
        connection.close()
        raise HTTPException(status_code=404, detail="Application not found")

    connection.commit()
    connection.close()

    return {"message": "Application deleted"}
