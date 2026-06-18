from __future__ import annotations

import re

from .models import FeedbackReport, SessionSummary


NOTEBOOK_QUESTION_PATTERN = re.compile(
    r'\*\*Question\s+\d+[^\n]*:\*\*\s*\n\s+\*"(.*?)"\*',
    flags=re.DOTALL | re.IGNORECASE,
)

SAME_LINE_QUESTION_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?\*\*Question\s+\d+[^\n]*:\*\*\s*(.+?)\s*$",
    flags=re.IGNORECASE,
)

NUMBERED_QUESTION_PATTERN = re.compile(r"^\s*\d{1,2}[\).\:-]\s+(.+?)\s*$")

BULLET_QUESTION_PATTERN = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")

FIELD_PATTERNS = {
    "score": re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?Score(?:\*\*)?\s*:\s*(.+?)\s*$", re.I),
    "what_worked": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?What worked(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "missing_signal": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Missing signal(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "stronger_outline": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Stronger outline(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "next_instruction": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Next (?:revision|instruction)(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "recurring_gaps": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Recurring gaps(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "strongest_answer": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Strongest answer(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "weakest_answer": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Weakest answer(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
    "next_practice_plan": re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?Next practice plan(?:\*\*)?\s*:\s*(.+?)\s*$",
        re.I,
    ),
}


def parse_interview_questions(questions_text: object) -> list[str]:
    raw_text = str(questions_text)
    matches = NOTEBOOK_QUESTION_PATTERN.findall(raw_text)

    if not matches:
        matches = _parse_line_oriented_questions(raw_text)

    questions: list[str] = []
    seen: set[str] = set()
    for match in matches:
        question = clean_question(match)
        key = question.casefold()
        if question and key not in seen:
            questions.append(question)
            seen.add(key)

    return questions


def clean_question(question: str) -> str:
    value = re.sub(r"\s+", " ", question).strip()
    value = re.sub(
        r"^(?:\*\*)?Question\s+\d+[^\n]*?:(?:\*\*)?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = _strip_wrapping_markdown(value)
    return value


def parse_feedback_report(markdown: object) -> FeedbackReport:
    raw_markdown = str(markdown or "").strip()
    fields = _parse_named_fields(
        raw_markdown,
        ("score", "what_worked", "missing_signal", "stronger_outline", "next_instruction"),
    )
    score = _parse_score(fields.get("score", ""))
    return FeedbackReport(
        score=score,
        what_worked=fields.get("what_worked", ""),
        missing_signal=fields.get("missing_signal", ""),
        stronger_outline=fields.get("stronger_outline", ""),
        next_instruction=fields.get("next_instruction", ""),
        raw_markdown=raw_markdown,
    )


def parse_session_summary(markdown: object) -> SessionSummary:
    raw_markdown = str(markdown or "").strip()
    fields = _parse_named_fields(
        raw_markdown,
        ("recurring_gaps", "strongest_answer", "weakest_answer", "next_practice_plan"),
    )
    return SessionSummary(
        recurring_gaps=fields.get("recurring_gaps", ""),
        strongest_answer=fields.get("strongest_answer", ""),
        weakest_answer=fields.get("weakest_answer", ""),
        next_practice_plan=fields.get("next_practice_plan", ""),
        raw_markdown=raw_markdown,
    )


def _parse_line_oriented_questions(raw_text: str) -> list[str]:
    matches: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        same_line = SAME_LINE_QUESTION_PATTERN.match(stripped)
        if same_line:
            matches.append(same_line.group(1))
            continue

        numbered = NUMBERED_QUESTION_PATTERN.match(stripped)
        if numbered:
            matches.append(numbered.group(1))
            continue

        bullet = BULLET_QUESTION_PATTERN.match(stripped)
        if bullet:
            matches.append(bullet.group(1))

    return matches


def _parse_named_fields(raw_text: str, names: tuple[str, ...]) -> dict[str, str]:
    fields: dict[str, str] = {}
    active_name: str | None = None
    active_lines: list[str] = []

    def flush() -> None:
        if active_name:
            fields[active_name] = " ".join(active_lines).strip()

    for line in raw_text.splitlines():
        stripped = line.strip()
        matched_name = None
        matched_value = ""
        for name in names:
            match = FIELD_PATTERNS[name].match(stripped)
            if match:
                matched_name = name
                matched_value = match.group(1).strip()
                break

        if matched_name:
            flush()
            active_name = matched_name
            active_lines = [matched_value] if matched_value else []
            continue

        if active_name and stripped:
            active_lines.append(stripped.lstrip("-* ").strip())

    flush()
    return fields


def _parse_score(value: str) -> int | None:
    match = re.search(r"\b([1-5])(?:\s*/\s*5)?\b", value)
    if not match:
        return None
    return int(match.group(1))


def _strip_wrapping_markdown(value: str) -> str:
    cleaned = value.strip()

    for marker in ('"', "'"):
        if cleaned.startswith(marker) and cleaned.endswith(marker) and len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()

    for marker in ("***", "**", "*", "__", "_"):
        if cleaned.startswith(marker) and cleaned.endswith(marker) and len(cleaned) > len(marker) * 2:
            cleaned = cleaned[len(marker) : -len(marker)].strip()

    for marker in ('"', "'"):
        if cleaned.startswith(marker) and cleaned.endswith(marker) and len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()

    return cleaned
