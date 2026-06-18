import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from interviewer_agent.models import (
    FeedbackReport,
    InterviewInputs,
    QuestionDeck,
    ResearchBrief,
    SessionRecord,
    SessionSummary,
)


class SessionRecordTests(unittest.TestCase):
    def test_session_record_serializes_to_json(self) -> None:
        with self.subTest("write session history"):
            with TemporaryDirectory() as temp_dir:
                record = SessionRecord(
                    inputs=InterviewInputs(
                        interviewer="Avery Smith",
                        company="Maneva",
                        job_position="Forward Deployed Engineer",
                        job_description="Build AI workflows for industrial customers.",
                    ),
                    questions_markdown="1. Question?",
                    questions=["Question?"],
                    company_research="Company notes",
                    interviewer_research="Interviewer notes",
                    research_brief=ResearchBrief(
                        company_research="Company notes",
                        interviewer_research="Interviewer notes",
                    ),
                    question_deck=QuestionDeck(
                        questions_markdown="1. Question?",
                        questions=["Question?"],
                    ),
                )
                record.add_attempt(
                    question_index=1,
                    question="Question?",
                    attempt=1,
                    answer="Answer",
                    feedback_report=FeedbackReport(
                        score=4,
                        what_worked="Specific example.",
                        missing_signal="More metrics.",
                        stronger_outline="Situation, action, result.",
                        next_instruction="Add impact.",
                    ),
                )
                record.add_event("attempt_scored", "Scored one answer.", {"score": 4})
                record.set_summary(
                    SessionSummary(
                        recurring_gaps="More metrics.",
                        strongest_answer="Question 1.",
                        weakest_answer="Question 1.",
                        next_practice_plan="Try again.",
                    )
                )
                record.finish(stopped_early=True, stop_reason="user_exit")

                output_path = record.save_json(Path(temp_dir) / "session.json")

                data = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(data["inputs"]["company"], "Maneva")
                self.assertEqual(data["attempts"][0]["feedback_report"]["score"], 4)
                self.assertIn("Score", data["attempts"][0]["feedback"])
                self.assertEqual(data["summary"]["next_practice_plan"], "Try again.")
                self.assertEqual(data["events"][0]["kind"], "attempt_scored")
                self.assertIs(data["stopped_early"], True)
                self.assertEqual(data["stop_reason"], "user_exit")
                self.assertTrue(data["completed_at"])


if __name__ == "__main__":
    unittest.main()
