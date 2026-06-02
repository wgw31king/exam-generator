from importers.base import cell_str, find_column, open_sheet, require_columns
from models import Question


def load_judge(path: str) -> list[Question]:
    sheet = open_sheet(path)
    headers = [cell_str(sheet, 1, col) for col in range(sheet.ncols)]
    require_columns(headers, ["编号", "题目", "正确答案选项"], path)

    answer_col = find_column(headers, "正确答案选项")
    questions: list[Question] = []
    for row in range(2, sheet.nrows):
        stem = cell_str(sheet, row, find_column(headers, "题目"))
        if not stem:
            continue

        answer = cell_str(sheet, row, answer_col)
        answer = answer.replace("√", "√").replace("×", "×")
        if answer in ("对", "正确", "T", "Y", "true", "TRUE"):
            answer = "√"
        elif answer in ("错", "错误", "F", "N", "false", "FALSE"):
            answer = "×"

        questions.append(
            Question(
                type="judge",
                original_id=cell_str(sheet, row, find_column(headers, "编号")),
                stem=stem,
                answer=answer,
            )
        )
    return questions
