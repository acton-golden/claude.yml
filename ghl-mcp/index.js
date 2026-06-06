#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

const GHL_API_KEY = process.env.GHL_API_KEY;
const GHL_LOCATION_ID = process.env.GHL_LOCATION_ID;
const GHL_BASE_URL = "https://services.leadconnectorhq.com";

if (!GHL_API_KEY) {
  console.error("Error: GHL_API_KEY environment variable is required");
  process.exit(1);
}

async function ghlRequest(method, path, body) {
  const headers = {
    Authorization: `Bearer ${GHL_API_KEY}`,
    "Content-Type": "application/json",
    Version: "2021-07-28",
  };

  const res = await fetch(`${GHL_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`GHL API error ${res.status}: ${text}`);
  }
  return text ? JSON.parse(text) : {};
}

const server = new Server(
  { name: "ghl-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "ghl_get_contacts",
      description: "Search and list contacts in GoHighLevel",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query (name, email, phone)" },
          limit: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "ghl_create_contact",
      description: "Create a new contact in GoHighLevel",
      inputSchema: {
        type: "object",
        required: ["firstName", "lastName"],
        properties: {
          firstName: { type: "string" },
          lastName: { type: "string" },
          email: { type: "string" },
          phone: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          customFields: { type: "object", description: "Custom field key-value pairs" },
          source: { type: "string" },
        },
      },
    },
    {
      name: "ghl_get_contact",
      description: "Get a specific contact by ID",
      inputSchema: {
        type: "object",
        required: ["contactId"],
        properties: {
          contactId: { type: "string" },
        },
      },
    },
    {
      name: "ghl_update_contact",
      description: "Update an existing contact",
      inputSchema: {
        type: "object",
        required: ["contactId"],
        properties: {
          contactId: { type: "string" },
          firstName: { type: "string" },
          lastName: { type: "string" },
          email: { type: "string" },
          phone: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
          customFields: { type: "object" },
        },
      },
    },
    {
      name: "ghl_get_opportunities",
      description: "List opportunities/deals in a pipeline",
      inputSchema: {
        type: "object",
        properties: {
          pipelineId: { type: "string" },
          stageId: { type: "string" },
          status: { type: "string", enum: ["open", "won", "lost", "abandoned"] },
          limit: { type: "number" },
        },
      },
    },
    {
      name: "ghl_create_opportunity",
      description: "Create a new opportunity/deal",
      inputSchema: {
        type: "object",
        required: ["title", "pipelineId", "pipelineStageId", "contactId"],
        properties: {
          title: { type: "string" },
          pipelineId: { type: "string" },
          pipelineStageId: { type: "string" },
          contactId: { type: "string" },
          monetaryValue: { type: "number" },
          status: { type: "string", enum: ["open", "won", "lost", "abandoned"] },
          assignedTo: { type: "string" },
        },
      },
    },
    {
      name: "ghl_get_pipelines",
      description: "List all pipelines in the location",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "ghl_send_message",
      description: "Send SMS or email to a contact",
      inputSchema: {
        type: "object",
        required: ["contactId", "type", "message"],
        properties: {
          contactId: { type: "string" },
          type: { type: "string", enum: ["SMS", "Email"] },
          message: { type: "string" },
          subject: { type: "string", description: "Email subject (required for Email type)" },
          html: { type: "string", description: "HTML body for emails" },
        },
      },
    },
    {
      name: "ghl_get_conversations",
      description: "List conversations for a contact or location",
      inputSchema: {
        type: "object",
        properties: {
          contactId: { type: "string" },
          limit: { type: "number" },
        },
      },
    },
    {
      name: "ghl_add_note",
      description: "Add a note to a contact",
      inputSchema: {
        type: "object",
        required: ["contactId", "body"],
        properties: {
          contactId: { type: "string" },
          body: { type: "string" },
          userId: { type: "string" },
        },
      },
    },
    {
      name: "ghl_add_tag",
      description: "Add tags to a contact",
      inputSchema: {
        type: "object",
        required: ["contactId", "tags"],
        properties: {
          contactId: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
        },
      },
    },
    {
      name: "ghl_remove_tag",
      description: "Remove tags from a contact",
      inputSchema: {
        type: "object",
        required: ["contactId", "tags"],
        properties: {
          contactId: { type: "string" },
          tags: { type: "array", items: { type: "string" } },
        },
      },
    },
    {
      name: "ghl_get_calendars",
      description: "List all calendars in the location",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "ghl_get_appointments",
      description: "List appointments/bookings",
      inputSchema: {
        type: "object",
        properties: {
          contactId: { type: "string" },
          calendarId: { type: "string" },
          startTime: { type: "string", description: "ISO 8601 datetime" },
          endTime: { type: "string", description: "ISO 8601 datetime" },
        },
      },
    },
    {
      name: "ghl_create_appointment",
      description: "Book an appointment for a contact",
      inputSchema: {
        type: "object",
        required: ["calendarId", "contactId", "startTime", "endTime"],
        properties: {
          calendarId: { type: "string" },
          contactId: { type: "string" },
          startTime: { type: "string", description: "ISO 8601 datetime" },
          endTime: { type: "string", description: "ISO 8601 datetime" },
          title: { type: "string" },
          appointmentStatus: {
            type: "string",
            enum: ["new", "confirmed", "cancelled", "showed", "noshow", "invalid"],
          },
        },
      },
    },
    {
      name: "ghl_get_location",
      description: "Get details about the current GHL sub-account/location",
      inputSchema: { type: "object", properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;
  const locId = args.locationId || GHL_LOCATION_ID;

  try {
    let result;

    switch (name) {
      case "ghl_get_contacts": {
        const params = new URLSearchParams({ locationId: locId });
        if (args.query) params.set("query", args.query);
        if (args.limit) params.set("limit", String(args.limit));
        result = await ghlRequest("GET", `/contacts/search?${params}`);
        break;
      }

      case "ghl_create_contact": {
        const { contactId: _, ...payload } = args;
        result = await ghlRequest("POST", "/contacts/", { ...payload, locationId: locId });
        break;
      }

      case "ghl_get_contact": {
        result = await ghlRequest("GET", `/contacts/${args.contactId}`);
        break;
      }

      case "ghl_update_contact": {
        const { contactId, ...payload } = args;
        result = await ghlRequest("PUT", `/contacts/${contactId}`, payload);
        break;
      }

      case "ghl_get_opportunities": {
        const params = new URLSearchParams({ location_id: locId });
        if (args.pipelineId) params.set("pipeline_id", args.pipelineId);
        if (args.stageId) params.set("pipeline_stage_id", args.stageId);
        if (args.status) params.set("status", args.status);
        if (args.limit) params.set("limit", String(args.limit));
        result = await ghlRequest("GET", `/opportunities/search?${params}`);
        break;
      }

      case "ghl_create_opportunity": {
        result = await ghlRequest("POST", "/opportunities/", args);
        break;
      }

      case "ghl_get_pipelines": {
        result = await ghlRequest("GET", `/opportunities/pipelines?locationId=${locId}`);
        break;
      }

      case "ghl_send_message": {
        const { contactId, type, message, subject, html } = args;
        const payload = { type, message };
        if (subject) payload.subject = subject;
        if (html) payload.html = html;
        result = await ghlRequest("POST", `/conversations/messages/outbound`, {
          contactId,
          locationId: locId,
          ...payload,
        });
        break;
      }

      case "ghl_get_conversations": {
        const params = new URLSearchParams({ locationId: locId });
        if (args.contactId) params.set("contactId", args.contactId);
        if (args.limit) params.set("limit", String(args.limit));
        result = await ghlRequest("GET", `/conversations/?${params}`);
        break;
      }

      case "ghl_add_note": {
        const { contactId, ...payload } = args;
        result = await ghlRequest("POST", `/contacts/${contactId}/notes`, payload);
        break;
      }

      case "ghl_add_tag": {
        result = await ghlRequest("POST", `/contacts/${args.contactId}/tags`, {
          tags: args.tags,
        });
        break;
      }

      case "ghl_remove_tag": {
        result = await ghlRequest("DELETE", `/contacts/${args.contactId}/tags`, {
          tags: args.tags,
        });
        break;
      }

      case "ghl_get_calendars": {
        result = await ghlRequest("GET", `/calendars/?locationId=${locId}`);
        break;
      }

      case "ghl_get_appointments": {
        const params = new URLSearchParams({ locationId: locId });
        if (args.contactId) params.set("contactId", args.contactId);
        if (args.calendarId) params.set("calendarId", args.calendarId);
        if (args.startTime) params.set("startTime", args.startTime);
        if (args.endTime) params.set("endTime", args.endTime);
        result = await ghlRequest("GET", `/calendars/events?${params}`);
        break;
      }

      case "ghl_create_appointment": {
        result = await ghlRequest("POST", "/calendars/events/appointments", {
          locationId: locId,
          ...args,
        });
        break;
      }

      case "ghl_get_location": {
        result = await ghlRequest("GET", `/locations/${locId}`);
        break;
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
