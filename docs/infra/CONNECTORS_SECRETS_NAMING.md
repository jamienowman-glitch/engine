# CONNECTORS & SECRETS NAMING (PLANNING)

Canonical naming for tenants, connectors, and GSM secrets. Planning-only; no code or migrations in this pass.

## Tenant ID pattern
- `tenant_id = "t_<slug>"` (lowercase, alphanumeric + hyphen/underscore).
- Examples: `t_northstar-dev`, `t_snakeboard-uk`, `t_alpha`.

## Connector ID pattern
- `connector_id = "conn.<provider>.<product>.<scope>"`
  - `provider`: cloud/vendor (vertex, bedrock, openrouter, shopify, youtube, google_ads).
  - `product`: model or service family (gemini, claude, mistral, admin, ingest).
  - `scope`: lane such as `core`, `cheap`, `sandbox`, `prod`, or a specific purpose (`reporting`, `ingest`).
  - Examples: `conn.vertex.gemini.core`, `conn.vertex.gemini.cheap`, `conn.bedrock.claude.core`, `conn.router.openrouter.core`, `conn.shopify.admin.prod`.

## GSM secret naming
- OS-paid connector secret: `conn-<provider>-<product>-<scope>-key` (e.g., `conn-vertex-gemini-core-key`).
- Per-tenant BYOK secret: `tenant-<tenant_id>-<provider>-<product>-<scope>-key` (e.g., `tenant-t_northstar-dev-vertex-gemini-core-key`).
- If a connector needs multiple secrets, append a suffix to the same base: `...-key`, `...-refresh`, `...-secret`. Keep the base consistent with `connector_id`.

## Provider/product/scope examples
- `conn.gcp.vertex.chat` → provider=`gcp`, product=`vertex`, scope=`chat`
- `conn.aws.bedrock.chat` → provider=`aws`, product=`bedrock`, scope=`chat`
- `conn.mistral.api.core` → provider=`mistral`, product=`api`, scope=`core`
- `<provider>`: cloud or vendor (gcp, aws, azure, oci, mistral, openai, etc.)
- `<product>`: service/product within that provider (vertex, bedrock, api, etc.)
- `<scope>`: narrow usage slice (chat, core, eval, billing, etc.)

## OS-paid vs BYOK (GSM only)
- OS-paid: `conn-<provider>-<product>-<scope>-key` (optional `...-secret`, `...-refresh` as needed).
- BYOK (per tenant): `tenant-<tenant_id>-<provider>-<product>-<scope>-key` (suffixes as above).
- All secrets live in GSM; raw keys never sit in env vars.

## LLM API keys follow the same pattern
- OpenAI: `conn.openai.api.core` → `conn-openai-api-core-key` (OS-paid) or `tenant-<tenant_id>-openai-api-core-key` (BYOK).
- Mistral: `conn.mistral.api.core` → `conn-mistral-api-core-key` or `tenant-<tenant_id>-mistral-api-core-key`.
- Vertex/Bedrock LLM lanes reuse the same shapes (provider=gcp/aws, product=vertex/bedrock, scope=chat/eval/etc.).

## Env vs tenant scoping
- Non-secret routing config (e.g., `TENANT_ID`, `ENV`, `REGION`, bucket names, nexus backend selector) is set via env vars.
- Sensitive values (keys/tokens, bucket names when secret-backed, nexus backend selector when secret-backed) stay in GSM following the patterns above. Example dev secrets (docs/02_REPO_PLAN.md): `northstar-dev-tenant-0-id`, `northstar-dev-raw-bucket`, `northstar-dev-datasets-bucket`, `northstar-dev-nexus-backend`.

## Implementation checklist
- For any new connector: define `connector_id`, OS-paid GSM key name(s), optional BYOK GSM key name(s) using the existing patterns, and note whether it is infra-level or tool-level.

## Storage rules
- Secret values live only in GSM. DB/Nexus store metadata only (`connector_id`, `has_byok`, `last_updated_at`, masked preview).
- Runtime readers derive GSM names from `connector_id` + tenant: OS-paid reads `conn-...-key`; BYOK reads `tenant-...-key`.

## Tasks to validate later
- Audit for any conflicting/legacy secret names; if divergence exists, document migration steps here—never silently diverge.
- Ensure runtime readers resolve these names consistently across connectors and tenants.
