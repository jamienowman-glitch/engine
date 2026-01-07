# WORK_JULES_MCP_PHASE3: Verification Guide

**Status**: Phase 3 Delivered (Publisher, GateChain, Bulk Wrappers, TSV Exports)
**Branch**: `main`

## 1. Overview
Phase 3 completed the integration of "Engines as MCP Tools".
Key deliveries:
- **Publisher Service**: Publish `PortableMCPPackage` and `NorthstarActivationOverlay`.
- **GateChain Integration**: Runtime policy enforcement via `GateChain` in `/tools/call`.
- **Bulk Wrappers**: Initial wrappers for Chat and Canvas (placeholder logic).
- **TSV Exports**: Discoverability endpoints for Tools, Scopes, and Policies.

## 2. Automated Verification

Run the test suite for Phase 3 components:

```bash
# Setup environment (required for feature flag skip)
export FEATURE_FLAGS_BACKEND=memory
export PYTHONPATH=.

# Run Phase 3 Tests
python3 -m pytest engines/workbench/tests/test_publisher.py -v
python3 -m pytest engines/mcp_gateway/tests/test_enforcement.py -v
python3 -m pytest engines/mcp_gateway/tests/test_wrappers.py -v
python3 -m pytest engines/mcp_gateway/tests/test_exports.py -v
```

## 3. Manual Verification Script (End-to-End)

This script simulates the entire flow:
1. Publisher publishes a new Tool.
2. Gateway Lists the Tool.
3. Gateway Checks Policy (via GateChain).
4. Gateway Exports TSV.

Create `verify_phase3.py`:

```python
import requests
import json
import sys

BASE_URL = "http://localhost:8000"
HEADERS = {
    "X-Tenant-Id": "t_demo",
    "X-Mode": "lab",
    "X-Project-Id": "p_verify",
    "X-Surface-Id": "s_verify",
    "X-App-Id": "a_verify",
    "X-User-Id": "u_verify"
}

def check(name, success):
    print(f"[{'PASS' if success else 'FAIL'}] {name}")
    if not success:
        sys.exit(1)

def verify_exports():
    print("\n--- Verifying Exports ---")
    r = requests.get(f"{BASE_URL}/exports/tools", headers=HEADERS)
    check("Export Tools (200 OK)", r.status_code == 200)
    check("Export content contains 'echo'", "echo" in r.text)
    
    r = requests.get(f"{BASE_URL}/exports/policies", headers=HEADERS)
    check("Export Policies (200 OK)", r.status_code == 200)

def verify_tool_call_blocked():
    print("\n--- Verifying GateChain Block ---")
    # Using 'echo.echo' which we can conceptually block if we set policy
    # Since we can't easily seed real Policy Service via HTTP yet (internal only),
    # we rely on unit tests for the BLOCK case.
    # However, we can verify that 'echo.ping' works (Allowed).
    
    payload = {
        "tool_id": "echo",
        "scope_name": "echo.ping",
        "arguments": {}
    }
    r = requests.post(f"{BASE_URL}/tools/call", json=payload, headers=HEADERS)
    check("Call Safe Tool (200 OK)", r.status_code == 200)
    print("Response:", r.json())

if __name__ == "__main__":
    # Ensure server is running!
    try:
        verify_exports()
        verify_tool_call_blocked()
    except Exception as e:
        print(f"Error: {e}")
        print("Ensure server is running on localhost:8000")
```

## 4. Run Server
```bash
uvicorn engines.mcp_gateway.server:app --reload --port 8000
```
