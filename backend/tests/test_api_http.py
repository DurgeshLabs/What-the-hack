import csv

from sqlalchemy import create_engine

from app.db.session import get_db
from app.main import app as fastapi_app
from tests.conftest import SAMPLE_CSV, bearer, login


def test_health_reports_database_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "what-the-hack-api", "database": "ok"}


def test_health_is_503_when_database_is_unreachable(client) -> None:
    broken = create_engine("sqlite:////nonexistent-dir/does-not-exist.db")

    def broken_db():
        from sqlalchemy.orm import Session

        with Session(broken) as db:
            yield db

    fastapi_app.dependency_overrides[get_db] = broken_db
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


def test_login_and_role_enforcement(client, seeded_users) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "viewer@what-the-hack.local", "password": "WrongPass123!"}).status_code == 401

    tokens = login(client, "viewer@what-the-hack.local", seeded_users["viewer@what-the-hack.local"])
    assert tokens["user"]["role"] == "viewer"
    assert client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"])).json()["email"] == "viewer@what-the-hack.local"
    assert client.get("/api/v1/auth/admin-check", headers=bearer(tokens["access_token"])).status_code == 403

    admin = login(client, "admin@what-the-hack.local", seeded_users["admin@what-the-hack.local"])
    assert client.get("/api/v1/auth/admin-check", headers=bearer(admin["access_token"])).status_code == 200


def test_logout_revokes_access_and_refresh_tokens(client, seeded_users) -> None:
    tokens = login(client, "analyst@what-the-hack.local", seeded_users["analyst@what-the-hack.local"])
    assert client.post("/api/v1/auth/logout", headers=bearer(tokens["access_token"])).status_code == 204
    assert client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"])).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_refresh_rotates_and_old_refresh_token_dies(client, seeded_users) -> None:
    tokens = login(client, "analyst@what-the-hack.local", seeded_users["analyst@what-the-hack.local"])
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(rotated.json()["access_token"])).status_code == 200


def test_login_is_rate_limited(client, seeded_users) -> None:
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json={"email": "viewer@what-the-hack.local", "password": "WrongPass123!"}).status_code == 401
    blocked = client.post("/api/v1/auth/login", json={"email": "viewer@what-the-hack.local", "password": "WrongPass123!"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_upload_pipeline_windows_and_duplicate_guard(client, seeded_users) -> None:
    admin = login(client, "admin@what-the-hack.local", seeded_users["admin@what-the-hack.local"])
    viewer = login(client, "viewer@what-the-hack.local", seeded_users["viewer@what-the-hack.local"])
    content = SAMPLE_CSV.read_bytes()

    assert client.post("/api/v1/ingestion/upload", headers=bearer(viewer["access_token"]),
                       files={"file": ("sample.csv", content, "text/csv")}).status_code == 403
    assert client.post("/api/v1/ingestion/upload", headers=bearer(admin["access_token"]),
                       files={"file": ("sample.txt", content, "text/plain")}).status_code == 415
    assert client.post("/api/v1/ingestion/upload", headers=bearer(admin["access_token"]),
                       files={"file": ("empty.csv", b"", "text/csv")}).status_code == 422

    created = client.post("/api/v1/ingestion/upload", headers=bearer(admin["access_token"]),
                          data={"source_name": "http-test"}, files={"file": ("sample.csv", content, "text/csv")})
    assert created.status_code == 201, created.text
    job = created.json()
    assert (job["status"], job["total_rows"], job["accepted_rows"], job["skipped_rows"]) == ("completed", 120, 120, 0)

    status = client.get(f"/api/v1/ingestion/{job['id']}/status", headers=bearer(viewer["access_token"]))
    assert status.status_code == 200 and status.json()["error_message"] is None

    duplicate = client.post("/api/v1/ingestion/upload", headers=bearer(admin["access_token"]),
                            data={"source_name": "http-test"}, files={"file": ("sample.csv", content, "text/csv")})
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == job["id"]

    # Background build ran inside the TestClient call; page through the windows two at a time.
    source_id = job["traffic_source_id"]
    windows, cursor = [], None
    for _ in range(10):
        params = {"traffic_source_id": source_id, "limit": 2}
        if cursor:
            params["after"] = cursor
        page = client.get("/api/v1/windows", params=params, headers=bearer(viewer["access_token"]))
        assert page.status_code == 200, page.text
        windows.extend(page.json()["items"])
        cursor = page.json()["next_cursor"]
        if cursor is None:
            break
    assert len(windows) == 5
    assert [w["window_start"][11:16] for w in windows] == ["18:00", "18:01", "18:02", "18:03", "18:04"]
    with SAMPLE_CSV.open(encoding="utf-8") as handle:
        expected_packets = sum(int(row["packets"]) for row in csv.DictReader(handle))
    assert sum(w["packet_count"] for w in windows) == expected_packets

    # Manual rebuild is idempotent and admin-only.
    assert client.post("/api/v1/windows/build", json={"traffic_source_id": source_id}, headers=bearer(viewer["access_token"])).status_code == 403
    rebuilt = client.post("/api/v1/windows/build", json={"traffic_source_id": source_id}, headers=bearer(admin["access_token"]))
    assert rebuilt.status_code == 201 and rebuilt.json()["windows_written"] == 5


def unique_csv(index: int) -> bytes:
    """A valid one-flow CSV whose content hash differs per index, so each upload is a new import."""
    return (
        "timestamp,src_ip,dst_ip,src_port,dst_port,protocol,packets,bytes\n"
        f"2026-08-28T18:00:00.000Z,192.168.10.{index + 1},10.0.0.2,49152,443,TCP,{index + 1},100\n"
    ).encode()


def upload(client, token: str, index: int, source: str):
    return client.post(
        "/api/v1/ingestion/upload",
        headers=bearer(token),
        data={"source_name": source},
        files={"file": (f"flows-{index}.csv", unique_csv(index), "text/csv")},
    )


def test_upload_is_rate_limited_per_user(client, seeded_users) -> None:
    """Only genuinely new imports consume the budget: rejected files and idempotent repeats do not."""
    admin = login(client, "admin@what-the-hack.local", seeded_users["admin@what-the-hack.local"])
    token = admin["access_token"]

    # Rejected before the limiter runs, so these must not count against the budget.
    for _ in range(5):
        assert client.post("/api/v1/ingestion/upload", headers=bearer(token), files={"file": ("x.txt", b"x", "text/plain")}).status_code == 415

    for index in range(10):
        response = upload(client, token, index, f"rate-limit-{index}")
        assert response.status_code == 201, response.text

    # The budget is now spent, but re-sending an already completed file is idempotent and
    # still returns its original job instead of a 429 (a demo must not lock the analyst out).
    repeat = upload(client, token, 0, "rate-limit-0")
    assert repeat.status_code == 201, repeat.text

    blocked = upload(client, token, 99, "rate-limit-overflow")
    assert blocked.status_code == 429
