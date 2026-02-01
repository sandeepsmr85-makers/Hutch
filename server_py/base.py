from datetime import datetime
import json
import re

class BaseService:
    """
    Base class for all backend services (Airflow, S3, SFTP, etc.).
    Provides initialization logic for credentials and storage.
    """
    def __init__(self, credential_id=None, storage=None):
        """
        Initialize the service with a credential ID and storage instance.
        :param credential_id: The ID of the credential to use.
        :param storage: The storage instance to fetch credential data.
        """
        self.credential_id = credential_id
        self.storage = storage
        self.cred_data = {}
        if credential_id and storage:
            cred = storage.get_credential(int(credential_id))
            if cred:
                self.cred_data = cred.get('data', {})

class BaseNode:
    """
    Base class for all workflow nodes.
    Handles configuration, execution context, and logging.
    """
    def __init__(self, node_data, execution_context, logs, storage, execution_id):
        """
        Initialize a node with its data and execution state.
        :param node_data: Configuration and metadata for this node.
        :param execution_context: Shared state between nodes in a workflow.
        :param logs: List to collect execution logs.
        :param storage: Storage instance for data access.
        :param execution_id: Unique identifier for the current workflow run.
        """
        self.node_data = node_data
        self.config = node_data.get('data', {}).get('config', {})
        self.execution_context = execution_context
        self.logs = logs
        self.storage = storage
        self.execution_id = execution_id
        self.id = node_data.get('id')

    def run_assertions(self, result_data):
        """
        Execute custom Python assertions on the node's result data.
        Fails the node if any assertion evaluates to False.
        :param result_data: The output produced by the node's execute method.
        """
        assertion_code = self.config.get('assertion') or self.config.get('pythonAssertion')
        if not assertion_code:
            return

        self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"Running assertions: {assertion_code}"})
        
        # Prepare context for assertion
        safe_builtins = {
            'any': any, 'all': all, 'len': len, 'sum': sum, 'min': min, 'max': max, 
            'abs': abs, 'round': round, 'int': int, 'str': str, 'float': float, 
            'list': list, 'dict': dict, 'bool': bool, 'type': type, 'isinstance': isinstance,
            'datetime': datetime, 'json': json, 're': re
        }
        
        ctx = {
            'results': result_data.get('results', []),
            'count': result_data.get('count', 0),
            'data': result_data,
            'context': self.execution_context,
            'ctx': self.execution_context,
            'prev': self.execution_context
        }
        # Add results of all previous nodes to context
        ctx.update(self.execution_context)
        
        try:
            # We use eval for simple boolean expressions
            # or exec if it's more complex, but usually assertions are expressions
            result = eval(assertion_code, {"__builtins__": safe_builtins}, ctx)
            if not result:
                raise Exception(f"Assertion failed: {assertion_code}")
            self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': "Assertion passed"})
        except Exception as e:
            self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'ERROR', 'message': f"Assertion error: {str(e)}"})
            raise Exception(f"Assertion failed: {str(e)}")
