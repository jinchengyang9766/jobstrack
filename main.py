import sqlite3

from fastapi import FastAPI, HTTPException

app = FastAPI()

applications = [
    {
        "id": 1,
        "company": "Example Company",
        "position": "Python Developer",
        "status": "applied",
    }
]



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
    for application in applications:
        if application["id"] == application_id:
            return application

    raise HTTPException(status_code=404, detail="Application not found")

@app.patch("/applications/{application_id}")
def update_application(application_id: int, status: str):
    for application in applications:
        if application["id"] == application_id:
            application["status"] = status
            return application

    raise HTTPException(status_code=404, detail="Application not found")

@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    for application in applications:
        if application["id"] == application_id:
            applications.remove(application)
            return {"message": "Application deleted"}

    raise HTTPException(status_code=404, detail="Application not found")
