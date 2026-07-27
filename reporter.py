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
import datetime
import anthropic
import formats as fmt_module

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
WIDTH = 80

# config.json lives next to this file
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Available models per provider — shown as a menu during setup
_MODELS = {
    "openrouter": {
        "main": [
            # ── Free tier (no cost, rate-limited) ──────────────────────────
            ("meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B  — FREE, strong interviews"),
            ("google/gemini-2.0-flash-exp:free",        "Gemini 2.0 Flash — FREE, fast"),
            ("deepseek/deepseek-r1:free",               "DeepSeek R1  — FREE, deep reasoning"),
            ("qwen/qwen3-235b-a22b:free",               "Qwen3 235B  — FREE, very capable"),
            # ── Paid tier ──────────────────────────────────────────────────
            ("anthropic/claude-sonnet-4-5",   "Sonnet 4.5  — paid, best value"),
            ("anthropic/claude-sonnet-4-6",   "Sonnet 4.6  — paid, latest"),
            ("anthropic/claude-opus-4-5",     "Opus 4.5    — paid, most powerful"),
            ("anthropic/claude-haiku-4-5",    "Haiku 4.5   — paid, fastest"),
        ],
        "fast": [
            # ── Free tier ──────────────────────────────────────────────────
            ("meta-llama/llama-3.1-8b-instruct:free", "Llama 3.1 8B  — FREE, fast analysis"),
            ("google/gemini-2.0-flash-exp:free",       "Gemini 2.0 Flash — FREE"),
            # ── Paid tier ──────────────────────────────────────────────────
            ("anthropic/claude-haiku-4-5",    "Haiku 4.5   — paid, sharp analysis"),
            ("anthropic/claude-sonnet-4-5",   "Sonnet 4.5  — paid, deepest analysis"),
        ],
    },
    "anthropic": {
        "main": [
            ("claude-sonnet-4-6",             "Sonnet 4.6  — latest, best value"),
            ("claude-opus-4-7",               "Opus 4.7    — most powerful"),
            ("claude-haiku-4-5-20251001",     "Haiku 4.5   — fastest, cheapest"),
        ],
        "fast": [
            ("claude-haiku-4-5-20251001",     "Haiku 4.5   — recommended for analysis"),
            ("claude-sonnet-4-6",             "Sonnet 4.6  — sharper analysis"),
        ],
    },
}


def _load_config() -> dict:
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    return {}


def _save_config(cfg: dict) -> None:
    with open(_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _pick_from_menu(options: list[tuple[str, str]], prompt: str, default_idx: int = 0) -> str:
    for i, (val, label) in enumerate(options, 1):
        marker = " (default)" if i - 1 == default_idx else ""
        print(f"  {i}. {label}{marker}")
    while True:
        raw = input(f"{prompt} [1]: ").strip() or "1"
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        print(f"  Enter a number between 1 and {len(options)}.")


def run_setup(reconfigure: bool = False) -> dict:
    """Interactive setup wizard. Returns saved config dict."""
    existing = _load_config() if reconfigure else {}

    print()
    print("=" * WIDTH)
    print("REPORTER BOT — Setup" + (" (reconfigure)" if reconfigure else ""))
    print("=" * WIDTH)

    # Provider
    print("\nProvider:")
    print("  1. OpenRouter  — works now, great model selection  (recommended)")
    print("  2. Anthropic   — direct API, use when you have an Anthropic key")
    cur_provider = existing.get("provider", "openrouter")
    default_p = "1" if cur_provider == "openrouter" else "2"
    raw = input(f"Provider [{default_p}]: ").strip() or default_p
    provider = "anthropic" if raw == "2" else "openrouter"

    # API key
    cur_key = existing.get("api_key", "")
    key_hint = f"...{cur_key[-6:]}" if cur_key else "none set"
    print(f"\nAPI key (current: {key_hint})")
    print(f"  {'OpenRouter key — get one at openrouter.ai' if provider == 'openrouter' else 'Anthropic key — get one at console.anthropic.com'}")
    raw_key = input("  Key (press Enter to keep current): ").strip()
    api_key = raw_key if raw_key else cur_key
    if not api_key:
        print("Error: API key required.", file=sys.stderr)
        sys.exit(1)

    # Main model
    print("\nMain model (used for interview questions and debrief):")
    main_options = _MODELS[provider]["main"]
    cur_main = existing.get("model", main_options[0][0])
    default_main = next((i for i, (v, _) in enumerate(main_options) if v == cur_main), 0)
    model = _pick_from_menu(main_options, "  Choice", default_main)

    # Fast model
    print("\nFast model (used for claim extraction and evasion scoring):")
    fast_options = _MODELS[provider]["fast"]
    cur_fast = existing.get("fast_model", fast_options[0][0])
    default_fast = next((i for i, (v, _) in enumerate(fast_options) if v == cur_fast), 0)
    fast_model = _pick_from_menu(fast_options, "  Choice", default_fast)

    cfg = {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "fast_model": fast_model,
    }
    _save_config(cfg)
    print(f"\n  Saved to {_CONFIG_PATH}")
    print(f"  Provider:   {provider}")
    print(f"  Model:      {model}")
    print(f"  Fast model: {fast_model}")
    print()
    return cfg


def _make_client() -> tuple[anthropic.Anthropic, str, str, str]:
    """Return (client, provider, main_model, fast_model).
    Priority: env vars > config.json > setup wizard."""

    # 1. Env vars (backwards compat)
    or_key = os.environ.get("OPENROUTER_API_KEY")
    ant_key = os.environ.get("ANTHROPIC_API_KEY")
    if or_key:
        model = os.environ.get("OPENROUTER_MODEL", _MODELS["openrouter"]["main"][0][0])
        fast  = os.environ.get("OPENROUTER_FAST_MODEL", _MODELS["openrouter"]["fast"][0][0])
        return anthropic.Anthropic(api_key=or_key, base_url=OPENROUTER_BASE), "openrouter", model, fast
    if ant_key:
        model = _MODELS["anthropic"]["main"][0][0]
        fast  = _MODELS["anthropic"]["fast"][0][0]
        return anthropic.Anthropic(api_key=ant_key), "anthropic", model, fast

    # 2. Config file (or first-run setup)
    cfg = _load_config()
    if not cfg:
        print("No config found — running setup (you only do this once).")
        cfg = run_setup()

    provider   = cfg["provider"]
    api_key    = cfg["api_key"]
    model      = cfg["model"]
    fast_model = cfg["fast_model"]

    if provider == "openrouter":
        client = anthropic.Anthropic(api_key=api_key, base_url=OPENROUTER_BASE)
    else:
        client = anthropic.Anthropic(api_key=api_key)

    return client, provider, model, fast_model


def _call(
    client: anthropic.Anthropic,
    provider: str,
    model: str,
    max_tokens: int,
    system_blocks: list[dict],
    messages: list[dict],
) -> str:
    """Unified API call — strips cache_control for OpenRouter."""
    if provider == "openrouter":
        # OpenRouter doesn't support cache_control; strip it
        clean_blocks = [{k: v for k, v in b.items() if k != "cache_control"} for b in system_blocks]
    else:
        clean_blocks = system_blocks
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=clean_blocks,
        messages=messages,
    )
    return resp.content[0].text


# Wire formats module so it can make API calls
fmt_module.init(_call)

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

A <pressure> tag will appear before each answer indicating your current intensity level.
You MUST match that level exactly — not warmer, not cooler. The levels are:

  LEVEL 1 — MEASURED: Professional, unhurried. Build credibility. Let them talk.
  LEVEL 2 — FIRM: Name the dodge plainly. Short sentences. No pleasantries.
  LEVEL 3 — HARD: Repeat the unanswered question verbatim. Express visible impatience.
             "That's not an answer. [question again, word for word.]"
  LEVEL 4 — RELENTLESS: Tally the evasions out loud. Refuse to move on.
             "You have now avoided this [N] times. I'm going to keep asking."
  LEVEL 5 — MAXIMUM: Full confrontation. The record is the story now.
             "At this point your refusal to answer IS the answer. On the record:
              you were asked [X] and you declined to answer."

Your opening move: greet the subject by acknowledging the topic, then ask the
single most uncomfortable question you can build from the briefing material.
Do not warm up slowly. Start where it matters."""

# Descriptions shown in the status bar for each pressure level
PRESSURE_LABELS = {
    1: "measured",
    2: "firm",
    3: "hard",
    4: "relentless",
    5: "MAXIMUM",
}


class ClaimTracker:
    """Extracts and cross-checks factual claims across interview turns."""

    def __init__(self, client: anthropic.Anthropic, provider: str, fast_model: str):
        self.client = client
        self.provider = provider
        self.fast_model = fast_model
        self.claims: list[dict] = []

    def _fast(self, prompt: str, max_tokens: int) -> str:
        resp = self.client.messages.create(
            model=self.fast_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

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
            raw = self._fast(prompt, 512)
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                new_claims = json.loads(match.group())
                for c in new_claims:
                    c["turn"] = turn
                self.claims.extend(new_claims)
        except Exception:
            pass

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
            '{"contradiction": true, "earlier_turn": <N>, '
            '"earlier_quote": "<exact words from earlier>", '
            '"earlier_claim": "<what was claimed>", '
            '"new_quote": "<exact words from new answer>", '
            '"new_claim": "<what is now claimed>"}\n\n'
            "Claim log:\n" + "\n".join(log_lines) +
            f"\n\nNew answer:\n{answer}"
        )
        try:
            raw = self._fast(prompt, 256)
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
        return f"{len(self.claims)} claim(s)"


class PressureTracker:
    """Scores each answer for evasion and tracks cumulative interview pressure."""

    _THRESHOLDS = [(0, 1), (2, 2), (4, 3), (7, 4), (11, 5)]

    def __init__(self, client: anthropic.Anthropic, provider: str, fast_model: str):
        self.client = client
        self.provider = provider
        self.fast_model = fast_model
        self.cumulative_score: int = 0
        self.turn_scores: list[tuple[int, int]] = []
        self._last_question: str = ""

    def set_last_question(self, q: str) -> None:
        self._last_question = q

    def score_answer(self, answer: str, turn: int) -> int:
        prompt = (
            "Rate how evasive this interview answer is on a scale of 0–3.\n\n"
            "0 = Direct: concrete facts, specific names/dates/numbers, admits or denies clearly.\n"
            "1 = Partial: some substance but avoids the sharpest part of the question.\n"
            "2 = Evasive: vague generalities, deflection, pivots to talking points, "
            "non-answers dressed as answers.\n"
            "3 = Full dodge: refuses to engage, repeats prior talking point, "
            "challenges the premise without answering, or goes silent.\n\n"
            + (f"Question asked: {self._last_question}\n\n" if self._last_question else "")
            + f"Answer:\n{answer}\n\n"
            'Return a single JSON object: {"score": <0|1|2|3>, "reason": "<10 words max>"}'
        )
        try:
            resp = self.client.messages.create(
                model=self.fast_model, max_tokens=64,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            match = re.search(r"\{.*?\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                score = max(0, min(3, int(data.get("score", 0))))
                self.cumulative_score += score
                self.turn_scores.append((turn, score))
                return score
        except Exception:
            pass
        return 0

    def level(self) -> int:
        for threshold, lvl in reversed(self._THRESHOLDS):
            if self.cumulative_score >= threshold:
                return lvl
        return 1

    def evasion_count(self) -> int:
        return sum(1 for _, s in self.turn_scores if s >= 2)


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


def build_cached_system(briefing: str, format_key: str = "") -> list[dict]:
    hint = fmt_module.interview_hint(format_key)
    blocks = [{"type": "text", "text": SYSTEM_PROMPT + hint}]
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
            line, width=WIDTH,
            initial_indent=prefix if first else indent,
            subsequent_indent=indent,
        ))
        first = False


def run_interview(topic_paths: list[str], format_key: str = "") -> None:
    client, provider, model, fast_model = _make_client()
    claims = ClaimTracker(client, provider, fast_model)
    pressure = PressureTracker(client, provider, fast_model)

    briefing = load_topics(topic_paths)
    system_blocks = build_cached_system(briefing, format_key)
    history: list[dict] = []

    topic_hint = (
        ", ".join(os.path.basename(p) for p in topic_paths)
        if topic_paths else "loaded topics"
    )

    print("=" * WIDTH)
    print("REPORTER BOT — Investigative Interview Engine")
    print(f"Provider: {provider}  Model: {model}")
    if briefing:
        print(f"Briefing loaded: {topic_hint}")
    else:
        print("No briefing loaded. Running cold.")
        print("Tip: drop .md files in ./topics/ or pass paths as arguments.")
    if format_key and format_key in fmt_module.FORMATS:
        f = fmt_module.FORMATS[format_key]
        print(f"Format: {f['emoji']} {f['name']} — interview shaped for this platform")
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
    reporter_text = _call(client, provider, model, 1024, system_blocks, history)
    history.append({"role": "assistant", "content": reporter_text})
    pressure.set_last_question(reporter_text)
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
                    _run_debrief(client, provider, model, history, claims, pressure, briefing)
                    return
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print("\n[Interview ended]")
            _run_debrief(client, provider, model, history, claims, pressure, briefing)
            return

        user_answer = "\n".join(lines).strip()
        if not user_answer:
            continue

        turn += 1

        # Parallel analysis: contradiction check + evasion scoring
        contradiction = claims.check(user_answer)
        evasion_score = pressure.score_answer(user_answer, turn)
        claims.extract(user_answer, turn)

        current_level = pressure.level()
        level_label = PRESSURE_LABELS[current_level]
        evasion_count = pressure.evasion_count()

        # Status bar
        markers = ""
        if contradiction:
            markers += "  [!] CONTRADICTION"
        if evasion_score >= 2:
            markers += f"  [dodge #{evasion_count}]"
        print(
            f"  [pressure: {current_level}/5 {level_label}]"
            f"  [claims: {claims.summary()}]"
            + markers
        )
        if contradiction:
            earlier_quote = contradiction.get("earlier_quote", "")
            new_quote = contradiction.get("new_quote", "")
            earlier_turn = contradiction.get("earlier_turn", "?")
            print(f"      Turn {earlier_turn}: \"{earlier_quote}\"")
            print(f"      Now:       \"{new_quote}\"")
        print()

        # Build message for the reporter
        prefix_blocks: list[str] = []

        if contradiction:
            earlier_turn = contradiction.get("earlier_turn", "?")
            prefix_blocks.append(
                f'<contradiction turn="{earlier_turn}">\n'
                f'Earlier they said: "{contradiction.get("earlier_quote","")}"'
                f' — claiming {contradiction.get("earlier_claim","")}.\n'
                f'Now they say: "{contradiction.get("new_quote","")}"'
                f' — claiming {contradiction.get("new_claim","")}.\n'
                f"</contradiction>"
            )

        prefix_blocks.append(
            f"<pressure level=\"{current_level}\" label=\"{level_label}\""
            + (f' evasions="{evasion_count}"' if evasion_count > 0 else "")
            + " />"
        )

        message_content = "\n\n".join(prefix_blocks) + "\n\n" + user_answer

        history.append({"role": "user", "content": message_content})
        reporter_text = _call(client, provider, model, 1024, system_blocks, history)
        history.append({"role": "assistant", "content": reporter_text})
        pressure.set_last_question(reporter_text)

        print()
        wrap("REPORTER", reporter_text)
        print()


def _build_clean_transcript(history: list[dict]) -> str:
    """Return a readable transcript, stripping injected XML tags from user turns."""
    lines = []
    turn = 0
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            # Strip <contradiction ...>...</contradiction> and <pressure ... /> blocks
            content = re.sub(r"<contradiction[^>]*>.*?</contradiction>", "", content, flags=re.DOTALL)
            content = re.sub(r"<pressure[^/]*/\s*>", "", content)
            content = content.strip()
            # Skip the internal boot messages
            if content.startswith("Begin the interview") or content.startswith("Ask the subject"):
                continue
            turn += 1
            label = f"SUBJECT (Turn {turn})"
        else:
            label = "REPORTER"
        if content:
            lines.append(f"[{label}]\n{content}\n")
    return "\n".join(lines)


def generate_debrief(
    client: anthropic.Anthropic,
    provider: str,
    model: str,
    history: list[dict],
    claims: ClaimTracker,
    pressure: PressureTracker,
    briefing: str,
) -> str:
    """Generate a structured post-interview debrief report."""
    transcript = _build_clean_transcript(history)
    if not transcript.strip():
        return ""

    claim_log = ""
    if claims.claims:
        claim_log = "\n".join(
            f"  Turn {c['turn']}: {c['text']}  (\"{c['quote']}\")"
            for c in claims.claims
        )

    evasion_summary = (
        f"Total evasion score: {pressure.cumulative_score}. "
        f"Full dodges: {pressure.evasion_count()}. "
        f"Final pressure level reached: {pressure.level()}/5."
    )

    prompt = f"""You are a senior investigative editor reviewing a reporter's completed interview.
Produce a structured DEBRIEF REPORT based on the transcript and metadata below.

{"ORIGINAL BRIEFING:" + chr(10) + briefing + chr(10) if briefing else ""}
EVASION STATS: {evasion_summary}

{"CLAIM LOG (extracted during interview):" + chr(10) + claim_log + chr(10) if claim_log else ""}
TRANSCRIPT:
{transcript}

---

Write the debrief with these exact sections. Be specific — quote the subject directly wherever possible.

## ADMISSIONS
What the subject explicitly confirmed, admitted, or let slip that is newsworthy.
One bullet per admission. Quote directly.

## EVASIONS
Questions the subject refused or failed to answer directly.
For each: what was asked, how they dodged it, how many times if repeated.

## CONTRADICTIONS
Statements the subject made that contradict each other or contradict the briefing.
Quote both sides of each contradiction.

## KEY QUOTES
3–5 quotes worth publishing verbatim. Tag each: [damaging] [revealing] [defensive] [notable].

## CREDIBILITY SCORE
Rate 1–10 (10 = fully credible). Two sentences: what this subject revealed about their own reliability.

## FOLLOW-UP INVESTIGATION
Top 3–5 specific actionable leads: documents to FOIA, witnesses to find, records to subpoena, data to cross-check.

## DRAFT LEDE
Two sentences. The opening of the story this interview supports. Make it publishable."""

    return _call(
        client, provider, model, 2048,
        [{"type": "text", "text": "You are a senior investigative editor."}],
        [{"role": "user", "content": prompt}],
    )


def _run_debrief(
    client: anthropic.Anthropic,
    provider: str,
    model: str,
    history: list[dict],
    claims: ClaimTracker,
    pressure: PressureTracker,
    briefing: str,
) -> None:
    if len([m for m in history if m["role"] == "user"]) < 2:
        _print_claim_log(claims)
        return

    print("\n[Generating debrief report...]")
    report = generate_debrief(client, provider, model, history, claims, pressure, briefing)
    if not report:
        _print_claim_log(claims)
        return

    print("\n" + "=" * WIDTH)
    print("DEBRIEF REPORT")
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
    path = f"transcripts/debrief-{ts}.md"
    transcript = _build_clean_transcript(history)
    with open(path, "w") as f:
        f.write(f"# Interview Transcript — {ts}\n\n")
        f.write("## Transcript\n\n```\n")
        f.write(transcript)
        f.write("```\n\n")
        f.write("## Debrief\n\n")
        f.write(report)
        if claims.claims:
            f.write("\n\n## Claim Log\n\n")
            for c in claims.claims:
                f.write(f"- [Turn {c['turn']}] {c['text']}\n")
                f.write(f'  > "{c["quote"]}"\n')
    print(f"\n[Saved to {path}]")

    # Platform format outputs
    chosen = fmt_module.pick_formats_menu()
    if chosen:
        fmt_module.run_format_outputs(client, provider, model, transcript, briefing, chosen)


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
    args = sys.argv[1:]
    if "--setup" in args:
        run_setup(reconfigure=True)
        sys.exit(0)
    # --format <key>  e.g. --format podcast
    format_key = ""
    if "--format" in args:
        idx = args.index("--format")
        if idx + 1 < len(args):
            format_key = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
    if format_key and format_key not in fmt_module.FORMATS:
        print(f"Unknown format '{format_key}'. Options: {', '.join(fmt_module.FORMATS)}")
        sys.exit(1)
    topic_paths = [a for a in args if not a.startswith("--")]
    try:
        run_interview(topic_paths, format_key=format_key)
    except anthropic.AuthenticationError:
        print("Error: API key is invalid. Run: python reporter.py --setup", file=sys.stderr)
        sys.exit(1)
