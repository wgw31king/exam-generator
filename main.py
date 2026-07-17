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

from assembler import InsufficientQuestionsError
from paths import app_dir
from service import (
    describe_bank_files,
    friendly_error,
    generate_batch,
    load_config,
    resolve,
    resolve_excel_paths,
)


def apply_excel_overrides(config: dict, args: argparse.Namespace) -> None:
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
    if getattr(args, "bank", None):
        # 选题库时忽略固定 excel，走 banks 发现逻辑
        config.pop("excel", None)


def _has_cli_excel_overrides(args: argparse.Namespace) -> bool:
    return any((args.single, args.multiple, args.judge, args.qa))


def _launch_ui(config_path: Path) -> None:
    try:
        import tkinter  # noqa: F401
        from ui import run_app

        run_app(config_path=config_path)
    except ImportError:
        from web_ui import run_web_app

        print("未检测到 tkinter，改为启动本地网页界面…")
        print("浏览器打开 http://127.0.0.1:8765/ 即可组卷；关闭本窗口即停止。")
        run_web_app(config_path=config_path)


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
    parser.add_argument(
        "--ui",
        action="store_true",
        help="启动图形界面（一键组卷）",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="强制命令行模式（即使无其它参数也不开界面）",
    )
    args = parser.parse_args()

    # 双击 exe / 无参数启动 → 直接开界面，方便 Windows 用户
    want_ui = args.ui or (len(sys.argv) == 1 and not args.cli)
    if want_ui:
        _launch_ui(resolve(args.config))
        return

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

    try:
        config = load_config(resolve(args.config))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    apply_excel_overrides(config, args)

    excel_overrides = None
    if _has_cli_excel_overrides(args):
        excel_overrides = {
            key: value
            for key, value in {
                "single": args.single,
                "multiple": args.multiple,
                "judge": args.judge,
                "qa": args.qa,
            }.items()
            if value
        }

    try:
        excel_paths, bank_name = resolve_excel_paths(
            config,
            bank_name=args.bank,
            excel_overrides=excel_overrides,
            interactive_pick=not args.bank and not excel_overrides,
        )
        if bank_name:
            print(f"已选择题库: {bank_name}")
            print(describe_bank_files(excel_paths))
        outputs = generate_batch(config, paper_count, seed, excel_paths, bank_name)
    except InsufficientQuestionsError as exc:
        raise SystemExit(friendly_error(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"生成试卷失败: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"生成试卷失败: {exc}") from exc

    for output in outputs:
        print(f"已生成: {output}")


if __name__ == "__main__":
    main()
