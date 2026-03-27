# Google Cloud Console Verification Checklist

Your backend configuration is correct. The issue is in Google Cloud Console settings.

---

## Your Client IDs

**Web Client**: `498782874156-8ecqia8ge49cegnqae1eeq3qgdvanrlj.apps.googleusercontent.com`
**iOS Client**: `498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com`

---

## Step-by-Step Verification

### 1. Go to Google Cloud Console

[https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)

### 2. Find Your Web Client

Search for: `498782874156-8ecqia8ge49cegnqae1eeq3qgdvanrlj`

**Does it exist?**
- ✅ Yes → Continue to Step 3
- ❌ No → **PROBLEM FOUND**: Client doesn't exist, needs to be created

### 3. Check Client Type

Click on the client to view details.

**Type should be**: `Web application`

**If it shows**: iOS, Android, Desktop, Other → **PROBLEM FOUND**: Wrong type

### 4. Check Status

**Status should be**: Enabled / Active

**If it shows**: Disabled, Deleted → **PROBLEM FOUND**: Client is disabled

### 5. Check Authorized Redirect URIs

Click **Edit** on the Web client.

**Under "Authorized redirect URIs", you should see**:

```
☐ http://localhost:3000/auth/callback
☐ http://localhost:8000/auth/callback
☐ http://localhost:65263/auth/callback
☐ http://localhost:5173/auth/callback
```

**Missing any of these?** → **PROBLEM FOUND**: Add them

### 6. Check Authorized JavaScript Origins

**Under "Authorized JavaScript origins", you should see**:

```
☐ http://localhost:3000
☐ http://localhost:8000
☐ http://localhost:65263
☐ http://localhost:5173
```

**Missing any of these?** → Add them (helps with CORS)

### 7. Check for PKCE Support

Some old clients don't support PKCE (code_challenge parameter).

**If your client was created before 2020**, it might not support PKCE.

**Solution**: Create a new Web OAuth client (new ones support PKCE by default).

---

## Quick Fix: Add All Required Redirect URIs

1. Click **Edit** on Web client
2. Under "Authorized redirect URIs", click **+ ADD URI**
3. Add these one by one:
   ```
   http://localhost:3000/auth/callback
   http://localhost:8000/auth/callback
   http://localhost:65263/auth/callback
   http://localhost:5173/auth/callback
   ```
4. Under "Authorized JavaScript origins", click **+ ADD URI**
5. Add these:
   ```
   http://localhost:3000
   http://localhost:8000
   http://localhost:65263
   http://localhost:5173
   ```
6. Click **SAVE**
7. **Wait 10 minutes** for changes to propagate
8. Clear browser cache
9. Test again

---

## If Web Client Doesn't Exist

Create a new one:

1. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
2. Application type: **Web application**
3. Name: `Pocket Guide Web Client`
4. Authorized redirect URIs:
   ```
   http://localhost:3000/auth/callback
   http://localhost:8000/auth/callback
   http://localhost:65263/auth/callback
   http://localhost:5173/auth/callback
   ```
5. Authorized JavaScript origins:
   ```
   http://localhost:3000
   http://localhost:8000
   http://localhost:65263
   http://localhost:5173
   ```
6. Click **CREATE**
7. Copy the new **Client ID** and **Client Secret**
8. Update `.env`:
   ```bash
   GOOGLE_WEB_CLIENT_ID=<new_client_id>
   GOOGLE_WEB_CLIENT_SECRET=<new_client_secret>
   ```
9. Restart API server:
   ```bash
   ./scripts/start_api_server.sh
   ```

---

## Verify iOS Client Too

While you're there, check the iOS client:

Search for: `498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5`

**Should have**:
- Type: iOS
- Redirect URI: `pocketguide://auth/callback`
- Status: Enabled

---

## Test After Changes

### Method 1: Use Debug Endpoint

```bash
# Start API server
./scripts/start_api_server.sh

# Test detection
curl "http://localhost:8000/auth/debug/oauth-config?redirect_uri=http://localhost:3000/auth/callback"
```

Should show your Web client_id and not error.

### Method 2: Test OAuth URL

The debug endpoint returns `generated_oauth_url`. Copy and paste it in browser.

**If Google shows sign-in page** → ✅ Working!
**If Google shows "invalid_client"** → ❌ Still misconfigured

---

## Common Issues

### Issue: "Client doesn't exist"

**Cause**: Client ID in `.env` is wrong or was deleted.

**Fix**: Create new Web OAuth client, update `.env`.

### Issue: "redirect_uri_mismatch" instead of "invalid_client"

**Good news**: This means client_id is valid! Just missing redirect URI.

**Fix**: Add the exact redirect URI shown in error to Google Console.

### Issue: Still getting "invalid_client" after adding URIs

**Possible causes**:
1. Changes not propagated (wait 10 minutes)
2. Browser cache (clear cache or use incognito)
3. Wrong client_id (double-check `.env` matches Google Console)
4. Client is disabled (check status in Console)

---

## Screenshot Checklist

Take screenshots of:

1. ✅ Web client exists and is enabled
2. ✅ Web client type is "Web application"
3. ✅ Redirect URIs list (should include localhost:3000)
4. ✅ JavaScript origins list

Share these if still not working.

---

## After You Fix It

Restart API server to ensure config is loaded:

```bash
./scripts/start_api_server.sh
```

You should see:
```
INFO:api_server:OAuth clients configured: ['web', 'ios']
```

Then test login from your client app.
