from importers.base import cell_str, find_column, open_sheet, require_columns
from models import Option, Question


def load_multiple(path: str) -> list[Question]:
    sheet = open_sheet(path)
    headers = [cell_str(sheet, 1, col) for col in range(sheet.ncols)]
    require_columns(headers, ["编号", "题目", "正确答案选项"], path)

    answer_col = find_column(headers, "正确答案选项")
    option_cols = {}
    for letter in "ABCDEF":
        col = find_column(headers, f"备选答案({letter})")
        if col is not None:
            option_cols[letter] = col

    questions: list[Question] = []
    for row in range(2, sheet.nrows):
        stem = cell_str(sheet, row, find_column(headers, "题目"))
        if not stem:
            continue

        options = []
        for letter, col in option_cols.items():
            text = cell_str(sheet, row, col)
            if text:
                options.append(Option(letter, text))

        answer = cell_str(sheet, row, answer_col).upper().replace(" ", "")
        questions.append(
            Question(
                type="multiple",
                original_id=cell_str(sheet, row, find_column(headers, "编号")),
                stem=stem,
                options=options,
                answer=answer,
            )
        )
    return questions
