"""
Anomaly detection tests — verifies that the data analysis tools can surface
real data quality issues in the classicmodels / enterprise_api dataset.

Confirmed anomalies found in the dataset:
  - Product S18_3233 (1985 Toyota Supra): 7,733 units in stock, zero historical orders.
  - No products sold below buy price (expected: clean pricing).
  - No zero-credit customers with active orders (expected: no bad-debt anomaly).
"""
import json
import pytest
from fastapi.testclient import TestClient
from app.tests.ai_judge import ai_judge


# ---------------------------------------------------------------------------
# Helper: call run_python_analysis and assert success
# ---------------------------------------------------------------------------

def _run(client: TestClient, code: str) -> dict:
    resp = client.post("/skills/run_python_analysis", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success", f"Execution failed: {data.get('message')}"
    return data


# ---------------------------------------------------------------------------
# Test 1: Products never ordered (dead stock anomaly)
# ---------------------------------------------------------------------------

def test_never_ordered_products_exist(client: TestClient):
    """At least one product must exist that has stock but zero historical orders."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT p.productCode, p.productName, p.quantityInStock
    FROM products p
    LEFT JOIN orderdetails od ON od.productCode = p.productCode
    WHERE od.productCode IS NULL
      AND p.quantityInStock > 0
    ORDER BY p.quantityInStock DESC
''')
print(df.to_json(orient='records'))
"""
    result = _run(client, code)
    records = json.loads(result["stdout"].strip())
    assert len(records) >= 1, "Expected at least one dead-stock product"


def test_toyota_supra_is_never_ordered(client: TestClient):
    """S18_3233 (1985 Toyota Supra) should appear in the dead-stock list."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT p.productCode, p.productName, p.quantityInStock
    FROM products p
    LEFT JOIN orderdetails od ON od.productCode = p.productCode
    WHERE od.productCode IS NULL AND p.productCode = 'S18_3233'
''')
print(df.to_json(orient='records'))
"""
    result = _run(client, code)
    records = json.loads(result["stdout"].strip())
    assert len(records) == 1, "S18_3233 should have zero orders"
    assert records[0]["productCode"] == "S18_3233"
    assert records[0]["quantityInStock"] > 0


def test_toyota_supra_stock_is_high(client: TestClient):
    """S18_3233 stock should be above 5,000 units — a significant stranded-inventory risk."""
    code = """
import pandas as pd

df = read_sql("SELECT quantityInStock FROM products WHERE productCode = 'S18_3233'")
print(int(df['quantityInStock'].iloc[0]))
"""
    result = _run(client, code)
    stock = int(result["stdout"].strip())
    assert stock > 5000, f"Expected stock > 5000, got {stock}"


# ---------------------------------------------------------------------------
# Test 2: Price-below-cost anomaly (should be clean)
# ---------------------------------------------------------------------------

def test_no_orders_below_buy_price(client: TestClient):
    """No order line should have priceEach < buyPrice (no below-cost sales)."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT od.orderNumber, od.productCode, od.priceEach, p.buyPrice,
           ROUND(od.priceEach - p.buyPrice, 2) AS margin
    FROM orderdetails od
    JOIN products p ON od.productCode = p.productCode
    WHERE od.priceEach < p.buyPrice
''')
print(len(df))
"""
    result = _run(client, code)
    count = int(result["stdout"].strip())
    assert count == 0, f"Found {count} order lines sold below cost price — unexpected"


def test_profit_margin_stats(client: TestClient):
    """Overall margin stats: avg margin must be positive, min margin must be >= 0."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT
        ROUND(MIN(od.priceEach - p.buyPrice), 2)  AS min_margin,
        ROUND(AVG(od.priceEach - p.buyPrice), 2)  AS avg_margin,
        ROUND(MAX(od.priceEach - p.buyPrice), 2)  AS max_margin
    FROM orderdetails od
    JOIN products p ON od.productCode = p.productCode
''')
print(df.to_json(orient='records'))
"""
    result = _run(client, code)
    stats = json.loads(result["stdout"].strip())[0]
    assert stats["avg_margin"] > 0, "Average margin should be positive"
    assert stats["min_margin"] >= 0, "Minimum margin should not be negative"


# ---------------------------------------------------------------------------
# Test 3: Zero-credit customers with orders (bad-debt risk)
# ---------------------------------------------------------------------------

def test_no_zero_credit_customers_with_orders(client: TestClient):
    """Customers with creditLimit = 0 should not have any orders."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT c.customerNumber, c.customerName, c.creditLimit,
           COUNT(o.orderNumber) AS order_count
    FROM customers c
    JOIN orders o ON o.customerNumber = c.customerNumber
    WHERE c.creditLimit = 0
    GROUP BY c.customerNumber, c.customerName, c.creditLimit
''')
print(len(df))
"""
    result = _run(client, code)
    count = int(result["stdout"].strip())
    assert count == 0, f"Found {count} zero-credit customers with orders — bad-debt risk"


def test_customers_with_zero_credit_exist(client: TestClient):
    """There are customers with creditLimit = 0 in the DB, just none with orders."""
    code = """
import pandas as pd

df = read_sql('SELECT COUNT(*) AS cnt FROM customers WHERE creditLimit = 0')
print(int(df['cnt'].iloc[0]))
"""
    result = _run(client, code)
    count = int(result["stdout"].strip())
    assert count >= 1, "Expected at least one customer with creditLimit = 0"


# ---------------------------------------------------------------------------
# Test 4: Overdue orders anomaly (shipped after required date)
# ---------------------------------------------------------------------------

def test_late_shipments_exist(client: TestClient):
    """Some orders were shipped after the requiredDate — detect late deliveries."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT orderNumber, orderDate, requiredDate, shippedDate,
           DATEDIFF(shippedDate, requiredDate) AS days_late
    FROM orders
    WHERE shippedDate > requiredDate
    ORDER BY days_late DESC
''')
print(len(df))
print(df.head(3).to_csv(index=False))
"""
    result = _run(client, code)
    lines = result["stdout"].strip().splitlines()
    late_count = int(lines[0])
    assert late_count > 0, "Expected some late shipments in the dataset"


def test_late_shipments_summary(client: TestClient):
    """Verify the average lateness of overdue shipments."""
    code = """
import pandas as pd

df = read_sql('''
    SELECT
        COUNT(*)                                    AS late_order_count,
        ROUND(AVG(DATEDIFF(shippedDate, requiredDate)), 1) AS avg_days_late,
        MAX(DATEDIFF(shippedDate, requiredDate))    AS max_days_late
    FROM orders
    WHERE shippedDate > requiredDate
''')
print(df.to_json(orient='records'))
"""
    result = _run(client, code)
    stats = json.loads(result["stdout"].strip())[0]
    assert stats["late_order_count"] > 0
    assert stats["avg_days_late"] > 0
    assert stats["max_days_late"] >= stats["avg_days_late"]


# ---------------------------------------------------------------------------
# Test 5: Full agent — anomaly detection via NLQ
# ---------------------------------------------------------------------------

@pytest.mark.flaky(reruns=2, reruns_delay=3)
def test_agent_finds_dead_stock_anomaly(client: TestClient):
    """Agent should identify S18_3233 as a dead-stock product via natural language."""
    question = (
        "Find the product with the highest stock quantity that has never had any sales orders. "
        "List its product code, name, and stock quantity."
    )
    resp = client.post("/analytics/analyze", json={"question": question})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"], "Agent should return a non-empty answer"

    reasoning, passed = ai_judge(
        question=question,
        result=data,
        criteria=(
            "The agent must have queried the database and identified the product with the "
            "highest stock that has never been ordered. The correct answer is product S18_3233 "
            "(1985 Toyota Supra) with approximately 7,733 units in stock. "
            "The answer should mention the product code (S18_3233) or the product name "
            "(Toyota Supra or 1985 Toyota Supra) and a stock quantity above 7,000."
        ),
    )
    print(f"\n  AI Judge reasoning: {reasoning}")
    assert passed, f"AI Judge ruled No:\n{reasoning}"


def test_agent_anomaly_report_is_saved(client: TestClient):
    """Agent NLQ should auto-save the result to saved_queries."""
    resp = client.post(
        "/analytics/analyze",
        json={"question": "Are there any orders where products were sold below their purchase cost price? List the exact count."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("saved_query_id") is not None, (
        "Successful analysis should be saved to saved_queries"
    )
    sq_id = data["saved_query_id"]

    get_resp = client.get(f"/saved-queries/{sq_id}")
    assert get_resp.status_code == 200
    saved = get_resp.json()
    assert saved["generated_code"] is not None
    assert saved["natural_language_query"] != ""
