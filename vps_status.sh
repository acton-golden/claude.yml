#!/bin/bash
# ============================================================
#  VPS Status Check → Telegram Gateway
#  SSH: root@2.24.30.198
#  Usage:
#    export BOT_TOKEN="your_bot_token_here"
#    export CHAT_ID="your_chat_id_here"
#    bash vps_status.sh
# ============================================================

BOT_TOKEN="${BOT_TOKEN:-}"
CHAT_ID="${CHAT_ID:-}"

# ── Validate credentials ────────────────────────────────────
if [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]]; then
  echo "❌ ERROR: Set BOT_TOKEN and CHAT_ID environment variables first."
  echo "   export BOT_TOKEN='123456:ABC-DEF...'"
  echo "   export CHAT_ID='-100123456789'"
  exit 1
fi

TELEGRAM_URL="https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"

# ── Gather system info ──────────────────────────────────────
HOSTNAME=$(hostname)
PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org || echo "N/A")
UPTIME=$(uptime -p)
UPTIME_SINCE=$(uptime -s)

# CPU — /proc/stat is more reliable than top -bn1 across distros
CPU_IDLE1=$(awk '/^cpu /{print $5}' /proc/stat)
CPU_TOTAL1=$(awk '/^cpu /{t=0; for(i=2;i<=NF;i++) t+=$i; print t}' /proc/stat)
sleep 0.5
CPU_IDLE2=$(awk '/^cpu /{print $5}' /proc/stat)
CPU_TOTAL2=$(awk '/^cpu /{t=0; for(i=2;i<=NF;i++) t+=$i; print t}' /proc/stat)
CPU_USAGE=$(awk "BEGIN {
  idle=$CPU_IDLE2-$CPU_IDLE1
  total=$CPU_TOTAL2-$CPU_TOTAL1
  printf \"%.1f\", (total-idle)/total*100
}")
LOAD_AVG=$(awk '{print $1, $2, $3}' /proc/loadavg)
CPU_CORES=$(nproc)

# Memory
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_USED=$(free -m  | awk '/^Mem:/{print $3}')
MEM_FREE=$(free -m  | awk '/^Mem:/{print $4}')
MEM_PCT=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED/$MEM_TOTAL)*100}")

# Swap
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
SWAP_USED=$(free -m  | awk '/^Swap:/{print $3}')

# Disk (root)
DISK_TOTAL=$(df -h / | awk 'NR==2{print $2}')
DISK_USED=$(df -h  / | awk 'NR==2{print $3}')
DISK_FREE=$(df -h  / | awk 'NR==2{print $4}')
DISK_PCT=$(df /    | awk 'NR==2{print $5}')

# Network interfaces (non-loopback) — join with comma+space, handle missing ip cmd
NET_INFO=$(ip -brief addr 2>/dev/null | grep -v '^lo' | awk '{print $1": "$3}' | head -5 | paste -sd', ' || echo "N/A")

# Running services (active)
SERVICES_UP=$(systemctl list-units --type=service --state=running --no-legend | wc -l)

# Failed services
FAILED=$(systemctl list-units --type=service --state=failed --no-legend 2>/dev/null | wc -l)
FAILED_NAMES=$(systemctl list-units --type=service --state=failed --no-legend 2>/dev/null \
  | awk '{print "  ⚠️ "$1}' | head -5)
[[ -z "$FAILED_NAMES" ]] && FAILED_NAMES="  none"

# Last 3 logins
LAST_LOGINS=$(last -n 3 -F 2>/dev/null | head -3 | awk '{print "  "$0}')
[[ -z "$LAST_LOGINS" ]] && LAST_LOGINS="  no login data"

# Processes
PROC_TOTAL=$(ps aux | wc -l)

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

# ── Emoji helpers ───────────────────────────────────────────
# Fixed: pass value as arg directly into awk — no stdin pipe needed
pct_icon() {
  local v=${1/\%/}   # strip % if present
  awk -v v="$v" 'BEGIN{ if(v+0<70) print "🟢"; else if(v+0<90) print "🟡"; else print "🔴" }'
}

MEM_ICON=$(pct_icon "$MEM_PCT")
DISK_ICON=$(pct_icon "$DISK_PCT")
CPU_ICON=$(pct_icon "$CPU_USAGE")
FAIL_ICON=$([ "${FAILED:-0}" -eq 0 ] && echo "✅" || echo "🚨")

# ── Build message ───────────────────────────────────────────
MESSAGE="🖥️ *VPS STATUS REPORT*
\`\`\`
Host : ${HOSTNAME}
IP   : ${PUBLIC_IP}
Time : ${TIMESTAMP}
\`\`\`

⏱️ *Uptime*
• Since: \`${UPTIME_SINCE}\`
• ${UPTIME}

${CPU_ICON} *CPU*
• Usage : \`${CPU_USAGE}%\`  (${CPU_CORES} cores)
• Load  : \`${LOAD_AVG}\` (1m 5m 15m)

${MEM_ICON} *Memory*
• Used  : \`${MEM_USED} MB / ${MEM_TOTAL} MB\` (${MEM_PCT}%)
• Free  : \`${MEM_FREE} MB\`
• Swap  : \`${SWAP_USED} MB / ${SWAP_TOTAL} MB\`

${DISK_ICON} *Disk /*
• Used  : \`${DISK_USED} / ${DISK_TOTAL}\` (${DISK_PCT})
• Free  : \`${DISK_FREE}\`

🌐 *Network*
${NET_INFO}

⚙️ *Services*
• Running : \`${SERVICES_UP}\`
• Failed  : ${FAIL_ICON} \`${FAILED}\`
${FAILED_NAMES}

👥 *Recent Logins*
${LAST_LOGINS}

🔢 *Processes* : \`${PROC_TOTAL}\`"

# ── Send to Telegram ─────────────────────────────────────────
# Use --data-urlencode / form POST to avoid JSON escaping nightmares
RESPONSE=$(curl -s -X POST "$TELEGRAM_URL" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MESSAGE}" \
  --data-urlencode "parse_mode=Markdown" \
  --data-urlencode "disable_web_page_preview=true")

# ── Result ──────────────────────────────────────────────────
if echo "$RESPONSE" | grep -q '"ok":true'; then
  echo "✅ Status sent to Telegram successfully."
else
  echo "❌ Failed to send. Response:"
  echo "$RESPONSE"
  exit 1
fi
