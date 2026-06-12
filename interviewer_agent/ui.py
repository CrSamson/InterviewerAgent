from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich import box
from rich.console import Console
from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from .progress import PHASE_ORDER, Phase, ProgressSnapshot


THEME = Theme(
    {
        "agent.title": "bold cyan",
        "agent.accent": "bold magenta",
        "agent.success": "bold green",
        "agent.warn": "bold yellow",
        "agent.error": "bold red",
        "agent.muted": "dim white",
        "agent.prompt": "bold cyan",
        "agent.stage": "bold bright_cyan",
        "agent.future": "dim cyan",
    }
)


def make_console() -> Console:
    return Console(theme=THEME)


@contextmanager
def stage_status(console: Console, label: str, detail: str) -> Iterator[Any]:
    with console.status(
        f"[agent.stage]{label}[/] [agent.muted]{detail}[/]",
        spinner="dots12",
    ) as status:
        yield status


def render_dashboard(snapshot: ProgressSnapshot) -> Group:
    """Content-sized dashboard frame: stepper, phase body, status footer."""
    return Group(
        render_header_stepper(snapshot.phase),
        render_body(snapshot),
        render_footer(snapshot),
    )


def print_stepper(console: Console, phase: Phase) -> None:
    console.print(render_header_stepper(phase))


def render_header_stepper(phase: Phase) -> Panel:
    current_index = PHASE_ORDER.index(phase)
    parts: list[str] = []
    for index, step in enumerate(PHASE_ORDER):
        if index < current_index:
            # \[x] keeps Rich from consuming [x] as a markup tag.
            parts.append(f"[agent.success]\\[x] {step.value}[/]")
        elif index == current_index:
            parts.append(f"[agent.stage][>] {step.value}[/]")
        else:
            parts.append(f"[agent.future][ ] {step.value}[/]")
    return Panel(
        "  ->  ".join(parts),
        border_style="cyan",
        box=box.SIMPLE,
        padding=(0, 1),
    )


def render_body(snapshot: ProgressSnapshot):
    if snapshot.error:
        return render_error_panel(snapshot.error)
    if snapshot.phase == Phase.RESEARCH:
        return render_research_body(snapshot)
    return render_boot_body(snapshot)


def render_boot_body(snapshot: ProgressSnapshot) -> Panel:
    return Panel(
        "Checking environment, loading .env, and preparing the interview target.",
        title="[agent.title]BOOT[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def render_research_body(snapshot: ProgressSnapshot) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=4)
    for task in snapshot.research_tasks:
        table.add_row(
            f"[agent.stage]{task.label}[/]",
            _bar(done=task.done, tick=snapshot.elapsed_seconds),
        )
    table.add_row("", "")
    table.add_row("[agent.stage]Now[/]", snapshot.now_line)
    table.add_row("[agent.stage]Tool calls[/]", str(snapshot.tool_calls))
    table.add_row(
        "[agent.stage]Budget[/]",
        "fast: small search/scrape budget"
        if snapshot.depth == "fast"
        else "standard: deeper search/scrape budget",
    )
    return Panel(
        table,
        title="[agent.title]LIVE RESEARCH DASHBOARD[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def render_footer(snapshot: ProgressSnapshot) -> Panel:
    text = (
        f"mode={snapshot.depth}  questions={snapshot.question_count}  "
        f"elapsed={format_elapsed(snapshot.elapsed_seconds)}  "
        f"tools={snapshot.tool_calls}  hints=Ctrl+C aborts"
    )
    return Panel(text, border_style="cyan", box=box.SIMPLE, padding=(0, 1))


def render_error_panel(message: str) -> Panel:
    return Panel(
        message,
        title="[agent.error]ERROR[/]",
        border_style="red",
        box=box.HEAVY,
        padding=(1, 2),
    )


def render_banner(console: Console) -> None:
    title = Text("INTERVIEWER AGENT", style="agent.title")
    title.append(" // CREWAI PREP CONSOLE", style="agent.muted")
    body = Text()
    body.append("workflow ", style="agent.muted")
    body.append("research -> questions -> practice -> feedback", style="agent.success")
    console.print(
        Panel(
            body,
            title=title,
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )


def render_stage(console: Console, label: str, detail: str | None = None) -> None:
    text = f"[agent.stage]{label}[/]"
    if detail:
        text = f"{text} [agent.muted]{detail}[/]"
    console.rule(text, style="cyan")


def format_elapsed(seconds: int) -> str:
    minutes, remainder = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{remainder:02d}"


def _bar(*, done: bool, tick: int = 0, width: int = 20) -> str:
    if done:
        return f"[agent.success]{'#' * width}[/] [agent.success]done[/]"
    cells = ["."] * width
    for offset in range(4):
        cells[(tick + offset) % width] = "#"
    return f"[agent.stage]{''.join(cells)}[/] [agent.muted]working[/]"


def render_error(console: Console, title: str, message: str) -> None:
    console.print(
        Panel(
            message,
            title=f"[agent.error]{title}[/]",
            border_style="red",
            box=box.HEAVY,
            padding=(1, 2),
        )
    )


def render_markdown_panel(
    console: Console,
    *,
    title: str,
    markdown: str,
    border_style: str = "cyan",
) -> None:
    console.print(
        Panel(
            Markdown(markdown or "_No content returned._"),
            title=f"[agent.accent]{title}[/]",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def prompt_required(label: str, default: str | None = None) -> str:
    while True:
        value = Prompt.ask(f"[agent.prompt]{label}[/]", default=default).strip()
        if value:
            return value


def console_input(console: Console, prompt: str) -> str:
    return console.input(f"[agent.prompt]{prompt}[/] ")


def render_question_table(console: Console, questions: list[str]) -> None:
    table = Table(
        title="Generated Interview Questions",
        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        header_style="agent.title",
        show_lines=False,
    )
    table.add_column("#", style="agent.muted", width=4, justify="right")
    table.add_column("Question", style="white")
    for index, question in enumerate(questions, start=1):
        table.add_row(f"{index:02d}", question)
    console.print(table)


def render_question(console: Console, index: int, total: int, question: str) -> None:
    console.print(
        Panel(
            question,
            title=f"[agent.title]QUESTION {index:02d}/{total:02d}[/]",
            border_style="magenta",
            box=box.HEAVY,
            padding=(1, 2),
        )
    )
