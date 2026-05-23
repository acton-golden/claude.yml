const OpenAI = require('openai');

const client = new OpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1',
});

async function ask(systemPrompt, userMessage) {
  const res = await client.chat.completions.create({
    model: 'anthropic/claude-sonnet-4-6',
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userMessage },
    ],
    max_tokens: 1024,
  });
  return res.choices[0].message.content.trim();
}

module.exports = { ask };
