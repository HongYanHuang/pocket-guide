# 🚀 Quick Start - Mobile Testing (30 seconds)

## First Time Setup

```bash
# 1. Install Cloudflare tunnel (one-time)
brew install cloudflare/cloudflare/cloudflared
```

---

## Every Time You Test

### Step 1: Start API Server (Terminal 1)

```bash
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_api_server.sh
```

**✅ Leave this terminal open**

---

### Step 2: Start Tunnel (Terminal 2)

```bash
cd /Users/huanghongyan/Github/pocket-guide
./scripts/start_tunnel.sh
```

**📋 COPY THE URL** that appears (looks like: `https://abc-xyz-123.trycloudflare.com`)

**✅ Leave this terminal open**

---

### Step 3: Update Flutter App

**Edit your API config file:**

```dart
final String baseUrl = 'https://YOUR_TUNNEL_URL_HERE';  // Paste the URL from Step 2
```

**Save the file**

---

### Step 4: Build & Install on iPhone

```bash
# Connect iPhone via USB
cd /path/to/your/flutter/app
flutter run --release
```

---

### Step 5: Test & Walk! 🚶‍♂️

1. Open app on iPhone
2. Login (Google OAuth)
3. Start a tour
4. Go walk!

---

## Stop Everything

**Both Terminals:** Press `Ctrl+C`

---

## Full Documentation

See [MOBILE_TESTING_SETUP.md](./MOBILE_TESTING_SETUP.md) for detailed instructions and troubleshooting.

---

## Troubleshooting One-Liners

**Port 8000 in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

**Check if tunnel is working:**
```bash
curl https://YOUR_TUNNEL_URL/docs
```

**Check API server status:**
```bash
lsof -i:8000
```

---

## API Endpoints to Test

**Progress tracking:**
- `POST /tours/{tour_id}/progress` - Mark POI complete
- `GET /tours/{tour_id}/progress` - Get progress

**GPS trail:**
- `POST /tours/{tour_id}/trail` - Upload trail points
- `GET /tours/{tour_id}/trail` - Get trail

---

## That's It! 🎉

Two commands, copy one URL, update Flutter app, and you're ready to test!
