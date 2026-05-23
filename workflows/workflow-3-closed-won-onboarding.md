# Workflow 3: Closed Won Onboarding

**Trigger:** Tag Added → `closed won`

---

## Steps

### Trigger
- Action: Tag Added
- Tag: `closed won`

### Step 1 — Send SMS (to contact)
```
Hi {{contact.firstName}}! 🎉 You're officially a Velos client — welcome to the family!
Payment confirmed. Your KINDRA unit is being personalized right now.
Your Human Agent will be in touch within 1 hour. — The Velos Team
```

### Step 2 — Send SMS (to Jeriah: +1 916-329-5997)
```
🏆 CLOSED WON — New Velos Client!
{{contact.firstName}} {{contact.lastName}}
Phone: {{contact.phone}}
Email: {{contact.email}}
Action: Assign HA + send intro within 1 hour.
```

### Step 3 — Create Task
- Assigned to: jeriah@velos.com
- Title: `Assign Human Agent to {{contact.firstName}} — new Closed Won`
- Due: 1 hour

### Step 4 — Create Opportunity
- Pipeline: Sales (`hTtq3qhs2hEUGeQ0n0rg`)
- Stage: won (`90bf4aaf-43f6-49dc-8499-fc234f45d467`)
- Name: `{{contact.firstName}} {{contact.lastName}} — KINDRA Unit`
- Contact: `{{contact.id}}`
- Status: won

### Step 5a — Add Tag
- Tag: `Active Client`

### Step 5b — Add Tag
- Tag: `Pending HA Assignment`

### Step 5c — Update Custom Field
- Field: Client Status
- Value: `Active — Onboarding`

### Step 6 — Wait
- 1 hour

### Step 7 — Send SMS (to contact)
```
Hi {{contact.firstName}}! This is Jeriah — your dedicated Velos Human Agent.
I'm your direct point of contact for everything. No ticket systems, no hold queues — just me.
I'll oversee your KINDRA setup personally. Reply here anytime.
Let's build something great! 🚀
```

### Step 8a — Update Custom Field
- Field: Human Agent Assigned
- Value: `Jeriah Broker`

### Step 8b — Update Custom Field
- Field: Client Status
- Value: `Active — HA Assigned`

### Step 9a — Remove Tag
- Tag: `Pending HA Assignment`

### Step 9b — Add Tag
- Tag: `HA Assigned`

### Step 10 — Wait
- 24 hours

### Step 11 — Send SMS (to contact)
```
Hey {{contact.firstName}}! ✨ Just checking in — how's everything feeling so far?
KINDRA is live and ready. Any questions? Reply here and I'll handle it personally. — Jeriah
```

### Step 12 — Wait
- 144 hours (6 days) — total = 7 days from close

### Step 13 — Send SMS (to contact)
```
Hi {{contact.firstName}}! It's been a week since KINDRA went live for you 🎉
How's she performing? Any wins?
If you know another business owner drowning in missed calls — send them our way.
Your referral means everything to us. — The Velos Team
```

### Step 14 — Create Task
- Assigned to: jeriah@velos.com
- Title: `7-Day review — {{contact.firstName}}'s KINDRA performance + referral ask`
- Due: immediately
