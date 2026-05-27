#!/usr/bin/env python3
"""
Reporter Bot — a trainable investigative interviewer.

Drop .md briefing files into ./topics/ to give the bot background.
Run: python reporter.py [topic_file.md ...]
"""

import os
import sys
import glob
import textwrap
import anthropic

MODEL = "claude-sonnet-4-6"
WIDTH = 80

SYSTEM_PROMPT = """You are a seasoned investigative journalist conducting a hard interview.
Your style: relentless, precise, human. You have done your homework.

Rules you never break:
1. Ask ONE question at a time. Make it count.
2. Never accept vague, deflecting, or incomplete answers. Name the evasion directly:
   "You didn't answer the question. Let me ask it again."
3. Follow the thread. If the subject reveals something interesting, abandon your
   prepared line and go where the story leads.
4. Push for specifics: names, dates, numbers, decisions, consequences.
5. Ask the question the subject is hoping you won't ask.
6. When the answer is surprising or contradictory, say so and press:
   "That contradicts what you said earlier about X. Explain that."
7. Look for the human cost, the turning point, the thing that keeps them up at night.
8. End each response with your next hard question — nothing else.

Your opening move: greet the subject by acknowledging the topic, then ask the
single most uncomfortable question you can build from the briefing material.
Do not warm up slowly. Start where it matters."""


def load_topics(paths: list[str]) -> str:
    """Load and concatenate .md briefing files."""
    if not paths:
        md_files = sorted(glob.glob("topics/*.md"))
        if not md_files:
            return ""
        paths = md_files

    chunks = []
    for p in paths:
        try:
            with open(p) as f:
                content = f.read().strip()
            if content:
                chunks.append(f"## Briefing: {os.path.basename(p)}\n\n{content}")
        except FileNotFoundError:
            print(f"Warning: {p} not found, skipping.", file=sys.stderr)

    return "\n\n---\n\n".join(chunks)


def build_cached_system(briefing: str) -> list[dict]:
    """Build system blocks with prompt caching on the briefing material."""
    blocks = [{"type": "text", "text": SYSTEM_PROMPT}]
    if briefing:
        blocks.append({
            "type": "text",
            "text": f"\n\n<briefing>\n{briefing}\n</briefing>",
            "cache_control": {"type": "ephemeral"},
        })
    return blocks


def wrap(label: str, text: str) -> None:
    prefix = f"{label}: "
    indent = " " * len(prefix)
    lines = text.strip().split("\n")
    first = True
    for line in lines:
        if not line.strip():
            print()
            first = False
            continue
        wrapped = textwrap.fill(
            line,
            width=WIDTH,
            initial_indent=prefix if first else indent,
            subsequent_indent=indent,
        )
        print(wrapped)
        first = False


def run_interview(topic_paths: list[str]) -> None:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    briefing = load_topics(topic_paths)
    system_blocks = build_cached_system(briefing)

    history: list[dict] = []

    topic_hint = (
        ", ".join(os.path.basename(p) for p in topic_paths)
        if topic_paths
        else "loaded topics"
    )

    print("=" * WIDTH)
    print("REPORTER BOT — Investigative Interview Engine")
    if briefing:
        print(f"Briefing loaded: {topic_hint}")
    else:
        print("No briefing loaded. Running cold — bot will interview on any topic.")
        print("Tip: drop .md files in ./topics/ or pass paths as arguments.")
    print("Type your answers and press Enter twice (blank line) to submit.")
    print("Type 'quit' or Ctrl-C to end.")
    print("=" * WIDTH)
    print()

    # Opening question from the reporter
    opening_msg = (
        "Begin the interview. Deliver your opening and ask your first hard question."
        if briefing
        else (
            "Ask the subject what topic they want to be interviewed on, "
            "then immediately pivot to your first probing question."
        )
    )

    history.append({"role": "user", "content": opening_msg})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_blocks,
        messages=history,
    )

    reporter_text = response.content[0].text
    history.append({"role": "assistant", "content": reporter_text})
    wrap("REPORTER", reporter_text)
    print()

    # Interview loop
    while True:
        lines = []
        try:
            while True:
                line = input()
                if line.lower() in ("quit", "exit", "q"):
                    print("\n[Interview ended]")
                    return
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print("\n[Interview ended]")
            return

        user_answer = "\n".join(lines).strip()
        if not user_answer:
            continue

        history.append({"role": "user", "content": user_answer})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_blocks,
            messages=history,
        )

        reporter_text = response.content[0].text
        history.append({"role": "assistant", "content": reporter_text})

        print()
        wrap("REPORTER", reporter_text)
        print()


if __name__ == "__main__":
    topic_paths = sys.argv[1:] if len(sys.argv) > 1 else []
    try:
        run_interview(topic_paths)
    except anthropic.AuthenticationError:
        print("Error: ANTHROPIC_API_KEY is missing or invalid.", file=sys.stderr)
        sys.exit(1)
