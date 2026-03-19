# Development Commands Cheatsheet

## Starting Development Environment

### Option 1: tmux (Recommended - Best Experience) 🎯

Starts both backend and frontend in a split terminal:

```bash
./start-dev-tmux.sh
```

**Features:**
- ✅ Backend on left pane, Frontend on right pane
- ✅ Both servers visible at once
- ✅ Auto-attaches to tmux session
- ✅ Can detach and reattach anytime

**Tmux Commands (once inside):**
- `Ctrl+b` then `→` or `←` - Switch between panes
- `Ctrl+b` then `d` - Detach (servers keep running in background)
- `Ctrl+c` in both panes - Stop servers
- `exit` in both panes - Exit tmux

**Reattach later:**
```bash
tmux attach -t pocket-guide
```

**Kill session:**
```bash
tmux kill-session -t pocket-guide
```

---

### Option 2: Background Processes

Starts both in background, you see a single terminal with logs:

```bash
./start-dev.sh
```

**Features:**
- ✅ Simple start with one command
- ✅ Press Ctrl+C to stop both servers
- ❌ Can't see both server logs at once

---

### Option 3: Manual (Separate Terminals)

**Terminal 1 - Backend:**
```bash
source pocket-guide-3.11/bin/activate
python src/api_server.py
```

**Terminal 2 - Frontend:**
```bash
cd backstage
npm run dev
```

**Features:**
- ✅ Full control over each server
- ✅ Can restart independently
- ❌ Requires managing two terminal windows

---

### Option 4: Just the Server

If you only need the backend API:

```bash
./start_server.sh
```

---

## Quick Stop Commands

```bash
# Kill backend (port 8000)
lsof -ti:8000 | xargs kill -9

# Kill frontend (port 5173)
lsof -ti:5173 | xargs kill -9

# Kill both
lsof -ti:8000,5173 | xargs kill -9

# Kill tmux session
tmux kill-session -t pocket-guide
```

---

## URLs

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'jwt'"

→ Scripts are now fixed to use `pocket-guide-3.11` venv
→ If still happening, manually activate: `source pocket-guide-3.11/bin/activate`

### "Port already in use"

```bash
# Kill whatever's on that port
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

### "tmux session already exists"

```bash
# Reattach to existing session
tmux attach -t pocket-guide

# Or kill it and start fresh
tmux kill-session -t pocket-guide
./start-dev-tmux.sh
```

### "tmux not installed"

```bash
# Install tmux
brew install tmux

# Or use non-tmux version
./start-dev.sh
```

---

## Recommended Workflow

**Daily Development:**
1. `./start-dev-tmux.sh` - Start everything in tmux
2. Code your changes
3. `Ctrl+b` then `d` - Detach when you need terminal
4. `tmux attach -t pocket-guide` - Reattach when needed
5. `Ctrl+c` in both panes when done for the day

**Quick API Testing:**
1. `./start_server.sh` - Just the backend
2. Test with curl or Postman
3. `Ctrl+c` to stop

---

## Authentication Status

✅ Backend OAuth ready (PyJWT, session management)
⏳ Frontend login UI (not required yet)
✅ Can use backstage without authentication

---

## All Scripts Reference

| Script | Purpose |
|--------|---------|
| `./start-dev-tmux.sh` | Start both in tmux (split screen) |
| `./start-dev.sh` | Start both in background |
| `./start_server.sh` | Start backend only |
| `./stop-dev.sh` | Stop all development servers |
| `./dev-aliases.sh` | Load development aliases |
| `./setup.sh` | Initial project setup |
