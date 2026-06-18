from __future__ import annotations

from typing import Protocol

from .models import (
    FeedbackReport,
    InterviewInputs,
    QuestionDeck,
    ResearchBrief,
    SessionRecord,
    SessionSummary,
    WorkflowSettings,
)
from .progress import ProgressState


class InterviewEngine(Protocol):
    inputs: InterviewInputs
    settings: WorkflowSettings

    async def generate_research_brief(
        self,
        progress: ProgressState | None = None,
    ) -> ResearchBrief:
        """Research company and interviewer context for the session."""

    async def generate_question_deck(
        self,
        *,
        research: ResearchBrief,
        progress: ProgressState | None = None,
    ) -> QuestionDeck:
        """Generate an interview question deck from reviewed context."""

    async def generate_answer_feedback(
        self,
        *,
        question: str,
        answer: str,
        attempt_number: int,
    ) -> FeedbackReport:
        """Score one answer attempt and return structured coaching feedback."""

    async def generate_session_summary(
        self,
        *,
        session: SessionRecord,
    ) -> SessionSummary:
        """Summarize the completed practice session."""
