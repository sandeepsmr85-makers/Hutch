from ..base import BaseNode
from .registry import register_node
import json
import requests
from datetime import datetime

@register_node('python_script')
class PythonScriptNode(BaseNode):
    def execute(self):
        script_code = self.config.get('code', '')
        self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': "Executing Python script..."})
        
        local_scope = {'context': self.execution_context, 'result': None, 'requests': requests, 'json': json}
        exec(script_code, {}, local_scope)
        
        script_result = local_scope.get('result')
        self.execution_context[self.id] = {'result': script_result}
        result = {'status': 'success', 'result': script_result}
        
        self.run_assertions(result)
        return result
