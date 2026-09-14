"""Stage 1 tests.

These require a live Postgres. That is deliberate: they pass on your laptop
and will FAIL in CI until you make the pipeline spin up a throwaway database
container. Solving that is one of the most useful lessons in this project.
"""


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] == "up"


def test_create_then_list_message(client):
    r = client.post("/messages", json={"author": "mohamed", "content": "hello"})
    assert r.status_code == 201
    created = r.json()
    assert created["id"] > 0
    assert created["created_at"]

    r = client.get("/messages")
    assert any(m["id"] == created["id"] for m in r.json())

    client.delete(f"/messages/{created['id']}")


def test_delete_removes_message(client):
    created = client.post(
        "/messages", json={"author": "mohamed", "content": "temporary"}
    ).json()

    assert client.delete(f"/messages/{created['id']}").status_code == 204
    assert client.delete(f"/messages/{created['id']}").status_code == 404


def test_rejects_empty_author(client):
    r = client.post("/messages", json={"author": "", "content": "hi"})
    assert r.status_code == 422


def test_rejects_too_long_content(client):
    r = client.post("/messages", json={"author": "m", "content": "x" * 501})
    assert r.status_code == 422
