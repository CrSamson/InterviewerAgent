from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


EXIT_COMMANDS = {"exit", "quit", "stop"}
NEXT_COMMANDS = {"next", "n", "skip"}
RESEARCH_DEPTHS = {"fast", "standard"}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class InterviewInputs:
    interviewer: str
    company: str
    job_position: str
    job_description: str


@dataclass(frozen=True)
class QuestionGenerationResult:
    company_research: str
    interviewer_research: str
    questions_markdown: str
    questions: list[str]


@dataclass(frozen=True)
class WorkflowSettings:
    question_count: int = 5
    research_depth: str = "fast"

    def __post_init__(self) -> None:
        if self.question_count < 1:
            raise ValueError("question_count must be at least 1")
        if self.research_depth not in RESEARCH_DEPTHS:
            options = ", ".join(sorted(RESEARCH_DEPTHS))
            raise ValueError(f"research_depth must be one of: {options}")


@dataclass
class PracticeAttempt:
    question_index: int
    question: str
    attempt: int
    answer: str
    feedback: str
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class SessionRecord:
    inputs: InterviewInputs
    questions_markdown: str
    questions: list[str]
    company_research: str = ""
    interviewer_research: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    attempts: list[PracticeAttempt] = field(default_factory=list)
    stopped_early: bool = False
    stop_reason: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    completed_at: str | None = None

    def add_attempt(
        self,
        *,
        question_index: int,
        question: str,
        attempt: int,
        answer: str,
        feedback: str,
    ) -> None:
        self.attempts.append(
            PracticeAttempt(
                question_index=question_index,
                question=question,
                attempt=attempt,
                answer=answer,
                feedback=feedback,
            )
        )

    def finish(self, *, stopped_early: bool = False, stop_reason: str | None = None) -> None:
        self.stopped_early = stopped_early
        self.stop_reason = stop_reason
        self.completed_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path
