import random

from importers.base import cell_str, find_column, open_sheet, require_columns
from models import Option, Question

SINGLE_COLUMNS = [
    "编号",
    "题目",
    "正确答案(A)",
    "备选答案1(B)",
    "备选答案2(C)",
    "备选答案3(D)",
]


def load_single(path: str) -> list[Question]:
    sheet = open_sheet(path)
    headers = [cell_str(sheet, 1, col) for col in range(sheet.ncols)]
    require_columns(headers, SINGLE_COLUMNS, path)

    columns = {name: find_column(headers, name) for name in SINGLE_COLUMNS}

    questions: list[Question] = []
    for row in range(2, sheet.nrows):
        stem = cell_str(sheet, row, columns["题目"])
        if not stem:
            continue

        options = []
        for label, col_name in [
            ("A", "正确答案(A)"),
            ("B", "备选答案1(B)"),
            ("C", "备选答案2(C)"),
            ("D", "备选答案3(D)"),
        ]:
            text = cell_str(sheet, row, columns[col_name])
            if text:
                options.append(Option(label, text))

        questions.append(
            Question(
                type="single",
                original_id=cell_str(sheet, row, columns["编号"]),
                stem=stem,
                options=options,
                answer="A",
            )
        )
    return questions


def shuffle_single_options(question: Question, rng: random.Random) -> Question:
    """打乱单选选项顺序，并按新位置更新答案字母。Excel 中正确答案仍在 A 列，此处仅调整卷面顺序。"""
    if len(question.options) < 2:
        return question

    correct_text = next(
        (option.text for option in question.options if option.label == question.answer),
        None,
    )
    if correct_text is None:
        return question

    texts = [option.text for option in question.options]
    rng.shuffle(texts)
    new_options = [
        Option(chr(ord("A") + index), text) for index, text in enumerate(texts)
    ]
    new_answer = next(option.label for option in new_options if option.text == correct_text)

    return Question(
        type=question.type,
        original_id=question.original_id,
        stem=question.stem,
        options=new_options,
        answer=new_answer,
    )
