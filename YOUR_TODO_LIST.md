# 🎯 YOUR TODO LIST - Mobile Testing Setup

## ✅ What I Did For You

I created a new branch and set up everything for your mobile testing:

**Branch:** `setup/cloudflare-tunnel-testing`

**Created files:**
1. ✅ **MOBILE_TESTING_SETUP.md** - Complete step-by-step guide with troubleshooting
2. ✅ **QUICK_START_MOBILE_TEST.md** - 30-second quick reference card
3. ✅ **scripts/start_api_server.sh** - Smart script to start API server
4. ✅ **scripts/start_tunnel.sh** - Smart script to start Cloudflare tunnel
5. ✅ **scripts/test_tunnel_connection.sh** - Test if everything works
6. ✅ **client_docs/FLUTTER_CONFIG_EXAMPLE.dart** - Flutter code examples

All scripts are executable and ready to use! 🚀

---

## 📋 WHAT YOU NEED TO DO

### Step 1: Install Cloudflare Tunnel (One-Time, 1 minute)

Open Terminal:

```bash
brew install cloudflare/cloudflare/cloudflared
```

**Verify:**
```bash
cloudflared --version
```

You should see version info.

---

### Step 2: Start API Server (Every time you test)

Open Terminal 1:

```bash
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_api_server.sh
```

**Expected output:**
```
========================================
  Starting Pocket Guide API Server
========================================

✅ Starting API server on http://localhost:8000
✅ API docs available at http://localhost:8000/docs

Press Ctrl+C to stop the server
```

**✅ LEAVE THIS TERMINAL OPEN!**

---

### Step 3: Start Cloudflare Tunnel (Every time you test)

Open Terminal 2 (NEW window):

```bash
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_tunnel.sh
```

**Expected output:**
```
========================================
  Starting Cloudflare Tunnel
========================================

✅ cloudflared is installed
✅ Creating tunnel to http://localhost:8000

================================================
  COPY THE URL THAT APPEARS BELOW
  You'll need it for your Flutter app!
================================================

2024-03-21 INF +-------------------------------------------------------------------------+
2024-03-21 INF |  Your quick Tunnel has been created! Visit it at:                       |
2024-03-21 INF |  https://abc-xyz-123-def.trycloudflare.com                             |
2024-03-21 INF +-------------------------------------------------------------------------+
```

**📋 COPY THIS URL:** `https://abc-xyz-123-def.trycloudflare.com`

**✅ LEAVE THIS TERMINAL OPEN TOO!**

---

### Step 4: Test Connection (Optional but Recommended)

Open Terminal 3:

```bash
cd /Users/huanghongyan/Github/pocket-guide
./scripts/test_tunnel_connection.sh
```

Paste your tunnel URL when asked.

**Expected output:**
```
========================================
  Testing Tunnel Connection
========================================

[1/4] Testing if tunnel is reachable...
✅ Tunnel is reachable!

[2/4] Testing API documentation endpoint...
✅ API docs accessible!

[3/4] Testing OpenAPI schema...
✅ Map mode endpoints detected!

[4/4] Testing authentication requirement...
✅ Authentication is working!

========================================
  ✅ All Tests Passed!
========================================
```

---

### Step 5: Update Your Flutter App

**Find your API config file** (create if doesn't exist):
- Usually: `lib/config/api_config.dart` or `lib/services/api_config.dart`

**Option A: If you have a config file, update it:**

```dart
class ApiConfig {
  static const String baseUrl = 'https://YOUR_TUNNEL_URL_HERE';  // ← Paste URL from Step 3
}
```

**Option B: If you don't have one, see:**
- `client_docs/FLUTTER_CONFIG_EXAMPLE.dart` (I created complete examples)

**IMPORTANT:**
- ❌ Don't include trailing slash
- ❌ Don't add `/api` or any suffix
- ✅ Just the base URL: `https://abc-xyz-123.trycloudflare.com`

---

### Step 6: Build App on iPhone

**Option A: Xcode**
1. Connect iPhone via USB
2. Open project in Xcode
3. Select iPhone as target
4. Click Run ▶️

**Option B: Flutter CLI**
```bash
cd /path/to/your/flutter/app
flutter devices  # Verify iPhone is connected
flutter run --release
```

---

### Step 7: Test Authentication First (Before Walking)

1. Open app on iPhone
2. Login (Google OAuth)
3. Select a tour
4. Try marking a POI complete (test POST /progress)
5. Check if it saved (test GET /progress)

**If something fails:**
- Check both terminal windows are still running
- Check tunnel URL is correct in Flutter app
- Check you're logged in

---

### Step 8: Go Walk! 🚶‍♂️

Now you can go outside and test:

1. Start a tour in the app
2. Enable GPS when prompted
3. Walk around
4. GPS trail should record
5. POIs should auto-complete when within 100m + audio finished

**Watch Terminal 1** to see API requests in real-time!

---

## 🔄 Next Time You Test

You only need Steps 2-3:

```bash
# Terminal 1
./scripts/start_api_server.sh

# Terminal 2
./scripts/start_tunnel.sh
# Copy the NEW URL (changes each time)
# Update Flutter app with new URL
```

**Note:** Tunnel URL changes each restart, so you'll need to update your Flutter app each time.

---

## 📚 Documentation Files

**Quick reference:**
- **QUICK_START_MOBILE_TEST.md** ← Read this first! (30 seconds)

**Detailed guide:**
- **MOBILE_TESTING_SETUP.md** ← Read for troubleshooting

**Flutter examples:**
- **client_docs/FLUTTER_CONFIG_EXAMPLE.dart** ← Copy-paste code

---

## 🛑 When Done Testing

**Both Terminals:** Press `Ctrl+C`

---

## ❓ Common Issues

**"Port 8000 already in use"**
```bash
lsof -ti:8000 | xargs kill -9
./scripts/start_api_server.sh
```

**"Tunnel URL doesn't work"**
- Wait 10-20 seconds (Cloudflare needs time to propagate)
- Try again

**"Not authenticated" in app**
- Make sure you logged in first
- Check JWT token is being sent in Authorization header

**GPS not working**
- Check iOS Settings → Your App → Location → "While Using App"

---

## 📊 What to Expect During Walk

**API calls per minute (normal usage):**
- GPS trail uploads: ~1 per minute
- Progress updates: occasional (when marking POI)
- Audio requests: occasional (when playing)
- **Total:** ~2-5 requests/minute

**Cloudflare limit:** ✅ Unlimited (no worries!)

---

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ App shows your tours
2. ✅ GPS blue dot moves as you walk
3. ✅ Trail line appears behind you
4. ✅ POIs auto-complete within 100m + audio finished
5. ✅ You can manually mark POIs complete
6. ✅ Progress percentage updates

---

## 🚀 Ready?

**Start with:**
1. Install cloudflared (Step 1)
2. Read QUICK_START_MOBILE_TEST.md
3. Follow steps 2-8

**Have fun testing! 🎯**

---

## 📍 Files Location

All files are in branch: `setup/cloudflare-tunnel-testing`

```
/Users/huanghongyan/Github/pocket-guide/
├── QUICK_START_MOBILE_TEST.md          ← Start here
├── MOBILE_TESTING_SETUP.md             ← Detailed guide
├── YOUR_TODO_LIST.md                   ← This file
├── scripts/
│   ├── start_api_server.sh            ← Run this first
│   ├── start_tunnel.sh                ← Run this second
│   └── test_tunnel_connection.sh      ← Test connection
└── client_docs/
    └── FLUTTER_CONFIG_EXAMPLE.dart    ← Flutter examples
```

---

**Questions?** Check MOBILE_TESTING_SETUP.md for troubleshooting!

**Good luck with your walk! 🚶‍♂️📱**
