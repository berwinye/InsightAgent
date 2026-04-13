from typing import Any
from sqlalchemy import text
from app.core.database import ro_engine


def _run_ro(sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    with ro_engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def get_store_sales_summary() -> list[dict]:
    sql = """
        SELECT
            o.officeCode,
            o.city,
            o.country,
            COUNT(DISTINCT ord.orderNumber)                              AS total_orders,
            ROUND(SUM(od.quantityOrdered * od.priceEach), 2)            AS total_revenue,
            ROUND(AVG(ot.order_total), 2)                               AS avg_order_value,
            COUNT(DISTINCT e.employeeNumber)                             AS employee_count
        FROM offices o
        JOIN employees e   ON e.officeCode          = o.officeCode
        JOIN customers c   ON c.salesRepEmployeeNumber = e.employeeNumber
        JOIN orders ord    ON ord.customerNumber    = c.customerNumber
        JOIN orderdetails od ON od.orderNumber      = ord.orderNumber
        JOIN (
            SELECT orderNumber, SUM(quantityOrdered * priceEach) AS order_total
            FROM orderdetails
            GROUP BY orderNumber
        ) ot ON ot.orderNumber = ord.orderNumber
        GROUP BY o.officeCode, o.city, o.country
        ORDER BY total_revenue DESC
    """
    return _run_ro(sql)


def get_product_ranking(limit: int = 20) -> list[dict]:
    sql = """
        SELECT
            p.productCode,
            p.productName,
            p.productLine,
            SUM(od.quantityOrdered)                              AS total_quantity,
            ROUND(SUM(od.quantityOrdered * od.priceEach), 2)    AS total_revenue
        FROM products p
        JOIN orderdetails od ON od.productCode = p.productCode
        GROUP BY p.productCode, p.productName, p.productLine
        ORDER BY total_revenue DESC
        LIMIT :lim
    """
    return _run_ro(sql, {"lim": limit})


def get_employee_performance() -> list[dict]:
    sql = """
        SELECT
            e.employeeNumber,
            CONCAT(e.firstName, ' ', e.lastName)                        AS employee_name,
            e.jobTitle,
            o.city                                                       AS office_city,
            COUNT(DISTINCT c.customerNumber)                             AS customer_count,
            COUNT(DISTINCT ord.orderNumber)                              AS order_count,
            ROUND(COALESCE(SUM(od.quantityOrdered * od.priceEach), 0), 2) AS total_sales
        FROM employees e
        LEFT JOIN offices o      ON o.officeCode             = e.officeCode
        LEFT JOIN customers c    ON c.salesRepEmployeeNumber = e.employeeNumber
        LEFT JOIN orders ord     ON ord.customerNumber       = c.customerNumber
        LEFT JOIN orderdetails od ON od.orderNumber          = ord.orderNumber
        GROUP BY e.employeeNumber, e.firstName, e.lastName, e.jobTitle, o.city
        ORDER BY total_sales DESC
    """
    return _run_ro(sql)


def get_sales_trend(year: int | None = None) -> list[dict]:
    if year:
        sql = """
            SELECT
                DATE_FORMAT(ord.orderDate, '%Y-%m')             AS month,
                COUNT(DISTINCT ord.orderNumber)                 AS order_count,
                ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS monthly_revenue
            FROM orders ord
            JOIN orderdetails od ON od.orderNumber = ord.orderNumber
            WHERE YEAR(ord.orderDate) = :yr
            GROUP BY DATE_FORMAT(ord.orderDate, '%Y-%m')
            ORDER BY month
        """
        return _run_ro(sql, {"yr": year})
    else:
        sql = """
            SELECT
                DATE_FORMAT(ord.orderDate, '%Y-%m')             AS month,
                COUNT(DISTINCT ord.orderNumber)                 AS order_count,
                ROUND(SUM(od.quantityOrdered * od.priceEach), 2) AS monthly_revenue
            FROM orders ord
            JOIN orderdetails od ON od.orderNumber = ord.orderNumber
            GROUP BY DATE_FORMAT(ord.orderDate, '%Y-%m')
            ORDER BY month
        """
        return _run_ro(sql)
