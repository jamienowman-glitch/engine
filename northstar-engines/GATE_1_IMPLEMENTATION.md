# Gate 1 Mode-only RequestContext Implementation

## Changes Summary

### Files Created/Modified

#### 1. `engines/common/identity.py` (NEW)
- **RequestContext** dataclass: canonical context with required fields (tenant_id, mode, project_id, request_id)
- **Validation**: strict mode enum (saas|enterprise|lab only); tenant_id regex ^t_[a-z0-9_-]+$
- **RequestContextBuilder**: 
  - `from_headers()`: build from raw headers dict (core builder, used by tests)
  - `from_request()`: build from FastAPI Request object (HTTP integration)
  - Rejects X-Env header (fail-fast with ValueError)
  - Requires X-Mode header (must be saas|enterprise|lab)
  - Requires X-Tenant-Id and X-Project-Id headers
  - JWT overlay: tenant_id, user_id, role from JWT payload if present

#### 2. `tests/context/test_mode_headers.py` (NEW)
Comprehensive test suite covering:

**TestRequestContextValidation**:
- Valid context creation
- Missing/invalid tenant_id (format + presence)
- Missing/invalid mode (enum validation)
- Missing project_id

**TestRequestContextBuilderFromHeaders**:
- Minimal valid headers
- Case-insensitive header names
- Missing required headers (X-Mode, X-Tenant-Id, X-Project-Id)
- Invalid mode values
- Legacy env values rejected (dev, staging, prod, production, stage)
- **X-Env header rejection (case-insensitive)**
- Optional headers populated
- JWT overlay behavior
- t_system tenant allowed

**TestRequestContextBuilderFromRequest**:
- Valid FastAPI request integration
- X-Env rejection via FastAPI

**TestMinimalEndpoint**:
- Minimal endpoint using RequestContext
- Valid requests pass
- Missing mode → 400
- Invalid mode → 400
- X-Env present → 400

#### 3. Supporting Files
- `engines/__init__.py`: package marker
- `engines/common/__init__.py`: package marker
- `tests/__init__.py`: package marker
- `tests/context/__init__.py`: package marker
- `conftest.py`: pytest configuration with sys.path setup
- `pytest.ini`: pytest test discovery config
- `run_tests.py`: test runner script

## Contract Compliance

✓ **Mode-only requirement**: X-Mode header required, must be saas|enterprise|lab
✓ **Legacy env rejection**: X-Env header rejected with ValueError
✓ **Scope requirement**: tenant_id + mode + project_id always present
✓ **t_system allowed**: hardcoded tenant literal accepted
✓ **Auth integration**: JWT overlay preserves identity_repo defaults
✓ **Fail-fast**: all validation at RequestContext boundary

## Test Coverage

- 25+ test cases covering:
  - RequestContext creation and validation
  - Header parsing and case-insensitivity
  - Mode enum strictness
  - Legacy value rejection
  - **X-Env rejection (primary DoD)**
  - Optional field handling
  - JWT payload overlay
  - FastAPI request integration
  - Minimal endpoint validation

## DoD Achieved

✓ `pytest tests/context/test_mode_headers.py` passes all tests
✓ Missing mode → 400 (ValueError)
✓ Invalid mode → 400 (ValueError)
✓ X-Env present → 400 (ValueError)
✓ Valid tenant/mode/project → PASS on minimal endpoint
✓ Ready for commit
