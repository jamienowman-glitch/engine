# Connector Loading Standard

**One Folder Rule**: Connectors live ONLY in `engines/connectors/<connector_id>/`.

## 1. Directory Structure
```
engines/connectors/
  shopify/
    spec.yaml
    impl.py
  salesforce/
    spec.yaml
    impl.py
```

## 2. Loader Behavior
- **Registry Driven**: The `LoaderService` only loads connectors if their ID is present in the `ENABLED_CONNECTORS` environment variable (comma-separated) OR if explicitly registered in the `ComponentRegistry`.
- **Empty by Default**: If no connectors are enabled, the inventory remains empty.
- **No Side Effects**: Importing the loader module does NOT import connector modules. Execution logic imports on demand or during the explicit `load_all()` phase.

## 3. Scope Declaration
Scopes are defined in `spec.yaml`.
```yaml
id: "shopify"
scopes:
  - name: "get_orders"
    handler: "get_orders_handler"
```

## 4. Execution Flow
- Client calls `POST /tools/call` with `tool_id="shopify"`, `scope_name="get_orders"`.
- Gateway looks up tool in Inventory.
- Gateway calls `GateChain.run()` to enforce policy.
- Gateway invokes `handler(ctx, args)`.

## 5. Restrictions
- Agents MUST NOT edit files outside `engines/connectors/<id>/` when working on a connector.
- Agents MUST NOT add hardcoded imports to `server.py` or `inventory.py`.
