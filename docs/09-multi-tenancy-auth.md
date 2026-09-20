# 09 — Multi-Tenancy & Auth

Multi-tenant from day one — that's what separates this from the hobby repos.

## 1. Model
- **User** authenticates. **Tenant** (workspace) owns all business data. **Membership** links them with a
  **role** (`owner|admin|member`). A user can belong to several tenants (agencies managing many clients).
- Every tenant-owned row has `tenant_id`. This is the isolation boundary.

## 2. Isolation strategy
- **Shared database, shared schema, row-level scoping by `tenant_id`** (simple, cost-efficient, fine to
  large scale). Postgres RLS can be layered later for defense in depth.
- Enforced in two places (belt & suspenders):
  1. A FastAPI dependency resolves `current_tenant` from the JWT/route and injects a tenant-scoped
     session/filter.
  2. Services re-assert `tenant_id` on reads/writes; cross-tenant access raises `TenantMismatch`.

## 3. Auth flow
```
POST /auth/signup  → create user (+ first tenant + owner membership)
POST /auth/login   → verify bcrypt hash → issue short-lived access JWT + refresh token
Authorization: Bearer <jwt>  → deps resolve user + active tenant
POST /auth/refresh → rotate
```
- Access token claims: `sub` (user id), `tid` (active tenant), `role`, `exp`.
- Switching workspace re-issues a token with a different `tid` (membership checked).

## 4. Roles & permissions
| Action | owner | admin | member |
|---|---|---|---|
| Manage billing/tenant | ✅ | ✖ | ✖ |
| Invite/remove members | ✅ | ✅ | ✖ |
| Configure agent / knowledge / numbers | ✅ | ✅ | ✖ |
| View calls / bookings / analytics | ✅ | ✅ | ✅ |

## 5. Agent/worker access
- The voice agent isn't a "user"; it resolves tenant from the **dialed number** (phone) or the **test
  room token** (browser). It uses internal service calls already scoped to that tenant.
- LiveKit tokens are minted server-side, scoped to a single room, short-lived.

## 6. Secrets & PII
- Integration secrets (Cal.com/Twilio keys, OAuth tokens) encrypted at rest; never returned by the API.
- Provider tier (free vs paid/self-host) is per-tenant, enabling privacy upgrades for sensitive clients.
  See [13](13-security-compliance.md).

## 7. Rate limiting & quotas
- Per-tenant quotas (minutes, uploads, RPM) in Redis → protects free provider tiers and controls cost.
