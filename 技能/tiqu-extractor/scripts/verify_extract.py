#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tiqu-extractor · 最严格核对的"自动机检"第一步。

把 extract.json 里【能用程序确定】的错误先全部扫出来并精确定位，
替代"凭印象看一眼"。机检通过不代表视觉无误——逐字/逐图的视觉并排
核对仍必须按 references/最严格核对清单.md 逐项完成。

检查分三级：
  ERR   可确定的错误，必须改（文件缺失、JSON 非法、题号重复等）；
  CHECK 疑似项，必须调出原照片逐处确认并记录结果（题号断档、括号内
        文字、选项数量异常，以及中文/符号、数字与单位、运算符两侧空格）；
  INFO  计数与配图尺寸，用来和原卷逐项对数。

用法：python3 verify_extract.py extract.json
退出码：存在 ERR 时为 1，否则 0（CHECK 需人工确认，不改变退出码）。
"""
import sys
import os
import re
from extract_schema import load_extract, question_number

# 数学 / 中文符号集合（出现空格紧贴时必报）
MATH_SYMS = set("△∠≅∽≈≠∥⊥≥≤√π°∶·×±∓∈∵∴∝∪∩∅⌒⊙⊥")
CJK_RE = re.compile(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]")
OPT_PREFIX_RE = re.compile(r"^\s*[A-Da-d][\.．、]\s*")
PAREN_RE = re.compile(r"[（(]([^（）()]*)[）)]")
UNIT_RE = re.compile(r"^(cm|mm|km|m|米|厘米|毫米|千米|分米)", re.I)


def is_cjk(ch):
    return bool(CJK_RE.match(ch))


def classify_spaces(s):
    """返回字符串中所有"疑似不该有"的半角空格 [(index, left, right, reason)]。"""
    out = []
    for i, ch in enumerate(s):
        if ch != " ":
            continue
        left = s[i - 1] if i > 0 else ""
        right = s[i + 1] if i + 1 < len(s) else ""
        if not left or not right:
            continue
        # 唯一放行：英文句子里两个英文字母之间（中文试卷几乎不出现）
        if left.isascii() and right.isascii() and left.isalpha() and right.isalpha():
            continue
        reason = None
        if is_cjk(left) or is_cjk(right):
            reason = "中文/中文标点与相邻字符之间出现空格"
        elif left in MATH_SYMS or right in MATH_SYMS:
            reason = "数学符号与相邻字符之间出现空格"
        elif left.isdigit() and UNIT_RE.match(right):
            reason = "数字与单位之间出现空格"
        elif left in "=+-−*/×" or right in "=+-−*/×":
            reason = "运算符两侧出现空格"
        elif left.isalnum() or right.isalnum():
            reason = "字母/数字相邻处出现空格"
        if reason:
            out.append((i, left, right, reason))
    return out


def paren_filled(s):
    """括号内若被填入非空白内容（疑似手写答案没删干净），返回内容列表。"""
    hits = []
    for m in PAREN_RE.finditer(s):
        inner = m.group(1)
        stripped = inner.replace("\u3000", "").strip()
        if stripped:
            hits.append(inner)
    return hits


def main(path):
    errs, checks, info = [], [], []

    try:
        data = load_extract(path)
    except (OSError, ValueError) as e:
        print("ERR：输入校验失败，禁止交付：\n%s" % e)
        return 1

    root = os.path.dirname(os.path.abspath(path))
    title = data.get("title", "").strip()
    if not title:
        errs.append("缺少试卷标题 title")
    else:
        info.append("标题：%s" % title)

    blocks = data.get("blocks", [])
    sections, qnos = [], []
    current_section = ""
    n_opts_blocks = n_images = n_para = 0
    q_index = 0

    for pos, b in enumerate(blocks):
        typ = b.get("type")
        if typ == "section":
            sections.append(b.get("text", ""))
            current_section = b.get("text", "")
        elif typ == "q":
            q_index += 1
            no = b.get("no")
            text = b.get("text", "")
            try:
                qnos.append(question_number(no))
            except (TypeError, ValueError):
                errs.append("块#%d 题目缺少数字题号 no=%r" % (pos, no))
            loc = "题%s" % no
            if "填空" in current_section and "_" not in text and "＿" not in text:
                checks.append("%s：填空题未见空位下划线，对照原图确认是漏画横线还是被答案替换"
                              % loc)
            # 选项（q 内联 opts）
            opts = b.get("opts")
            if opts is not None:
                n_opts_blocks += 1
                if len(opts) != 4:
                    checks.append("%s：选项数量为 %d（非常见的4个），对照原图确认"
                                  % (loc, len(opts)))
                for item in opts:
                    body = OPT_PREFIX_RE.sub("", item)
                    for (_, _, _, why) in classify_spaces(body):
                        checks.append("%s 选项「%s」：%s" % (loc, item, why))
            # 括号内文字：分值（数字+分）属印刷原文直接放行；其余须对照
            # 原图确认是"印刷注释"还是"误入的手写答案"（脚本无法判定，故为 CHECK）
            for inner in paren_filled(text):
                if re.fullmatch(r"\s*\d+\s*分\s*", inner):
                    continue
                checks.append('%s：括号内有文字「%s」，对照原图确认是印刷原文还是误入答案'
                              % (loc, inner))
            # 疑似空格
            for (i, l, r, why) in classify_spaces(text):
                snippet = text[max(0, i - 6):i + 7]
                checks.append("%s：%s → …%s…" % (loc, why, snippet))
        elif typ == "opts":
            n_opts_blocks += 1
            items = b.get("items", [])
            if len(items) != 4:
                checks.append("块#%d 独立选项块数量为 %d（非常见4个），对照原图确认"
                              % (pos, len(items)))
            for it in items:
                body = OPT_PREFIX_RE.sub("", it)
                for (i, l, r, why) in classify_spaces(body):
                    checks.append("选项「%s」：%s" % (it, why))
        elif typ == "image":
            n_images += 1
            p = b.get("path", "")
            if not p or not os.path.exists(p):
                errs.append("配图文件不存在：%s" % p)
            else:
                size = os.path.getsize(p)
                if size == 0:
                    errs.append("配图为空文件：%s" % p)
                wh = ""
                try:
                    from PIL import Image
                    with Image.open(p) as im:
                        wh = "，尺寸 %dx%d，宽高比 %.3f" % (
                            im.width, im.height, im.width / im.height)
                        im.load()
                except Exception as exc:
                    errs.append("配图无法读取：%s（%s）" % (p, type(exc).__name__))
                info.append("配图 %s（%d KB%s）" % (
                    os.path.basename(p), size // 1024, wh))
        elif typ == "para":
            n_para += 1
            text = b.get("text", "")
            for inner in paren_filled(text):
                pass  # 小问里的括号多为编号，不判答案
            for (i, l, r, why) in classify_spaces(text):
                snippet = text[max(0, i - 6):i + 7]
                checks.append("小问/段落：%s → …%s…" % (why, snippet))

    # 题号连续性（全局应 1..N 不重不漏；若原卷分科编号则人工确认）
    if qnos:
        dup = sorted({x for x in qnos if qnos.count(x) > 1})
        for x in dup:
            errs.append("题号 %d 重复出现" % x)
        expect = set(range(1, max(qnos) + 1))
        missing = sorted(expect - set(qnos))
        if missing:
            checks.append("题号序列缺少 %s（若原卷按大题分别编号请确认，否则是漏题）"
                          % missing)
        info.append("题目总数 %d（题号 %d–%d）" % (len(qnos), min(qnos), max(qnos)))

    info.append("大题分区 %d 个：%s" % (len(sections), " / ".join(sections)))
    info.append("配图 %d 张；选项块 %d 个；小问/段落 %d 段"
                % (n_images, n_opts_blocks, n_para))

    # 填空题应留下空位（下划线 / 括号），仅作信息提示
    print("=" * 64)
    print("机检报告：%s" % path)
    print("=" * 64)
    print("\n【INFO 计数（逐项与原卷对数）】")
    for x in info:
        print("  - " + x)
    print("\n【CHECK 疑似（必须调出原照片逐处确认并记录）】共 %d 处" % len(checks))
    if not checks:
        print("  - 无")
    for x in checks:
        print("  ? " + x)
    print("\n【ERR 确定错误（必须修改）】共 %d 处" % len(errs))
    if not errs:
        print("  - 无")
    for x in errs:
        print("  X " + x)

    print("\n结论：%s。机检不含视觉判断，逐字/逐图/逐页并排核对仍须按"
          "「最严格核对清单」逐项打勾后方可交付。"
          % ("存在 ERR，禁止交付" if errs else "机检项通过"))
    return 1 if errs else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit("usage: verify_extract.py extract.json")
    sys.exit(main(a[0]))
