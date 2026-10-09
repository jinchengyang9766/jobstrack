import sqlite3

import pytest
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


@pytest.fixture
def db_client(tmp_path, monkeypatch):
    # 为每个使用此夹具的测试准备独立的临时数据库。
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
    return client


def test_application_lifecycle(db_client):
    client = db_client
    response = client.post(
        "/applications",
        json={"company": "  Test Company  ", "position": "  Python Developer  "},
    )
    assert response.status_code == 200
    application = response.json()
    application_id = application["id"]
    assert application["company"] == "Test Company"
    assert application["position"] == "Python Developer"
    assert application["status"] == "applied"

    application_url = f"/applications/{application_id}"

    response = client.get(application_url)
    assert response.status_code == 200
    assert response.json() == application

    # 非法状态应该被拒绝，数据库里的原状态应该保留。
    response = client.patch(application_url, json={"status": "abc"})
    assert response.status_code == 422

    response = client.get(application_url)
    assert response.status_code == 200
    assert response.json()["status"] == "applied"

    # 依次检查四种合法状态，并重新查询以确认修改已保存。
    for status in ("applied", "interview", "offer", "rejected"):
        response = client.patch(application_url, json={"status": status})
        assert response.status_code == 200
        assert response.json() == {
            "id": application_id,
            "company": "Test Company",
            "position": "Python Developer",
            "status": status,
        }

        response = client.get(application_url)
        assert response.status_code == 200
        assert response.json()["status"] == status

    response = client.delete(application_url)
    assert response.status_code == 200
    assert response.json() == {"message": "Application deleted"}

    response = client.get(application_url)
    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


@pytest.mark.parametrize("application_id", ["abc", 0, -1])
def test_invalid_ids_for_all_operations(db_client, application_id):
    for method in ("GET", "PATCH", "DELETE"):
        url = f"/applications/{application_id}"
        if method == "PATCH":
            response = db_client.patch(url, json={"status": "interview"})
        else:
            response = db_client.request(method, url)
        assert response.status_code == 422


@pytest.mark.parametrize("body", [
    {"company": "", "position": "Developer"},
    {"company": "   ", "position": "Developer"},
    {"company": "Company", "position": ""},
    {"company": "Company", "position": "   "},
    {"company": "C" * 101, "position": "Developer"},
    {"company": "Company", "position": "P" * 151},
    {"position": "Developer"},
    {"company": "Company"},
])
def test_invalid_text_does_not_insert(db_client, body):
    response = db_client.post("/applications", json=body)
    assert response.status_code == 422
    response = db_client.get("/applications")
    assert response.status_code == 200
    assert response.json() == []


def test_text_length_boundaries(db_client):
    company = "C" * 100
    position = "P" * 150
    response = db_client.post(
        "/applications",
        json={"company": f"  {company}  ", "position": f"  {position}  "},
    )
    assert response.status_code == 200
    application = response.json()
    assert application["company"] == company
    assert application["position"] == position
    response = db_client.get(f"/applications/{application['id']}")
    assert response.status_code == 200
    assert response.json() == application


def test_company_filter(db_client):
    response = db_client.post(
        "/applications", json={"company": "O'Reilly", "position": "Developer"}
    )
    assert response.status_code == 200
    application = response.json()
    response = db_client.post(
        "/applications", json={"company": "Other Company", "position": "Developer"}
    )
    assert response.status_code == 200
    response = db_client.get("/applications")
    assert response.status_code == 200
    assert len(response.json()) == 2
    response = db_client.get("/applications", params={"company": "  O'Reilly  "})
    assert response.status_code == 200
    assert response.json() == [application]
    response = db_client.get("/applications", params={"company": "Missing Company"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("company", ["", "   ", "C" * 101])
def test_invalid_company_filter(db_client, company):
    response = db_client.get("/applications", params={"company": company})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_missing_application_does_not_change_others(db_client, method):
    response = db_client.post(
        "/applications", json={"company": "Company", "position": "Developer"}
    )
    assert response.status_code == 200
    application = response.json()
    missing_id = application["id"] + 1
    url = f"/applications/{missing_id}"
    if method == "PATCH":
        response = db_client.patch(url, json={"status": "interview"})
    else:
        response = db_client.request(method, url)
    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}
    response = db_client.get("/applications")
    assert response.status_code == 200
    assert response.json() == [application]


@pytest.mark.parametrize("status", ["abc", "Interview", "", " interview "])
def test_invalid_status_preserves_record(db_client, status):
    response = db_client.post(
        "/applications", json={"company": "Company", "position": "Developer"}
    )
    assert response.status_code == 200
    application = response.json()
    application_url = f"/applications/{application['id']}"
    response = db_client.patch(application_url, json={"status": status})
    assert response.status_code == 422
    response = db_client.get(application_url)
    assert response.status_code == 200
    assert response.json() == application


@pytest.mark.parametrize("body", [
    {"company": 123, "position": "Developer"},
    {"company": "Company", "position": ["Developer"]},
    ["Company", "Developer"],
    "Company",
])
def test_invalid_json_body_does_not_insert(db_client, body):
    response = db_client.post("/applications", json=body)
    assert response.status_code == 422
    response = db_client.get("/applications")
    assert response.status_code == 200
    assert response.json() == []


def test_post_requires_request_body(db_client):
    response = db_client.post(
        "/applications", params={"company": "Company", "position": "Developer"}
    )
    assert response.status_code == 422
    response = db_client.get("/applications")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("body", [{}, {"status": 123}, {"status": None}])
def test_invalid_patch_body_preserves_record(db_client, body):
    response = db_client.post(
        "/applications", json={"company": "Company", "position": "Developer"}
    )
    assert response.status_code == 200
    application = response.json()
    url = f"/applications/{application['id']}"

    response = db_client.patch(url, json=body)
    assert response.status_code == 422
    response = db_client.get(url)
    assert response.status_code == 200
    assert response.json() == application


def test_patch_requires_request_body(db_client):
    response = db_client.post(
        "/applications", json={"company": "Company", "position": "Developer"}
    )
    assert response.status_code == 200
    application = response.json()
    url = f"/applications/{application['id']}"

    response = db_client.patch(url, params={"status": "interview"})
    assert response.status_code == 422
    response = db_client.get(url)
    assert response.status_code == 200
    assert response.json() == application


@pytest.fixture
def filter_records(db_client):
    records = []
    for data in (
        {"company": "Acme", "position": "Backend", "status": "applied"},
        {"company": "Acme", "position": "Frontend", "status": "interview"},
        {"company": "Other", "position": "Backend", "status": "interview"},
    ):
        response = db_client.post(
            "/applications",
            json={"company": data["company"], "position": data["position"]},
        )
        assert response.status_code == 200
        application_id = response.json()["id"]
        response = db_client.patch(
            f"/applications/{application_id}", json={"status": data["status"]}
        )
        assert response.status_code == 200
        records.append(response.json())
    return records


@pytest.mark.parametrize("params, expected_indexes", [
    ({}, [0, 1, 2]),
    ({"company": "Acme"}, [0, 1]),
    ({"status": "applied"}, [0]),
    ({"status": "interview"}, [1, 2]),
    ({"company": "  Acme  ", "status": "interview"}, [1]),
    ({"company": "Other", "status": "applied"}, []),
    ({"status": "offer"}, []),
])
def test_combined_filters_and_order(db_client, filter_records, params, expected_indexes):
    expected = []
    for index in expected_indexes:
        expected.append(filter_records[index])

    response = db_client.get("/applications", params=params)
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("status", ["abc", "", "Interview", " interview "])
def test_invalid_status_filter(db_client, filter_records, status):
    response = db_client.get("/applications", params={"status": status})
    assert response.status_code == 422
    response = db_client.get("/applications")
    assert response.status_code == 200
    assert response.json() == filter_records
