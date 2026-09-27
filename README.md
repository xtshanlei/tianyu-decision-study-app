# Project decision study

This is the participant-facing Streamlit app for a three-question research study. The experimental instructions and credentials are supplied through Streamlit Cloud Secrets and are not stored in this repository.

## Deployment

Use `app.py` on Python 3.12. Configure these root-level Streamlit Secrets before collecting responses:

```toml
DATABASE_URL = "postgresql+psycopg://..."
DEEPSEEK_API_KEY = "..."
PROMPT_A = "..."
PROMPT_B = "..."
```

Each prompt must contain exactly one `{{PARTICIPANT_POSITION}}` placeholder. The app requires an external PostgreSQL database to retain responses across Streamlit Cloud restarts. Do not configure `ALLOW_LOCAL_SQLITE` or `DEEPSEEK_BASE_URL` in production.
