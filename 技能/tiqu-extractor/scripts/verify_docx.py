#!/usr/bin/env python3
"""只读核对 extract.json 与生成的 Word；不代替原照片及逐页视觉核对。"""
import argparse
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from extract_schema import load_extract


def digest(data):
    return hashlib.sha256(data).hexdigest()


def expected_items(data):
    items = [("文字", data["title"])]
    for block in data["blocks"]:
        typ = block["type"]
        if typ in ("section", "para"):
            items.append(("文字", block["text"]))
        elif typ == "q":
            items.append(("文字", block["no"] + " " + block["text"]))
        elif typ == "image":
            items.append(("图片", digest(Path(block["path"]).read_bytes())))
        opts = block.get("opts") if typ == "q" else block.get("items") if typ == "opts" else None
        if opts:
            items.append(("选项", tuple(opts) + (("",) if len(opts) % 2 else ())))
    return items


def actual_items(doc):
    items = []
    for element in doc.element.body:
        if element.tag == qn("w:sectPr"):
            continue
        if element.tag == qn("w:tbl"):
            table = Table(element, doc)
            if len(table.columns) != 2 or element.xpath('.//w:drawing | .//w:tbl'):
                raise ValueError("选项表必须为两列纯文字，不含图片或嵌套表格")
            items.append(("选项", tuple(cell.text for row in table.rows for cell in row.cells)))
        elif element.tag == qn("w:p"):
            paragraph = Paragraph(element, doc)
            drawings = element.xpath('.//w:drawing')
            if paragraph.text:
                if drawings:
                    raise ValueError("图片应独立成段，不能与题干文字混排")
                items.append(("文字", paragraph.text))
            for drawing in drawings:
                if len(drawing.xpath('./wp:inline')) != 1:
                    raise ValueError("配图必须为行内图片，不支持浮动锚点")
                blips = drawing.xpath('.//a:blip')
                if len(blips) != 1 or blips[0].get(qn("r:link")):
                    raise ValueError("配图缺失、使用外部链接或图片结构异常")
                rel_id = blips[0].get(qn("r:embed"))
                rel = doc.part.rels.get(rel_id)
                if rel is None or rel.is_external:
                    raise ValueError("配图关联缺失或为外部链接")
                items.append(("图片", digest(rel.target_part.blob)))
            if element.xpath('.//w:pict | .//w:object'):
                raise ValueError("发现生成器未支持的旧式图片或嵌入对象")
        else:
            raise ValueError("发现生成器未支持的正文结构：" + element.tag)
    return items


def verify(json_path, docx_path):
    report = {"ok": False, "errors": [],
              "scope": "只核对 JSON 与 Word 的文字、选项顺序和图片内容；仍须核对原照片及逐页排版"}
    try:
        expected = expected_items(load_extract(json_path))
        doc = Document(docx_path)
        if doc.element.body.xpath('.//w:ins | .//w:del | .//w:vanish | .//w:webHidden'):
            raise ValueError("正文含修订或隐藏文字，请先明确最终可见内容")
        for part in doc.part.related_parts.values():
            if str(part.partname).startswith(("/word/header", "/word/footer")):
                if part.element.xpath('.//w:drawing | .//w:pict') or any(
                        node.text and node.text.strip() for node in part.element.xpath('.//w:t')):
                    raise ValueError("发现 JSON 未提供的页眉或页脚内容")
        actual = actual_items(doc)
        if len(expected) != len(actual):
            report["errors"].append("内容块数不一致：JSON {}，Word {}".format(len(expected), len(actual)))
        for index, (left, right) in enumerate(zip(expected, actual), 1):
            if left != right:
                report["errors"].append("第 {} 个内容块不一致（预期 {}，实际 {}），请对照 JSON 核对".format(index, left[0], right[0]))
        # 本生成器固定单节 A4，防止图片或页边距使内容越出正文宽度。
        if len(doc.sections) != 1:
            report["errors"].append("预期单节文档，发现额外分节")
        section = doc.sections[0]
        width = section.page_width - section.left_margin - section.right_margin
        height = section.page_height - section.top_margin - section.bottom_margin
        if width <= 0 or height <= 0:
            report["errors"].append("页边距超过页面尺寸")
        for index, shape in enumerate(doc.inline_shapes, 1):
            if shape.width <= 0 or shape.height <= 0 or shape.width > width or shape.height > height:
                report["errors"].append("第 {} 张图片尺寸无效或超出页面正文区域".format(index))
        report.update(expected_blocks=len(expected), actual_blocks=len(actual))
    except Exception as exc:
        # 任一解析/依赖/读取问题均使检查失败，不将异常当作通过。
        report["errors"].append("检查失败：{}：{}".format(type(exc).__name__, exc))
    report["ok"] = not report["errors"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract_json")
    parser.add_argument("document")
    args = parser.parse_args()
    report = verify(args.extract_json, args.document)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
