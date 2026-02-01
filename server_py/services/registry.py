_service_registry = {}

def register_service(service_name):
    """
    Decorator to register a service class in the global registry.
    :param service_name: Unique identifier for the service (e.g., 'sql', 's3').
    """
    def decorator(cls):
        _service_registry[service_name] = cls
        return cls
    return decorator

def get_service_class(service_name):
    """
    Retrieve a registered service class by name.
    :param service_name: Name of the service to look up.
    :return: The service class or None if not found.
    """
    return _service_registry.get(service_name)
