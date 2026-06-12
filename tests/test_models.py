import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from interviewer_agent.models import InterviewInputs, SessionRecord


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
                )
                record.add_attempt(
                    question_index=1,
                    question="Question?",
                    attempt=1,
                    answer="Answer",
                    feedback="Feedback",
                )
                record.finish(stopped_early=True, stop_reason="user_exit")

                output_path = record.save_json(Path(temp_dir) / "session.json")

                data = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(data["inputs"]["company"], "Maneva")
                self.assertEqual(data["attempts"][0]["feedback"], "Feedback")
                self.assertIs(data["stopped_early"], True)
                self.assertEqual(data["stop_reason"], "user_exit")
                self.assertTrue(data["completed_at"])


if __name__ == "__main__":
    unittest.main()
