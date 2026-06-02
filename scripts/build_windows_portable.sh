#!/usr/bin/env bash
# 在 Mac 上构建 Windows 离线便携包（内置 Python，目标机无需联网/无需安装 Python）
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
  main.py assembler.py renderer.py formatter.py models.py
  doc_styles.py paths.py
)
for f in "${APP_FILES[@]}"; do
  cp "$ROOT/$f" "$RELEASE/"
done
cp -R "$ROOT/importers" "$RELEASE/importers"
cp "$ROOT/templates/template.docx" "$RELEASE/templates/template.docx"
cp "$ROOT/config.release.yaml" "$RELEASE/config.yaml"

cat > "$RELEASE/题库/请放入四个题库文件.txt" <<'EOF'
请将四个 Excel 题库放入本文件夹，或修改上级 config.yaml 中的路径：

  单选.xls
  多选.xls
  判断.xls
  问答.xls

Windows 路径示例：
  D:/我的题库/单选.xls
  题库/单选.xls
EOF

cat > "$RELEASE/组卷.bat" <<'EOF'
@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set "PATH=%~dp0python;%PATH%"
set "PYTHONPATH=%~dp0"
"%~dp0python\python.exe" "%~dp0main.py"
echo.
pause
EOF

cat > "$RELEASE/使用说明.txt" <<'EOF'
710型船柴油机专业操作技能自动组卷系统（Windows 离线版）

【无需安装 Python，无需联网】

【首次使用】
1. 解压整个「组卷工具」文件夹到任意位置（如 D:\组卷工具）
2. 用记事本打开 config.yaml，修改 excel 下的四个题库路径
   例如：
     single: "D:/题库/单选.xls"
     或放入 题库 文件夹后保持：
     single: "题库/单选.xls"
3. 双击 组卷.bat
4. 输入本次要生成的试卷份数

【每次组卷】
  双击 组卷.bat → 输入份数 → 桌面获取 待命名试卷_1.docx ...

【修改题量】
  编辑 config.yaml 中 paper 下的 single_count / multiple_count 等

【输出位置】
  默认桌面，可在 config.yaml 的 output.dir 修改
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
echo "  2. 编辑 config.yaml 里的题库路径"
echo "  3. 双击 组卷.bat"
