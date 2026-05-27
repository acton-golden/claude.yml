#!/usr/bin/env python3
"""
Reporter Bot — a trainable investigative interviewer.

Drop .md briefing files into ./topics/ to give the bot background.
Run: python reporter.py [topic_file.md ...]
"""

import json
import os
import re
import sys
import glob
import textwrap
import anthropic

MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5-20251001"
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

A <contradiction> tag may appear before the subject's answer. If it does, you MUST
lead your response by confronting it directly. Quote both statements. Demand an
explanation. Do not soften it.

Your opening move: greet the subject by acknowledging the topic, then ask the
single most uncomfortable question you can build from the briefing material.
Do not warm up slowly. Start where it matters."""


class ClaimTracker:
    """Extracts and cross-checks factual claims across interview turns."""

    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.claims: list[dict] = []

    def extract(self, answer: str, turn: int) -> None:
        prompt = (
            "Extract concrete, falsifiable claims from this interview answer.\n"
            "Return a JSON array only. Each element: "
            '{"text": "concise claim", "quote": "shortest exact phrase supporting it"}\n'
            "Only include: denials, assertions of fact, dates/numbers stated, "
            "causal claims, who-did-what statements.\n"
            "Return [] if nothing concrete.\n\n"
            f"Answer:\n{answer}"
        )
        try:
            resp = self.client.messages.create(
                model=FAST_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                new_claims = json.loads(match.group())
                for c in new_claims:
                    c["turn"] = turn
                self.claims.extend(new_claims)
        except Exception:
            pass  # extraction failure is non-fatal

    def check(self, answer: str) -> dict | None:
        if len(self.claims) < 2:
            return None
        log_lines = [
            f"[Turn {c['turn']}] {c['text']}  (exact quote: \"{c['quote']}\")"
            for c in self.claims
        ]
        prompt = (
            "You are a fact-checker. Compare the new answer against the claim log "
            "and find DIRECT contradictions — not vagueness, actual logical contradictions.\n\n"
            "Return JSON in one of two forms:\n"
            '{"contradiction": false}\n'
            "or\n"
            '{"contradiction": true, '
            '"earlier_turn": <N>, '
            '"earlier_quote": "<exact words from earlier>", '
            '"earlier_claim": "<what was claimed>", '
            '"new_quote": "<exact words from new answer>", '
            '"new_claim": "<what is now claimed>"}\n\n'
            "Claim log:\n"
            + "\n".join(log_lines)
            + f"\n\nNew answer:\n{answer}"
        )
        try:
            resp = self.client.messages.create(
                model=FAST_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            match = re.search(r"\{.*?\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group())
                if result.get("contradiction"):
                    return result
        except Exception:
            pass
        return None

    def summary(self) -> str:
        if not self.claims:
            return "no claims logged"
        return f"{len(self.claims)} claim(s) on record"


def load_topics(paths: list[str]) -> str:
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
    first = True
    for line in text.strip().split("\n"):
        if not line.strip():
            print()
            first = False
            continue
        print(textwrap.fill(
            line,
            width=WIDTH,
            initial_indent=prefix if first else indent,
            subsequent_indent=indent,
        ))
        first = False


def run_interview(topic_paths: list[str]) -> None:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    tracker = ClaimTracker(client)

    briefing = load_topics(topic_paths)
    system_blocks = build_cached_system(briefing)
    history: list[dict] = []

    topic_hint = (
        ", ".join(os.path.basename(p) for p in topic_paths)
        if topic_paths else "loaded topics"
    )

    print("=" * WIDTH)
    print("REPORTER BOT — Investigative Interview Engine")
    if briefing:
        print(f"Briefing loaded: {topic_hint}")
    else:
        print("No briefing loaded. Running cold.")
        print("Tip: drop .md files in ./topics/ or pass paths as arguments.")
    print("Type your answer and press Enter twice to submit.")
    print("Type 'quit' or Ctrl-C to end.")
    print("=" * WIDTH)
    print()

    opening_msg = (
        "Begin the interview. Deliver your opening and ask your first hard question."
        if briefing else
        "Ask the subject what topic they want to be interviewed on, "
        "then immediately pivot to your first probing question."
    )

    history.append({"role": "user", "content": opening_msg})
    response = client.messages.create(
        model=MODEL, max_tokens=1024,
        system=system_blocks, messages=history,
    )
    reporter_text = response.content[0].text
    history.append({"role": "assistant", "content": reporter_text})
    wrap("REPORTER", reporter_text)
    print()

    turn = 0
    while True:
        lines: list[str] = []
        try:
            while True:
                line = input()
                if line.lower() in ("quit", "exit", "q"):
                    print("\n[Interview ended]")
                    _print_claim_log(tracker)
                    return
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print("\n[Interview ended]")
            _print_claim_log(tracker)
            return

        user_answer = "\n".join(lines).strip()
        if not user_answer:
            continue

        turn += 1

        # Run claim extraction and contradiction check in parallel via two calls
        # (extraction first so we have prior claims to check against)
        contradiction = tracker.check(user_answer)
        tracker.extract(user_answer, turn)

        # Build the message sent to the reporter
        if contradiction:
            earlier_turn = contradiction.get("earlier_turn", "?")
            earlier_quote = contradiction.get("earlier_quote", "")
            earlier_claim = contradiction.get("earlier_claim", "")
            new_quote = contradiction.get("new_quote", "")
            new_claim = contradiction.get("new_claim", "")
            contradiction_block = (
                f'<contradiction turn="{earlier_turn}">\n'
                f'Earlier they said: "{earlier_quote}" — claiming {earlier_claim}.\n'
                f'Now they say: "{new_quote}" — claiming {new_claim}.\n'
                f"</contradiction>\n\n"
            )
            message_content = contradiction_block + user_answer
            print(f"\n  [!] CONTRADICTION DETECTED — Turn {earlier_turn} vs now")
            print(f"      Before: \"{earlier_quote}\"")
            print(f"      Now:    \"{new_quote}\"")
        else:
            message_content = user_answer

        status = tracker.summary()
        print(f"  [claims: {status}]\n")

        history.append({"role": "user", "content": message_content})
        response = client.messages.create(
            model=MODEL, max_tokens=1024,
            system=system_blocks, messages=history,
        )
        reporter_text = response.content[0].text
        history.append({"role": "assistant", "content": reporter_text})

        print()
        wrap("REPORTER", reporter_text)
        print()


def _print_claim_log(tracker: ClaimTracker) -> None:
    if not tracker.claims:
        return
    print("\n" + "=" * WIDTH)
    print("CLAIM LOG")
    print("=" * WIDTH)
    for c in tracker.claims:
        print(f"  [Turn {c['turn']}] {c['text']}")
        print(f"           \"{c['quote']}\"")
    print()


if __name__ == "__main__":
    topic_paths = sys.argv[1:] if len(sys.argv) > 1 else []
    try:
        run_interview(topic_paths)
    except anthropic.AuthenticationError:
        print("Error: ANTHROPIC_API_KEY is missing or invalid.", file=sys.stderr)
        sys.exit(1)
