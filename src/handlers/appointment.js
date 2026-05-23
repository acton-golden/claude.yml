const ghl = require('../services/ghl');

const PIPELINE_ID = 'hTtq3qhs2hEUGeQ0n0rg';
const STAGE_DEMO_BOOKED = 'd78336c8-9368-451d-baad-166ffcd6a3b4';
const DEMO_CALENDAR_ID = 'bk4Nk5uDE41tWaxkN3db';

async function handleAppointmentCreated(payload) {
  const { contact, appointment } = payload;
  if (appointment?.calendarId !== DEMO_CALENDAR_ID) return;

  const contactId = contact.id;
  const phone = contact.phone;
  const firstName = contact.firstName;
  const lastName = contact.lastName;
  const apptDate = appointment.startTime;

  await Promise.all([
    ghl.addTag(contactId, 'demo booked'),
    ghl.sendSMS(
      contactId,
      phone,
      `Hi ${firstName}! 📍 You're booked for your Velos demo!\nDate: ${apptDate}\nReply RESCHEDULE to change your time. See you soon! 🚀`
    ),
    ghl.sendSMS(
      contactId,
      process.env.JERIAH_PHONE,
      `🔥 NEW DEMO BOOKED\n${firstName} ${lastName}\n${phone}\n${apptDate}`
    ),
  ]);

  console.log(`[appointment] Demo booked for ${firstName} ${lastName} — tagged + SMS sent`);
}

async function handleAppointmentStatusChanged(payload) {
  const { contact, appointment } = payload;
  const contactId = contact.id;
  const phone = contact.phone;
  const firstName = contact.firstName;
  const lastName = contact.lastName;
  const status = appointment?.status;

  if (status === 'showed') {
    await Promise.all([
      ghl.sendSMS(
        contactId,
        phone,
        `${firstName}, thanks for joining your Velos demo today! 🌟 Jeriah will follow up shortly with next steps.`
      ),
      ghl.sendSMS(
        contactId,
        process.env.JERIAH_PHONE,
        `✅ DEMO ATTENDED — ${firstName} ${lastName}\nFollow up NOW to close.\nPhone: ${phone}`
      ),
      ghl.createTask(
        contactId,
        `Post-demo follow-up — ${firstName} — close or nurture`,
        process.env.JERIAH_EMAIL,
        new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
      ),
    ]);
  } else if (status === 'no_show') {
    await Promise.all([
      ghl.sendSMS(
        contactId,
        process.env.JERIAH_PHONE,
        `🚨 NO-SHOW — ${firstName} ${lastName} did not attend their demo.\nPhone: ${phone}`
      ),
      ghl.sendSMS(
        contactId,
        phone,
        `Hey ${firstName}, we missed you at your Velos demo today! No worries 😊 Want to reschedule? Reply YES or call ${process.env.VELOS_PHONE}`
      ),
    ]);
  }

  console.log(`[appointment] Status changed to ${status} for ${firstName} ${lastName}`);
}

module.exports = { handleAppointmentCreated, handleAppointmentStatusChanged };
