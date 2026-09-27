# Project decision study

This is the participant-facing Streamlit app for a three-question research study. The experimental instructions and credentials are supplied through Streamlit Cloud Secrets and are not stored in this repository.

Participants choose Option A or B and enter one sentence before the chat begins. Their initial view, each fixed question, and each assistant reply appear in one chronological chat transcript. The interface does not accept additional free-form questions.

## Deployment

Use `app.py` on Python 3.12. Configure these root-level Streamlit Secrets before collecting responses:

```toml
DATABASE_URL = "postgresql://..."
DEEPSEEK_API_KEY = "..."
PROMPT_A = "..."
PROMPT_B = "..."
```

Each prompt must contain exactly one `{{PARTICIPANT_POSITION}}` placeholder. The app uses an external managed PostgreSQL database to retain responses across Streamlit Cloud restarts; participants and researchers do not need to install PostgreSQL. Standard `postgres://` and `postgresql://` URLs are accepted. Do not configure `ALLOW_LOCAL_SQLITE` or `DEEPSEEK_BASE_URL` in production.
