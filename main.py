#!/usr/bin/env python3
"""710型船柴油机专业操作技能自动组卷系统 — Auto-Generation System"""

from __future__ import annotations

import sys
from pathlib import Path

# Windows 嵌入式 Python 不会自动把程序目录加入模块路径
_APP_ROOT = Path(__file__).resolve().parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

import argparse

import yaml

from assembler import BatchAssembler, InsufficientQuestionsError
from bank_resolver import discover_bank_files, format_bank_listing
from paths import app_dir, resolve_path
from renderer import render_paper


def _normalize_config_text(text: str) -> str:
    """修正 Windows 记事本常见隐藏问题：Tab、中文引号等。"""
    text = text.replace("\t", "  ")
    for bad, good in (
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\uff02", '"'),
        ("\u2018", "'"),
        ("\u2019", "'"),
    ):
        text = text.replace(bad, good)
    return text


def load_config(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        raw = _normalize_config_text(raw)
        return yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SystemExit(
            f"config.yaml 格式错误: {exc}\n\n"
            "常见原因：\n"
            "  1. excel 下四行缩进不一致（必须用空格，每行前 2 格，不要用 Tab）\n"
            "  2. 路径用了中文引号或双引号写成了 \"\"...\"\"\n"
            "  3. 注释行里写了 D:\\题库 这类反斜杠路径\n\n"
            "建议：删除 config.yaml 全部内容，从 使用说明.txt 或下方模板重新粘贴：\n"
            "excel:\n"
            '  single: "题库/单选.xls"\n'
            '  multiple: "题库/多选.xls"\n'
            '  judge: "题库/判断.xls"\n'
            '  qa: "题库/问答.xls"'
        ) from exc


def resolve(path: str | Path) -> Path:
    return resolve_path(path)


def apply_excel_overrides(config: dict, args: argparse.Namespace) -> None:
    if getattr(args, "bank", None):
        config.pop("excel", None)
        return
    mapping = {
        "single": args.single,
        "multiple": args.multiple,
        "judge": args.judge,
        "qa": args.qa,
    }
    for key, value in mapping.items():
        if value:
            config.setdefault("excel", {})
            config["excel"][key] = value


def _has_cli_excel_overrides(args: argparse.Namespace) -> bool:
    return any((args.single, args.multiple, args.judge, args.qa))


def _pick_bank_name(banks: dict[str, str]) -> str:
    names = list(banks.keys())
    if len(names) == 1:
        return names[0]

    print("请选择题库：")
    for index, name in enumerate(names, start=1):
        print(f"  {index}. {name}")
    while True:
        raw = input("请输入编号: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(names):
            return names[int(raw) - 1]
        print("请输入有效编号。")


def resolve_excel_paths(config: dict, args: argparse.Namespace) -> tuple[dict[str, str], str | None]:
    if _has_cli_excel_overrides(args):
        return build_excel_paths(config), None

    banks = config.get("banks")
    if banks:
        if args.bank:
            bank_name = args.bank
            if bank_name not in banks:
                raise SystemExit(
                    f"未知题库「{bank_name}」。可选: {', '.join(banks.keys())}"
                )
        elif config.get("active_bank"):
            bank_name = config["active_bank"]
            if bank_name not in banks:
                raise SystemExit(
                    f"config.yaml 中 active_bank={bank_name!r} 不在 banks 列表里。"
                )
        else:
            bank_name = _pick_bank_name(banks)

        folder = resolve(banks[bank_name])
        discovered = discover_bank_files(folder)
        print(f"已选择题库: {bank_name}")
        print(format_bank_listing(discovered))
        return {key: str(path) for key, path in discovered.items()}, bank_name

    return build_excel_paths(config), None


def generate_batch(
    config: dict,
    paper_count: int,
    seed: int | None,
    excel_paths: dict[str, str],
    bank_name: str | None = None,
) -> list[Path]:
    counts = {
        "single": config["paper"]["single_count"],
        "multiple": config["paper"]["multiple_count"],
        "judge": config["paper"]["judge_count"],
        "short": config["paper"]["short_count"],
    }

    batch = BatchAssembler(excel_paths, counts, seed=seed)
    batch.validate_capacity(paper_count)

    output_dir = resolve(config["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = resolve(config["template"]["path"])

    outputs: list[Path] = []
    for index in range(1, paper_count + 1):
        paper = batch.assemble_next(index)
        filename = config["output"]["filename_pattern"].format(
            n=index,
            bank=bank_name or "",
        )
        output_path = output_dir / filename
        render_paper(
            template_path,
            paper,
            output_path,
            paper_title=config.get("paper", {}).get("title", ""),
        )
        outputs.append(output_path)
    return outputs


def build_excel_paths(config: dict) -> dict[str, str]:
    paths = {}
    missing: list[str] = []
    for key, path in config["excel"].items():
        resolved = resolve(path)
        if not resolved.exists():
            missing.append(f"  {key}: {resolved}")
        else:
            paths[key] = str(resolved)

    if missing:
        bank_dir = app_dir() / "题库"
        hint = ""
        if bank_dir.is_dir():
            found = sorted(p.name for p in bank_dir.iterdir() if p.is_file())
            hint = f"\n\n「题库」文件夹里现有文件：\n  " + "\n  ".join(found or ["（空）"])
            hint += (
                f"\n\n需要以下 4 个文件（文件名必须一致）：\n"
                f"  单选.xls  多选.xls  判断.xls  问答.xls"
            )
        raise FileNotFoundError("题库文件不存在:\n" + "\n".join(missing) + hint)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="710型船柴油机专业操作自动组卷")
    parser.add_argument(
        "--config",
        default=str(app_dir() / "config.yaml"),
        help="配置文件路径",
    )
    parser.add_argument("--count", type=int, default=None, help="生成试卷份数")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--single", help="单选题库 .xls 路径（覆盖 config）")
    parser.add_argument("--multiple", help="多选题库 .xls 路径（覆盖 config）")
    parser.add_argument("--judge", help="判断题库 .xls 路径（覆盖 config）")
    parser.add_argument("--qa", help="问答题库 .xls 路径（覆盖 config）")
    parser.add_argument(
        "--bank",
        help="banks 配置中的题库名称，如 操作初级（跳过交互选择）",
    )
    args = parser.parse_args()

    paper_count = args.count
    if paper_count is None:
        while True:
            raw = input("请输入要生成的试卷份数: ").strip()
            if raw.isdigit() and int(raw) > 0:
                paper_count = int(raw)
                break
            print("请输入大于 0 的整数。")

    seed = args.seed
    if seed is None and paper_count is not None and args.count is None:
        raw = input("请输入随机种子(直接回车则每次随机): ").strip()
        if raw.isdigit():
            seed = int(raw)

    config = load_config(resolve(args.config))
    apply_excel_overrides(config, args)
    excel_paths, bank_name = resolve_excel_paths(config, args)

    try:
        outputs = generate_batch(config, paper_count, seed, excel_paths, bank_name)
    except InsufficientQuestionsError as exc:
        raise SystemExit(f"组卷失败: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"生成试卷失败: {exc}") from exc

    for output in outputs:
        print(f"已生成: {output}")


if __name__ == "__main__":
    main()
