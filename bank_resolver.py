"""从文件夹自动识别单选/多选/判断/问答四个 xls 文件。"""

from __future__ import annotations

from pathlib import Path

BANK_KEYS = ("single", "multiple", "judge", "qa")
KEYWORDS = {
    "single": ("单选",),
    "multiple": ("多选",),
    "judge": ("判断",),
    "qa": ("问答", "简答"),
}


def discover_bank_files(directory: Path) -> dict[str, Path]:
    """在目录中按文件名关键词匹配四个题库文件。"""
    if not directory.is_dir():
        raise FileNotFoundError(f"题库文件夹不存在: {directory}")

    files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".xls"
    )
    if not files:
        raise FileNotFoundError(f"文件夹中没有 .xls 文件: {directory}")

    found: dict[str, Path] = {}
    for key in BANK_KEYS:
        matches = [
            path
            for path in files
            if any(keyword in path.name for keyword in KEYWORDS[key])
        ]
        if not matches:
            raise FileNotFoundError(
                f"在 {directory} 中未找到含「{KEYWORDS[key][0]}」的 .xls 文件。\n"
                f"现有文件: {', '.join(path.name for path in files)}"
            )
        found[key] = sorted(matches, key=lambda p: len(p.name))[0]

    return found


def format_bank_listing(paths: dict[str, Path]) -> str:
    labels = {
        "single": "单选",
        "multiple": "多选",
        "judge": "判断",
        "qa": "问答",
    }
    lines = [f"  {labels[key]}: {path.name}" for key, path in paths.items()]
    return "\n".join(lines)
