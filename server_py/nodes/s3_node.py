from ..base import BaseNode
from .registry import register_node
from ..services.s3_service import S3Service
from ..utils import resolve_variables
from datetime import datetime

@register_node('s3_operation')
class S3Node(BaseNode):
    def execute(self):
        bucket = resolve_variables(self.config.get('bucket', ''), self.execution_context)
        operation = self.config.get('operation', 'list')
        key = resolve_variables(self.config.get('key', ''), self.execution_context)
        credential_id = self.config.get('credentialId')
        
        self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"S3 {operation} on {bucket}"})
        
        service = S3Service(credential_id, self.storage)
        
        if operation == 'list':
            files = service.list_objects(bucket, self.config.get('prefix', ''))
            self.execution_context[self.id] = {'files': files}
            result = {'status': 'success', 'files': files}
            self.run_assertions(result)
            return result
        elif operation == 'upload':
            content = resolve_variables(self.config.get('content', ''), self.execution_context)
            service.put_object(bucket, key, content)
            result = {'status': 'success'}
            self.run_assertions(result)
            return result
        
        return {'status': 'error', 'message': f"Unsupported S3 operation: {operation}"}
