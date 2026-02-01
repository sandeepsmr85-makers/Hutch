import os
import json
import time
import base64
import requests
import re
import threading
import sqlalchemy
from sqlalchemy import text
from datetime import datetime, timedelta
from flask import request, jsonify
from .storage import storage
from .utils import log, resolve_variables, get_ai

def export_to_excel(data, node_id, execution_id):
    """
    Export query result to an HTML-based Excel file with column auto-fitting and yellow headers.
    :param data: List of dictionaries representing the query result rows.
    :param node_id: ID of the node that produced the data.
    :param execution_id: ID of the current workflow execution.
    :return: Path to the generated Excel file or None on failure.
    """
    try:
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
            
        file_path = f"/tmp/query_result_{execution_id}_{node_id}.xlsx"
        headers = list(data[0].keys())
        
        # Calculate approximate column widths based on headers and data
        col_widths = {h: len(str(h)) for h in headers}
        for row in data:
            for h in headers:
                val_len = len(str(row.get(h, '')))
                if val_len > col_widths[h]:
                    col_widths[h] = val_len

        # Generate HTML table with basic Excel-compatible styling
        html = [
            '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">',
            '<head><meta http-equiv="content-type" content="application/vnd.ms-excel; charset=UTF-8">',
            '<style>',
            'table { border-collapse: collapse; }',
            'th { background-color: #FFFF00; border: 0.5pt solid black; font-weight: bold; }',
            'td { border: 0.5pt solid black; white-space: nowrap; }',
            '</style>',
            '</head><body><table>'
        ]
        
        # Set column widths using <col> tags
        for h in headers:
            width = (col_widths[h] + 2) * 7
            html.append(f'<col width="{width}">')
            
        # Write headers
        html.append('<tr>')
        for h in headers:
            html.append(f'<th>{h}</th>')
        html.append('</tr>')
        
        # Write data
        for row in data:
            html.append('<tr>')
            for h in headers:
                val = str(row.get(h, ''))
                html.append(f'<td>{val}</td>')
            html.append('</tr>')
            
        html.append('</table></body></html>')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))
            
        return file_path
    except Exception as e:
        log(f"Export failed: {e}")
        return None

def execute_workflow_async(execution_id, workflow_id):
    """
    Main asynchronous execution loop for a workflow.
    Handles node traversal, result propagation, and status updates.
    :param execution_id: ID of the execution record to update.
    :param workflow_id: ID of the workflow to run.
    """
    workflow = storage.get_workflow(workflow_id)
    if not workflow:
        return
    
    logs = []
    results = {}
    nodes = workflow.get('nodes', [])
    edges = workflow.get('edges', [])
    
    storage.update_execution(execution_id, 'running', logs)
    
    execution_context = {}
    
    def find_next_nodes(current_node_id, handle=None):
        return [
            node for edge in edges
            if edge.get('source') == current_node_id and (not handle or edge.get('sourceHandle') == handle)
            for node in nodes if node.get('id') == edge.get('target')
        ]
    
    current_nodes = [n for n in nodes if not any(e.get('target') == n.get('id') for e in edges)]
    visited = set()
    assertion_failed = False
    
    while current_nodes and not assertion_failed:
        next_batch = []
        for node in current_nodes:
            node_id = node.get('id')
            if node_id in visited: continue
            visited.add(node_id)
            
            time.sleep(1)
            node_data = node.get('data', {})
            node_type = node_data.get('type')
            
            logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"Executing node {node_data.get('label')} ({node_type})..."})
            results[node_id] = {'status': 'running'}
            storage.update_execution(execution_id, 'running', logs, results)
            
            output_handle = 'output'
            current_node_result = {'status': 'success'}
            try:
                from .nodes.registry import get_node_class
                node_class = get_node_class(node_type)
                
                if node_class:
                    node_instance = node_class(node, execution_context, logs, storage, execution_id)
                    current_node_result = node_instance.execute()
                else:
                    raise Exception(f"Unsupported node type: {node_type}")
                
                results[node_id] = current_node_result
                storage.update_execution(execution_id, 'running', logs, results)
                
                if current_node_result.get('status') == 'failed':
                    assertion_failed = True
                else:
                    next_nodes = find_next_nodes(node_id, output_handle)
                    for next_node in next_nodes:
                        if next_node not in next_batch:
                            next_batch.append(next_node)

            except Exception as e:
                log(f"Node execution failed: {e}")
                current_node_result = {'status': 'failed', 'error': str(e)}
                results[node_id] = current_node_result
                storage.update_execution(execution_id, 'failed', logs, results)
                assertion_failed = True

        current_nodes = next_batch

    if not assertion_failed:
        logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': 'Workflow completed successfully'})
        storage.update_execution(execution_id, 'completed', logs, results)
    else:
        logs.append({'timestamp': datetime.now().isoformat(), 'level': 'ERROR', 'message': 'Workflow failed'})
        storage.update_execution(execution_id, 'failed', logs, results)

def register_workflow_routes(app):
    """
    Register all HTTP routes related to workflow management and execution.
    :param app: The Flask application instance.
    """
    @app.route('/api/workflows', methods=['GET'])
    def list_workflows():
        return jsonify(storage.get_workflows())

    @app.route('/api/workflows', methods=['POST'])
    def create_workflow():
        workflow = request.json
        return jsonify(storage.create_workflow(workflow))

    @app.route('/api/workflows/<int:workflow_id>', methods=['GET'])
    def get_workflow(workflow_id):
        return jsonify(storage.get_workflow(workflow_id))

    @app.route('/api/workflows/<int:workflow_id>', methods=['PUT'])
    def update_workflow(workflow_id):
        workflow = request.json
        return jsonify(storage.update_workflow(workflow_id, workflow))

    @app.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
    def delete_workflow(workflow_id):
        storage.delete_workflow(workflow_id)
        return jsonify({'status': 'success'})

    @app.route('/api/workflows/<int:workflow_id>/execute', methods=['POST'])
    def execute_workflow(workflow_id):
        execution = storage.create_execution(workflow_id)
        execution_id = execution['id']
        
        thread = threading.Thread(target=execute_workflow_async, args=(execution_id, workflow_id))
        thread.start()
        
        return jsonify(execution)
