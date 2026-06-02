#!/usr/bin/env python3
"""打包 Windows 离线发布目录（不含题库，由用户自行准备）。"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
EXE_NAME = "组卷工具.exe" if platform.system() == "Windows" else "组卷工具"
APP_NAME = "组卷工具.app"

BANK_README = """请将四个 Excel 题库文件放入本文件夹：

  单选.xls
  多选.xls
  判断.xls
  问答.xls

若文件名或位置不同，请用记事本编辑上级目录的 config.yaml，
将 excel 下的路径改为本机实际路径。
"""


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def _prepare_question_bank_dir(release_dir: Path) -> None:
    bank_dir = release_dir / "题库"
    bank_dir.mkdir(parents=True, exist_ok=True)
    readme = bank_dir / "请放入四个题库文件.txt"
    readme.write_text(BANK_README, encoding="utf-8")


def _write_windows_launcher(release_dir: Path) -> None:
    launcher = release_dir / "组卷.bat"
    launcher.write_text(
        "\n".join(
            [
                "@echo off",
                "chcp 65001 >nul",
                "set PYTHONUTF8=1",
                "set PYTHONIOENCODING=utf-8",
                'cd /d "%~dp0"',
                f'"{EXE_NAME}"',
                "echo.",
                "pause",
                "",
            ]
        ),
        encoding="ascii",
    )


def _write_mac_launcher(release_dir: Path) -> None:
    launcher = release_dir / "组卷.command"
    launcher.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                'cd "$(dirname "$0")"',
                'read -p "请输入要生成的试卷份数: " COUNT',
                'while ! [[ "$COUNT" =~ ^[1-9][0-9]*$ ]]; do',
                '  read -p "请输入大于 0 的整数: " COUNT',
                "done",
                'read -p "请输入随机种子(直接回车则随机): " SEED',
                'if [ -z "$SEED" ]; then',
                f'  ./{EXE_NAME.replace(".exe", "")} --count "$COUNT"',
                "else",
                f'  ./{EXE_NAME.replace(".exe", "")} --count "$COUNT" --seed "$SEED"',
                "fi",
                'read -p "按回车键关闭..."',
                "",
            ]
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)


def _write_readme(release_dir: Path) -> None:
    readme = release_dir / "使用说明.txt"
    readme.write_text(
        "\n".join(
            [
                "710型船柴油机专业操作技能自动组卷系统（Windows 离线版）",
                "",
                "【首次使用】",
                "1. 将整个「组卷工具」文件夹复制到目标 Windows 电脑",
                "2. 把四个题库 .xls 放入「题库」文件夹（见该目录内说明）",
                "   或在 config.yaml 中改为本机路径",
                "3. 双击「组卷.bat」",
                "4. 按提示输入本次要生成的试卷份数",
                "",
                "【目录说明】",
                f"  {EXE_NAME}    主程序",
                "  组卷.bat          双击启动（每次输入份数）",
                "  config.yaml       题量、输出目录、题库路径",
                "  题库/             自行放入四个 Excel 题库",
                "",
                "【config.yaml 可修改项】",
                "  paper.single_count / multiple_count / judge_count / short_count",
                "  output.dir        输出目录，默认桌面",
                "  excel.*           四个题库的 .xls 路径",
                "",
                "【命令行（可选）】",
                "  组卷工具.exe --count 10",
                "  组卷工具.exe --count 10 --seed 42",
                "",
                "【输出】",
                "  默认桌面：待命名试卷_1.docx、待命名试卷_2.docx ...",
                "  同一批次内各卷题目不重复",
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_release() -> Path:
    if shutil.which("pyinstaller") is None:
        _run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    if DIST.exists():
        shutil.rmtree(DIST)
    if RELEASE.exists():
        shutil.rmtree(RELEASE)

    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "exam_generator.spec"])

    release_dir = RELEASE / "组卷工具"
    release_dir.mkdir(parents=True, exist_ok=True)

    built_exe = DIST / EXE_NAME
    if not built_exe.exists() and platform.system() == "Darwin":
        built_app = DIST / APP_NAME
        if built_app.exists():
            built_exe = built_app / "Contents" / "MacOS" / "组卷工具"
    if not built_exe.exists():
        candidates = list(DIST.glob("*"))
        raise FileNotFoundError(f"未找到打包产物，dist 目录内容: {candidates}")

    if platform.system() == "Darwin" and built_exe.suffix != ".exe":
        shutil.copy2(built_exe, release_dir / EXE_NAME.replace(".exe", ""))
        exe_in_release = release_dir / EXE_NAME.replace(".exe", "")
        exe_in_release.chmod(0o755)
    else:
        shutil.copy2(built_exe, release_dir / EXE_NAME)

    shutil.copy2(ROOT / "config.release.yaml", release_dir / "config.yaml")
    _prepare_question_bank_dir(release_dir)

    if platform.system() == "Windows":
        _write_windows_launcher(release_dir)
    else:
        _write_mac_launcher(release_dir)
    _write_readme(release_dir)

    print(f"\n发布目录已生成: {release_dir}")
    if platform.system() != "Windows":
        print("注意：当前为 Mac 打包，Windows 目标机请在 Windows 上运行 scripts\\build_release.bat 生成 .exe。")
    print("发布包不含题库，请将 release/组卷工具 文件夹复制到离线 Windows 电脑使用。")
    return release_dir


def main() -> None:
    try:
        build_release()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"打包失败: {exc}") from exc


if __name__ == "__main__":
    main()
