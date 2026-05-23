# Workflow 4: Daily Digest — Jeriah Morning Brief

**Trigger:** Time-Based → Every day at 8:00 AM Pacific/Honolulu

---

## Steps

### Trigger
- Action: Time-Based
- Schedule: Daily at 08:00
- Timezone: Pacific/Honolulu

### Step 1 — Send Email
- To: jasonstermer@jeriahbroker.com
- Subject: `☀️ KINDRA Daily Brief — {{today's date}}`

**Body:**
```
Hi Jeriah,

🗓 DEMOS SCHEDULED TODAY
{{demos_today || "No demos today — great day to follow up on Nurture leads."}}

✅ DEMOS ATTENDED YESTERDAY
{{demos_attended_yesterday || "No demos attended yesterday."}}

🆕 NEW CONTACTS (Last 24 Hours)
{{new_contacts || "No new contacts in the last 24 hours."}}

📌 OPEN FOLLOW-UP TASKS
{{open_tasks || "No open tasks. You're all caught up! 🌟"}}

💧 PIPELINE SNAPSHOT
Nurture stage: {{nurture_count}}
Demo Booked stage: {{demo_booked_count}}

🚨 OVERNIGHT ESCALATIONS
{{overnight_escalations || "No overnight escalations. ✔️"}}

─────────────────────────────
KINDRA worked through the night so you didn't have to.
Let's close some deals today. 🚀
— KINDRA by Velos
```

### Step 2 — IF/ELSE
- Condition: Contact → Tags **contains** `after hours — hold`

#### → IF TRUE
- Move Opportunity → Stage: demo booked (`d78336c8-9368-451d-baad-166ffcd6a3b4`)
- Send SMS to Jeriah (+1 916-329-5997):
```
☀️ Good morning! Overnight KINDRA call —
{{contact.firstName}} {{contact.lastName}}
{{contact.phone}}
Outcome: {{contact.tags}}
Summary: {{voiceAI.callSummary}}
```
- Remove Tag: `after hours — hold`

---

## ⚠️ Template Variable Warning

The following variables in the email body are **NOT native GHL variables** and will not auto-populate:

| Variable | What it needs |
|----------|--------------|
| `{{demos_today}}` | GHL Reporting API or custom webhook |
| `{{demos_attended_yesterday}}` | GHL Reporting API or custom webhook |
| `{{new_contacts}}` | GHL Reporting API or custom webhook |
| `{{open_tasks}}` | GHL Reporting API or custom webhook |
| `{{nurture_count}}` | GHL Reporting API or custom webhook |
| `{{demo_booked_count}}` | GHL Reporting API or custom webhook |
| `{{overnight_escalations}}` | Based on KINDRA/voiceAI data |

**Options:**
1. **Simple (static):** Build the workflow with placeholder text now and accept it won't have live counts until you wire up the API.
2. **Dynamic (webhook):** Add a webhook step before the email that calls your dashboard API, then use the response values to populate the email.
