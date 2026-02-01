from flask import request, jsonify
from ..storage import storage
from ..services.registry import get_service_class

def register_mcp_routes(app):
    @app.route('/api/mcp/execute', methods=['POST'])
    def mcp_execute():
        data = request.json
        service_name = data.get('service')
        operation = data.get('operation')
        credential_id = data.get('credentialId')
        params = data.get('params', {})
        
        service_class = get_service_class(service_name)
        if not service_class:
            return jsonify({"status": "error", "message": f"Service {service_name} not found"}), 404
            
        try:
            service = service_class(credential_id, storage)
            # Dynamically call the operation if it exists on the service
            if hasattr(service, operation):
                method = getattr(service, operation)
                result = method(**params)
                return jsonify({"status": "success", "data": result})
            else:
                return jsonify({"status": "error", "message": f"Operation {operation} not found on service {service_name}"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/mcp/tools', methods=['GET'])
    def list_mcp_tools():
        # This could eventually be dynamic by inspecting service classes
        return jsonify([
            {"name": "sql_query", "service": "sql", "operation": "execute_query"},
            {"name": "airflow_trigger", "service": "airflow", "operation": "trigger_dag"},
            {"name": "s3_list", "service": "s3", "operation": "list_objects"},
            {"name": "sftp_list", "service": "sftp", "operation": "list_dir"}
        ])
