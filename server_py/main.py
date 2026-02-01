import os
import time
import json
from flask import Flask, send_from_directory, request, jsonify, send_file
from flask_cors import CORS
from .models import init_db
from .utils import log
from .workflows import register_workflow_routes
from .airflow_routes import register_airflow_routes
from .management import register_management_routes
from .mcp.tools import register_mcp_routes

app = Flask(__name__, static_folder='../client/dist', static_url_path='')
CORS(app)

init_db()

@app.before_request
def log_request():
    request.start_time = time.time()

@app.after_request
def log_response(response):
    if hasattr(request, 'start_time') and request.path.startswith('/api'):
        duration = int((time.time() - request.start_time) * 1000)
        log(f"{request.method} {request.path} {response.status_code} in {duration}ms")
    return response

# Register module routes
register_workflow_routes(app)
register_airflow_routes(app)
register_management_routes(app)
register_mcp_routes(app)

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "time": time.time()})

@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path=''):
    if path and os.path.exists(os.path.join(app.static_folder or '', path)):
        return send_from_directory(app.static_folder or '', path)
    if os.path.exists(os.path.join(app.static_folder or '', 'index.html')):
        return send_from_directory(app.static_folder or '', 'index.html')
    return "Frontend build not found. Please run 'npm run build' or check client/dist directory.", 404

from .storage import storage

@app.route('/api/workflows/<int:id>/generate-test', methods=['POST'])
def generate_workflow_test(id):
    workflow = storage.get_workflow(id)
    if not workflow:
        return jsonify({"error": "Workflow not found"}), 404
    
    nodes = workflow.get('nodes', [])
    safe_name = workflow.get('name', f'workflow_{id}').lower().replace(' ', '_')
    
    # Map node types to service methods for direct service-level testing
    service_map = {
        'sql_query': ('SQLService', 'execute_query', ['query']),
        'airflow_trigger': ('AirflowService', 'trigger_dag', ['dagId', 'conf']),
        's3_operation': ('S3Service', 'list_objects', ['bucket', 'prefix']),
        'sftp_operation': ('SFTPService', 'list_dir', ['path']),
        'airflow_log_check': ('AirflowService', 'get_task_logs', ['dagId', 'dagRunId', 'taskId'])
    }
    
    test_lines = [
        "import pytest",
        "from server_py.services.sql_service import SQLService",
        "from server_py.services.airflow_service import AirflowService",
        "from server_py.services.s3_service import S3Service",
        "from server_py.services.sftp_service import SFTPService",
        "from server_py.storage import storage",
        "",
        f"class Test{workflow.get('name', f'Workflow{id}').replace(' ', '')}:",
        "    def test_service_logic(self):",
        "        # Service-level test: Invokes business logic directly on service classes.",
        "        # Bypasses workflow engine, nodes, and API routing.",
        "        context = {}"
    ]
    
    # Process nodes in order to build sequential service calls
    for node in nodes:
        node_id = node.get('id')
        node_type = node.get('data', {}).get('type')
        config = node.get('data', {}).get('config', {})
        cred_id = config.get('credentialId')
        cred_id_str = str(cred_id) if cred_id is not None else "None"
        
        if node_type in service_map:
            svc_class, svc_method, params = service_map[node_type]
            
            # Build parameter string with basic variable resolution support (context['node_id'])
            param_args = []
            for p in params:
                val = config.get(p)
                if isinstance(val, str):
                    # Basic check for dynamic variable pattern {{node_id.key}}
                    if val.startswith('{{') and val.endswith('}}'):
                        var_path = val[2:-2].strip()
                        if '.' in var_path:
                            ref_id, key = var_path.split('.', 1)
                            param_args.append(f"context.get('{ref_id}', {{}}).get('{key}')")
                        else:
                            param_args.append(f"context.get('{var_path}')")
                    else:
                        param_args.append(f"'{val}'")
                else:
                    param_args.append(json.dumps(val))
            
            test_lines.extend([
                f"        # Test Step: {node.get('data', {}).get('label', node_id)}",
                f"        service_{node_id} = {svc_class}({cred_id_str}, storage)",
                f"        result_{node_id} = service_{node_id}.{svc_method}({', '.join(param_args)})",
                f"        assert result_{node_id} is not None",
                f"        context['{node_id}'] = result_{node_id}",
                ""
            ])

    test_code = '\n'.join(test_lines)
    
    file_path = f"tests/workflow_tests/test_{safe_name}.py"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(test_code)
        
    return jsonify({"status": "success", "file_path": file_path, "code": test_code})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    log(f"serving on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
