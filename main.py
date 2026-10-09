import sqlite3
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class ApplicationCreate(BaseModel):
    company: str
    position: str


class ApplicationUpdate(BaseModel):
    status: Literal["applied", "interview", "offer", "rejected"]


def clean_application_text(value: str, field: str, max_length: int):
    value = value.strip()

    if not value:
        raise HTTPException(status_code=422, detail=f"{field} must not be blank")

    if len(value) > max_length:
        raise HTTPException(
            status_code=422,
            detail=f"{field} must be at most {max_length} characters",
        )

    return value


def validate_application_id(application_id: int):
    if application_id <= 0:
        raise HTTPException(
            status_code=422,
            detail="Application id must be a positive integer",
        )


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "project": "JobTrack",
    }

@app.get("/applications")
def list_applications(
    company: str | None = None,
    status: Literal["applied", "interview", "offer", "rejected"] | None = None,
):
    if company is not None:
        company = clean_application_text(company, "Company", 100)

    query = "SELECT id, company, position, status FROM applications"
    conditions = []
    values = []

    if company is not None:
        conditions.append("company = ?")
        values.append(company)

    if status is not None:
        conditions.append("status = ?")
        values.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id"

    connection = sqlite3.connect("jobtrack.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(query, values)
    rows = cursor.fetchall()
    connection.close()

    results = []
    for row in rows:
        results.append(dict(row))

    return results

@app.post("/applications")
def create_application(application: ApplicationCreate):
    company = clean_application_text(application.company, "Company", 100)
    position = clean_application_text(application.position, "Position", 150)

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
    validate_application_id(application_id)

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
def update_application(
    application_id: int,
    update: ApplicationUpdate,
):
    validate_application_id(application_id)
    status = update.status

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
    validate_application_id(application_id)

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
