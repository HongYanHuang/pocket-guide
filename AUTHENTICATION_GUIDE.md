# Authentication System Guide

## Current Status

✅ **Backend (Phase 1) - COMPLETE**
- JWT token creation and validation
- Session management
- Google OAuth 2.0 integration
- Auth API endpoints
- Admin endpoint to view sessions

❌ **Frontend (Phase 2) - NOT IMPLEMENTED**
- Login page UI
- OAuth callback handler
- Token management
- User dropdown

---

## Step 1: Configure Google OAuth

### 1.1 Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing
3. Click **"Create Credentials"** → **"OAuth 2.0 Client ID"**
4. Application type: **Web application**
5. Name: `Pocket Guide Backstage`

**Authorized JavaScript origins:**
```
http://localhost:5173
http://localhost:8000
```

**Authorized redirect URIs:**
```
http://localhost:8000/auth/google/callback
```

6. Click **"Create"** and copy:
   - Client ID: `123456789-abcdefg.apps.googleusercontent.com`
   - Client Secret: `GOCSPX-your-secret-here`

### 1.2 Create .env File

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# 1. Paste your Google OAuth credentials
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here

# 2. Generate a secure JWT secret (run this command):
# openssl rand -hex 32
JWT_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# 3. Add your Google email (the one you'll login with)
AUTHORIZED_EMAILS=your-email@gmail.com

# 4. URLs (already correct for local development)
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# 5. Token settings (already correct)
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# 6. CORS (already correct)
CORS_ORIGINS=http://localhost:5173,http://localhost:8000
```

### 1.3 Configure User Roles

Edit `config.yaml` and add your email:

```yaml
authentication:
  enabled: true
  # ... (other settings)

  user_roles:
    # Replace with YOUR Google email
    your-email@gmail.com:
      role: backstage_admin
      scopes: [backstage, read_tours, write_tours]

    # Add more users if needed:
    # colleague@gmail.com:
    #   role: backstage_editor
    #   scopes: [backstage, read_tours, write_tours]
```

### 1.4 Restart Backend

```bash
# Kill existing tmux session
tmux kill-session -t pocket-guide

# Restart with new config
./start-dev-tmux.sh
```

---

## Step 2: View Active Sessions (Admin Only)

Once you've logged in (via frontend), you can view active sessions:

### API Call (curl):

```bash
# First, get your access token from frontend (after login)
ACCESS_TOKEN="your-jwt-token-here"

# Then call admin endpoint
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/admin/sessions
```

### Response Example:

```json
{
  "total_sessions": 2,
  "sessions": [
    {
      "email": "admin@gmail.com",
      "name": "John Doe",
      "role": "backstage_admin",
      "scopes": ["backstage", "read_tours", "write_tours"],
      "client_type": "backstage",
      "created_at": "2026-03-19T14:30:00",
      "expires_at": "2026-03-26T14:30:00",
      "last_accessed": "2026-03-19T15:45:00"
    }
  ]
}
```

---

## Step 3: Test Backend Auth (Without Frontend)

You can test the auth flow with curl:

### 3.1 Get Google Auth URL

```bash
curl "http://localhost:8000/auth/google/login?redirect_uri=http://localhost:5173/auth/callback&code_challenge=test123"
```

Response:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "uuid-here"
}
```

### 3.2 Manual OAuth Flow

1. Open `auth_url` in browser
2. Login with Google
3. Google redirects to: `http://localhost:8000/auth/google/callback?code=...&state=...`
4. Backend returns tokens:

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "uuid-here",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 3.3 Test Authenticated Endpoint

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/auth/me
```

Response:
```json
{
  "email": "your-email@gmail.com",
  "name": "Your Name",
  "picture": "https://lh3.googleusercontent.com/...",
  "role": "backstage_admin"
}
```

---

## Step 4: Frontend Login System (To Be Implemented)

The frontend needs these components to enable login:

### 4.1 Files to Create

```
backstage/src/
├── auth/
│   ├── authService.js      # API calls to /auth/* endpoints
│   ├── tokenManager.js     # sessionStorage/localStorage for tokens
│   └── useAuth.js          # Vue 3 composable for auth state
├── views/
│   ├── Login.vue           # Login page with "Sign in with Google" button
│   └── AuthCallback.vue    # Handles OAuth redirect
└── components/
    └── UserHeader.vue      # User avatar + logout dropdown
```

### 4.2 Frontend Login Flow

```
1. User visits backstage → Redirected to /login
2. Clicks "Sign in with Google"
3. Frontend generates PKCE code challenge
4. Call GET /auth/google/login → Get Google auth URL
5. Redirect to Google
6. User approves
7. Google redirects to /auth/callback?code=...
8. Frontend calls GET /auth/google/callback
9. Backend returns access_token + refresh_token
10. Store tokens:
    - access_token → sessionStorage (15 min)
    - refresh_token → localStorage (7 days)
11. Redirect to dashboard
```

### 4.3 API Client Setup

All API calls need to include the `Authorization` header:

```javascript
// backstage/src/api/client.js
import axios from 'axios'
import tokenManager from '../auth/tokenManager'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000
})

// Add access token to every request
apiClient.interceptors.request.use(config => {
  const token = tokenManager.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401 errors
apiClient.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = tokenManager.getRefreshToken()
      if (refreshToken) {
        const { data } = await axios.post('/auth/refresh', { refresh_token: refreshToken })
        tokenManager.setAccessToken(data.access_token)

        // Retry original request
        error.config.headers.Authorization = `Bearer ${data.access_token}`
        return apiClient(error.config)
      }
    }
    throw error
  }
)

export default apiClient
```

### 4.4 Vue Router Guards

Protect routes that require authentication:

```javascript
// backstage/src/router/index.js
import { createRouter } from 'vue-router'
import { useAuth } from '../auth/useAuth'

const router = createRouter({
  routes: [
    { path: '/login', component: Login, meta: { requiresAuth: false } },
    { path: '/', component: Dashboard, meta: { requiresAuth: true } },
    // ... other routes
  ]
})

router.beforeEach(async (to, from, next) => {
  const { isAuthenticated, checkAuth } = useAuth()

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    await checkAuth()

    if (!isAuthenticated.value) {
      next('/login')
    } else {
      next()
    }
  } else {
    next()
  }
})
```

---

## Step 5: Implementation Checklist

### Backend ✅ (Already Done)
- [x] JWT handler
- [x] Session manager
- [x] Google OAuth handler
- [x] Auth API endpoints
- [x] Admin sessions endpoint
- [x] CORS configuration
- [x] Role-based dependencies

### Frontend ❌ (To Do)
- [ ] Create `auth/` directory with services
- [ ] Create Login page
- [ ] Create OAuth callback handler
- [ ] Add token management
- [ ] Add auth composable (useAuth)
- [ ] Update API client with auth headers
- [ ] Add router guards
- [ ] Add user dropdown in header
- [ ] Test full OAuth flow

---

## Current Endpoints

### Public (No Auth Required)
- `GET /health` - Health check
- `GET /cities` - List cities
- `GET /pois/{city}/{poi_id}` - Get POI details
- `GET /tours` - List tours

### Authentication Endpoints
- `GET /auth/google/login` - Get Google OAuth URL
- `GET /auth/google/callback` - OAuth callback (exchange code for tokens)
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (invalidate refresh token)
- `GET /auth/me` - Get current user info

### Admin Only (Requires backstage_admin Role)
- `GET /admin/sessions` - View active sessions

---

## Security Notes

### Access Token (JWT)
- Stored in: `sessionStorage`
- Lifetime: 15 minutes
- Cleared when: Browser tab closes
- Contains: email, name, role, scopes

### Refresh Token (UUID)
- Stored in: `localStorage`
- Lifetime: 7 days
- Cleared when: Explicit logout or expiry
- Used to: Get new access tokens

### Why This Design?
- **sessionStorage** for access token = Tab closes, token is gone (secure)
- **localStorage** for refresh token = Survives page reload (convenient)
- Short access token lifetime = Limits damage if stolen
- Long refresh token = Less frequent logins

---

## Troubleshooting

### "Authentication not enabled"
- Check `.env` file exists with correct credentials
- Check `config.yaml` has `authentication.enabled: true`
- Restart backend: `tmux kill-session -t pocket-guide && ./start-dev-tmux.sh`

### "Not authorized" when logging in
- Check your Google email is in `config.yaml` under `user_roles`
- Check email matches exactly (case-sensitive)

### "Invalid redirect URI" from Google
- Check Google Cloud Console authorized redirect URIs
- Must include: `http://localhost:8000/auth/google/callback`

### "CORS error" from frontend
- Check CORS origins in `config.yaml` include frontend URL
- Restart backend after config changes

---

## Next Steps

**To complete the authentication system:**

1. ✅ Configure Google OAuth (Step 1)
2. ✅ Test backend auth with curl (Step 3)
3. ❌ Implement frontend login UI (Step 4)

**Want me to implement the frontend login system for you?**

I can create all the files listed in Step 4 (Login.vue, AuthCallback.vue, authService.js, etc.) so you have a complete working authentication system.

Just let me know!
