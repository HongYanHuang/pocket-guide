# Fix: OAuth "invalid_client" Error for Chrome/Web Debugging

## Problem

When testing in Chrome (localhost), you get:
```
error 401: invalid_client
Request details: flowName=GeneralOAuthFlow
```

## Root Cause

Your **Web OAuth Client** in Google Cloud Console doesn't have the redirect URI registered.

Backend correctly detects:
- `http://localhost:*` → uses **Web client**
- `pocketguide://` → uses **iOS client**

But Google rejects it because the redirect URI isn't in the allowed list.

---

## Solution: Add Redirect URIs to Google Cloud Console

### Step 1: Go to Google Cloud Console

1. Open [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select your project
3. Click on **OAuth 2.0 Client IDs**
4. Find your **Web client** (check .env file for GOOGLE_WEB_CLIENT_ID)

### Step 2: Add Authorized Redirect URIs

Click **Edit** on the Web client, then add these URIs:

#### For Local Development (Chrome Debugging)
```
http://localhost:8000/auth/callback
http://localhost:65263/auth/callback
http://localhost:5173/auth/callback
http://localhost:3000/auth/callback
```

#### For Cloudflare Tunnel Testing
```
https://[your-tunnel-url].trycloudflare.com/auth/callback
```
*(Replace with actual tunnel URL when you start it)*

#### For Production
```
https://your-domain.com/auth/callback
https://api.your-domain.com/auth/callback
```

### Step 3: Add Authorized JavaScript Origins

Also add these under **Authorized JavaScript origins**:

```
http://localhost:8000
http://localhost:65263
http://localhost:5173
http://localhost:3000
https://[your-tunnel-url].trycloudflare.com
```

### Step 4: Save and Wait

- Click **Save**
- Wait **5-10 minutes** for changes to propagate
- Try login again

---

## How Backend Detection Works

The backend automatically chooses the correct OAuth client:

```python
def detect_client_type(redirect_uri: str) -> str:
    if redirect_uri.startswith("pocketguide://"):
        return "ios"  # Use iOS client (no client_secret needed)
    elif redirect_uri.startswith("http://") or redirect_uri.startswith("https://"):
        return "web"  # Use Web client (has client_secret)
    else:
        return "web"  # Default
```

### Examples

| Redirect URI | Detected Client | Client ID Used |
|--------------|----------------|----------------|
| `http://localhost:8000/auth/callback` | **web** | `498782874156-8ecqia8ge49ce...` |
| `http://localhost:65263/callback` | **web** | `498782874156-8ecqia8ge49ce...` |
| `https://app.example.com/callback` | **web** | `498782874156-8ecqia8ge49ce...` |
| `pocketguide://auth/callback` | **ios** | `498782874156-vdhctn0cc6uh2...` |

---

## Verify Configuration

### 1. Check Backend Logs

Start API server and look for:

```bash
./scripts/start_api_server.sh
```

You should see:
```
INFO:api_server:OAuth clients configured: ['web', 'ios']
```

### 2. Test Login and Check Logs

When you try to login, backend logs:

```
INFO:api_auth:Client app login initiated:
INFO:api_auth:  - Redirect URI: http://localhost:8000/auth/callback
INFO:api_auth:  - Detected OAuth client: web
INFO:api_auth:  - Using client_id: 498782874156-8ecqia8ge49ce...
```

**If you see `web` for localhost URLs** → Backend detection is working correctly ✅

**If Google still rejects** → Redirect URI not added in Google Cloud Console ❌

### 3. Verify Environment Variables

```bash
grep "GOOGLE.*CLIENT" .env
```

Expected output:
```
GOOGLE_WEB_CLIENT_ID=498782874156-xxxxxxxxxx.apps.googleusercontent.com
GOOGLE_WEB_CLIENT_SECRET=GOCSPX-xxxxxxxxxx
GOOGLE_IOS_CLIENT_ID=498782874156-yyyyyyyyyy.apps.googleusercontent.com
```

---

## Testing

### Test 1: Chrome Localhost Login

```bash
# 1. Start API server
./scripts/start_api_server.sh

# 2. In browser, open your app
http://localhost:65263

# 3. Click "Sign in with Google"
# 4. Check backend logs for detection
# 5. Google should accept redirect_uri
```

### Test 2: iOS App (Simulator)

```bash
# 1. Start API with Cloudflare tunnel
./start-mobile-test-tmux.sh

# 2. Run iOS app in simulator
# 3. Click "Sign in with Google"
# 4. Check logs: should show "ios" client
```

### Test 3: Detection Logic

Run test script:
```bash
python3 test_oauth_detection.py
```

All should show ✅

---

## Current Configuration Summary

### Web OAuth Client
- **Client ID**: `${GOOGLE_WEB_CLIENT_ID}` (from .env)
- **Client Secret**: ✅ Yes (required)
- **For**: Chrome debugging, web apps, localhost
- **Redirect URIs**: ⚠️ **You need to add these manually**

### iOS OAuth Client
- **Client ID**: `${GOOGLE_IOS_CLIENT_ID}` (from .env)
- **Client Secret**: ❌ No (PKCE only)
- **For**: iOS native app
- **Redirect URIs**: `pocketguide://auth/callback` (should already be set)

---

## Common Issues

### Issue 1: Still Getting "invalid_client" After Adding URIs

**Cause**: Changes not propagated yet
**Solution**: Wait 10 minutes, clear browser cache, try again

### Issue 2: Backend Uses Wrong Client

**Cause**: Detection logic issue
**Solution**: Check backend logs to see which client is detected. Should be:
- localhost → web
- pocketguide:// → ios

### Issue 3: "redirect_uri_mismatch" Error

**Cause**: Exact URI not in list (case-sensitive, protocol-sensitive)
**Solution**:
- Check exact URI in error message
- Add **exact** match to Google Cloud Console (http vs https, trailing slash, port number)

### Issue 4: Environment Variables Not Loaded

**Cause**: `.env` file not in project root or not loaded
**Solution**:
```bash
# Check if .env is loaded
cat .env | grep GOOGLE_WEB_CLIENT_ID

# Restart API server
./scripts/start_api_server.sh
```

---

## Quick Fix Checklist

- [ ] Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
- [ ] Find Web client (check GOOGLE_WEB_CLIENT_ID in .env)
- [ ] Click Edit
- [ ] Add redirect URIs:
  - [ ] `http://localhost:8000/auth/callback`
  - [ ] `http://localhost:65263/auth/callback`
  - [ ] `http://localhost:5173/auth/callback`
- [ ] Add JavaScript origins:
  - [ ] `http://localhost:8000`
  - [ ] `http://localhost:65263`
  - [ ] `http://localhost:5173`
- [ ] Click Save
- [ ] Wait 10 minutes
- [ ] Clear browser cache
- [ ] Test login again
- [ ] Check backend logs for `Detected OAuth client: web`

---

## Debug Commands

```bash
# Test detection logic
python3 test_oauth_detection.py

# Check environment variables
grep GOOGLE .env

# Check OAuth config
grep -A 15 "google_oauth:" config.yaml

# Start API with verbose logging
./scripts/start_api_server.sh

# Monitor logs during login
tail -f logs/api_server.log  # If logging to file
```

---

## Need More Help?

1. **Check backend logs** during login attempt
2. **Copy exact error message** from Google
3. **Copy exact redirect_uri** from URL bar when error happens
4. **Verify which client_id** backend is using (from logs)
5. **Double-check Google Cloud Console** has exact URI match

The backend detection logic is correct ✅
The issue is Google Cloud Console configuration ⚙️
