# -*- coding: utf-8 -*-
"""tiqu-extractor 几何重画辅助库（matplotlib）。

用途：把试卷照片里的"印刷几何图"按原图比例重画为干净 PNG；
不用于、也不应保留任何手写内容（手写文字、打勾、草稿、手画辅助线）。

基本用法：
    from fig_helpers import *
    set_outdir("/abs/path/figs")
    fig, ax = newax((-0.5, 5.0), (-0.5, 3.0))
    seg(ax, (0, 0), (4, 0))                 # 一条边
    poly(ax, [(0, 0), (2, 1.8), (4, 0)])    # 三角形
    rmark(ax, D, A, C)                      # D 处直角符号（A、C 为两邻边上的点）
    ang(ax, A, B, C, r=0.4)                 # A 处角弧
    lab(ax, (0, 0), "A", 0, -0.3)           # 点标注
    save(fig, "q01.png")

重画要点：先用 set_aspect("equal") 保证不变形；坐标范围按原图相对比例设定；
印刷的虚线用 seg(..., ls="--")，阴影用 poly(..., fill=True)。
"""
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Polygon

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "SimSun", "Songti SC", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"
plt.rcParams["axes.unicode_minus"] = False

BLK = "#222222"   # 印刷主线/字
GRY = "#666666"   # 印刷辅助/虚线
SH = "#9CC3E5"    # 浅蓝阴影（如试卷有阴影区域）

_OUT = "."


def set_outdir(d):
    """设置干净配图的输出目录。"""
    global _OUT
    _OUT = d
    os.makedirs(d, exist_ok=True)


def newax(xlim, ylim, figsize=None):
    """新建等比例、无坐标轴的画布。figsize 英寸，默认按坐标跨度估算。"""
    w = (xlim[1] - xlim[0])
    h = (ylim[1] - ylim[0])
    fs = figsize or (max(3.2, w * 1.15), max(2.6, h * 1.15))
    fig, ax = plt.subplots(figsize=fs)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def seg(ax, p, q, ls="-", lw=1.5, c=BLK, z=2):
    """画线段 p→q；ls="--" 为印刷虚线。"""
    ax.plot([p[0], q[0]], [p[1], q[1]], ls=ls, lw=lw, c=c, zorder=z,
            solid_capstyle="round")


def poly(ax, pts, fill=False, fc=SH, ec=BLK, lw=1.5, alpha=0.55, z=1):
    """画闭合多边形；fill=True 时填充（试卷阴影区域）。"""
    if fill:
        ax.add_patch(Polygon(pts, closed=True, facecolor=fc, edgecolor="none",
                             alpha=alpha, zorder=z))
    for i in range(len(pts)):
        seg(ax, pts[i], pts[(i + 1) % len(pts)], lw=lw, c=ec, z=z + 1)


def lab(ax, p, t, dx=0, dy=0, ha="center", va="center", fs=15, c=BLK, weight="normal"):
    """在点 p 附近偏移 (dx,dy) 标注文字 t（点字母、角度值等）。"""
    ax.annotate(t, xy=p, xytext=(p[0] + dx, p[1] + dy), ha=ha, va=va,
                fontsize=fs, color=c, weight=weight,
                arrowprops=dict(arrowstyle="-", lw=0))


def rmark(ax, p, u, v, s=0.22, c=BLK):
    """在 p 处画直角符号；u、v 为直角两条边上的任意点。"""
    p = np.array(p, float)
    u = np.array(u, float) - p
    v = np.array(v, float) - p
    u /= np.hypot(*u)
    v /= np.hypot(*v)
    q1 = p + s * u
    q2 = p + s * u + s * v
    q3 = p + s * v
    ax.plot([q1[0], q2[0], q3[0]], [q1[1], q2[1], q3[1]], lw=1.2, c=c, zorder=3)


def ang(ax, p, q1, q2, r=0.4, c=BLK, lw=1.2):
    """在 p 处画角弧，角由射线 p→q1、p→q2 张成。"""
    p = np.array(p, float)
    a1 = math.degrees(math.atan2(q1[1] - p[1], q1[0] - p[0]))
    a2 = math.degrees(math.atan2(q2[1] - p[1], q2[0] - p[0]))
    ax.add_patch(Arc(p, 2 * r, 2 * r, angle=0, theta1=min(a1, a2),
                     theta2=max(a1, a2), lw=lw, color=c, zorder=3))


def tick(ax, p, u, v, s=0.12, c=BLK):
    """在线段上画全等记号（单短划）；p 为标记点，u、v 为该线段两端点。"""
    p = np.array(p, float)
    d = np.array(v, float) - np.array(u, float)
    d = d / np.hypot(*d)
    n = np.array([-d[1], d[0]])
    seg(ax, p - s * n + 0.0 * d, p + s * n, lw=1.3, c=c)


def save(fig, name):
    """保存为干净 PNG（白底、200dpi、紧凑边距），输出到 set_outdir 设定目录。"""
    fig.savefig(os.path.join(_OUT, name), dpi=200, bbox_inches="tight",
                facecolor="white", pad_inches=0.08)
    plt.close(fig)
