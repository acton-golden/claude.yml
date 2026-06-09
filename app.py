"""
Reporter Bot — Streamlit web app
Run: streamlit run app.py
"""

import anthropic
import streamlit as st

from reporter import (
    _call, build_cached_system, load_topics,
    ClaimTracker, PressureTracker,
    OPENROUTER_BASE, _MODELS,
)
from panel import REPORTERS as ALL_REPORTERS
from formats import FORMATS, generate_platform_content
from voice_component import voice_turn
import formats as fmt_module

st.set_page_config(
    page_title="Reporter Bot",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRESSURE_LABELS = ["Measured", "Firm", "Hard", "Relentless", "⚠ MAXIMUM"]
REPORTER_AVATARS = {"devil": "🔴", "buddy": "🟡", "hombre": "🟢", "cobra": "⚫", "traveler": "🔵"}


# ── Session state ─────────────────────────────────────────────────────────────

def _init():
    import os
    defaults = {
        "phase": "setup",
        "api_key": os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or "",
        "provider": "openrouter" if os.environ.get("OPENROUTER_API_KEY") else "anthropic",
        "model": _MODELS["openrouter"]["main"][0][0],
        "fast_model": _MODELS["openrouter"]["fast"][0][0],
        "briefing": "",
        "format_key": "",
        "selected_reporters": [r.key for r in ALL_REPORTERS],
        "client": None,
        "histories": {},
        "systems": {},
        "chat": [],
        "transcript_entries": [],
        "transcript_text": "",
        "prev_questions": {},
        "claims": None,
        "pressure": None,
        "debrief": "",
        "format_outputs": {},
        "voice_mode": True,
        "voice_turn_key": 0,   # incremented each round so TTS re-fires
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init()
fmt_module.init(_call)


def _build_client():
    s = st.session_state
    if s.provider == "openrouter":
        return anthropic.Anthropic(api_key=s.api_key, base_url=OPENROUTER_BASE)
    return anthropic.Anthropic(api_key=s.api_key)


def _reporter_system(persona: str, briefing: str, provider: str, format_key: str) -> list[dict]:
    hint = fmt_module.interview_hint(format_key)
    blocks: list[dict] = [{"type": "text", "text": persona + hint}]
    if briefing:
        b: dict = {"type": "text", "text": f"\n\n<briefing>\n{briefing}\n</briefing>"}
        if provider != "openrouter":
            b["cache_control"] = {"type": "ephemeral"}
        blocks.append(b)
    return blocks


# ── Setup ─────────────────────────────────────────────────────────────────────

def show_setup():
    st.title("🎙 Reporter Bot")
    st.caption(
        "An AI-powered investigative interview engine. "
        "Load a topic briefing, pick your reporters, and get interrogated."
    )

    with st.sidebar:
        st.header("⚙️ Connection")

        provider = st.selectbox(
            "Provider",
            ["openrouter", "anthropic"],
            index=0 if st.session_state.provider == "openrouter" else 1,
            format_func=lambda x: "OpenRouter (recommended)" if x == "openrouter" else "Anthropic",
        )
        if provider != st.session_state.provider:
            st.session_state.provider = provider
            # Reset model to provider default
            st.session_state.model = _MODELS[provider]["main"][0][0]
            st.session_state.fast_model = _MODELS[provider]["fast"][0][0]

        api_key = st.text_input(
            "API Key", value=st.session_state.api_key, type="password",
            help="OpenRouter: openrouter.ai  |  Anthropic: console.anthropic.com",
        )
        st.session_state.api_key = api_key

        main_opts = _MODELS[provider]["main"]
        main_vals = [v for v, _ in main_opts]
        main_lbls = [l for _, l in main_opts]
        cur_m = main_vals.index(st.session_state.model) if st.session_state.model in main_vals else 0
        m_idx = st.selectbox("Interview model", range(len(main_opts)), index=cur_m,
                             format_func=lambda i: main_lbls[i])
        st.session_state.model = main_vals[m_idx]

        fast_opts = _MODELS[provider]["fast"]
        fast_vals = [v for v, _ in fast_opts]
        fast_lbls = [l for _, l in fast_opts]
        cur_f = fast_vals.index(st.session_state.fast_model) if st.session_state.fast_model in fast_vals else 0
        f_idx = st.selectbox("Analysis model", range(len(fast_opts)), index=cur_f,
                             format_func=lambda i: fast_lbls[i])
        st.session_state.fast_model = fast_vals[f_idx]

        st.divider()
        st.session_state.voice_mode = st.toggle(
            "🎤 Voice Mode",
            value=st.session_state.voice_mode,
            help="Reporters speak their questions. You answer out loud. Requires Chrome or Edge.",
        )
        if st.session_state.voice_mode:
            st.caption("Reporters speak. You speak back. Real interview feel.")

    # Main content: two columns
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("📄 Topic Briefing")
        uploaded = st.file_uploader("Upload .md briefing file", type=["md", "txt"])
        briefing = st.text_area(
            "Or paste briefing text",
            value=st.session_state.briefing,
            height=220,
            placeholder=(
                "# Topic: Your Subject\n\n"
                "## Key Facts\n- ...\n\n"
                "## Tension Points\n- ...\n\n"
                "## Questions They'll Dodge\n- ..."
            ),
        )
        if uploaded:
            st.session_state.briefing = uploaded.read().decode()
        elif briefing != st.session_state.briefing:
            st.session_state.briefing = briefing

    with col_right:
        st.subheader("🎭 Reporters")
        selected = []
        for r in ALL_REPORTERS:
            avatar = REPORTER_AVATARS.get(r.key, "⚪")
            checked = st.checkbox(
                f"{avatar} **{r.name}**",
                value=r.key in st.session_state.selected_reporters,
                key=f"sel_{r.key}",
                help=r.tagline,
            )
            if checked:
                selected.append(r.key)
        st.session_state.selected_reporters = selected

        st.divider()
        st.subheader("📤 Output Format")
        fmt_options = [""] + list(FORMATS.keys())
        fmt_labels = ["Standard debrief only"] + [
            f"{FORMATS[k]['emoji']} {FORMATS[k]['name']}" for k in FORMATS
        ]
        fmt_idx = st.selectbox(
            "Shape interview for platform",
            range(len(fmt_options)),
            format_func=lambda i: fmt_labels[i],
            index=fmt_options.index(st.session_state.format_key) if st.session_state.format_key in fmt_options else 0,
        )
        st.session_state.format_key = fmt_options[fmt_idx]
        if st.session_state.format_key:
            f = FORMATS[st.session_state.format_key]
            st.info(f"{f['emoji']} **{f['name']}** — {f['description']}")

    st.divider()

    ready = bool(st.session_state.api_key and st.session_state.selected_reporters)
    if not ready:
        st.warning("Set your API key and select at least one reporter to begin.")

    if st.button("▶  Start Interview", disabled=not ready, type="primary", use_container_width=True):
        with st.spinner("Connecting and generating opening questions..."):
            _start_interview()
        st.rerun()


def _start_interview():
    s = st.session_state
    s.client = _build_client()
    s.histories = {}
    s.systems = {}
    s.chat = []
    s.transcript_entries = []
    s.prev_questions = {}
    s.debrief = ""
    s.format_outputs = {}

    active = [r for r in ALL_REPORTERS if r.key in s.selected_reporters]
    opening = (
        "Begin the interview. Ask your single most distinctive opening question based on the briefing."
        if s.briefing else
        "Ask the subject what they want to be interviewed about, then ask your first probing question."
    )

    for r in active:
        s.systems[r.key] = _reporter_system(r.persona, s.briefing, s.provider, s.format_key)
        history = [{"role": "user", "content": opening}]
        q = _call(s.client, s.provider, s.model, 512, s.systems[r.key], history)
        history.append({"role": "assistant", "content": q})
        s.histories[r.key] = history
        s.chat.append({"role": "reporter", "reporter_name": r.name, "reporter_key": r.key, "content": q})
        s.transcript_entries.append({"type": "q", "reporter": r.name, "text": q})
        s.prev_questions[r.key] = q

    s.claims = ClaimTracker(s.client, s.provider, s.fast_model)
    s.pressure = PressureTracker(s.client, s.provider, s.fast_model)
    if s.chat:
        s.pressure.set_last_question(s.chat[-1]["content"])
    s.phase = "interview"


# ── Interview ─────────────────────────────────────────────────────────────────

def show_interview():
    s = st.session_state
    active = [r for r in ALL_REPORTERS if r.key in s.selected_reporters]

    # Status bar
    level = s.pressure.level() if s.pressure else 1
    claims_n = len(s.claims.claims) if s.claims else 0
    evasions = s.pressure.evasion_count() if s.pressure else 0

    col_h, col_p, col_c, col_e, col_end = st.columns([3, 1, 1, 1, 1])
    with col_h:
        st.title("🎙 Interview")
    with col_p:
        st.metric("Pressure", f"{level}/5", delta=PRESSURE_LABELS[level - 1], delta_color="off")
    with col_c:
        st.metric("Claims", claims_n)
    with col_e:
        st.metric("Dodges", evasions)
    with col_end:
        st.write("")
        if st.button("⏹ End", use_container_width=True):
            _finish_interview()
            st.rerun()
            return

    # Chat
    for msg in s.chat:
        if msg["role"] == "reporter":
            avatar = REPORTER_AVATARS.get(msg.get("reporter_key", ""), "⚪")
            with st.chat_message("assistant", avatar=avatar):
                st.markdown(f"**{msg['reporter_name']}**")
                st.write(msg["content"])
        else:
            with st.chat_message("user"):
                st.write(msg["content"])

    # Input — voice or text
    answer = None
    if s.voice_mode and s.chat:
        # Find the latest reporter message to speak
        latest = next(
            (m for m in reversed(s.chat) if m["role"] == "reporter"), None
        )
        if latest:
            answer = voice_turn(
                question=latest["content"],
                reporter_name=latest["reporter_name"],
                reporter_key=latest.get("reporter_key", "devil"),
                key=f"voice_{s.voice_turn_key}",
            )
    else:
        answer = st.chat_input("Your answer...")

    if answer:
        if answer.strip().lower() in ("end", "quit", "done", "finish", "/end"):
            _finish_interview()
            st.rerun()
            return

        s.chat.append({"role": "user", "content": answer})
        s.transcript_entries.append({"type": "a", "reporter": None, "text": answer})

        # Analysis
        contradiction = s.claims.check(answer)
        turn_n = sum(1 for m in s.chat if m["role"] == "user")
        s.pressure.score_answer(answer, turn_n)
        s.claims.extract(answer, turn_n)

        if contradiction:
            eq = contradiction.get("earlier_quote", "")
            nq = contradiction.get("new_quote", "")
            et = contradiction.get("earlier_turn", "?")
            st.warning(f"⚠️ **Contradiction — Turn {et}:** \"{eq}\" vs now: \"{nq}\"")

        # Next questions
        current_level = s.pressure.level()
        level_label = ["measured","firm","hard","relentless","MAXIMUM"][current_level - 1]

        for r in active:
            if r.key not in s.histories:
                continue
            others = [
                f"  {rep.name}: \"{s.prev_questions.get(rep.key,'')[:80]}\""
                for rep in active if rep.key != r.key and rep.key in s.prev_questions
            ]
            trigger = f"Subject's answer:\n{answer}"
            if others:
                trigger += "\n\n[Other reporters:\n" + "\n".join(others) + "\n]"
            if contradiction:
                et = contradiction.get("earlier_turn", "?")
                trigger = (
                    f'<contradiction turn="{et}">\n'
                    f'Earlier: "{contradiction.get("earlier_quote","")}" — {contradiction.get("earlier_claim","")}\n'
                    f'Now: "{contradiction.get("new_quote","")}" — {contradiction.get("new_claim","")}\n'
                    f'</contradiction>\n\n' + trigger
                )
            trigger += f'\n\n<pressure level="{current_level}" label="{level_label}" />\n\nAsk your next question.'

            s.histories[r.key].append({"role": "user", "content": trigger})
            q = _call(s.client, s.provider, s.model, 512, s.systems[r.key], s.histories[r.key])
            s.histories[r.key].append({"role": "assistant", "content": q})
            s.chat.append({"role": "reporter", "reporter_name": r.name, "reporter_key": r.key, "content": q})
            s.transcript_entries.append({"type": "q", "reporter": r.name, "text": q})
            s.prev_questions[r.key] = q

        s.pressure.set_last_question(
            next((m["content"] for m in reversed(s.chat) if m["role"] == "reporter"), "")
        )
        s.voice_turn_key += 1  # trigger TTS re-fire on next render
        st.rerun()


def _finish_interview():
    s = st.session_state
    tx_lines = []
    for e in s.transcript_entries:
        if e["type"] == "q":
            tx_lines.append(f"[{e['reporter'].upper()}]\n{e['text']}")
        else:
            tx_lines.append(f"[SUBJECT]\n{e['text']}")
    s.transcript_text = "\n\n".join(tx_lines)

    cl_log = "\n".join(
        f"  Turn {c['turn']}: {c['text']}  (\"{c['quote']}\")"
        for c in (s.claims.claims if s.claims else [])
    )
    ev_summary = (
        f"Evasion score: {s.pressure.cumulative_score}. "
        f"Dodges: {s.pressure.evasion_count()}. "
        f"Peak pressure: {s.pressure.level()}/5."
    ) if s.pressure else ""

    reporter_list = "\n".join(
        f"  - {r.name}: {r.tagline}"
        for r in ALL_REPORTERS if r.key in s.selected_reporters
    )

    prompt = (
        f"You are a senior investigative editor.\n\n"
        f"Reporters: {reporter_list}\n"
        + (f"BRIEFING:\n{s.briefing}\n\n" if s.briefing else "")
        + (f"EVASION STATS: {ev_summary}\n\n" if ev_summary else "")
        + (f"CLAIM LOG:\n{cl_log}\n\n" if cl_log else "")
        + f"TRANSCRIPT:\n{s.transcript_text}\n\n"
        "Write a DEBRIEF REPORT:\n"
        "## ADMISSIONS\n## EVASIONS\n## CONTRADICTIONS\n"
        "## KEY QUOTES (3–5, tagged [damaging] [revealing] [defensive] [notable])\n"
        "## CREDIBILITY SCORE (1–10 + two sentences)\n"
        "## FOLLOW-UP INVESTIGATION (3–5 specific leads)\n"
        "## DRAFT LEDE (two publishable sentences)"
    )
    try:
        s.debrief = _call(
            s.client, s.provider, s.model, 2048,
            [{"type": "text", "text": "You are a senior investigative editor."}],
            [{"role": "user", "content": prompt}],
        )
    except Exception as e:
        s.debrief = f"Error generating debrief: {e}"
    s.phase = "debrief"


# ── Debrief ───────────────────────────────────────────────────────────────────

def show_debrief():
    s = st.session_state

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title("📋 Debrief")
    with col_btn:
        st.write("")
        if st.button("🔄 New Interview", use_container_width=True):
            for k in ["phase","chat","histories","systems","claims","pressure",
                      "transcript_entries","transcript_text","debrief","format_outputs","prev_questions"]:
                st.session_state.pop(k, None)
            st.rerun()

    tab_debrief, tab_tx, tab_platforms = st.tabs(["📋 Debrief", "📝 Transcript", "📤 Platform Outputs"])

    with tab_debrief:
        if s.debrief:
            st.markdown(s.debrief)
            st.download_button("⬇ Download", s.debrief, "debrief.md", "text/markdown")
        else:
            st.info("No debrief yet.")

    with tab_tx:
        tx = s.transcript_text or ""
        st.code(tx, language=None)
        if tx:
            st.download_button("⬇ Download Transcript", tx, "transcript.txt", "text/plain")

    with tab_platforms:
        st.subheader("Generate Platform Content")
        st.caption("Select platforms and generate ready-to-post content from the interview transcript.")

        keys = list(FORMATS.keys())
        # Show checkboxes in a 3-column grid
        cols = st.columns(3)
        chosen = []
        for i, key in enumerate(keys):
            f = FORMATS[key]
            with cols[i % 3]:
                already = key in s.format_outputs
                label = f"{f['emoji']} {f['name']}" + (" ✓" if already else "")
                if st.checkbox(label, key=f"gen_{key}", value=already, help=f["description"]):
                    chosen.append(key)

        new_chosen = [k for k in chosen if k not in s.format_outputs]
        if new_chosen:
            if st.button(f"⚡ Generate {len(new_chosen)} format(s)", type="primary"):
                for key in new_chosen:
                    f = FORMATS[key]
                    with st.spinner(f"Generating {f['emoji']} {f['name']}..."):
                        try:
                            s.format_outputs[key] = generate_platform_content(
                                s.client, s.provider, s.model,
                                s.transcript_text, s.briefing, key,
                            )
                        except Exception as e:
                            s.format_outputs[key] = f"Error: {e}"
                st.rerun()

        for key in keys:
            if key not in s.format_outputs:
                continue
            f = FORMATS[key]
            with st.expander(f"{f['emoji']} {f['name']}", expanded=True):
                st.markdown(s.format_outputs[key])
                st.download_button(
                    f"⬇ Download {f['name']}",
                    s.format_outputs[key],
                    f"{key}-output.md",
                    "text/markdown",
                    key=f"dl_{key}",
                )


# ── Router ────────────────────────────────────────────────────────────────────

{
    "setup": show_setup,
    "interview": show_interview,
    "debrief": show_debrief,
}.get(st.session_state.phase, show_setup)()
