# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Rich-powered terminal CLI that wraps a CrewAI multi-agent workflow for interview preparation. It researches a target company and interviewer, generates role-specific interview questions, then runs an interactive practice loop where the user answers and receives coaching feedback. The original prototype lives in `experimentation_part2.ipynb`; the production code is the `interviewer_agent/` package and the notebook is now reference-only.

## Commands

Setup (Windows, the supported dev platform):
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Run the app:
```powershell
.\interview                       # wrapper: chcp 65001 + UTF-8 + python -m interviewer_agent run
.\interview --company "X" --interviewer "Y" --position "Z" --job-description "..." --questions 5
interviewer-agent run             # installed console script (entry point: interviewer_agent.cli:app)
```

Tests use the stdlib `unittest` runner (no pytest config despite pytest-style files):
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests        # all tests
.\.venv\Scripts\python.exe -m unittest tests.test_parsing       # one module
.\.venv\Scripts\python.exe -m unittest tests.test_cli_practice.PracticeLoopTests.test_first_empty_answer_is_silently_ignored  # one test
```

Regenerate architecture diagrams (requires Pillow, not a declared dependency):
```powershell
.\.venv\Scripts\python.exe .\scripts\generate_diagrams.py
```

## Required environment

`.env` (loaded via `python-dotenv`) must define both keys or the run aborts at the `BOOT` stage:
- `ANTHROPIC_API_KEY` — Claude via CrewAI's `LLM`
- `SERPER_API_KEY` — Serper web search

## Architecture

The flow runs in five visible stages — `BOOT → RESEARCH → QUESTION GEN → PRACTICE → SESSION SAVED` — across these layers:

- **`cli.py`** — Typer app + the async orchestrator (`_run_async`). Owns control flow: env validation, prompting for any missing input, the practice loop, and saving the session. `run()` wraps everything in `asyncio.run`. `_run_async` takes a `workflow_factory` param so tests inject a fake workflow.
- **`workflow.py`** — `CrewInterviewWorkflow`, the only place CrewAI is touched. Two methods: `generate_questions()` (3-task sequential crew) and `generate_answer_feedback()` (single-task crew per attempt). CrewAI is imported lazily inside `_load_crewai()` so the CLI, models, and parsing stay importable/testable without CrewAI installed or API keys present.
- **`models.py`** — Frozen dataclasses for inputs/settings/results, plus `SessionRecord` (mutable, accumulates `PracticeAttempt`s and serializes to JSON). Also defines the command vocab: `EXIT_COMMANDS` (exit/quit/stop), `NEXT_COMMANDS` (next/n/skip), `RESEARCH_DEPTHS` (fast/standard).
- **`parsing.py`** — `parse_interview_questions`, a tolerant regex parser, decoupled from CrewAI entirely.
- **`progress.py`** — stdlib-only, lock-guarded `ProgressState` + frozen `ProgressSnapshot`. CrewAI callbacks/events fire on a **worker thread** (`kickoff_async` uses `asyncio.to_thread`), so they may only mutate this state; all Rich rendering happens on the event loop. Tool calls are counted via CrewAI's event bus (`ToolUsageStartedEvent`) — `step_callback` never sees tool steps under native function calling.
- **`ui.py`** — All Rich rendering (theme, panels, the live research dashboard, Markdown feedback). No business logic. The `Live` dashboard runs **only while the crew works** (research), `transient=True`, content-sized `Group` — never while reading user input (a running Live garbles `console.input`). Practice is plain scrollback prints. Answers are read multi-line: a blank line submits (prevents pasted lines from leaking into later prompts).

### CrewAI agents and tasks

Two agents, both on Claude Sonnet 4.6 (`MODEL_NAME = "anthropic/claude-sonnet-4-6"`, `temperature=0.2`, `max_tokens=1600`):
- **Research Agent** — has `SerperDevTool` + `ScrapeWebsiteTool`; runs the company task then the interviewer task.
- **Coach Agent** — generates the question deck (with the two research tasks as `context`), and separately scores each answer attempt.

Question generation is one sequential `Crew` of three tasks. Feedback is a fresh single-task `Crew` created per answer attempt (the coach agent and LLM are cached on the workflow instance and reused). Both use `kickoff_async` because the CLI runs inside an asyncio loop.

### Two intentional design decisions worth preserving

1. **Deterministic prompt + tolerant parser.** The question-gen task prompt pins an exact numbered-line output format (`1.`, `2.`, ...) for reproducibility, but `parse_interview_questions` still accepts numbered lines, plain bullets, `**Question N:**` notebook blocks, and same-line variants, then de-dupes. This pairing exists because models drift from the format and a strict parser previously caused hard failures. When changing either, keep them compatible.

2. **`research_depth` budgets.** `_research_limits()` caps search/scrape/iteration counts. `fast` (default) is deliberately small; `standard` matches the original notebook's heavier budget. These limits exist to control token spend — lowering `fast` or raising `standard` changes cost/latency on purpose.

### Session output

Each run writes `runs/interview-session-YYYYMMDD-HHMMSS.json` (overridable with `--output`) containing inputs, both research briefs, raw question markdown, parsed questions, every attempt with feedback, and early-exit state.

## Conventions

- All modules use `from __future__ import annotations`; Python 3.12+ syntax (`str | None`, `dict[str, str]`).
- Keep CrewAI imports lazy inside `workflow.py` — importing `cli`, `models`, or `parsing` must not require CrewAI or API keys (the test suite relies on this).
- The `chcp 65001` / `PYTHONUTF8=1` in `interview.cmd` exist for Windows console UTF-8; the Rich UI emits unicode.
