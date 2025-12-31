# Local Development: Filesystem Mode

To run Northstar Engines locally without cloud dependencies (S3/Firestore), use the provided dev scripts. These scripts configure the environment to use local filesystem storage and dummy authentication secrets.

## Usage

1. **Start the Server**:
   ```bash
   ./scripts/dev_local_run.sh
   ```

2. **Environment Variables**:
   The script sets the following defaults (in `scripts/dev_local_env.sh`):
   - `ENVIRONMENT=local`
   - `FILESYSTEM_BACKEND=true`
   - `KNOWLEDGE_BACKEND=filesystem`
   - `ENGINES_TICKET_SECRET=dev-local-ticket-secret-0000`
   - Storage paths: `.northstar/data`, `.northstar/uploads`

## Verification

### 1. Check Status
```bash
curl http://localhost:8000/ops/status
```

### 2. Get Authentication Token
Generate a valid dev token using the provided helper script:
```bash
export TOKEN=$(python3 scripts/issue_dev_token.py)
echo $TOKEN
```

### 3. Issue a Ticket
Use the token to request a ticket. You must providing the context headers seeded by the startup script.
```bash
curl -X POST http://localhost:8000/api/auth/ticket \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Mode: saas" \
  -H "X-Tenant-Id: t_system" \
  -H "X-Project-Id: p_default" \
  -H "X-Surface-Id: s_default" \
  -H "X-App-Id: a_default" \
  -d '{}'
```

## Notes
- The `dev_local_run.sh` script automatically runs `scripts/seed_local_routing.py` on boot to populate the in-memory identity database and filesystem routing registry.
- Default seeded entities:
  - User: `dev-user-001`
  - Tenant: `t_system`
  - Project: `p_default`
  - Surface: `s_default`
  - App: `a_default`
