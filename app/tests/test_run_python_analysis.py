"""Tests for POST /skills/run_python_analysis."""
import pytest
import app.services.skills.run_python_analysis as _rpa_module
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
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"
    assert data["error_type"] == "SECURITY_VIOLATION"
    assert "os" in data["message"]


def test_import_sys_is_blocked(client: TestClient):
    code = "import sys\nprint(sys.version)"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"


def test_open_call_is_blocked(client: TestClient):
    code = "f = open('/etc/passwd', 'r')\nprint(f.read())"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"
    assert "open" in data["message"]


def test_eval_call_is_blocked(client: TestClient):
    code = "result = eval('1+1')\nprint(result)"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"


def test_non_select_sql_is_blocked(client: TestClient):
    code = (
        "df = read_sql('INSERT INTO saved_queries (title, natural_language_query) "
        "VALUES (\"x\", \"x\")')\nprint(df)"
    )
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code in (403, 422)
    data = resp.json()["detail"]
    assert data["status"] in ("blocked", "failed")


def test_syntax_error_returns_error(client: TestClient):
    code = "def foo(\n    print('bad')"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 422
    data = resp.json()["detail"]
    assert data["status"] == "blocked"


def test_runtime_error_returns_structured_error(client: TestClient):
    code = "x = 1 / 0\nprint(x)"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 422
    data = resp.json()["detail"]
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


# ---------------------------------------------------------------------------
# Timeout tests  (monkeypatch EXECUTION_TIMEOUT to 3 s so tests run fast)
# ---------------------------------------------------------------------------

@pytest.fixture()
def short_timeout(monkeypatch):
    """Temporarily reduce the subprocess timeout to 3 seconds."""
    monkeypatch.setattr(_rpa_module, "EXECUTION_TIMEOUT", 3)
    yield


def test_infinite_loop_is_terminated(client: TestClient, short_timeout):
    """An infinite loop must be killed and return EXECUTION_TIMEOUT error."""
    code = "while True:\n    pass"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 408
    data = resp.json()["detail"]
    assert data["status"] == "failed"
    assert data["error_type"] == "EXECUTION_TIMEOUT"
    assert "exceeded" in data["message"].lower() or "timeout" in data["message"].lower()


def test_sleep_beyond_limit_is_terminated(client: TestClient, short_timeout):
    """Sleeping beyond the timeout must also be terminated."""
    code = "import math\nmath.factorial(0)\nwhile True:\n    x = 1 + 1"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 408
    data = resp.json()["detail"]
    assert data["status"] == "failed"
    assert data["error_type"] == "EXECUTION_TIMEOUT"


def test_normal_code_finishes_within_timeout(client: TestClient, short_timeout):
    """Normal fast code must still succeed even with a short timeout."""
    code = "print(sum(range(1000)))"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "499500" in data["stdout"]


def test_timeout_error_includes_hint(client: TestClient, short_timeout):
    """Timeout response must include a hint field to guide the LLM agent."""
    code = "while True:\n    pass"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 408
    data = resp.json()["detail"]
    assert data.get("hint") is not None, "Timeout response must include a 'hint' field"


# ---------------------------------------------------------------------------
# Negative / Authentication Tests
# ---------------------------------------------------------------------------

def test_wrong_api_key_returns_401(client: TestClient):
    resp = client.post(
        "/skills/run_python_analysis",
        json={"code": "print('hello')"},
        headers={"X-API-Key": "invalid-key"},
    )
    assert resp.status_code == 401


def test_missing_code_field_returns_422(client: TestClient):
    """POST with an empty body must be rejected — code field is required."""
    resp = client.post("/skills/run_python_analysis", json={})
    assert resp.status_code == 422


def test_empty_code_string_returns_200(client: TestClient):
    """An empty string is valid Python (no-op); the endpoint must return 200 with a status field."""
    resp = client.post("/skills/run_python_analysis", json={"code": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


# ---------------------------------------------------------------------------
# Jailbreak / Sandbox Escape Tests
# ---------------------------------------------------------------------------

def test_jailbreak_dunder_import_os_is_blocked(client: TestClient):
    """Using __import__('os') to bypass the import keyword must be blocked."""
    code = "x = __import__('os')\nprint(x.getcwd())"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"
    assert data["error_type"] == "SECURITY_VIOLATION"


def test_jailbreak_os_environ_access_is_blocked(client: TestClient):
    """Attempting to read environment variables through os must be blocked."""
    code = "import os\nprint(os.environ.get('QWEN_API_KEY', 'not_found'))"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"
    assert data["error_type"] == "SECURITY_VIOLATION"


def test_jailbreak_subprocess_spawn_is_blocked(client: TestClient):
    """Attempting to spawn a shell subprocess must be blocked before execution."""
    code = "import subprocess\nresult = subprocess.run(['pwd'], capture_output=True)\nprint(result.stdout.decode())"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"
    assert data["error_type"] == "SECURITY_VIOLATION"


def test_jailbreak_write_to_filesystem_is_blocked(client: TestClient):
    """Attempting to write a file using open() in write mode must be blocked."""
    code = "f = open('/tmp/pwned.txt', 'w')\nf.write('hacked')\nf.close()"
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["status"] == "blocked"
    assert data["error_type"] == "SECURITY_VIOLATION"
