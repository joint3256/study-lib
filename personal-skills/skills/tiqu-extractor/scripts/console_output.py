"""CLI 报告保留终端编码，并转义终端无法显示的字符。"""

import sys


def configure_stdout():
    """仅供 CLI 入口调用，不修改文件内容、路径或导入者的输出设置。"""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="backslashreplace")
