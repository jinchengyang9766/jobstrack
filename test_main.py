import sqlite3

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "project": "JobTrack"}


def test_application_id_must_be_integer():
    response = client.get("/applications/abc")

    assert response.status_code == 422


def test_application_lifecycle(tmp_path, monkeypatch):
    # Use a separate database in a temporary directory for this test.
    monkeypatch.chdir(tmp_path)

    connection = sqlite3.connect("jobtrack.db")
    connection.execute("""
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    connection.commit()
    connection.close()

    response = client.post(
        "/applications",
        params={"company": "Test Company", "position": "Python Developer"},
    )
    assert response.status_code == 200
    application = response.json()
    application_id = application["id"]
    assert application["company"] == "Test Company"
    assert application["status"] == "applied"

    application_url = f"/applications/{application_id}"

    response = client.get(application_url)
    assert response.status_code == 200
    assert response.json() == application

    response = client.patch(application_url, params={"status": "interview"})
    assert response.status_code == 200
    assert response.json() == {
        "id": application_id,
        "company": "Test Company",
        "position": "Python Developer",
        "status": "interview",
    }

    response = client.get(application_url)
    assert response.status_code == 200
    assert response.json()["status"] == "interview"

    response = client.delete(application_url)
    assert response.status_code == 200
    assert response.json() == {"message": "Application deleted"}

    response = client.get(application_url)
    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}
