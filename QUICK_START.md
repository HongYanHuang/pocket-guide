# Quick Start Guide

## Starting the Server

### From anywhere (even inside backstage):
```bash
../start_server.sh          # if in backstage/
./start_server.sh           # if in project root
~/Github/pocket-guide/start_server.sh  # absolute path
```

### Manual method (your original way):
```bash
# From project root
source pocket-guide-3.11/bin/activate
python src/api_server.py
```

## Starting the Backstage

```bash
cd backstage
npm run dev
```

Then open: http://localhost:5173

## Full Workflow

**Terminal 1 - API Server:**
```bash
cd ~/Github/pocket-guide
./start_server.sh
# Server runs on http://localhost:8000
```

**Terminal 2 - Backstage Frontend:**
```bash
cd ~/Github/pocket-guide/backstage
npm run dev
# Frontend runs on http://localhost:5173
```

## Quick Commands

```bash
# Kill server on port 8000
lsof -ti:8000 | xargs kill -9

# Check if server is running
curl http://localhost:8000/docs

# View API documentation
open http://localhost:8000/docs
```

## Common Issues

### "ModuleNotFoundError: No module named 'jwt'"
→ You're using the wrong virtual environment
→ **Fix:** Use `./start_server.sh` instead of manual commands

### "Port 8000 already in use"
→ Server is already running
→ **Fix:** `lsof -ti:8000 | xargs kill -9`

### "Virtual environment not found"
→ Script can't find `pocket-guide-3.11/`
→ **Fix:** Make sure you're in the project root or use absolute path

## Status

✅ API Server: http://localhost:8000
✅ API Docs: http://localhost:8000/docs
✅ Backstage: http://localhost:5173
✅ Auth Backend: Ready (login UI optional)
