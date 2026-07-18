#!/usr/bin/env bash
# 在 Mac（需联网）交叉打包：飞腾 ARM 银河麒麟离线便携包
# 目标机：aarch64 Linux（Kylin V10），无需 Python、无需联网
# 默认启动网页组卷界面（内置 Python 通常无 tkinter）
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
rm -rf "$ROOT/release/组卷工具-麒麟ARM" "$ROOT/release/KylinArmPack"
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
cp "$ROOT/config.kylin.yaml" "$RELEASE/config.yaml"

cat > "$RELEASE/题库/请放入四个题库文件.txt" <<'EOF'
请将四个 Excel 题库放入本文件夹，建议文件名：

  单选.xls
  多选.xls
  判断.xls
  问答.xls

也可在组卷界面中直接粘贴四个 .xls 的完整路径。
EOF

# 默认：网页界面（麒麟内置 Python 通常无 tkinter）
cat > "$RELEASE/组卷.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export LD_LIBRARY_PATH="$ROOT/python/lib:${LD_LIBRARY_PATH:-}"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
echo "正在启动组卷界面…"
echo "若浏览器未自动打开，请访问 http://127.0.0.1:8765/"
echo "结束请在本终端按 Ctrl+C"
"$ROOT/python/bin/python3" "$ROOT/web_ui.py"
status=$?
echo
read -r -p "按回车键关闭..."
exit $status
EOF
chmod +x "$RELEASE/组卷.sh"

cat > "$RELEASE/组卷-命令行.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export LD_LIBRARY_PATH="$ROOT/python/lib:${LD_LIBRARY_PATH:-}"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
"$ROOT/python/bin/python3" "$ROOT/main.py" --cli "$@"
status=$?
echo
read -r -p "按回车键关闭..."
exit $status
EOF
chmod +x "$RELEASE/组卷-命令行.sh"

cat > "$RELEASE/环境检测.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export LD_LIBRARY_PATH="$ROOT/python/lib:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
echo "==> 系统: $(uname -m) $(uname -s)"
echo "==> 程序目录: $ROOT"
echo "==> 检测内置 Python..."
if "$ROOT/python/bin/python3" -c "import xlrd, yaml, docxtpl, openpyxl; print('依赖 OK')"; then
  echo "==> Python 与依赖正常，可运行 ./组卷.sh"
else
  echo "==> 依赖检测失败，请将本页截图反馈"
  exit 1
fi
echo "==> 检测界面模块..."
"$ROOT/python/bin/python3" -c "import service, web_ui, bank_resolver; print('界面模块 OK')"
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
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if "$ROOT/python/bin/python3" - <<'PY'
from pathlib import Path
from importers.base import ensure_readable_excel

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
chmod +x "$ROOT"/*.sh "$ROOT"/*.desktop 2>/dev/null || true
DESKTOP=""
for d in "$HOME/桌面" "$HOME/Desktop"; do
  [[ -d "$d" ]] && DESKTOP="$d" && break
done
if [[ -z "$DESKTOP" ]]; then
  echo "未找到桌面目录，请直接双击本目录中的「组卷.desktop」"
  exit 1
fi
cat > "$DESKTOP/组卷.desktop" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=组卷
Comment=自动组卷工具（麒麟离线版）
Exec=$ROOT/start.sh
Path=$ROOT
Terminal=true
StartupNotify=true
Categories=Office;
DESKTOP
chmod +x "$DESKTOP/组卷.desktop"
# 标记为已信任（部分麒麟/GNOME 版本有效）
command -v gio >/dev/null 2>&1 && gio set "$DESKTOP/组卷.desktop" metadata::trusted true 2>/dev/null || true
echo "已创建桌面图标: $DESKTOP/组卷.desktop"
echo "若双击无效：右键 → 属性 → 允许启动 / 信任此启动器"
EOF
chmod +x "$RELEASE/安装桌面快捷方式.sh"

# 包内可直接双击的启动器（不依赖绝对路径）
cat > "$RELEASE/组卷.desktop" <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=组卷
Comment=解压后双击即可启动（麒麟离线版）
Exec=bash -c 'DIR="$(dirname "$(readlink -f "%k")")"; cd "$DIR" || exit 1; chmod +x start.sh 组卷.sh *.sh 2>/dev/null; exec ./start.sh'
Terminal=true
StartupNotify=true
Categories=Office;
EOF

cat > "$RELEASE/Zujuan.desktop" <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Zujuan
Comment=Double-click to start exam generator
Exec=bash -c 'DIR="$(dirname "$(readlink -f "%k")")"; cd "$DIR" || exit 1; chmod +x start.sh *.sh 2>/dev/null; exec ./start.sh'
Terminal=true
StartupNotify=true
Categories=Office;
EOF

# 首次双击：赋权 + 装桌面图标 + 启动
cat > "$RELEASE/首次使用-双击我.sh" <<'EOF'
#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
chmod +x "$ROOT"/*.sh "$ROOT"/*.desktop 2>/dev/null || true
command -v gio >/dev/null 2>&1 && {
  gio set "$ROOT/组卷.desktop" metadata::trusted true 2>/dev/null || true
  gio set "$ROOT/Zujuan.desktop" metadata::trusted true 2>/dev/null || true
}
"$ROOT/安装桌面快捷方式.sh" || true
echo
echo "正在启动组卷界面…"
exec "$ROOT/start.sh"
EOF
chmod +x "$RELEASE/首次使用-双击我.sh"
cp "$RELEASE/首次使用-双击我.sh" "$RELEASE/FIRST-RUN.sh"
chmod +x "$RELEASE/FIRST-RUN.sh"

cat > "$RELEASE/使用说明.txt" <<'EOF'
组卷工具 — 银河麒麟飞腾 ARM 离线版

【最简单：解压后双击】
1. 解压整个文件夹到任意位置（如 /home/kylin/组卷工具）
2. 打开该文件夹，双击下面任一图标：
   · 组卷.desktop
   · Zujuan.desktop
   · 首次使用-双击我.sh  /  FIRST-RUN.sh
3. 若提示「不允许启动」：右键 → 允许启动 / 信任
4. 浏览器打开组卷界面后，填写四个题库路径，点「生成试卷」

建议首次运行「首次使用-双击我.sh」，它会自动赋权并在桌面创建「组卷」图标，
之后可直接在桌面双击「组卷」。

【适用系统】
  银河麒麟 V10 / 飞腾等 ARM64（aarch64）
  本包不适用于 x86_64 麒麟

【可选命令行】
  ./start.sh / ./组卷.sh
  ./start-cli.sh / ./组卷-命令行.sh
  ./check-env.sh / ./环境检测.sh

【输出】
  默认：~/桌面/待命名试卷_1.docx …
EOF

# ASCII 别名，避免部分环境中文文件名乱码
cp "$RELEASE/组卷.sh" "$RELEASE/start.sh"
cp "$RELEASE/组卷-命令行.sh" "$RELEASE/start-cli.sh"
cp "$RELEASE/环境检测.sh" "$RELEASE/check-env.sh"
cp "$RELEASE/安装桌面快捷方式.sh" "$RELEASE/install-desktop.sh"
cp "$RELEASE/转换题库格式.sh" "$RELEASE/convert-banks.sh"
cp "$RELEASE/使用说明.txt" "$RELEASE/README.txt"
chmod +x "$RELEASE"/*.sh "$RELEASE"/*.desktop

echo "==> 打包 zip（UTF-8 文件名，保留可执行权限）"
rm -f "$ZIP_OUT"
STAGE="$ROOT/release/KylinArmPack"
rm -rf "$STAGE"
cp -R "$RELEASE" "$STAGE"
"$ROOT/.venv/bin/python" - <<PY
from pathlib import Path
import zipfile
import stat

stage = Path(r"$STAGE")
zip_path = Path(r"$ZIP_OUT")
exec_suffixes = {".sh", ".desktop"}
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        arc = path.relative_to(stage).as_posix()
        info = zipfile.ZipInfo(arc)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.flag_bits |= 0x800  # UTF-8
        mode = 0o755 if (path.suffix in exec_suffixes) else 0o644
        if path.stat().st_mode & stat.S_IXUSR:
            mode = 0o755
        info.external_attr = mode << 16
        zf.writestr(info, path.read_bytes())
print("wrote", zip_path)
PY

echo ""
echo "完成！"
echo "  目录: $RELEASE"
echo "  压缩包: $ZIP_OUT"
echo "  麒麟上：解压 → 双击「组卷.desktop」或「首次使用-双击我.sh」"
