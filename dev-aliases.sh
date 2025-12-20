#!/bin/bash

# Pocket Guide - Development Aliases
# Source this file in your shell config to get convenient aliases
#
# Add to ~/.bashrc or ~/.zshrc:
#   source /path/to/pocket-guide/dev-aliases.sh

# Get the directory where this script is located
POCKET_GUIDE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Alias to start both servers
alias pg-start="cd $POCKET_GUIDE_DIR && ./start-dev.sh"

# Alias to stop both servers
alias pg-stop="cd $POCKET_GUIDE_DIR && ./stop-dev.sh"

# Alias to start backend only
alias pg-backend="cd $POCKET_GUIDE_DIR && source venv/bin/activate && python src/api_server.py"

# Alias to start frontend only
alias pg-frontend="cd $POCKET_GUIDE_DIR/backstage && npm run dev"

# Alias to activate venv
alias pg-venv="cd $POCKET_GUIDE_DIR && source venv/bin/activate"

# Alias to open API docs
alias pg-docs="open http://localhost:8000/docs"

# Alias to open frontend
alias pg-web="open http://localhost:5173"

echo "✅ Pocket Guide aliases loaded!"
echo "   pg-start    - Start both servers"
echo "   pg-stop     - Stop both servers"
echo "   pg-backend  - Start backend only"
echo "   pg-frontend - Start frontend only"
echo "   pg-venv     - Activate virtual environment"
echo "   pg-docs     - Open API docs in browser"
echo "   pg-web      - Open frontend in browser"
