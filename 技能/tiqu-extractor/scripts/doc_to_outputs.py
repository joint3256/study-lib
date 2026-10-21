#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Word → PDF 与逐页 PNG；依赖 LibreOffice(soffice) 和 pdftoppm。

用法：python3 doc_to_outputs.py file.docx [outdir] [dpi]
每次在 outdir（默认 docx 同目录）中新建 <文档名>-<随机后缀>/：
  <文档名>.pdf
  pages/page-1.png, page-2.png, ...
仅使用本次生成的同名 PDF；不覆盖或清理任何既有输出。
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile


def run(cmd):
    subprocess.run(cmd, check=True)


def main(docx, outdir=None, dpi=150):
    source = Path(docx).resolve()
    if not source.is_file():
        raise FileNotFoundError("Word 文件不存在：%s" % source)
    if type(dpi) is not int or dpi <= 0:
        raise ValueError("dpi 必须为正整数")
    try:
        with zipfile.ZipFile(source) as archive:
            document = ET.fromstring(archive.read("word/document.xml"))
            ET.fromstring(archive.read("[Content_Types].xml"))
        if document.tag != "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document":
            raise ValueError("不是 Word 正文 XML")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ValueError("输入不是有效的 DOCX：%s" % source) from exc
    output = Path(outdir).resolve() if outdir is not None else source.parent
    output.mkdir(parents=True, exist_ok=True)
    # mkdtemp 原子创建独占目录；失败时仅清理本次创建的目录。
    result = Path(tempfile.mkdtemp(prefix=source.stem + "-", dir=output))
    try:
        with tempfile.TemporaryDirectory(prefix="tiqu-soffice-") as profile:
            run(["soffice", "-env:UserInstallation=" + Path(profile).as_uri(),
                 "--headless", "--convert-to", "pdf", "--outdir",
                 str(result), str(source)])
        pdf = result / (source.stem + ".pdf")
        if not pdf.is_file():
            raise RuntimeError("PDF 转换未生成预期文件：%s" % pdf)
        with pdf.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise RuntimeError("生成的 PDF 无效：%s" % pdf)
        imgdir = result / "pages"
        imgdir.mkdir()
        run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(imgdir / "page")])
        pages = [p for p in imgdir.iterdir() if re.fullmatch(r"page-\d+\.png", p.name)]
        pages.sort(key=lambda p: int(p.stem.split("-")[-1]))
        if not pages:
            raise RuntimeError("页面转换未生成 PNG：%s" % imgdir)
        numbers = [int(p.stem.split("-")[-1]) for p in pages]
        if numbers != list(range(1, len(pages) + 1)):
            raise RuntimeError("页面编号不连续：%s" % imgdir)
        for page in pages:
            with page.open("rb") as stream:
                if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                    raise RuntimeError("页面图片无效：%s" % page)
    except BaseException:
        shutil.rmtree(result)
        raise

    print("PDF:", pdf)
    print("pages:", len(pages))
    for page in pages:
        print(page)
    return str(pdf), [str(page) for page in pages]


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: doc_to_outputs.py file.docx [outdir] [dpi]")
    try:
        main(args[0], args[1] if len(args) > 1 else None,
             int(args[2]) if len(args) > 2 else 150)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        sys.exit("转换失败：%s" % exc)
