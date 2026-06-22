"""
formats.py — platform output contexts for the reporter bot.

Each format does two things:
  1. interview_hint  — injected into every reporter's system prompt when the
                       format is active at startup, shaping how they ask questions
  2. output_prompt   — drives post-interview content generation for the platform
"""

import os
import datetime
import textwrap

# Populated by _make_client in reporter.py at runtime
_call_fn = None  # set by init()

WIDTH = 80


def init(call_fn) -> None:
    """Wire in the _call function from reporter.py."""
    global _call_fn
    _call_fn = call_fn


# ── Format definitions ──────────────────────────────────────────────────────

FORMATS: dict[str, dict] = {
    "podcast": {
        "name": "Podcast Episode",
        "emoji": "🎙",
        "description": "Full episode script, chapters, show notes, promo clip pulls",
        "interview_hint": (
            "FORMAT CONTEXT — PODCAST:\n"
            "This interview will become a podcast episode. Shape your questions accordingly:\n"
            "- Ask for stories, not just facts. 'Walk me through the moment when...'\n"
            "- Pursue the emotional truth, not just the logical one.\n"
            "- Invite context and backstory — listeners need it.\n"
            "- Create chapter-worthy moments: a reveal, a turning point, a confrontation.\n"
            "- Still go hard. A great podcast episode has a narrative arc AND a body count."
        ),
        "output_prompt": (
            "You are a podcast producer. From this interview transcript, generate:\n\n"
            "## EPISODE TITLE\n"
            "Three options: one factual, one provocative, one narrative.\n\n"
            "## EPISODE DESCRIPTION (200 words)\n"
            "What listeners will hear. Written to make them hit play.\n\n"
            "## CHAPTER MARKERS\n"
            "Timestamped sections (estimate timestamps). Format: [00:00] Title\n\n"
            "## SHOW NOTES\n"
            "Key facts, names, dates, and documents mentioned. Formatted for the episode page.\n\n"
            "## PROMO CLIP\n"
            "The 30-second exchange that would make someone share the episode. Quote it verbatim.\n\n"
            "## HOST INTRO SCRIPT\n"
            "Two paragraphs. Sets up the episode. Ends on a hook."
        ),
    },
    "tiktok": {
        "name": "TikTok",
        "emoji": "🎵",
        "description": "Hook + 60-sec script + text overlays + caption + hashtags",
        "interview_hint": (
            "FORMAT CONTEXT — TIKTOK:\n"
            "This interview will be cut into short-form video. Shape your questions accordingly:\n"
            "- Engineer punchy, quotable moments. One sentence that stops a scroll.\n"
            "- Ask for definitive statements: 'Say that in one sentence.'\n"
            "- Create tension in short exchanges. Fast back-and-forth.\n"
            "- The best TikTok clip is a single devastating exchange under 60 seconds.\n"
            "- Still get the truth. Compression makes it hit harder, not softer."
        ),
        "output_prompt": (
            "You are a viral content creator. From this interview, generate:\n\n"
            "## HOOK (first 3 seconds)\n"
            "One sentence. Creates immediate tension or curiosity. No intro.\n\n"
            "## 60-SECOND SCRIPT\n"
            "The single best exchange from this interview, tightened for video.\n"
            "Format: [REPORTER]: ... / [SUBJECT]: ...\n\n"
            "## TEXT OVERLAYS\n"
            "5 on-screen text moments timed to the script. Short, punchy.\n\n"
            "## CAPTION\n"
            "Under 150 characters. Designed to generate comments.\n\n"
            "## HASHTAGS\n"
            "8–12 hashtags. Mix niche and broad.\n\n"
            "## SERIES POTENTIAL\n"
            "Two follow-up TikTok angles this interview could spawn."
        ),
    },
    "instagram": {
        "name": "Instagram",
        "emoji": "📸",
        "description": "Carousel slides + caption + Story text + quote card + hashtags",
        "interview_hint": (
            "FORMAT CONTEXT — INSTAGRAM:\n"
            "This interview will become Instagram content. Shape your questions accordingly:\n"
            "- Pull for visual moments and quotable lines.\n"
            "- Ask for 'before and after' moments — transformation, realization, decision.\n"
            "- Get the one quote that belongs on a graphic: short, true, devastating.\n"
            "- Create contrast: what they said vs. what the documents show.\n"
            "- Visually dramatic revelations land hardest on this platform."
        ),
        "output_prompt": (
            "You are an Instagram content strategist. From this interview, generate:\n\n"
            "## CAROUSEL (10 slides)\n"
            "Slide 1: Hook — one bold claim or question.\n"
            "Slides 2–9: Evidence, quotes, and escalating tension. One idea per slide.\n"
            "Slide 10: Call to action or cliffhanger.\n"
            "Format each slide as: [Slide N] Headline / Body (max 30 words)\n\n"
            "## CAPTION\n"
            "Under 2,200 characters. Hook line, context, key revelation, CTA.\n\n"
            "## STORY TEXT (3 frames)\n"
            "Three punchy Story frames. Each under 15 words.\n\n"
            "## QUOTE CARD\n"
            "The single most shareable quote from this interview. Exact words.\n\n"
            "## HASHTAGS\n"
            "15–20 hashtags. Include niche, mid-tier, and broad."
        ),
    },
    "youtube": {
        "name": "YouTube",
        "emoji": "▶️",
        "description": "Title options + description + chapters + thumbnail concept + tags",
        "interview_hint": (
            "FORMAT CONTEXT — YOUTUBE:\n"
            "This interview will be a full YouTube video. Shape your questions accordingly:\n"
            "- Build narrative arc: setup, escalation, revelation, consequence.\n"
            "- Ask for backstory and context — YouTube audiences want depth.\n"
            "- Create distinct chapter moments: a specific reveal or confrontation per segment.\n"
            "- Pursue the 'thumbnail moment' — the single most shocking exchange.\n"
            "- Long-form audience will stay for the full story if it's earned."
        ),
        "output_prompt": (
            "You are a YouTube producer. From this interview, generate:\n\n"
            "## VIDEO TITLES (4 options)\n"
            "One SEO-optimized. One curiosity-gap. One confrontational. One narrative.\n\n"
            "## DESCRIPTION\n"
            "Full video description: hook paragraph, what viewers will see, key timestamps, "
            "relevant links section, subscribe CTA.\n\n"
            "## CHAPTER MARKERS\n"
            "Full chapter list with estimated timestamps. Format: 00:00 Chapter Title\n\n"
            "## THUMBNAIL CONCEPT\n"
            "Describe the ideal thumbnail: image, text overlay, emotional expression, color.\n\n"
            "## TAGS\n"
            "20 YouTube tags for discovery.\n\n"
            "## RETENTION HOOKS\n"
            "Three moments in the interview that should be teased in the first 30 seconds "
            "to keep viewers watching."
        ),
    },
    "facebook": {
        "name": "Facebook",
        "emoji": "👥",
        "description": "Post copy + engagement question + shareable summary",
        "interview_hint": (
            "FORMAT CONTEXT — FACEBOOK:\n"
            "This interview will become a Facebook post. Shape your questions accordingly:\n"
            "- Ask about community impact, not just individual decisions.\n"
            "- Get the personal, relatable angle — Facebook audience connects through people.\n"
            "- Ask for the 'you won't believe this' moment — shareable outrage or revelation.\n"
            "- Create a clear villain and stakes that a general audience cares about."
        ),
        "output_prompt": (
            "You are a Facebook content strategist. From this interview, generate:\n\n"
            "## POST (long-form)\n"
            "400–600 words. Narrative style. Hook, context, key revelation, stakes.\n"
            "Written for a general audience. Ends with a question.\n\n"
            "## SHORT POST (under 100 words)\n"
            "Most shareable version. One revelation. One question.\n\n"
            "## ENGAGEMENT QUESTION\n"
            "One question that will generate comments. Specific to this story.\n\n"
            "## SHAREABLE QUOTE\n"
            "The quote most likely to be shared as a screenshot."
        ),
    },
    "twitter": {
        "name": "Twitter / X",
        "emoji": "𝕏",
        "description": "Thread + standalone tweets + key quote tweets",
        "interview_hint": (
            "FORMAT CONTEXT — TWITTER/X:\n"
            "This interview will become a Twitter thread. Shape your questions accordingly:\n"
            "- Engineer tweet-sized revelations: short, definitive, undeniable.\n"
            "- Create a sequence of escalating facts that demand to be threaded.\n"
            "- Ask for the one-sentence answer that can't be taken back.\n"
            "- Pursue the ratio-bait moment: the statement that will generate 10,000 replies."
        ),
        "output_prompt": (
            "You are a Twitter/X journalist. From this interview, generate:\n\n"
            "## THREAD (10–15 tweets)\n"
            "Numbered. Tweet 1 is the hook. Each tweet stands alone AND advances the story.\n"
            "Format: [1/N] text\n\n"
            "## STANDALONE TWEET\n"
            "The single most explosive revelation in 280 characters. No thread.\n\n"
            "## KEY QUOTE TWEET\n"
            "One direct quote from the subject, formatted as a screenshot caption.\n\n"
            "## REPLY BAIT\n"
            "The tweet that will generate the most replies. Write it.\n\n"
            "## ALT TEXT / IMAGE DESCRIPTION\n"
            "If posting the interview transcript as an image, describe it."
        ),
    },
    "newsletter": {
        "name": "Newsletter / Article",
        "emoji": "📰",
        "description": "Subject line + full article + pull quotes + summary box",
        "interview_hint": (
            "FORMAT CONTEXT — NEWSLETTER/ARTICLE:\n"
            "This interview will become a newsletter or article. Shape your questions accordingly:\n"
            "- Build for inverted pyramid: most important revelation first.\n"
            "- Get attributable quotes with full context.\n"
            "- Ask follow-up questions that create a paper trail narrative.\n"
            "- Pursue the nut graf moment: the one paragraph that explains why this matters.\n"
            "- Long-form readers want depth, specificity, and consequence."
        ),
        "output_prompt": (
            "You are an investigative journalist. From this interview, write:\n\n"
            "## SUBJECT LINE / HEADLINE\n"
            "Three options: factual, punchy, narrative.\n\n"
            "## PREVIEW TEXT / SUBHEAD\n"
            "One sentence. Completes the headline's promise.\n\n"
            "## FULL ARTICLE (600–900 words)\n"
            "Inverted pyramid. Lede, nut graf, body, quote blocks, kicker.\n"
            "Use the subject's exact quotes. Attribute precisely.\n\n"
            "## PULL QUOTES (3)\n"
            "Best quotes for visual breakout. Exact words only.\n\n"
            "## SUMMARY BOX\n"
            "Three bullet points. The three things the reader must know."
        ),
    },
}


def pick_formats_menu() -> list[str]:
    """Interactive multi-select format picker. Returns list of chosen format keys."""
    keys = list(FORMATS.keys())
    print()
    print("  Generate content for which platforms?")
    print("  Enter numbers separated by spaces, or Enter to skip.")
    print()
    for i, key in enumerate(keys, 1):
        f = FORMATS[key]
        print(f"  {i}. {f['emoji']} {f['name']:<22} {f['description']}")
    print()
    while True:
        raw = input("  Platforms [Enter to skip]: ").strip()
        if not raw:
            return []
        try:
            indices = [int(x) - 1 for x in raw.split()]
            chosen = []
            for idx in indices:
                if 0 <= idx < len(keys) and keys[idx] not in chosen:
                    chosen.append(keys[idx])
            if chosen:
                return chosen
        except ValueError:
            pass
        print(f"  Enter numbers like: 1 3 5  (1–{len(keys)})")


def generate_platform_content(
    client,
    provider: str,
    model: str,
    transcript: str,
    briefing: str,
    fmt_key: str,
) -> str:
    """Generate platform-specific content from a transcript."""
    if _call_fn is None:
        raise RuntimeError("formats.init() not called")
    fmt = FORMATS[fmt_key]
    context = (
        f"ORIGINAL BRIEFING:\n{briefing}\n\n" if briefing else ""
    )
    prompt = (
        f"{context}"
        f"INTERVIEW TRANSCRIPT:\n{transcript}\n\n"
        "---\n\n"
        f"{fmt['output_prompt']}"
    )
    return _call_fn(
        client, provider, model, 2048,
        [{"type": "text", "text": f"You are creating content for {fmt['name']}."}],
        [{"role": "user", "content": prompt}],
    )


def run_format_outputs(
    client,
    provider: str,
    model: str,
    transcript: str,
    briefing: str,
    chosen_keys: list[str],
) -> None:
    """Generate and save content for all chosen formats."""
    if not chosen_keys:
        return
    os.makedirs("transcripts", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for key in chosen_keys:
        fmt = FORMATS[key]
        print(f"\n[Generating {fmt['emoji']} {fmt['name']} content...]")
        try:
            content = generate_platform_content(client, provider, model, transcript, briefing, key)
        except Exception as e:
            print(f"  [Failed: {e}]")
            continue
        # Print to terminal
        print(f"\n{'=' * WIDTH}")
        print(f"{fmt['emoji']}  {fmt['name'].upper()}")
        print("=" * WIDTH)
        for line in content.split("\n"):
            if not line.strip():
                print()
            elif line.startswith("##"):
                print(f"\n{line}")
            else:
                print(textwrap.fill(line, width=WIDTH, subsequent_indent="  "))
        # Save to file
        path = f"transcripts/{key}-{ts}.md"
        with open(path, "w") as fh:
            fh.write(f"# {fmt['name']} — {ts}\n\n{content}\n")
        print(f"\n  [Saved to {path}]")


def interview_hint(fmt_key: str) -> str:
    """Return the interview-shaping instruction for a format, or empty string."""
    if fmt_key and fmt_key in FORMATS:
        return "\n\n" + FORMATS[fmt_key]["interview_hint"]
    return ""
