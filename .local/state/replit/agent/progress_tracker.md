[x] 1. Install the required packages
[x] 2. Restart the workflow to see if the project is working
[x] 3. Verify the project is working using the feedback tool
[x] 4. Inform user the import is completed and they can start building, mark the import as completed using the complete_project_import tool
[x] 5. Fixed crash issue (0xC0000409) related to missing dependencies and added safety checks for Git operations.
[x] 6. Verified server stability and dependency integrity.

## Feature Updates
[x] Added SQL query assertion support in backend (pythonAssertion field)
[x] Added database credential selector for SQL queries in UI
[x] Added Excel download endpoint (/api/executions/{id}/excel/{nodeId})
[x] Added Excel download buttons in execution logs panel

## Migration Complete
[x] Installed Python packages (flask, flask-cors, sqlalchemy, requests)
[x] Installed npm packages
[x] Verified workflow is running - Flask API on 5001, Vite on 5000

## MCP Tools Implementation
[x] Installed fastmcp Python SDK
[x] Created server_py/mcp_server.py with lightweight MCP tools
[x] Added Airflow tools: list_dags, trigger_dag, get_dag_run_status, pause/unpause_dag, clear_dag_run, health_check
[x] Added S3 tools: list_objects, check_object_exists, delete_object, get_object_metadata, copy_object, list_buckets, generate_presigned_url
[x] Added SFTP tools: list_directory, check_file_exists, delete_file, get_file_info, rename_file, create_directory, remove_directory, test_connection
[x] Added SQL tools: execute_query (limited rows), test_connection, get_tables, get_table_columns, count_rows, table_exists, get_primary_keys, get_indexes, get_database_info
[x] Added list_credentials helper tool
[x] Verified workflow running after MCP implementation
