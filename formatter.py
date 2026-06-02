import re

from models import Question

SHORT_BLANK_LINES = 8
SCORE_PATTERN = re.compile(r"[（(]\s*\d+\s*分[）)]")


def _ensure_score(stem: str, points: int) -> str:
    """题干末尾统一为（N分）标记；若已有分值则替换。"""
    score = f"（{points}分）"
    if SCORE_PATTERN.search(stem):
        return SCORE_PATTERN.sub(score, stem, count=1)
    return f"{stem.rstrip('。')}{score}"


def format_single_questions(questions: list[Question]) -> list[dict]:
    items = []
    for idx, question in enumerate(questions, start=1):
        options_line = " ".join(
            f"{option.label}. {option.text}" for option in question.options
        )
        items.append({"stem": f"{idx}. {question.stem}", "options_line": options_line})
    return items


def format_multiple_questions(questions: list[Question]) -> list[dict]:
    items = []
    for idx, question in enumerate(questions, start=1):
        stem = _ensure_score(question.stem.rstrip("。"), 1) + "。"
        options_line = " ".join(
            f"{option.label}. {option.text}" for option in question.options
        )
        items.append({"stem": f"{idx}. {stem}", "options_line": options_line})
    return items


def format_judge_questions(questions: list[Question]) -> list[dict]:
    items = []
    for idx, question in enumerate(questions, start=1):
        stem = _ensure_score(question.stem.rstrip("。"), 1)
        if not stem.endswith("（  ）"):
            stem = f"{stem}。（  ）"
        items.append({"stem": f"{idx}.(  ) {stem}"})
    return items


def format_short_questions(questions: list[Question]) -> list[dict]:
    items = []
    for idx, question in enumerate(questions, start=1):
        stem = _ensure_score(question.stem, 6)
        items.append({"stem": f"{idx}. {stem}", "blank_lines": SHORT_BLANK_LINES})
    return items


def format_choice_answer_lines(questions: list[Question]) -> list[str]:
    lines = []
    for start in range(0, len(questions), 5):
        chunk = questions[start : start + 5]
        parts = [f"{start + i + 1}.{q.answer}" for i, q in enumerate(chunk)]
        lines.append("    ".join(parts))
    return lines


def format_short_answer_lines(questions: list[Question]) -> list[str]:
    lines: list[str] = []
    for idx, question in enumerate(questions, start=1):
        answer = question.answer.replace("\n", "\n")
        lines.append(f"{idx}.{answer}")
    return lines
