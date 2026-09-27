"""Three-round study flow; all state transitions are persisted before model calls."""

from __future__ import annotations

import json
import re
import secrets
from typing import Final

from content import QUESTIONS, Condition, InitialPosition, make_system_prompt
from llm import ChatRequest, Message, ModelProvider, ProviderError
from storage import StudyStore, Turn

MODEL: Final[str] = "deepseek-flash"


class StudyService:
    def __init__(self, store: StudyStore, provider: ModelProvider) -> None:
        self._store = store
        self._provider = provider

    def start(
        self,
        position: InitialPosition,
        condition: Condition | None = None,
        *,
        participation_id: str | None = None,
    ) -> str:
        assigned = condition or (
            Condition.B if secrets.randbelow(2) == 0 else Condition.A
        )
        prompt = make_system_prompt(assigned, position)
        return self._store.create_participant(
            assigned,
            position.choice,
            position.reason,
            prompt,
            MODEL,
            participation_id=participation_id,
        )

    def answer_next(self, token: str) -> Turn:
        participant = self._store.get_participant(token)
        if participant is None:
            raise ValueError("This study session was not found.")
        if participant.next_turn >= len(QUESTIONS):
            raise ValueError("This study session is complete.")

        question = QUESTIONS[participant.next_turn]
        messages: list[Message] = [
            {"role": "system", "content": participant.system_prompt}
        ]
        for previous in self._store.get_turns(participant.id):
            messages.extend(
                (
                    {"role": "user", "content": previous.question},
                    {"role": "assistant", "content": previous.answer},
                )
            )
        messages.append({"role": "user", "content": question})
        request = ChatRequest(model=participant.model, messages=messages)
        attempt_id = self._store.claim_turn(
            participant.id,
            participant.next_turn,
            question,
            json.dumps(request.as_record(), ensure_ascii=False),
        )
        if attempt_id is None:
            raise ValueError(
                "This question is already being processed. Please wait and try again."
            )

        try:
            result = self._provider.complete(request)
        except ProviderError as exc:
            self._store.fail_turn(
                participant.id, attempt_id, exc.code, exc.detail, exc.raw_response
            )
            raise

        word_count = len(re.findall(r"\b[\w'-]+\b", result.answer))
        committed = self._store.complete_turn(
            participant.id,
            participant.next_turn,
            attempt_id,
            question,
            result.answer,
            result.raw_response_json,
            result.response_model,
            word_count,
        )
        if not committed:
            raise ValueError("This response was superseded by a later attempt.")
        return Turn(participant.next_turn, question, result.answer, word_count)
