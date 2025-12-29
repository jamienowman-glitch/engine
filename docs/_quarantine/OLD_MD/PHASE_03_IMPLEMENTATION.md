# PHASE 3 IMPLEMENTATION PLAN

## Summary
Implement the "Cards" layer: a storage system for "YAML Header + Natural Language Body" documents. This involves a custom parser to split the YAML/NL sections, a `Card` model to store metadata and body, and a service to manage CRUD and versioning. API routes `POST /nexus/cards` (create) and `GET /nexus/cards/{card_id}` will be exposed.

## User Review Required
> [!IMPORTANT]
> **Card Format**: The system strictly expects `---` as the separator between YAML header and NL body. Malformed cards will be rejected.

## Proposed Changes

### `engines/nexus`
#### [NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/cards/models.py)
- `Card` model:
  - `card_id`: uuid (PK)
  - `tenant_id`: str (PK component)
  - `env`: str (PK component)
  - `version`: str (default "v1")
  - `card_type`: str
  - `header`: dict (parsed YAML)
  - `body_text`: str (raw NL part)
  - `full_text`: str (original raw input)
  - `created_at`: datetime
  - `created_by`: str
  - `metadata`: dict

#### [NEW] [parser.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/cards/parser.py)
- `parse_card(text) -> (header_dict, body_text)`
- Validates YAML syntax.
- Checks required header keys (`card_type`, `version` usually, but maybe lax for raw storage?).
- Rejects if `---` separator missing or YAML invalid.

#### [NEW] [repository.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/cards/repository.py)
- `CardRepository` protocol.
- `InMemoryCardRepository` (Phase 3 baseline).
- Methods: `create_card`, `get_card`, `list_cards`.

#### [NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/cards/service.py)
- `CardService`:
  - `create_card(ctx, text)`: Parses text, validates, creates `Card`, triggers `card_created` event.
  - `get_card(ctx, card_id)`: returns Card.

#### [NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/cards/routes.py)
- `POST /nexus/cards`: Body `{ text: "..." }`
- `GET /nexus/cards/{card_id}`

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py)
- Mount `engines.nexus.cards.routes.router`.

## Verification Plan

### Automated Tests
Create `engines/nexus/cards/tests/test_cards.py`:
- **Unit Tests**:
  - Test `parser.py` with valid/invalid inputs.
  - Test `Card` model validation.
  - Test `CardService` flow + event logging.
- **Integration Tests**:
  - `TestClient` API tests.

**Command**:
```bash
python -m pytest engines/nexus/cards/tests/test_cards.py
```

### Manual Verification
1. Run server.
2. `POST /nexus/cards` with a valid YAML+NL card.
3. Verify 200 OK and parsed response structure.
4. Verify `GET` returns the card.

### "No Prompts" Compliance
- Verify parser has no "interpretation" logic, just mechanical splitting/parsing.
- `grep` check.
