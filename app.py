#!/usr/bin/env python3
"""图形界面入口：优先桌面 tkinter，不可用时回退本地网页。"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from paths import app_dir


def main() -> None:
    config_path = app_dir() / "config.yaml"
    try:
        import tkinter  # noqa: F401
        from ui import run_app

        run_app(config_path=config_path)
    except ImportError:
        print(
            "未检测到 tkinter（桌面界面不可用），改为启动本地网页界面…\n"
            "若需要桌面窗口：macOS 可用 brew 安装 python-tk，或使用系统自带 Python。\n"
        )
        from web_ui import run_web_app

        run_web_app(config_path=config_path)


if __name__ == "__main__":
    main()
