#!/bin/bash
# Host-side wrapper for retail-sentiment skill
# Runs outside container with direct localhost PostgreSQL access

set -e

# Ensure unbuffered Python output for real-time logging
export PYTHONUNBUFFERED=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_DIR="$PROJECT_ROOT/container/skills/retail-sentiment"
VENV_DIR="/tmp/retail-sentiment-venv"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -E '^POSTGRES_' "$PROJECT_ROOT/.env" | xargs)
fi

# Ensure Python dependencies are installed (venv in /tmp to avoid repo clutter)
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment in /tmp..."
    python3 -m venv "$VENV_DIR" || {
        echo "❌ Failed to create virtual environment"
        exit 1
    }
    source "$VENV_DIR/bin/activate" || {
        echo "❌ Failed to activate virtual environment"
        exit 1
    }
    echo "Installing Python dependencies..."
    pip install --quiet psycopg2-binary matplotlib pandas numpy requests || {
        echo "❌ Failed to install dependencies"
        exit 1
    }
else
    source "$VENV_DIR/bin/activate" || {
        echo "❌ Failed to activate virtual environment"
        exit 1
    }
fi

# Run the skill
cd "$SKILL_DIR"
python3 main.py

# Deactivate venv
deactivate
