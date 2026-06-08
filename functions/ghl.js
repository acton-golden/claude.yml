const axios = require("axios");

const BASE = "https://services.leadconnectorhq.com";

function client() {
  const key = process.env.GHL_API_KEY;
  if (!key) throw new Error("GHL_API_KEY environment variable is not set");
  return axios.create({
    baseURL: BASE,
    headers: {
      Authorization: `Bearer ${key}`,
      Version: "2021-07-28",
      "Content-Type": "application/json",
    },
  });
}

async function listConversations({ locationId, limit = 20, query = "" }) {
  const params = { locationId, limit };
  if (query) params.query = query;
  const { data } = await client().get("/conversations/search", { params });
  return data.conversations ?? [];
}

async function getConversation(conversationId) {
  const { data } = await client().get(`/conversations/${conversationId}`);
  return data.conversation;
}

async function getMessages(conversationId, limit = 20) {
  const { data } = await client().get(`/conversations/${conversationId}/messages`, {
    params: { limit },
  });
  return data.messages ?? [];
}

async function sendSms({ locationId, contactId, message }) {
  const { data } = await client().post("/conversations/messages", {
    type: "SMS",
    locationId,
    contactId,
    message,
  });
  return data;
}

async function listPhoneNumbers(locationId) {
  const { data } = await client().get("/phone-numbers/", {
    params: { locationId },
  });
  return data.phoneNumbers ?? [];
}

async function getContact(contactId) {
  const { data } = await client().get(`/contacts/${contactId}`);
  return data.contact;
}

async function searchContacts({ locationId, query, limit = 20 }) {
  const { data } = await client().get("/contacts/search", {
    params: { locationId, query, limit },
  });
  return data.contacts ?? [];
}

async function getCallRecordings(locationId) {
  const { data } = await client().get("/conversations/messages/recording", {
    params: { locationId },
  });
  return data;
}

module.exports = {
  listConversations,
  getConversation,
  getMessages,
  sendSms,
  listPhoneNumbers,
  getContact,
  searchContacts,
  getCallRecordings,
};
