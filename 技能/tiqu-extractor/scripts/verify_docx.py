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


def on_off(element):
    """OOXML 开关：缺省为开启；显式 0/false/off 为关闭。"""
    value = element.get(qn("w:val"), "true")
    if value in ("1", "true", "on"):
        return True
    if value in ("0", "false", "off"):
        return False
    raise ValueError("隐藏属性的开关值无效：" + value)


def visibility_value(properties, name):
    if properties is None:
        return None
    nodes = properties.findall(qn("w:" + name))
    if len(nodes) > 1:
        raise ValueError("隐藏属性重复：" + name)
    return on_off(nodes[0]) if nodes else None


def check_body_visibility(doc):
    """核对直接格式及普通段落/字符样式的隐藏属性，不实现完整布局引擎。"""
    body = doc.element.body
    if body.xpath('.//w:ins | .//w:del'):
        raise ValueError("正文含修订，请先明确最终可见内容")
    # 包含段落标记等直接格式；不能仅因存在一个关闭的开关而拒绝。
    if any(on_off(node) for node in body.xpath('.//w:vanish | .//w:webHidden')):
        raise ValueError("正文含隐藏文字，请先明确最终可见内容")
    style_elements = doc.styles.element.findall(qn("w:style"))
    styles = {style.get(qn("w:styleId")): style for style in style_elements}
    defaults = {style.get(qn("w:type")): style.get(qn("w:styleId"))
                for style in style_elements
                if style.get(qn("w:default")) in ("1", "true", "on")}
    default_properties = doc.styles.element.find('./' + qn('w:docDefaults') +
                                                 '/' + qn('w:rPrDefault') + '/' + qn('w:rPr'))
    chains = {}

    def chain(style_id):
        if style_id not in chains:
            result, seen = [], set()
            current = style_id
            while current in styles:
                if current in seen:
                    raise ValueError("样式继承存在循环：" + str(current))
                seen.add(current)
                style = styles[current]
                result.append(style.find(qn("w:rPr")))
                base = style.find(qn("w:basedOn"))
                current = base.get(qn("w:val")) if base is not None else None
            chains[style_id] = result[::-1]
        return chains[style_id]

    for paragraph in body.xpath('.//w:p'):
        pstyle = paragraph.xpath('./w:pPr/w:pStyle/@w:val')
        pchain = chain(pstyle[0] if pstyle else defaults.get("paragraph"))
        for run in paragraph.xpath('./w:r | ./w:hyperlink/w:r'):
            properties = run.find(qn("w:rPr"))
            rstyle = run.xpath('./w:rPr/w:rStyle/@w:val')
            rchain = chain(rstyle[0] if rstyle else defaults.get("character"))
            for name in ("vanish", "webHidden"):
                state = visibility_value(properties, name)
                if state is None:
                    state = visibility_value(default_properties, name) or False
                    for inherited in pchain + rchain:
                        value = visibility_value(inherited, name)
                        # vanish 在样式中是切换属性；直接格式则是绝对值。
                        if value is not None:
                            state = (not state if value else state) if name == "vanish" else value
                if state:
                    raise ValueError("正文样式使文字隐藏，请先明确最终可见内容")


def reject_native_equations(element):
    # python-docx 的 paragraph.text / cell.text 不包含 m:oMath，必须显式拒绝。
    if element.xpath('.//m:oMath | .//m:oMathPara'):
        raise ValueError("发现 JSON 和生成器未支持的 Word 公式，不能按普通文字核对")


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
        reject_native_equations(doc.element.body)
        check_body_visibility(doc)
        for part in doc.part.related_parts.values():
            if str(part.partname).startswith(("/word/header", "/word/footer")):
                reject_native_equations(part.element)
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
