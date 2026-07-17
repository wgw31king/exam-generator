"""桌面图形界面：配置出题参数并一键组卷（标准库 tkinter）。"""

from __future__ import annotations

import os
import platform
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

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

EXCEL_LABELS = (
    ("single", "单选", "excel_single"),
    ("multiple", "多选", "excel_multiple"),
    ("judge", "判断", "excel_judge"),
    ("qa", "简答", "excel_qa"),
)


def _open_folder(path: Path) -> None:
    folder = path if path.is_dir() else path.parent
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(folder)], check=False)
        elif system == "Windows":
            os.startfile(str(folder))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)
    except OSError:
        pass


class ExamGeneratorApp(ttk.Frame):
    def __init__(self, master: tk.Tk, config_path: Path) -> None:
        super().__init__(master, padding=14)
        self.master = master
        self.config_path = config_path
        self.config: dict = {}
        self._last_output_dir: Path | None = None
        self._generating = False

        self.pack(fill=tk.BOTH, expand=True)
        self._build_vars()
        self._build_ui()
        self._load_initial()

    def _build_vars(self) -> None:
        self.bank_var = tk.StringVar()
        self.excel_vars = {
            "single": tk.StringVar(),
            "multiple": tk.StringVar(),
            "judge": tk.StringVar(),
            "qa": tk.StringVar(),
        }
        self.single_count = tk.IntVar(value=30)
        self.multiple_count = tk.IntVar(value=10)
        self.judge_count = tk.IntVar(value=30)
        self.short_count = tk.IntVar(value=5)
        self.paper_count = tk.IntVar(value=1)
        self.seed_var = tk.StringVar(value="")
        self.title_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value=str(user_desktop_dir()))
        self.filename_var = tk.StringVar(value="待命名试卷_{n}.docx")
        self.template_var = tk.StringVar(value="templates/template.docx")
        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")

    def _build_ui(self) -> None:
        self.master.title("组卷")
        self.master.minsize(640, 620)

        row = 0
        ttk.Label(self, text="组卷", font=("", 18, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W
        )
        row += 1
        ttk.Label(
            self, text="填写四类题库路径，设定题量后一键生成试卷", foreground="#555"
        ).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        row += 1

        ttk.Label(self, text="题库路径", font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(4, 4)
        )
        row += 1

        ttk.Label(self, text="快捷填充").grid(row=row, column=0, sticky=tk.W)
        self.bank_combo = ttk.Combobox(
            self, textvariable=self.bank_var, state="readonly", width=32
        )
        self.bank_combo.grid(row=row, column=1, sticky=tk.EW, padx=4)
        ttk.Button(self, text="填入路径", command=self._fill_from_bank).grid(
            row=row, column=2, sticky=tk.W
        )
        row += 1

        for key, label, _ in EXCEL_LABELS:
            ttk.Label(self, text=f"{label}题库").grid(row=row, column=0, sticky=tk.W)
            ttk.Entry(self, textvariable=self.excel_vars[key]).grid(
                row=row, column=1, sticky=tk.EW, padx=4, pady=2
            )
            ttk.Button(
                self,
                text="浏览…",
                command=lambda k=key, lb=label: self._browse_excel(k, lb),
            ).grid(row=row, column=2, sticky=tk.W)
            row += 1

        ttk.Separator(self).grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)
        row += 1

        ttk.Label(self, text="出题数量", font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 4)
        )
        row += 1

        counts = [
            ("单选", self.single_count),
            ("多选", self.multiple_count),
            ("判断", self.judge_count),
            ("简答", self.short_count),
        ]
        count_frame = ttk.Frame(self)
        count_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W)
        for i, (label, var) in enumerate(counts):
            ttk.Label(count_frame, text=label).grid(row=0, column=i * 2, padx=(0, 4))
            ttk.Spinbox(
                count_frame, from_=0, to=500, textvariable=var, width=6
            ).grid(row=0, column=i * 2 + 1, padx=(0, 12))
        row += 1

        ttk.Separator(self).grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)
        row += 1

        ttk.Label(self, text="生成选项", font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 4)
        )
        row += 1

        ttk.Label(self, text="生成份数").grid(row=row, column=0, sticky=tk.W)
        ttk.Spinbox(
            self, from_=1, to=100, textvariable=self.paper_count, width=8
        ).grid(row=row, column=1, sticky=tk.W, padx=4)
        row += 1

        ttk.Label(self, text="随机种子（可空）").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(self, textvariable=self.seed_var, width=16).grid(
            row=row, column=1, sticky=tk.W, padx=4
        )
        row += 1

        ttk.Label(self, text="试卷标题（可选）").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(self, textvariable=self.title_var).grid(
            row=row, column=1, columnspan=2, sticky=tk.EW, padx=4
        )
        row += 1

        ttk.Label(self, text="输出目录").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(self, textvariable=self.output_dir_var).grid(
            row=row, column=1, sticky=tk.EW, padx=4
        )
        ttk.Button(self, text="浏览…", command=self._browse_output).grid(
            row=row, column=2, sticky=tk.W
        )
        row += 1

        ttk.Label(self, text="文件名模式").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(self, textvariable=self.filename_var).grid(
            row=row, column=1, columnspan=2, sticky=tk.EW, padx=4
        )
        ttk.Label(
            self, text="需包含 {n}；可用 {bank}", foreground="#666"
        ).grid(row=row + 1, column=1, sticky=tk.W, padx=4)
        row += 2

        self.advanced = ttk.LabelFrame(self, text="高级选项", padding=8)
        self.advanced.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=6)
        ttk.Label(self.advanced, text="模板路径").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(self.advanced, textvariable=self.template_var).grid(
            row=0, column=1, sticky=tk.EW, padx=4
        )
        ttk.Button(self.advanced, text="浏览…", command=self._browse_template).grid(
            row=0, column=2
        )
        ttk.Label(self.advanced, text="题库文件夹（可选）").grid(
            row=1, column=0, sticky=tk.W, pady=(6, 0)
        )
        ttk.Entry(self.advanced, textvariable=self.folder_var).grid(
            row=1, column=1, sticky=tk.EW, padx=4, pady=(6, 0)
        )
        ttk.Button(self.advanced, text="浏览…", command=self._browse_folder).grid(
            row=1, column=2, pady=(6, 0)
        )
        self.advanced.columnconfigure(1, weight=1)
        row += 1

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)
        self.generate_btn = ttk.Button(
            btn_frame, text="生成试卷", command=self._on_generate
        )
        self.generate_btn.pack(side=tk.LEFT)
        self.open_btn = ttk.Button(
            btn_frame, text="打开输出文件夹", command=self._open_output, state=tk.DISABLED
        )
        self.open_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="记住当前设置", command=self._save_state).pack(
            side=tk.LEFT
        )
        row += 1

        ttk.Label(self, text="状态").grid(row=row, column=0, sticky=tk.NW)
        self.log = tk.Text(self, height=7, wrap=tk.WORD, state=tk.DISABLED)
        self.log.grid(row=row, column=1, columnspan=2, sticky=tk.NSEW, padx=4)
        row += 1

        ttk.Label(self, textvariable=self.status_var).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(6, 0)
        )

        self.columnconfigure(1, weight=1)
        self.rowconfigure(row - 1, weight=1)

    def _load_initial(self) -> None:
        try:
            self.config = load_config(self.config_path)
        except ValueError as exc:
            messagebox.showerror("配置错误", str(exc))
            self.config = {}

        paper = self.config.get("paper", {})
        output = self.config.get("output", {})
        template = self.config.get("template", {})
        excel = self.config.get("excel") or {}

        for key, _, _ in EXCEL_LABELS:
            self.excel_vars[key].set(str(excel.get(key, "") or ""))

        self.single_count.set(int(paper.get("single_count", 30)))
        self.multiple_count.set(int(paper.get("multiple_count", 10)))
        self.judge_count.set(int(paper.get("judge_count", 30)))
        self.short_count.set(int(paper.get("short_count", 5)))
        self.title_var.set(str(paper.get("title", "") or ""))
        self.output_dir_var.set(str(output.get("dir", str(user_desktop_dir()))))
        self.filename_var.set(
            str(output.get("filename_pattern", "待命名试卷_{n}.docx"))
        )
        self.template_var.set(str(template.get("path", "templates/template.docx")))

        banks = list((self.config.get("banks") or {}).keys())
        self.bank_combo["values"] = banks
        if banks:
            active = self.config.get("active_bank")
            self.bank_var.set(active if active in banks else banks[0])

        state = load_ui_state()
        if state:
            self._apply_state(state)

        self._append_log(f"已加载配置: {self.config_path}")

    def _apply_state(self, state: dict) -> None:
        mapping = {
            "bank": self.bank_var,
            "folder": self.folder_var,
            "seed": self.seed_var,
            "title": self.title_var,
            "output_dir": self.output_dir_var,
            "filename_pattern": self.filename_var,
            "template_path": self.template_var,
        }
        for key, var in mapping.items():
            if key in state and state[key] is not None:
                var.set(str(state[key]))
        for excel_key, _, state_key in EXCEL_LABELS:
            if state_key in state and state[state_key] is not None:
                self.excel_vars[excel_key].set(str(state[state_key]))
        for key, var in (
            ("single_count", self.single_count),
            ("multiple_count", self.multiple_count),
            ("judge_count", self.judge_count),
            ("short_count", self.short_count),
            ("paper_count", self.paper_count),
        ):
            if key in state and state[key] is not None:
                try:
                    var.set(int(state[key]))
                except (TypeError, ValueError):
                    pass

    def _collect_state(self) -> dict[str, Any]:
        state = {
            "bank": self.bank_var.get(),
            "folder": self.folder_var.get().strip(),
            "single_count": self.single_count.get(),
            "multiple_count": self.multiple_count.get(),
            "judge_count": self.judge_count.get(),
            "short_count": self.short_count.get(),
            "paper_count": self.paper_count.get(),
            "seed": self.seed_var.get().strip(),
            "title": self.title_var.get().strip(),
            "output_dir": self.output_dir_var.get().strip(),
            "filename_pattern": self.filename_var.get().strip(),
            "template_path": self.template_var.get().strip(),
        }
        for excel_key, _, state_key in EXCEL_LABELS:
            state[state_key] = self.excel_vars[excel_key].get().strip()
        return state

    def _save_state(self) -> None:
        save_ui_state(self._collect_state())
        self.status_var.set("已保存当前设置")
        self._append_log("已写入 ui_state.yaml")

    def _browse_excel(self, key: str, label: str) -> None:
        path = filedialog.askopenfilename(
            title=f"选择{label}题库",
            filetypes=[("Excel 97-2003", "*.xls"), ("所有文件", "*.*")],
        )
        if path:
            self.excel_vars[key].set(path)

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(title="选择题库文件夹")
        if path:
            self.folder_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir_var.set(path)

    def _browse_template(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 Word 模板",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")],
        )
        if path:
            self.template_var.set(path)

    def _fill_from_bank(self) -> None:
        bank = self.bank_var.get().strip()
        if not bank:
            messagebox.showwarning("提示", "请先选择快捷填充题库。")
            return
        try:
            excel_paths, name = resolve_excel_paths(self.config, bank_name=bank)
            for key in self.excel_vars:
                self.excel_vars[key].set(excel_paths[key])
            self.folder_var.set("")
            self._append_log(f"已从「{name}」填入路径\n{describe_bank_files(excel_paths)}")
            self.status_var.set(f"已填入：{name}")
        except Exception as exc:
            messagebox.showerror("填充失败", friendly_error(exc))

    def _append_log(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text.rstrip() + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._generating = busy
        self.generate_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.status_var.set("正在生成…" if busy else "就绪")

    def _parse_seed(self) -> int | None:
        raw = self.seed_var.get().strip()
        if not raw:
            return None
        if not raw.isdigit():
            raise ValueError("随机种子必须是非负整数，或留空。")
        return int(raw)

    def _require_excel_overrides(self) -> dict[str, str]:
        missing: list[str] = []
        overrides: dict[str, str] = {}
        for key, label, _ in EXCEL_LABELS:
            raw = self.excel_vars[key].get().strip()
            if not raw:
                missing.append(label)
                continue
            path = resolve_path(raw)
            if not path.is_file():
                raise FileNotFoundError(f"{label}题库文件不存在: {path}")
            overrides[key] = str(path)
        if missing:
            raise ValueError("请填写完整四个题库路径：" + "、".join(missing))
        return overrides

    def _on_generate(self) -> None:
        if self._generating:
            return
        try:
            paper_count = int(self.paper_count.get())
            if paper_count < 1:
                raise ValueError("生成份数必须 ≥ 1。")
            seed = self._parse_seed()
            pattern = self.filename_var.get().strip()
            if not pattern:
                raise ValueError("文件名模式不能为空。")
            if "{n}" not in pattern:
                raise ValueError("文件名模式需包含 {n}，例如 待命名试卷_{n}.docx")
        except (tk.TclError, ValueError) as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self._set_busy(True)
        self._append_log("—— 开始生成 ——")
        state = self._collect_state()

        def worker() -> None:
            try:
                save_ui_state(state)
                folder = self.folder_var.get().strip()
                if folder:
                    excel_paths, bank_name = resolve_excel_paths(
                        self.config, bank_folder=folder
                    )
                else:
                    overrides = self._require_excel_overrides()
                    excel_paths, _ = resolve_excel_paths(
                        self.config, excel_overrides=overrides
                    )
                    bank_name = self.bank_var.get().strip() or None

                working = dict(self.config)
                working["paper"] = {
                    **working.get("paper", {}),
                    "title": self.title_var.get().strip(),
                    "single_count": int(self.single_count.get()),
                    "multiple_count": int(self.multiple_count.get()),
                    "judge_count": int(self.judge_count.get()),
                    "short_count": int(self.short_count.get()),
                }
                working["output"] = {
                    **working.get("output", {}),
                    "dir": self.output_dir_var.get().strip(),
                    "filename_pattern": pattern,
                }
                working["template"] = {
                    **working.get("template", {}),
                    "path": self.template_var.get().strip(),
                }
                outputs = generate_batch(
                    working, paper_count, seed, excel_paths, bank_name
                )
                self.master.after(
                    0, lambda: self._on_success(outputs, bank_name, excel_paths)
                )
            except Exception as exc:
                msg = friendly_error(exc)
                self.master.after(0, lambda: self._on_failure(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(
        self,
        outputs: list[Path],
        bank_name: str | None,
        excel_paths: dict[str, str],
    ) -> None:
        self._set_busy(False)
        if bank_name:
            self._append_log(f"题库: {bank_name}")
        self._append_log(describe_bank_files(excel_paths))
        for path in outputs:
            self._append_log(f"已生成: {path}")
        self._last_output_dir = outputs[0].parent if outputs else None
        self.open_btn.configure(state=tk.NORMAL)
        self.status_var.set(f"完成：共 {len(outputs)} 份")
        messagebox.showinfo(
            "生成成功",
            f"已生成 {len(outputs)} 份试卷。\n\n" + "\n".join(str(p) for p in outputs),
        )

    def _on_failure(self, message: str) -> None:
        self._set_busy(False)
        self._append_log(message)
        self.status_var.set("失败")
        messagebox.showerror("生成失败", message)

    def _open_output(self) -> None:
        if self._last_output_dir:
            _open_folder(self._last_output_dir)
        else:
            out = self.output_dir_var.get().strip()
            if out:
                _open_folder(resolve_path(out))


def run_app(config_path: Path | None = None) -> None:
    path = config_path or (app_dir() / "config.yaml")
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    ExamGeneratorApp(root, Path(path))
    root.mainloop()


if __name__ == "__main__":
    run_app()
