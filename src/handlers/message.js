const ghl = require('../services/ghl');
const { ask } = require('../services/claude');

const SYSTEM_PROMPT = `You are KINDRA, an AI assistant for Velos — a company that helps businesses eliminate missed calls and automate customer communication.

You are responding to an inbound SMS from a lead or client. Be warm, helpful, and concise (under 160 characters when possible).

Rules:
- If they say RESCHEDULE, tell them to call +1 (833) 379-1600 or visit the booking link.
- If they say YES (after a no-show), send them the booking link.
- If they ask about pricing or services, keep it brief and tell Jeriah will follow up.
- Never make up details. Never promise specific prices.
- Sign messages as "— The Velos Team" unless it feels unnatural.`;

async function handleInboundMessage(payload) {
  const { contact, message } = payload;
  const contactId = contact.id;
  const phone = contact.phone;
  const firstName = contact.firstName;
  const body = message?.body || '';

  if (!body.trim()) return;

  const userContext = `Contact name: ${firstName}
Inbound message: "${body}"`;

  const reply = await ask(SYSTEM_PROMPT, userContext);

  await ghl.sendSMS(contactId, phone, reply);

  console.log(`[message] Replied to ${firstName} (${phone}): ${reply}`);
}

module.exports = { handleInboundMessage };
