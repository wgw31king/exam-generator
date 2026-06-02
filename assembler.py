import random

from importers.judge import load_judge
from importers.multiple import load_multiple
from importers.qa import load_qa
from importers.single import load_single, shuffle_single_options
from models import Paper, Question


class InsufficientQuestionsError(Exception):
    pass


def _load_pools(excel_paths: dict[str, str]) -> dict[str, list[Question]]:
    return {
        "single": load_single(excel_paths["single"]),
        "multiple": load_multiple(excel_paths["multiple"]),
        "judge": load_judge(excel_paths["judge"]),
        "short": load_qa(excel_paths["qa"]),
    }


class BatchAssembler:
    """批量组卷：多份试卷之间题目不重复。"""

    def __init__(
        self,
        excel_paths: dict[str, str],
        counts: dict[str, int],
        seed: int | None = None,
    ) -> None:
        self.counts = counts
        self.rng = random.Random(seed)
        self.pools = _load_pools(excel_paths)
        self.remaining: dict[str, list[Question]] = {
            key: list(questions) for key, questions in self.pools.items()
        }

    def validate_capacity(self, paper_count: int) -> None:
        for key, per_paper in self.counts.items():
            needed = per_paper * paper_count
            available = len(self.remaining[key])
            if available < needed:
                raise InsufficientQuestionsError(
                    f"{key} 题库仅有 {available} 题，"
                    f"生成 {paper_count} 份卷需要 {needed} 题（每份 {per_paper} 题）"
                )

    def assemble_next(self, paper_index: int) -> Paper:
        paper = Paper()
        paper.log.append(f"=== 第 {paper_index} 份试卷 ===")
        paper.log.append("")

        for key, count in self.counts.items():
            pool = self.remaining[key]
            if len(pool) < count:
                raise InsufficientQuestionsError(
                    f"{key} 剩余 {len(pool)} 题，不足以组成第 {paper_index} 份卷（需要 {count} 题）"
                )
            selected = self.rng.sample(pool, count)
            if key == "single":
                selected = [shuffle_single_options(q, self.rng) for q in selected]
            selected_ids = {question.original_id for question in selected}
            self.remaining[key] = [
                question for question in pool if question.original_id not in selected_ids
            ]
            setattr(paper, key, selected)
            _append_log(paper, key, selected)

        return paper


def assemble_paper(
    excel_paths: dict[str, str],
    counts: dict[str, int],
    seed: int | None = None,
) -> Paper:
    batch = BatchAssembler(excel_paths, counts, seed=seed)
    batch.validate_capacity(1)
    return batch.assemble_next(1)


def _append_log(paper: Paper, section: str, questions: list[Question]) -> None:
    titles = {
        "single": "一、单选题",
        "multiple": "二、多选题",
        "judge": "三、判断题",
        "short": "四、简答题",
    }
    paper.log.append(titles[section])
    for idx, question in enumerate(questions, start=1):
        preview = question.stem.replace("\n", " ")[:40]
        if question.type == "multiple":
            paper.log.append(
                f"{idx} -> Excel编号 {question.original_id} | 选项数 {len(question.options)} | 答案 {question.answer} | {preview}"
            )
        else:
            paper.log.append(
                f"{idx} -> Excel编号 {question.original_id} | {preview}"
            )
    paper.log.append("")
