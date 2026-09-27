"""Study row models and schema shared by the storage adapter."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from content import Choice, Condition


@dataclass(frozen=True, slots=True)
class Participant:
    id: str
    condition: Condition
    choice: Choice
    reason: str
    system_prompt: str
    model: str
    next_turn: int


@dataclass(frozen=True, slots=True)
class Turn:
    turn_index: int
    question: str
    answer: str
    word_count: int


@dataclass(frozen=True, slots=True)
class Attempt:
    id: str
    turn_index: int
    status: str
    question: str
    answer: str | None
    error_code: str | None


def initialize_schema(engine: Engine) -> None:
    statements = (
        """CREATE TABLE IF NOT EXISTS participants (
            id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
            condition TEXT NOT NULL, choice TEXT NOT NULL, reason TEXT NOT NULL,
            system_prompt TEXT NOT NULL, prompt_sha256 TEXT NOT NULL,
            model TEXT NOT NULL, created_at TEXT NOT NULL,
            completed_at TEXT, next_turn INTEGER NOT NULL DEFAULT 0,
            active_attempt_id TEXT, active_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS attempts (
            id TEXT PRIMARY KEY, participant_id TEXT NOT NULL,
            turn_index INTEGER NOT NULL, question TEXT NOT NULL,
            request_json TEXT NOT NULL, response_json TEXT,
            response_model TEXT, answer TEXT, word_count INTEGER,
            status TEXT NOT NULL, error_code TEXT, error_detail TEXT,
            started_at TEXT NOT NULL, finished_at TEXT,
            FOREIGN KEY (participant_id) REFERENCES participants(id)
        )""",
        """CREATE TABLE IF NOT EXISTS turns (
            participant_id TEXT NOT NULL, turn_index INTEGER NOT NULL,
            attempt_id TEXT NOT NULL, question TEXT NOT NULL,
            answer TEXT NOT NULL, word_count INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            PRIMARY KEY (participant_id, turn_index),
            FOREIGN KEY (participant_id) REFERENCES participants(id),
            FOREIGN KEY (attempt_id) REFERENCES attempts(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_attempts_participant ON attempts(participant_id, started_at)",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
