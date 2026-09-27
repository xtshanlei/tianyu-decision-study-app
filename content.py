"""The fixed study case, questions, and condition prompt snapshots."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

Choice = Literal["A", "B"]


class Condition(StrEnum):
    A = "a"
    B = "b"


class PromptConfigurationError(RuntimeError):
    """The assigned condition prompt is unavailable or malformed."""


@dataclass(frozen=True, slots=True)
class InitialPosition:
    choice: Choice
    reason: str

    def __post_init__(self) -> None:
        reason = self.reason.strip()
        if not reason or len(reason) > 500:
            raise ValueError(
                "Please enter one sentence of no more than 500 characters."
            )
        if any(mark in reason[:-1] for mark in ".!?"):
            raise ValueError("Please enter a single sentence.")
        object.__setattr__(self, "reason", reason)


CASE_TEXT: Final[str] = (
    "You are a project team member involved in planning a new project. "
    "The team is preparing for the early stages of the project and needs to decide "
    "how to allocate its limited resources during the initial phase."
)

OPTION_A: Final[str] = (
    "Allocate more resources to early planning and analysis before beginning full execution."
)
OPTION_B: Final[str] = (
    "Move quickly into execution and iteration, adjusting the approach based on "
    "feedback and ongoing results."
)

CASE_CLOSE: Final[str] = (
    "The team needs to decide which approach to prioritize for the project's initial phase."
)

QUESTIONS: Final[tuple[str, str, str]] = (
    "What do you think about the approach I’m leaning toward?",
    "How do you think this approach would work over the course of the project?",
    "Is there anything else I should consider before making a decision?",
)

_PLACEHOLDER: Final[str] = "{{PARTICIPANT_POSITION}}"
_PROMPT_DIR: Final[Path] = Path(__file__).resolve().parent / "prompts"


def make_system_prompt(condition: Condition, position: InitialPosition) -> str:
    """Fill only the designated position slot in the supplied condition prompt."""
    template = os.environ.get(f"PROMPT_{condition.name}")
    if template is None:
        path = _PROMPT_DIR / f"{condition.value}.txt"
        if not path.is_file():
            raise PromptConfigurationError("The study prompt is unavailable.")
        template = path.read_text(encoding="utf-8")
    if template.count(_PLACEHOLDER) != 1:
        raise PromptConfigurationError("The study prompt has an invalid position slot.")
    statement = (
        f"Option {position.choice}. Their stated reason, verbatim: "
        f"{json.dumps(position.reason, ensure_ascii=False)}"
    )
    return template.replace(_PLACEHOLDER, statement)
