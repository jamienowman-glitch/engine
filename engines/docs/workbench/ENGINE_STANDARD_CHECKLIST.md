# Engine Standard Checklist

| Requirement | Details |
|---|---|
| **Identity** | Must inject `RequestContext`. No global state. |
| **Envelope** | Must return `ErrorEnvelope` on failure. |
| **GateChain** | Must invoke `GateChain` for significant/mutating ops. |
| **Persistence** | Must use `store` or `repository` pattern, no direct DB calls in route/wrapper. |
| **Config** | Must rely on `engines.config` or env vars, no hardcoded secrets. |
| **Durability** | If async/long-running, must use `EventSpine` or `Timeline` (Rail). |
