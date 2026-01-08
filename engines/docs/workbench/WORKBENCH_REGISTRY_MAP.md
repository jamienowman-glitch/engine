# Workbench Registry Map

## 1. Store Types
- **VersionedStore**: Used for drafts and history.
- **ComponentRegistry**: Used for published `PortableMCPPackage`.
- **FirearmsPolicyStore**: Used for `FirearmBinding` (Activation Overlay).

## 2. Key Schema
| Entity | Store | Key Format | content_type |
|---|---|---|---|
| Connector Draft | VersionedStore | `draft:connector:<id>` | `application/vnd.northstar.connector+yaml` |
| Published Tool | ComponentRegistry | `tool:<id>:<version>` | `application/vnd.northstar.package+json` |
| Activation Overlay | FirearmsPolicyStore | `binding:<tool_id>.<scope_name>` | `application/vnd.northstar.binding+json` |

## 3. UI Interaction
- **Read**: UI queries `VersionedStore` for drafts.
- **Publish**: UI calls `PublisherService`, which writes to `ComponentRegistry` and `FirearmsPolicyStore`.
- **Enforce**: Gateway reads `FirearmsPolicyStore` (via `FirearmsService`) to check `FirearmBinding`.
