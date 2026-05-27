#!/usr/bin/env python3
"""
Reporter Panel — five investigative agents, each a distinct psychological weapon.

Usage: python panel.py [topic_file.md ...]

Commands mid-interview:
  /solo <key>    Go 1-on-1 with one reporter  (e.g. /solo devil)
  /panel         Return to full panel
  /mute <key>    Silence a reporter permanently
  /active        Show reporter statuses
  quit           End interview and generate panel debrief
"""

import os
import re
import sys
import textwrap
import datetime
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from reporter import _make_client, _call, load_topics, wrap, WIDTH


@dataclass
class Reporter:
    key: str
    name: str
    tagline: str
    persona: str
    history: list[dict] = field(default_factory=list)
    muted: bool = False


REPORTERS: list[Reporter] = [
    Reporter(
        key="devil",
        name="Devil's Advocate",
        tagline="inverts every claim — forces you to prove your own words",
        persona="""You are a Devil's Advocate interviewer. One method: systematic inversion.
Whatever the subject asserts, argue the opposite — not out of disbelief, but to force them to prove it.
- "But doesn't that actually mean the opposite is true?"
- "You're making my case for me — if X, then Y must follow."
- Use their own language against them.
- If they claim good faith, ask what bad faith would have looked like.
- If they deny, ask what evidence would change their mind.
- Every statement contains a hidden self-contradiction. Find it.
Ask ONE sharp, inverting question. End on it.""",
    ),
    Reporter(
        key="manipulator",
        name="The Manipulator",
        tagline="builds false consensus, reframes your words, springs the trap",
        persona="""You are a psychological manipulator conducting an interview.
- Build false consensus before the pivot: "Most reasonable people would find X understandable — so how do you explain Y?"
- Reframe answers to tighten the noose: "So what you're really admitting is..."
- Treat denials as partial admissions: "You said you 'don't recall' — which means you're not denying it happened."
- Apply social pressure: "Others close to you told us something very different."
- Make the subject feel understood right before the trap closes.
Ask ONE question. Make it feel like a lifeline. Make it function as a snare.""",
    ),
    Reporter(
        key="narcissist",
        name="The Narcissist",
        tagline="flattery and mirroring — makes you perform, then uses the performance",
        persona="""You are a narcissistic interviewer who makes the interview partly about yourself — and uses that to disarm.
- Relate their situation to your own "experiences" to create false intimacy and lower defenses.
- Deploy strategic flattery right before the hard question: "That's a remarkably honest answer. So honest I have to go further..."
- Make the subject want to impress you. Approval is currency — withhold it at key moments.
- When they resist, turn subtly cold. The withdrawal of warmth is pressure.
- Make them perform for you. They'll reveal themselves in the performance.
Ask ONE question. Give it a personal angle that makes it harder to dodge.""",
    ),
    Reporter(
        key="buddy",
        name="The Buddy",
        tagline="radical warmth as a weapon — softens you up, then asks the knife question",
        persona="""You are the warm, disarming interviewer. Your method: radical empathy as a trap.
- First-name basis. Informal. "Look, I get it. I really do."
- Make the subject feel safe, seen, even liked — safe enough to say more than they should.
- Never raise your voice. Never show impatience. The warmth never cracks.
- Ask the hardest question in the softest voice: "And I have to ask you this one, just between us..."
- The more comfortable they feel, the more they give away.
Ask ONE question. It should feel like a friend asking. It should land like a knife.""",
    ),
    Reporter(
        key="hombre",
        name="Best Hombre",
        tagline="pure charm — makes you want to talk, then uses everything you said",
        persona="""You are the most charming interviewer alive. Pure charisma. Everyone loves talking to you.
- Self-deprecating humor that puts the subject completely at ease.
- Make every subject feel like the most interesting person in the room.
- The longer they talk, the more they give away — so keep them talking.
- Use humor to lower defenses, then pivot cleanly to the real question.
- They'll realize what they said only after they've said it.
Ask ONE question. Make it feel like an invitation to share a great story. Let it be a trap.""",
    ),
]

# Transcript entry for debrief
Tx = dict  # {"type": "q"|"a", "reporter": name|None, "text": str}


def _build_system(persona: str, briefing: str, provider: str) -> list[dict]:
    blocks: list[dict] = [{"type": "text", "text": persona}]
    if briefing:
        b: dict = {"type": "text", "text": f"\n\n<briefing>\n{briefing}\n</briefing>"}
        if provider != "openrouter":
            b["cache_control"] = {"type": "ephemeral"}
        blocks.append(b)
    return blocks


def _fire_round(
    active: list[Reporter],
    systems: dict[str, list[dict]],
    answer: str,
    prev_questions: dict[str, str] | None,
    client,
    provider: str,
    model: str,
) -> dict[str, str]:
    """Generate next question from all active reporters in parallel."""

    def ask_one(r: Reporter) -> tuple[str, str]:
        if prev_questions is None:
            # Opening round
            trigger = (
                "Begin the interview. Ask your single most distinctive opening question "
                "based on the briefing and your interrogation style."
                if answer else  # answer holds briefing hint on first call
                "Ask the subject what topic they want to discuss, then immediately ask your first question."
            )
        else:
            others = [
                f"  {rep.name} asked: \"{prev_questions[rep.key][:100]}"
                f"{'...' if len(prev_questions[rep.key]) > 100 else ''}\""
                for rep in active
                if rep.key in prev_questions and rep.key != r.key
            ]
            trigger = f"Subject's answer:\n{answer}"
            if others:
                trigger += "\n\n[Other reporters this round:\n" + "\n".join(others) + "\n]"
            trigger += "\n\nAsk your next question."

        r.history.append({"role": "user", "content": trigger})
        q = _call(client, provider, model, 512, systems[r.key], r.history)
        r.history.append({"role": "assistant", "content": q})
        return r.key, q

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, len(active))) as pool:
        futures = {pool.submit(ask_one, r): r.key for r in active}
        for fut in as_completed(futures):
            key, q = fut.result()
            results[key] = q
    return results


def _display_questions(questions: dict[str, str]) -> None:
    order = [r for r in REPORTERS if r.key in questions]
    for r in order:
        print(f"\n  [{r.name.upper()}]  —  {r.tagline}")
        wrap("  Q", questions[r.key])


def _reporter_by_key(key: str) -> Reporter | None:
    return next((r for r in REPORTERS if r.key == key), None)


def _pick_reporters() -> list[Reporter]:
    """Interactive reporter selector. Returns chosen subset (1–5)."""
    print()
    print("  Choose your reporters (1–5). Enter numbers separated by spaces,")
    print("  or press Enter to use all five.")
    print()
    for i, r in enumerate(REPORTERS, 1):
        print(f"  {i}. {r.name:<20}  {r.tagline}")
    print()
    while True:
        raw = input("  Your selection [default: all]: ").strip()
        if not raw:
            return list(REPORTERS)
        try:
            indices = [int(x) for x in raw.split()]
            chosen = []
            for idx in indices:
                if 1 <= idx <= len(REPORTERS):
                    r = REPORTERS[idx - 1]
                    if r not in chosen:
                        chosen.append(r)
            if chosen:
                return chosen
        except ValueError:
            pass
        print("  Enter numbers like: 1 3 5")


def run_panel(topic_paths: list[str]) -> None:
    client, provider, model, _fast = _make_client()
    briefing = load_topics(topic_paths)
    topic_hint = ", ".join(os.path.basename(p) for p in topic_paths) if topic_paths else None

    print("=" * WIDTH)
    print("REPORTER PANEL — Multi-Agent Interrogation")
    print(f"Provider: {provider}  Model: {model}")
    if topic_hint:
        print(f"Briefing: {topic_hint}")
    else:
        print("No briefing loaded. Running cold.")

    # Let the user pick which reporters are in the room
    selected = _pick_reporters()
    for r in REPORTERS:
        r.muted = r not in selected

    print()
    print("  Active reporters:")
    for r in selected:
        print(f"    /{r.key:<12}  {r.name} — {r.tagline}")
    print()
    print("  Commands: /solo <key>  /panel  /mute <key>  /active  quit")
    print("=" * WIDTH)

    systems = {r.key: _build_system(r.persona, briefing, provider) for r in REPORTERS}
    transcript: list[Tx] = []

    # Opening round
    print("\n[Opening — generating in parallel...]")
    active = [r for r in REPORTERS if not r.muted]
    questions = _fire_round(active, systems, briefing, None, client, provider, model)

    # Keep questions in display order (REPORTERS list order)
    for r in REPORTERS:
        if r.key in questions:
            transcript.append({"type": "q", "reporter": r.name, "text": questions[r.key]})

    _display_questions(questions)
    print()

    solo_key: str | None = None

    while True:
        lines: list[str] = []
        try:
            while True:
                line = input()
                if line.lower() in ("quit", "exit", "q"):
                    print("\n[Interview ended]")
                    _run_debrief(client, provider, model, transcript, briefing)
                    return

                if line.startswith("/"):
                    parts = line.strip().split(maxsplit=1)
                    cmd, arg = parts[0], (parts[1] if len(parts) > 1 else "").strip()
                    if cmd == "/solo":
                        r = _reporter_by_key(arg)
                        if r and not r.muted:
                            solo_key = arg
                            print(f"  [1-on-1 with {r.name}. /panel to return to full panel.]")
                        else:
                            print(f"  [Unknown or muted reporter: '{arg}'. Keys: {', '.join(r.key for r in REPORTERS)}]")
                    elif cmd == "/panel":
                        solo_key = None
                        print("  [Full panel restored.]")
                    elif cmd == "/mute":
                        r = _reporter_by_key(arg)
                        if r:
                            r.muted = True
                            if solo_key == arg:
                                solo_key = None
                            print(f"  [{r.name} muted for the rest of the interview.]")
                        else:
                            print(f"  [Unknown reporter: '{arg}']")
                    elif cmd == "/active":
                        for r in REPORTERS:
                            status = "muted" if r.muted else ("SOLO ◀" if r.key == solo_key else "active")
                            print(f"  /{r.key:<12} {r.name:<20} [{status}]")
                    else:
                        print(f"  [Unknown command: {cmd}]")
                    continue

                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)

        except (EOFError, KeyboardInterrupt):
            print("\n[Interview ended]")
            _run_debrief(client, provider, model, transcript, briefing)
            return

        answer = "\n".join(lines).strip()
        if not answer:
            continue

        transcript.append({"type": "a", "reporter": None, "text": answer})

        asking = (
            [r for r in REPORTERS if r.key == solo_key]
            if solo_key else
            [r for r in REPORTERS if not r.muted]
        )
        if not asking:
            print("  [No active reporters. /panel or /mute to adjust.]")
            continue

        print("\n[Reporters thinking...]")
        questions = _fire_round(asking, systems, answer, questions, client, provider, model)

        for r in REPORTERS:
            if r.key in questions:
                transcript.append({"type": "q", "reporter": r.name, "text": questions[r.key]})

        _display_questions(questions)
        print()


def _run_debrief(client, provider, model, transcript: list[Tx], briefing: str) -> None:
    if not transcript:
        return

    print("\n[Generating panel debrief...]")

    tx_text = ""
    for entry in transcript:
        if entry["type"] == "q":
            tx_text += f"\n[{entry['reporter'].upper()}]\n{entry['text']}\n"
        else:
            tx_text += f"\n[SUBJECT]\n{entry['text']}\n"

    reporter_list = "\n".join(f"  - {r.name}: {r.tagline}" for r in REPORTERS if not r.muted)

    prompt = f"""You are a senior editor reviewing a simultaneous panel interview by five reporters.

Reporters and their methods:
{reporter_list}

{"ORIGINAL BRIEFING:" + chr(10) + briefing + chr(10) if briefing else ""}
PANEL TRANSCRIPT:
{tx_text}

---
Write a PANEL DEBRIEF. Be specific. Quote the subject directly wherever possible.

## WHAT EACH REPORTER UNCOVERED
One or two sentences per reporter: what their specific approach revealed that the others missed.

## KEY ADMISSIONS
Concrete things the subject admitted, revealed, or let slip. Quote directly.

## MOST EFFECTIVE QUESTION
The single question that did the most damage. Name the reporter, quote the question, explain why it worked.

## WHAT WASN'T SAID
What the subject conspicuously avoided across all five lines of questioning.

## PSYCHOLOGICAL PROFILE
Two sentences: what this subject's pattern of responses reveals about their psychology and strategy.

## DRAFT LEDE
Two publishable sentences. The story this panel interview supports."""

    try:
        report = _call(
            client, provider, model, 2048,
            [{"type": "text", "text": "You are a senior investigative editor."}],
            [{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"\n[Debrief failed: {e}]")
        return

    print("\n" + "=" * WIDTH)
    print("PANEL DEBRIEF")
    print("=" * WIDTH)
    for line in report.split("\n"):
        if not line.strip():
            print()
        elif line.startswith("##"):
            print(f"\n{line}")
        else:
            print(textwrap.fill(line, width=WIDTH, subsequent_indent="  "))

    os.makedirs("transcripts", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = f"transcripts/panel-{ts}.md"
    with open(path, "w") as f:
        f.write(f"# Panel Interview — {ts}\n\n## Transcript\n\n```\n{tx_text}\n```\n\n## Debrief\n\n{report}\n")
    print(f"\n[Saved to {path}]")


if __name__ == "__main__":
    topic_paths = sys.argv[1:] if len(sys.argv) > 1 else []
    try:
        run_panel(topic_paths)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
