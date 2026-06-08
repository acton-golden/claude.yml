# Alyst by Velos — GHL + Voice AI Setup

## How it works

```
Inbound call → GHL LC Phone number
                    ↓
           Firebase /alystInbound  (returns TwiML)
                    ↓
           Alyst Voice AI (phone number)
                    ↓  (call ends)
           Firebase /alystCallStatus
                    ↓
           GHL contact gets call note logged
                    ↓
           GHL workflow fires on "call completed"
```

---

## Prerequisites
- Firebase CLI: `npm install -g firebase-tools`
- Firebase project at console.firebase.google.com
- GHL API key: GHL → Settings → Integrations → API Keys
- GHL Location ID: visible in sub-account URL (`/location/XXXXX/`)
- Alyst Voice AI phone number

---

## Step 1 — Set Firebase project ID

Edit `.firebaserc`, replace `YOUR_FIREBASE_PROJECT_ID` with your actual project ID.

---

## Step 2 — Set secrets

```bash
firebase functions:secrets:set GHL_API_KEY
firebase functions:secrets:set GHL_LOCATION_ID
firebase functions:secrets:set GHL_MCP_SECRET     # any random string
firebase functions:secrets:set VOICE_AI_NUMBER    # Alyst AI phone number e.g. +15551234567
```

---

## Step 3 — Deploy

```bash
cd functions && npm install
cd .. && firebase deploy --only functions
```

Firebase will print four URLs like:
```
https://us-central1-YOUR_PROJECT.cloudfunctions.net/ghlMcp
https://us-central1-YOUR_PROJECT.cloudfunctions.net/alystInbound
https://us-central1-YOUR_PROJECT.cloudfunctions.net/alystCallStatus
```

---

## Step 4 — Wire GHL LC Phone to the inbound webhook

1. In GHL → **Settings → Phone Numbers**
2. Click your inbound number → **Edit**
3. Set **Inbound Webhook URL** to:
   ```
   https://us-central1-YOUR_PROJECT.cloudfunctions.net/alystInbound
   ```
4. Save

Now every inbound call to that GHL number will route to Alyst.

---

## Step 5 — Set up GHL post-call workflow

1. GHL → **Automation → Workflows → New Workflow**
2. Trigger: **Inbound Webhook** or **Contact Activity → Call Completed**
3. Add actions as needed (tag contact, move pipeline, send follow-up SMS, etc.)

The call note that gets logged to the contact record (by `/alystCallStatus`) will
include call status, duration, SID, and recording URL — use these as conditions
in your workflow.

---

## Step 6 — GitHub secrets (for CI)

In GitHub repo → Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter key |
| `GHL_MCP_URL` | `https://us-central1-YOUR_PROJECT.cloudfunctions.net/ghlMcp` |
| `GHL_MCP_SECRET` | Same value you set in step 2 |

---

## MCP tools available to Claude

| Tool | What it does |
|------|-------------|
| `list_conversations` | See all recent calls + SMS threads |
| `get_messages` | Read messages in a conversation |
| `send_sms` | Text a contact from GHL |
| `get_contact` | Look up a contact's full record |
| `search_contacts` | Find who called by name or number |
| `list_phone_numbers` | See your GHL phone numbers |
| `get_call_recordings` | Access call recordings |

---

## Connecting Claude Desktop / Claude Code to the MCP server

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ghl-phone": {
      "type": "http",
      "url": "https://us-central1-YOUR_PROJECT.cloudfunctions.net/ghlMcp",
      "headers": {
        "Authorization": "Bearer YOUR_GHL_MCP_SECRET"
      }
    }
  }
}
```
