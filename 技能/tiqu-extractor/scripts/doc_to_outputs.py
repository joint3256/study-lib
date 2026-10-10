#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把"干净原题" Word 转为 PDF，并把 PDF 每页导出为干净页面 PNG（即用户要的
"干净页面导出的图片"）。依赖 LibreOffice(soffice) 与 poppler-utils(pdftoppm)。

用法：python3 doc_to_outputs.py file.docx [outdir] [dpi]
产出（默认在 docx 同目录）：
  _pdf/<同名>.pdf
  pages/page-1.png, page-2.png, ...
"""
import sys
import os
import glob
import subprocess


def run(cmd):
    subprocess.run(cmd, check=True)


def main(docx, outdir=None, dpi=150):
    docx = os.path.abspath(docx)
    outdir = outdir or os.path.dirname(docx)
    base = os.path.splitext(os.path.basename(docx))[0]

    pdfdir = os.path.join(outdir, "_pdf")
    os.makedirs(pdfdir, exist_ok=True)
    run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", pdfdir, docx])
    pdf = os.path.join(pdfdir, base + ".pdf")
    if not os.path.exists(pdf):
        cands = glob.glob(os.path.join(pdfdir, "*.pdf"))
        if not cands:
            sys.exit("PDF conversion failed")
        pdf = cands[0]

    imgdir = os.path.join(outdir, "pages")
    os.makedirs(imgdir, exist_ok=True)
    for f in glob.glob(os.path.join(imgdir, "*.png")):
        os.remove(f)
    prefix = os.path.join(imgdir, "page")
    run(["pdftoppm", "-png", "-r", str(dpi), pdf, prefix])
    pages = sorted(glob.glob(prefix + "*.png"))

    print("PDF:", pdf)
    print("pages:", len(pages))
    for p in pages:
        print(p)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit("usage: doc_to_outputs.py file.docx [outdir] [dpi]")
    main(a[0], a[1] if len(a) > 1 else None,
         int(a[2]) if len(a) > 2 else 150)
