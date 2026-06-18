from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from rich.live import Live
import typer

from .engine import InterviewEngine
from .models import (
    EXAMPLE_COMMANDS,
    EXIT_COMMANDS,
    HELP_COMMANDS,
    HINT_COMMANDS,
    NEXT_COMMANDS,
    REPEAT_COMMANDS,
    FeedbackReport,
    InterviewInputs,
    QuestionDeck,
    ResearchBrief,
    SessionRecord,
    SessionSummary,
    WorkflowSettings,
)
from .parsing import parse_feedback_report, parse_session_summary
from .progress import Phase, ProgressState
from .ui import (
    console_input,
    format_elapsed,
    prompt_required,
    render_banner,
    render_context_review,
    render_dashboard,
    render_error,
    render_example_answer,
    render_feedback_report,
    render_hint,
    render_practice_help,
    render_question,
    render_question_table,
    render_question_review_help,
    render_session_summary,
    stage_status,
    print_stepper,
)
from .workflow import CrewAIInterviewEngine, MissingEnvironmentError, load_environment


class PracticeCommand(str, Enum):
    EXIT = "exit"
    NEXT = "next"
    HELP = "help"
    REPEAT = "repeat"
    HINT = "hint"
    EXAMPLE = "example"


async def run_session(
    *,
    company: str | None,
    interviewer: str | None,
    position: str | None,
    job_description: str | None,
    max_attempts: int,
    questions: int,
    research_depth: str,
    output: Path | None,
    verbose: bool,
    console,
    engine_factory: type[InterviewEngine] = CrewAIInterviewEngine,
) -> None:
    render_banner(console)

    try:
        load_environment()
    except MissingEnvironmentError as exc:
        render_error(
            console,
            "BOOT FAILED",
            (
                f"{exc}\n\nAdd these values to .env or your shell before running:\n"
                "ANTHROPIC_API_KEY=...\nSERPER_API_KEY=..."
            ),
        )
        raise typer.Exit(1) from exc

    inputs = _collect_inputs(
        company=company,
        interviewer=interviewer,
        position=position,
        job_description=job_description,
    )
    try:
        settings = WorkflowSettings(question_count=questions, research_depth=research_depth)
    except ValueError as exc:
        render_error(console, "BOOT FAILED", str(exc))
        raise typer.Exit(2) from exc

    inputs, settings, max_attempts = _review_context(
        console=console,
        inputs=inputs,
        settings=settings,
        max_attempts=max_attempts,
    )

    engine = engine_factory(inputs, verbose=verbose, settings=settings)
    state = ProgressState(
        depth=settings.research_depth,
        question_count=settings.question_count,
        max_attempts=max_attempts,
    )

    try:
        state.set_phase(Phase.RESEARCH)
        with Live(
            render_dashboard(state.snapshot()),
            console=console,
            refresh_per_second=4,
            transient=True,
        ) as live:
            research, deck = await _prepare_deck_with_live_progress(
                engine=engine,
                state=state,
                live=live,
            )
    except typer.Exit:
        raise
    except Exception as exc:
        render_error(console, "RESEARCH FAILED", str(exc))
        raise typer.Exit(1) from exc

    summary = state.snapshot()
    print_stepper(console, Phase.QUESTION_GEN)
    console.print(
        f"[agent.success]Research complete[/] [agent.muted]elapsed "
        f"{format_elapsed(summary.elapsed_seconds)} | {summary.tool_calls} tool calls[/]"
    )

    session = SessionRecord(
        inputs=inputs,
        company_research=research.company_research,
        interviewer_research=research.interviewer_research,
        research_brief=research,
        question_deck=deck,
        settings={
            "question_count": settings.question_count,
            "research_depth": settings.research_depth,
            "max_attempts": max_attempts,
        },
        questions_markdown=deck.questions_markdown,
        questions=deck.questions,
    )
    session.add_event(
        "research_complete",
        "Initial research and question deck generated.",
        {"tool_calls": summary.tool_calls},
    )

    deck = await _review_question_deck(
        console=console,
        engine=engine,
        research=research,
        deck=deck,
        session=session,
    )
    session.set_question_deck(deck)

    if not session.questions:
        render_error(
            console,
            "QUESTION GEN FAILED",
            (
                "No interview questions are available after review. "
                "Regenerate the deck or reduce manual removals."
            ),
        )
        raise typer.Exit(1)

    print_stepper(console, Phase.PRACTICE)
    console_input(console, "Press Enter to start practice:")
    stopped_early = await _practice_loop(
        console=console,
        engine=engine,
        session=session,
        max_attempts=max_attempts,
    )

    if stopped_early:
        session.finish(stopped_early=True, stop_reason="user_exit")
    else:
        session.finish()

    print_stepper(console, Phase.SUMMARY)
    session_summary = await _summarize_session(
        console=console,
        engine=engine,
        session=session,
    )
    session.set_summary(session_summary)
    session.add_event("session_summarized", "Generated final session summary.")
    render_session_summary(console, session_summary)

    output_path = output or _default_output_path()
    saved_path = session.save_json(output_path)

    print_stepper(console, Phase.SESSION_SAVED)
    console.print(f"[agent.success]Saved practice history to[/] {saved_path}")


async def _prepare_deck_with_live_progress(
    *,
    engine: InterviewEngine,
    state: ProgressState,
    live: Live,
) -> tuple[ResearchBrief, QuestionDeck]:
    task = asyncio.create_task(_prepare_deck(engine=engine, state=state))

    def mark_failure(done_task: asyncio.Task) -> None:
        if done_task.cancelled():
            state.set_error("Research task cancelled")
            return
        error = done_task.exception()
        if error:
            state.set_error(str(error))

    task.add_done_callback(mark_failure)

    while not task.done():
        live.update(render_dashboard(state.snapshot()), refresh=True)
        await asyncio.sleep(0.4)

    live.update(render_dashboard(state.snapshot()), refresh=True)
    return await task


async def _prepare_deck(
    *,
    engine: InterviewEngine,
    state: ProgressState,
) -> tuple[ResearchBrief, QuestionDeck]:
    research = await engine.generate_research_brief(progress=state)
    deck = await engine.generate_question_deck(research=research, progress=state)
    return research, deck


async def _review_question_deck(
    *,
    console,
    engine: InterviewEngine,
    research: ResearchBrief,
    deck: QuestionDeck,
    session: SessionRecord,
) -> QuestionDeck:
    current_deck = deck
    while True:
        render_question_table(console, current_deck.questions)
        command = console_input(
            console,
            "Press Enter to start, or type edit/remove/regenerate/help/exit:",
        ).strip()
        normalized = command.casefold()

        if normalized in {"", "start", "accept", "accept all", "practice"}:
            session.add_event("question_deck_accepted", "Accepted reviewed question deck.")
            return current_deck
        if normalized in EXIT_COMMANDS:
            raise typer.Exit(0)
        if normalized in HELP_COMMANDS or normalized == "help":
            render_question_review_help(console)
            continue
        if normalized.startswith("edit"):
            current_deck = _edit_question(console, current_deck)
            session.add_event("question_edited", "Edited a generated question.")
            continue
        if normalized.startswith("remove"):
            updated = _remove_question(console, current_deck)
            if updated is current_deck:
                continue
            current_deck = updated
            session.add_event("question_removed", "Removed a generated question.")
            continue
        if normalized in {"regenerate", "regen", "again"}:
            with stage_status(console, "QUESTION GEN", "regenerating question deck"):
                regenerated = await engine.generate_question_deck(research=research)
            if regenerated.questions:
                current_deck = regenerated
                session.add_event("question_deck_regenerated", "Regenerated question deck.")
            else:
                console.print("[agent.warn]Regeneration returned no parseable questions.[/]")
            continue

        console.print("[agent.warn]Unknown review command. Type 'help' for options.[/]")


async def _practice_loop(
    *,
    console,
    engine=None,
    workflow=None,
    session: SessionRecord,
    max_attempts: int,
) -> bool:
    if engine is None:
        engine = workflow
    if engine is None:
        raise TypeError("engine is required")

    total_questions = len(session.questions)
    for question_index, question in enumerate(session.questions, start=1):
        render_question(console, question_index, total_questions, question)

        attempt_number = 1
        empty_reads = 0
        while attempt_number <= max_attempts:
            answer = _read_answer(
                console,
                f"Attempt {attempt_number}. Your answer "
                "(blank line submits), or 'help':",
            )
            command = parse_practice_command(answer)

            if command == PracticeCommand.EXIT:
                session.add_event("practice_exit", "User exited during practice.")
                return True
            if command == PracticeCommand.NEXT:
                session.add_event(
                    "question_skipped",
                    f"Skipped question {question_index}.",
                    {"question_index": question_index},
                )
                break
            if command == PracticeCommand.HELP:
                render_practice_help(console)
                continue
            if command == PracticeCommand.REPEAT:
                render_question(console, question_index, total_questions, question)
                continue
            if command == PracticeCommand.HINT:
                render_hint(console, _build_hint(session.inputs, question))
                continue
            if command == PracticeCommand.EXAMPLE:
                render_example_answer(console, _build_example_answer(session.inputs, question))
                continue
            if not answer:
                empty_reads += 1
                if empty_reads > 1:
                    console.print("[agent.warn]Answer cannot be empty.[/]")
                continue

            empty_reads = 0
            with stage_status(
                console,
                "PRACTICE",
                f"scoring question {question_index:02d}, attempt {attempt_number}",
            ):
                feedback_value = await engine.generate_answer_feedback(
                    question=question,
                    answer=answer,
                    attempt_number=attempt_number,
                )
            feedback = _coerce_feedback_report(feedback_value)

            session.add_attempt(
                question_index=question_index,
                question=question,
                attempt=attempt_number,
                answer=answer,
                feedback_report=feedback,
            )
            session.add_event(
                "attempt_scored",
                f"Scored question {question_index}, attempt {attempt_number}.",
                {
                    "question_index": question_index,
                    "attempt": attempt_number,
                    "score": feedback.score,
                },
            )
            render_feedback_report(
                console,
                title=f"Feedback Q{question_index:02d} / Attempt {attempt_number}",
                feedback=feedback,
            )

            attempt_number += 1
            if attempt_number <= max_attempts:
                console.print("[agent.muted]Type a revision, or use help/next/exit.[/]")

        if attempt_number > max_attempts:
            console.print("[agent.muted]Max attempts reached. Moving to next question.[/]")

    return False


def parse_practice_command(answer: str) -> PracticeCommand | None:
    if "\n" in answer:
        return None
    command = answer.strip().casefold()
    if command in EXIT_COMMANDS:
        return PracticeCommand.EXIT
    if command in NEXT_COMMANDS:
        return PracticeCommand.NEXT
    if command in HELP_COMMANDS:
        return PracticeCommand.HELP
    if command in REPEAT_COMMANDS:
        return PracticeCommand.REPEAT
    if command in HINT_COMMANDS:
        return PracticeCommand.HINT
    if command in EXAMPLE_COMMANDS:
        return PracticeCommand.EXAMPLE
    return None


def _read_answer(console, prompt: str) -> str:
    """Read a possibly multi-line answer; a blank line submits it."""
    first = console_input(console, prompt).strip()
    if not first or parse_practice_command(first):
        return first
    lines = [first]
    while True:
        line = console.input("").strip()
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


async def _summarize_session(
    *,
    console,
    engine: InterviewEngine,
    session: SessionRecord,
) -> SessionSummary:
    try:
        with stage_status(console, "SUMMARY", "finding patterns across attempts"):
            summary = await engine.generate_session_summary(session=session)
        return _coerce_session_summary(summary)
    except Exception as exc:
        console.print(f"[agent.warn]Summary generation failed: {exc}[/]")
        return SessionSummary(
            recurring_gaps="Summary generation failed.",
            strongest_answer="Review the saved attempts manually.",
            weakest_answer="Review the saved attempts manually.",
            next_practice_plan="Run another session after checking the saved feedback.",
        )


def _collect_inputs(
    *,
    company: str | None,
    interviewer: str | None,
    position: str | None,
    job_description: str | None,
) -> InterviewInputs:
    return InterviewInputs(
        interviewer=interviewer or prompt_required("Interviewer"),
        company=company or prompt_required("Company"),
        job_position=position or prompt_required("Position"),
        job_description=job_description or prompt_required("Job description"),
    )


def _review_context(
    *,
    console,
    inputs: InterviewInputs,
    settings: WorkflowSettings,
    max_attempts: int,
) -> tuple[InterviewInputs, WorkflowSettings, int]:
    current_inputs = inputs
    current_settings = settings
    current_attempts = max_attempts

    while True:
        render_context_review(
            console,
            inputs=current_inputs,
            settings=current_settings,
            max_attempts=current_attempts,
        )
        command = console_input(
            console,
            "Press Enter to research, or type edit/restart/exit:",
        ).strip()
        normalized = command.casefold()
        if normalized in {"", "start", "continue", "research", "yes", "y"}:
            return current_inputs, current_settings, current_attempts
        if normalized in EXIT_COMMANDS:
            raise typer.Exit(0)
        if normalized == "restart":
            current_inputs = _collect_inputs(
                company=None,
                interviewer=None,
                position=None,
                job_description=None,
            )
            continue
        if normalized.startswith("edit"):
            field = normalized.removeprefix("edit").strip()
            current_inputs, current_settings, current_attempts = _edit_context_value(
                console=console,
                field=field,
                inputs=current_inputs,
                settings=current_settings,
                max_attempts=current_attempts,
            )
            continue

        console.print("[agent.warn]Unknown preflight command. Use Enter, edit, restart, or exit.[/]")


def _edit_context_value(
    *,
    console,
    field: str,
    inputs: InterviewInputs,
    settings: WorkflowSettings,
    max_attempts: int,
) -> tuple[InterviewInputs, WorkflowSettings, int]:
    target = field or console_input(
        console,
        "Field to edit (company/interviewer/position/job/questions/depth/attempts):",
    ).strip().casefold()
    target = {
        "role": "position",
        "job_description": "job",
        "description": "job",
        "research": "depth",
        "max_attempts": "attempts",
    }.get(target, target)

    if target == "company":
        inputs = InterviewInputs(
            interviewer=inputs.interviewer,
            company=prompt_required("Company"),
            job_position=inputs.job_position,
            job_description=inputs.job_description,
        )
    elif target == "interviewer":
        inputs = InterviewInputs(
            interviewer=prompt_required("Interviewer"),
            company=inputs.company,
            job_position=inputs.job_position,
            job_description=inputs.job_description,
        )
    elif target == "position":
        inputs = InterviewInputs(
            interviewer=inputs.interviewer,
            company=inputs.company,
            job_position=prompt_required("Position"),
            job_description=inputs.job_description,
        )
    elif target == "job":
        inputs = InterviewInputs(
            interviewer=inputs.interviewer,
            company=inputs.company,
            job_position=inputs.job_position,
            job_description=prompt_required("Job description"),
        )
    elif target == "questions":
        settings = WorkflowSettings(
            question_count=_prompt_int(console, "Questions", settings.question_count, 1, 10),
            research_depth=settings.research_depth,
        )
    elif target == "depth":
        settings = WorkflowSettings(
            question_count=settings.question_count,
            research_depth=_prompt_research_depth(console, settings.research_depth),
        )
    elif target == "attempts":
        max_attempts = _prompt_int(console, "Max attempts", max_attempts, 1, 10)
    else:
        console.print("[agent.warn]Unknown field. Nothing changed.[/]")

    return inputs, settings, max_attempts


def _edit_question(console, deck: QuestionDeck) -> QuestionDeck:
    if not deck.questions:
        console.print("[agent.warn]There are no questions to edit.[/]")
        return deck
    index = _prompt_question_index(console, deck.questions, "Question number to edit")
    questions = list(deck.questions)
    questions[index - 1] = prompt_required("New question")
    return QuestionDeck.from_questions(questions)


def _remove_question(console, deck: QuestionDeck) -> QuestionDeck:
    if len(deck.questions) <= 1:
        console.print("[agent.warn]At least one question is required.[/]")
        return deck
    index = _prompt_question_index(console, deck.questions, "Question number to remove")
    questions = list(deck.questions)
    questions.pop(index - 1)
    return QuestionDeck.from_questions(questions)


def _prompt_question_index(console, questions: list[str], prompt: str) -> int:
    while True:
        raw = console_input(console, prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            console.print("[agent.warn]Enter a question number.[/]")
            continue
        if 1 <= value <= len(questions):
            return value
        console.print(f"[agent.warn]Choose a number from 1 to {len(questions)}.[/]")


def _prompt_int(console, label: str, current: int, minimum: int, maximum: int) -> int:
    while True:
        raw = console_input(console, f"{label} [{current}]").strip()
        if not raw:
            return current
        try:
            value = int(raw)
        except ValueError:
            console.print("[agent.warn]Enter a number.[/]")
            continue
        if minimum <= value <= maximum:
            return value
        console.print(f"[agent.warn]Choose a value from {minimum} to {maximum}.[/]")


def _prompt_research_depth(console, current: str) -> str:
    while True:
        raw = console_input(console, f"Research depth fast/standard [{current}]").strip()
        if not raw:
            return current
        if raw in {"fast", "standard"}:
            return raw
        console.print("[agent.warn]Use 'fast' or 'standard'.[/]")


def _build_hint(inputs: InterviewInputs, question: str) -> str:
    return (
        f"Question: {question}\n\n"
        "- Start with the direct answer before background.\n"
        "- Use one concrete project or decision, then name the action you personally took.\n"
        "- Tie the impact back to the role: "
        f"{inputs.job_position} at {inputs.company}.\n"
        "- End with the result, tradeoff, or lesson."
    )


def _build_example_answer(inputs: InterviewInputs, question: str) -> str:
    return (
        f"Question: {question}\n\n"
        "Example structure:\n"
        "I would frame this with a specific situation, the constraint I had to work "
        "within, the action I owned, and the measurable result. For this role at "
        f"{inputs.company}, I would also connect the answer to customer impact, "
        "engineering judgment, and how I handled ambiguity."
    )


def _coerce_feedback_report(value: Any) -> FeedbackReport:
    if isinstance(value, FeedbackReport):
        return value
    return parse_feedback_report(str(value))


def _coerce_session_summary(value: Any) -> SessionSummary:
    if isinstance(value, SessionSummary):
        return value
    return parse_session_summary(str(value))


def _default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("runs") / f"interview-session-{timestamp}.json"
