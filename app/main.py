import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, employees, products, saved_queries, skills
from app.core.config import settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="InsightAgent API",
    description=(
        "Enterprise sales data API with skill-based natural language analysis. "
        "Powered by FastAPI + MySQL 8 + Qwen (Alibaba Bailian).\n\n"
        "## Key Features\n"
        "- Full CRUD for **saved-queries**\n"
        "- Read-only endpoints for **employees** and **products**\n"
        "- Pre-built **analytics** endpoints (store sales, product ranking, employee performance, sales trend)\n"
        "- **Skill 1**: `POST /skills/observe_schema` – introspect the database schema\n"
        "- **Skill 2**: `POST /skills/run_python_analysis` – execute sandboxed Python code\n"
        "- **Agent**: `POST /analytics/analyze` – Qwen-powered self-loop analysis from natural language\n"
    ),
    version="1.0.0",
    contact={"name": "InsightAgent", "url": "https://github.com/berwinye/InsightAgent"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employees.router)
app.include_router(products.router)
app.include_router(saved_queries.router)
app.include_router(analytics.router)
app.include_router(skills.router)


@app.get("/", tags=["Health"], summary="Health check")
def root():
    return {
        "status": "ok",
        "service": "InsightAgent API",
        "version": "1.0.0",
        "docs": "/docs",
        "database": settings.MYSQL_DATABASE,
    }


@app.get("/health", tags=["Health"], summary="Detailed health check")
def health():
    from app.core.database import rw_engine, ro_engine
    from sqlalchemy import text

    checks: dict = {}
    for name, engine in [("rw", rw_engine), ("ro", ro_engine)]:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks[name] = "ok"
        except Exception as exc:
            checks[name] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "db_connections": checks}
