#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查器和生成器共用的 extract.json 校验；不会改写输入文件。"""
import copy
import json
import math
from pathlib import Path
import re


def question_number(value):
    """接受正整数、数字字符串及末尾带 .／．／、的题号，拒绝布尔值。"""
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str):
        match = re.fullmatch(r"\s*([0-9]+)[.．、]?\s*", value)
        if match and int(match[1]) > 0:
            return int(match[1])
    raise ValueError("题号必须为正整数或数字字符串（可带 .／．／、）")


def load_extract(path):
    """返回校验后的副本：题号统一为 '1.'，图片相对 JSON 所在目录定位。"""
    source = Path(path).resolve()
    with source.open(encoding="utf-8") as stream:
        data = json.load(stream)
    return validate_extract(data, source.parent)


def validate_extract(data, root):
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须为对象")
    data = copy.deepcopy(data)
    errors = []

    def require_text(value, label):
        if not isinstance(value, str) or not value.strip():
            errors.append(label + " 必须为非空字符串")

    def require_options(value, label):
        if not isinstance(value, list) or not value:
            errors.append(label + " 必须为非空字符串列表")
        else:
            for index, item in enumerate(value):
                require_text(item, "%s[%d]" % (label, index))

    def require_number(value, label, minimum, inclusive=False):
        if (type(value) not in (int, float) or not math.isfinite(value)
                or (value < minimum if inclusive else value <= minimum)):
            errors.append(label + (" 必须为非负有限数值" if inclusive else " 必须为正有限数值"))

    require_text(data.get("title"), "title")
    blocks = data.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("\n".join(errors + ["blocks 必须为非空列表，且至少含一道 q 题目"]))
    qnos = []
    question_count = 0
    for index, block in enumerate(blocks):
        label = "块#%d" % index
        if not isinstance(block, dict):
            errors.append(label + " 必须为对象")
            continue
        typ = block.get("type")
        if typ not in ("section", "q", "image", "opts", "para", "blank"):
            errors.append("%s 未知块类型：%r" % (label, typ))
            continue
        if typ in ("section", "q", "para"):
            require_text(block.get("text"), label + ".text")
        if typ == "q":
            question_count += 1
            try:
                number = question_number(block.get("no"))
                if number in qnos:
                    errors.append("%s 题号 %d 重复出现" % (label, number))
                qnos.append(number)
                block["no"] = "%d." % number
            except ValueError as exc:
                errors.append("%s.no：%s" % (label, exc))
            if "opts" in block:
                require_options(block["opts"], label + ".opts")
        elif typ == "opts":
            require_options(block.get("items"), label + ".items")
        elif typ == "para" and "indent" in block:
            require_number(block["indent"], label + ".indent", 0, inclusive=True)
        elif typ == "image":
            if "width_cm" in block:
                require_number(block["width_cm"], label + ".width_cm", 0)
            value = block.get("path")
            if not isinstance(value, str) or not value.strip():
                errors.append(label + ".path 必须为非空字符串")
                continue
            image = Path(value)
            if not image.is_absolute():
                image = Path(root) / image
            block["path"] = str(image.resolve())
            try:
                from PIL import Image
                from docx.image.image import Image as DocxImage
            except ImportError:
                errors.append(label + " 无法校验图片：请安装 Pillow 和 python-docx")
                continue
            try:
                # verify 检查文件结构；load 检查完整像素数据；最后检查 Word 支持。
                with Image.open(image) as im:
                    im.verify()
                with Image.open(image) as im:
                    im.load()
                DocxImage.from_file(str(image))
            except Exception as exc:
                errors.append("%s 配图缺失、损坏或格式不受支持：%s（%s）"
                              % (label, image, type(exc).__name__))
    if not question_count:
        errors.append("blocks 至少需要一道 q 题目，不能生成空试卷")
    if errors:
        raise ValueError("\n".join(errors))
    return data
