@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt -r requirements-build.txt
python scripts\build_release.py
echo.
echo 打包完成: release\组卷工具
echo 将该文件夹复制到离线 Windows 电脑，放入题库后双击 组卷.bat
pause
