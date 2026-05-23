# Workflow 2: Demo Booked Lifecycle

**Trigger:** Appointment Created → Calendar: "Velos Demo — 15 min" (`bk4Nk5uDE41tWaxkN3db`)

---

## Steps

### Trigger
- Action: Appointment Created
- Calendar: Velos Demo — 15 min (`bk4Nk5uDE41tWaxkN3db`)

### Step 1a — Add Tag
- Tag: `demo booked`

### Step 1b — Move Opportunity
- Pipeline: Sales (`hTtq3qhs2hEUGeQ0n0rg`)
- Stage: demo booked (`d78336c8-9368-451d-baad-166ffcd6a3b4`)

### Step 2 — Send SMS (to contact)
```
Hi {{contact.firstName}}! 📍 You're booked for your Velos demo!
Date: {{appointment.date}} at {{appointment.time}}
[YOUR ZOOM/MEET/PHONE LINK]
Reply RESCHEDULE to change your time. See you soon! 🚀
```

### Step 3 — Send SMS (to Jeriah: +1 916-329-5997)
```
🔥 NEW DEMO BOOKED
{{contact.firstName}} {{contact.lastName}}
{{contact.phone}}
{{appointment.date}} at {{appointment.time}}
```

### Step 4 — Wait
- 24 hours **before** appointment

### Step 5 — Send SMS (to contact)
```
Hey {{contact.firstName}}! Your Velos demo is tomorrow at {{appointment.time}}.
💬 KINDRA is going to walk you through exactly how she eliminates missed calls and automates your chaos 24/7.
See you tomorrow! — The Velos Team
```

### Step 6 — Send SMS (to Jeriah: +1 916-329-5997)
```
🔔 24HR REMINDER — Demo tomorrow at {{appointment.time}}
{{contact.firstName}} {{contact.lastName}}
{{contact.phone}}
```

### Step 7 — Wait
- 1 hour **before** appointment

### Step 8 — Send SMS (to contact)
```
{{contact.firstName}}, your Velos demo starts in 1 hour! ⏰
[YOUR ZOOM/MEET/PHONE LINK]
KINDRA is ready — see you in 60 minutes!
```

### Step 9 — Wait
- 15 minutes **after** appointment

### Step 10 — IF/ELSE
- Condition: Appointment → Appointment Status **equals** `Showed`

#### → IF TRUE (Showed)

**Step 11 — Send SMS (to contact)**
```
{{contact.firstName}}, thanks for joining your Velos demo today! 🌟
Really great connecting. Jeriah will follow up shortly with next steps.
```

**Step 12 — Send SMS (to Jeriah: +1 916-329-5997)**
```
✅ DEMO ATTENDED — {{contact.firstName}} {{contact.lastName}}
Follow up NOW to close.
Phone: {{contact.phone}}
```

**Step 13 — Create Task**
- Assigned to: jeriah@velos.com
- Title: `Post-demo follow-up — {{contact.firstName}} — close or nurture`
- Due: 2 hours

**Step 14 — Wait**
- 2 hours

**Step 15 — IF/ELSE**
- Condition: Contact → Tags **contains** `closed won`

##### → IF TRUE (closed won)
- Trigger Workflow: "KINDRA — Closed Won Onboarding" (Workflow 3)

##### → ELSE IF (nurture tag)
- Condition: Contact → Tags **contains** `nurture`
- Add Tag: `nurture`
- Move Opportunity → Stage: nurture (`99eaa4a6-dd30-4945-b659-b8c80015c299`)

##### → ELSE (no tag)
- Send SMS to Jeriah (+1 916-329-5997):
```
⚠️ No outcome tagged yet for {{contact.firstName}} — update pipeline.
```

#### → IF FALSE (No-Show)

**Step 16 — Send SMS (to Jeriah: +1 916-329-5997)**
```
🚨 NO-SHOW — {{contact.firstName}} {{contact.lastName}} did not attend their demo at {{appointment.time}}
Phone: {{contact.phone}}
```

**Step 17 — Send SMS (to contact)**
```
Hey {{contact.firstName}}, we missed you at your Velos demo today! No worries at all 😊
Want to reschedule? Reply YES or call +1 (833) 379-1600 — KINDRA will get you sorted.
```

**Step 18 — Wait**
- 48 hours

**Step 19 — IF/ELSE**
- Condition: Appointment → Rescheduled **equals** `true`

##### → IF TRUE (rescheduled)
- Trigger Workflow: "KINDRA — Demo Booked Lifecycle" (re-enters itself / Workflow 2)

##### → ELSE (didn't reschedule)
- Step 19b — Add Tag: `No-Show — Nurture`
- Step 19c — Move Opportunity → Stage: nurture (`99eaa4a6-dd30-4945-b659-b8c80015c299`)
- Step 19d — Send SMS to Jeriah (+1 916-329-5997):
```
💧 {{contact.firstName}} no-showed and didn't reschedule. Moved to Nurture.
```
