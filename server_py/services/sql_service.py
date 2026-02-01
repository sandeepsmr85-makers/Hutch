import sqlalchemy
from sqlalchemy import text
from ..base import BaseService

from .registry import register_service

@register_service('sql')
class SQLService(BaseService):
    def execute_query(self, query):
        if self.credential_id:
            cred_type = self.cred_data.get('type')
            if cred_type == 'mssql':
                conn_str = f"mssql+pymssql://{self.cred_data.get('username')}:{self.cred_data.get('password')}@{self.cred_data.get('host')}:{self.cred_data.get('port', 1433)}/{self.cred_data.get('database')}"
                engine = sqlalchemy.create_engine(conn_str)
                with engine.connect() as conn:
                    result = conn.execute(text(query))
                    return [dict(row._mapping) for row in result]
            else:
                raise Exception(f"Unsupported SQL credential type: {cred_type}")
        else:
            from ..models import engine as internal_engine
            with internal_engine.connect() as conn:
                result = conn.execute(text(query))
                return [dict(row._mapping) for row in result]
