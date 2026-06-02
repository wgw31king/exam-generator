# Auto-Generation System

710型船柴油机专业操作技能自动组卷系统（阶段一：本地调试）

## 项目结构

```
exam-generator/
├── main.py                 # CLI 入口
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

# 生成试卷
python main.py --count 1 --seed 42
# 输出：output/待命名试卷_1.docx + output/待命名试卷_1_组卷日志.txt

python main.py --count 6          # 批量
python -m pytest tests/ -q          # 测试
```

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
| `{{ paper_title }}` | 答案标题括号内名称（可留空） |
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

## 阶段二（验收通过后）

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name 组卷工具 \
  --add-data "templates/template.docx:templates" \
  --add-data "config.yaml:." \
  main.py
```

在无 Python 的 Windows 10/11 实机测试。
