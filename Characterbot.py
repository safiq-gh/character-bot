"""
Human-Like AI Chat — Claude Code Edition (Fixed)
- IBM Plex Mono (no pixel font artifacts)
- Manual HTML message rows (no avatar bleed)
- Orange/black terminal aesthetic
"""

import random
import html as html_lib
import streamlit as st
import ollama
from dataclasses import dataclass, field
from typing import List, Dict, Generator

# ============================================================
# DOMAIN MODELS
# ============================================================

@dataclass
class BehaviorConfig:
    enable_memory: bool = True
    enable_openers: bool = True
    temperature: float = 0.7


@dataclass
class CognitiveState:
    emotion_history: List[str] = field(default_factory=list)
    memory_turns: List[Dict] = field(default_factory=list)
    theme_fragments: List[str] = field(default_factory=list)


# ============================================================
# EMOTION ENGINE
# ============================================================

EMOTION_KEYWORDS = {
    "curious":   ["how", "why", "what if", "explain", "?"],
    "warm":      ["thank", "love", "grateful"],
    "energetic": ["!", "great", "awesome"],
    "pensive":   ["think", "reflect", "meaning"],
    "uncertain": ["not sure", "maybe", "might"],
}

def detect_emotion(text: str) -> str:
    text = text.lower()
    scores = {k: 0 for k in EMOTION_KEYWORDS}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[emotion] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"

def blend_emotion(history: List[str]) -> str:
    if not history:
        return "neutral"
    return history[-1] if random.random() < 0.7 else random.choice(history[-3:])


# ============================================================
# MEMORY ENGINE
# ============================================================

MAX_TURNS = 6
FORGET_RATE = 0.25

def update_memory(state: CognitiveState, role: str, content: str):
    state.memory_turns.append({"role": role, "content": content})
    state.memory_turns = state.memory_turns[-(MAX_TURNS * 2):]
    if role == "user":
        words = content.split()
        filtered = [w for w in words if random.random() > FORGET_RATE or len(w) > 5]
        fragment = " ".join(filtered[:10])
        state.theme_fragments.append(fragment)
        state.theme_fragments = state.theme_fragments[-8:]

def memory_summary(state: CognitiveState) -> str:
    if not state.theme_fragments:
        return ""
    return "Recent themes: " + "; ".join(state.theme_fragments[-4:])


# ============================================================
# PERSONALITY ENGINE
# ============================================================

OPINION_OPENERS     = ["I think ", "Honestly, ", "From where I stand, ", "I'd say ", "My sense is that "]
REFLECTIVE_PAUSES   = ["Hmm. ", "Let me think. ", "Okay, so — ", ""]
UNCERTAINTY_PHRASES = ["I'm not entirely sure, but ", "I could be wrong here — "]

def build_system_prompt(emotion: str, memory_text: str) -> str:
    tone_map = {
        "neutral":   "Stay natural and grounded.",
        "curious":   "Show curiosity and mild engagement.",
        "warm":      "Be warm and human.",
        "pensive":   "Sound reflective.",
        "energetic": "Be sharp and energetic.",
        "uncertain": "Allow slight uncertainty.",
    }
    tone = tone_map.get(emotion, tone_map["neutral"])
    base = (
        "You are a thoughtful human speaking naturally. "
        "Use first-person language. Avoid lists and headers. "
        "Vary sentence length. Don't over-explain. "
        "Never say you're an AI."
    )
    return f"{base} {tone} {memory_text}"

def post_process(text: str, emotion: str, config: BehaviorConfig) -> str:
    text = text.strip()
    if config.enable_openers and len(text.split()) > 6:
        roll = random.random()
        if emotion == "pensive" and roll < 0.5:
            text = random.choice(REFLECTIVE_PAUSES) + text
        elif emotion == "uncertain" and roll < 0.5:
            text = random.choice(UNCERTAINTY_PHRASES) + text
        elif roll < 0.2:
            text = random.choice(OPINION_OPENERS) + text
    return text


# ============================================================
# LLM LAYER
# ============================================================

def stream_llm(model: str, messages: List[Dict], system_prompt: str, temperature: float) -> Generator[str, None, None]:
    payload = [{"role": "system", "content": system_prompt}] + messages
    stream = ollama.chat(
        model=model,
        messages=payload,
        options={"temperature": temperature},
        stream=True
    )
    for chunk in stream:
        token = chunk["message"]["content"]
        if token:
            yield token


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Claudex",
    page_icon="■",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS
# ============================================================

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">

<style>
:root {
  --bg:          #000000;
  --bg2:         #080808;
  --border:      #1c1c1c;
  --border2:     #282828;
  --orange:      #e8720c;
  --orange2:     #ff9535;
  --orange-lo:   rgba(232,114,12,0.08);
  --dim:         #505048;
  --dimmer:      #282824;
  --fg:          #dedad2;
  --fg2:         #80807a;
  --mono:        'IBM Plex Mono', 'Courier New', monospace;
}

html, body, [class*="css"] {
  font-family: var(--mono) !important;
  background: var(--bg) !important;
  color: var(--fg) !important;
}

/* subtle scanlines */
body::after {
  content: '';
  position: fixed; inset: 0;
  background: repeating-linear-gradient(
    0deg, transparent, transparent 2px,
    rgba(0,0,0,0.035) 2px, rgba(0,0,0,0.035) 4px
  );
  pointer-events: none;
  z-index: 99999;
}

.main .block-container {
  max-width: 800px !important;
  padding: 0 1.5rem 5rem !important;
  background: var(--bg) !important;
}
[data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }

/* ── STATUS BAR ── */
.cc-bar {
  background: var(--orange);
  color: #000;
  font-size: 0.72rem;
  font-weight: 500;
  padding: 0.28rem 1rem;
  margin: 0 -1.5rem;
  letter-spacing: 0.04em;
}
.cc-bar b { font-weight: 700; }

/* ── LOGO ── */
.cc-logo-wrap {
  padding: 2rem 0 1.5rem;
  border-bottom: 1px solid var(--border);
}
.cc-logo-line {
  font-family: var(--mono) !important;
  font-size: clamp(2.2rem, 6vw, 3.4rem);
  font-weight: 600;
  color: var(--orange);
  line-height: 1.1;
  letter-spacing: 0.2em;
  display: block;
  text-shadow:
    1px 1px 0 #6b3406,
    2px 2px 0 #4a2404,
    3px 3px 0 #2e1602,
    0   0  16px rgba(232,114,12,0.2);
}

/* ── INTRO ── */
.cc-intro {
  padding: 1.3rem 0 0.5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.4rem;
}
.cc-intro p {
  font-size: 0.87rem;
  color: var(--fg);
  line-height: 1.75;
  margin: 0 0 0.35rem;
}
.cc-intro .hint { margin-top: 0.8rem; }
.cc-intro .hint em { color: var(--orange); font-style: normal; }

/* ── MESSAGE ROWS ── */
/* Hide ALL default Streamlit chat UI */
[data-testid="stChatMessage"],
[data-testid="chatAvatarIcon-user"],
[data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessageContent"] {
  display: none !important;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  padding: 0.6rem 0.9rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.9rem;
  line-height: 1.8;
  margin: 0 -0.2rem;
  gap: 0.5rem;
}
.msg-row.user-row {
  border-left: 3px solid var(--orange);
  background: var(--orange-lo);
}
.msg-row.ai-row {
  border-left: 3px solid var(--border2);
}
.msg-prefix {
  font-size: 0.8rem;
  font-weight: 600;
  min-width: 1.4rem;
  padding-top: 0.08rem;
  flex-shrink: 0;
  user-select: none;
}
.msg-prefix.u { color: var(--orange); }
.msg-prefix.a { color: var(--dim); }
.msg-body { flex: 1; color: var(--fg); word-break: break-word; }

/* ── STREAM WRAPPER ── */
.stream-wrap {
  border-left: 3px solid var(--border2);
  padding: 0.6rem 0.9rem;
  border-bottom: 1px solid var(--border);
  margin: 0 -0.2rem;
  font-size: 0.9rem;
  line-height: 1.8;
}
.stream-tag {
  font-size: 0.78rem;
  color: var(--dim);
  font-weight: 600;
  margin-bottom: 0.15rem;
}

/* ── CHAT INPUT ── */
[data-testid="stChatInput"] {
  background: var(--bg) !important;
  border-top: 1px solid var(--border) !important;
  padding-top: 0.55rem !important;
}
[data-testid="stChatInputTextArea"] textarea {
  background: var(--bg) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 0 !important;
  color: var(--fg) !important;
  font-family: var(--mono) !important;
  font-size: 0.88rem !important;
  caret-color: var(--orange) !important;
  padding: 0.6rem 1rem !important;
}
[data-testid="stChatInputTextArea"] textarea:focus {
  border-color: var(--orange) !important;
  box-shadow: 0 0 0 1px rgba(232,114,12,0.15) !important;
  outline: none !important;
}
textarea::placeholder { color: var(--dimmer) !important; }
[data-testid="stChatInputSubmitButton"] button {
  background: transparent !important;
  border: 1px solid var(--border2) !important;
  border-radius: 0 !important;
  color: var(--orange) !important;
}
[data-testid="stChatInputSubmitButton"] button:hover {
  background: var(--orange-lo) !important;
  border-color: var(--orange) !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { font-family: var(--mono) !important; }
[data-testid="stSidebar"] h3 {
  font-size: 0.66rem !important;
  font-weight: 600 !important;
  color: var(--orange) !important;
  letter-spacing: 0.15em !important;
  text-transform: uppercase !important;
  border-bottom: 1px solid var(--border) !important;
  padding-bottom: 0.5rem !important;
  margin-bottom: 1rem !important;
}
[data-testid="stSidebar"] label {
  font-size: 0.68rem !important;
  color: var(--fg2) !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: var(--bg) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 0 !important;
  font-size: 0.82rem !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: var(--orange) !important;
  border-color: var(--orange) !important;
}
[data-testid="stToggle"] [role="switch"]                     { background: var(--border2) !important; }
[data-testid="stToggle"] [role="switch"][aria-checked="true"]{ background: var(--orange)  !important; }
[data-testid="stSidebar"] button {
  background: transparent !important;
  border: 1px solid var(--border2) !important;
  border-radius: 0 !important;
  color: var(--fg2) !important;
  font-size: 0.68rem !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  padding: 0.4rem 0.8rem !important;
  width: 100% !important;
  margin-top: 0.2rem !important;
  transition: all 0.1s !important;
}
[data-testid="stSidebar"] button:hover {
  border-color: var(--orange) !important;
  color: var(--orange) !important;
  background: var(--orange-lo) !important;
}
.sb-head { font-size: 0.6rem; color: var(--dimmer); letter-spacing: 0.12em; text-transform: uppercase; margin: 1rem 0 0.28rem; }
.sb-chip { display: inline-block; font-size: 0.66rem; padding: 0.14rem 0.42rem; border: 1px solid; letter-spacing: 0.05em; }
.c-on  { color: var(--orange); border-color: #6b3406; background: rgba(232,114,12,0.08); }
.c-off { color: var(--fg2);    border-color: var(--border2); }
.sb-frag { font-size: 0.66rem; color: var(--dim); line-height: 1.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sb-frag::before { content: "· "; color: var(--border2); }
.sb-stat { font-size: 0.68rem; color: var(--dimmer); line-height: 2.1; }
.sb-stat span { color: var(--fg2); }

/* ── MISC ── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 0.65rem 0 !important; }
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); }
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stDecoration"]          { display: none !important; }

/* ── HIDE SIDEBAR COLLAPSE BUTTON & MATERIAL ICON LEAKS ── */
[data-testid="collapsedControl"]      { display: none !important; }
[data-testid="stSidebarCollapseButton"]{ display: none !important; }
button[kind="header"]                 { display: none !important; }

/* Kill any raw Material Symbols text rendering everywhere */
[class*="material-symbols"],
[class*="material-icons"] {
  font-size: 0 !important;
  color: transparent !important;
  visibility: hidden !important;
}

/* Specifically target the sidebar chevron span */
[data-testid="stSidebar"] span[aria-hidden="true"],
section[data-testid="stSidebar"] > div > button {
  display: none !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "messages"        not in st.session_state: st.session_state.messages        = []
if "cognitive_state" not in st.session_state: st.session_state.cognitive_state = CognitiveState()
if "last_emotion"    not in st.session_state: st.session_state.last_emotion    = "neutral"
if "turn_count"      not in st.session_state: st.session_state.turn_count      = 0


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### ■ CONFIG")

    model          = st.selectbox("Model", ["gemma3:latest", "llama3:latest", "mistral:latest"])
    temperature    = st.slider("Temperature", 0.0, 1.5, 0.7, 0.05)
    enable_memory  = st.toggle("Memory Engine", True)
    enable_openers = st.toggle("Personality Openers", True)

    st.markdown("---")

    emotion  = st.session_state.last_emotion
    chip_cls = "c-on" if emotion not in ("neutral", "uncertain") else "c-off"
    tc       = st.session_state.turn_count
    frags    = st.session_state.cognitive_state.theme_fragments

    st.markdown(
        f'<div class="sb-head">State</div><span class="sb-chip {chip_cls}">{emotion.upper()}</span>',
        unsafe_allow_html=True,
    )

    if enable_memory and frags:
        st.markdown('<div class="sb-head">Memory</div>', unsafe_allow_html=True)
        for f in frags[-3:]:
            st.markdown(f'<div class="sb-frag" title="{f}">{f}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="sb-head">Session</div>'
        f'<div class="sb-stat">'
        f'turns &nbsp;&nbsp;&nbsp;<span>{tc}</span><br>'
        f'memory &nbsp;&nbsp;<span>{"on" if enable_memory else "off"}</span><br>'
        f'openers &nbsp;<span>{"on" if enable_openers else "off"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.button("✕  Clear Session"):
        st.session_state.messages        = []
        st.session_state.cognitive_state = CognitiveState()
        st.session_state.last_emotion    = "neutral"
        st.session_state.turn_count      = 0
        st.rerun()


# ============================================================
# CONFIG OBJECT
# ============================================================

config = BehaviorConfig(
    enable_memory=enable_memory,
    enable_openers=enable_openers,
    temperature=temperature,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="cc-bar">★&nbsp;&nbsp;Welcome to <b>human-ai</b> research preview!</div>',
    unsafe_allow_html=True,
)

st.markdown("""
<div class="cc-logo-wrap">
  <span class="cc-logo-line">CLAUDEX</span>
  <span class="cc-logo-line">AI</span>
</div>
""", unsafe_allow_html=True)


# ============================================================
# INTRO
# ============================================================

if not st.session_state.messages:
    st.markdown("""
    <div class="cc-intro">
      <p>Claudex uses your local Ollama instance for inference.</p>
      <p>No data leaves your machine.</p>
      <p class="hint"><em>Press Enter</em> to start a conversation.</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# RENDER MESSAGES
# ============================================================

def render_msg(role: str, content: str):
    safe = html_lib.escape(content).replace("\n", "<br>")
    if role == "user":
        st.markdown(
            f'<div class="msg-row user-row">'
            f'<span class="msg-prefix u">&gt;</span>'
            f'<span class="msg-body">{safe}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="msg-row ai-row">'
            f'<span class="msg-prefix a">◆</span>'
            f'<span class="msg-body">{safe}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

for msg in st.session_state.messages:
    render_msg(msg["role"], msg["content"])


# ============================================================
# INPUT
# ============================================================

user_input = st.chat_input("Type a message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    render_msg("user", user_input)

    state   = st.session_state.cognitive_state
    emotion = detect_emotion(user_input)
    state.emotion_history.append(emotion)
    blended = blend_emotion(state.emotion_history)
    st.session_state.last_emotion = blended

    if config.enable_memory:
        update_memory(state, "user", user_input)

    memory_text   = memory_summary(state) if config.enable_memory else ""
    system_prompt = build_system_prompt(blended, memory_text)

    # Streaming — inside styled wrapper
    st.markdown('<div class="stream-wrap"><div class="stream-tag">◆</div>', unsafe_allow_html=True)

    raw_chunks: list = []

    def token_gen():
        for token in stream_llm(model, st.session_state.messages, system_prompt, temperature):
            raw_chunks.append(token)
            yield token

    st.write_stream(token_gen())
    st.markdown('</div>', unsafe_allow_html=True)

    raw_reply   = "".join(raw_chunks)
    final_reply = post_process(raw_reply, blended, config)

    st.session_state.messages.append({"role": "assistant", "content": final_reply})
    st.session_state.turn_count += 1

    if config.enable_memory:
        update_memory(state, "assistant", final_reply)

    st.rerun()