# Multi-Role Authentication Guide

## Overview

The same Google account can have **different roles** depending on which app they're logging in from:

- **Backstage login** (admin panel) → Configured role (admin/editor/viewer)
- **Client app login** (user app) → Always `client_user` role

This allows administrators to:
1. Use the backstage admin panel with elevated permissions
2. Use the client app as a regular user
3. Keep separate sessions for each app

---

## How It Works

### 1. Client Type Detection

The backend detects which app the user is logging in from based on the **redirect_uri**:

| Redirect URI Pattern | Detected Client Type |
|---------------------|---------------------|
| Contains `5173` or `backstage` | `backstage` |
| Contains `65263` or anything else | `client_app` |

**Examples:**
```
http://localhost:5173/auth/callback     → backstage
http://localhost:65263/auth/callback    → client_app
https://backstage.yourapp.com/callback  → backstage
https://app.yourapp.com/callback        → client_app
```

---

### 2. Role Assignment Logic

#### Backstage Login (Port 5173)

**Requirements:**
- Email MUST be in `config.yaml` under `user_roles`
- If email not found → **403 Forbidden**

**Assigned:**
- Role: From configuration (e.g., `backstage_admin`)
- Scopes: From configuration (e.g., `[backstage, read_tours, write_tours]`)
- Client Type: `backstage`

**Example:**
```yaml
# config.yaml
authentication:
  user_roles:
    admin@example.com:
      role: backstage_admin
      scopes: [backstage, read_tours, write_tours]
```

When `admin@example.com` logs in from backstage:
```json
{
  "email": "admin@example.com",
  "role": "backstage_admin",
  "scopes": ["backstage", "read_tours", "write_tours"],
  "client_type": "backstage"
}
```

---

#### Client App Login (Port 65263)

**Requirements:**
- `allow_public_signup: true` in config
- No email whitelist required
- Anyone with a Google account can register

**Assigned:**
- Role: `client_user` (always, even if email is in backstage config)
- Scopes: `[client_app, read_tours, user_data]`
- Client Type: `client_app`

**Example:**
```yaml
# config.yaml
authentication:
  allow_public_signup: true
  default_role: client_user
  default_scopes: [client_app, read_tours, user_data]
```

When `admin@example.com` logs in from client app:
```json
{
  "email": "admin@example.com",
  "role": "client_user",
  "scopes": ["client_app", "read_tours", "user_data"],
  "client_type": "client_app"
}
```

**Note:** Even though `admin@example.com` is configured as `backstage_admin`, they get `client_user` role when logging in from the client app.

---

## Configuration

### Enable Client App Public Signup

```yaml
# config.yaml
authentication:
  # Allow anyone to register via client app
  allow_public_signup: true

  # Default role for client app users
  default_role: client_user
  default_scopes: [client_app, read_tours, user_data]

  # Backstage users (whitelist only)
  user_roles:
    admin@example.com:
      role: backstage_admin
      scopes: [backstage, read_tours, write_tours]

    editor@example.com:
      role: backstage_editor
      scopes: [backstage, read_tours, write_tours]
```

---

## Example Scenarios

### Scenario 1: Admin Using Both Apps

**User:** `henry@example.com`

**Config:**
```yaml
user_roles:
  henry@example.com:
    role: backstage_admin
    scopes: [backstage, read_tours, write_tours]
```

**Backstage Login** (http://localhost:5173):
```json
{
  "email": "henry@example.com",
  "role": "backstage_admin",
  "scopes": ["backstage", "read_tours", "write_tours"],
  "client_type": "backstage"
}
```
✅ Can access `/admin/users`, delete POIs, create tours

**Client App Login** (http://localhost:65263):
```json
{
  "email": "henry@example.com",
  "role": "client_user",
  "scopes": ["client_app", "read_tours", "user_data"],
  "client_type": "client_app"
}
```
✅ Can view tours, mark POIs as visited, save preferences
❌ Cannot access admin endpoints

**Result:** Two separate sessions, different roles, same Google account.

---

### Scenario 2: Regular User (Not in Config)

**User:** `john@example.com`

**Not in config** (not whitelisted for backstage)

**Backstage Login Attempt:**
```
❌ 403 Forbidden
"Not authorized for backstage access. Please contact administrator."
```

**Client App Login:**
```json
{
  "email": "john@example.com",
  "role": "client_user",
  "scopes": ["client_app", "read_tours", "user_data"],
  "client_type": "client_app"
}
```
✅ Success (if `allow_public_signup: true`)

---

### Scenario 3: Public Signup Disabled

**Config:**
```yaml
allow_public_signup: false
```

**Backstage Login:**
- Only users in `user_roles` config can login
- Others get 403 Forbidden

**Client App Login:**
```
❌ 403 Forbidden
"Client app registration is currently disabled. Please contact administrator."
```

**Use Case:** Private beta, backstage-only system

---

## Session Management

Each login creates a **separate session**:

**Backend Session Storage:**
```python
sessions = {
  "refresh-token-1": {
    "user": {
      "email": "henry@example.com",
      "role": "backstage_admin",
      "client_type": "backstage"
    }
  },
  "refresh-token-2": {
    "user": {
      "email": "henry@example.com",
      "role": "client_user",
      "client_type": "client_app"
    }
  }
}
```

**User's Browser Storage:**

*Backstage Tab (localhost:5173):*
```javascript
sessionStorage: { access_token: "jwt-admin-token" }
localStorage: { refresh_token: "refresh-token-1" }
```

*Client App Tab (localhost:65263):*
```javascript
sessionStorage: { access_token: "jwt-user-token" }
localStorage: { refresh_token: "refresh-token-2" }
```

---

## API Endpoint Behavior

### Backstage-Only Endpoints

```python
@app.get("/admin/users")
async def list_users(current_user = Depends(require_backstage_admin)):
    # Only accessible with backstage_admin role
    pass
```

**Client App User Attempt:**
```bash
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer <client-app-token>"

# Response: 403 Forbidden
# "Admin access required"
```

---

### Client App Endpoints

```python
@app.post("/my/visited/{city}/{poi_id}")
async def mark_poi_visited(
    city: str,
    poi_id: str,
    current_user: dict = Depends(require_client_app)
):
    # Only accessible with client_app scope
    pass
```

**Backstage Admin Attempt:**
```bash
curl -X POST http://localhost:8000/my/visited/paris/eiffel-tower \
  -H "Authorization: Bearer <backstage-admin-token>"

# Response: 403 Forbidden
# "Client app access required"
```

**Solution:** Admin must log in separately from client app to use client endpoints.

---

## Google OAuth Setup

### Single OAuth Client ID (Recommended)

Use **one** Google OAuth Client ID for both apps:

**Authorized JavaScript Origins:**
```
http://localhost:5173
http://localhost:8000
http://localhost:65263
```

**Authorized Redirect URIs:**
```
http://localhost:8000/auth/google/callback
http://localhost:5173/auth/callback
http://localhost:65263/auth/callback
```

**Benefits:**
- ✅ Simpler setup (one OAuth client)
- ✅ Same Google consent screen
- ✅ Backend detects app type automatically
- ✅ Same user can have different roles

---

### Alternative: Separate OAuth Clients (Not Recommended)

You could create two OAuth clients:
- One for backstage
- One for client app

**Drawbacks:**
- ❌ More complex setup
- ❌ Two consent screens
- ❌ Need to configure both in backend
- ❌ No significant benefit

**Verdict:** Use single OAuth client.

---

## Testing

### Test 1: Backstage Login (Whitelisted User)

```bash
# 1. Generate PKCE challenge
# 2. Get auth URL
curl "http://localhost:8000/auth/google/login?redirect_uri=http://localhost:5173/auth/callback&code_challenge=CHALLENGE"

# 3. Approve in Google
# 4. Exchange code for tokens
curl "http://localhost:8000/auth/google/callback?code=CODE&state=STATE&code_verifier=VERIFIER"

# Expected: backstage_admin role
```

---

### Test 2: Client App Login (Same User)

```bash
# 1. Generate new PKCE challenge
# 2. Get auth URL (different redirect_uri)
curl "http://localhost:8000/auth/google/login?redirect_uri=http://localhost:65263/auth/callback&code_challenge=CHALLENGE"

# 3. Approve in Google
# 4. Exchange code for tokens
curl "http://localhost:8000/auth/google/callback?code=CODE&state=STATE&code_verifier=VERIFIER"

# Expected: client_user role (even though email is whitelisted)
```

---

### Test 3: View Active Sessions (Admin)

```bash
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer <backstage-admin-token>"

# Response:
{
  "backstage": {
    "users": [
      {
        "email": "henry@example.com",
        "role": "backstage_admin",
        "client_type": "backstage"
      }
    ]
  },
  "client": {
    "users": [
      {
        "email": "henry@example.com",
        "role": "client_user",
        "client_type": "client_app"
      }
    ]
  }
}
```

**You'll see yourself twice!** Once as admin, once as regular user.

---

## Security Considerations

### 1. Separate Sessions = Separate Security

Even though it's the same Google account, the sessions are **completely separate**:
- Different JWT tokens
- Different refresh tokens
- Different scopes
- Cannot elevate privileges by switching tokens

### 2. Logout Only Affects Current Session

```javascript
// Logout from backstage
await logout(backstageRefreshToken)

// Client app session remains active
// User can still use client app
```

### 3. Token Expiry

Both sessions expire independently:
- Access tokens: 15 minutes
- Refresh tokens: 7 days

### 4. Scope Validation

Every API endpoint checks scopes:
```python
@app.get("/admin/users")
async def list_users(current_user = Depends(require_backstage_admin)):
    # Validates:
    # 1. Token is valid
    # 2. Role is backstage_admin
    # 3. Scope includes "backstage"
    pass
```

Client app tokens **cannot** access backstage endpoints, even if the email is whitelisted.

---

## Migration Guide

### From Single-Role to Multi-Role

**Before:**
- Users could only have ONE role
- Admins couldn't use client app without downgrading

**After:**
- Same user, multiple roles
- Separate sessions for each app

**No Migration Needed:**
- Existing sessions continue to work
- Existing `user_roles` config stays the same
- Just set `allow_public_signup: true` to enable client app

---

## FAQ

**Q: Can the same email have both backstage_admin and client_user at the same time?**

A: Yes! They log in separately from each app and get different roles.

---

**Q: Do I need two Google accounts?**

A: No. One Google account is enough.

---

**Q: How does the backend know which app the user is logging in from?**

A: From the `redirect_uri` parameter. If it contains `5173` or `backstage`, it's backstage. Otherwise, it's client app.

---

**Q: Can I add a user to both backstage and client app explicitly?**

A: Not needed. Backstage users are whitelisted in config. Client app users are auto-assigned on login (if `allow_public_signup: true`).

---

**Q: What if I want to disable client app for now?**

A: Set `allow_public_signup: false`. Only backstage logins will work.

---

**Q: Can a client app user become a backstage admin?**

A: Yes. Add their email to `user_roles` config. Next time they log in from backstage, they'll get admin role. Their client app session remains as `client_user`.

---

**Q: What happens if I remove a user from `user_roles` config?**

A: They can no longer log in to backstage (403 Forbidden). Their client app access is unaffected.

---

## Summary

✅ **Single OAuth Client ID**
✅ **Smart role assignment based on app type**
✅ **Same account, different roles**
✅ **Separate sessions**
✅ **No configuration duplication**
✅ **Secure scope enforcement**

This architecture gives you the best of both worlds:
- Admins can use both apps
- Regular users only access client app
- Clean separation of concerns
- Simple configuration
