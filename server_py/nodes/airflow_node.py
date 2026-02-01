from ..base import BaseNode
from .registry import register_node
from ..services.airflow_service import AirflowService
from ..utils import resolve_variables

@register_node('airflow_trigger')
class AirflowTriggerNode(BaseNode):
    def execute(self):
        dag_id = resolve_variables(self.config.get('dagId', ''), self.execution_context)
        conf = self.config.get('conf', {})
        credential_id = self.config.get('credentialId')
        
        service = AirflowService(credential_id, self.storage)
        # Simplified trigger for now
        result = service.trigger_dag(dag_id, conf=conf)
        
        result = {
            'dagId': dag_id,
            'dagRunId': result.get('dag_run_id'),
            'status': 'success'
        }
        
        self.run_assertions(result)
        return result
