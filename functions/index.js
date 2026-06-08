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

  // ── Tool: list recent conversations (calls + SMS) ─────────────────────────
  server.tool(
    "list_conversations",
    "List recent phone / SMS conversations in GoHighLevel. Use this to see which clients have reached out and may need follow-up.",
    {
      limit: z.number().min(1).max(100).default(20).describe("Max conversations to return"),
      query: z.string().optional().describe("Search by contact name or phone number"),
    },
    async ({ limit, query }) => {
      const convos = await ghl.listConversations({ locationId: loc(), limit, query });
      return {
        content: [{ type: "text", text: JSON.stringify(convos, null, 2) }],
      };
    }
  );

  // ── Tool: get messages in a conversation ──────────────────────────────────
  server.tool(
    "get_messages",
    "Fetch the message history (SMS + call notes) for a specific conversation.",
    {
      conversationId: z.string().describe("GHL conversation ID"),
      limit: z.number().default(20),
    },
    async ({ conversationId, limit }) => {
      const msgs = await ghl.getMessages(conversationId, limit);
      return {
        content: [{ type: "text", text: JSON.stringify(msgs, null, 2) }],
      };
    }
  );

  // ── Tool: send SMS ────────────────────────────────────────────────────────
  server.tool(
    "send_sms",
    "Send an SMS to a contact through GoHighLevel's phone system.",
    {
      contactId: z.string().describe("GHL contact ID"),
      message: z.string().describe("Text message body to send"),
    },
    async ({ contactId, message }) => {
      const result = await ghl.sendSms({ locationId: loc(), contactId, message });
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    }
  );

  // ── Tool: look up a contact ────────────────────────────────────────────────
  server.tool(
    "get_contact",
    "Get full contact details (name, phone, email, tags, pipeline stage) for a GHL contact.",
    {
      contactId: z.string().describe("GHL contact ID"),
    },
    async ({ contactId }) => {
      const contact = await ghl.getContact(contactId);
      return {
        content: [{ type: "text", text: JSON.stringify(contact, null, 2) }],
      };
    }
  );

  // ── Tool: search contacts ─────────────────────────────────────────────────
  server.tool(
    "search_contacts",
    "Search for contacts by name or phone number. Useful for finding who called or texted.",
    {
      query: z.string().describe("Name or phone number to search"),
      limit: z.number().default(10),
    },
    async ({ query, limit }) => {
      const contacts = await ghl.searchContacts({ locationId: loc(), query, limit });
      return {
        content: [{ type: "text", text: JSON.stringify(contacts, null, 2) }],
      };
    }
  );

  // ── Tool: list phone numbers ──────────────────────────────────────────────
  server.tool(
    "list_phone_numbers",
    "List all phone numbers configured in GHL for this location.",
    {},
    async () => {
      const numbers = await ghl.listPhoneNumbers(loc());
      return {
        content: [{ type: "text", text: JSON.stringify(numbers, null, 2) }],
      };
    }
  );

  // ── Tool: get call recordings ─────────────────────────────────────────────
  server.tool(
    "get_call_recordings",
    "Retrieve recent call recordings from GHL LC Phone so you can review missed or completed calls.",
    {},
    async () => {
      const data = await ghl.getCallRecordings(loc());
      return {
        content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  return server;
}

// ── Firebase HTTP function ───────────────────────────────────────────────────

exports.ghlMcp = functions
  .runWith({ secrets: ["GHL_API_KEY", "GHL_LOCATION_ID"] })
  .https.onRequest(async (req, res) => {
    // Simple bearer-token guard — set GHL_MCP_SECRET in Firebase secrets
    const secret = process.env.GHL_MCP_SECRET;
    if (secret) {
      const auth = req.headers.authorization ?? "";
      if (auth !== `Bearer ${secret}`) {
        res.status(401).json({ error: "Unauthorized" });
        return;
      }
    }

    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless
    });

    const server = buildServer();
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  });
