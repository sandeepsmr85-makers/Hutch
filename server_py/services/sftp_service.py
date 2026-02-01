import paramiko
from ..base import BaseService

from .registry import register_service

@register_service('sftp')
class SFTPService(BaseService):
    def __init__(self, credential_id, storage):
        super().__init__(credential_id, storage)
        self.host = self.cred_data.get('host') or self.cred_data.get('baseUrl')
        self.port = int(self.cred_data.get('port', 22))
        self.username = self.cred_data.get('username')
        self.password = self.cred_data.get('password')

    def _get_client(self):
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, password=self.password)
        return paramiko.SFTPClient.from_transport(transport), transport

    def list_dir(self, path='.'):
        sftp, transport = self._get_client()
        try:
            return sftp.listdir(path)
        finally:
            sftp.close()
            transport.close()
