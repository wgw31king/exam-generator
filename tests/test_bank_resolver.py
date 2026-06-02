from pathlib import Path

import pytest

from bank_resolver import discover_bank_files


def test_discover_bank_files(tmp_path: Path):
    names = {
        "710型舰柴油机专业操作技能初级--单选-旧标签.xls": "single",
        "710型舰柴油机专业操作技能初级--多选.xls": "multiple",
        "710型舰柴油机专业操作技能初级--判断.xls": "judge",
        "710型舰柴油机专业操作技能初级--问答.xls": "qa",
    }
    for filename in names:
        (tmp_path / filename).write_bytes(b"\xd0\xcf\x11\xe0")

    found = discover_bank_files(tmp_path)
    assert set(found) == {"single", "multiple", "judge", "qa"}
    assert "单选" in found["single"].name


def test_discover_bank_files_missing(tmp_path: Path):
    (tmp_path / "只有单选.xls").write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(FileNotFoundError, match="多选"):
        discover_bank_files(tmp_path)
