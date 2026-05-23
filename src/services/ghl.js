const axios = require('axios');

const BASE = 'https://services.leadconnectorhq.com';
const LOCATION_ID = process.env.GHL_LOCATION_ID;

const api = axios.create({
  baseURL: BASE,
  headers: {
    Authorization: `Bearer ${process.env.GHL_API_KEY}`,
    Version: '2021-07-28',
    'Content-Type': 'application/json',
  },
});

const ghl = {
  async sendSMS(contactId, phone, message) {
    const res = await api.post('/conversations/messages', {
      type: 'SMS',
      contactId,
      message,
      toNumber: phone,
      fromNumber: process.env.VELOS_PHONE,
    });
    return res.data;
  },

  async addTag(contactId, tag) {
    const res = await api.post(`/contacts/${contactId}/tags`, { tags: [tag] });
    return res.data;
  },

  async removeTag(contactId, tag) {
    const res = await api.delete(`/contacts/${contactId}/tags`, { data: { tags: [tag] } });
    return res.data;
  },

  async moveOpportunity(opportunityId, stageId) {
    const res = await api.put(`/opportunities/${opportunityId}`, { stageId });
    return res.data;
  },

  async createOpportunity(contactId, name, pipelineId, stageId, status = 'open') {
    const res = await api.post('/opportunities/', {
      pipelineId,
      locationId: LOCATION_ID,
      name,
      pipelineStageId: stageId,
      status,
      contactId,
    });
    return res.data;
  },

  async createTask(contactId, title, assignedTo, dueDate) {
    const res = await api.post('/tasks/', {
      title,
      contactId,
      assignedTo,
      dueDate,
      status: 'incompleted',
    });
    return res.data;
  },

  async updateCustomField(contactId, fieldKey, value) {
    const res = await api.put(`/contacts/${contactId}`, {
      customFields: [{ key: fieldKey, field_value: value }],
    });
    return res.data;
  },

  async triggerWorkflow(contactId, workflowId) {
    const res = await api.post(`/contacts/${contactId}/workflow/${workflowId}`, {});
    return res.data;
  },

  async getContact(contactId) {
    const res = await api.get(`/contacts/${contactId}`);
    return res.data.contact;
  },
};

module.exports = ghl;
