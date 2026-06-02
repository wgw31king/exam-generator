"""应用目录与打包资源路径。"""

from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """可执行文件或项目根目录（config、题库、输出配置相对此目录）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """PyInstaller 内置只读资源目录。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return app_dir()


def user_desktop_dir() -> Path:
    """返回用户桌面目录（兼容麒麟「桌面」与 Desktop）。"""
    home = Path.home()
    for name in ("Desktop", "桌面"):
        candidate = home / name
        if candidate.is_dir():
            return candidate
    return home / "Desktop"


def resolve_path(path: str | Path) -> Path:
    """相对路径基于 app_dir；绝对路径原样返回。"""
    text = str(path).strip().strip('"').strip("'")
    path = Path(text).expanduser()
    # 常见笔误：home/kylin/... 少了开头的 /
    if not path.is_absolute() and text.startswith("home/"):
        path = Path("/" + text).expanduser()
    # ~/Desktop 在银河麒麟等中文系统上常为 ~/桌面
    home = Path.home()
    if path == home / "Desktop" and not path.is_dir():
        alt = home / "桌面"
        if alt.is_dir():
            path = alt
    if path.is_absolute():
        return path
    for base in (app_dir(), bundle_dir()):
        candidate = base / path
        if candidate.exists():
            return candidate
    return app_dir() / path
