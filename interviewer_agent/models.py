from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


EXIT_COMMANDS = {"exit", "quit", "stop"}
NEXT_COMMANDS = {"next", "n", "skip"}
HELP_COMMANDS = {"help", "h", "?"}
REPEAT_COMMANDS = {"repeat", "r", "again"}
HINT_COMMANDS = {"hint", "coach"}
EXAMPLE_COMMANDS = {"example", "sample"}
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
class ResearchBrief:
    company_research: str
    interviewer_research: str


@dataclass(frozen=True)
class QuestionDeck:
    questions_markdown: str
    questions: list[str]

    @classmethod
    def from_questions(cls, questions: list[str]) -> "QuestionDeck":
        markdown = "\n".join(
            f"{index}. {question}" for index, question in enumerate(questions, start=1)
        )
        return cls(questions_markdown=markdown, questions=questions)


@dataclass(frozen=True)
class QuestionGenerationResult:
    company_research: str
    interviewer_research: str
    questions_markdown: str
    questions: list[str]


@dataclass(frozen=True)
class FeedbackReport:
    score: int | None = None
    what_worked: str = ""
    missing_signal: str = ""
    stronger_outline: str = ""
    next_instruction: str = ""
    raw_markdown: str = ""

    def as_markdown(self) -> str:
        if self.raw_markdown and not any(
            [
                self.score is not None,
                self.what_worked,
                self.missing_signal,
                self.stronger_outline,
                self.next_instruction,
            ]
        ):
            return self.raw_markdown

        score = f"{self.score}/5" if self.score is not None else "Not scored"
        return "\n\n".join(
            [
                f"**Score:** {score}",
                f"**What worked:** {self.what_worked or 'Not provided.'}",
                f"**Missing signal:** {self.missing_signal or 'Not provided.'}",
                f"**Stronger outline:** {self.stronger_outline or 'Not provided.'}",
                f"**Next revision:** {self.next_instruction or 'Not provided.'}",
            ]
        )


@dataclass(frozen=True)
class SessionSummary:
    recurring_gaps: str = ""
    strongest_answer: str = ""
    weakest_answer: str = ""
    next_practice_plan: str = ""
    raw_markdown: str = ""

    def as_markdown(self) -> str:
        if self.raw_markdown and not any(
            [
                self.recurring_gaps,
                self.strongest_answer,
                self.weakest_answer,
                self.next_practice_plan,
            ]
        ):
            return self.raw_markdown

        return "\n\n".join(
            [
                f"**Recurring gaps:** {self.recurring_gaps or 'Not provided.'}",
                f"**Strongest answer:** {self.strongest_answer or 'Not provided.'}",
                f"**Weakest answer:** {self.weakest_answer or 'Not provided.'}",
                f"**Next practice plan:** {self.next_practice_plan or 'Not provided.'}",
            ]
        )


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
    feedback_report: FeedbackReport | None = None
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class SessionEvent:
    kind: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class SessionRecord:
    inputs: InterviewInputs
    questions_markdown: str
    questions: list[str]
    company_research: str = ""
    interviewer_research: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    research_brief: ResearchBrief | None = None
    question_deck: QuestionDeck | None = None
    attempts: list[PracticeAttempt] = field(default_factory=list)
    summary: SessionSummary | None = None
    events: list[SessionEvent] = field(default_factory=list)
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
        feedback: str | None = None,
        feedback_report: FeedbackReport | None = None,
    ) -> None:
        resolved_feedback = feedback
        if resolved_feedback is None and feedback_report is not None:
            resolved_feedback = feedback_report.as_markdown()
        if resolved_feedback is None:
            resolved_feedback = ""
        self.attempts.append(
            PracticeAttempt(
                question_index=question_index,
                question=question,
                attempt=attempt,
                answer=answer,
                feedback=resolved_feedback,
                feedback_report=feedback_report,
            )
        )

    def add_event(
        self,
        kind: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            SessionEvent(
                kind=kind,
                message=message,
                payload=payload or {},
            )
        )

    def set_question_deck(self, deck: QuestionDeck) -> None:
        self.question_deck = deck
        self.questions_markdown = deck.questions_markdown
        self.questions = list(deck.questions)

    def set_summary(self, summary: SessionSummary) -> None:
        self.summary = summary

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
