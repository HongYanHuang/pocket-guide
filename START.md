# Starting Pocket Guide Development

## Quick Start

```bash
./start-dev-tmux.sh
```

That's it! This starts both backend and frontend in a split tmux terminal.

---

## What You'll See

```
┌─────────────────────────────────┬─────────────────────────────────┐
│ 📡 Backend (Python 3.11)        │ 🎨 Frontend (Vue + Vite)        │
│ http://localhost:8000           │ http://localhost:5173           │
│                                 │                                 │
│ (pocket-guide-3.11)             │ $ npm run dev                   │
│ INFO: Uvicorn running...        │ VITE ready in 500ms...          │
└─────────────────────────────────┴─────────────────────────────────┘
```

**Wait ~10 seconds** for both servers to fully start.

---

## Tmux Basics

**Switch between panes:**
- `Ctrl+b` then press `→` (right arrow) or `←` (left arrow)

**Detach (servers keep running):**
- `Ctrl+b` then press `d`

**Reattach later:**
```bash
tmux attach -t pocket-guide
```

**Stop everything:**
- `Ctrl+c` in both panes (left and right)
- Then type `exit` in both panes

**Kill session completely:**
```bash
tmux kill-session -t pocket-guide
```

---

## URLs

- **Backstage UI**: http://localhost:5173
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Troubleshooting

### "Session already exists"

```bash
# Option 1: Reattach to existing session
tmux attach -t pocket-guide

# Option 2: Kill and restart
tmux kill-session -t pocket-guide
./start-dev-tmux.sh
```

### "tmux not installed"

```bash
brew install tmux
```

### Backend shows "ModuleNotFoundError"

The script automatically activates `pocket-guide-3.11` virtual environment. If you still see this:

```bash
# Reinstall dependencies
source pocket-guide-3.11/bin/activate
pip install -r requirements.txt
```

### Frontend shows "Cannot find package.json"

The script automatically `cd`s into the `backstage` directory. If you still see this, check that `backstage/package.json` exists:

```bash
ls -la backstage/package.json
```

### Port already in use

```bash
# Kill any process on ports 8000 or 5173
lsof -ti:8000,5173 | xargs kill -9

# Then restart
./start-dev-tmux.sh
```

### Servers don't start / panes are empty

Sometimes tmux needs a moment. Try:

1. Wait 10-15 seconds after running the script
2. Check each pane with `Ctrl+b` then `→` or `←`
3. If still not working:
   ```bash
   tmux kill-session -t pocket-guide
   ./start-dev-tmux.sh
   ```

---

## First Time Setup

If this is your first time running the project:

1. **Install tmux**
   ```bash
   brew install tmux
   ```

2. **Install backend dependencies**
   ```bash
   source pocket-guide-3.11/bin/activate
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd backstage
   npm install
   cd ..
   ```

4. **Start development**
   ```bash
   ./start-dev-tmux.sh
   ```

---

## Notes

- The backend uses **Python 3.11** (virtual environment: `pocket-guide-3.11`)
- The frontend uses **Vue 3 + Vite**
- Both servers auto-reload on file changes
- Authentication is **optional** - backstage works without login
- It takes ~10 seconds for both servers to be fully ready

---

## Common Issues Fixed

✅ **Backend**: Uses absolute path for venv activation
✅ **Frontend**: Uses absolute path `$PWD/backstage`
✅ **Commands**: Uses `.` instead of `source` (works in bash and zsh)
✅ **Timing**: Added sleep delays to let commands complete

If you still have issues, check that you're running from the project root directory!
