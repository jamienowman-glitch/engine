# Workbench API Surface Requirements

**Standard:** JSON over HTTP.
**Auth:** Bearer Token (Propagated).

## 1. Registry: Firearms
**Prefix:** `/registry/firearms`

### List License Types
- **GET** `/license-types`
- **Response:**
  ```json
  [
    {
      "id": "firearm_123",
      "name": "Database Write Access",
      "description": "Allows writing to production DBs"
    }
  ]
  ```

### Create License Type
- **POST** `/license-types`
- **Body:** `{ "name": "...", "description": "..." }`
- **Response:** `200 OK` (Returns created object)

## 2. Registry: KPI
**Prefix:** `/registry/kpi`

### List Categories
- **GET** `/categories`
- **Response:**
  ```json
  [
    { "id": "cat_perf", "name": "Performance", "description": "System latency and throughput" }
  ]
  ```

### Create Category
- **POST** `/categories`
- **Body:** `{ "name": "..." }`
- **Response:** `200 OK`

### List Metrics (Types)
- **GET** `/types` (or `/definitions`)
- **Response:**
  ```json
  [
    { "id": "kpi_def_latency", "name": "Latency", "category_id": "cat_perf" }
  ]
  ```

## 3. Workbench: Drafts
**Prefix:** `/workbench/drafts`

### Save Draft
- **PUT** `/{tool_name}`
- **Body:** `MCPToolDefinition` (Complete JSON)
- **Response:** `200 OK`

### Load Draft
- **GET** `/{tool_name}`
- **Response:** `MCPToolDefinition`

## 4. Workbench: Publish
**Prefix:** `/workbench/publish`

### Publish Tool
- **POST** `/`
- **Body:**
  ```json
  {
    "tool_id": "...",
    "draft_version": "..." // Optional constraint
  }
  ```
- **Response:**
  ```json
  {
    "portable_package": {
      "package_id": "...",
      "version": "1.0.1",
      "download_url": "..."
    },
    "activation_overlay": {
      "overlay_id": "...",
      "version": "1.0.1"
    }
  }
  ```

## 5. Errors
All endpoints MUST return standard `error_envelope`:
```json
{
  "error": {
    "code": "resource.not_found",
    "message": "...",
    "details": {}
  }
}
```
