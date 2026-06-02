#!/usr/bin/env bash
# 在麒麟 / Linux 上运行，生成离线便携包（目标机同样为 Linux，无需预装 Python 环境）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE="$ROOT/release/组卷工具-Linux"
ZIP_OUT="$HOME/组卷工具-麒麟离线版.zip"

echo "==> 清理旧产物"
rm -rf "$ROOT/release/组卷工具-Linux"
mkdir -p "$RELEASE/题库" "$RELEASE/templates"

echo "==> 创建内置 Python 虚拟环境"
python3 -m venv "$RELEASE/venv"
"$RELEASE/venv/bin/pip" install -q --upgrade pip
"$RELEASE/venv/bin/pip" install -q -r "$ROOT/requirements.txt"

echo "==> 复制程序与模板"
APP_FILES=(main.py assembler.py renderer.py formatter.py models.py doc_styles.py paths.py)
for f in "${APP_FILES[@]}"; do
  cp "$ROOT/$f" "$RELEASE/"
done
cp -R "$ROOT/importers" "$RELEASE/importers"
cp "$ROOT/templates/template.docx" "$RELEASE/templates/template.docx"
cp "$ROOT/config.release.yaml" "$RELEASE/config.yaml"

cat > "$RELEASE/题库/请放入四个题库文件.txt" <<'EOF'
请将四个 Excel 题库放入本文件夹，或修改 config.yaml：

  单选.xls  多选.xls  判断.xls  问答.xls

Linux 路径示例：
  single: "/home/用户/题库/单选.xls"
  single: "题库/单选.xls"
EOF

cat > "$RELEASE/组卷.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
"./venv/bin/python" "./main.py"
echo
read -r -p "按回车键关闭..."
EOF
chmod +x "$RELEASE/组卷.sh"

cat > "$RELEASE/使用说明.txt" <<'EOF'
710型船柴油机自动组卷 — 麒麟/Linux 离线版

【与 Windows 版的区别】
  Windows 压缩包（含 python.exe、组卷.bat）不能在麒麟上运行。
  请使用本 Linux/麒麟 专用包。

【首次使用】
1. 解压整个文件夹
2. 编辑 config.yaml（路径用引号，Linux 用正斜杠 /）
3. 双击或在终端运行：./组卷.sh
   （若双击无效，右键 → 属性 → 允许执行，或在终端 chmod +x 组卷.sh）

【config.yaml 路径示例】
  single: "/opt/题库/单选.xls"
  single: "题库/单选.xls"

【输出】
  默认桌面：~/Desktop/待命名试卷_1.docx
EOF

echo "==> 打包 zip"
rm -f "$ZIP_OUT"
(cd "$ROOT/release" && zip -r "$ZIP_OUT" "组卷工具-Linux")

echo ""
echo "完成！"
echo "  目录: $RELEASE"
echo "  压缩包: $ZIP_OUT"
echo ""
echo "请将该 zip 复制到离线麒麟电脑解压使用。"
echo "注意：须在相同 CPU 架构的麒麟上打包（x86 打 x86，ARM 打 ARM）。"
