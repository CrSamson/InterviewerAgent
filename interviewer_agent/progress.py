from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading
import time


class Phase(str, Enum):
    BOOT = "BOOT"
    RESEARCH = "RESEARCH"
    QUESTION_GEN = "QUESTION GEN"
    PRACTICE = "PRACTICE"
    SESSION_SAVED = "SESSION SAVED"


PHASE_ORDER = (
    Phase.BOOT,
    Phase.RESEARCH,
    Phase.QUESTION_GEN,
    Phase.PRACTICE,
    Phase.SESSION_SAVED,
)


@dataclass(frozen=True)
class TaskProgress:
    key: str
    label: str
    done: bool = False


@dataclass(frozen=True)
class ProgressSnapshot:
    phase: Phase
    depth: str
    question_count: int
    max_attempts: int
    elapsed_seconds: int
    research_tasks: tuple[TaskProgress, ...]
    research_completed: int
    now_line: str
    tool_calls: int
    error: str | None


class ProgressState:
    def __init__(
        self,
        *,
        depth: str,
        question_count: int,
        max_attempts: int,
    ) -> None:
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._phase = Phase.BOOT
        self._depth = depth
        self._question_count = question_count
        self._max_attempts = max_attempts
        self._research_tasks = {
            "company": TaskProgress("company", "Company brief"),
            "interviewer": TaskProgress("interviewer", "Interviewer context"),
            "questions": TaskProgress("questions", "Question deck"),
        }
        self._now_line = "Booting interview console"
        self._tool_calls = 0
        self._error: str | None = None

    def set_phase(self, phase: Phase) -> None:
        with self._lock:
            self._phase = phase
            self._now_line = _phase_now_line(phase)

    def note_tool_call(self, tool: str) -> None:
        label = _clean_tool_name(tool)
        with self._lock:
            self._tool_calls += 1
            self._now_line = f"Using tool: {label}"

    def note_thinking(self, text: str) -> None:
        cleaned = " ".join(str(text).split())
        if len(cleaned) > 90:
            cleaned = cleaned[:87].rstrip() + "..."
        if not cleaned:
            return
        with self._lock:
            self._now_line = cleaned

    def complete_task(self, key: str) -> None:
        with self._lock:
            existing = self._research_tasks.get(key)
            if not existing:
                return
            self._research_tasks[key] = TaskProgress(
                key=existing.key,
                label=existing.label,
                done=True,
            )
            self._now_line = f"Completed: {existing.label}"

    def set_error(self, message: str) -> None:
        with self._lock:
            self._error = message
            self._now_line = "Error"

    def snapshot(self) -> ProgressSnapshot:
        with self._lock:
            research_tasks = tuple(self._research_tasks.values())
            completed = sum(1 for task in research_tasks if task.done)
            return ProgressSnapshot(
                phase=self._phase,
                depth=self._depth,
                question_count=self._question_count,
                max_attempts=self._max_attempts,
                elapsed_seconds=int(time.monotonic() - self._started_at),
                research_tasks=research_tasks,
                research_completed=completed,
                now_line=self._now_line,
                tool_calls=self._tool_calls,
                error=self._error,
            )


def _phase_now_line(phase: Phase) -> str:
    return {
        Phase.BOOT: "Checking environment and collecting inputs",
        Phase.RESEARCH: "Starting focused research",
        Phase.QUESTION_GEN: "Preparing question deck",
        Phase.PRACTICE: "Practice loop ready",
        Phase.SESSION_SAVED: "Session saved",
    }[phase]


def _clean_tool_name(tool: str) -> str:
    cleaned = str(tool or "tool").replace("_", " ").strip()
    return cleaned[:60] if cleaned else "tool"
