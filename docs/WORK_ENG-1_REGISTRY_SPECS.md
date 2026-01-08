# Worklog: ENG-1 Registry Specs

## Endpoints implemented
- `GET /registry/specs?kind=atom|component|lens&cursor=<token>` – returns `{ specs: Spec[], next_cursor?: string, etag?: string }` with deterministic ordering, cursor validation, and canonical error envelopes.
- `GET /registry/specs/{id}` – returns the full `Spec` bundle (with schema/defaults/controls/token_surface) plus ETag/If-None-Match support.

## Payload example
```json
{
  "specs": [
    {
      "id": "atom.builder.button",
      "kind": "atom",
      "version": 1,
      "schema": { "type": "object", "properties": { "label": { "type": "string" } } },
      "defaults": { "label": "Click me" },
      "controls": { "/label": { "type": "text" } },
      "token_surface": ["/label"],
      "metadata": { "title": "Builder button" }
    }
  ],
  "next_cursor": "Mg",
  "etag": "\"<sha256-hash>\""
}
```

## Testing
- `pytest engines/registry/tests/test_registry_specs.py`

## Files touched
- `engines/registry/routes.py`
- `engines/registry/service.py`
- `engines/registry/repository.py`
- `engines/registry/tests/test_registry_specs.py`
- `docs/WORK_ENG-1_REGISTRY_SPECS.md`
