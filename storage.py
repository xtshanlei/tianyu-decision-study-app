"""Persistent, concurrency-safe study records for SQLite or PostgreSQL."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url

from content import Choice, Condition
from db_schema import Attempt, Participant, Turn, initialize_schema


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _engine_url(database_url: str) -> URL:
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


class StudyStore:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(
            _engine_url(database_url), pool_pre_ping=True
        )
        initialize_schema(self.engine)

    def create_participant(
        self,
        condition: Condition,
        choice: Choice,
        reason: str,
        system_prompt: str,
        model: str,
        *,
        participation_id: str | None = None,
    ) -> str:
        token = secrets.token_urlsafe(32)
        with self.engine.begin() as connection:
            connection.execute(
                text("""INSERT INTO participants
                    (id, token_hash, participation_id, condition, choice, reason, system_prompt,
                     prompt_sha256, model, created_at)
                    VALUES (:id, :token_hash, :participation_id, :condition, :choice, :reason,
                            :system_prompt, :prompt_sha256, :model, :created_at)"""),
                {
                    "id": str(uuid4()),
                    "token_hash": _token_hash(token),
                    "participation_id": participation_id,
                    "condition": condition.value,
                    "choice": choice,
                    "reason": reason,
                    "system_prompt": system_prompt,
                    "prompt_sha256": hashlib.sha256(
                        system_prompt.encode("utf-8")
                    ).hexdigest(),
                    "model": model,
                    "created_at": _now(),
                },
            )
        return token

    def get_participant(self, token: str) -> Participant | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM participants WHERE token_hash = :token_hash"),
                    {"token_hash": _token_hash(token)},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return Participant(
            id=row["id"],
            participation_id=row["participation_id"],
            condition=Condition(row["condition"]),
            choice=row["choice"],
            reason=row["reason"],
            system_prompt=row["system_prompt"],
            model=row["model"],
            next_turn=row["next_turn"],
        )

    def get_turns(self, participant_id: str) -> list[Turn]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT * FROM turns WHERE participant_id = :id ORDER BY turn_index"
                    ),
                    {"id": participant_id},
                )
                .mappings()
                .all()
            )
        return [
            Turn(row["turn_index"], row["question"], row["answer"], row["word_count"])
            for row in rows
        ]

    def get_attempts(self, participant_id: str) -> list[Attempt]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT * FROM attempts WHERE participant_id = :id ORDER BY started_at, id"
                    ),
                    {"id": participant_id},
                )
                .mappings()
                .all()
            )
        return [
            Attempt(
                row["id"],
                row["turn_index"],
                row["status"],
                row["question"],
                row["answer"],
                row["error_code"],
            )
            for row in rows
        ]

    def claim_turn(
        self, participant_id: str, turn_index: int, question: str, request_json: str
    ) -> str | None:
        attempt_id = str(uuid4())
        now = _now()
        stale_before = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
        with self.engine.begin() as connection:
            result = connection.execute(
                text("""UPDATE participants
                    SET active_attempt_id = :attempt_id, active_at = :now
                    WHERE id = :id AND next_turn = :turn_index
                    AND (active_attempt_id IS NULL OR active_at < :stale_before)"""),
                {
                    "attempt_id": attempt_id,
                    "now": now,
                    "id": participant_id,
                    "turn_index": turn_index,
                    "stale_before": stale_before,
                },
            )
            if result.rowcount != 1:
                return None
            connection.execute(
                text("""INSERT INTO attempts
                    (id, participant_id, turn_index, question, request_json, status, started_at)
                    VALUES (:id, :participant_id, :turn_index, :question,
                            :request_json, 'started', :started_at)"""),
                {
                    "id": attempt_id,
                    "participant_id": participant_id,
                    "turn_index": turn_index,
                    "question": question,
                    "request_json": request_json,
                    "started_at": now,
                },
            )
        return attempt_id

    def complete_turn(
        self,
        participant_id: str,
        turn_index: int,
        attempt_id: str,
        question: str,
        answer: str,
        response_json: str,
        response_model: str,
        word_count: int,
    ) -> bool:
        now = _now()
        with self.engine.begin() as connection:
            connection.execute(
                text("""UPDATE attempts SET status = 'completed', answer = :answer,
                    response_json = :response_json, response_model = :response_model,
                    word_count = :word_count, finished_at = :now WHERE id = :attempt_id"""),
                {
                    "answer": answer,
                    "response_json": response_json,
                    "response_model": response_model,
                    "word_count": word_count,
                    "now": now,
                    "attempt_id": attempt_id,
                },
            )
            result = connection.execute(
                text("""UPDATE participants SET next_turn = :next_turn,
                    active_attempt_id = NULL, active_at = NULL,
                    completed_at = :completed_at
                    WHERE id = :id AND active_attempt_id = :attempt_id
                    AND next_turn = :turn_index"""),
                {
                    "next_turn": turn_index + 1,
                    "completed_at": now if turn_index == 2 else None,
                    "id": participant_id,
                    "attempt_id": attempt_id,
                    "turn_index": turn_index,
                },
            )
            if result.rowcount != 1:
                return False
            connection.execute(
                text("""INSERT INTO turns
                    (participant_id, turn_index, attempt_id, question, answer, word_count, completed_at)
                    VALUES (:participant_id, :turn_index, :attempt_id, :question,
                            :answer, :word_count, :completed_at)"""),
                {
                    "participant_id": participant_id,
                    "turn_index": turn_index,
                    "attempt_id": attempt_id,
                    "question": question,
                    "answer": answer,
                    "word_count": word_count,
                    "completed_at": now,
                },
            )
        return True

    def fail_turn(
        self,
        participant_id: str,
        attempt_id: str,
        error_code: str,
        error_detail: str,
        raw_response: str | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("""UPDATE attempts SET status = 'failed', error_code = :error_code,
                    error_detail = :error_detail, response_json = :raw_response,
                    finished_at = :now WHERE id = :attempt_id"""),
                {
                    "error_code": error_code,
                    "error_detail": error_detail,
                    "raw_response": raw_response,
                    "now": _now(),
                    "attempt_id": attempt_id,
                },
            )
            connection.execute(
                text("""UPDATE participants SET active_attempt_id = NULL, active_at = NULL
                    WHERE id = :id AND active_attempt_id = :attempt_id"""),
                {"id": participant_id, "attempt_id": attempt_id},
            )
