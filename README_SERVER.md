# Server Startup Guide

## Quick Start

### Option 1: Using the startup script (Recommended)
```bash
./start_server.sh
```

### Option 2: Manual startup
```bash
# Activate the correct virtual environment
source pocket-guide-3.11/bin/activate

# Start the server
python src/api_server.py
```

## Important Notes

⚠️ **Always use `pocket-guide-3.11` virtual environment**, not `venv`!

The `venv` directory is old and doesn't have the authentication dependencies (PyJWT, etc.)

## Verifying the Server

After starting, check:
- Server running: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: `curl http://localhost:8000/cities`

## Troubleshooting

### "ModuleNotFoundError: No module named 'jwt'"

This means you're using the wrong virtual environment.

**Fix:**
```bash
# Deactivate current environment
deactivate

# Activate the correct one
source pocket-guide-3.11/bin/activate

# Verify Python version (should be 3.11.x)
python --version

# Start server
python src/api_server.py
```

### "Port 8000 already in use"

**Fix:**
```bash
# Kill existing server
lsof -ti:8000 | xargs kill -9

# Start new server
python src/api_server.py
```

### "Config file not found"

The server looks for `config.yaml` in the `src` directory. There should be a symlink:
```bash
# Check if symlink exists
ls -la src/config.yaml

# If missing, create it
cd src && ln -sf ../config.yaml config.yaml
```

## Frontend (Backstage)

Once the server is running on port 8000, start the frontend:

```bash
cd backstage
npm run dev
```

Then open http://localhost:5173 in your browser.

## Current Status

✅ Authentication system implemented (backend only)
✅ Server runs on http://localhost:8000
✅ API docs available at http://localhost:8000/docs
⏳ Frontend login UI (not yet implemented - authentication is optional)

You can use the backstage without logging in for now.
