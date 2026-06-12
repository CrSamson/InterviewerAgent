from __future__ import annotations

import re


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
