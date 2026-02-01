import os
import importlib
import pkgutil

class BaseNode:
    def __init__(self, node_data, execution_context, logs, storage, execution_id):
        self.node_data = node_data
        self.config = node_data.get('data', {}).get('config', {})
        self.execution_context = execution_context
        self.logs = logs
        self.storage = storage
        self.execution_id = execution_id
        self.id = node_data.get('id')

    def execute(self):
        raise NotImplementedError("Subclasses must implement execute()")

NODE_REGISTRY = {}

def register_node(node_type):
    """
    Decorator to register a node class in the global registry.
    :param node_type: Unique identifier for the node type (e.g., 'sql_query').
    """
    def decorator(cls):
        NODE_REGISTRY[node_type] = cls
        return cls
    return decorator

def discover_nodes():
    """
    Automatically discover and import all node modules in the current directory.
    This ensures decorators are executed and nodes are registered.
    """
    nodes_path = os.path.dirname(__file__)
    for _, name, _ in pkgutil.iter_modules([nodes_path]):
        if name != 'registry':
            importlib.import_module(f'.{name}', package='server_py.nodes')

def get_node_class(node_type):
    """
    Retrieve a registered node class by type identifier.
    Triggers discovery on first call.
    :param node_type: The type of node to retrieve.
    :return: The node class or None if not found.
    """
    if not NODE_REGISTRY:
        discover_nodes()
    return NODE_REGISTRY.get(node_type)
