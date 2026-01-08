# Workbench Registry Map

**Authority**: Northstar Data Plane  
**Status**: Critical infrastructure for Workbench.

## 1. Draft Store (Holding Pen)
- **Concept**: Mutable, temporary storage for work-in-progress connectors.
- **Resource Kind**: `workbench_store`
- **Table Name**: `tools` (Version = "draft")
- **Backend**: 
    - Lab: `FileSystemTabularStore` (`var/tabular_store/...`)
    - Prod: `FirestoreTabularStore` / `DynamoDB`
- **Routing**: Per-tenant, Per-env.

## 2. Component Registry (Layer 1)
- **Concept**: Immutable(ish) storage for **Portable MCP Packages**.
- **Resource Kind**: `component_registry`
- **Backend**: Blob Storage (S3/GCS) + Metadata DB.
- **Access**: Public / Shared across tenants (potentially).

## 3. Policy Store (Layer 2)
- **Concept**: Storage for **Northstar Activation Overlays** (Firearms/KPI bindings).
- **Resource Kind**: `policy_store`
- **Backend**: `TabularStore` (for fast lookup by GateChain).
- **Access**: Private (Tenant-scoped).

## 4. Firearms Registry
- **Concept**: Definitions of License Types (e.g. `commercial_banking`).
- **Resource Kind**: `firearms_registry`
- **Backend**: Config-as-Data (Git-backed) OR Tabular.

## 5. KPI Registry
- **Concept**: Definitions of KPI Categories and Core KPIs.
- **Resource Kind**: `kpi_registry`
- **Backend**: Tabular.

## 6. Config / Feature Flags
- **Concept**: System-wide defaults.
- **Resource Kind**: `config_store`
