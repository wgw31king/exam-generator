#!/usr/bin/env bash
# 在 Mac（需联网）交叉打包：飞腾 ARM 银河麒麟离线便携包
# 目标机：aarch64 Linux（Kylin V10），无需 Python、无需联网
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE="$ROOT/release/组卷工具-麒麟ARM"
CACHE="$ROOT/build/kylin-arm-cache"
PY_RELEASE="${PY_RELEASE:-20260127}"
PY_VER="${PY_VER:-3.12.12}"
PLATFORM="manylinux2014_aarch64"
PY_TAG="312"
PYTHON_TAR="cpython-${PY_VER}+${PY_RELEASE}-aarch64-unknown-linux-gnu-install_only_stripped.tar.gz"
PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_RELEASE}/${PYTHON_TAR}"
ZIP_OUT="$HOME/Desktop/组卷工具-麒麟ARM离线版.zip"

echo "==> 清理旧产物"
rm -rf "$ROOT/release/组卷工具-麒麟ARM"
mkdir -p "$CACHE" "$RELEASE/python" "$RELEASE/题库" "$RELEASE/templates"

echo "==> 下载 Linux ARM64 Python ${PY_VER}"
if [[ ! -f "$CACHE/$PYTHON_TAR" ]]; then
  curl -fsSL -L "$PYTHON_URL" -o "$CACHE/$PYTHON_TAR"
else
  echo "    使用缓存: $CACHE/$PYTHON_TAR"
fi
tar -xzf "$CACHE/$PYTHON_TAR" -C "$RELEASE/python" --strip-components=1

echo "==> 安装 ARM64 Linux 依赖"
mkdir -p "$RELEASE/python/lib/python3.12/site-packages"
"$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt" \
  --target "$RELEASE/python/lib/python3.12/site-packages" \
  --platform "$PLATFORM" \
  --python-version "$PY_TAG" \
  --only-binary=:all: \
  --upgrade

echo "==> 复制程序与模板"
APP_FILES=(main.py assembler.py renderer.py formatter.py models.py doc_styles.py paths.py)
for f in "${APP_FILES[@]}"; do
  cp "$ROOT/$f" "$RELEASE/"
done
cp -R "$ROOT/importers" "$RELEASE/importers"
cp "$ROOT/templates/template.docx" "$RELEASE/templates/template.docx"
cp "$ROOT/config.kylin.yaml" "$RELEASE/config.yaml"

cat > "$RELEASE/题库/请放入四个题库文件.txt" <<'EOF'
请将四个 Excel 题库放入本文件夹：

  单选.xls  多选.xls  判断.xls  问答.xls

文件名必须与上面完全一致（注意没有空格）。
或在 config.yaml 中写绝对路径，例如：
  single: "/home/kylin/组卷工具-麒麟ARM/题库/单选.xls"
EOF

cat > "$RELEASE/组卷.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export LD_LIBRARY_PATH="$ROOT/python/lib:${LD_LIBRARY_PATH:-}"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
"$ROOT/python/bin/python3" "$ROOT/main.py"
status=$?
echo
read -r -p "按回车键关闭..."
exit $status
EOF
chmod +x "$RELEASE/组卷.sh"

cat > "$RELEASE/环境检测.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export LD_LIBRARY_PATH="$ROOT/python/lib:${LD_LIBRARY_PATH:-}"
echo "==> 系统: $(uname -m) $(uname -s)"
echo "==> 程序目录: $ROOT"
echo "==> 检测内置 Python..."
if "$ROOT/python/bin/python3" -c "import xlrd, yaml, docxtpl, openpyxl; print('依赖 OK')"; then
  echo "==> Python 与依赖正常，可运行 ./组卷.sh"
else
  echo "==> 依赖检测失败，请将本页截图反馈"
  exit 1
fi
echo "==> 检测题库格式（必须是标准 Excel 97-2003 .xls）..."
"$ROOT/python/bin/python3" - <<'PY'
from pathlib import Path
from importers.base import inspect_bank_file

root = Path(".")
for name in ("单选.xls", "多选.xls", "判断.xls", "问答.xls"):
    print(" ", inspect_bank_file(root / "题库" / name))
PY
echo "==> 桌面目录:"
for d in "$HOME/桌面" "$HOME/Desktop"; do
  [[ -d "$d" ]] && echo "  $d"
done
EOF
chmod +x "$RELEASE/环境检测.sh"

cat > "$RELEASE/转换题库格式.sh" <<'EOF'
#!/bin/bash
# 离线批量转换：把 题库/ 下四个 xls 转为标准 Excel 97-2003 格式
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/题库"
BAK="$ROOT/题库_原始备份"
OUT="$ROOT/题库"
mkdir -p "$BAK"
echo "==> 备份原文件到 题库_原始备份/"
for f in 单选.xls 多选.xls 判断.xls 问答.xls; do
  [[ -f "$SRC/$f" ]] || { echo "缺少 题库/$f"; exit 1; }
  cp -f "$SRC/$f" "$BAK/$f"
  echo "  已备份 $f"
done
CONVERTER=""
command -v libreoffice &>/dev/null && CONVERTER="libreoffice"
command -v soffice &>/dev/null && CONVERTER="soffice"
if [[ -n "$CONVERTER" ]]; then
  echo "==> 使用 $CONVERTER 批量转换..."
  TMP="$ROOT/.convert_tmp"
  rm -rf "$TMP" && mkdir -p "$TMP"
  for f in 单选.xls 多选.xls 判断.xls 问答.xls; do
    "$CONVERTER" --headless --convert-to 'xls:MS Excel 97' --outdir "$TMP" "$BAK/$f" 2>/dev/null || true
  done
  ok=0
  for f in 单选.xls 多选.xls 判断.xls 问答.xls; do
    base="${f%.xls}"
    if [[ -f "$TMP/${base}.xls" ]]; then
      cp -f "$TMP/${base}.xls" "$OUT/$f"
      echo "  已转换 $f"
      ok=$((ok + 1))
    fi
  done
  rm -rf "$TMP"
  [[ "$ok" -eq 4 ]] && { echo "转换完成！运行 ./组卷.sh"; exit 0; }
fi
echo "==> 尝试使用内置 Python 转换..."
export LD_LIBRARY_PATH="$ROOT/python/lib:${LD_LIBRARY_PATH:-}"
if "$ROOT/python/bin/python3" - <<'PY'
from pathlib import Path
from importers.base import ensure_readable_excel, is_standard_xls

root = Path(".")
for name in ("单选.xls", "多选.xls", "判断.xls", "问答.xls"):
    src = root / "题库" / name
    ensure_readable_excel(src)
    print(f"  已处理 {name}")
PY
then
  echo "转换完成！运行 ./组卷.sh"
  exit 0
fi
echo "自动转换失败。请安装 LibreOffice 后重试，或运行 ./环境检测.sh 查看详情。"
EOF
chmod +x "$RELEASE/转换题库格式.sh"

cat > "$RELEASE/安装桌面快捷方式.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
DESKTOP=""
for d in "$HOME/桌面" "$HOME/Desktop"; do
  [[ -d "$d" ]] && DESKTOP="$d" && break
done
if [[ -z "$DESKTOP" ]]; then
  echo "未找到桌面目录，请手动运行: $ROOT/组卷.sh"
  exit 1
fi
chmod +x "$ROOT/组卷.sh"
cat > "$DESKTOP/组卷工具.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=710型船柴油机组卷
Comment=自动组卷工具
Exec=$ROOT/组卷.sh
Path=$ROOT
Terminal=true
Categories=Office;
DESKTOP
chmod +x "$DESKTOP/组卷工具.desktop"
echo "已创建: $DESKTOP/组卷工具.desktop"
echo "若双击无效，请在文件管理器中右键该快捷方式 → 允许启动 / 信任"
EOF
chmod +x "$RELEASE/安装桌面快捷方式.sh"

cat > "$RELEASE/使用说明.txt" <<'EOF'
710型船柴油机自动组卷 — 银河麒麟飞腾ARM离线版

【说明】
  本程序是 Python 应用，不是 Java，没有 jar 包。
  本压缩包已内置 Linux ARM64 Python，麒麟上解压即用，无需联网。

【适用系统】
  银河麒麟 V10 / 飞腾 D2000 等 ARM64（aarch64）电脑

【首次使用 — 四步】
1. 解压到任意目录，例如：
   /home/kylin/组卷工具-麒麟ARM

2. 打开终端，进入目录并赋权：
   cd /home/kylin/组卷工具-麒麟ARM
   chmod +x 组卷.sh 环境检测.sh 安装桌面快捷方式.sh

3. 将四个题库放入「题库」文件夹：
   单选.xls  多选.xls  判断.xls  问答.xls
   （单选表头须为：编号, 题目, 正确答案(A), 备选答案1(B), 备选答案2(C), 备选答案3(D)）

4. 将四个题库放入「题库」文件夹（支持麒麟 WPS 原生格式，程序会自动转换）：
   单选.xls  多选.xls  判断.xls  问答.xls

5. 检测并组卷：
   ./环境检测.sh
   ./组卷.sh

【config.yaml 说明】
  默认从「题库/」读取，输出到 ~/桌面
  如需改路径，用文本编辑器打开 config.yaml，路径用 / 且加引号：
excel:
  single: "题库/单选.xls"
  multiple: "题库/多选.xls"
  judge: "题库/判断.xls"
  qa: "题库/问答.xls"

output:
  dir: "~/桌面"

【桌面快捷方式（可选）】
  ./安装桌面快捷方式.sh
  然后在桌面双击「710型船柴油机组卷」

【常见问题】
  Q: 提示找不到题库？
  A: 确认四个 xls 在 题库/ 下，文件名无多余空格。

  Q: Expected BOF record / WPS 格式？
  A: 新版已自动兼容麒麟 WPS 题库。直接 ./组卷.sh 即可。
     首次会自动转换（需 LibreOffice，麒麟一般已预装）。
     也可先运行 ./转换题库格式.sh

  Q: python 无法运行 / 找不到 libpython？
  A: 必须用 ./组卷.sh 启动，不要直接双击 main.py。

  Q: 输出文件在哪？
  A: 默认在 /home/kylin/桌面/待命名试卷_1.docx
EOF

echo "==> 打包 zip"
rm -f "$ZIP_OUT"
(cd "$ROOT/release" && zip -r "$ZIP_OUT" "组卷工具-麒麟ARM")

echo ""
echo "完成！"
echo "  目录: $RELEASE"
echo "  压缩包: $ZIP_OUT"
echo "  拷到飞腾麒麟离线电脑解压后运行 ./组卷.sh"
