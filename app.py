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
  --action-hover: #233B37; --participant: #EAF0ED; --radius: 8px;
  --title-font: Georgia, serif; --title-size: 32px; --title-leading: 1.15;
  --title-tracking: -0.02em; --body-leading: 1.55; --metadata-size: 13px;
  --content-width: 760px; --page-top: 52px; --page-bottom: 64px;
  --mobile-page-top: 28px; --mobile-page-side: 16px; --mobile-page-bottom: 48px;
  --chat-indent: 48px; --mobile-chat-indent: 18px; --chat-gap: 12px;
}
[data-testid="stAppViewContainer"] { background: var(--canvas); color: var(--text); }
[data-testid="stToolbar"], [data-testid="stMainMenu"] { display: none; }
.block-container { max-width: var(--content-width); padding-top: var(--page-top); padding-bottom: var(--page-bottom); }
h1 { font-family: var(--title-font) !important; font-size: var(--title-size) !important; letter-spacing: var(--title-tracking); line-height: var(--title-leading); }
p, label { line-height: var(--body-leading); }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--surface); border-color: var(--border) !important; border-radius: var(--radius) !important; }
[data-testid="stChatMessage"] { width: calc(100% - var(--chat-indent)) !important; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); margin: 0 var(--chat-indent) var(--chat-gap) 0; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: var(--participant); margin: 0 0 var(--chat-gap) var(--chat-indent); }
[data-testid="stChatMessageAvatarAssistant"] { background: var(--participant) !important; color: var(--action) !important; }
[data-testid="stChatMessageAvatarUser"] { background: var(--action) !important; color: var(--surface) !important; }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background: var(--action); border-color: var(--action); border-radius: var(--radius); }
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover { background: var(--action-hover); border-color: var(--action-hover); }
[data-testid="stCaptionContainer"] { color: var(--muted); font-size: var(--metadata-size); }
@media (max-width: 600px) { .block-container { padding: var(--mobile-page-top) var(--mobile-page-side) var(--mobile-page-bottom); } [data-testid="stChatMessage"] { width: calc(100% - var(--mobile-chat-indent)) !important; margin-right: var(--mobile-chat-indent); } [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { margin-left: var(--mobile-chat-indent); } }
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

with st.chat_message("assistant"):
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
                    st.error(
                        "The study is temporarily unavailable. Please contact the researcher."
                    )
                else:
                    st.rerun()
    st.stop()

assert token is not None
st.caption(f"ROUND {min(participant.next_turn + 1, 3)} OF 3")
st.progress(participant.next_turn / 3)
with st.chat_message("user"):
    st.markdown(f"**My initial view: Option {participant.choice}**")
    st.write(participant.reason)

for turn in store.get_turns(participant.id):
    with st.chat_message("user"):
        st.write(turn.question)
    with st.chat_message("assistant"):
        st.write(turn.answer)

if participant.next_turn == len(QUESTIONS):
    st.success("Thank you. You have completed all three questions.")
    st.stop()

st.caption("SELECT THE NEXT MESSAGE")
next_question = QUESTIONS[participant.next_turn]
if st.button(next_question, type="primary", use_container_width=True):
    service = StudyService(
        store,
        DeepSeekProvider(
            api_key, setting("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        ),
    )
    with st.chat_message("user"):
        st.write(next_question)
    with st.chat_message("assistant"), st.spinner("Preparing a response..."):
        try:
            service.answer_next(token)
        except ProviderError:
            st.error("The assistant could not respond. Please try this question again.")
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.rerun()
