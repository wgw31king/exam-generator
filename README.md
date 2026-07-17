# Auto-Generation System

710型船柴油机专业操作技能自动组卷系统（阶段一：本地调试）

## 项目结构

```
exam-generator/
├── main.py                 # CLI 入口（可用 --ui 开图形界面）
├── app.py                  # 图形界面入口
├── ui.py                   # tkinter 一键组卷界面
├── service.py              # CLI / UI 共用组卷 API
├── config.yaml             # 题量、路径、模板
├── models.py               # 统一数据模型
├── assembler.py            # 随机组卷
├── renderer.py             # docxtpl 填充模板
├── formatter.py            # 题目/答案排版
├── importers/              # Excel 导入
├── templates/
│   ├── template_raw.docx   # 样板卷转换（勿改占位符）
│   └── template.docx       # 含 {{p ...}} 占位符的母版
├── sample_data/            # 4 个 xls 样例
├── output/                 # 生成结果
├── scripts/
│   ├── prepare_template.py # 从样板生成 template.docx
│   └── build_qa_sample.py  # 从样板提取标准问答.xls
└── tests/
```

## 快速开始

```bash
cd /Users/wahhh/exam-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 首次：由样板 doc 生成 template.docx（已完成可跳过）
textutil -convert docx -output templates/template_raw.docx \
  "/path/to/2026年半年710型船主推进柴油机专业操作高级A卷.doc"
python scripts/prepare_template.py
python scripts/build_qa_sample.py   # 若问答.xls 非标准格式

# 图形界面（推荐）：选题库 / 改题量 → 点「生成试卷」
python app.py
# 或：python main.py --ui
# 有 tkinter 时开桌面窗口；否则自动打开 http://127.0.0.1:8765/ 网页界面

# CLI 生成试卷
python main.py --count 1 --seed 42
# 输出：桌面或 config 中 output.dir 下的 docx

python main.py --count 6          # 批量
python -m pytest tests/ -q          # 测试
```

### 图形界面说明

1. 启动 `python app.py`（优先桌面窗口；无 tkinter 时自动开本地网页）
2. 分别填写（或浏览）单选 / 多选 / 判断 / 简答 四个 `.xls` 路径；若配置了 `banks`，可用「快捷填充」一键回填
3. 按需修改题量、份数、随机种子、标题、输出目录
4. 点击「生成试卷」；桌面版成功后可「打开输出文件夹」
5. 设置会写入程序目录下的 `ui_state.yaml`（下次自动恢复）

## template.docx 制作步骤

1. 用 Word / macOS `textutil` 将样板 `.doc` 另存为 `templates/template_raw.docx`
2. 运行 `python scripts/prepare_template.py`
3. 脚本**仅**在题目区与答案区插入 `{{p single_questions }}` 等占位符
4. 装订线、密封纹、信息表、得分表、页码等固定元素**不改动**

### 占位符设计

| 占位符 | 说明 |
|--------|------|
| `{{p single_questions }}` | 单选 30 题正文 |
| `{{p multiple_questions }}` | 多选 10 题正文 |
| `{{p judge_questions }}` | 判断 30 题正文 |
| `{{p short_questions }}` | 简答 5 题 + 空白行 |
| `{{ paper_title }}` | 卷首直接显示标题；答案区为「《标题》答案」；留空时两处均用「待命名试卷」 |
| `{{p single_answer_lines }}` | 单选答案（每行 5 题） |
| `{{p multiple_answer_lines }}` | 多选答案 |
| `{{p judge_answer_lines }}` | 判断答案 |
| `{{p short_answer_lines }}` | 简答完整参考答案 |

## 组卷规则

- 单选 30 / 多选 10 / 判断 30 / 简答 5，各库 `random.sample` 无放回
- 题量不足报错中止
- 正文无答案；答案仅在文档末尾
- 文件名：`待命名试卷_{n}.docx`（不自动 A/B/C 卷）

## Excel 输入

- 格式 `.xls`，`xlrd` 读取 Sheet0
- 跳过第 1 行（类别标题）、第 2 行（列名），从第 3 行读数据

**注意：** 微信题库中的 `问答.xls` 可能为 NT195 加密格式，非标准 BIFF。请用 Excel/WPS 打开后**另存为标准 .xls**，或运行 `scripts/build_qa_sample.py` 从样板卷提取示例数据。

## 阶段一验收清单

生成 1 份卷后与样板卷并排对照：

- [ ] 左侧装订线（装/订/线、○、六点）
- [ ] 保密密封花纹块
- [ ] 单位/姓名/考号表、座位号表、单位/姓名/部职别表
- [ ] 题型得分表、四大题固定说明
- [ ] 单选 30、多选 10、判断 30、简答 5
- [ ] 正文无答案；末尾答案区格式正确
- [ ] 文件名无 A卷/B卷

## Windows 打包分发

本机是 Mac 时，**不能**直接打出 Windows `.exe`（PyInstaller 需在 Windows 上运行）。

### 方式 A（推荐，可在 Mac 上打）：Windows 离线便携包

```bash
bash scripts/build_windows_portable.sh
```

产物：桌面上的 `组卷工具-Windows离线版.zip`（内置 Python，目标机无需安装）。
解压后双击 `组卷.bat` 即可打开组卷界面。

### 方式 B：真正的单个 `.exe`（必须在 Windows 电脑上）

```bat
scripts\build_release.bat
```

产物：`release\组卷工具\组卷工具.exe`，双击 `组卷.bat` 启动界面。
