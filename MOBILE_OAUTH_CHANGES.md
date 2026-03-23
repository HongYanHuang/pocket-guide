# Mobile OAuth Support Implementation

## Client Request Analysis ✅

**iOS Client ID:** `498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com`
**Mobile Redirect URI:** `pocketguide://auth/callback`

## What Needs to Change

### Current Situation:
- ✅ Backend accepts custom redirect URIs (already works)
- ❌ Backend only knows about ONE client ID (web)
- ❌ Token exchange uses web client credentials for all requests
- ❌ iOS client has different client ID and NO client secret

### Required Changes:

1. **Config Structure** - Support multiple OAuth clients
2. **OAuth Handler** - Support iOS client (no client_secret)
3. **Client Detection** - Auto-detect iOS vs web from redirect URI
4. **Token Exchange** - Use correct client credentials
5. **Environment Variables** - Add iOS client ID

## Implementation Plan

### 1. Update Config (config.yaml)
```yaml
authentication:
  google_oauth:
    # Web client (existing)
    web:
      client_id: "${GOOGLE_WEB_CLIENT_ID}"
      client_secret: "${GOOGLE_WEB_CLIENT_SECRET}"

    # iOS client (new)
    ios:
      client_id: "${GOOGLE_IOS_CLIENT_ID}"
      # No client_secret for native iOS apps
```

### 2. Update Environment Variables (.env)
```bash
# Web OAuth Client
GOOGLE_WEB_CLIENT_ID=your-web-client-id
GOOGLE_WEB_CLIENT_SECRET=your-web-client-secret

# iOS OAuth Client
GOOGLE_IOS_CLIENT_ID=498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com
```

### 3. Create Multi-Client OAuth Handler
- Accept multiple client configurations
- Auto-detect client type from redirect URI
- Support iOS (no client_secret)

### 4. Update API Endpoints
- `/auth/client/google/login` - Detect client type, store in state
- `/auth/client/google/callback` - Use correct client for token exchange

## Detection Logic

**Auto-detect client type from redirect_uri:**
```python
def detect_client_type(redirect_uri: str) -> str:
    if redirect_uri.startswith("pocketguide://"):
        return "ios"
    else:
        return "web"
```

## Backward Compatibility

- ✅ Existing web login continues to work
- ✅ No breaking changes to current flow
- ✅ Config supports old format with fallback

## Security Notes

**Why iOS has no client_secret:**
- Native mobile apps cannot securely store secrets
- PKCE (code_challenge/code_verifier) provides security instead
- Google OAuth for iOS doesn't require client_secret
- This is standard OAuth practice for native apps

## Testing Checklist

After implementation:
- [ ] Web login still works (backstage)
- [ ] iOS login works (mobile app)
- [ ] Token exchange uses correct client
- [ ] PKCE verification works for both
- [ ] JWT tokens valid for both clients
