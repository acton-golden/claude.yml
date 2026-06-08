const functions = require("firebase-functions");
const { McpServer } = require("@modelcontextprotocol/sdk/server/mcp.js");
const { StreamableHTTPServerTransport } = require("@modelcontextprotocol/sdk/server/streamableHttp.js");
const { z } = require("zod");
const ghl = require("./ghl");

// ── MCP server definition ────────────────────────────────────────────────────

function buildServer() {
  const server = new McpServer({
    name: "ghl-phone",
    version: "1.0.0",
  });

  const loc = () => process.env.GHL_LOCATION_ID;

  server.tool(
    "list_conversations",
    "List recent phone / SMS conversations in GoHighLevel.",
    {
      limit: z.number().min(1).max(100).default(20),
      query: z.string().optional().describe("Search by contact name or phone number"),
    },
    async ({ limit, query }) => {
      const convos = await ghl.listConversations({ locationId: loc(), limit, query });
      return { content: [{ type: "text", text: JSON.stringify(convos, null, 2) }] };
    }
  );

  server.tool(
    "get_messages",
    "Fetch the message/call history for a specific conversation.",
    {
      conversationId: z.string(),
      limit: z.number().default(20),
    },
    async ({ conversationId, limit }) => {
      const msgs = await ghl.getMessages(conversationId, limit);
      return { content: [{ type: "text", text: JSON.stringify(msgs, null, 2) }] };
    }
  );

  server.tool(
    "send_sms",
    "Send an SMS to a contact through GoHighLevel.",
    {
      contactId: z.string(),
      message: z.string(),
    },
    async ({ contactId, message }) => {
      const result = await ghl.sendSms({ locationId: loc(), contactId, message });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    "get_contact",
    "Get full contact details from GHL.",
    { contactId: z.string() },
    async ({ contactId }) => {
      const contact = await ghl.getContact(contactId);
      return { content: [{ type: "text", text: JSON.stringify(contact, null, 2) }] };
    }
  );

  server.tool(
    "search_contacts",
    "Search contacts by name or phone number.",
    {
      query: z.string(),
      limit: z.number().default(10),
    },
    async ({ query, limit }) => {
      const contacts = await ghl.searchContacts({ locationId: loc(), query, limit });
      return { content: [{ type: "text", text: JSON.stringify(contacts, null, 2) }] };
    }
  );

  server.tool(
    "list_phone_numbers",
    "List all GHL LC Phone numbers for this location.",
    {},
    async () => {
      const numbers = await ghl.listPhoneNumbers(loc());
      return { content: [{ type: "text", text: JSON.stringify(numbers, null, 2) }] };
    }
  );

  server.tool(
    "get_call_recordings",
    "Retrieve recent call recordings from GHL LC Phone.",
    {},
    async () => {
      const data = await ghl.getCallRecordings(loc());
      return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
    }
  );

  return server;
}

// ── MCP HTTP endpoint ────────────────────────────────────────────────────────

exports.ghlMcp = functions
  .runWith({ secrets: ["GHL_API_KEY", "GHL_LOCATION_ID", "GHL_MCP_SECRET"] })
  .https.onRequest(async (req, res) => {
    const secret = process.env.GHL_MCP_SECRET;
    if (secret) {
      const auth = req.headers.authorization ?? "";
      if (auth !== `Bearer ${secret}`) {
        res.status(401).json({ error: "Unauthorized" });
        return;
      }
    }
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    const server = buildServer();
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  });

// ── Alyst Voice AI inbound call bridge ──────────────────────────────────────
//
// GHL LC Phone webhook flow:
//   1. Inbound call hits GHL number
//   2. GHL posts to this /alystInbound endpoint
//   3. We return TwiML that dials the Alyst voice AI phone number
//   4. After the call, Twilio posts status to /alystCallStatus
//   5. We write a call note back to the GHL contact record

exports.alystInbound = functions
  .runWith({ secrets: ["VOICE_AI_NUMBER", "GHL_API_KEY", "GHL_LOCATION_ID"] })
  .https.onRequest(async (req, res) => {
    const voiceAiNumber = process.env.VOICE_AI_NUMBER;
    if (!voiceAiNumber) {
      res.status(500).send("<Response><Say>Configuration error: voice AI number not set.</Say></Response>");
      return;
    }

    // Build the callback URL for post-call status
    const statusUrl = `https://${req.hostname}/alystCallStatus`;

    const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Dial
    action="${statusUrl}"
    method="POST"
    record="record-from-answer-dual-channel"
    recordingStatusCallback="${statusUrl}"
    recordingStatusCallbackMethod="POST"
    timeout="30"
  >
    <Number statusCallbackEvent="completed" statusCallback="${statusUrl}">${voiceAiNumber}</Number>
  </Dial>
</Response>`;

    res.set("Content-Type", "text/xml");
    res.send(twiml);
  });

// ── Post-call status handler — logs call back to GHL ────────────────────────

exports.alystCallStatus = functions
  .runWith({ secrets: ["GHL_API_KEY", "GHL_LOCATION_ID"] })
  .https.onRequest(async (req, res) => {
    try {
      const {
        CallSid,
        CallStatus,
        CallDuration,
        From,
        To,
        RecordingUrl,
      } = req.body;

      // Find the GHL contact by the caller's phone number
      const callerNumber = From || "";
      const contacts = await ghl.searchContacts({
        locationId: process.env.GHL_LOCATION_ID,
        query: callerNumber,
        limit: 1,
      });

      if (contacts.length > 0) {
        const contact = contacts[0];
        // Post a call note to the contact's conversation
        await ghl.sendSms({
          locationId: process.env.GHL_LOCATION_ID,
          contactId: contact.id,
          // Internal note format — GHL stores this as a call activity
          message: `[Alyst Voice AI Call]\nStatus: ${CallStatus}\nDuration: ${CallDuration}s\nSID: ${CallSid}${RecordingUrl ? `\nRecording: ${RecordingUrl}` : ""}`,
        });
      }
    } catch (err) {
      // Log but don't fail — Twilio needs a 200 or it retries
      console.error("alystCallStatus error:", err.message);
    }

    res.status(200).send("OK");
  });
