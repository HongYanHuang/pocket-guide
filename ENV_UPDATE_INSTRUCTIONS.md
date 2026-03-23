# Environment Variables Update for Mobile OAuth

## Required Changes to Your `.env` File

### Current (Old Format):
```bash
GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-web-client-secret
```

### New (Multi-Client Format):
```bash
# Web OAuth Client (for backstage admin and web apps)
GOOGLE_WEB_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
GOOGLE_WEB_CLIENT_SECRET=your-web-client-secret

# iOS OAuth Client (provided by client team)
GOOGLE_IOS_CLIENT_ID=498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com
```

## Migration Steps

### Option 1: Update Existing `.env` (Recommended)

1. Open your `.env` file
2. Rename existing variables:
   ```bash
   # Change this:
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...

   # To this:
   GOOGLE_WEB_CLIENT_ID=...
   GOOGLE_WEB_CLIENT_SECRET=...
   ```
3. Add iOS client ID:
   ```bash
   GOOGLE_IOS_CLIENT_ID=498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com
   ```
4. Save the file

### Option 2: Keep Old Variables (Backward Compatible)

If you don't want to rename:

1. Keep your existing variables:
   ```bash
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```
2. Just add the iOS client ID:
   ```bash
   GOOGLE_IOS_CLIENT_ID=498782874156-vdhctn0cc6uh2jlvaoa01surqg9lnop5.apps.googleusercontent.com
   ```
3. The code will use `GOOGLE_CLIENT_ID` as fallback for `GOOGLE_WEB_CLIENT_ID`

## Verification

After updating, restart your API server:
```bash
./scripts/start_api_server.sh
```

You should see in the logs:
```
INFO:src.api_server:OAuth clients configured: ['web', 'ios']
```

## What This Enables

- ✅ Web login (backstage) - uses web client
- ✅ iOS login (mobile app) - uses iOS client
- ✅ Automatic client detection from redirect URI
- ✅ PKCE security for iOS (no client_secret needed)

## Troubleshooting

**If you see "OAuth clients configured: ['web']" only:**
- Check that `GOOGLE_IOS_CLIENT_ID` is set in `.env`
- Check that `.env` file is loaded (in project root)
- Restart API server

**If web login stops working:**
- Make sure `GOOGLE_WEB_CLIENT_ID` or `GOOGLE_CLIENT_ID` is set
- Make sure `GOOGLE_WEB_CLIENT_SECRET` or `GOOGLE_CLIENT_SECRET` is set

**If iOS login fails:**
- Make sure `GOOGLE_IOS_CLIENT_ID` matches the client team provided
- Check redirect URI is `pocketguide://auth/callback`
- Check Google Cloud Console has this redirect URI added
