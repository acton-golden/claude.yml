#!/bin/bash
# ============================================================
#  Setup cron job to run vps_status.sh every 10 minutes
#  Run this once on your VPS as root
# ============================================================

SCRIPT_DIR="/opt/vps-monitor"
SCRIPT_FILE="$SCRIPT_DIR/vps_status.sh"
ENV_FILE="$SCRIPT_DIR/.env"

echo "📦 Setting up VPS Monitor..."

# Create directory
mkdir -p "$SCRIPT_DIR"

# Copy script
cp "$(dirname "$0")/vps_status.sh" "$SCRIPT_FILE"
chmod +x "$SCRIPT_FILE"

# Create env file if not exists
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<EOF
# Telegram credentials — fill these in!
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
CHAT_ID=YOUR_CHAT_ID_HERE
EOF
  echo "📝 Created $ENV_FILE — please edit it with your credentials."
fi

# Wrapper script that loads env vars
cat > "$SCRIPT_DIR/run.sh" <<'WRAPPER'
#!/bin/bash
set -a
source /opt/vps-monitor/.env
set +a
exec /opt/vps-monitor/vps_status.sh
WRAPPER
chmod +x "$SCRIPT_DIR/run.sh"

# Add cron job (every 10 minutes)
CRON_LINE="*/10 * * * * /opt/vps-monitor/run.sh >> /var/log/vps-monitor.log 2>&1"

if crontab -l 2>/dev/null | grep -q "vps-monitor"; then
  echo "⏩ Cron job already exists, skipping."
else
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
  echo "✅ Cron job added: every 10 minutes"
fi

echo ""
echo "═══════════════════════════════════════"
echo "  SETUP COMPLETE"
echo "═══════════════════════════════════════"
echo "  1. Edit credentials:  nano $ENV_FILE"
echo "  2. Test now:          $SCRIPT_DIR/run.sh"
echo "  3. View logs:         tail -f /var/log/vps-monitor.log"
echo "  4. Remove cron:       crontab -e"
echo "═══════════════════════════════════════"
