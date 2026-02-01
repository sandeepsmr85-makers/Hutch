import boto3
from ..base import BaseService

from .registry import register_service

@register_service('s3')
class S3Service(BaseService):
    def __init__(self, credential_id, storage):
        super().__init__(credential_id, storage)
        self.client = boto3.client(
            's3',
            aws_access_key_id=self.cred_data.get('accessKey'),
            aws_secret_access_key=self.cred_data.get('secretKey'),
            region_name=self.cred_data.get('region', 'us-east-1')
        )

    def list_objects(self, bucket, prefix=''):
        response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', [])]

    def put_object(self, bucket, key, body):
        return self.client.put_object(Bucket=bucket, Key=key, Body=body)
