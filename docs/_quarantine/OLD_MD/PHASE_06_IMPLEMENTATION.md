# PHASE 6 IMPLEMENTATION PLAN

## Summary
Implement "Settings & Control Screens" APIs. In Nexus, settings are simply **Cards** with specific `card_type`s (e.g., `surface_settings`, `app_definition`, `connector_config`). The `SettingsService` acts as a thin facade over the `CardIndexService` to retrieve these typed cards. Writes are handled via the standard `CardService` (Phase 3).

## User Review Required
> [!NOTE]
> **Settings are Cards**: We are not creating a new "Settings" storage engine. We are leveraging the Card engine. A "setting" is just a Card with `card_type=settings`.
> **Facade Pattern**: `SettingsService` is a convenience layer for fetching specific card types with minimal boilerplate.

## Proposed Changes

### `engines/nexus`
#### [NEW] `engines/nexus/settings`
- **[NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/settings/models.py)**:
  - `SettingsCard`: Inherits from/Wraps `Card` (or just type alias).
  - Common schemas for `surface_settings` (optional, for validation if needed, but likely keeping opaque).

- **[NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/settings/service.py)**:
  - `SettingsService(index_service)`:
    - `get_surface_settings(ctx)`: Queries index for `card_type=surface_settings`, returns latest.
    - `get_apps(ctx)`: Queries index for `card_type=app_definition`.
    - `get_connectors(ctx)`: Queries index for `card_type=connector_config`.

- **[NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/settings/routes.py)**:
  - `GET /nexus/settings/surface`: Returns singular surface settings card.
  - `GET /nexus/settings/apps`: Returns list of app cards.
  - `GET /nexus/settings/connectors`: Returns list of connector cards.

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py):
- Mount `engines.nexus.settings.routes.router`.

## Verification Plan

### Automated Tests
Create `engines/nexus/settings/tests/test_settings.py`:
- **Unit/Integration**:
  - Mock `CardIndexService`.
  - Verify `SettingsService` constructs correct `SearchQuery` (filters by tenant + card_type).
  - Verify route responses map to list of Cards.

**Command**:
```bash
python -m pytest engines/nexus/settings/tests/test_settings.py
```

### Manual Verification
1. Run server.
2. Create Card via `POST /nexus/cards` with `card_type: surface_settings`.
3. Call `GET /nexus/settings/surface`.
4. Verify the card is returned.
