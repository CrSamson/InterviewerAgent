import asyncio
import unittest

from interviewer_agent.cli import _practice_loop
from interviewer_agent.models import InterviewInputs, SessionRecord


class _FakeStatus:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _FakeConsole:
    def __init__(self, inputs: list[str]) -> None:
        self.inputs = inputs
        self.messages: list[str] = []

    def input(self, prompt: str) -> str:
        if not self.inputs:
            raise AssertionError(f"Unexpected prompt: {prompt}")
        return self.inputs.pop(0)

    def print(self, *values, **kwargs) -> None:
        self.messages.append(" ".join(str(value) for value in values))

    def status(self, *args, **kwargs) -> _FakeStatus:
        return _FakeStatus()


class _FakeWorkflow:
    async def generate_answer_feedback(
        self,
        *,
        question: str,
        answer: str,
        attempt_number: int,
    ) -> str:
        return f"feedback {attempt_number}: {answer}"


class PracticeLoopTests(unittest.TestCase):
    def test_revised_answer_after_feedback_is_not_swallowed_as_command(self) -> None:
        session = SessionRecord(
            inputs=InterviewInputs(
                interviewer="Avery",
                company="Maneva",
                job_position="Engineer",
                job_description="Build agents.",
            ),
            questions_markdown="1. Question?",
            questions=["Question?"],
        )
        console = _FakeConsole(["first answer", "", "revised answer", ""])

        stopped_early = asyncio.run(
            _practice_loop(
                console=console,
                workflow=_FakeWorkflow(),
                session=session,
                max_attempts=2,
            )
        )

        self.assertFalse(stopped_early)
        self.assertEqual(
            [attempt.answer for attempt in session.attempts],
            ["first answer", "revised answer"],
        )

    def test_first_empty_answer_is_silently_ignored(self) -> None:
        session = SessionRecord(
            inputs=InterviewInputs(
                interviewer="Avery",
                company="Maneva",
                job_position="Engineer",
                job_description="Build agents.",
            ),
            questions_markdown="1. Question?",
            questions=["Question?"],
        )
        console = _FakeConsole(["", "actual answer", ""])

        stopped_early = asyncio.run(
            _practice_loop(
                console=console,
                workflow=_FakeWorkflow(),
                session=session,
                max_attempts=1,
            )
        )

        self.assertFalse(stopped_early)
        self.assertEqual([attempt.answer for attempt in session.attempts], ["actual answer"])
        self.assertFalse(
            any("Answer cannot be empty" in message for message in console.messages)
        )

    def test_multiline_paste_is_consumed_as_one_answer(self) -> None:
        session = SessionRecord(
            inputs=InterviewInputs(
                interviewer="Avery",
                company="Maneva",
                job_position="Engineer",
                job_description="Build agents.",
            ),
            questions_markdown="1. Question?",
            questions=["Question?"],
        )
        # A multi-line paste arrives as buffered lines; the blank line submits
        # them as one answer instead of feeding later attempt prompts.
        console = _FakeConsole(["pasted line one", "pasted line two", "", "next"])

        stopped_early = asyncio.run(
            _practice_loop(
                console=console,
                workflow=_FakeWorkflow(),
                session=session,
                max_attempts=2,
            )
        )

        self.assertFalse(stopped_early)
        self.assertEqual(
            [attempt.answer for attempt in session.attempts],
            ["pasted line one\npasted line two"],
        )

    def test_exit_command_returns_without_blank_line(self) -> None:
        session = SessionRecord(
            inputs=InterviewInputs(
                interviewer="Avery",
                company="Maneva",
                job_position="Engineer",
                job_description="Build agents.",
            ),
            questions_markdown="1. Question?",
            questions=["Question?"],
        )
        console = _FakeConsole(["exit"])

        stopped_early = asyncio.run(
            _practice_loop(
                console=console,
                workflow=_FakeWorkflow(),
                session=session,
                max_attempts=3,
            )
        )

        self.assertTrue(stopped_early)
        self.assertEqual(session.attempts, [])


if __name__ == "__main__":
    unittest.main()
