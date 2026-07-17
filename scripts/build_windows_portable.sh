#!/usr/bin/env bash
# 在 Mac 上构建 Windows 离线便携包（内置 Python + 可双击的 .exe 启动器）
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
LAUNCHER_DIR="$ROOT/scripts/windows_launcher"

echo "==> 清理旧产物"
rm -rf "$ROOT/release" "$BUILD"
mkdir -p "$CACHE/wheels" "$BUILD" "$RELEASE/python" "$RELEASE/题库" "$RELEASE/templates"

echo "==> 交叉编译 Windows 启动器 组卷工具.exe"
if ! command -v go >/dev/null 2>&1; then
  echo "未找到 go，请先: brew install go"
  exit 1
fi
(
  cd "$LAUNCHER_DIR"
  GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -ldflags="-s -w" -o "$RELEASE/组卷工具.exe" .
)
cp "$RELEASE/组卷工具.exe" "$RELEASE/ZujuanTool.exe"
ls -lh "$RELEASE/组卷工具.exe" "$RELEASE/ZujuanTool.exe"

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
rm -rf "$RELEASE/importers"
mkdir -p "$RELEASE/importers"
cp "$ROOT"/importers/*.py "$RELEASE/importers/"
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
cd /d "%~dp0"
start "" "%~dp0组卷工具.exe"
EOF

cat > "$RELEASE/使用说明.txt" <<'EOF'
组卷工具（Windows 离线版）

【一键使用】
1. 解压整个文件夹到任意位置（如 D:\组卷工具）
2. 双击「组卷工具.exe」或「ZujuanTool.exe」
3. 浏览器打开组卷界面（若未自动打开，访问 http://127.0.0.1:8765/）
4. 填写四个题库路径后点「生成试卷」

无需安装 Python，无需联网，免费使用。

【注意】
请保留整个文件夹一起使用（不要只拷贝单个 exe）。
exe 旁边必须有 python、app.py、templates、config.yaml 等文件。

【输出】
默认生成到桌面。
EOF

echo "==> 打包 zip 到桌面（扁平结构，解压即见 exe）"
rm -f "$ZIP_OUT"
STAGE="$ROOT/release/ZujuanTool"
rm -rf "$STAGE"
cp -R "$RELEASE" "$STAGE"
(cd "$STAGE" && zip -r "$ZIP_OUT" . -x "*.pyc" -x "*__pycache__*")

echo ""
echo "完成！"
echo "  文件夹: $RELEASE"
echo "  压缩包: $ZIP_OUT"
echo ""
echo "拷到 Windows 后："
echo "  1. 解压（解压后应直接看到 组卷工具.exe）"
echo "  2. 双击 组卷工具.exe"
