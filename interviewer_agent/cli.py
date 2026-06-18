from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .controller import (
    _practice_loop,
    _read_answer,
    parse_practice_command,
    run_session,
)
from .ui import make_console
from .workflow import CrewAIInterviewEngine


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
    engine_factory=CrewAIInterviewEngine,
) -> None:
    await run_session(
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
        engine_factory=engine_factory,
    )


if __name__ == "__main__":
    app()
