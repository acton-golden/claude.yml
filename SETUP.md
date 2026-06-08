# GHL Phone MCP — Firebase Setup

## Prerequisites
- Firebase CLI: `npm install -g firebase-tools`
- Firebase project created at console.firebase.google.com
- GHL API key (Settings → Integrations → API Keys in GHL)
- GHL Location ID (visible in your GHL sub-account URL)

## 1. Set Firebase project

Edit `.firebaserc` and replace `YOUR_FIREBASE_PROJECT_ID` with your actual project ID.

## 2. Set secrets in Firebase

```bash
firebase functions:secrets:set GHL_API_KEY
firebase functions:secrets:set GHL_LOCATION_ID
firebase functions:secrets:set GHL_MCP_SECRET   # any random string you choose
```

## 3. Install dependencies and deploy

```bash
cd functions && npm install
cd .. && firebase deploy --only functions
```

After deploy, Firebase prints the function URL, e.g.:
```
https://us-central1-YOUR_PROJECT.cloudfunctions.net/ghlMcp
```

## 4. Add GitHub secrets

In your GitHub repo → Settings → Secrets → Actions, add:

| Secret | Value |
|--------|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter key |
| `GHL_MCP_URL` | Firebase function URL from step 3 |
| `GHL_MCP_SECRET` | The secret you set in step 2 |

## 5. Connect Claude Desktop / Claude Code

Add to your `claude_desktop_config.json` or `.claude/settings.json`:

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

## Available MCP tools

| Tool | What it does |
|------|-------------|
| `list_conversations` | See all recent calls + SMS threads |
| `get_messages` | Read messages in a conversation |
| `send_sms` | Text a contact from GHL |
| `get_contact` | Look up a contact's full record |
| `search_contacts` | Find who called by name or number |
| `list_phone_numbers` | See your GHL phone numbers |
| `get_call_recordings` | Access call recordings |
