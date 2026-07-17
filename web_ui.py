"""本地 Web 界面（标准库）：无 tkinter 时作为备用一键组卷入口。"""

from __future__ import annotations

import html
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from paths import app_dir, resolve_path, user_desktop_dir
from service import (
    describe_bank_files,
    friendly_error,
    generate_batch,
    load_config,
    load_ui_state,
    resolve_excel_paths,
    save_ui_state,
)

HOST = "127.0.0.1"
PORT = 8765

EXCEL_KEYS = (
    ("excel_single", "single", "单选"),
    ("excel_multiple", "multiple", "多选"),
    ("excel_judge", "judge", "判断"),
    ("excel_qa", "qa", "简答"),
)


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _default_excel_paths(config: dict) -> dict[str, str]:
    excel = config.get("excel") or {}
    return {
        "excel_single": str(excel.get("single", "") or ""),
        "excel_multiple": str(excel.get("multiple", "") or ""),
        "excel_judge": str(excel.get("judge", "") or ""),
        "excel_qa": str(excel.get("qa", "") or ""),
    }


def _merge_defaults(config: dict, state: dict) -> dict:
    """ui_state 优先，其次 config.excel，再给其它字段默认值。"""
    paper = config.get("paper", {})
    output = config.get("output", {})
    template = config.get("template", {})
    defaults = {
        **_default_excel_paths(config),
        "bank": "",
        "single_count": paper.get("single_count", 30),
        "multiple_count": paper.get("multiple_count", 10),
        "judge_count": paper.get("judge_count", 30),
        "short_count": paper.get("short_count", 5),
        "paper_count": 1,
        "seed": "",
        "title": paper.get("title", "") or "",
        "output_dir": output.get("dir", str(user_desktop_dir())),
        "filename_pattern": output.get(
            "filename_pattern", "待命名试卷_{n}.docx"
        ),
        "template_path": template.get("path", "templates/template.docx"),
    }
    merged = {**defaults}
    for key, value in state.items():
        if value is not None and value != "":
            merged[key] = value
    # 空字符串的路径仍允许用 state 覆盖（用户清空）
    for key, _, _ in EXCEL_KEYS:
        if key in state:
            merged[key] = state[key]
    return merged


def _require_excel_overrides(state: dict) -> dict[str, str]:
    missing: list[str] = []
    resolved: list[tuple[str, str, Path]] = []
    for state_key, excel_key, label in EXCEL_KEYS:
        raw = str(state.get(state_key, "") or "").strip()
        if not raw:
            missing.append(label)
            continue
        resolved.append((excel_key, label, resolve_path(raw)))
    if missing:
        raise ValueError("请填写完整四个题库路径：" + "、".join(missing))
    overrides: dict[str, str] = {}
    for excel_key, label, path in resolved:
        if not path.is_file():
            raise FileNotFoundError(f"{label}题库文件不存在: {path}")
        overrides[excel_key] = str(path)
    return overrides


def _html_page(
    config: dict,
    state: dict,
    message: str = "",
    outputs: list[str] | None = None,
    ok: bool | None = None,
) -> str:
    s = _merge_defaults(config, state)
    banks = list((config.get("banks") or {}).keys())

    bank_options = ['<option value="">— 选择后点「填入路径」—</option>']
    selected_bank = str(s.get("bank", "") or "")
    for name in banks:
        sel = " selected" if selected_bank == name else ""
        bank_options.append(f'<option value="{_esc(name)}"{sel}>{_esc(name)}</option>')

    status_html = ""
    if message:
        kind = "ok" if ok else ("err" if ok is False else "info")
        status_html = f'<div class="banner {kind}">{html.escape(message)}</div>'
    if outputs:
        items = "".join(f"<li><code>{_esc(p)}</code></li>" for p in outputs)
        status_html += f'<div class="banner ok"><strong>已生成文件</strong><ul>{items}</ul></div>'

    bank_fill = ""
    if banks:
        bank_fill = f"""
      <div class="quick-fill">
        <label>快捷填充（可选）</label>
        <div class="inline">
          <select name="bank" form="fill-form">{"".join(bank_options)}</select>
          <button type="submit" form="fill-form" class="btn ghost">填入路径</button>
        </div>
        <p class="hint">从 config 的 banks 自动识别单选/多选/判断/问答文件</p>
      </div>
"""
    else:
        bank_fill = ""

    path_cards = []
    placeholders = {
        "excel_single": "例如：题库/单选.xls 或绝对路径",
        "excel_multiple": "例如：题库/多选.xls",
        "excel_judge": "例如：题库/判断.xls",
        "excel_qa": "例如：题库/问答.xls",
    }
    for state_key, _, label in EXCEL_KEYS:
        path_cards.append(
            f"""
        <div class="path-card">
          <label>{label}题库 <span class="tag">.xls</span></label>
          <input name="{state_key}" value="{_esc(s.get(state_key, ''))}"
            placeholder="{placeholders[state_key]}"/>
        </div>"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>组卷</title>
<style>
:root {{
  --bg0: #e8eef2;
  --bg1: #f3f6f4;
  --ink: #1c2b33;
  --muted: #5a6b75;
  --card: rgba(255,255,255,0.92);
  --line: #d0d8dc;
  --accent: #1f6f5b;
  --accent-hover: #185a4a;
  --accent-soft: #e3f2ed;
  --danger: #9b2c2c;
  --danger-bg: #fdecec;
  --ok: #1f6f5b;
  --ok-bg: #e3f2ed;
  --radius: 14px;
  --shadow: 0 12px 40px rgba(28, 43, 51, 0.08);
  --font: "Avenir Next", "Segoe UI", "PingFang SC", "Hiragino Sans GB",
    "Microsoft YaHei", sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; min-height: 100vh; color: var(--ink); font-family: var(--font);
  background:
    radial-gradient(1200px 600px at 10% -10%, #cfe3dc 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #d7e4ef 0%, transparent 50%),
    linear-gradient(165deg, var(--bg0), var(--bg1));
}}
.wrap {{
  max-width: 820px; margin: 0 auto; padding: 28px 18px 48px;
}}
.hero {{
  margin-bottom: 18px;
}}
.brand {{
  font-size: clamp(2rem, 5vw, 2.6rem); font-weight: 750; letter-spacing: 0.04em;
  margin: 0; line-height: 1.1;
}}
.sub {{
  margin: 8px 0 0; color: var(--muted); font-size: 0.98rem;
}}
.card {{
  background: var(--card); border: 1px solid rgba(255,255,255,0.7);
  border-radius: var(--radius); box-shadow: var(--shadow);
  padding: 20px 20px 8px; backdrop-filter: blur(8px);
}}
section {{
  margin-bottom: 22px; padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
}}
section:last-of-type {{ border-bottom: none; }}
.section-title {{
  margin: 0 0 12px; font-size: 0.82rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
}}
label {{
  display: block; font-weight: 650; font-size: 0.92rem; margin-bottom: 6px;
}}
.hint {{ color: var(--muted); font-size: 0.85rem; margin: 6px 0 0; }}
.tag {{
  display: inline-block; font-size: 0.72rem; font-weight: 600;
  color: var(--accent); background: var(--accent-soft);
  padding: 2px 7px; border-radius: 999px; margin-left: 4px;
}}
input, select {{
  width: 100%; padding: 10px 12px; border: 1px solid var(--line);
  border-radius: 10px; background: #fff; color: var(--ink);
  font: inherit; outline: none; transition: border-color .15s, box-shadow .15s;
}}
input:focus, select:focus {{
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(31, 111, 91, 0.15);
}}
.path-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}}
.path-card {{
  background: #f7faf9; border: 1px solid var(--line);
  border-radius: 12px; padding: 12px;
}}
.count-grid, .gen-grid {{
  display: grid; gap: 12px;
}}
.count-grid {{ grid-template-columns: repeat(4, 1fr); }}
.gen-grid {{ grid-template-columns: 1fr 1fr; }}
.field {{ min-width: 0; }}
.inline {{ display: flex; gap: 8px; align-items: center; }}
.inline select {{ flex: 1; }}
.quick-fill {{
  margin-bottom: 14px; padding: 12px; border-radius: 12px;
  background: var(--accent-soft); border: 1px solid #c5e0d6;
}}
.actions {{
  display: flex; gap: 10px; flex-wrap: wrap; margin: 8px 0 18px;
}}
.btn {{
  appearance: none; border: none; cursor: pointer; font: inherit;
  border-radius: 12px; padding: 12px 20px; font-weight: 700;
  transition: background .15s, transform .1s;
}}
.btn:active {{ transform: translateY(1px); }}
.btn.primary {{
  background: var(--accent); color: #fff; min-width: 160px;
  box-shadow: 0 8px 20px rgba(31, 111, 91, 0.28);
}}
.btn.primary:hover {{ background: var(--accent-hover); }}
.btn.ghost {{
  background: #fff; color: var(--accent); border: 1px solid #b7d4c9;
  font-weight: 650; padding: 10px 14px;
}}
.btn.ghost:hover {{ background: #f3faf7; }}
details.advanced {{
  margin: 4px 0 16px; border: 1px dashed var(--line);
  border-radius: 12px; padding: 10px 12px; background: #fafcfa;
}}
details.advanced summary {{
  cursor: pointer; font-weight: 650; color: var(--muted);
}}
.banner {{
  margin: 0 0 14px; padding: 12px 14px; border-radius: 12px;
  white-space: pre-wrap; line-height: 1.45;
}}
.banner ul {{ margin: 8px 0 0; padding-left: 1.2em; }}
.banner code {{
  font-size: 0.88rem; word-break: break-all;
}}
.banner.ok {{ background: var(--ok-bg); color: #14493d; border: 1px solid #b7d4c9; }}
.banner.err {{ background: var(--danger-bg); color: var(--danger); border: 1px solid #f0c2c2; }}
.banner.info {{ background: #eef3f6; color: #334; border: 1px solid #d0dce4; }}
@media (max-width: 640px) {{
  .path-grid, .count-grid, .gen-grid {{ grid-template-columns: 1fr 1fr; }}
  .count-grid {{ grid-template-columns: 1fr 1fr; }}
  .inline {{ flex-direction: column; align-items: stretch; }}
}}
@media (max-width: 420px) {{
  .path-grid, .gen-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <h1 class="brand">组卷</h1>
      <p class="sub">填写四类题库路径，设定题量后一键生成试卷</p>
    </header>

    {status_html}

    <form id="fill-form" method="post" action="/fill"></form>

    <form class="card" method="post" action="/generate">
      <input type="hidden" name="bank" value="{_esc(selected_bank)}"/>
      <section>
        <h2 class="section-title">题库路径</h2>
        {bank_fill}
        <div class="path-grid">
          {"".join(path_cards)}
        </div>
      </section>

      <section>
        <h2 class="section-title">出题数量</h2>
        <div class="count-grid">
          <div class="field"><label>单选</label>
            <input name="single_count" type="number" min="0" value="{_esc(s['single_count'])}"/></div>
          <div class="field"><label>多选</label>
            <input name="multiple_count" type="number" min="0" value="{_esc(s['multiple_count'])}"/></div>
          <div class="field"><label>判断</label>
            <input name="judge_count" type="number" min="0" value="{_esc(s['judge_count'])}"/></div>
          <div class="field"><label>简答</label>
            <input name="short_count" type="number" min="0" value="{_esc(s['short_count'])}"/></div>
        </div>
      </section>

      <section>
        <h2 class="section-title">生成选项</h2>
        <div class="gen-grid">
          <div class="field"><label>生成份数</label>
            <input name="paper_count" type="number" min="1" value="{_esc(s['paper_count'])}"/></div>
          <div class="field"><label>随机种子（可空）</label>
            <input name="seed" value="{_esc(s['seed'])}" placeholder="留空则每次随机"/></div>
          <div class="field" style="grid-column:1/-1"><label>试卷标题（可选）</label>
            <input name="title" value="{_esc(s['title'])}"/></div>
          <div class="field"><label>输出目录</label>
            <input name="output_dir" value="{_esc(s['output_dir'])}"/></div>
          <div class="field"><label>文件名模式</label>
            <input name="filename_pattern" value="{_esc(s['filename_pattern'])}"/>
            <p class="hint">需包含 {{n}}；可用 {{bank}}</p></div>
        </div>
      </section>

      <details class="advanced">
        <summary>高级选项</summary>
        <div class="field" style="margin-top:10px">
          <label>模板路径</label>
          <input name="template_path" value="{_esc(s['template_path'])}"/>
        </div>
        <div class="field" style="margin-top:10px">
          <label>题库文件夹（可选，降级）</label>
          <input name="folder" value="{_esc(s.get('folder', ''))}"
            placeholder="若填写则忽略上方四个路径，按文件夹自动识别"/>
        </div>
      </details>

      <div class="actions">
        <button class="btn primary" type="submit">生成试卷</button>
      </div>
    </form>
  </div>
</body>
</html>
"""


def _parse_form(raw: str) -> dict:
    form = {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}
    state = {
        "bank": form.get("bank", ""),
        "folder": form.get("folder", "").strip(),
        "excel_single": form.get("excel_single", "").strip(),
        "excel_multiple": form.get("excel_multiple", "").strip(),
        "excel_judge": form.get("excel_judge", "").strip(),
        "excel_qa": form.get("excel_qa", "").strip(),
        "single_count": int(form.get("single_count") or 0),
        "multiple_count": int(form.get("multiple_count") or 0),
        "judge_count": int(form.get("judge_count") or 0),
        "short_count": int(form.get("short_count") or 0),
        "paper_count": int(form.get("paper_count") or 1),
        "seed": form.get("seed", "").strip(),
        "title": form.get("title", "").strip(),
        "output_dir": form.get("output_dir", "").strip(),
        "filename_pattern": form.get("filename_pattern", "").strip(),
        "template_path": form.get("template_path", "").strip(),
    }
    return state


def _make_handler(config_path: Path):
    config = load_config(config_path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, body: str, code: int = 200) -> None:
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            state = load_ui_state()
            self._send(_html_page(config, state))

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            path = self.path.split("?", 1)[0]

            if path == "/fill":
                form = {
                    k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()
                }
                state = load_ui_state()
                bank = (form.get("bank") or "").strip()
                state["bank"] = bank
                try:
                    if not bank:
                        raise ValueError("请先选择要填充的题库。")
                    excel_paths, name = resolve_excel_paths(config, bank_name=bank)
                    state["excel_single"] = excel_paths["single"]
                    state["excel_multiple"] = excel_paths["multiple"]
                    state["excel_judge"] = excel_paths["judge"]
                    state["excel_qa"] = excel_paths["qa"]
                    state["folder"] = ""
                    save_ui_state(state)
                    msg = f"已从「{name}」填入四个题库路径。\n{describe_bank_files(excel_paths)}"
                    self._send(_html_page(config, state, msg, ok=True))
                except Exception as exc:
                    self._send(
                        _html_page(config, state, friendly_error(exc), ok=False)
                    )
                return

            state = _parse_form(raw)
            save_ui_state(state)

            try:
                paper_count = state["paper_count"]
                if paper_count < 1:
                    raise ValueError("生成份数必须 ≥ 1。")
                pattern = state["filename_pattern"]
                if "{n}" not in pattern:
                    raise ValueError("文件名模式需包含 {n}")
                seed = int(state["seed"]) if state["seed"] else None

                folder = state.get("folder") or ""
                if folder:
                    excel_paths, bank_name = resolve_excel_paths(
                        config, bank_folder=folder
                    )
                else:
                    overrides = _require_excel_overrides(state)
                    excel_paths, bank_name = resolve_excel_paths(
                        config, excel_overrides=overrides
                    )
                    bank_name = state.get("bank") or None

                working = {
                    **config,
                    "paper": {
                        **config.get("paper", {}),
                        "title": state["title"],
                        "single_count": state["single_count"],
                        "multiple_count": state["multiple_count"],
                        "judge_count": state["judge_count"],
                        "short_count": state["short_count"],
                    },
                    "output": {
                        **config.get("output", {}),
                        "dir": state["output_dir"],
                        "filename_pattern": pattern,
                    },
                    "template": {
                        **config.get("template", {}),
                        "path": state["template_path"],
                    },
                }
                outputs = generate_batch(
                    working, paper_count, seed, excel_paths, bank_name
                )
                listing = describe_bank_files(excel_paths)
                msg = f"生成成功。\n{listing}"
                self._send(
                    _html_page(
                        config,
                        state,
                        msg,
                        [str(p) for p in outputs],
                        ok=True,
                    )
                )
            except Exception as exc:
                self._send(
                    _html_page(config, state, friendly_error(exc), ok=False),
                )

    return Handler


def run_web_app(config_path: Path | None = None, open_browser: bool = True) -> None:
    path = config_path or (app_dir() / "config.yaml")
    handler = _make_handler(Path(path))
    server = ThreadingHTTPServer((HOST, PORT), handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"组卷界面已启动: {url}")
    print("浏览器中操作即可；终端按 Ctrl+C 结束。")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_web_app()
