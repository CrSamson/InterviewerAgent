from io import StringIO
import unittest

from rich.console import Console

from interviewer_agent.models import (
    FeedbackReport,
    InterviewInputs,
    SessionSummary,
    WorkflowSettings,
)
from interviewer_agent.ui import (
    THEME,
    render_context_review,
    render_feedback_report,
    render_practice_help,
    render_question_review_help,
    render_session_summary,
)


class UiRenderTests(unittest.TestCase):
    def test_new_review_and_feedback_panels_render_to_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120, theme=THEME)

        render_context_review(
            console,
            inputs=InterviewInputs(
                interviewer="Avery",
                company="Maneva",
                job_position="Engineer",
                job_description="Build agent workflows.",
            ),
            settings=WorkflowSettings(question_count=2, research_depth="fast"),
            max_attempts=2,
        )
        render_question_review_help(console)
        render_practice_help(console)
        render_feedback_report(
            console,
            title="Feedback",
            feedback=FeedbackReport(
                score=4,
                what_worked="Clear ownership.",
                missing_signal="More metrics.",
                stronger_outline="Situation, action, result.",
                next_instruction="Quantify impact.",
            ),
        )
        render_session_summary(
            console,
            SessionSummary(
                recurring_gaps="Needs metrics.",
                strongest_answer="Question 1.",
                weakest_answer="Question 2.",
                next_practice_plan="Practice one story.",
            ),
        )

        rendered = output.getvalue()
        self.assertIn("PREFLIGHT REVIEW", rendered)
        self.assertIn("Question Review Commands", rendered)
        self.assertIn("Practice Commands", rendered)
        self.assertIn("Score", rendered)
        self.assertIn("Session Summary", rendered)


if __name__ == "__main__":
    unittest.main()
