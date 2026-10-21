#!/usr/bin/env python3
"""Read-only library discovery/checks; Python 3.8+, standard library only."""

import argparse
import json
import os
from pathlib import Path, PureWindowsPath
import sys


SUBJECTS = ("数学", "物理", "化学", "历史", "道法", "语文")
MARKER_FILE = Path("知识清单/_编写规范与模板.md")
MARKER_DIRS = (Path("知识清单/初中"), Path("方法套路"))
SIX_BOOKS = tuple(g + t for g in ("七年级", "八年级", "九年级")
                  for t in ("上册", "下册"))


def configured_path(value):
    """Never interpret foreign OS paths or relative explicit roots as cwd paths."""
    if not value or not value.strip():
        raise ValueError("配置的根目录为空")
    win = PureWindowsPath(value)
    if os.name != "nt" and (win.drive or "\\" in value):
        raise ValueError("当前系统不能使用 Windows 路径：" + value)
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("根目录必须是当前系统的绝对路径：" + value)
    return path.resolve()


def readable_file(path):
    try:
        if not path.is_file():
            return "文件缺失或不是普通文件：" + str(path)
        with path.open("rb") as stream:
            if not stream.read(1):
                return "文件为空：" + str(path)
    except OSError as exc:
        return "文件缺失或不可读：{} ({})".format(path, exc)
    return None


def readable_dir(path):
    try:
        list(path.iterdir())
    except OSError as exc:
        return "目录缺失或不可读：{} ({})".format(path, exc)
    return None


def root_errors(root):
    checks = [readable_file(root / MARKER_FILE)]
    checks.extend(readable_dir(root / part) for part in MARKER_DIRS)
    return [error for error in checks if error]


def candidates(skill_dir, cwd):
    """Only inspect ancestors and two named children, never recursively scan disks."""
    seen = set()
    for start in (skill_dir.resolve(), cwd.resolve()):
        for parent in (start, *start.parents):
            for candidate in (parent, parent / "学习资料库", parent / "study-lib"):
                candidate = candidate.resolve()
                if candidate not in seen:
                    seen.add(candidate)
                    yield candidate


def select_library(explicit, source, skill_dir, cwd):
    if explicit is not None:
        root = configured_path(explicit)
        errors = root_errors(root)
        if errors:
            raise ValueError("{} 配置无效，未自动回退：\n{}".format(source, "\n".join(errors)))
        return root, source, [str(root)]
    checked = list(candidates(skill_dir, cwd))
    valid = [root for root in checked if not root_errors(root)]
    if len(valid) == 1:
        return valid[0], "relative-discovery", [str(p) for p in checked]
    if valid:
        raise ValueError("发现多个知识库，请用 --lib-root 或 CZ_COMBINE_LIB_ROOT 选择：\n"
                         + "\n".join(str(p) for p in valid))
    raise ValueError("未找到知识库；需要可读且非空的 {} 及目录 {}。已检查：\n{}".format(
        MARKER_FILE, ", ".join(str(p) for p in MARKER_DIRS),
        "\n".join(str(p) for p in checked)))


def relative_file(root, value):
    """Resolve portable relative resource paths; reject accidental absolute/escape paths."""
    win = PureWindowsPath(value)
    if not value or win.drive or win.root or Path(value).is_absolute():
        raise ValueError("资源必须是根目录内的相对路径：" + value)
    path = (root / value.replace("\\", "/")).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        raise ValueError("资源路径越出根目录：" + value)
    return path


def subject_errors(root, subjects):
    errors = []
    for subject in subjects:
        books = (("八年级上册", "八年级下册", "九年级全一册") if subject == "物理"
                 else ("九年级上册", "九年级下册") if subject == "化学" else SIX_BOOKS)
        for book in books:
            error = readable_file(root / "知识清单" / "初中" / subject / (book + ".md"))
            if error:
                errors.append(error)
        methods = root / "方法套路" / ("初中数学" if subject == "数学" else subject + "/初中")
        error = readable_dir(methods)
        if error:
            errors.append(error)
        else:
            files = sorted(methods.glob("[0-9]*.md"))
            if not files:
                errors.append("未找到方法文件：" + str(methods / "[0-9]*.md"))
            for path in files:
                error = readable_file(path)
                if error:
                    errors.append(error)
        talk = (root / "方法套路/讲法话术.md" if subject in ("数学", "物理")
                else root / "方法套路/讲法话术_化学英语.md" if subject == "化学"
                else methods / ("讲法话术_" + subject + ".md"))
        error = readable_file(talk)
        if error:
            errors.append(error)
    return errors


def run_checks(args, skill_dir=None, cwd=None, environ=None):
    environ = os.environ if environ is None else environ
    skill_dir = Path(__file__).resolve().parents[1] if skill_dir is None else skill_dir
    cwd = Path.cwd() if cwd is None else cwd
    report = {"ok": False, "lib_root": None, "textbook_root": None,
              "errors": [], "warnings": [],
              "citation_status": "未检索内容；路径检查不等于已引用教材"}
    try:
        explicit = args.lib_root if args.lib_root is not None else environ.get("CZ_COMBINE_LIB_ROOT")
        source = "--lib-root" if args.lib_root is not None else "CZ_COMBINE_LIB_ROOT"
        root, source, checked = select_library(explicit, source, skill_dir, cwd)
        report.update(lib_root=str(root), lib_source=source, checked=checked)
        report["errors"].extend(subject_errors(root, args.subject or SUBJECTS))
        for value in args.require:
            error = readable_file(relative_file(root, value))
            if error:
                report["errors"].append(error)

        explicit = (args.textbook_root if args.textbook_root is not None
                    else environ.get("CZ_COMBINE_TEXTBOOK_ROOT"))
        source = "--textbook-root" if args.textbook_root is not None else "CZ_COMBINE_TEXTBOOK_ROOT"
        textbook = configured_path(explicit) if explicit is not None else root.parent / "教材库"
        report.update(textbook_source=source if explicit is not None else "lib-sibling",
                      textbook_checked=str(textbook))
        error = readable_dir(textbook)
        if error:
            target = "errors" if explicit is not None or args.textbook else "warnings"
            report[target].append(error + "；未读取教材全本，不得标为已引用教材")
        else:
            report["textbook_root"] = str(textbook)
        for value in args.textbook:
            error = readable_file(relative_file(textbook, value))
            if error:
                report["errors"].append(error)
    except (ValueError, OSError, RuntimeError) as exc:
        report["errors"].append(str(exc))
    report["ok"] = not report["errors"]
    return report


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--lib-root", help="知识库绝对路径；优先于 CZ_COMBINE_LIB_ROOT")
    result.add_argument("--textbook-root", help="本地教材库绝对路径；优先于 CZ_COMBINE_TEXTBOOK_ROOT")
    result.add_argument("--subject", choices=SUBJECTS, action="append", help="可重复；默认检查六科")
    result.add_argument("--require", action="append", default=[], metavar="RELATIVE_FILE",
                        help="本题必需的知识库文件（可重复，须精确到文件）")
    result.add_argument("--textbook", action="append", default=[], metavar="RELATIVE_DOCX",
                        help="本题必需的教材文件（可重复，缺失时失败）")
    return result


def main():
    report = run_checks(parser().parse_args())
    # ASCII JSON also round-trips in legacy Windows PowerShell code pages.
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
