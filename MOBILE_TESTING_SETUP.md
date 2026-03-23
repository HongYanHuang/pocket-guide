# Mobile Testing Setup Guide - Cloudflare Tunnel

## 🎯 Goal
Test the Map Mode API from your iPhone while walking outside using Cloudflare Tunnel to expose your local API server.

---

## 📋 What You Need to Do (Step-by-Step)

### Step 1: Install Cloudflare Tunnel (One-Time Setup)

Open Terminal and run:

```bash
brew install cloudflare/cloudflare/cloudflared
```

**Expected output:**
```
==> Downloading cloudflare/cloudflare/cloudflared
...
🍺  cloudflared was successfully installed!
```

**Verify installation:**
```bash
cloudflared --version
```

You should see something like: `cloudflared version 2024.x.x`

---

### Step 2: Start Your API Server

Open Terminal and navigate to your project:

```bash
cd /Users/huanghongyan/Github/pocket-guide
```

Start the API server:

```bash
./scripts/start_api_server.sh
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**✅ Keep this terminal window open!**

---

### Step 3: Start Cloudflare Tunnel

Open a **NEW Terminal window** and run:

```bash
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_tunnel.sh
```

**Expected output:**
```
2024-03-21 20:00:00 INF +--------------------------------------------------------------------------------------------+
2024-03-21 20:00:00 INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
2024-03-21 20:00:00 INF |  https://abc-def-ghi-jkl.trycloudflare.com                                                |
2024-03-21 20:00:00 INF +--------------------------------------------------------------------------------------------+
```

**📝 IMPORTANT: Copy the URL!**

Example: `https://abc-def-ghi-jkl.trycloudflare.com`

**✅ Keep this terminal window open too!**

---

### Step 4: Test the Tunnel (Optional but Recommended)

In a **third Terminal window**, test that the tunnel works:

```bash
# Replace YOUR_TUNNEL_URL with the URL from Step 3
curl https://YOUR_TUNNEL_URL/docs

# Example:
# curl https://abc-def-ghi-jkl.trycloudflare.com/docs
```

If it works, you should see HTML output starting with `<!DOCTYPE html>`.

---

### Step 5: Update Your Flutter App

In your Flutter app, update the base URL:

**File to edit:** (your API service file, e.g., `lib/services/api_config.dart`)

```dart
class ApiConfig {
  // Replace with YOUR tunnel URL from Step 3
  static const String baseUrl = 'https://abc-def-ghi-jkl.trycloudflare.com';

  // Don't include /api or any path suffix, just the base URL
}
```

**OR if you have a simpler config:**

```dart
final String baseUrl = 'https://YOUR_TUNNEL_URL';  // Replace this
```

---

### Step 6: Build and Install App on iPhone

**Option A: Using Xcode**

1. Open your Flutter project in Xcode
2. Connect your iPhone via USB
3. Select your iPhone as the target device
4. Click "Run" (▶️)

**Option B: Using Flutter CLI**

```bash
cd /path/to/your/flutter/app

# Make sure iPhone is connected and trusted
flutter devices

# Build and install
flutter run --release
```

---

### Step 7: Test Authentication First

Before going outside:

1. **Open the app on your iPhone**
2. **Login** (Google OAuth should work)
3. **Verify you can see tours**
4. **Try marking a POI complete** (test POST /progress)
5. **Check if progress shows** (test GET /progress)

**If any step fails:**
- Check both terminal windows are still running
- Check tunnel URL is correct in Flutter app
- Check WiFi/cellular data is enabled

---

### Step 8: Go Walk! 🚶‍♂️

Now you can go outside and test:

1. **Start a tour** in the app
2. **Enable GPS** when prompted
3. **Walk around** (trail recording should work)
4. **Visit POIs** (auto-completion should trigger)
5. **Check trail** is being recorded

---

## 🔍 Monitoring & Debugging

### View Real-Time Requests

While testing, you can monitor requests in Terminal 1 (API server).

You'll see logs like:
```
INFO:     127.0.0.1:54540 - "POST /tours/rome-tour-123/progress HTTP/1.1" 200 OK
INFO:     127.0.0.1:54540 - "POST /tours/rome-tour-123/trail HTTP/1.1" 200 OK
```

### Check API Health

From any browser (even on iPhone), visit:
```
https://YOUR_TUNNEL_URL/docs
```

You should see the Swagger API documentation.

---

## 🛑 Stopping Everything

When you're done testing:

**Terminal 1 (API Server):**
```bash
# Press Ctrl+C
```

**Terminal 2 (Cloudflare Tunnel):**
```bash
# Press Ctrl+C
```

---

## 🔄 Next Time You Test

You only need to repeat Steps 2-3:

```bash
# Terminal 1: Start API
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_api_server.sh

# Terminal 2: Start tunnel
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_tunnel.sh

# Copy the NEW tunnel URL and update Flutter app (URL changes each time)
```

**Note:** The tunnel URL will be different each time. You'll need to update your Flutter app with the new URL.

---

## ❓ Troubleshooting

### Problem: "command not found: cloudflared"

**Solution:** Install cloudflared first (Step 1)

---

### Problem: "Error: listen tcp :8000: bind: address already in use"

**Solution:** Another process is using port 8000

```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Then restart API server
```

---

### Problem: Tunnel URL doesn't work

**Solution:** Wait 10-20 seconds after tunnel starts

Cloudflare needs time to propagate the URL. Try again after a few seconds.

---

### Problem: "Not authenticated" errors in app

**Solution:** Make sure you login first

1. Open app
2. Login with Google
3. Then try using features

---

### Problem: GPS not recording

**Solution:** Check iOS permissions

1. Go to iPhone Settings
2. Find your app
3. Enable "Location" → "Always" or "While Using App"

---

### Problem: Trail not uploading

**Solution:** Check network connection

1. Make sure iPhone has WiFi or cellular data
2. Check tunnel is still running (Terminal 2)
3. Check API server is still running (Terminal 1)

---

## 📊 Expected API Usage During Walking

For a 10-minute walk:

- **GPS trail uploads:** ~10 requests (1 per minute)
- **Progress updates:** 1-3 requests (marking POIs complete)
- **Progress fetches:** 1-2 requests (checking status)
- **Audio requests:** 2-4 requests (if playing audio)

**Total:** ~15-20 requests in 10 minutes

**Cloudflare limit:** ✅ Unlimited (no worries!)

---

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ App shows your tours
2. ✅ GPS blue dot moves on map as you walk
3. ✅ Trail line appears behind you
4. ✅ POIs auto-complete when you're within 100m + audio finished
5. ✅ You can manually mark POIs complete
6. ✅ Progress percentage updates

---

## 📞 Need Help?

Check the API logs in Terminal 1 for errors.

Common things to check:
- Both terminals still running?
- Tunnel URL correct in Flutter app?
- Logged in to the app?
- GPS permissions enabled?
- Network connection working?

---

## 🚀 Ready to Start?

1. ✅ Install cloudflared (Step 1)
2. ✅ Start API server (Step 2)
3. ✅ Start tunnel (Step 3)
4. ✅ Copy tunnel URL
5. ✅ Update Flutter app with URL
6. ✅ Build app on iPhone
7. ✅ Test authentication
8. ✅ Go walk!

Good luck! 🎯
