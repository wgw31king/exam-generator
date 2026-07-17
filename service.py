"""组卷公共 API：供 CLI 与桌面界面共用，避免两套业务逻辑。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from assembler import BatchAssembler, InsufficientQuestionsError
from bank_resolver import discover_bank_files, format_bank_listing
from paths import app_dir, resolve_path
from renderer import render_paper

UI_STATE_NAME = "ui_state.yaml"


def _normalize_config_text(text: str) -> str:
    """修正 Windows 记事本常见隐藏问题：Tab、中文引号等。"""
    text = text.replace("\t", "  ")
    for bad, good in (
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\uff02", '"'),
        ("\u2018", "'"),
        ("\u2019", "'"),
    ):
        text = text.replace(bad, good)
    return text


def load_config(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        raw = _normalize_config_text(raw)
        return yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ValueError(
            f"config.yaml 格式错误: {exc}\n\n"
            "常见原因：\n"
            "  1. excel 下四行缩进不一致（必须用空格，每行前 2 格，不要用 Tab）\n"
            "  2. 路径用了中文引号或双引号写成了 \"\"...\"\"\n"
            "  3. 注释行里写了 D:\\题库 这类反斜杠路径\n\n"
            "建议：删除 config.yaml 全部内容，从 使用说明.txt 或下方模板重新粘贴：\n"
            "excel:\n"
            '  single: "题库/单选.xls"\n'
            '  multiple: "题库/多选.xls"\n'
            '  judge: "题库/判断.xls"\n'
            '  qa: "题库/问答.xls"'
        ) from exc


def resolve(path: str | Path) -> Path:
    return resolve_path(path)


def build_excel_paths(config: dict) -> dict[str, str]:
    if "excel" not in config:
        raise FileNotFoundError(
            "未配置题库。请在 config.yaml 中设置 banks 或 excel，"
            "或在界面中选择题库文件夹。"
        )
    paths: dict[str, str] = {}
    missing: list[str] = []
    for key, path in config["excel"].items():
        resolved = resolve(path)
        if not resolved.exists():
            missing.append(f"  {key}: {resolved}")
        else:
            paths[key] = str(resolved)

    if missing:
        bank_dir = app_dir() / "题库"
        hint = ""
        if bank_dir.is_dir():
            found = sorted(p.name for p in bank_dir.iterdir() if p.is_file())
            hint = f"\n\n「题库」文件夹里现有文件：\n  " + "\n  ".join(found or ["（空）"])
            hint += (
                "\n\n需要以下 4 个文件（文件名必须一致）：\n"
                "  单选.xls  多选.xls  判断.xls  问答.xls"
            )
        raise FileNotFoundError("题库文件不存在:\n" + "\n".join(missing) + hint)
    return paths


def excel_paths_from_folder(folder: str | Path) -> tuple[dict[str, str], str]:
    """从文件夹自动识别四类题库，返回 (excel_paths, bank_name)。"""
    directory = resolve(folder)
    discovered = discover_bank_files(directory)
    bank_name = directory.name
    return {key: str(path) for key, path in discovered.items()}, bank_name


def resolve_excel_paths(
    config: dict,
    *,
    bank_name: str | None = None,
    excel_overrides: dict[str, str] | None = None,
    bank_folder: str | Path | None = None,
    interactive_pick: bool = False,
) -> tuple[dict[str, str], str | None]:
    """解析题库路径。

    优先级：excel_overrides > bank_folder > banks(+bank_name) > excel。
    """
    if excel_overrides:
        merged = dict(config)
        merged["excel"] = {**config.get("excel", {}), **excel_overrides}
        return build_excel_paths(merged), None

    if bank_folder:
        return excel_paths_from_folder(bank_folder)

    banks = config.get("banks")
    if banks:
        if bank_name:
            if bank_name not in banks:
                raise ValueError(
                    f"未知题库「{bank_name}」。可选: {', '.join(banks.keys())}"
                )
            chosen = bank_name
        elif config.get("active_bank"):
            chosen = config["active_bank"]
            if chosen not in banks:
                raise ValueError(
                    f"config.yaml 中 active_bank={chosen!r} 不在 banks 列表里。"
                )
        elif interactive_pick:
            chosen = _pick_bank_name(banks)
        elif len(banks) == 1:
            chosen = next(iter(banks))
        else:
            raise ValueError(
                "请选择题库名称。可选: " + "、".join(banks.keys())
            )

        folder = resolve(banks[chosen])
        discovered = discover_bank_files(folder)
        return {key: str(path) for key, path in discovered.items()}, chosen

    return build_excel_paths(config), None


def _pick_bank_name(banks: dict[str, str]) -> str:
    names = list(banks.keys())
    if len(names) == 1:
        return names[0]

    print("请选择题库：")
    for index, name in enumerate(names, start=1):
        print(f"  {index}. {name}")
    while True:
        raw = input("请输入编号: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(names):
            return names[int(raw) - 1]
        print("请输入有效编号。")


def apply_paper_overrides(config: dict, overrides: dict[str, Any]) -> dict:
    """浅拷贝 config，并用界面/调用方参数覆盖 paper/output/template。"""
    merged = {
        **config,
        "paper": {**config.get("paper", {})},
        "output": {**config.get("output", {})},
        "template": {**config.get("template", {})},
    }
    paper_keys = (
        "title",
        "single_count",
        "multiple_count",
        "judge_count",
        "short_count",
    )
    for key in paper_keys:
        if key in overrides and overrides[key] is not None:
            merged["paper"][key] = overrides[key]
    if "output_dir" in overrides and overrides["output_dir"] is not None:
        merged["output"]["dir"] = overrides["output_dir"]
    if "filename_pattern" in overrides and overrides["filename_pattern"] is not None:
        merged["output"]["filename_pattern"] = overrides["filename_pattern"]
    if "template_path" in overrides and overrides["template_path"] is not None:
        merged["template"]["path"] = overrides["template_path"]
    return merged


def generate_batch(
    config: dict,
    paper_count: int,
    seed: int | None,
    excel_paths: dict[str, str],
    bank_name: str | None = None,
) -> list[Path]:
    counts = {
        "single": config["paper"]["single_count"],
        "multiple": config["paper"]["multiple_count"],
        "judge": config["paper"]["judge_count"],
        "short": config["paper"]["short_count"],
    }

    batch = BatchAssembler(excel_paths, counts, seed=seed)
    batch.validate_capacity(paper_count)

    output_dir = resolve(config["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = resolve(config["template"]["path"])

    outputs: list[Path] = []
    for index in range(1, paper_count + 1):
        paper = batch.assemble_next(index)
        filename = config["output"]["filename_pattern"].format(
            n=index,
            bank=bank_name or "",
        )
        output_path = output_dir / filename
        render_paper(
            template_path,
            paper,
            output_path,
            paper_title=config.get("paper", {}).get("title", ""),
        )
        outputs.append(output_path)
    return outputs


def run_generation(
    config: dict,
    *,
    paper_count: int,
    seed: int | None = None,
    bank_name: str | None = None,
    bank_folder: str | Path | None = None,
    excel_overrides: dict[str, str] | None = None,
    paper_overrides: dict[str, Any] | None = None,
) -> list[Path]:
    """一次完整组卷：解析题库 → 覆盖参数 → 生成。"""
    working = apply_paper_overrides(config, paper_overrides or {})
    excel_paths, resolved_bank = resolve_excel_paths(
        working,
        bank_name=bank_name,
        excel_overrides=excel_overrides,
        bank_folder=bank_folder,
        interactive_pick=False,
    )
    return generate_batch(
        working,
        paper_count,
        seed,
        excel_paths,
        resolved_bank or bank_name,
    )


def describe_bank_files(excel_paths: dict[str, str]) -> str:
    return format_bank_listing({k: Path(v) for k, v in excel_paths.items()})


def ui_state_path() -> Path:
    return app_dir() / UI_STATE_NAME


def load_ui_state() -> dict:
    path = ui_state_path()
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8-sig")
        data = yaml.safe_load(_normalize_config_text(raw))
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def save_ui_state(state: dict) -> None:
    path = ui_state_path()
    path.write_text(
        yaml.safe_dump(state, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def friendly_error(exc: BaseException) -> str:
    if isinstance(exc, InsufficientQuestionsError):
        text = str(exc)
        for eng, zh in (
            ("single", "单选"),
            ("multiple", "多选"),
            ("judge", "判断"),
            ("short", "简答"),
        ):
            text = text.replace(f"{eng} 题库", f"{zh}题库")
            text = text.replace(f"{eng} 剩余", f"{zh}剩余")
        return f"组卷失败: {text}"
    return str(exc)
