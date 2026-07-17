#!/usr/bin/env bash
# 在 Mac 上构建 Windows 离线便携包（内置 Python，目标机无需联网/无需安装 Python）
# 说明：此包不是单个 .exe；真正的 .exe 需在 Windows 上运行 scripts/build_release.bat
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_VERSION="${PYTHON_VERSION:-3.12.7}"
PLATFORM="win_amd64"
PY_TAG="312"
RELEASE="$ROOT/release/组卷工具"
CACHE="$ROOT/build/windows-portable-cache"
BUILD="$ROOT/build/windows-portable"
EMBED_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip"
ZIP_OUT="$HOME/Desktop/组卷工具-Windows离线版.zip"

echo "==> 清理旧产物"
rm -rf "$ROOT/release" "$BUILD"
mkdir -p "$CACHE/wheels" "$BUILD" "$RELEASE/python" "$RELEASE/题库" "$RELEASE/templates"

echo "==> 下载 Windows 嵌入式 Python ${PYTHON_VERSION}"
if [[ -f "$CACHE/embed.zip" ]]; then
  echo "    使用缓存: $CACHE/embed.zip"
else
  curl -fsSL -A "Mozilla/5.0" "$EMBED_URL" -o "$CACHE/embed.zip"
fi
unzip -q -o "$CACHE/embed.zip" -d "$RELEASE/python"

PTH_FILE="$(ls "$RELEASE/python/"*._pth)"
cat > "$PTH_FILE" <<EOF
python${PY_TAG}.zip
.
Lib/site-packages
..
import site
EOF

mkdir -p "$RELEASE/python/Lib/site-packages"

echo "==> 下载 Windows 依赖 wheel（在 Mac 上交叉下载）"
"$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt" \
  --target "$RELEASE/python/Lib/site-packages" \
  --platform "$PLATFORM" \
  --python-version "$PY_TAG" \
  --only-binary=:all: \
  --upgrade

echo "==> 复制程序与模板"
APP_FILES=(
  main.py app.py service.py ui.py web_ui.py
  assembler.py renderer.py formatter.py models.py
  doc_styles.py paths.py bank_resolver.py
)
for f in "${APP_FILES[@]}"; do
  cp "$ROOT/$f" "$RELEASE/"
done
cp -R "$ROOT/importers" "$RELEASE/importers"
cp "$ROOT/templates/template.docx" "$RELEASE/templates/template.docx"
cp "$ROOT/config.release.yaml" "$RELEASE/config.yaml"

cat > "$RELEASE/题库/请放入四个题库文件.txt" <<'EOF'
请将四个 Excel 题库放入本文件夹，文件名建议：

  单选.xls
  多选.xls
  判断.xls
  问答.xls

也可在组卷界面中直接粘贴四个 .xls 的完整路径。
EOF

cat > "$RELEASE/组卷.bat" <<'EOF'
@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set "PATH=%~dp0python;%PATH%"
set "PYTHONPATH=%~dp0"
echo 正在启动组卷界面…
"%~dp0python\python.exe" "%~dp0app.py"
echo.
pause
EOF

cat > "$RELEASE/组卷-命令行.bat" <<'EOF'
@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set "PATH=%~dp0python;%PATH%"
set "PYTHONPATH=%~dp0"
"%~dp0python\python.exe" "%~dp0main.py" %*
echo.
pause
EOF

cat > "$RELEASE/使用说明.txt" <<'EOF'
710型船柴油机专业操作技能自动组卷系统（Windows 离线版）

【无需安装 Python，无需联网】

【首次使用】
1. 解压整个「组卷工具」文件夹到任意位置（如 D:\组卷工具）
2. 把四个题库 .xls 放入「题库」文件夹，或记住它们的完整路径
3. 双击「组卷.bat」
4. 浏览器会打开组卷界面（若未自动打开，访问 http://127.0.0.1:8765/）
5. 填写单选/多选/判断/简答四个题库路径、题量、份数后，点「生成试卷」

【每次组卷】
  双击 组卷.bat → 在网页界面操作 → 到输出目录取 .docx

【命令行（可选）】
  双击 组卷-命令行.bat
  或：python\python.exe main.py --count 2 --seed 42

【修改默认题量等】
  可编辑 config.yaml；界面上的设置会优先生效，并记住到 ui_state.yaml

【输出位置】
  默认桌面，可在界面或 config.yaml 的 output.dir 修改

【说明】
  本包为「内置 Python 的文件夹」，不是单个 .exe。
  若必须只要一个 .exe，请在 Windows 电脑上运行 scripts\build_release.bat 打包。
EOF

echo "==> 打包 zip 到桌面"
rm -f "$ZIP_OUT"
(cd "$ROOT/release" && zip -r "$ZIP_OUT" "组卷工具")

echo ""
echo "完成！"
echo "  文件夹: $RELEASE"
echo "  压缩包: $ZIP_OUT"
echo ""
echo "请将 zip 拷到离线 Windows 电脑："
echo "  1. 右键 zip → 全部解压缩"
echo "  2. 双击 组卷.bat 打开界面"
echo "  3. 填写四个题库路径后生成试卷"
