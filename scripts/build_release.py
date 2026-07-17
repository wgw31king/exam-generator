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
# PyInstaller 产物用 ASCII 名，发布时再命名为中文 exe，避免 CI 编码问题
BUILD_EXE_STEM = "ZujuanTool"
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
    # 双击 exe 已默认开界面；bat 仅作备用入口
    launcher = release_dir / "组卷.bat"
    launcher.write_text(
        "\n".join(
            [
                "@echo off",
                "chcp 65001 >nul",
                "set PYTHONUTF8=1",
                "set PYTHONIOENCODING=utf-8",
                'cd /d "%~dp0"',
                f'start "" "{EXE_NAME}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    cli = release_dir / "组卷-命令行.bat"
    cli.write_text(
        "\n".join(
            [
                "@echo off",
                "chcp 65001 >nul",
                "set PYTHONUTF8=1",
                "set PYTHONIOENCODING=utf-8",
                'cd /d "%~dp0"',
                f'"{EXE_NAME}" --cli %*',
                "echo.",
                "pause",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_mac_launcher(release_dir: Path) -> None:
    launcher = release_dir / "组卷.command"
    launcher.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                'cd "$(dirname "$0")"',
                f'./{EXE_NAME.replace(".exe", "")} --ui',
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
                "组卷工具（Windows）",
                "",
                "【一键使用】",
                "1. 解压本文件夹到任意位置（如 D:\\组卷工具）",
                "2. 双击「组卷工具.exe」",
                "3. 在界面填写四个题库路径（单选/多选/判断/简答），点「生成试卷」",
                "",
                "无需安装 Python，无需联网，免费使用。",
                "",
                "【题库】",
                "可把四个 .xls 放进「题库」文件夹，也可在界面里粘贴完整路径。",
                "",
                "【输出】",
                "默认生成到桌面：待命名试卷_1.docx …",
                "",
                "【注意】",
                "请保留整个文件夹一起拷贝（exe 旁边的 config.yaml、templates 不要删）。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _make_zip(release_dir: Path) -> Path:
    zip_path = RELEASE / "组卷工具-Windows"
    if zip_path.with_suffix(".zip").exists():
        zip_path.with_suffix(".zip").unlink()
    archive = shutil.make_archive(
        str(zip_path),
        "zip",
        root_dir=str(release_dir.parent),
        base_dir=release_dir.name,
    )
    return Path(archive)


def build_release(*, make_zip: bool = False) -> Path:
    if shutil.which("pyinstaller") is None:
        _run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    if DIST.exists():
        shutil.rmtree(DIST)
    if RELEASE.exists():
        shutil.rmtree(RELEASE)

    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "exam_generator.spec"])

    release_dir = RELEASE / "组卷工具"
    release_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        DIST / f"{BUILD_EXE_STEM}.exe",
        DIST / BUILD_EXE_STEM,
        DIST / EXE_NAME,
        DIST / EXE_NAME.replace(".exe", ""),
    ]
    built_exe = next((p for p in candidates if p.exists()), None)
    if built_exe is None and platform.system() == "Darwin":
        built_app = DIST / APP_NAME
        if built_app.exists():
            built_exe = built_app / "Contents" / "MacOS" / "组卷工具"
            if not built_exe.exists():
                built_exe = built_app / "Contents" / "MacOS" / BUILD_EXE_STEM
    if built_exe is None or not built_exe.exists():
        listing = list(DIST.glob("**/*")) if DIST.exists() else []
        raise FileNotFoundError(f"未找到打包产物，dist 内容: {listing}")

    target_name = EXE_NAME if platform.system() == "Windows" else EXE_NAME.replace(".exe", "")
    shutil.copy2(built_exe, release_dir / target_name)
    if platform.system() != "Windows":
        (release_dir / target_name).chmod(0o755)

    # 确保模板目录在 exe 旁也有一份（便于检查；PyInstaller 已内嵌）
    templates_dir = release_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "templates" / "template.docx", templates_dir / "template.docx")

    shutil.copy2(ROOT / "config.release.yaml", release_dir / "config.yaml")
    _prepare_question_bank_dir(release_dir)

    if platform.system() == "Windows":
        _write_windows_launcher(release_dir)
    else:
        _write_mac_launcher(release_dir)
    _write_readme(release_dir)

    print(f"\n发布目录已生成: {release_dir}")
    if platform.system() == "Windows":
        print("用户用法：解压后双击 组卷工具.exe")
    else:
        print("注意：当前不是 Windows，产物不是 .exe。请用 GitHub Actions 或 Windows 机打包。")

    if make_zip:
        zip_file = _make_zip(release_dir)
        print(f"压缩包已生成: {zip_file}")

    return release_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="打包组卷工具发布目录")
    parser.add_argument(
        "--zip",
        action="store_true",
        help="同时生成 release/组卷工具-Windows.zip",
    )
    args = parser.parse_args()
    try:
        build_release(make_zip=args.zip)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"打包失败: {exc}") from exc


if __name__ == "__main__":
    main()
