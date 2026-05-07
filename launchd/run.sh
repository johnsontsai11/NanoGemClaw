#!/bin/bash
# NanoGemClaw Launchd Wrapper
# This script ensures the correct Node version and environment are used

# Navigate to project root
cd /Volumes/DevDisk/NanoGemClaw

# Set up environment
export PATH="/Users/johnsontsai/.nvm/versions/node/v24.15.0/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/johnsontsai"
export NODE_ENV=production

# Load .env if it exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Force Node.js to use IPv4 first (fixes ETIMEDOUT when IPv6 is broken locally)
export NODE_OPTIONS="--dns-result-order=ipv4first"

# Start the bot using tsx (via npm run dev)
# This ensures all TypeScript packages are resolved correctly
exec /Users/johnsontsai/.nvm/versions/node/v24.15.0/bin/npm run dev
