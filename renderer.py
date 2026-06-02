from pathlib import Path

from docxtpl import DocxTemplate

from doc_styles import (
    add_answer_line_paragraph,
    add_blank_paragraph,
    add_body_paragraph,
    add_options_paragraph,
    add_stem_paragraph,
)
from formatter import (
    format_choice_answer_lines,
    format_judge_questions,
    format_multiple_questions,
    format_short_questions,
    format_single_questions,
    SHORT_BLANK_LINES,
)
from models import Paper


def _fill_single_subdoc(doc: DocxTemplate, questions: list) -> object:
    sub = doc.new_subdoc()
    for item in format_single_questions(questions):
        add_stem_paragraph(sub, item["stem"])
        add_options_paragraph(sub, item["options_line"])
    return sub


def _fill_multiple_subdoc(doc: DocxTemplate, questions: list) -> object:
    sub = doc.new_subdoc()
    for item in format_multiple_questions(questions):
        add_stem_paragraph(sub, item["stem"])
        add_options_paragraph(sub, item["options_line"])
    return sub


def _fill_judge_subdoc(doc: DocxTemplate, questions: list) -> object:
    sub = doc.new_subdoc()
    for item in format_judge_questions(questions):
        add_stem_paragraph(sub, item["stem"])
    return sub


def _fill_short_subdoc(doc: DocxTemplate, questions: list) -> object:
    sub = doc.new_subdoc()
    for item in format_short_questions(questions):
        add_stem_paragraph(sub, item["stem"])
        for _ in range(SHORT_BLANK_LINES):
            add_blank_paragraph(sub)
    return sub


def _fill_answer_lines_subdoc(doc: DocxTemplate, lines: list[str]) -> object:
    sub = doc.new_subdoc()
    for line in lines:
        add_answer_line_paragraph(sub, line)
    return sub


def _fill_short_answer_subdoc(doc: DocxTemplate, questions: list) -> object:
    sub = doc.new_subdoc()
    for idx, question in enumerate(questions, start=1):
        lines = question.answer.split("\n")
        add_stem_paragraph(sub, f"{idx}.{lines[0]}")
        for line in lines[1:]:
            add_body_paragraph(sub, line)
    return sub


def render_paper(
    template_path: str | Path,
    paper: Paper,
    output_path: str | Path,
    paper_title: str = "",
) -> None:
    doc = DocxTemplate(str(template_path))
    context = {
        "paper_title": paper_title,
        "single_questions": _fill_single_subdoc(doc, paper.single),
        "multiple_questions": _fill_multiple_subdoc(doc, paper.multiple),
        "judge_questions": _fill_judge_subdoc(doc, paper.judge),
        "short_questions": _fill_short_subdoc(doc, paper.short),
        "single_answer_lines": _fill_answer_lines_subdoc(
            doc, format_choice_answer_lines(paper.single)
        ),
        "multiple_answer_lines": _fill_answer_lines_subdoc(
            doc, format_choice_answer_lines(paper.multiple)
        ),
        "judge_answer_lines": _fill_answer_lines_subdoc(
            doc, format_choice_answer_lines(paper.judge)
        ),
        "short_answer_lines": _fill_short_answer_subdoc(doc, paper.short),
    }
    doc.render(context)
    doc.save(str(output_path))
