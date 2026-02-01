from ..base import BaseNode
from .registry import register_node
from ..utils import resolve_variables
import requests
from datetime import datetime

@register_node('api_request')
class APINode(BaseNode):
    def execute(self):
        url = resolve_variables(self.config.get('url', ''), self.execution_context)
        method = self.config.get('method', 'GET').upper()
        headers = self.config.get('headers', {})
        body = resolve_variables(self.config.get('body', ''), self.execution_context)
        
        self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"API {method} {url}"})
        
        response = requests.request(method, url, headers=headers, data=body)
        response.raise_for_status()
        
        try:
            res_data = response.json()
        except:
            res_data = response.text
            
        self.execution_context[self.id] = {'response': res_data}
        result = {'status': 'success', 'data': res_data}
        
        self.run_assertions(result)
        return result
