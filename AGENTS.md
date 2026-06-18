# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.12 CLI project for a Rich/Typer interface around an interview-prep workflow. Production code lives in `interviewer_agent/`: `cli.py` is the thin Typer entrypoint, `controller.py` owns the deterministic session flow, `engine.py` defines the provider-neutral orchestration protocol, `workflow.py` contains the CrewAI adapter, `models.py` holds dataclasses and command constants, `parsing.py` handles tolerant text parsing, `progress.py` tracks thread-safe progress, and `ui.py` renders Rich output. Tests live in `tests/`. `scripts/` contains utilities, `diagrams/` stores PNG architecture assets, `runs/` contains session JSON, and notebooks are reference material.

## Build, Test, and Development Commands

Create and install a local editable environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Run the app through the Windows wrapper or installed entry point:

```powershell
.\interview
interviewer-agent run
```

Run all tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Run one test module or test case:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_parsing
```

Regenerate architecture diagrams with `.\.venv\Scripts\python.exe .\scripts\generate_diagrams.py`; this requires Pillow.

## Coding Style & Naming Conventions

Use 4-space indentation, type hints, and Python 3.12 syntax such as `str | None`. Existing modules use `from __future__ import annotations`; keep that pattern for new modules. Use `snake_case` for modules, functions, variables, and test methods; use `PascalCase` for dataclasses and classes. Keep CrewAI imports lazy and localized to `workflow.py`; controller, models, parsing, and UI tests must stay runnable without CrewAI calls.

## Testing Guidelines

Tests use the standard-library `unittest` runner. Name files `test_<module>.py` and test classes descriptively, for example `PracticeLoopTests`. Add focused tests for parser tolerance, workflow configuration, CLI branching, and session serialization when touching those areas. Prefer dependency injection, as in the CLI workflow factory, over real network or LLM calls in tests.

## Commit & Pull Request Guidelines

The current history uses short, capitalized summary commits such as `Initial Commit` and `Improved the UI and the flow of the interviewer agent.` Keep subjects concise and outcome-focused. Pull requests should describe the behavior change, list the test command run, note any `.env` or dependency changes, and include terminal screenshots or sample output for Rich UI changes.

## Security & Configuration Tips

Do not commit `.env`, API keys, generated session records, or local virtualenv files. Runtime configuration expects `ANTHROPIC_API_KEY` and `SERPER_API_KEY`; failures should remain clear at the `BOOT` stage.
