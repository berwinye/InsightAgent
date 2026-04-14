# InsightAgent

An enterprise sales data Web API system built with **FastAPI + MySQL 8 + Docker**, featuring a **Qwen-powered self-loop agent** for natural language data analysis.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI (Python 3.11) |
| Database | MySQL 8 (`enterprise_api`) |
| ORM | SQLAlchemy 2.0 |
| LLM Agent | Qwen (Alibaba Bailian – OpenAI-compatible) |
| Containerisation | Docker + Docker Compose |
| Data | Classic Models sample dataset |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose Network                 │
│                                                           │
│  ┌──────────────────────┐    ┌──────────────────────┐   │
│  │   FastAPI Container   │    │   MySQL 8 Container   │   │
│  │   (insightagent_api)  │◄──►│ (insightagent_mysql)  │   │
│  │                       │    │                       │   │
│  │  app_rw → CRUD API    │    │  enterprise_api DB    │   │
│  │  app_ro → Skills &    │    │  (classicmodels data  │   │
│  │           Analytics   │    │   + custom tables)    │   │
│  └──────────────────────┘    └──────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Dual-account design:**
- `app_rw` — SELECT / INSERT / UPDATE / DELETE on `enterprise_api.*` (used by CRUD routes)
- `app_ro` — SELECT only (used by analytics, observe_schema, run_python_analysis)

---

## API Documentation

| Format | Location |
|--------|----------|
| **Full API Reference (PDF)** | [`docs/API.pdf`](docs/API.pdf) |
| **Full API Reference (Markdown)** | [`docs/API.md`](docs/API.md) |
| **Interactive Swagger UI** | `http://localhost:8000/docs` (requires running stack) |
| **OpenAPI JSON** | `http://localhost:8000/openapi.json` |

`docs/API.pdf` / `docs/API.md` covers every endpoint, all parameters, example requests/responses, authentication flow, and error codes.

---

## Directory Structure

```
InsightAgent/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── README.md
├── classicmodels.sql              ← source data (do not commit credentials)
├── docker/mysql/init/
│   ├── 01_setup.sh                ← creates users, custom tables
│   └── 02_import.sh               ← imports classicmodels data
└── app/
    ├── main.py
    ├── api/routes/
    │   ├── employees.py
    │   ├── products.py
    │   ├── saved_queries.py       ← full CRUD
    │   ├── analytics.py           ← pre-built analytics + agent endpoint
    │   └── skills.py              ← observe_schema + run_python_analysis
    ├── core/                      ← config, database engines, exceptions
    ├── db/                        ← rw/ro session factories, schema reader
    ├── models/                    ← SQLAlchemy ORM models
    ├── schemas/                   ← Pydantic request/response schemas
    ├── services/
    │   ├── analytics_service.py
    │   ├── agent_service.py       ← Qwen self-loop agent
    │   └── skills/
    │       ├── observe_schema.py
    │       ├── run_python_analysis.py
    │       ├── ast_guard.py       ← static AST security check
    │       ├── sql_guard.py       ← SQL keyword check
    │       ├── python_worker.py   ← isolated subprocess executor
    │       └── result_serializer.py
    └── tests/
        ├── conftest.py
        ├── ai_judge.py            ← LLM-based semantic test evaluator
        ├── test_observe_schema.py
        ├── test_run_python_analysis.py
        ├── test_saved_queries.py
        ├── test_api_negative.py   ← auth & validation failure tests
        ├── test_multistep_agent.py ← multi-step LLM agent + jailbreak tests
        └── test_anomaly_detection.py ← data anomaly detection tests
```

---

## Quick Start

### 1. Clone / enter the project

```bash
cd InsightAgent
```

### 2. Create the `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
MYSQL_ROOT_PASSWORD=rootpassword123
MYSQL_DATABASE=enterprise_api
MYSQL_APP_RW_USER=app_rw
MYSQL_APP_RW_PASSWORD=rw_password123
MYSQL_APP_RO_USER=app_ro
MYSQL_APP_RO_PASSWORD=ro_password123
MYSQL_HOST=mysql
MYSQL_PORT=3306

# API Authentication (leave empty to disable auth)
API_KEY=insightagent-secret-key

QWEN_API_KEY=sk-your-api-key-here
QWEN_MODEL=qwen-plus
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 3. Start with Docker Compose

```bash
docker compose up --build
```

On first start the MySQL container will:
1. Create the `enterprise_api` database
2. Create `app_rw` and `app_ro` accounts with appropriate permissions
3. Create `saved_queries` and `analysis_logs` tables
4. Import all `classicmodels` data into `enterprise_api`

The API will be available at **http://localhost:8000** once MySQL is healthy.

### 4. Access Swagger UI

```
http://localhost:8000/docs
```

### 5. Health check

```bash
curl http://localhost:8000/health
```

---

## API Reference

### Employees (read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/employees` | List all employees |
| GET | `/employees/{id}` | Get employee by ID |

### Products (read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products |
| GET | `/products/{code}` | Get product by code |

### Saved Queries (full CRUD)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/saved-queries` | Create a saved query |
| GET | `/saved-queries` | List all saved queries |
| GET | `/saved-queries/{id}` | Get by ID |
| PUT | `/saved-queries/{id}` | Update by ID |
| DELETE | `/saved-queries/{id}` | Delete by ID |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/store-sales-summary` | Revenue & order counts by office |
| GET | `/analytics/product-ranking` | Products ranked by revenue |
| GET | `/analytics/employee-performance` | Sales KPIs per employee |
| GET | `/analytics/sales-trend` | Monthly revenue trend (optional `?year=2004`) |
| POST | `/analytics/analyze` | Natural language analysis (Qwen agent) |
| GET | `/analytics/logs` | List past analysis run logs |
| GET | `/analytics/logs/{log_id}/turns` | Per-turn LLM details for an analysis run |

### Skills

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/skills/observe_schema` | Return full DB schema (tables, columns, PKs, FKs) |
| POST | `/skills/run_python_analysis` | Execute sandboxed Python code |

---

## Skill: observe_schema

**Endpoint:** `POST /skills/observe_schema`  
**Body:** empty  
**Auth:** uses read-only `app_ro` account

Returns the complete schema of `enterprise_api`:
```json
{
  "database": "enterprise_api",
  "tables": [
    {
      "table_name": "employees",
      "columns": [
        {"name": "employeeNumber", "declared_type": "INT", "nullable": false, "is_primary_key": true}
      ],
      "foreign_keys": [
        {"from_column": "officeCode", "ref_table": "offices", "ref_column": "officeCode"}
      ]
    }
  ]
}
```

---

## Skill: run_python_analysis

**Endpoint:** `POST /skills/run_python_analysis`  
**Body:** `{"code": "<python source>"}`

### Security pipeline

```
Incoming code
     │
     ▼
┌─────────────┐   fail   ┌──────────────────────┐
│  AST Guard  │─────────►│ blocked + error JSON  │
└─────────────┘          └──────────────────────┘
     │ pass
     ▼
┌────────────────────────────────────────────┐
│  Subprocess Worker (isolated process)       │
│  ┌──────────────────────────────────────┐  │
│  │  Controlled namespace:               │  │
│  │  - read_sql() via app_ro account     │  │
│  │  - pandas, numpy, math, statistics   │  │
│  │  - restricted builtins (no open/eval)│  │
│  │  - 30 s timeout                      │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
     │
     ▼
Structured JSON result (stdout / error)
```

### Allowed imports

`pandas`, `numpy`, `math`, `statistics`, `datetime`, `re`

### Forbidden (AST-blocked)

`os`, `sys`, `subprocess`, `socket`, `requests`, `pathlib`, `open()`, `eval()`, `exec()`, `compile()`, `__import__()`

### Example request

```bash
curl -X POST http://localhost:8000/skills/run_python_analysis \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import pandas as pd\ndf = read_sql(\"SELECT productLine, SUM(quantityOrdered * priceEach) AS revenue FROM orderdetails od JOIN products p ON od.productCode = p.productCode GROUP BY productLine ORDER BY revenue DESC\")\nprint(df.to_csv(index=False))"
  }'
```

---

## Natural Language Analysis Agent

**Endpoint:** `POST /analytics/analyze`  
**Body:** `{"question": "Compare total revenue of each office."}`

### Agent self-loop (max 8 iterations)

```
User question
     │
     ▼
1. observe_schema  →  DB context
     │
     ▼
2. LLM generates Python code
     │
     ▼
3. run_python_analysis
     │
     ├── success → LLM reads stdout → may call final_answer
     │
     └── error   → LLM reads error → fixes code → retry
          │
          └── (repeat up to 8 times)
               │
               ▼
         final_answer(text)  ←  stop function
```

### Example

```bash
curl -X POST http://localhost:8000/analytics/analyze \
  -H "X-API-Key: insightagent-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which product line generated the most revenue?"}'
```

Response:
```json
{
  "answer": "Classic Cars generated the most revenue at $3,853,438.94...",
  "iterations": 3,
  "generated_code": "import pandas as pd\n...",
  "saved_query_id": 1,
  "log_id": 5,
  "tool_trace": ["observe_schema", "run_python_analysis", "final_answer"]
}
```

---

## Running Tests

Tests require a running MySQL instance. Start the stack first:

```bash
docker compose up -d

# Wait for MySQL to be healthy, then run tests inside the api container
docker exec insightagent_api pytest app/tests/ -v
```

Or locally (with a running DB and `.env` configured):

```bash
pip install -r requirements.txt
pytest app/tests/ -v
```

---

## Stopping

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop containers, remove data volume
```

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| **Dual MySQL accounts** | `app_rw` for CRUD; `app_ro` for analysis. Even if injected code bypasses Python-level guards, the DB account prevents writes. |
| **AST guard before execution** | Reject dangerous imports/calls before a subprocess is ever spawned — fast and safe. |
| **Subprocess isolation** | User code runs in a separate process, preventing it from accessing FastAPI's internal state or memory. |
| **`read_sql()` injection** | User code never holds a DB connection object directly; all queries are mediated through a trusted helper that enforces SQL guards and row limits. |
| **Agent self-loop** | Single-round Q&A would fail on complex multi-table analysis. The agent iteratively explores the schema, writes code, reads errors, and refines — mirroring expert analyst behaviour. |