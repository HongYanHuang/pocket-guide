# 🚀 START HERE - Mobile Testing

## 🎯 Two Ways to Start

### Option 1: One Command (tmux) ⭐ RECOMMENDED

**Requirements:** tmux installed

```bash
# Install tmux if needed
brew install tmux

# One command starts everything!
./start-mobile-test-tmux.sh
```

**That's it!** Both API server and tunnel start in split screen.

---

### Option 2: Two Separate Terminals

**If you prefer separate windows:**

```bash
# Terminal 1
./scripts/start_api_server.sh

# Terminal 2
./scripts/start_tunnel.sh
```

---

## 📋 Complete Setup (First Time)

### Step 1: Install Tools (One-Time)

```bash
# Install Cloudflare tunnel
brew install cloudflare/cloudflare/cloudflared

# Install tmux (optional, for Option 1)
brew install tmux
```

---

### Step 2: Start Servers

**Option A - One Command (tmux):**
```bash
cd /Users/huanghongyan/Github/pocket-guide
./start-mobile-test-tmux.sh
```

**Option B - Two Terminals:**
```bash
# Terminal 1
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_api_server.sh

# Terminal 2
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_tunnel.sh
```

---

### Step 3: Copy Tunnel URL

**Look for output like:**
```
+-------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at:                      |
|  https://abc-xyz-123-def.trycloudflare.com                            |
+-------------------------------------------------------------------------+
```

**📋 Copy this URL!**

---

### Step 4: Update Flutter App

**Edit your API config:**

```dart
// lib/config/api_config.dart (or similar)
class ApiConfig {
  static const String baseUrl = 'https://YOUR_TUNNEL_URL_HERE';
}
```

**OR see:** `client_docs/FLUTTER_CONFIG_EXAMPLE.dart` for complete examples

---

### Step 5: Build & Install on iPhone

```bash
cd /path/to/your/flutter/app
flutter run --release
```

**OR:** Open in Xcode and click Run ▶️

---

### Step 6: Test & Walk!

1. Open app on iPhone
2. Login (Google OAuth)
3. Start a tour
4. Go walk! 🚶‍♂️

---

## 🎨 tmux Layout (Option 1)

```
┌────────────────────────┬────────────────────────┐
│                        │                        │
│   API Server           │   Cloudflare Tunnel    │
│   (Left Pane)          │   (Right Pane)         │
│                        │                        │
│   Port: 8000           │   📋 COPY THE URL      │
│   Logs here            │   Tunnel URL here      │
│                        │                        │
└────────────────────────┴────────────────────────┘
```

**tmux Commands:**
- `Ctrl+b` then `→` / `←` - Switch panes
- `Ctrl+b` then `d` - Detach (keeps running)
- `Ctrl+c` in both panes - Stop servers

**Reattach later:**
```bash
tmux attach -t pocket-guide-mobile
```

---

## 🛑 Stop Everything

### If using tmux:
```bash
# Inside tmux: Ctrl+c in both panes
# Or kill session:
tmux kill-session -t pocket-guide-mobile
```

### If using separate terminals:
```bash
# Press Ctrl+C in both terminals
```

---

## 🔄 Next Time You Test

### Option 1 (tmux):
```bash
./start-mobile-test-tmux.sh
# Copy NEW tunnel URL
# Update Flutter app
```

### Option 2 (separate):
```bash
# Terminal 1: ./scripts/start_api_server.sh
# Terminal 2: ./scripts/start_tunnel.sh
# Copy NEW tunnel URL
# Update Flutter app
```

**Note:** Tunnel URL changes each time!

---

## ✅ Verify Everything Works

**Optional test script:**
```bash
./scripts/test_tunnel_connection.sh
```

Paste your tunnel URL when asked.

**Should see:**
```
✅ Tunnel is reachable!
✅ API docs accessible!
✅ Map mode endpoints detected!
✅ Authentication is working!
```

---

## ❓ Troubleshooting

### "No module named uvicorn"

**Fixed!** The scripts now use your virtual environment automatically.

If still failing:
```bash
# Activate virtual environment manually
source pocket-guide-3.11/bin/activate
python -m uvicorn src.api_server:app --reload --port 8000
```

---

### "Port 8000 already in use"

```bash
lsof -ti:8000 | xargs kill -9
```

Then restart.

---

### "tmux: command not found"

```bash
brew install tmux
```

Or use Option 2 (separate terminals).

---

### "cloudflared: command not found"

```bash
brew install cloudflare/cloudflare/cloudflared
```

---

### Tunnel URL doesn't work

- Wait 10-20 seconds (Cloudflare needs time)
- Check both servers are running
- Try accessing: `https://YOUR_TUNNEL_URL/docs`

---

## 📊 What to Expect

**During 10-minute walk:**
- GPS trail uploads: ~10 requests
- Progress updates: 1-3 requests
- Audio: 2-4 requests
- **Total:** ~15-20 requests

**Cloudflare limit:** ✅ Unlimited!

---

## 🎉 Success Criteria

You know it's working when:

1. ✅ App shows tours
2. ✅ GPS blue dot moves as you walk
3. ✅ Trail appears behind you
4. ✅ POIs auto-complete within 100m
5. ✅ Progress updates

---

## 📚 More Documentation

- **YOUR_TODO_LIST.md** - Complete checklist
- **QUICK_START_MOBILE_TEST.md** - Command reference
- **MOBILE_TESTING_SETUP.md** - Detailed troubleshooting
- **client_docs/FLUTTER_CONFIG_EXAMPLE.dart** - Flutter code

---

## 🚀 Quick Commands Summary

**Install (one-time):**
```bash
brew install cloudflare/cloudflare/cloudflared
brew install tmux  # optional
```

**Start testing:**
```bash
./start-mobile-test-tmux.sh  # Option 1
# OR
./scripts/start_api_server.sh  # Option 2 - Terminal 1
./scripts/start_tunnel.sh      # Option 2 - Terminal 2
```

**Copy tunnel URL → Update Flutter app → Build → Walk!**

---

**That's it! You're ready to test! 🎯**

Questions? Check **MOBILE_TESTING_SETUP.md** for details.
