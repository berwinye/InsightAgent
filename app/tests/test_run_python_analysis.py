"""Tests for POST /skills/run_python_analysis."""
import pytest
from fastapi.testclient import TestClient


def test_valid_analysis_code_succeeds(client: TestClient):
    code = (
        "import pandas as pd\n"
        "df = read_sql('SELECT productCode, productName FROM products LIMIT 5')\n"
        "print(df.to_csv(index=False))"
    )
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "stdout" in data
    assert len(data["stdout"]) > 0


def test_import_os_is_blocked(client: TestClient):
    code = "import os\nprint(os.getcwd())"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert data["error_type"] == "SECURITY_VIOLATION"
    assert "os" in data["message"]


def test_import_sys_is_blocked(client: TestClient):
    code = "import sys\nprint(sys.version)"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"


def test_open_call_is_blocked(client: TestClient):
    code = "f = open('/etc/passwd', 'r')\nprint(f.read())"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert "open" in data["message"]


def test_eval_call_is_blocked(client: TestClient):
    code = "result = eval('1+1')\nprint(result)"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"


def test_non_select_sql_is_blocked(client: TestClient):
    code = (
        "df = read_sql('INSERT INTO saved_queries (title, natural_language_query) "
        "VALUES (\"x\", \"x\")')\nprint(df)"
    )
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("blocked", "failed")


def test_syntax_error_returns_error(client: TestClient):
    code = "def foo(\n    print('bad')"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"


def test_runtime_error_returns_structured_error(client: TestClient):
    code = "x = 1 / 0\nprint(x)"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "ZeroDivisionError" in data["message"]


def test_pandas_analysis_works(client: TestClient):
    code = (
        "import pandas as pd\n"
        "import numpy as np\n"
        "df = read_sql('SELECT quantityOrdered, priceEach FROM orderdetails LIMIT 100')\n"
        "df['revenue'] = df['quantityOrdered'] * df['priceEach']\n"
        "print('Total revenue:', round(df['revenue'].sum(), 2))\n"
    )
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Total revenue" in data["stdout"]
