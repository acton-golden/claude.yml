# Reporter Bot

An AI-powered investigative interview engine. Load a topic briefing, pick your reporters, and get interrogated by five distinct psychological archetypes — each with a different weapon.

---

## Quickstart (web app — no terminal needed after setup)

```bash
git clone https://github.com/acton-golden/claude.yml
cd claude.yml
pip install -r requirements.txt
streamlit run app.py
```

Opens in your browser. Paste your API key on the first screen and you're in.

**Get an API key:**
- [OpenRouter](https://openrouter.ai) — recommended, works immediately, wide model selection
- [Anthropic](https://console.anthropic.com) — direct API access

---

## The Five Reporters

| Reporter | Method |
|---|---|
| 🔴 **Devil's Advocate** | Inverts every claim. Forces you to prove your own words against themselves. |
| 🟡 **The Buddy** | Warmth + flattery + manipulation fused. A hug that functions as a cage. |
| 🟢 **Best Hombre** | Pure charm. Makes you want to talk. Uses everything you say. |
| ⚫ **The Cobra** | Asks one question then goes silent. You fill the void. |
| 🔵 **The Time Traveler** | Interviews from the future. The fall already happened — now narrate it. |

---

## Training the Bot

Drop a `.md` file in `topics/` — or paste it directly in the web app. Use this structure:

```markdown
# Topic: Your Subject's Name

## Key Facts
- Date, number, or name that creates contradiction
- The thing they said publicly vs. what records show

## Tension Points
- Where their story breaks down
- What they'd prefer you not ask

## Questions They'll Dodge
- The specific question they're hoping you won't ask
```

The reporters read the briefing and use it. The more specific the facts, the harder the questions.

---

## Platform Outputs

After every interview, generate ready-to-post content for:

| Platform | What you get |
|---|---|
| 🎙 Podcast | Episode script, chapters, show notes, promo clip |
| 🎵 TikTok | Hook, 60-sec script, overlays, caption, hashtags |
| 📸 Instagram | Carousel, caption, Stories, quote card, hashtags |
| ▶️ YouTube | Titles, description, chapters, thumbnail concept |
| 👥 Facebook | Long post, short post, engagement question |
| 𝕏 Twitter/X | Thread, standalone tweet, reply bait |
| 📰 Newsletter | Headline, full article, pull quotes, summary |

---

## CLI Usage (power users)

```bash
# First-time setup — saves config.json locally
python reporter.py --setup

# Solo interview with one reporter
python reporter.py topics/my-topic.md

# Panel interview — pick reporters at startup
python panel.py topics/my-topic.md

# Shape the interview for a platform
python reporter.py --format podcast topics/my-topic.md
python panel.py --format tiktok topics/my-topic.md

# Reconfigure key or model
python reporter.py --setup
```

---

## What happens during every interview

- **Contradiction tracker** — logs every factual claim. When the subject contradicts themselves, the reporter is alerted with the exact earlier quote.
- **Evasion scorer** — rates each answer 0–3 for evasiveness. Accumulates a pressure score that escalates the reporter's intensity across 5 levels.
- **Post-interview debrief** — admissions, evasions, contradictions, best quotes, credibility score, follow-up investigation leads, and a draft publishable lede.

---

## Deploy to Streamlit Cloud (free, shareable link)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set main file to `app.py`
4. Add your API key under **Secrets**: `OPENROUTER_API_KEY = "sk-or-..."`
5. Deploy — share the link

Anyone with the link can use it without any setup.
