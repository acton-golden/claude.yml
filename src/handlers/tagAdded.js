const ghl = require('../services/ghl');

const PIPELINE_ID = 'hTtq3qhs2hEUGeQ0n0rg';
const STAGE_WON = '90bf4aaf-43f6-49dc-8499-fc234f45d467';
const STAGE_NURTURE = '99eaa4a6-dd30-4945-b659-b8c80015c299';

async function handleTagAdded(payload) {
  const { contact, tag } = payload;
  const contactId = contact.id;
  const phone = contact.phone;
  const firstName = contact.firstName;
  const lastName = contact.lastName;
  const email = contact.email;

  if (tag === 'closed won') {
    await Promise.all([
      ghl.sendSMS(
        contactId,
        phone,
        `Hi ${firstName}! 🎉 You're officially a Velos client — welcome to the family! Payment confirmed. Your KINDRA unit is being personalized right now. Your Human Agent will be in touch within 1 hour. — The Velos Team`
      ),
      ghl.sendSMS(
        contactId,
        process.env.JERIAH_PHONE,
        `🏆 CLOSED WON — New Velos Client!\n${firstName} ${lastName}\nPhone: ${phone}\nEmail: ${email}\nAction: Assign HA + send intro within 1 hour.`
      ),
      ghl.createTask(
        contactId,
        `Assign Human Agent to ${firstName} — new Closed Won`,
        process.env.JERIAH_EMAIL,
        new Date(Date.now() + 1 * 60 * 60 * 1000).toISOString()
      ),
      ghl.createOpportunity(
        contactId,
        `${firstName} ${lastName} — KINDRA Unit`,
        PIPELINE_ID,
        STAGE_WON,
        'won'
      ),
      ghl.addTag(contactId, 'Active Client'),
      ghl.addTag(contactId, 'Pending HA Assignment'),
      ghl.updateCustomField(contactId, 'client_status', 'Active — Onboarding'),
    ]);

    console.log(`[tag] Closed Won onboarding triggered for ${firstName} ${lastName}`);
  }

  if (tag === 'nurture') {
    await ghl.moveOpportunity(contact.opportunityId, STAGE_NURTURE);
    console.log(`[tag] Moved ${firstName} ${lastName} to Nurture stage`);
  }
}

module.exports = { handleTagAdded };
