import json
import os
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from rich.console import Console

from interviewer_agent.controller import PracticeCommand, parse_practice_command, run_session
from interviewer_agent.models import (
    FeedbackReport,
    QuestionDeck,
    ResearchBrief,
    SessionSummary,
)
from interviewer_agent.ui import THEME


class ScriptedConsole(Console):
    def __init__(self, inputs: list[str]) -> None:
        super().__init__(file=StringIO(), force_terminal=False, width=120, theme=THEME)
        self.inputs = inputs

    def input(self, prompt: str = "", *args, **kwargs) -> str:
        if not self.inputs:
            raise AssertionError(f"Unexpected prompt: {prompt}")
        return self.inputs.pop(0)


class FakeEngine:
    def __init__(self, inputs, *, verbose=False, settings=None) -> None:
        self.inputs = inputs
        self.verbose = verbose
        self.settings = settings

    async def generate_research_brief(self, progress=None) -> ResearchBrief:
        if progress:
            progress.complete_task("company")
            progress.complete_task("interviewer")
        return ResearchBrief(
            company_research="Company brief",
            interviewer_research="Interviewer brief",
        )

    async def generate_question_deck(self, *, research, progress=None) -> QuestionDeck:
        if progress:
            progress.complete_task("questions")
        return QuestionDeck(
            questions_markdown="1. Why this role?",
            questions=["Why this role?"],
        )

    async def generate_answer_feedback(self, *, question, answer, attempt_number):
        return FeedbackReport(
            score=4,
            what_worked="Clear structure.",
            missing_signal="Add one measurable result.",
            stronger_outline="Situation, action, result, lesson.",
            next_instruction="Quantify the impact.",
        )

    async def generate_session_summary(self, *, session):
        return SessionSummary(
            recurring_gaps="Needs more metrics.",
            strongest_answer="The first answer had clear ownership.",
            weakest_answer="No weak answer in this short session.",
            next_practice_plan="Practice one quantified story.",
        )


class PracticeCommandTests(unittest.TestCase):
    def test_parse_practice_commands(self) -> None:
        self.assertEqual(parse_practice_command("help"), PracticeCommand.HELP)
        self.assertEqual(parse_practice_command("hint"), PracticeCommand.HINT)
        self.assertEqual(parse_practice_command("example"), PracticeCommand.EXAMPLE)
        self.assertEqual(parse_practice_command("repeat"), PracticeCommand.REPEAT)
        self.assertEqual(parse_practice_command("next"), PracticeCommand.NEXT)
        self.assertEqual(parse_practice_command("exit"), PracticeCommand.EXIT)

    def test_parse_practice_command_ignores_answer_text(self) -> None:
        self.assertIsNone(parse_practice_command("next I would clarify requirements"))
        self.assertIsNone(parse_practice_command("help\nwith this project"))


class RunSessionControllerTests(unittest.TestCase):
    def test_run_session_with_fake_engine_saves_structured_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "session.json"
            console = ScriptedConsole(["", "", "", "My answer", ""])

            with patch.dict(
                os.environ,
                {"ANTHROPIC_API_KEY": "anthropic-test", "SERPER_API_KEY": "serper-test"},
            ):
                import asyncio

                asyncio.run(
                    run_session(
                        company="Maneva",
                        interviewer="Avery",
                        position="Engineer",
                        job_description="Build agent workflows.",
                        max_attempts=1,
                        questions=1,
                        research_depth="fast",
                        output=output,
                        verbose=False,
                        console=console,
                        engine_factory=FakeEngine,
                    )
                )

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["inputs"]["company"], "Maneva")
            self.assertEqual(data["research_brief"]["company_research"], "Company brief")
            self.assertEqual(data["question_deck"]["questions"], ["Why this role?"])
            self.assertEqual(data["attempts"][0]["feedback_report"]["score"], 4)
            self.assertEqual(data["summary"]["recurring_gaps"], "Needs more metrics.")
            self.assertTrue(data["events"])


if __name__ == "__main__":
    unittest.main()
