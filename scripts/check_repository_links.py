#!/usr/bin/env python3
"""只读检查本地 Markdown 链接、明确的库内文件路径与方法索引；不访问外部网站。"""
import argparse
import json
from pathlib import Path, PureWindowsPath
import re
from urllib.parse import unquote, urlsplit


AREAS = ("初中数学", "高中数学", "物理", "化学", "英语", "历史", "道法", "语文")


def prose_lines(text):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            token = match[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield number, line


def method_counts(root):
    counts = {}
    for area in AREAS:
        counts[area] = sum(
            len(re.findall(r"^## (?:方法|模型|【快解·超纲】)", path.read_text(encoding="utf-8"), re.M))
            for path in (root / "方法套路" / area).rglob("*.md") if path.name[0].isdigit())
    return counts


def local_link_errors(root):
    errors = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r"/home/[^\s`]*Doubao/chats/", line):
                errors.append(f"{rel}:{number} 仍依赖旧工作目录")
        for number, line in prose_lines(text):
            # 本库使用内联 Markdown 链接。只检查文件目标，锚点和外部网站另行核验。
            for match in re.finditer(r"\[[^\]\n]+\]\(([^)\n]+)\)", line):
                target = match[1].strip()
                if target.startswith('<') and '>' in target:
                    target = target[1:target.index('>')]
                else:
                    target = re.split(r'\s+["\']', target)[0]
                if PureWindowsPath(target).drive:
                    errors.append(f"{rel}:{number} 非便携链接：{target}")
                    continue
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith(("#", "//")):
                    continue
                value = unquote(parsed.path)
                if not value:
                    continue
                if Path(value).is_absolute() or PureWindowsPath(value).drive:
                    errors.append(f"{rel}:{number} 非便携链接：{target}")
                    continue
                location = (path.parent / value).resolve()
                try:
                    location.relative_to(root)
                except ValueError:
                    errors.append(f"{rel}:{number} 链接越出知识库：{target}")
                    continue
                if not location.exists():
                    errors.append(f"{rel}:{number} 链接目标缺失：{location}")
            # 检查正文中明确写出的库内 Markdown 文件；省略号、通配符和模板不代表精确文件。
            for match in re.finditer(r"`(?:\$LIB/)?((?:知识清单|方法套路|同步清单|课标)/[^`\n]+\.md)`", line):
                value = match[1]
                if any(c in value for c in ('*', '?', '<', '>', '{', '}', '…', '...')):
                    continue
                location = root / value
                if not location.is_file():
                    errors.append(f"{rel}:{number} 库内文件缺失：{location}")
    return errors


def index_errors(root):
    errors = []
    for level in ("初中", "高中"):
        folder = root / "方法套路/物理" / level
        index = (folder / "README.md").read_text(encoding="utf-8")
        linked = re.findall(r"\]\(([^)]+\.md)\)", index)
        expected = {p.name for p in folder.glob("[0-9]*.md")}
        if set(linked) != expected or len(linked) != len(expected):
            errors.append(f"物理/{level}：专题索引与现有编号文件不一致")
    folder = root / "方法套路/初中数学"
    numbers = []
    for path in folder.glob("[0-9]*.md"):
        numbers.extend(re.findall(r"^## 方法(\d+)：", path.read_text(encoding="utf-8"), re.M))
    indexed = re.findall(r"^\| (\d+) \|", (folder / "README.md").read_text(encoding="utf-8"), re.M)
    if len(numbers) != len(set(numbers)):
        errors.append("初中数学方法编号重复")
    if sorted(numbers) != sorted(indexed):
        errors.append("初中数学方法正文与 README 索引编号不一致")
    return errors


def check(root):
    root = Path(root).resolve()
    report = {"ok": False, "errors": [], "root": str(root),
              "scope": "本地内联链接的文件目标、明确的库内路径及方法索引；不证明锚点、外部网址或知识事实正确"}
    try:
        if not (root / "README.md").is_file() or not (root / "方法套路").is_dir():
            raise ValueError("不是可检查的知识库根目录：" + str(root))
        report["errors"] = local_link_errors(root) + index_errors(root)
        report["method_counts"] = method_counts(root)
        report["method_total"] = sum(report["method_counts"].values())
    except (OSError, ValueError) as exc:
        report["errors"].append(str(exc))
    report["ok"] = not report["errors"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    report = check(parser.parse_args().root)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
