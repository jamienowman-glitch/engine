# CONTRACT B1: MCP Tool + Scope Contract (Portable)

This document defines the **Canonical MCP Tool Contract** as used by the Connector Workbench.
This contract is **PORTABLE**: it does not contain Northstar-specific policy (firearms, budget, internal routing). It can be published to npm or used by external MCP clients.

## 1. The Connector Definition (Spec)

Stored in Registry as `kind=component`, `metadata.spec_class="mcp_connector"`.

```json
{
  "id": "github-connector",
  "version": "1.2.0",
  "description": "GitHub API connector for managing repositories and issues.",
  "author": "Northstar Platform",
  "license": "MIT",
  "homepage": "https://github.com/...",
  "icon": "https://...",
  "capabilities": {
    "tools": true,
    "resources": true,
    "prompts": false
  },
  "scopes": [
    {
      "name": "read_public",
      "description": "Read public repositories and issues only."
    },
    {
      "name": "admin_write",
      "description": "Create repositories, push code, and manage secrets."
    }
  ],
  "env_vars": [
    {
      "name": "GITHUB_TOKEN",
      "required": true,
      "description": "Personal Access Token"
    }
  ]
}
```

## 2. The Tool Definition (Per-Tool Scope)

Each tool exposed by the connector must define which "Scope" it belongs to.
**CRITICAL:** A tool cannot exist without a scope.

```json
{
  "name": "create_issue",
  "description": "Creates a new issue in a repository.",
  "input_schema": { ... },
  "required_scope": "admin_write"
}
```

## 3. Packaging Metadata

When publishing to `npm` or an external registry, the workbench uses this metadata:

*   **Package Name:** `@northstar/mcp-connector-{id}`
*   **Entrypoint:** `dist/index.js` (for Node) or `main.py` (for Python)
*   **Readme:** Auto-generated from Description + Scopes + Tools list.

## 4. No Allowlists

*   **Anti-Pattern:** "Allowed Users: [alice, bob]" inside the connector.
*   **Rule:** The connector checks **valid credentials** (e.g., GitHub Token) but does **not** check internal policy (Firearms, Northstar permissions).
*   **Reasoning:** The connector is just a driver. The *Platform* wraps it with policy.
