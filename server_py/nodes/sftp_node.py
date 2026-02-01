from ..base import BaseNode
from .registry import register_node
from ..services.sftp_service import SFTPService
from ..utils import resolve_variables
from datetime import datetime
import io

@register_node('sftp_operation')
class SFTPNode(BaseNode):
    def execute(self):
        operation = self.config.get('operation', 'list')
        remote_path = resolve_variables(self.config.get('path', ''), self.execution_context)
        credential_id = self.config.get('credentialId')
        
        self.logs.append({'timestamp': datetime.now().isoformat(), 'level': 'INFO', 'message': f"SFTP {operation} on {remote_path}"})
        
        service = SFTPService(credential_id, self.storage)
        sftp, transport = service._get_client()
        
        if not sftp:
            return {'status': 'error', 'message': "Failed to connect to SFTP server"}
            
        try:
            if operation == 'list':
                files = sftp.listdir(remote_path or '.')
                self.execution_context[self.id] = {'files': files}
                return {'status': 'success', 'files': files}
            elif operation == 'upload':
                content = resolve_variables(self.config.get('content', ''), self.execution_context)
                sftp.putfo(io.BytesIO(content.encode()), remote_path)
                result = {'status': 'success'}
                self.run_assertions(result)
                return result
        finally:
            if sftp:
                sftp.close()
            if transport:
                transport.close()
            
        return {'status': 'error', 'message': f"Unsupported SFTP operation: {operation}"}
