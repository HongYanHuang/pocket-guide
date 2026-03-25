# Fixing "invalid_client" with "flowName=GeneralOAuthFlow"

## What This Error Means

When Google shows:
```
error 401: invalid_client
Request details: flowName=GeneralOAuthFlow
```

**Important**: `flowName=GeneralOAuthFlow` is **NOT a parameter we send**. This is Google's internal classification showing what type of OAuth flow was attempted.

## Root Cause

The `invalid_client` error means **Google doesn't recognize or accept the client_id** we're sending. This is NOT about the redirect_uri (you confirmed that's correct).

### Most Common Causes

1. **client_id doesn't exist** in Google Cloud Console
2. **client_id is disabled**
3. **client_id is for wrong type** (e.g., Android client_id but request comes from web)
4. **Web client doesn't allow PKCE flow** (needs configuration)

---

## What We Send to Google

Our backend sends these parameters:

```
https://accounts.google.com/o/oauth2/v2/auth?
  client_id=XXXXX.apps.googleusercontent.com        ← From GOOGLE_WEB_CLIENT_ID
  &redirect_uri=http://localhost:3000/auth/callback  ← From client's request
  &response_type=code                                ← Standard OAuth
  &scope=openid%20email%20profile                    ← User info permissions
  &code_challenge=xxx                                ← PKCE security
  &code_challenge_method=S256                        ← PKCE method
  &state=xxx                                         ← CSRF protection
```

**We do NOT send**:
- ❌ `flowName` (Google's internal label)
- ❌ `client_secret` (only used later in token exchange)

---

## Debug Steps

### Step 1: See Exact URL Being Generated

```bash
# Start API server
./scripts/start_api_server.sh

# In another terminal, test with your redirect_uri
curl "http://localhost:8000/auth/debug/oauth-config?redirect_uri=http://localhost:3000/auth/callback" | python3 -m json.tool
```

This shows:
- Detected client type (should be "web")
- client_id being used
- Exact OAuth URL generated
- All parameters sent to Google

### Step 2: Check client_id in .env

```bash
grep "GOOGLE_WEB_CLIENT_ID" .env
```

Copy that client_id value.

### Step 3: Verify in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Look for the client_id from Step 2
3. **Does it exist?** ✅ or ❌

#### If it DOESN'T exist:
Your `.env` has a wrong or old client_id. You need to:
- Create a new Web OAuth Client in Google Cloud Console
- Update `GOOGLE_WEB_CLIENT_ID` in `.env`
- Restart API server

#### If it DOES exist:
Check these:

4. **Client Type**: Should be "Web application" (NOT iOS, NOT Android)
5. **Status**: Should be enabled (not disabled/deleted)
6. **Redirect URIs**: Should include `http://localhost:3000/auth/callback`

---

## Common Issues

### Issue 1: Using iOS client_id for Web

**Problem**: Your `GOOGLE_WEB_CLIENT_ID` in `.env` is actually an iOS client_id.

**How to check**:
```bash
# Check both client IDs
grep "CLIENT_ID" .env
```

**Expected**:
```
GOOGLE_WEB_CLIENT_ID=498782874156-xxxxxxxxxx.apps.googleusercontent.com   ← Web
GOOGLE_IOS_CLIENT_ID=498782874156-yyyyyyyyyy.apps.googleusercontent.com   ← iOS (different)
```

**If they're the same** → Wrong! Web needs a separate client_id.

**Fix**: Create a new "Web application" OAuth client in Google Cloud Console.

### Issue 2: Client Doesn't Allow PKCE

**Problem**: Old OAuth clients might not allow PKCE (code_challenge parameter).

**How to check**: Look for this error in Google's response when you test.

**Fix**:
1. Go to Google Cloud Console
2. Edit the Web OAuth client
3. Look for "PKCE" or "Code Challenge" settings
4. Enable it
5. Save

Or create a NEW Web OAuth client (new ones support PKCE by default).

### Issue 3: Client Disabled

**Problem**: The OAuth client was disabled or deleted.

**How to check**: In Google Cloud Console, the client shows as "Disabled" or doesn't appear.

**Fix**: Re-enable it or create a new one.

### Issue 4: Wrong Project

**Problem**: The client_id exists but in a different Google Cloud project.

**How to check**: In Google Cloud Console, make sure you're viewing the correct project (check top nav bar).

**Fix**: Switch to correct project, or update `.env` with client_id from current project.

---

## Verification Checklist

Run these checks:

### ✓ Backend Configuration

```bash
# 1. Check OAuth clients configured
./scripts/start_api_server.sh
# Should see: "OAuth clients configured: ['web', 'ios']"

# 2. Check client IDs in .env
grep "GOOGLE.*CLIENT_ID" .env
# Should show TWO different client IDs (web and ios)

# 3. Test URL generation
curl "http://localhost:8000/auth/debug/oauth-config?redirect_uri=http://localhost:3000/auth/callback"
# Check the client_id in response
```

### ✓ Google Cloud Console

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
2. Find the client_id from step 3 above
3. Verify:
   - [ ] Client exists
   - [ ] Client type: "Web application"
   - [ ] Client status: Enabled
   - [ ] Redirect URIs includes: `http://localhost:3000/auth/callback`
   - [ ] PKCE enabled (if there's such a setting)

---

## Test the Fix

### Method 1: Test with Debug Endpoint

```bash
curl "http://localhost:8000/auth/debug/oauth-config?redirect_uri=http://localhost:3000/auth/callback"
```

Check the `generated_oauth_url`. Copy and paste it in browser. Should show Google sign-in, NOT "invalid_client" error.

### Method 2: Test with Actual Login

```bash
# Start API server
./scripts/start_api_server.sh

# In client app, try to login
# Watch backend logs for:
INFO:api_auth:Client app login initiated:
INFO:api_auth:  - Redirect URI: http://localhost:3000/auth/callback
INFO:api_auth:  - Detected OAuth client: web
INFO:api_auth:  - Using client_id: 498782874156-xxxxx...
```

Copy that client_id and verify it exists in Google Cloud Console.

---

## Still Not Working?

### Get These Details:

1. **client_id being used** (from debug endpoint or logs)
2. **Does it exist in Google Cloud Console?** (yes/no)
3. **What type is it?** (Web application / iOS / Android / Other)
4. **Is it enabled?** (yes/no)
5. **Project name** in Google Cloud Console

### Possible Solutions:

#### Solution A: Create New Web OAuth Client

If your current Web client is misconfigured:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Web application"
4. Name: "Pocket Guide Web Client"
5. Authorized redirect URIs:
   ```
   http://localhost:3000/auth/callback
   http://localhost:8000/auth/callback
   http://localhost:65263/auth/callback
   ```
6. Authorized JavaScript origins:
   ```
   http://localhost:3000
   http://localhost:8000
   http://localhost:65263
   ```
7. Click Create
8. Copy the new client_id and client_secret
9. Update `.env`:
   ```bash
   GOOGLE_WEB_CLIENT_ID=<new_client_id>
   GOOGLE_WEB_CLIENT_SECRET=<new_client_secret>
   ```
10. Restart API server
11. Test again

#### Solution B: Verify Correct Project

Make sure the client_id in `.env` is from the SAME Google Cloud project you're looking at in the Console.

Check project ID:
```bash
# If you have gcloud CLI
gcloud config get-value project
```

---

## What flowName=GeneralOAuthFlow Means

This is Google's way of saying: "You're trying to use the standard OAuth 2.0 flow (not OpenID Connect, not device flow, not service account flow), but the client_id is invalid."

**We are NOT sending `flowName` as a parameter**. Google adds this to the error message for debugging.

---

## Summary

**The error is NOT**:
- ❌ About redirect_uri (you confirmed this works)
- ❌ About parameters we're sending
- ❌ About `flowName` (we don't send this)

**The error IS**:
- ✅ About the `client_id` itself
- ✅ Either it doesn't exist, is disabled, is wrong type, or doesn't allow PKCE

**Fix**: Verify the `GOOGLE_WEB_CLIENT_ID` in your `.env` file corresponds to a valid, enabled, "Web application" OAuth client in Google Cloud Console.

---

## Quick Test Command

```bash
# See exact client_id and URL being generated
curl -s "http://localhost:8000/auth/debug/oauth-config?redirect_uri=http://localhost:3000/auth/callback" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Client ID: {d['client_id']}\\nClient Type: {d['detected_client_type']}\\nOAuth URL: {d['generated_oauth_url'][:100]}...\")"
```

Then go verify that client_id exists in Google Cloud Console.
