# Project decision study

This is the participant-facing Streamlit app for a three-question research study. The experimental instructions and credentials are supplied through Streamlit Cloud Secrets and are not stored in this repository.

Participants choose Option A or B and enter one sentence before the chat begins. Their initial view, each fixed question, and each assistant reply appear in one scrolling chat window. Each fixed question is prefilled in the composer and sent with the adjacent icon; the interface does not accept additional free-form questions.

The Qualtrics redirect must include a participation ID, for example `https://tianyu-decision-study.streamlit.app/?participant_id=${e://Field/ResponseID}`. Set `PARTICIPATION_ID_QUERY_PARAM` in Streamlit Secrets if the URL uses a different parameter name. The value is saved as `participation_id` in participant and analysis exports and is not sent to the model.

## Deployment

Use `app.py` on Python 3.12. Configure these root-level Streamlit Secrets before collecting responses:

```toml
DATABASE_URL = "postgresql://..."
DEEPSEEK_API_KEY = "..."
PROMPT_A = "..."
PROMPT_B = "..."
# Optional if Qualtrics uses a different query key:
# PARTICIPATION_ID_QUERY_PARAM = "ResponseID"
```

Each prompt must contain exactly one `{{PARTICIPANT_POSITION}}` placeholder. The app uses an external managed PostgreSQL database to retain responses across Streamlit Cloud restarts; participants and researchers do not need to install PostgreSQL. Standard `postgres://` and `postgresql://` URLs are accepted. Do not configure `ALLOW_LOCAL_SQLITE` or `DEEPSEEK_BASE_URL` in production.
