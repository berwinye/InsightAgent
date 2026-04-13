"""
Negative / failure tests for all remaining API endpoints.

Covers:
  - /employees           (auth, 404, 422)
  - /products            (auth, 404, 422)
  - /analytics/*         (auth, 422, 404)

Authentication, validation, and not-found cases for every endpoint group
that was not already covered in the skill- or saved-query-specific test files.
"""
import pytest
from fastapi.testclient import TestClient

BAD_KEY = {"X-API-Key": "invalid-key-xyz"}


# ===========================================================================
# Employees
# ===========================================================================

class TestEmployeesNegative:

    def test_list_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/employees", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_list_invalid_limit_returns_422(self, client: TestClient):
        """limit=0 violates the ge=1 constraint."""
        resp = client.get("/employees?limit=0")
        assert resp.status_code == 422

    def test_list_negative_skip_returns_422(self, client: TestClient):
        resp = client.get("/employees?skip=-1")
        assert resp.status_code == 422

    def test_get_nonexistent_employee_returns_404(self, client: TestClient):
        resp = client.get("/employees/999999")
        assert resp.status_code == 404

    def test_get_non_integer_id_returns_422(self, client: TestClient):
        resp = client.get("/employees/not-a-number")
        assert resp.status_code == 422

    def test_get_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/employees/1002", headers=BAD_KEY)
        assert resp.status_code == 401


# ===========================================================================
# Products
# ===========================================================================

class TestProductsNegative:

    def test_list_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/products", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_list_invalid_limit_returns_422(self, client: TestClient):
        resp = client.get("/products?limit=0")
        assert resp.status_code == 422

    def test_list_negative_skip_returns_422(self, client: TestClient):
        resp = client.get("/products?skip=-1")
        assert resp.status_code == 422

    def test_get_nonexistent_product_returns_404(self, client: TestClient):
        resp = client.get("/products/DOES_NOT_EXIST")
        assert resp.status_code == 404

    def test_get_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/products/S10_1678", headers=BAD_KEY)
        assert resp.status_code == 401


# ===========================================================================
# Analytics — pre-built endpoints
# ===========================================================================

class TestAnalyticsPrebuiltNegative:

    def test_store_sales_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/analytics/store-sales-summary", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_product_ranking_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/analytics/product-ranking", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_product_ranking_invalid_limit_returns_422(self, client: TestClient):
        """limit=0 violates ge=1."""
        resp = client.get("/analytics/product-ranking?limit=0")
        assert resp.status_code == 422

    def test_product_ranking_limit_over_max_returns_422(self, client: TestClient):
        """limit=101 violates le=100."""
        resp = client.get("/analytics/product-ranking?limit=101")
        assert resp.status_code == 422

    def test_employee_performance_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/analytics/employee-performance", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_sales_trend_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/analytics/sales-trend", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_sales_trend_non_integer_year_returns_422(self, client: TestClient):
        """year must be an integer; a string value must be rejected."""
        resp = client.get("/analytics/sales-trend?year=abc")
        assert resp.status_code == 422


# ===========================================================================
# Analytics — agent endpoint
# ===========================================================================

class TestAnalyticsAgentNegative:

    def test_analyze_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.post(
            "/analytics/analyze",
            json={"question": "How many orders?"},
            headers=BAD_KEY,
        )
        assert resp.status_code == 401

    def test_analyze_missing_question_returns_422(self, client: TestClient):
        """POST with empty body must be rejected — question field is required."""
        resp = client.post("/analytics/analyze", json={})
        assert resp.status_code == 422

    def test_analyze_empty_question_still_returns_answer(self, client: TestClient):
        """An empty string question is technically valid; agent must respond."""
        resp = client.post("/analytics/analyze", json={"question": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data


# ===========================================================================
# Analytics — logs endpoints
# ===========================================================================

class TestAnalyticsLogsNegative:

    def test_logs_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/analytics/logs", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_logs_invalid_limit_returns_422(self, client: TestClient):
        resp = client.get("/analytics/logs?limit=0")
        assert resp.status_code == 422

    def test_logs_turns_nonexistent_log_returns_404(self, client: TestClient):
        resp = client.get("/analytics/logs/999999/turns")
        assert resp.status_code == 404

    def test_logs_turns_wrong_api_key_returns_401(self, client: TestClient):
        resp = client.get("/analytics/logs/1/turns", headers=BAD_KEY)
        assert resp.status_code == 401

    def test_logs_turns_non_integer_id_returns_422(self, client: TestClient):
        resp = client.get("/analytics/logs/not-a-number/turns")
        assert resp.status_code == 422
