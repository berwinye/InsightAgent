"""Tests for POST /skills/observe_schema."""
import pytest
from fastapi.testclient import TestClient


def test_observe_schema_returns_200(client: TestClient):
    resp = client.post("/skills/observe_schema")
    assert resp.status_code == 200


def test_observe_schema_has_database_key(client: TestClient):
    data = client.post("/skills/observe_schema").json()
    assert "database" in data
    assert data["database"] == "enterprise_api"


def test_observe_schema_has_tables_list(client: TestClient):
    data = client.post("/skills/observe_schema").json()
    assert "tables" in data
    assert isinstance(data["tables"], list)
    assert len(data["tables"]) > 0


def test_observe_schema_includes_employees_table(client: TestClient):
    data = client.post("/skills/observe_schema").json()
    table_names = [t["table_name"] for t in data["tables"]]
    assert "employees" in table_names


def test_observe_schema_columns_have_required_fields(client: TestClient):
    data = client.post("/skills/observe_schema").json()
    for table in data["tables"]:
        assert "table_name" in table
        assert "columns" in table
        assert "foreign_keys" in table
        for col in table["columns"]:
            assert "name" in col
            assert "declared_type" in col
            assert "nullable" in col
            assert "is_primary_key" in col


def test_observe_schema_primary_keys_present(client: TestClient):
    data = client.post("/skills/observe_schema").json()
    emp = next(t for t in data["tables"] if t["table_name"] == "employees")
    pk_cols = [c["name"] for c in emp["columns"] if c["is_primary_key"]]
    assert "employeeNumber" in pk_cols


def test_observe_schema_foreign_keys_present(client: TestClient):
    data = client.post("/skills/observe_schema").json()
    emp = next(t for t in data["tables"] if t["table_name"] == "employees")
    fk_from_cols = [fk["from_column"] for fk in emp["foreign_keys"]]
    assert "officeCode" in fk_from_cols


def test_observe_schema_stable_structure(client: TestClient):
    r1 = client.post("/skills/observe_schema").json()
    r2 = client.post("/skills/observe_schema").json()
    assert r1["tables"] == r2["tables"]
