import sqlite3
from contextlib import closing
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel

app = FastAPI()


class ApplicationCreate(BaseModel):
    company: str
    position: str


class ApplicationUpdate(BaseModel):
    status: Literal["applied", "interview", "offer", "rejected"]


class ApplicationRead(BaseModel):
    id: int
    company: str
    position: str
    status: str


def get_db_connection():
    connection = sqlite3.connect("jobtrack.db")
    connection.row_factory = sqlite3.Row
    return connection


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

@app.get("/applications", response_model=list[ApplicationRead])
def list_applications(
    company: str | None = None,
    status: Literal["applied", "interview", "offer", "rejected"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
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

    query += " ORDER BY id LIMIT ? OFFSET ?"
    values.append(limit)
    values.append(offset)

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(query, values)
        rows = cursor.fetchall()

    results = []
    for row in rows:
        results.append(dict(row))

    return results

@app.get("/applications/stats")
def application_stats():
    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "SELECT status, COUNT(*) AS count FROM applications GROUP BY status"
        )
        rows = cursor.fetchall()

    by_status = {"applied": 0, "interview": 0, "offer": 0, "rejected": 0}
    total = 0
    for row in rows:
        by_status[row["status"]] = row["count"]
        total += row["count"]

    return {"total": total, "by_status": by_status}


@app.post("/applications", response_model=ApplicationRead, status_code=201)
def create_application(application: ApplicationCreate):
    company = clean_application_text(application.company, "Company", 100)
    position = clean_application_text(application.position, "Position", 150)

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO applications (company, position, status)
            VALUES (?, ?, ?)
            """,
            (company, position, "applied"),
        )

        connection.commit()
        application_id = cursor.lastrowid

    return {
        "id": application_id,
        "company": company,
        "position": position,
        "status": "applied",
    }

@app.get("/applications/{application_id}", response_model=ApplicationRead)
def get_application(application_id: int):
    validate_application_id(application_id)

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "SELECT id, company, position, status FROM applications WHERE id = ?",
            (application_id,),
        )
        application = cursor.fetchone()

    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    return dict(application)

@app.patch("/applications/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: int,
    update: ApplicationUpdate,
):
    validate_application_id(application_id)
    status = update.status

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, application_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")

        connection.commit()

        cursor = connection.execute(
            "SELECT id, company, position, status FROM applications WHERE id = ?",
            (application_id,),
        )
        application = cursor.fetchone()

    return dict(application)

@app.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: int):
    validate_application_id(application_id)

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "DELETE FROM applications WHERE id = ?",
            (application_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")

        connection.commit()

    return Response(status_code=204)
