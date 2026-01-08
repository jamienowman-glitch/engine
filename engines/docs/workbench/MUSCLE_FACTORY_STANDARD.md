# Muscle Factory Standard

**Goal**: Enable 1-click addition of new muscles (internal capabilities) by dropping files into `engines/muscles/`.

## Structure
Muscles have a slightly different structure to support multiple interfaces (MCP, REST, etc), but for MCP Factory:
```
engines/muscles/my_muscle/
  mcp/
    spec.yaml    # Tool definition
    impl.py      # Handler implementation
```

## `spec.yaml` Contract
Same as Connector Factory.

## `impl.py` Contract
Same as Connector Factory.
Important: Muscles often wrap internal services. `impl.py` should import from the sibling `service.py` if it exists, keeping the MCP layer thin.
