# WORK_ENG_MCP_01_LOCAL

## Summary
Successfully implemented the foundation for the Northstar MCP Gateway, adhering to the Multi-Scope and No-Allowlist principles.

## Changes
- **Scaffold**: Created `engines/mcp_gateway` with a FastAPI server (`server.py`).
- **Identity & Errors**: Wired `RequestContext` and `ErrorEnvelope` handling.
- **Inventory**: Implemented `inventory.py` to support multi-scope tool registration.
- **Schema Gen**: Added `schema_gen.py` to auto-generate JSON schemas from Pydantic models.
- **Tools**:
  - `echo`: Ping and Echo scopes.
  - `media_v2`: Read-only (list, get) scopes wrapping the MediaV2 service.
- **Endpoints**:
  - `GET /health`
  - `GET /debug/identity`
  - `POST /tools/list`
  - `POST /tools/call`

## Verification
All unit tests passed.

```bash
PYTHONPATH=. python3 -m pytest engines/mcp_gateway/tests/ -v
```

## How to Run Locally

1. **Start the Server** (Development Mode):
   You can run the gateway using uvicorn (assuming installed) or via python script if wired.
   
   ```bash
   uvicorn engines.mcp_gateway.server:app --reload --port 8000
   ```

2. **Test Health**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **List Tools** (Requires Headers):
   ```bash
   curl -X POST http://localhost:8000/tools/list \
     -H "Content-Type: application/json" \
     -H "X-Tenant-Id: t_demo" \
     -H "X-Mode: lab" \
     -H "X-Project-Id: p_local" \
     -H "X-User-Id: u_me" \
     -H "X-Surface-Id: s_cli" \
     -H "X-App-Id: a_cli"
   ```

4. **Call Tool**:
   ```bash
   curl -X POST http://localhost:8000/tools/call \
     -H "Content-Type: application/json" \
     -H "X-Tenant-Id: t_demo" \
     -H "X-Mode: lab" \
     -H "X-Project-Id: p_local" \
     -H "X-User-Id: u_me" \
     -H "X-Surface-Id: s_cli" \
     -H "X-App-Id: a_cli" \
     -d '{
       "tool_id": "echo",
       "scope_name": "echo.echo",
       "arguments": {"message": "Hello MCP"}
     }'
   ```
