from pathlib import Path

import pytest

from assembler import BatchAssembler, InsufficientQuestionsError, assemble_paper
from importers.judge import load_judge
from importers.multiple import load_multiple
from importers.qa import load_qa
from importers.single import load_single, shuffle_single_options

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample_data"


from formatter import (
    format_judge_questions,
    format_multiple_questions,
    format_short_questions,
)
from models import Question, Option


def test_question_score_markers():
    multiple = Question(
        type="multiple",
        original_id="m1",
        stem="柴油机曲轴上设置的平衡重块，不能平衡（ ）",
        options=[Option("A", "a"), Option("B", "b")],
        answer="AB",
    )
    judge = Question(
        type="judge",
        original_id="j1",
        stem="8PC2-5L主机运转初期是活塞环与气缸套之间的最容易发生拉缸的时期",
        answer="√",
    )
    short = Question(
        type="short",
        original_id="s1",
        stem="GCH710型齿轮箱常见故障有哪些？（5分）",
        answer="答案",
    )
    short_half = Question(
        type="short",
        original_id="s2",
        stem="如何按照柴油机的性能，正确的操作管理。(5分)",
        answer="答案",
    )

    assert "（1分）" in format_multiple_questions([multiple])[0]["stem"]
    assert "（1分）" in format_judge_questions([judge])[0]["stem"]
    assert format_short_questions([short])[0]["stem"].endswith("（6分）")
    assert format_short_questions([short_half])[0]["stem"].endswith("（6分）")
    assert "5分" not in format_short_questions([short_half])[0]["stem"]


def test_load_single():
    questions = load_single(str(SAMPLE / "单选.xls"))
    assert len(questions) >= 30
    assert questions[0].type == "single"
    assert len(questions[0].options) == 4
    assert questions[0].answer in "ABCD"


def test_load_multiple():
    questions = load_multiple(str(SAMPLE / "多选.xls"))
    assert len(questions) >= 20
    assert questions[0].type == "multiple"
    assert questions[0].answer


def test_load_judge():
    questions = load_judge(str(SAMPLE / "判断.xls"))
    assert len(questions) >= 20
    assert questions[0].answer in ("√", "×")


def test_load_qa():
    questions = load_qa(str(SAMPLE / "问答.xls"))
    assert len(questions) >= 5
    assert questions[0].answer


def test_assemble():
    paths = {
        "single": str(SAMPLE / "单选.xls"),
        "multiple": str(SAMPLE / "多选.xls"),
        "judge": str(SAMPLE / "判断.xls"),
        "qa": str(SAMPLE / "问答.xls"),
    }
    counts = {"single": 30, "multiple": 20, "judge": 20, "short": 5}
    paper = assemble_paper(paths, counts, seed=42)
    assert len(paper.single) == 30
    assert len(paper.multiple) == 20
    assert len(paper.judge) == 20
    assert len(paper.short) == 5


def test_shuffle_single_options():
    import random

    q = load_single(str(SAMPLE / "单选.xls"))[0]
    shuffled = shuffle_single_options(q, random.Random(42))
    assert [o.label for o in shuffled.options] == ["A", "B", "C", "D"]
    original_correct = next(o.text for o in q.options if o.label == q.answer)
    answer_text = next(o.text for o in shuffled.options if o.label == shuffled.answer)
    assert answer_text == original_correct


def test_insufficient_pool():
    paths = {
        "single": str(SAMPLE / "单选.xls"),
        "multiple": str(SAMPLE / "多选.xls"),
        "judge": str(SAMPLE / "判断.xls"),
        "qa": str(SAMPLE / "问答.xls"),
    }
    with pytest.raises(InsufficientQuestionsError):
        assemble_paper(paths, {"single": 9999, "multiple": 20, "judge": 20, "short": 5})


def test_batch_no_overlap():
    paths = {
        "single": str(SAMPLE / "单选.xls"),
        "multiple": str(SAMPLE / "多选.xls"),
        "judge": str(SAMPLE / "判断.xls"),
        "qa": str(SAMPLE / "问答.xls"),
    }
    counts = {"single": 10, "multiple": 5, "judge": 10, "short": 2}
    batch = BatchAssembler(paths, counts, seed=42)
    batch.validate_capacity(2)
    paper1 = batch.assemble_next(1)
    paper2 = batch.assemble_next(2)

    for attr in ("single", "multiple", "judge", "short"):
        ids1 = {q.original_id for q in getattr(paper1, attr)}
        ids2 = {q.original_id for q in getattr(paper2, attr)}
        assert ids1.isdisjoint(ids2), attr
