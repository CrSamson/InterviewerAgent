from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated

from rich.live import Live
import typer

from . import __version__
from .models import (
    EXIT_COMMANDS,
    NEXT_COMMANDS,
    InterviewInputs,
    SessionRecord,
    WorkflowSettings,
)
from .ui import (
    console_input,
    format_elapsed,
    make_console,
    print_stepper,
    prompt_required,
    render_banner,
    render_dashboard,
    render_error,
    render_question,
    render_question_table,
    render_markdown_panel,
    stage_status,
)
from .progress import Phase, ProgressState
from .workflow import CrewInterviewWorkflow, MissingEnvironmentError, load_environment


app = typer.Typer(
    name="interviewer-agent",
    help="Run the CrewAI interview preparation workflow from the terminal.",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the CLI version and exit."),
    ] = False,
) -> None:
    if version:
        typer.echo(f"interviewer-agent {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def run(
    company: Annotated[
        str | None,
        typer.Option("--company", "-c", help="Target company name."),
    ] = None,
    interviewer: Annotated[
        str | None,
        typer.Option("--interviewer", "-i", help="Interviewer name."),
    ] = None,
    position: Annotated[
        str | None,
        typer.Option("--position", "-p", help="Target job position."),
    ] = None,
    job_description: Annotated[
        str | None,
        typer.Option("--job-description", "-j", help="Job description text."),
    ] = None,
    max_attempts: Annotated[
        int,
        typer.Option("--max-attempts", "-m", min=1, help="Attempts per question."),
    ] = 3,
    questions: Annotated[
        int,
        typer.Option("--questions", "-q", min=1, max=10, help="Questions to generate."),
    ] = 5,
    research_depth: Annotated[
        str,
        typer.Option("--research-depth", help="Research depth: fast or standard."),
    ] = "fast",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="JSON file for the session history."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show CrewAI verbose task output."),
    ] = False,
) -> None:
    """Launch the guided interview preparation session."""
    console = make_console()
    try:
        asyncio.run(
            _run_async(
                company=company,
                interviewer=interviewer,
                position=position,
                job_description=job_description,
                max_attempts=max_attempts,
                questions=questions,
                research_depth=research_depth,
                output=output,
                verbose=verbose,
                console=console,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[agent.warn]Session interrupted.[/]")
        raise typer.Exit(130) from None


async def _run_async(
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
    workflow_factory=CrewInterviewWorkflow,
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

    inputs = InterviewInputs(
        interviewer=interviewer or prompt_required("Interviewer"),
        company=company or prompt_required("Company"),
        job_position=position or prompt_required("Position"),
        job_description=job_description or prompt_required("Job description"),
    )

    try:
        settings = WorkflowSettings(question_count=questions, research_depth=research_depth)
    except ValueError as exc:
        render_error(console, "BOOT FAILED", str(exc))
        raise typer.Exit(2) from exc

    workflow = workflow_factory(inputs, verbose=verbose, settings=settings)
    state = ProgressState(
        depth=settings.research_depth,
        question_count=settings.question_count,
        max_attempts=max_attempts,
    )

    # The live dashboard runs only while the crew works: no user input happens
    # inside it, and transient=True keeps intermediate frames out of scrollback.
    try:
        state.set_phase(Phase.RESEARCH)
        with Live(
            render_dashboard(state.snapshot()),
            console=console,
            refresh_per_second=4,
            transient=True,
        ) as live:
            generation = await _generate_questions_with_live_progress(
                workflow=workflow,
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

    if not generation.questions:
        render_error(
            console,
            "QUESTION GEN FAILED",
            (
                "The model returned question text, but no questions could be parsed. "
                "Run again with --verbose to inspect the raw CrewAI output."
            ),
        )
        raise typer.Exit(1)

    session = SessionRecord(
        inputs=inputs,
        company_research=generation.company_research,
        interviewer_research=generation.interviewer_research,
        settings={
            "question_count": settings.question_count,
            "research_depth": settings.research_depth,
            "max_attempts": max_attempts,
        },
        questions_markdown=generation.questions_markdown,
        questions=generation.questions,
    )

    render_question_table(console, generation.questions)

    print_stepper(console, Phase.PRACTICE)
    console_input(console, "Press Enter to start practice:")
    stopped_early = await _practice_loop(
        console=console,
        workflow=workflow,
        session=session,
        max_attempts=max_attempts,
    )

    if stopped_early:
        session.finish(stopped_early=True, stop_reason="user_exit")
    else:
        session.finish()

    output_path = output or _default_output_path()
    saved_path = session.save_json(output_path)

    print_stepper(console, Phase.SESSION_SAVED)
    console.print(f"[agent.success]Saved practice history to[/] {saved_path}")


async def _practice_loop(
    *,
    console,
    workflow,
    session: SessionRecord,
    max_attempts: int,
) -> bool:
    total_questions = len(session.questions)
    for question_index, question in enumerate(session.questions, start=1):
        render_question(console, question_index, total_questions, question)

        attempt_number = 1
        empty_reads = 0
        while attempt_number <= max_attempts:
            answer = _read_answer(
                console,
                f"Attempt {attempt_number}. Your answer "
                "(blank line submits), or 'next'/'exit':",
            )
            command = answer.casefold()

            if command in EXIT_COMMANDS:
                return True
            if command in NEXT_COMMANDS:
                break
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
                feedback = await workflow.generate_answer_feedback(
                    question=question,
                    answer=answer,
                    attempt_number=attempt_number,
                )

            session.add_attempt(
                question_index=question_index,
                question=question,
                attempt=attempt_number,
                answer=answer,
                feedback=feedback,
            )
            render_markdown_panel(
                console,
                title=f"Feedback Q{question_index:02d} / Attempt {attempt_number}",
                markdown=feedback,
                border_style="green",
            )

            attempt_number += 1
            if attempt_number <= max_attempts:
                console.print("[agent.muted]Type a revised answer, or use 'next'/'exit'.[/]")

        if attempt_number > max_attempts:
            console.print("[agent.muted]Max attempts reached. Moving to next question.[/]")

    return False


def _read_answer(console, prompt: str) -> str:
    """Read a possibly multi-line answer; a blank line submits it.

    Reading until a blank line means a pasted multi-line answer is consumed as
    one answer instead of leaking lines into the next prompts. Commands and
    empty first lines return immediately so 'next'/'exit' stay single-stroke.
    """
    first = console_input(console, prompt).strip()
    if not first or first.casefold() in EXIT_COMMANDS | NEXT_COMMANDS:
        return first
    lines = [first]
    while True:
        line = console.input("").strip()
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


async def _generate_questions_with_live_progress(
    *,
    workflow,
    state: ProgressState,
    live: Live,
):
    task = asyncio.create_task(workflow.generate_questions(progress=state))

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


def _default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("runs") / f"interview-session-{timestamp}.json"


if __name__ == "__main__":
    app()
