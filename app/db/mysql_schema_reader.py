from typing import Any
from sqlalchemy import text
from app.core.database import ro_engine
from app.core.config import settings


def read_schema() -> dict[str, Any]:
    """Read full schema from information_schema using the read-only account."""
    db_name = settings.MYSQL_DATABASE

    with ro_engine.connect() as conn:
        tables_result = conn.execute(
            text(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = :db AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME"
            ),
            {"db": db_name},
        ).fetchall()

        table_names = [row[0] for row in tables_result]

        columns_result = conn.execute(
            text(
                "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, ORDINAL_POSITION "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = :db "
                "ORDER BY TABLE_NAME, ORDINAL_POSITION"
            ),
            {"db": db_name},
        ).fetchall()

        pk_result = conn.execute(
            text(
                "SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME "
                "FROM information_schema.KEY_COLUMN_USAGE kcu "
                "JOIN information_schema.TABLE_CONSTRAINTS tc "
                "  ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME "
                "  AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA "
                "  AND kcu.TABLE_NAME = tc.TABLE_NAME "
                "WHERE kcu.TABLE_SCHEMA = :db AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'"
            ),
            {"db": db_name},
        ).fetchall()

        fk_result = conn.execute(
            text(
                "SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME, "
                "       kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME "
                "FROM information_schema.KEY_COLUMN_USAGE kcu "
                "JOIN information_schema.TABLE_CONSTRAINTS tc "
                "  ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME "
                "  AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA "
                "  AND kcu.TABLE_NAME = tc.TABLE_NAME "
                "WHERE kcu.TABLE_SCHEMA = :db AND tc.CONSTRAINT_TYPE = 'FOREIGN KEY'"
            ),
            {"db": db_name},
        ).fetchall()

    pk_set: dict[str, set[str]] = {}
    for row in pk_result:
        pk_set.setdefault(row[0], set()).add(row[1])

    fk_map: dict[str, list[dict]] = {}
    for row in fk_result:
        fk_map.setdefault(row[0], []).append(
            {"from_column": row[1], "ref_table": row[2], "ref_column": row[3]}
        )

    col_map: dict[str, list[dict]] = {}
    for row in columns_result:
        tname = row[0]
        col_map.setdefault(tname, []).append(
            {
                "name": row[1],
                "declared_type": row[2].upper(),
                "full_type": row[3],
                "nullable": row[4] == "YES",
                "is_primary_key": row[1] in pk_set.get(tname, set()),
            }
        )

    tables = []
    for tname in table_names:
        tables.append(
            {
                "table_name": tname,
                "columns": col_map.get(tname, []),
                "foreign_keys": fk_map.get(tname, []),
            }
        )

    return {"database": db_name, "tables": tables}
