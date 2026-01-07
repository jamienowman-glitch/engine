from typing import Type, Any, Dict
from pydantic import BaseModel

def generate_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Generate a JSON Schema compatible with MCP tool discovery from a Pydantic model.
    """
    schema = model.model_json_schema()
    
    # MCP expects 'inputSchema' to be a standard JSON schema object.
    # Pydantic's model_json_schema() output is usually what we want,
    # but we might need to clean up some Pydantic-specific fields if necessary.
    # For now, we return it as-is.
    
    # Ensure title is present if not
    if "title" not in schema:
        schema["title"] = model.__name__
        
    return schema
