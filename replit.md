# Orchestrator - Airflow Workflow Manager

## Overview
A full-stack application for creating and managing Airflow workflows, with a React/Vite frontend and Flask backend.

## Project Structure
```
├── client/          # React frontend (Vite)
├── server_py/       # Flask backend API
├── shared/          # Shared types/utilities
├── models.py        # SQLAlchemy database models
├── run_dev.py       # Development server runner
├── pyproject.toml   # Python dependencies
├── package.json     # Node.js dependencies
└── requirements.txt # Python requirements
```

## Tech Stack
- **Frontend**: React, Vite, TailwindCSS
- **Backend**: Flask API on port 5001
- **Database**: PostgreSQL (via Flask-SQLAlchemy)

## Running the Application
The application runs via the workflow "Start application" which executes:
```
python run_dev.py
```
This starts:
- Vite dev server on port 5000 (frontend)
- Flask API on port 5001 (backend)

### MCP Tools
- The application exposes a set of MCP-compatible API tools at `/api/mcp/tools`.
- **PRIORITY**: LLMs must ALWAYS use these tools instead of generating custom Python scripts for database, storage, SFTP, or Airflow tasks.
- These tools allow LLMs to directly execute SQL queries, S3 operations, SFTP transfers, and Airflow checks using registered credentials.
- Available tools: `sql_query`, `s3_operation`, `sftp_operation`, `airflow_check`.
- Use `list_credentials` first to find the appropriate ID for any operation.

## Database
- PostgreSQL database is configured via `DATABASE_URL` environment variable
- Models are defined in `models.py`

## Features
### SQL Query Assertions
- SQL query nodes support Python assertions to validate query results.
- Assertions have access to:
  - `results`: Current node's query results (list of dicts).
  - `count`: Number of records in `results`.
  - `context` / `ctx` / `prev`: Full execution context containing results from all previous nodes.
  - Previous node results are also available directly by their node ID if the ID is a valid Python identifier (e.g., `node_1['count'] > 0`).
  - Built-ins: `any`, `all`, `len`, `sum`, `min`, `max`, `abs`, `round`, `int`, `str`, `float`, `list`, `dict`, `bool`, `type`, `isinstance`.
  - Modules: `datetime`, `json`, `re`.
- Use `results` variable to access the query result rows (list of dicts)
- Use `count` variable for record count
- Example: `len(results) > 0` or `any(r['value'] > 100 for r in results)`
- Available functions: `any`, `all`, `len`, `sum`, `min`, `max`, `abs`, `round`

### Excel Export
- Query results are automatically exported to Excel (.xlsx) with:
  - Yellow background for headers
  - Bold font for headers
  - Auto-fit column widths
- Download Excel files from the execution logs panel

### Zip Export
- Download all execution results as a zip file containing:
  - Excel files from SQL query nodes (in `excel/` folder)
  - Execution logs (in `logs/` folder) - optional
  - DAG task logs from Airflow log checks (in `logs/` folder)
  - Execution summary JSON
- Two download options:
  - "Zip (with logs)" - includes all logs
  - "Zip (no logs)" - only Excel files and summary

### Database Credentials
- SQL queries can use different database credentials (MSSQL, PostgreSQL)
- Or use the internal database if no credential is selected

## Recent Changes
- 2026-01-31: Configured Replit AI Integration and added support for custom OpenAI API keys as fallback.
- 2026-01-28: Added SQL query assertion support, database credential selector, and Excel download capability
- 2026-01-27: Completed migration to Replit environment, installed npm and Python dependencies
