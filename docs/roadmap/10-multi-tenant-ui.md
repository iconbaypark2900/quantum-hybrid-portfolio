# 10 — Multi-Tenant Credential Management UI

**Priority:** Medium  
**Status:** Partially implicit — tenant logic exists in backend (`services/auth.py`, `services/tenant_integrations.py`) but is invisible in the frontend; the UI has no way to manage tenants or assign credentials  
**Area:** Frontend `web/src/app/(ledger)/settings/`; Backend `api/app.py`

---

## Problem

The backend supports multi-tenancy: IBM Quantum tokens are stored per `tenant_id` in the SQLite DB, and the `X-Tenant-Id` header controls which tenant's credentials are used. However:

- The frontend settings page only shows session state (objective, tickers) and two env vars
- There is no UI to list tenants, switch active tenant, or enter IBM/Braket credentials per tenant
- The active tenant is determined by `ql_active_tenant` in `localStorage` — there is no UI to set this
- Credentials must currently be entered via `POST /api/config/ibm-quantum/` directly (e.g., via curl or Postman)
- Tenant isolation is invisible to users — it is impossible to tell which tenant namespace is active

For institutional use (multiple teams or clients sharing one deployment), this gap means:
- Onboarding a new client requires manual API calls
- Users cannot verify which IBM token is active
- Credential rotation is not self-service

---

## Scope

**In scope:**
- Settings page: "Integrations" panel to enter and verify IBM Quantum token (and optionally Braket)
- Settings page: display the active tenant ID and allow switching via a dropdown (if multiple tenants exist)
- `POST /api/config/ibm-quantum/` — already exists; confirm it is called from the new UI
- `POST /api/config/ibm-quantum/verify` — already exists; wire a "Test Connection" button to it
- Admin-only: tenant list, create tenant, delete tenant (gated by admin API key role)

**Out of scope:**
- Full identity management / SSO (separate auth feature)
- Per-user API key generation (parking lot)
- Billing per tenant

---

## Affected Files

| File | Change |
|------|--------|
| `web/src/app/(ledger)/settings/page.tsx` | Add Integrations panel and Tenant panel |
| `web/src/lib/api.ts` | Add `saveIbmToken(token, instance?)`, `verifyIbmToken()`, `getActiveTenant()`, `setActiveTenant(id)` |
| `api/app.py` | Verify `GET /api/config/tenant` exists (list tenant IDs for admin) |
| `services/tenant_integrations.py` | Confirm `get_tenant_ids()` method available for admin listing |

---

## UI Additions to Settings Page

### 1. IBM Quantum Integration Panel

```
[IBM Quantum Integration]
Token:   [•••••••••••••••••••] [Clear]   Status: ✅ Connected
Instance CRN (optional): [________________]
[Save Token]  [Test Connection]
```

- "Save Token" calls `POST /api/config/ibm-quantum/` with `{token, instance}`
- "Test Connection" calls `POST /api/config/ibm-quantum/verify` and shows ✅ or ❌
- Token display is masked (show only last 6 chars if saved)
- Shows last verified timestamp

### 2. Active Tenant Panel

```
[Active Tenant]
Current tenant: default  [Change ▾]
  ├── default   (active)
  ├── client-alpha
  └── client-beta
[+ Create new tenant]
```

- Reads `ql_active_tenant` from `localStorage`
- Dropdown lists tenants from `GET /api/config/tenants` (admin-gated, shows only own tenant for non-admins)
- Selecting a tenant updates `localStorage` and the `X-Tenant-Id` header used by `web/src/lib/api.ts`
- "Create new tenant" shows an input field → calls `POST /api/config/tenants`

### 3. Braket / AWS Integration Panel (optional section)

```
[AWS Braket / D-Wave Integration]
Status: ⚠️ Not configured (mock mode active)
[Configure via environment variables — see docs]
[Run Smoke Test]
```

- "Run Smoke Test" calls `POST /api/config/braket/smoke-test`
- Shows last smoke test result and timestamp

---

## Implementation Plan

1. **Add API calls to `web/src/lib/api.ts`**:
   ```typescript
   export async function saveIbmToken(token: string, instance?: string): Promise<void>
   export async function verifyIbmToken(): Promise<{ ok: boolean; backend?: string; error?: string }>
   export async function getActiveTenant(): Promise<string>
   export async function listTenants(): Promise<string[]>  // admin only
   export async function createTenant(id: string): Promise<void>  // admin only
   export async function runBraketSmokeTest(): Promise<{ ok: boolean; result?: unknown }>
   ```

2. **Update `web/src/app/(ledger)/settings/page.tsx`** — add three new panels below the existing session panel:
   - IBM Quantum Integration
   - Active Tenant
   - Braket Smoke Test

3. **State management** — use local React state (no global store needed for settings):
   ```typescript
   const [ibmToken, setIbmToken] = useState('');
   const [ibmVerifyStatus, setIbmVerifyStatus] = useState<'idle'|'ok'|'error'>('idle');
   const [activeTenant, setActiveTenant] = useState(() => localStorage.getItem('ql_active_tenant') ?? 'default');
   ```

4. **Confirm `GET /api/config/tenants` exists** in `api/app.py`. If not, add it:
   ```python
   @app.route('/api/config/tenants', methods=['GET'])
   @require_api_key
   def list_tenants():
       # admin role required; for non-admin, return only own tenant
       ...
   ```

5. **Wire `X-Tenant-Id` in `web/src/lib/api.ts`** — the header should be read from `localStorage` on every request:
   ```typescript
   const tenantId = localStorage.getItem('ql_active_tenant') ?? 'default';
   headers['X-Tenant-Id'] = tenantId;
   ```

6. **Write tests**:
   - `test_settings_ibm_token_save` — Playwright or unit: filling token and clicking Save calls the correct API
   - `test_settings_verify_shows_status` — after Test Connection, status badge updates
   - `test_tenant_switch_updates_header` — switching tenant updates `X-Tenant-Id` on subsequent API calls

---

## Acceptance Criteria

- [ ] Settings page has an IBM Quantum Integration panel with Save Token and Test Connection
- [ ] "Test Connection" shows a success or failure status without page reload
- [ ] Active tenant is visible and switchable in the Settings UI
- [ ] `X-Tenant-Id` header in all API calls reflects the active tenant from `localStorage`
- [ ] Braket smoke test can be triggered from Settings and shows last result
- [ ] All three new tests pass

---

## Parking Lot

- Per-user API key generation UI (create, list, revoke keys)
- Role-based access control UI (admin / analyst / read-only)
- Tenant usage dashboard (API calls per tenant, quota, cost)
- SAML / OIDC SSO integration
