#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing GHL MCP server dependencies..."
cd "$(dirname "$0")"
npm install

echo ""
echo "==> Setup complete."
echo ""
echo "Required environment variables:"
echo "  GHL_API_KEY      — Your GoHighLevel API key or OAuth access token"
echo "  GHL_LOCATION_ID  — Your GHL sub-account/location ID"
echo ""
echo "To start the MCP server manually:"
echo "  GHL_API_KEY=<key> GHL_LOCATION_ID=<id> node ghl-mcp/index.js"
echo ""
echo "Claude Code will start it automatically via .claude/settings.json."
echo "Set the env vars in your shell profile or pass them when launching Claude Code."
