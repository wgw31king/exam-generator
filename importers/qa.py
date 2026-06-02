import xlrd

from importers.base import cell_str, find_column, open_sheet, require_columns
from models import Question


def load_qa(path: str) -> list[Question]:
    try:
        return _load_standard_xls(path)
    except xlrd.biffh.XLRDError as exc:
        raise ValueError(
            f"{path} 不是标准 .xls 格式（可能是 NT195 加密题库）。"
            "请用 Excel 打开后另存为标准 .xls，或运行 scripts/convert_nt195_qa.py 转换。"
        ) from exc


def _load_standard_xls(path: str) -> list[Question]:
    sheet = open_sheet(path)
    headers = [cell_str(sheet, 1, col) for col in range(sheet.ncols)]
    require_columns(headers, ["编号", "题目", "正确答案"], path)

    answer_col = find_column(headers, "正确答案")
    alt_cols = []
    for idx in range(1, 7):
        col = find_column(headers, f"备选答案{idx}")
        if col is not None:
            alt_cols.append(col)

    questions: list[Question] = []
    for row in range(2, sheet.nrows):
        stem = cell_str(sheet, row, find_column(headers, "题目"))
        if not stem:
            continue

        answer = cell_str(sheet, row, answer_col)
        questions.append(
            Question(
                type="short",
                original_id=cell_str(sheet, row, find_column(headers, "编号")),
                stem=stem,
                answer=answer,
            )
        )
    return questions
