# Orchestrator - Airflow Workflow Manager

## Project Overview
Orchestrator is a full-stack platform for creating, managing, and executing complex data workflows. It provides a drag-and-drop interface for building DAGs (Directed Acyclic Graphs) that integrate with services like Airflow, SQL databases, S3, and SFTP.

## Architecture
The project follows a modular, plugin-based architecture designed for extensibility.

### Backend (Python/Flask)
- **Service Layer**: (`server_py/services/`) Standardized interfaces for external integrations.
- **Node System**: (`server_py/nodes/`) Modular execution logic for workflow steps.
- **Workflow Engine**: (`server_py/workflows.py`) Async execution loop that handles node transitions and context.
- **MCP Layer**: (`server_py/mcp/`) Secure tool execution for AI agents.

### Frontend (React/Vite)
- **Flow Editor**: Interactive canvas for workflow design.
- **Management Console**: Monitor executions and manage credentials.

## Setup Instructions
1. **Environment**: Managed via Nix.
2. **Database**: Automatic PostgreSQL setup via `DATABASE_URL`.
3. **Execution**: Run via the "Start application" workflow (`python run_dev.py`).
4. **Ports**: Frontend on 5000, Backend on 5001.

## Onboarding a New Service
To add a new integration (e.g., Slack):
1. **Create Service**: Add `server_py/services/slack_service.py`.
   ```python
   from .registry import register_service
   from ..base import BaseService

   @register_service('slack')
   class SlackService(BaseService):
       def send_message(self, channel, text):
           # Implementation
           pass
   ```
2. **Create Node**: Add `server_py/nodes/slack_node.py`.
   ```python
   from .registry import register_node
   from ..base import BaseNode

   @register_node('slack_send')
   class SlackNode(BaseNode):
       def execute(self):
           # Logic to call service
           pass
   ```

## Creating MCP Tools
MCP tools are automatically supported via the universal execution endpoint:
- **Endpoint**: `/api/mcp/execute` (POST)
- **Payload**:
  ```json
  {
    "service": "slack",
    "operation": "send_message",
    "credentialId": 123,
    "params": { "channel": "#alerts", "text": "Hello" }
  }
  ```
Any method added to a registered service is immediately available as an MCP operation.
