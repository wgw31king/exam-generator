@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

echo ========================================
echo   组卷工具 - 打包 Windows .exe
echo   （免费，目标机可直接双击使用）
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 python。请先安装 Python 3.10+ 并勾选 Add to PATH。
  echo 下载: https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo 正在创建虚拟环境…
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo 正在安装依赖…
python -m pip install -U pip
python -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 (
  echo [错误] 依赖安装失败
  pause
  exit /b 1
)

echo 正在打包…
python scripts\build_release.py
if errorlevel 1 (
  echo [错误] 打包失败
  pause
  exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo.
echo 发布目录: release\组卷工具
echo 主程序:   release\组卷工具\组卷工具.exe
echo.
echo 发给别人时：把整个「组卷工具」文件夹拷过去
echo （不要只拷单个 exe，旁边还要有 config.yaml、templates、题库）
echo 对方双击 组卷工具.exe 即可打开界面，免费使用，无需安装 Python。
echo ========================================
pause
