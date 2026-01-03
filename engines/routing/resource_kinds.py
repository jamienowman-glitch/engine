"""Resource kind enumeration for routing registry.

Phase 0.5 Lane 1: Small set of infrastructure resource kinds.
"""
from enum import Enum


class ResourceKind(str, Enum):
    """Enum of supported infrastructure resource kinds."""
    
    VECTOR_STORE = "vector_store"
    OBJECT_STORE = "object_store"
    TABULAR_STORE = "tabular_store"
    EVENT_STREAM = "event_stream"
    METRICS_STORE = "metrics_store"
    MEMORY_STORE = "memory_store"
    ANALYTICS_STORE = "analytics_store"


# For convenience, also export as string constants
VECTOR_STORE = ResourceKind.VECTOR_STORE.value
OBJECT_STORE = ResourceKind.OBJECT_STORE.value
TABULAR_STORE = ResourceKind.TABULAR_STORE.value
EVENT_STREAM = ResourceKind.EVENT_STREAM.value
METRICS_STORE = ResourceKind.METRICS_STORE.value
MEMORY_STORE = ResourceKind.MEMORY_STORE.value
ANALYTICS_STORE = ResourceKind.ANALYTICS_STORE.value

# All kinds as list
ALL_RESOURCE_KINDS = [
    VECTOR_STORE,
    OBJECT_STORE,
    TABULAR_STORE,
    EVENT_STREAM,
    METRICS_STORE,
    MEMORY_STORE,
    ANALYTICS_STORE,
]
