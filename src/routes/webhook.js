const express = require('express');
const { handleAppointmentCreated, handleAppointmentStatusChanged } = require('../handlers/appointment');
const { handleTagAdded } = require('../handlers/tagAdded');
const { handleInboundMessage } = require('../handlers/message');

const router = express.Router();

router.post('/', async (req, res) => {
  const payload = req.body;
  const event = payload?.type || payload?.event;

  console.log(`[webhook] Received event: ${event}`);

  res.sendStatus(200);

  try {
    switch (event) {
      case 'AppointmentCreate':
      case 'appointment_created':
        await handleAppointmentCreated(payload);
        break;

      case 'AppointmentStatusChanged':
      case 'appointment_status_changed':
        await handleAppointmentStatusChanged(payload);
        break;

      case 'ContactTagAdded':
      case 'contact_tag_added':
        await handleTagAdded(payload);
        break;

      case 'InboundMessage':
      case 'inbound_message':
        await handleInboundMessage(payload);
        break;

      default:
        console.log(`[webhook] Unhandled event type: ${event}`);
    }
  } catch (err) {
    console.error(`[webhook] Error handling ${event}:`, err.message);
  }
});

module.exports = router;
