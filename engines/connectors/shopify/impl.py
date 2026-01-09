from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore
from engines.mcp_gateway.inventory import Tool, Scope

# --- Logic ---

# --- Phase 5: Dynamic Template Loading ---

import yaml
from pathlib import Path

# Cache templates
_TEMPLATES_CACHE = None

def _get_templates():
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is None:
        yaml_path = Path(__file__).parent / "templates.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                _TEMPLATES_CACHE = yaml.safe_load(f) or []
        else:
            _TEMPLATES_CACHE = []
    return _TEMPLATES_CACHE

import functools
from pydantic import create_model

async def _template_handler_wrapper(tool_name: str, ctx: RequestContext, payload: BaseModel) -> Any:
    # Unwrap payload to dict
    args = payload.dict(exclude_unset=True)
    return await handle_tool_call(ctx, tool_name, args)

def load_dynamic_tools() -> List[Tool]:
    """
    Called by Dynamic Loader to register tools based on templates.yaml
    """
    tools = []
    templates = _get_templates()
    
    for tpl in templates:
        t_name = tpl["name"]
        
        t = Tool(
            id=t_name,
            name=t_name,
            summary=tpl["description"]
        )
        
        # Create Dynamic Pydantic Model
        schema_props = tpl.get("input_schema", {}).get("properties", {})
        fields = {}
        for fname, fdef in schema_props.items():
            ftype = str
            if fdef.get("type") == "integer": ftype = int
            elif fdef.get("type") == "boolean": ftype = bool
            elif fdef.get("type") == "array": ftype = list
            fields[fname] = (Optional[ftype], None) 
            
        DynamicInput = create_model(f"{t_name}Input", **fields)
        
        # Bind handler with tool_name
        bound_handler = functools.partial(_template_handler_wrapper, t_name)
        # partial doesn't preserve __name__ which might be needed? 
        # Actually Scope expects a callable.
        # To avoid issues, let's just make it async callable.
        bound_handler.__name__ = f"handler_{t_name}"

        t.register_scope(Scope(
            name="execute",
            description=tpl["description"],
            input_model=DynamicInput,
            handler=bound_handler,
            firearms_required=True
        ))
        
        tools.append(t)
        
    return tools

async def handle_tool_call(ctx: RequestContext, tool_name: str, args: Dict[str, Any]) -> Any:

    """
    Handles tool calls by finding the matching template and executing GraphQL.
    """
    # 1. Find Template
    templates = _get_templates()
    template = next((t for t in templates if t["name"] == tool_name), None)
    
    if not template:
        raise ValueError(f"Tool {tool_name} not found.")

    # 2. Construct Variables (Transform)
    # The 'variables_transform' in YAML is a python expression string.
    # We evaluate it in a safe context where 'args' is available.
    # WARNING: eval() is dangerous. In production we'd use a safer templating engine like Jinja2
    # or a structured variable mapper. For this Lab/POC, eval is acceptable if templates are trusted.
    
    transform_code = template["variables_transform"]
    try:
        # Evaluate expression to get dict
        variables = eval(transform_code, {"args": args, "True": True, "False": False, "None": None})
    except Exception as e:
        raise ValueError(f"Failed to transform variables for {tool_name}: {e}")
        
    # 3. Get GraphQL Query
    query = template["graphql_template"]
    
    # 4. Execute via standard GraphQL handler
    # We reuse the specific shopify logic (Auth/HTTP) which lives in a helper or we inline it.
    # Since we can't easily call 'handle_graphql' (it expects GraphqlInput), let's refactor
    # the core execution logic or just instatiate GraphqlInput.
    
    # Check `_execute_graphql` implementation below
    return await _execute_graphql(ctx, query, variables)

async def _execute_graphql(ctx: RequestContext, query: str, variables: Dict[str, Any]) -> Any:
    """
    Core GraphQL execution logic (refactored from original handle_graphql)
    """
    secrets = LocalSecretStore()
    
    # 1. Get Secrets
    # Try tenant-specific first, then generic
    shop_url = secrets.get_secret(f"shopify-shop-url-{ctx.tenant_id}") or secrets.get_secret("shopify-shop-url")
    access_token = secrets.get_secret(f"shopify-access-token-{ctx.tenant_id}") or secrets.get_secret("shopify-access-token")
    
    if not shop_url or not access_token:
        # We raise a clear error so they know what to add.
        raise ValueError(
            "Missing Credentials. Please configure 'shopify-shop-url' and 'shopify-access-token' in your Secret Store."
        )

    # Clean URL
    shop_url = shop_url.replace("https://", "").replace("http://", "").rstrip("/")
    if not shop_url.endswith("myshopify.com"):
        shop_url = f"{shop_url}.myshopify.com"
        
    api_url = f"https://{shop_url}/admin/api/2024-01/graphql.json"

    # 2. Execute Request
    import httpx
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            api_url, 
            json={"query": input_data.query, "variables": input_data.variables}, 
            headers=headers
        )
        
    if resp.status_code != 200:
        raise RuntimeError(f"Shopify API Error ({resp.status_code}): {resp.text}")
        
    data = resp.json()
    if "errors" in data:
         raise RuntimeError(f"GraphQL Errors: {data['errors']}")
         
    # 3. Sanitize Output (W-15)
    from engines.security.sanitizer import get_sanitizer
    cleaned_data = get_sanitizer().sanitize(ctx, data)
    
    return cleaned_data
