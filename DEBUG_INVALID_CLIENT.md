# Debug: OAuth "invalid_client" Error

## Quick Diagnosis Steps

### Step 1: Check What Client is Sending

When you try to login, look at the **backend terminal logs**. You'll see:

```
INFO:api_auth:Client app login initiated:
INFO:api_auth:  - Redirect URI: <WHAT_THE_CLIENT_SENT>
INFO:api_auth:  - Detected OAuth client: web or ios
INFO:api_auth:  - Using client_id: 498782874156-xxxxx...
```

**Copy the exact redirect URI** shown in logs.

---

### Step 2: Check Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Find the client that backend is using (check the `Using client_id` from logs)
3. Look at **Authorized redirect URIs** list
4. **Does the exact URI from Step 1 appear in this list?**

**Important**: Must be **exact match**:
- ❌ `http://localhost:8000/callback` vs `http://localhost:8000/auth/callback` → Different
- ❌ `http://localhost:8000/callback` vs `http://localhost:8000/callback/` → Different (trailing slash)
- ❌ `http://localhost:8000` vs `https://localhost:8000` → Different (http vs https)
- ✅ `http://localhost:8000/auth/callback` vs `http://localhost:8000/auth/callback` → Same

---

## Common Causes

### Cause 1: Client Sending Wrong redirect_uri

**Problem**: Client app is sending `redirect_uri` that doesn't match any registered URI.

**Example**:
- Client sends: `http://localhost:8000/auth/callback`
- But should send: `http://localhost:65263/callback` (their own callback URL)

**Question for Client Team**:
> "What redirect_uri are you sending to `/auth/client/google/login`?"

**The redirect_uri should be**:
- For web app on port 65263: `http://localhost:65263/callback`
- For web app on port 8000: `http://localhost:8000/callback`
- For iOS app: `pocketguide://auth/callback`

---

### Cause 2: Wrong Client Selected

**Problem**: Backend detects wrong client type.

**Check**: Look at backend logs:
```
Detected OAuth client: web
```

**If client is running on localhost port 65263**:
- Expected: `web` ✅
- If shows: `ios` ❌ → Detection bug

**If client is iOS app**:
- Expected: `ios` ✅
- If shows: `web` ❌ → Detection bug

---

### Cause 3: Redirect URI Not Added to Google Cloud Console

**Problem**: The redirect URI is correct, but not registered.

**Check Google Cloud Console**:

For **Web client** (if localhost):
```
Authorized redirect URIs:
☐ http://localhost:8000/auth/callback
☐ http://localhost:65263/callback
☐ http://localhost:5173/callback
```

For **iOS client** (if mobile app):
```
Authorized redirect URIs:
☐ pocketguide://auth/callback
```

**Add missing URI** and wait 10 minutes.

---

## The Correct Flow

### For Chrome/Web Debugging

**Client app (localhost:65263)**:
1. User clicks "Sign in with Google"
2. Client calls backend:
   ```
   GET /auth/client/google/login?redirect_uri=http://localhost:65263/callback&code_challenge=xxx
   ```
3. Backend detects: `web` client (because `http://` prefix)
4. Backend returns Google OAuth URL using Web client_id
5. Client redirects to Google
6. User signs in
7. **Google redirects to: `http://localhost:65263/callback?code=xxx&state=xxx`**
8. Client extracts `code` and calls backend:
   ```
   GET /auth/client/google/callback?code=xxx&state=xxx&code_verifier=xxx
   ```
9. Backend exchanges code for tokens
10. Backend returns access_token & refresh_token

**Key Point**: `redirect_uri` should be **client's URL**, not backend's URL.

### For iOS Native App

**iOS app**:
1. User taps "Sign in with Google"
2. App calls backend:
   ```
   GET /auth/client/google/login?redirect_uri=pocketguide://auth/callback&code_challenge=xxx
   ```
3. Backend detects: `ios` client (because `pocketguide://` prefix)
4. Backend returns Google OAuth URL using iOS client_id
5. App opens Google sign-in
6. User signs in
7. **Google redirects to: `pocketguide://auth/callback?code=xxx&state=xxx`**
8. App extracts `code` and calls backend:
   ```
   GET /auth/client/google/callback?code=xxx&state=xxx&code_verifier=xxx
   ```
9. Backend exchanges code for tokens
10. Backend returns access_token & refresh_token

---

## What to Ask Client Team

### Question 1: What redirect_uri are you sending?

```
When you call /auth/client/google/login, what redirect_uri parameter are you using?
```

Expected answers:
- **Web app**: `http://localhost:[YOUR_PORT]/callback`
- **iOS app**: `pocketguide://auth/callback`

### Question 2: Can you share the exact error URL?

```
When Google shows the error, can you copy the full URL from the browser address bar?
```

The URL will look like:
```
https://accounts.google.com/o/oauth2/auth?error=invalid_client&...&redirect_uri=XXXXX
```

The `redirect_uri=XXXXX` part will show what was sent to Google.

### Question 3: What port is your app running on?

```
Are you testing on:
- localhost:65263
- localhost:8000
- localhost:5173
- Other port?
```

This helps us know which redirect URI to register.

---

## Add Required redirect_uri to Google Cloud Console

Based on client's answer to Question 1, add the exact URI:

### For Web Client (localhost testing)

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
2. Click your **Web application** client
3. Under "Authorized redirect URIs", add:
   ```
   http://localhost:8000/callback
   http://localhost:65263/callback
   http://localhost:5173/callback
   http://localhost:3000/callback
   ```
   (Add the port your client is actually using)

4. Under "Authorized JavaScript origins", add:
   ```
   http://localhost:8000
   http://localhost:65263
   http://localhost:5173
   ```

5. Click Save
6. Wait 10 minutes

### For iOS Client (mobile app)

1. Click your **iOS application** client
2. Should already have:
   ```
   pocketguide://auth/callback
   ```

---

## Test Commands

### 1. Start API server with enhanced logging
```bash
./scripts/start_api_server.sh
```

### 2. Watch logs during login attempt

You'll see:
```
INFO:api_auth:Client app login initiated:
INFO:api_auth:  - Redirect URI: http://localhost:65263/callback
INFO:api_auth:  - Detected OAuth client: web
INFO:api_auth:  - Using client_id: 498782874156-8ecqia8ge49ce...
```

### 3. Copy the exact redirect URI from logs

### 4. Verify it's in Google Cloud Console

Go to Console → Find the client_id from logs → Check if redirect URI is in the list

---

## Still Not Working? Double-Check These

### ✓ Checklist

- [ ] Client is sending correct redirect_uri (their URL, not backend URL)
- [ ] redirect_uri matches registered URI **exactly** (no trailing slash difference, etc.)
- [ ] Using correct client_id (web for localhost, ios for mobile)
- [ ] Waited 10 minutes after adding URI to Google Cloud Console
- [ ] Cleared browser cache
- [ ] Backend logs show correct client type detection

---

## Example Debugging Session

**User reports**: Getting `invalid_client` error

**Step 1 - Check logs**:
```
INFO:api_auth:Client app login initiated:
INFO:api_auth:  - Redirect URI: http://localhost:8000/auth/callback
INFO:api_auth:  - Detected OAuth client: web
INFO:api_auth:  - Using client_id: 498782874156-8ecqia8ge49ce...
```

**Step 2 - Check Google Cloud Console**:
- Found Web client: `498782874156-8ecqia8ge49ce...`
- Authorized redirect URIs: (empty) ❌

**Step 3 - Fix**:
- Add `http://localhost:8000/auth/callback`
- Save and wait 10 minutes

**Step 4 - Test again**:
- ✅ Works!

---

## Quick Fix Script

Run this to see current OAuth configuration:

```bash
# Check environment
grep GOOGLE .env

# Check config
grep -A 15 "google_oauth:" config.yaml

# Test detection logic
python3 test_oauth_detection.py
```

---

## Need More Info?

Please provide:

1. **Exact redirect_uri from backend logs** (when you try to login)
2. **Client type detected** (web or ios - from backend logs)
3. **client_id being used** (from backend logs)
4. **Full error URL** (copy from browser when error appears)
5. **What port is your client app running on?**

With this info, we can identify the exact issue.
