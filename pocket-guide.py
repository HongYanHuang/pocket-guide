#!/usr/bin/env python3
"""
Pocket Guide CLI - Clean wrapper without warnings
"""
import warnings
import sys
import os

# Suppress ALL warnings before any imports
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# Redirect stderr temporarily to suppress import-time errors
import io
original_stderr = sys.stderr
sys.stderr = io.StringIO()

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Import and run the CLI
    from cli import cli
finally:
    # Restore stderr
    sys.stderr = original_stderr

if __name__ == '__main__':
    cli(obj={})
