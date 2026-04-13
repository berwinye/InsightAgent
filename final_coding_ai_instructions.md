# XJCO3011 Coursework 1 Final Implementation Instructions (For the Code-Writing AI)

> This document is the final execution guide for “another AI responsible for writing the code.”
> The goal is not to discuss the solution, but to **directly implement a runnable, demonstrable project suitable for a high grade in the coursework according to this document**.
>
> The technology stack is fixed as follows:
> - **Python 3.11+**
> - **FastAPI**
> - **MySQL 8**
> - **Docker / Docker Compose**
> - The API service container and the database container must be separated and communicate over the network
> - Use the locally available `classicmodels.sql` as the initial data source

---

# 1. Project Objective

Implement an **enterprise sales data Web API system** that both satisfies the basic coursework requirements and demonstrates advanced functionality.

The system must include two layers of capabilities:

## Layer 1: Basic Data API (Mandatory)
It must satisfy the minimum coursework requirements:
- At least one data model must support full CRUD
- At least 4 HTTP API endpoints
- Use a database
- Return JSON
- Use appropriate status codes
- Be runnable and demonstrable locally

This project should provide at least the following business entities:
- Employees
- Products
- Offices (stores / sales offices)
- Orders / OrderDetails

Among these, **at least one entity must implement full CRUD**. Recommended choices:
- `employees`
- `products`
- or a newly added custom business table, such as `saved_queries` / `analysis_requests`

## Layer 2: Advanced Natural Language Analysis (Key Highlight)
After the user inputs a natural language question, the system must not call the LLM only once. Instead, it must enter an **agent self-loop workflow**.

This agent must be capable of:
1. Calling `observe_schema` to obtain the database structure
2. Autonomously planning the next step based on the schema
3. Generating Python analysis code and calling `run_python_analysis`
4. Continuing to revise the code and explore autonomously based on execution results or errors
5. Calling a **stop function** to output the final answer after confirming that the analysis is complete

In other words, the advanced analysis layer is not “single-round Q&A,” but rather **a self-looping agent + two skills + one stop function**.

The advanced functionality must clearly emphasize:
- agent self-looping
- skill design
- security
- isolation of code execution
- read-only database permissions
- support for complex data analysis tasks

---

# 2. Data Source and Import Requirements

## 2.1 Known Premise
The user has already saved `classicmodels.sql` locally.
The code-writing AI does not need to download the dataset again.

## 2.2 Required Database Initialization Steps
At project startup, the following steps must either be guided clearly or completed automatically:

### Step 1: Start the MySQL container
Use Docker Compose to start a MySQL 8 container.

### Step 2: Create the database
The database name must be fixed as:
- `enterprise_api`

### Step 3: Import the local SQL file
Import the user’s local `classicmodels.sql` into the `enterprise_api` database.

### Step 4: Create two database accounts
Two accounts must be created:

#### Management account (full permissions)
Used for the basic CRUD API.
For example:
- Username: `app_rw`
- Permissions: standard read/write privileges on `enterprise_api.*`

#### Analysis account (read-only)
Used for `observe_schema` and `run_python_analysis`.
For example:
- Username: `app_ro`
- Permissions: `SELECT` only

### Step 5: Verify account permissions
It must be verified that:
- `app_ro` can query data
- `app_ro` cannot execute INSERT / UPDATE / DELETE / CREATE / DROP / ALTER
- `app_rw` can perform normal read/write operations required by the basic API

---

# 3. Database Mapping Description

Use `classicmodels.sql` as the main business database.

## 3.1 Business Semantic Mapping
In code and documentation, the code-writing AI must consistently interpret classicmodels tables as follows:

- `employees` → employee table
- `offices` → store / sales office table
- `products` → product table
- `productlines` → product category table
- `customers` → customer table
- `orders` → order table
- `orderdetails` → sales detail table
- `payments` → payment / sales revenue table

## 3.2 Recommended Analytical Perspectives
The following analytical perspectives should be prioritized:
- average order amount by office/store
- total sales by office/store
- number of customers managed by each employee
- order performance associated with each employee
- product sales ranking
- sales distribution by product line
- sales trends within a time range

## 3.3 Custom Business Tables That May Be Added (Strongly Recommended)
To make it easier to satisfy full CRUD and better demonstrate system design, it is recommended to add 1–2 custom project tables, for example:

### `saved_queries`
Store users’ historical analysis requests:
- id
- title
- natural_language_query
- generated_code
- created_at
- updated_at

### `analysis_logs`
Store analysis execution logs:
- id
- query_text
- status
- error_type
- created_at

Benefits:
- Easier to implement full CRUD
- Easier to demonstrate system design ability
- More convenient for logging and testing
- More helpful for the oral examination

---

# 4. Overall System Architecture

It must be implemented as **two containers**:

## Container 1: MySQL
- MySQL 8
- Exposed port (for example 3306)
- Initialize the `enterprise_api` database
- Import `classicmodels.sql`
- Create `app_rw` and `app_ro`

## Container 2: FastAPI
- Python 3.11+
- Provide REST APIs
- SQLAlchemy or SQLModel or raw database access may be used
- Communicate with MySQL through the Docker Compose network

## Container Relationship
- The FastAPI container accesses MySQL through the internal network
- Basic CRUD routes use `app_rw`
- `observe_schema` and `run_python_analysis` routes use `app_ro`

---

# 5. Docker and Startup Requirements

The following must be provided:
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- startup instructions

## 5.1 docker-compose Must Include
At least two services:
- `api`
- `mysql`

## 5.2 MySQL Initialization Method
One of the following two approaches is preferred:

### Option A (Recommended)
Mount `classicmodels.sql` into the MySQL initialization directory, for example:
- `/docker-entrypoint-initdb.d/`

At the same time prepare an additional SQL initialization script to:
- create the `enterprise_api` database
- create `app_rw`
- create `app_ro`
- grant permissions

### Option B
Import manually via script after the container starts.

Requirement:
- The final effect must be identical
- README must explain it clearly

## 5.3 Environment Variables
At minimum include:
- MYSQL_DATABASE=enterprise_api
- MYSQL_ROOT_PASSWORD
- MYSQL_APP_RW_USER
- MYSQL_APP_RW_PASSWORD
- MYSQL_APP_RO_USER
- MYSQL_APP_RO_PASSWORD
- MYSQL_HOST=mysql
- MYSQL_PORT=3306

---

# 6. FastAPI Project Structure Requirements

Recommended directory structure:

```text
app/
├─ main.py
├─ api/
│  ├─ routes/
│  │  ├─ employees.py
│  │  ├─ products.py
│  │  ├─ saved_queries.py
│  │  ├─ analytics.py
│  │  └─ skills.py
├─ core/
│  ├─ config.py
│  ├─ database.py
│  ├─ security.py
│  └─ exceptions.py
├─ db/
│  ├─ rw_session.py
│  ├─ ro_session.py
│  └─ mysql_schema_reader.py
├─ models/
│  ├─ employees.py
│  ├─ products.py
│  ├─ saved_queries.py
│  └─ analysis_logs.py
├─ schemas/
│  ├─ employees.py
│  ├─ products.py
│  ├─ saved_queries.py
│  └─ skills.py
├─ services/
│  ├─ employees_service.py
│  ├─ products_service.py
│  ├─ saved_queries_service.py
│  ├─ analytics_service.py
│  └─ skills/
│     ├─ observe_schema.py
│     ├─ run_python_analysis.py
│     ├─ ast_guard.py
│     ├─ safe_import.py
│     ├─ sql_guard.py
│     ├─ python_worker.py
│     └─ result_serializer.py
└─ tests/
```

Requirements:
- Clear structure
- Separation of API layer, service layer, DB layer, and security layer
- Skill code placed in a dedicated directory

---

# 7. Basic REST API Functional Requirements

At least the following APIs must be implemented.

## 7.1 Full CRUD for At Least One Entity
It is recommended to implement full CRUD for `saved_queries`, because:
- It does not damage the original classicmodels business data
- It is easier to control
- It is more suitable for coursework demonstration

The following must be provided:
- `POST /saved-queries`
- `GET /saved-queries`
- `GET /saved-queries/{id}`
- `PUT /saved-queries/{id}`
- `DELETE /saved-queries/{id}`

## 7.2 Optional Additional CRUD
You may additionally provide CRUD for `employees` or `products`, but modifying the original business data should be done cautiously.

## 7.3 Analytics Endpoints (Recommended)
It is recommended to add several analytical endpoints to demonstrate advanced capability:
- `GET /analytics/store-sales-summary`
- `GET /analytics/product-ranking`
- `GET /analytics/employee-performance`
- `GET /analytics/sales-trend`

The purpose of these endpoints:
- Reinforce that the project is not CRUD only
- Better align with a high-grade direction
- Help demonstrate business value

---

# 8. Skill Design (Key Focus)

Two skills must be implemented:

## Skill 1: `observe_schema`
## Skill 2: `run_python_analysis`

These two skills are the core advanced highlight of the entire project and must be emphasized in implementation, documentation, and testing.

In addition, the system must include an external agent orchestration layer:
- the agent is allowed to self-loop
- the agent is encouraged to autonomously explore and revise over multiple rounds
- the agent outputs the final result by calling the stop function
- if `run_python_analysis` returns an error, the agent must read the error and continue attempting to fix the code

---

# 8A. External LLM Agent Self-Loop Requirements

The external LLM must be designed as an **agent**, not as a single-round static call.

## 8A.1 Agent Responsibilities
- receive the user’s natural language analysis question
- call `observe_schema` to obtain database context
- generate Python analysis code
- call `run_python_analysis`
- continue revising the code based on stdout or error information
- call the stop function at the appropriate time to output the final answer

## 8A.2 Stop Function Requirements
A stop function must be defined, for example:
- `final_answer(text: str)`
- or `stop_and_return(answer: str)`

The meaning of the stop function:
- explicitly tell the agent when to end the self-loop
- explicitly define the final outward-facing output
- avoid infinite looping

## 8A.3 Self-Loop Strategy
- By default, the agent is allowed to explore autonomously
- By default, multiple rounds of attempts are allowed
- When `run_python_analysis` returns an error, the agent should continue correcting the code
- When the result is already sufficient to support a conclusion, the agent should stop instead of continuing meaningless exploration

## 8A.4 Maximum Number of Loops
A maximum number of loops must be set, for example 5–8, to prevent infinite loops.

## 8A.5 Stop Conditions
Stop when any of the following conditions is met:
- the agent proactively calls the stop function
- the maximum loop count is reached
- the same error is repeated multiple times in a row
- the task is clearly impossible to complete

---

# 9. Detailed Implementation Requirements for Skill 1: observe_schema

## 9.1 Definition
`observe_schema` is a **zero-input, read-only, fixed-output** schema discovery skill.

Its purpose is to:
- inspect analyzable business tables in the MySQL database
- return table structure and relationship information
- provide database context to the external LLM

## 9.2 Input
No input parameters.

Suggested endpoint:
- `POST /skills/observe_schema`

The request body is empty.

## 9.3 Output
Output JSON must include at least:
- database name
- all table names
- column names of each table
- column types
- nullable
- primary keys
- foreign keys

Suggested output structure:

```json
{
  "database": "enterprise_api",
  "tables": [
    {
      "table_name": "employees",
      "columns": [
        {
          "name": "employeeNumber",
          "declared_type": "INT",
          "nullable": false,
          "is_primary_key": true
        }
      ],
      "foreign_keys": [
        {
          "from_column": "officeCode",
          "ref_table": "offices",
          "ref_column": "officeCode"
        }
      ]
    }
  ]
}
```

## 9.4 Data Source
It must connect to MySQL using the read-only account `app_ro`.

## 9.5 Implementation Method
Use MySQL `information_schema`.

At minimum, read the following:
- `information_schema.tables`
- `information_schema.columns`
- `information_schema.key_column_usage`
- `information_schema.table_constraints`

## 9.6 Output Content Requirements
Do not return sample data by default.
Return schema information only by default.

Reasons:
- save context
- reduce noise
- improve safety

## 9.7 Recommended Implementation Details
- sort tables by name
- sort columns of each table by ordinal position
- fix the output structure
- cache in memory or use short-term cache if appropriate

## 9.8 Error Handling
If the database connection fails, return:
- 500 Internal Server Error
- JSON error structure

For example:

```json
{
  "status": "failed",
  "error_type": "SCHEMA_READ_ERROR",
  "message": "Failed to inspect database schema."
}
```

---

# 10. Detailed Implementation Requirements for Skill 2: run_python_analysis (Most Important)

## 10.1 Definition
`run_python_analysis` is a **controlled Python code execution skill**.

It is not responsible for generating code.
It is only responsible for:
- receiving Python code generated by the external LLM agent
- performing security checks
- executing in a controlled environment
- returning standard output (stdout / `print` output) to the outside
- returning either results or structured errors

## 10.2 Input
Suggested endpoint:
- `POST /skills/run_python_analysis`

Request body:

```json
{
  "code": "import pandas as pd\n..."
}
```

There is only one field:
- `code`

## 10.3 Output
On success, return:
- execution status
- result type
- result preview
- row count / summary

On failure, return:
- execution status
- error type
- error message
- suggested hint

Example success:

```json
{
  "status": "success",
  "stdout": "productLine,revenue\nClassic Cars,123456.78\nVintage Cars,98765.43\n",
  "summary": {
    "line_count": 3
  }
}
```

Example failure:

```json
{
  "status": "blocked",
  "error_type": "SECURITY_VIOLATION",
  "message": "Import of module 'os' is not allowed.",
  "hint": "Use only pandas, numpy, math, statistics."
}
```

---

# 11. Core Execution Flow of run_python_analysis

The following flow must be implemented strictly:

## Step 1: Receive code
Read `code` from the request body.

## Step 2: AST static inspection
AST inspection must be performed before execution.

Goals:
- reject dangerous imports
- reject dangerous function calls
- block obviously illegal code before execution

## Step 3: Start an isolated worker
Do not execute code directly in the main FastAPI process.
It must run inside an isolated worker.

Recommended:
- start a worker via `subprocess`
- or use a dedicated Python child process

## Step 4: Construct a controlled runtime environment
The runtime environment may only allow:
- whitelisted builtins
- whitelisted imports
- MySQL read-only helper: `read_sql()`
- a controlled `print()` output channel

## Step 5: Execute the code
Execute the user code. The analysis result must be output through `print(...)` to stdout.

## Step 6: Collect stdout
The worker must capture standard output and return stdout as the primary result of this execution.

## Step 7: Return success or failure information
All exceptions must be returned in structured form.

---

# 12. Security Requirements for run_python_analysis

This is the focus of the project.

## 12.1 Database Permission Requirement
This skill **must use only the read-only account `app_ro`**.

Using `app_rw` is absolutely forbidden.

This way, even if the code tries to perform a write operation, the database account will block it.

## 12.2 Whitelist of Allowed Imports
Only the following modules are allowed:
- `pandas`
- `numpy`
- `math`
- `statistics`

Optionally allowed:
- `datetime`
- `re`

Everything else must be disallowed.

Explicitly forbidden:
- `os`
- `sys`
- `subprocess`
- `socket`
- `requests`
- `pathlib`
- `shutil`
- `importlib`
- any database driver used to reconnect directly to the database

## 12.3 No File Side Effects
The code must not be allowed to:
- create files
- modify files
- delete files
- rename files
- create directories

If any of the above illegal behaviors is detected, the system must:
1. immediately stop execution
2. return a structured error to the external agent
3. not continue executing the remaining code

## 12.4 No Network Access
The code must not be allowed to access the network.

## 12.5 No Shell / System Commands
The code must not be allowed to use:
- `os.system`
- `subprocess.*`
- any shell command

## 12.6 Forbidden Dangerous Built-ins
The following must be forbidden:
- `open`
- `eval`
- `exec`
- `compile`
- `input`
- `__import__` (replace with a controlled version)

---

# 13. AST Inspection Implementation Requirements

The code-writing AI must implement an AST guard.

## 13.1 Required Checks
### Import checks
- `import xxx`
- `from xxx import yyy`

If the module is not in the whitelist, reject immediately.

### Call checks
If any of the following calls appears, reject immediately:
- `open(...)`
- `eval(...)`
- `exec(...)`
- `compile(...)`
- `__import__(...)`

## 13.2 Return Method
If AST inspection fails, do not execute the code. Return directly:

```json
{
  "status": "blocked",
  "error_type": "SECURITY_VIOLATION",
  "message": "Import of module 'os' is not allowed."
}
```

---

# 14. MySQL Read-Only Helper: Implementation Requirements for read_sql()

External code must not be allowed to obtain a database connection directly.

Only one controlled helper must be provided, for example:
- `read_sql(sql: str, params: tuple = (), max_rows: int = 50000)`

## 14.1 Design Purpose
- external code can query the database
- but the database connection remains controlled by the service
- SQL security checks can be centralized
- result row limits can be centralized

## 14.2 Allowed SQL Types
Only allow:
- `SELECT`
- `WITH`

## 14.3 Explicitly Forbidden SQL Keywords
The following must be blocked:
- `INSERT`
- `UPDATE`
- `DELETE`
- `DROP`
- `ALTER`
- `CREATE`
- `TRUNCATE`
- `GRANT`
- `REVOKE`
- `SHOW GRANTS`
- `LOAD DATA`

## 14.4 Result Size Limitation
The following must be limited:
- maximum returned row count, for example 50000
- if the result is too large, return an error directly

## 14.5 Output Type
It is recommended that `read_sql()` directly return a pandas DataFrame.

---

# 15. Controlled Execution Environment Requirements

## 15.1 No Bare exec in the Main Service
The main FastAPI process must not directly execute the incoming code.

## 15.2 Isolated Worker
A worker must be run separately.

Recommended approach:
- `subprocess.run(..., timeout=5)`

## 15.3 Timeout Control
A timeout must be enforced, for example 5 seconds.

If a timeout occurs, return:

```json
{
  "status": "failed",
  "error_type": "EXECUTION_TIMEOUT",
  "message": "Execution exceeded 5 seconds."
}
```

## 15.4 Result Output Contract
The external code must place the final result into the variable:
- `result`

For example:

```python
result = df.groupby("productLine")["sales"].sum().reset_index()
```

## 15.5 Result Serialization
The following must be supported:
- DataFrame → `head(50).to_dict(orient="records")`
- list / dict / str / int / float / bool

If the result type is complex, convert it to a string summary before returning.

---

# 16. Usage Protocol for Code Generated by the External LLM

To make implementation by the code-writing AI more stable, the project must provide a “code generation specification for the external LLM.”

The external LLM must follow the rules below:

## 16.1 Allowed Coding Style
- `import pandas as pd` is allowed
- `import numpy as np` is allowed
- `read_sql()` may be called
- DataFrame analysis may be performed
- the final result must be output through `print(...)`
- multiple `print(...)` calls are allowed, but the final output should preferably be concise and readable

## 16.2 Forbidden Content
- importing modules outside the whitelist is forbidden
- file operations are forbidden
- shell operations are forbidden
- creating a new database connection is forbidden
- writing to the database is forbidden

## 16.3 Recommended Code Template
The project should provide an example template:

```python
import pandas as pd

sales = read_sql("""
SELECT o.orderDate, od.quantityOrdered, od.priceEach, p.productName, p.productLine, c.country
FROM orders o
JOIN orderdetails od ON o.orderNumber = od.orderNumber
JOIN products p ON od.productCode = p.productCode
JOIN customers c ON o.customerNumber = c.customerNumber
WHERE o.orderDate >= '2004-01-01'
""")

sales["revenue"] = sales["quantityOrdered"] * sales["priceEach"]
summary = sales.groupby("productLine", as_index=False)["revenue"].sum()
summary = summary.sort_values("revenue", ascending=False)
print(summary.to_csv(index=False))
```

---

# 17. Recommended Advanced Natural Language Analysis Workflow

This workflow must be implemented as the key project highlight:

## Step 1
The client submits a natural language question, for example:
- “Compare the average sales of different offices/stores”
- “Analyze the revenue ranking of product lines”
- “Find high-value customers in the past year”

## Step 2
The system first calls:
- `POST /skills/observe_schema`

## Step 3
The external LLM reads the schema result and generates Python analysis code.

## Step 4
The system calls:
- `POST /skills/run_python_analysis`

## Step 5
If execution succeeds, the agent reads stdout and determines whether it is already sufficient to answer the question.

## Step 6
If execution fails or is blocked by the security policy, the agent reads the structured error, fixes the code, and continues the loop.

## Step 7
When the agent believes the analysis is complete, it calls the stop function and outputs the final answer externally.

## Step 8 (Optional Enhancement)
Write the natural language input, generated code, stdout summary, and error records into `saved_queries` or `analysis_logs`.

---

# 18. Testing Requirements

Tests must be provided.

## 18.1 observe_schema Tests
At minimum test:
- the table list can be returned
- column information can be returned
- foreign key information can be returned
- the output structure is stable

## 18.2 run_python_analysis Tests
At minimum test:
- valid pandas analysis code runs successfully
- `import os` is rejected
- `open()` is rejected
- non-SELECT SQL is rejected
- timeout code is terminated
- invalid code can return structured errors

## 18.3 Basic CRUD Tests
At minimum test:
- create succeeds
- read succeeds
- update succeeds
- delete succeeds
- correct error code is returned when the record does not exist

---

# 19. API Documentation Requirements

API documentation must be provided.

Requirements:
- Swagger / OpenAPI must be usable
- README must clearly explain how to access it
- for each endpoint, the documentation must specify:
  - parameters
  - return values
  - error codes
  - example requests and responses

Skill endpoint documentation must be included:
- `/skills/observe_schema`
- `/skills/run_python_analysis`

---

# 20. README Requirements

README must clearly explain:
- project overview
- technology stack
- directory structure
- how to start with Docker
- how to import `classicmodels.sql`
- how to access Swagger
- how to test the API
- how to call the two skills

The complete startup command must be included, for example:

```bash
docker compose up --build
```

---

# 21. Deliverables Checklist

The code-writing AI must finally produce:

## Code
- complete FastAPI project source code
- Dockerfile
- docker-compose.yml
- MySQL initialization SQL / shell scripts
- skill implementation code
- tests

## Documentation
- README.md
- API Documentation (Swagger + exportable PDF)
- architecture explanation materials usable in the technical report

## Runtime Result
The following must be achieved:
- containers can start
- database can be initialized automatically
- basic CRUD works correctly
- analytics endpoints work correctly
- `observe_schema` returns structure correctly
- `run_python_analysis` can safely execute analytical code

---

# 22. High-Grade-Oriented Requirements (Must Be Considered)

During implementation, the code-writing AI must proactively aim toward high-grade standards:

- modular code
- clear architecture
- complete documentation
- professional Docker deployment
- sufficient testing
- clear error handling
- data analysis functionality with obvious highlights
- skill design with clear boundaries and security control
- demonstrate high-level use of GenAI, rather than merely using AI as an auxiliary coding tool

In particular, the implementation must highlight:
- why MySQL uses dual accounts (read/write separation)
- why the skills are `observe_schema + run_python_analysis`
- why natural language analysis does not directly stuff large amounts of data into the LLM, but instead uses Python to execute the analysis
- why AST inspection, read-only accounts, and worker isolation are used

---

# 23. Final Must-Do Items (Short Execution Checklist)

The code-writing AI must follow this order:

1. create the FastAPI project skeleton
2. create Dockerfile and docker-compose
3. create the MySQL initialization plan
4. create the `enterprise_api` database
5. import the user’s local `classicmodels.sql`
6. create `app_rw` and `app_ro`
7. implement the basic CRUD API
8. implement the basic analytics endpoints
9. implement `observe_schema`
10. implement `run_python_analysis`
11. implement AST inspection, SQL inspection, read-only helper, and worker execution
12. implement tests
13. complete README and OpenAPI documentation
14. ensure the whole system can run via `docker compose up --build`

---

# 24. Final Statement

This project is not a normal CRUD coursework, but rather:

**an enterprise sales data API system based on FastAPI + MySQL + Docker, with skill-based natural language data analysis capability.**

The focus is:
- the basic API must be reliable
- the skills must be secure
- the natural language analysis must be demonstrable
- the architecture must be clear
- the documentation must be complete

The code-writing AI must not change the overall solution any further, and should implement directly according to this document.
