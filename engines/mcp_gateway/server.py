from __future__ import annotations

import time
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from engines.common.error_envelope import build_error_envelope, ErrorEnvelope, ErrorDetail
from engines.common.identity import RequestContext, get_request_context
from engines.mcp_gateway.inventory import get_inventory
from engines.mcp_gateway.tools import echo, media_v2
from engines.policy.service import get_policy_service

# --- Error Handling ---

async def _http_exception_handler(request: Request, exc: HTTPException):
    # Normalize existing envelopes if possible
    detail = exc.detail
    payload = None
    if isinstance(detail, dict) and "error" in detail:
       payload = detail
    
    if payload:
        return JSONResponse(content=payload, status_code=exc.status_code)
        
    envelope = build_error_envelope(
        code="http.exception",
        message=str(detail) if detail else "HTTP exception",
        status_code=exc.status_code,
    )
    return JSONResponse(content=envelope.model_dump(), status_code=exc.status_code)

async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    envelope = build_error_envelope(
        code="validation.error",
        message="Validation failed",
        status_code=400,
        details={"errors": exc.errors()},
    )
    return JSONResponse(content=envelope.model_dump(), status_code=400)

async def _generic_exception_handler(request: Request, exc: Exception):
    envelope = build_error_envelope(
        code="internal.error",
        message="Internal server error",
        status_code=500,
    )
    return JSONResponse(content=envelope.model_dump(), status_code=500)

def register_error_handlers(target_app: FastAPI) -> None:
    target_app.add_exception_handler(HTTPException, _http_exception_handler)
    target_app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    target_app.add_exception_handler(Exception, _generic_exception_handler)

# --- Models ---

class ToolCallRequest(BaseModel):
    tool_id: str
    scope_name: str
    arguments: Dict[str, Any]

# --- App Factory ---

def create_app() -> FastAPI:
    app = FastAPI(title="Northstar MCP Gateway")
    
    register_error_handlers(app)
    
    # Register/Wire tools via Dynamic Loader
    # "Inventory must be empty by default" -> load_all scans disk.
    from engines.workbench.dynamic_loader import loader
    loader.load_all()

    # --- Wire Engines Routers ---
    from engines.firearms.registry_routes import router as firearms_router
    from engines.kpi.registry_routes import router as kpi_router
    from engines.workbench.routes import router as workbench_router

    app.include_router(firearms_router)
    app.include_router(kpi_router)
    app.include_router(workbench_router)

    @app.get("/health")
    async def health_check():
        return {
            "service": "mcp_gateway",
            "version": "0.1.0",
            "time": time.time(),
            "status": "ok"
        }

    @app.get("/debug/identity")
    async def debug_identity(
        ctx: RequestContext = Depends(get_request_context)
    ):
        """Proof of life for identity wiring."""
        return {
            "tenant_id": ctx.tenant_id,
            "mode": ctx.mode,
            "user_id": ctx.user_id,
            "project_id": ctx.project_id
        }

    @app.post("/tools/list")
    async def list_tools(
        ctx: RequestContext = Depends(get_request_context)
    ):
        inventory = get_inventory()
        tools = []
        for tool in inventory.list_tools():
            t_data = {
                "id": tool.id,
                "name": tool.name,
                "summary": tool.summary,
                "scopes": []
            }
            for scope_name, scope in tool.scopes.items():
                t_data["scopes"].append({
                    "name": scope.name,
                    "description": scope.description,
                    "inputSchema": scope.input_schema,
                    "firearms_required": scope.firearms_required
                })
            tools.append(t_data)
        
        return {"tools": tools}

    @app.post("/tools/call")
    async def call_tool(
        req: ToolCallRequest,
        request: Request,
        ctx: RequestContext = Depends(get_request_context)
    ):
        inventory = get_inventory()
        scope = inventory.get_scope(req.tool_id, req.scope_name)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope {req.tool_id}.{req.scope_name} not found")
    
        # Check Policy Requirements (GateChain)
        from engines.nexus.hardening.gate_chain import get_gate_chain
        
        action_key = f"{req.tool_id}.{req.scope_name}"
        get_gate_chain().run(
            ctx, 
            action=action_key, 
            surface=ctx.surface_id, 
            subject_type="tool",
            subject_id=req.tool_id
        )

        # Validate arguments
        try:
            validated_args = scope.input_model(**req.arguments)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Argument validation failed: {str(e)}")
        
        # Execute
        try:
            result = await scope.handler(ctx, validated_args)
            return {"result": result}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # --- Exports ---
    @app.get("/exports/tools")
    async def export_tools_endpoint():
        from engines.mcp_gateway.tsv_export import export_tools_tsv
        from fastapi.responses import Response
        return Response(content=export_tools_tsv(), media_type="text/tab-separated-values")

    @app.get("/exports/scopes")
    async def export_scopes_endpoint():
        from engines.mcp_gateway.tsv_export import export_scopes_tsv
        from fastapi.responses import Response
        return Response(content=export_scopes_tsv(), media_type="text/tab-separated-values")

    @app.get("/exports/policies")
    async def export_policies_endpoint(ctx: RequestContext = Depends(get_request_context)):
        from engines.mcp_gateway.tsv_export import export_policies_tsv
        from fastapi.responses import Response
        # We need to handle potential errors if firearms repo is strict about tenants
        try:
            tsv = export_policies_tsv(ctx)
            return Response(content=tsv, media_type="text/tab-separated-values")
        except Exception as e:
            return Response(content=str(e), status_code=500)

    return app

app = create_app()
