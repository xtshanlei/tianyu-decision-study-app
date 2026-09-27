"""Participant-facing Streamlit app for the three-question study."""

from __future__ import annotations

import os

import streamlit as st

from content import (
    CASE_CLOSE,
    CASE_TEXT,
    OPTION_A,
    OPTION_B,
    QUESTIONS,
    InitialPosition,
    PromptConfigurationError,
)
from llm import DeepSeekProvider, ProviderError
from storage import StudyStore
from study import StudyService

st.set_page_config(
    page_title="Project decision study",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root {
  --canvas: #FAF9F7; --surface: #FFFFFF; --text: #242320;
  --muted: #62605C; --border: #E7E4DF; --action: #2E4A46;
  --action-hover: #233B37; --radius: 8px;
}
[data-testid="stAppViewContainer"] { background: var(--canvas); color: var(--text); }
[data-testid="stToolbar"], [data-testid="stMainMenu"] { display: none; }
.block-container { max-width: 760px; padding-top: 52px; padding-bottom: 64px; }
h1 { font-family: Georgia, serif !important; font-size: 32px !important; letter-spacing: -0.02em; line-height: 1.15; }
p, label { line-height: 1.55; }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--surface); border-color: var(--border) !important; border-radius: var(--radius) !important; }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background: var(--action); border-color: var(--action); border-radius: var(--radius); }
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover { background: var(--action-hover); border-color: var(--action-hover); }
[data-testid="stCaptionContainer"] { color: var(--muted); font-size: 13px; }
@media (max-width: 600px) { .block-container { padding: 28px 16px 48px; } }
</style>
""",
    unsafe_allow_html=True,
)


def setting(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        secret = st.secrets.get(name)
    except FileNotFoundError:
        return None
    return str(secret) if secret else None


@st.cache_resource
def store_for(database_url: str) -> StudyStore:
    return StudyStore(database_url)


st.caption("RESEARCH STUDY  /  PROJECT DECISION")
st.title("A project decision")
st.write(
    "Please read the situation below, then share your initial view before speaking with the assistant."
)

with st.container(border=True):
    st.markdown("**The situation**")
    st.write(CASE_TEXT)
    st.markdown(f"**Option A:** {OPTION_A}")
    st.markdown(f"**Option B:** {OPTION_B}")
    st.write(CASE_CLOSE)

database_url = setting("DATABASE_URL")
api_key = setting("DEEPSEEK_API_KEY")
if not database_url or not api_key:
    st.error("The study is temporarily unavailable. Please contact the researcher.")
    st.stop()
if database_url.startswith("sqlite") and setting("ALLOW_LOCAL_SQLITE") != "1":
    st.error("The study is temporarily unavailable. Please contact the researcher.")
    st.stop()

store = store_for(database_url)
token = st.query_params.get("session")
participant = store.get_participant(token) if token else None

if token and participant is None:
    st.error("This study link could not be found. Please contact the researcher.")
    st.stop()

if participant is None:
    st.subheader("Your initial view")
    with st.form("initial_position"):
        choice = st.radio(
            "Which approach are you leaning toward?",
            options=("Option A", "Option B"),
            index=None,
        )
        reason = st.text_input(
            "In one sentence, why?",
            max_chars=500,
            placeholder="Write your reason in one sentence.",
        )
        submitted = st.form_submit_button(
            "Continue", type="primary", use_container_width=True
        )
    st.caption(
        "Your initial view and the assistant's answers are recorded for research."
    )
    if submitted:
        if choice is None or not reason.strip():
            st.error("Choose an approach and enter your reason before continuing.")
        else:
            try:
                position = InitialPosition("A" if choice == "Option A" else "B", reason)
            except ValueError as exc:
                st.error(str(exc))
            else:
                service = StudyService(
                    store,
                    DeepSeekProvider(
                        api_key,
                        setting("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
                    ),
                )
                try:
                    st.query_params["session"] = service.start(position)
                except PromptConfigurationError:
                    st.error("The study is temporarily unavailable. Please contact the researcher.")
                else:
                    st.rerun()
    st.stop()

st.divider()
st.caption(f"ROUND {min(participant.next_turn + 1, 3)} OF 3")
st.progress(participant.next_turn / 3)
for turn in store.get_turns(participant.id):
    with st.container(border=True):
        st.caption(f"QUESTION {turn.turn_index + 1}")
        st.write(turn.question)
        st.caption("ASSISTANT")
        st.write(turn.answer)

if participant.next_turn == len(QUESTIONS):
    st.success("Thank you. You have completed all three questions.")
    st.stop()

st.write("Select the next question to hear the assistant's response.")
next_question = QUESTIONS[participant.next_turn]
if st.button(next_question, type="primary", use_container_width=True):
    service = StudyService(
        store,
        DeepSeekProvider(
            api_key, setting("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        ),
    )
    with st.spinner("Preparing the assistant's response..."):
        try:
            if token is None:
                raise ValueError("This study session was not found.")
            service.answer_next(token)
        except ProviderError:
            st.error("The assistant could not respond. Please try this question again.")
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.rerun()
