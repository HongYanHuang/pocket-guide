# Google OAuth Authentication - Implementation Status

## ✅ Phase 1: Backend Core Components (COMPLETED)

### What's Been Implemented

#### 1. Authentication Infrastructure
- ✅ JWT token handler (`src/auth/jwt_handler.py`)
  - Access token generation (15 min expiry)
  - Token validation and decoding
  - Payload includes: email, name, picture, role, scopes

- ✅ Session manager (`src/auth/session_manager.py`)
  - In-memory session storage
  - Refresh token generation (UUID-based)
  - 7-day expiry with automatic cleanup
  - Thread-safe operations

- ✅ OAuth handler (`src/auth/oauth_handler.py`)
  - Google OAuth 2.0 with PKCE
  - Authorization URL generation
  - Code-to-token exchange
  - User info retrieval

#### 2. API Router
- ✅ Authentication endpoints (`src/api_auth.py`)
  - `GET /auth/google/login` - Initiate OAuth
  - `GET /auth/google/callback` - Handle OAuth callback
  - `POST /auth/refresh` - Refresh access token
  - `POST /auth/logout` - Invalidate session
  - `GET /auth/me` - Get current user info

#### 3. Authorization System
- ✅ FastAPI dependencies (`src/auth/dependencies.py`)
  - `get_current_user()` - Extract user from JWT
  - `require_role(role)` - Validate specific role
  - `require_scope(scope)` - Validate specific scope
  - `require_backstage_admin()` - Admin-only access
  - `require_backstage_write()` - Admin/editor access
  - `require_client_app()` - Client app access

#### 4. Configuration
- ✅ Environment variables (`.env.example`)
  - Google OAuth credentials
  - JWT secret key
  - Token expiry settings
  - CORS origins

- ✅ Config file updates (`config.yaml`)
  - Authentication section with role mapping
  - User email-to-role assignment
  - Default roles and scopes
  - Public signup toggle

#### 5. API Models
- ✅ Auth models (`src/api_models.py`)
  - `AuthTokenResponse` - Token response
  - `UserInfo` - User information
  - `RefreshTokenRequest` - Token refresh

#### 6. Server Integration
- ✅ API server updates (`src/api_server.py`)
  - Initialize auth handlers at startup
  - Dynamic CORS configuration
  - Auth router inclusion
  - Global access to jwt_handler, session_manager, oauth_handler

---

## 🔄 Phase 2: Frontend Implementation (NEXT)

### What Needs to Be Done

#### 1. Frontend Auth Infrastructure
- [ ] Token manager (`backstage/src/auth/tokenManager.js`)
  - Store access token in sessionStorage
  - Store refresh token in localStorage
  - Token retrieval and clearing

- [ ] Auth service (`backstage/src/auth/authService.js`)
  - API calls to backend auth endpoints
  - PKCE code generation (verifier + challenge)
  - Token exchange logic

- [ ] Auth composable (`backstage/src/auth/useAuth.js`)
  - Vue Composition API wrapper
  - Login/logout methods
  - Auto token refresh (every 10 min)
  - Reactive authentication state

- [ ] Centralized API client (`backstage/src/api/client.js`)
  - Axios interceptor for JWT injection
  - Auto-refresh on 401 errors
  - Request retry logic

#### 2. UI Components
- [ ] Login page (`backstage/src/views/Login.vue`)
  - "Sign in with Google" button
  - Redirect to Google OAuth
  - Loading states

- [ ] Auth callback handler (`backstage/src/views/AuthCallback.vue`)
  - Handle OAuth redirect
  - Exchange code for tokens
  - Redirect to dashboard

- [ ] User header (`backstage/src/components/UserHeader.vue`)
  - Display user avatar and name
  - Dropdown with logout option
  - Show user role

#### 3. Router Configuration
- [ ] Update `backstage/src/router/index.js`
  - Add `/login` and `/auth/callback` routes
  - Navigation guards for protected routes
  - Auto-redirect on authentication failure

- [ ] Update `backstage/src/App.vue`
  - Add UserHeader component
  - Check auth on mount
  - Handle session expiry

#### 4. Existing API Updates
- [ ] Update `backstage/src/api/metadata.js`
  - Use centralized API client
  - Remove local axios instance

- [ ] Update `backstage/src/api/tour.js`
  - Use centralized API client

- [ ] Update `backstage/src/api/comboTickets.js`
  - Use centralized API client

---

## 📝 Phase 3: User-Specific Data Endpoints (FUTURE)

### What's Planned

#### 1. Visit Tracking
- [ ] `GET /my/visited` - Get user's visited POIs
- [ ] `POST /my/visited/{city}/{poi_id}` - Mark POI as visited
- [ ] User data storage: `user_data/{user_id}/visited.json`

#### 2. Tour Management
- [ ] `GET /my/tours` - Get user's saved tours
- [ ] `POST /my/tours` - Save custom tour
- [ ] Link tours to user accounts

#### 3. Preferences
- [ ] `GET /my/preferences` - Get user preferences
- [ ] `PUT /my/preferences` - Update preferences
- [ ] Store language, theme, notification settings

---

## 🔒 Phase 4: Protected Endpoint Migration (GRADUAL)

### What's Planned

#### Week 1: Optional Auth (Logging)
- [ ] Add optional authentication to all endpoints
- [ ] Log authenticated requests (user, role, scopes)
- [ ] No blocking yet

#### Week 2: Backstage Write Protection
- [ ] Require `backstage_write` for:
  - `PUT /pois/{city}/{poi_id}/metadata`
  - `PUT /pois/{city}/{poi_id}/transcript`
  - `POST /tour/generate`
  - Combo tickets CREATE/UPDATE
- [ ] Require `backstage_admin` for:
  - `DELETE` endpoints
  - `/admin/*` endpoints

#### Week 3: Client App Integration
- [ ] Enable public signup (`allow_public_signup: true`)
- [ ] Deploy client app OAuth flow
- [ ] Require `client_app` scope for user-specific endpoints

#### Week 4: Full Enforcement
- [ ] All write operations require appropriate role
- [ ] Public reads remain open (optional read scope)
- [ ] Tighten CORS to production domains

---

## 🚀 Testing Checklist

### Backend Testing
- [x] Server starts without errors
- [ ] `/auth/google/login` returns Google URL
- [ ] OAuth callback exchanges code for tokens
- [ ] `/auth/refresh` renews access token
- [ ] `/auth/logout` invalidates session
- [ ] Protected endpoints reject unauthenticated requests
- [ ] Role-based access control works correctly

### Frontend Testing
- [ ] Login redirects to Google
- [ ] Callback handles OAuth response
- [ ] Tokens stored correctly (sessionStorage + localStorage)
- [ ] Dashboard accessible after login
- [ ] Auto-refresh works (check Network tab)
- [ ] Logout clears tokens
- [ ] Session persists across tab close/reopen

### End-to-End Flow
- [ ] Fresh login → Google → callback → dashboard
- [ ] Session persistence → close tab → reopen → auto-login
- [ ] Token expiry → API call → auto-refresh → success
- [ ] Protected endpoint → login required → redirect → login → redirect back

---

## 📦 Deployment Checklist

### Production Setup
- [ ] Set production environment variables
  - [ ] `GOOGLE_CLIENT_ID` (production credentials)
  - [ ] `GOOGLE_CLIENT_SECRET`
  - [ ] `JWT_SECRET_KEY` (unique secret)
  - [ ] `BACKEND_URL` (production API URL)
  - [ ] `FRONTEND_URL` (production frontend URL)

- [ ] Update Google OAuth settings
  - [ ] Add production origins to authorized JavaScript origins
  - [ ] Add production callback to redirect URIs

- [ ] Configure user roles
  - [ ] Add production admin emails to `config.yaml`
  - [ ] Set appropriate default roles
  - [ ] Configure public signup policy

- [ ] Security hardening
  - [ ] Enable HTTPS
  - [ ] Restrict CORS to specific origins
  - [ ] Use production-grade session storage (Redis)
  - [ ] Implement rate limiting
  - [ ] Add security headers

---

## 📚 Documentation

### Setup Guides
- [x] OAuth credentials setup (CLI_CHEATSHEET.md)
- [x] Environment configuration (.env.example)
- [ ] Frontend installation guide
- [ ] Production deployment guide

### API Documentation
- [x] Authentication endpoints (auto-generated by FastAPI)
- [ ] Role and scope reference
- [ ] Protected endpoint examples

### Developer Guides
- [ ] Adding new protected endpoints
- [ ] Custom role creation
- [ ] Testing authentication locally
- [ ] Troubleshooting auth issues

---

## 🎯 Current Status

**Branch**: `feature/google-oauth-authentication`

**Completed**: Backend authentication infrastructure (Phase 1)

**Next Steps**:
1. Implement frontend auth infrastructure
2. Create login UI and callback handler
3. Add authentication to existing API calls
4. Test end-to-end OAuth flow

**Time Estimate**:
- Frontend implementation: 4-6 hours
- Testing and debugging: 2-3 hours
- Documentation: 1-2 hours

---

## 🔑 Quick Start for Testing

### 1. Configure Backend

```bash
# Copy environment template
cp .env.example .env

# Generate JWT secret
openssl rand -hex 32

# Edit .env with your Google OAuth credentials and JWT secret
```

### 2. Configure User Role

Edit `config.yaml`:
```yaml
authentication:
  user_roles:
    your-email@gmail.com:
      role: backstage_admin
      scopes: [backstage, read_tours, write_tours]
```

### 3. Start Server

```bash
cd src
uvicorn api_server:app --reload --port 8000
```

### 4. Test Endpoints

Visit http://localhost:8000/docs to see authentication endpoints.

---

## 📞 Support

For issues or questions:
- Check `CLI_CHEATSHEET.md` for OAuth setup steps
- Review `.env.example` for required variables
- Verify `config.yaml` authentication section
- Check server logs for authentication errors

---

**Last Updated**: 2026-03-17
**Status**: Backend Complete ✅ | Frontend In Progress 🔄
