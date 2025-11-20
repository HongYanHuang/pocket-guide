#!/bin/bash
# Setup script for Pocket Guide CLI

echo "🚀 Setting up Pocket Guide CLI..."

# Check Python version
python_version=$(python3 --version 2>&1 | sed -n 's/Python \([0-9]*\.[0-9]*\).*/\1/p')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi

echo "✓ Python version OK"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Create config if not exists
if [ ! -f "config.yaml" ]; then
    echo "Creating config.yaml from template..."
    cp config.example.yaml config.yaml
    echo "✓ Config file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit config.yaml and add your API keys!"
    echo "   nano config.yaml"
else
    echo "✓ Config file exists"
fi

# Create content directory
mkdir -p content
echo "✓ Content directory created"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml and add your API keys"
echo "2. Run: source venv/bin/activate"
echo "3. Try: python src/cli.py --help"
echo ""
echo "Quick start:"
echo "  python src/cli.py generate"
