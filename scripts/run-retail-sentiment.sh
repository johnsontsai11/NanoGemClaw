#!/bin/bash
# Host-side wrapper for retail-sentiment skill
# Runs outside container with direct localhost PostgreSQL access

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_DIR="$PROJECT_ROOT/container/skills/retail-sentiment"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -E '^POSTGRES_' "$PROJECT_ROOT/.env" | xargs)
fi

# Ensure Python dependencies are installed
if [ ! -d "$SKILL_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$SKILL_DIR/venv"
    source "$SKILL_DIR/venv/bin/activate"
    pip install psycopg2-binary matplotlib pandas numpy requests
else
    source "$SKILL_DIR/venv/bin/activate"
fi

# Run the skill
cd "$SKILL_DIR"
python3 main.py

# Deactivate venv
deactivate
