"""Tests for /saved-queries CRUD endpoints."""
import pytest
from fastapi.testclient import TestClient


CREATE_PAYLOAD = {
    "title": "Test Query",
    "natural_language_query": "Show me total revenue by product line.",
    "generated_code": "import pandas as pd\nprint('test')",
    "result_summary": "Classic Cars had the highest revenue.",
}


def test_create_saved_query(client: TestClient):
    resp = client.post("/saved-queries", json=CREATE_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == CREATE_PAYLOAD["title"]
    assert data["id"] > 0


def test_list_saved_queries(client: TestClient):
    client.post("/saved-queries", json=CREATE_PAYLOAD)
    resp = client.get("/saved-queries")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1


def test_get_saved_query_by_id(client: TestClient):
    create_resp = client.post("/saved-queries", json=CREATE_PAYLOAD)
    created_id = create_resp.json()["id"]

    resp = client.get(f"/saved-queries/{created_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created_id
    assert data["title"] == CREATE_PAYLOAD["title"]


def test_update_saved_query(client: TestClient):
    create_resp = client.post("/saved-queries", json=CREATE_PAYLOAD)
    created_id = create_resp.json()["id"]

    update_payload = {"title": "Updated Title"}
    resp = client.put(f"/saved-queries/{created_id}", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["natural_language_query"] == CREATE_PAYLOAD["natural_language_query"]


def test_delete_saved_query(client: TestClient):
    create_resp = client.post("/saved-queries", json=CREATE_PAYLOAD)
    created_id = create_resp.json()["id"]

    del_resp = client.delete(f"/saved-queries/{created_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/saved-queries/{created_id}")
    assert get_resp.status_code == 404


def test_get_nonexistent_returns_404(client: TestClient):
    resp = client.get("/saved-queries/999999")
    assert resp.status_code == 404


def test_update_nonexistent_returns_404(client: TestClient):
    resp = client.put("/saved-queries/999999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_nonexistent_returns_404(client: TestClient):
    resp = client.delete("/saved-queries/999999")
    assert resp.status_code == 404
