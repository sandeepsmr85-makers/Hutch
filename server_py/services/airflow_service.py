from ..base import BaseService
from ..airflow_api import AirflowAPI

from .registry import register_service

@register_service('airflow')
class AirflowService(BaseService):
    def __init__(self, credential_id, storage):
        super().__init__(credential_id, storage)
        self.api = AirflowAPI(
            self.cred_data.get('baseUrl') or self.cred_data.get('url'),
            self.cred_data.get('username'),
            self.cred_data.get('password')
        )

    def health(self):
        return self.api.get_health()

    def list_dags(self, limit=10):
        return self.api.list_dags(limit=limit)

    def trigger_dag(self, dag_id, conf=None):
        return self.api.trigger_dag(dag_id, conf=conf)

    def get_task_logs(self, dag_id, dag_run_id, task_id):
        return self.api.get_task_logs(dag_id, dag_run_id, task_id)
