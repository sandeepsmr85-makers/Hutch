from ..base import BaseNode
from .registry import register_node
from ..services.sql_service import SQLService
from ..utils import resolve_variables, export_to_excel
from datetime import datetime

@register_node('sql_query')
class SQLQueryNode(BaseNode):
    def execute(self):
        query = resolve_variables(self.config.get('query', ''), self.execution_context)
        credential_id = self.config.get('credentialId')
        self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"Running SQL: {query}"})
        
        service = SQLService(credential_id, self.storage)
        query_results = service.execute_query(query)
        
        excel_path = export_to_excel(query_results, self.id, self.execution_id)
        if excel_path:
            self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"Query results exported to Excel: {excel_path}"})
            
        record_count = len(query_results)
        result = {
            'count': record_count,
            'excel_path': excel_path,
            'results': query_results,
            'status': 'success'
        }
        
        self.run_assertions(result)
        return result
