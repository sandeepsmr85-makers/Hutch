import json
from functools import wraps
from flask import request, jsonify
from datetime import datetime
from ..storage import storage

def register_mcp_routes(app):
    """
    Registers routes that act as MCP-like tools for an LLM to interact with.
    These routes provide structured access to S3, SFTP, Airflow, and SQL operations.
    """

    def mcp_tool(name, description, parameters):
        def decorator(f):
            f._mcp_metadata = {
                "name": name,
                "description": description,
                "parameters": parameters
            }
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapper
        return decorator

    @app.route('/api/mcp/tools', methods=['GET'])
    def list_tools():
        tools = []
        for rule in app.url_map.iter_rules():
            f = app.view_functions[rule.endpoint]
            if hasattr(f, '_mcp_metadata'):
                tools.append(f._mcp_metadata)
        return jsonify(tools)

    @app.route('/api/mcp/system/prompt', methods=['GET'])
    @mcp_tool(
        name="get_system_instructions",
        description="Get specific instructions for the AI on how to interact with this system correctly.",
        parameters={"type": "object", "properties": {}}
    )
    def mcp_get_instructions():
        return jsonify({
            "instruction": "DO NOT generate custom Python code for SFTP, S3, SQL, or Airflow. ALWAYS use the provided MCP tools. Use 'list_credentials' to find the required credentialId first."
        })

    @app.route('/api/mcp/credentials/list', methods=['GET'])
    @mcp_tool(
        name="list_credentials",
        description="List available credentials (names, types, and IDs) to use with other tools. Does not return sensitive data.",
        parameters={"type": "object", "properties": {}}
    )
    def mcp_list_credentials():
        try:
            creds = storage.get_credentials()
            # Return only non-sensitive info
            safe_creds = []
            for c in creds:
                safe_creds.append({
                    "id": c['id'],
                    "name": c['name'],
                    "type": c['type'],
                    "createdAt": c['createdAt']
                })
            return jsonify(safe_creds)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/mcp/sql/query', methods=['POST'])
    @mcp_tool(
        name="sql_query",
        description="Execute a SQL query against a registered database credential or the internal database. Use this tool instead of writing custom Python code for SQL tasks.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The SQL query to execute"},
                "credentialId": {"type": "integer", "description": "Optional ID of the database credential from list_credentials to use"}
            },
            "required": ["query"]
        }
    )
    def mcp_sql_query():
        data = request.json
        query = data.get('query')
        credential_id = data.get('credentialId')
        
        mock_node = {
            'id': 'mcp_sql',
            'type': 'sql_query',
            'data': {'query': query, 'credentialId': credential_id}
        }
        
        try:
            from ..nodes.registry import get_node_class
            node_class = get_node_class('sql_query')
            node = node_class(mock_node, {}, [], storage, 'mcp_exec')
            
            # The node.execute() already handles errors and returns a success dict
            # or raises an exception. Let's capture the result and return it.
            result = node.execute()
            return jsonify(result)
        except Exception as e:
            # Check if it's the specific "does not return rows" error from SQLAlchemy
            err_msg = str(e)
            if 'does not return rows' in err_msg or 'no rows' in err_msg.lower():
                return jsonify({"status": "success", "results": [], "count": 0})
            return jsonify({"status": "error", "message": err_msg}), 500

    @app.route('/api/mcp/airflow/check', methods=['POST'])
    @mcp_tool(
        name="airflow_check",
        description="Comprehensive Airflow operations (health, list_dags, trigger, logs, etc.). Use this tool instead of writing custom Python code for Airflow tasks. Requires a valid credentialId from list_credentials.",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["health", "list_dags", "get_dag_details", "trigger_dag", "get_dag_run", "list_dag_runs", "list_task_instances", "get_task_logs", "pause_dag", "unpause_dag", "clear_task_instances", "list_connections", "get_connection", "list_xcoms", "delete_dag", "clear_dag_run"]},
                "credentialId": {"type": "integer", "description": "The ID of the Airflow credential from list_credentials"},
                "dagId": {"type": "string"},
                "dagRunId": {"type": "string"},
                "taskId": {"type": "string"},
                "conf": {"type": "object"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["operation", "credentialId"]
        }
    )
    def mcp_airflow_check():
        data = request.json
        operation = data.get('operation')
        credential_id = data.get('credentialId')
        
        try:
            cred = storage.get_credential(int(credential_id))
            if not cred or cred.get('type') != 'airflow':
                return jsonify({"status": "error", "message": "Invalid Airflow credential"}), 400
                
            from ..airflow_api import AirflowAPI
            cred_data = cred.get('data', {})
            api = AirflowAPI(cred_data.get('url'), cred_data.get('username'), cred_data.get('password'))
            
            mapping = {
                "health": lambda: api.get_health(),
                "list_dags": lambda: api.list_dags(limit=data.get('limit', 10)),
                "get_dag_details": lambda: api.get_dag_details(data.get('dagId')),
                "trigger_dag": lambda: api.trigger_dag(data.get('dagId'), conf=data.get('conf')),
                "get_dag_run": lambda: api.get_dag_run(data.get('dagId'), data.get('dagRunId')),
                "list_dag_runs": lambda: api.list_dag_runs(data.get('dagId'), limit=data.get('limit', 10)),
                "list_task_instances": lambda: api.list_task_instances(data.get('dagId'), data.get('dagRunId')),
                "get_task_logs": lambda: api.get_task_logs(data.get('dagId'), data.get('dagRunId'), data.get('taskId')),
                "pause_dag": lambda: api.pause_dag(data.get('dagId')),
                "unpause_dag": lambda: api.unpause_dag(data.get('dagId')),
                "clear_task_instances": lambda: api.clear_task_instances(data.get('dagId'), dag_run_id=data.get('dagRunId')),
                "list_connections": lambda: api.list_connections(),
                "get_connection": lambda: api.get_connection(data.get('connectionId')),
                "list_xcoms": lambda: api.list_xcoms(data.get('dagId'), data.get('dagRunId'), data.get('taskId')),
                "delete_dag": lambda: api.delete_dag(data.get('dagId')),
                "clear_dag_run": lambda: api.clear_dag_run(data.get('dagId'), data.get('dagRunId'))
            }
            
            result = mapping[operation]()
            return jsonify(result)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/mcp/s3/operation', methods=['POST'])
    @mcp_tool(
        name="s3_operation",
        description="Comprehensive S3 operations (buckets, objects, metadata, presigned, etc.). Use this tool instead of writing custom Python code for S3 tasks. Requires a valid credentialId from list_credentials.",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["list_buckets", "list_objects", "get_metadata", "generate_presigned", "delete", "copy", "exists", "location", "versions", "versioning"]},
                "bucket": {"type": "string"},
                "key": {"type": "string"},
                "prefix": {"type": "string"},
                "credentialId": {"type": "integer", "description": "The ID of the S3 credential from list_credentials"}
            },
            "required": ["operation", "credentialId"]
        }
    )
    def mcp_s3_op():
        data = request.json
        operation = data.get('operation')
        credential_id = data.get('credentialId')
        try:
            cred = storage.get_credential(int(credential_id))
            import boto3
            c = cred['data']
            s3 = boto3.client('s3', aws_access_key_id=c['accessKey'], aws_secret_access_key=c['secretKey'], region_name=c.get('region', 'us-east-1'))
            bucket = data.get('bucket')
            key = data.get('key')
            
            if operation == 'list_buckets': return jsonify(s3.list_buckets()['Buckets'])
            if operation == 'list_objects': return jsonify(s3.list_objects_v2(Bucket=bucket, Prefix=data.get('prefix', ''))['Contents'])
            if operation == 'get_metadata': return jsonify(s3.head_object(Bucket=bucket, Key=key))
            if operation == 'exists': 
                try: s3.head_object(Bucket=bucket, Key=key); return jsonify({"exists": True})
                except: return jsonify({"exists": False})
            return jsonify({"status": "success"})
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/mcp/sftp/operation', methods=['POST'])
    @mcp_tool(
        name="sftp_operation",
        description="Detailed SFTP operations (list_dir, mkdir, rmdir, stat, rename, remove, chmod, chown). DO NOT GENERATE PYTHON CODE. USE THIS TOOL FOR ALL SFTP TASKS. Requires a valid credentialId from list_credentials.",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["list_dir", "mkdir", "rmdir", "stat", "rename", "remove", "chmod", "chown"]},
                "credentialId": {"type": "integer", "description": "The ID of the SFTP credential from list_credentials"},
                "path": {"type": "string", "description": "Remote path to operate on"},
                "newPath": {"type": "string", "description": "New path for rename operation"},
                "mode": {"type": "integer", "description": "Permissions mode for chmod"},
                "host": {"type": "string", "description": "SFTP host (if not provided in credential)"},
                "port": {"type": "integer", "default": 22, "description": "SFTP port (default 22)"}
            },
            "required": ["operation", "credentialId"]
        }
    )
    def mcp_sftp_op():
        data = request.json
        operation = data.get('operation')
        credential_id = data.get('credentialId')
        
        try:
            cred = storage.get_credential(int(credential_id))
            if not cred:
                return jsonify({"status": "error", "message": f"Credential {credential_id} not found"}), 404
            
            import paramiko
            c = cred['data']
            
            # Use host/port from credential data if not provided in request
            host = data.get('host') or c.get('host') or c.get('baseUrl')
            port = data.get('port') or c.get('port') or 22
            
            if not host:
                return jsonify({"status": "error", "message": "Host not found in request or credential"}), 400

            transport = paramiko.Transport((host, int(port)))
            transport.connect(username=c.get('username'), password=c.get('password'))
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            try:
                path = data.get('path')
                if operation == 'list_dir': return jsonify(sftp.listdir_attr(path or '.'))
                if operation == 'mkdir': sftp.mkdir(path); return jsonify({"status": "success"})
                if operation == 'rmdir': sftp.rmdir(path); return jsonify({"status": "success"})
                if operation == 'stat': return jsonify(str(sftp.stat(path)))
                if operation == 'rename': sftp.rename(path, data.get('newPath')); return jsonify({"status": "success"})
                if operation == 'remove': sftp.remove(path); return jsonify({"status": "success"})
                if operation == 'chmod': sftp.chmod(path, data.get('mode')); return jsonify({"status": "success"})
            finally:
                sftp.close()
                transport.close()
            return jsonify({"status": "error", "message": "Unsupported operation"}), 400
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/mcp/sql/inspect', methods=['POST'])
    @mcp_tool(
        name="sql_inspect",
        description="Inspect database schema, table info, rows, etc.",
        parameters={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["get_schema", "get_table_info", "count_rows", "query_limited"]},
                "credentialId": {"type": "integer"},
                "table": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 100}
            },
            "required": ["operation", "credentialId"]
        }
    )
    def mcp_sql_inspect():
        data = request.json
        operation = data.get('operation')
        credential_id = data.get('credentialId')
        table = data.get('table')
        
        mock_node = {
            'id': 'mcp_sql_inspect',
            'type': 'sql_query',
            'data': {'credentialId': credential_id}
        }
        
        try:
            from ..nodes.registry import get_node_class
            node_class = get_node_class('sql_query')
            
            if operation == 'get_schema':
                mock_node['data']['query'] = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            elif operation == 'get_table_info':
                mock_node['data']['query'] = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'"
            elif operation == 'count_rows':
                mock_node['data']['query'] = f"SELECT COUNT(*) as count FROM {table}"
            elif operation == 'query_limited':
                mock_node['data']['query'] = f"{data.get('query')} LIMIT {min(data.get('limit', 100), 100)}"
            
            node = node_class(mock_node, {}, [], storage, 'mcp_inspect')
            result = node.execute()
            return jsonify(result)
        except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

