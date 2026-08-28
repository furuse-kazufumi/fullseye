# -*- coding: utf-8 -*-
"""事例: 部品内部の「保証できる最大の中実ブロック」を最大内接ボックスで測る (metrology).

平たく言うと: スキャンした部品(二値ボクセル)の中に空洞や欠陥があるとき、「ここは確実に
中身が詰まっている」と言い切れる最大の直方体はどこか — 穴あけ・部品埋め込み・強度保証の
基準になる。これは 2-D の ``inner_rectangle1``(領域に内接する最大の軸平行長方形)の 3-D 版
= **最大内接ボックス**。座標は (depth, row, col)。

``regionprops3d.inner_box3`` は厳密解を返す: どの深さ区間 [z0,z1] でも、ボックスはその区間の
全スライスの**論理積**(全スライスで前景のボクセル)に内接せねばならない。各区間で最大内接
2-D 長方形(``inner_rectangle1`` と同じヒストグラム法)を解き、× 区間長 の最大を取る。

検証(GT): 既知の中実ブロックの内部に既知の空洞(ノッチ)を空けた小さめの領域で、inner_box3 の
体積が総当たり(全部分ボックスを走査した厳密最大)と**完全一致**することを確認する。

beat-the-null: 「前景全体のバウンディングボックス」を中実ブロックとみなす素朴な見積りは、空洞を
またいで**空洞を含んでしまう**(実際には中実でない)。inner_box3 が返すボックスは全ボクセルが
前景であることを assert で確かめ、素朴なバウンディングボックス体積より確実に小さい(=空洞を
避けた保証領域)ことを判別的に示す。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import regionprops3d as rp


def prefix_box_sum(V):
    """3-D 積分画像(prefix sum)。任意の軸平行ボックス内の前景数を O(1) で引くため。"""
    D, H, W = V.shape
    P = np.zeros((D + 1, H + 1, W + 1), np.int64)
    P[1:, 1:, 1:] = np.cumsum(np.cumsum(np.cumsum(V.astype(np.int64), 0), 1), 2)
    return P


def box_sum(P, z0, z1, y0, y1, x0, x1):
    return int(P[z1 + 1, y1 + 1, x1 + 1] - P[z0, y1 + 1, x1 + 1] - P[z1 + 1, y0, x1 + 1]
               - P[z1 + 1, y1 + 1, x0] + P[z0, y0, x1 + 1] + P[z0, y1 + 1, x0]
               + P[z1 + 1, y0, x0] - P[z0, y0, x0])


def brute_force_max_box(V):
    """全部分ボックスを走査して「全前景の最大軸平行ボックス」の体積を返す(厳密・小領域用)。"""
    D, H, W = V.shape
    P = prefix_box_sum(V)
    best = 0
    for z0 in range(D):
        for z1 in range(z0, D):
            for y0 in range(H):
                for y1 in range(y0, H):
                    for x0 in range(W):
                        for x1 in range(x0, W):
                            vv = (z1 - z0 + 1) * (y1 - y0 + 1) * (x1 - x0 + 1)
                            if vv > best and box_sum(P, z0, z1, y0, y1, x0, x1) == vv:
                                best = vv
    return best


# --- 1) 内部に空洞のある中実ブロック(スキャン部品を模す) ------------------
V = np.zeros((7, 9, 9), bool)
V[1:6, 1:8, 1:8] = True                   # 中実ブロック (5,7,7)
V[2:4, 3:6, 3:6] = False                  # 内部の空洞(欠陥)

# --- 2) 実 op: 最大内接ボックス ------------------------------------------
r = rp.inner_box3(V)
z0, y0, x0 = r["min"].astype(int)
dz, dy, dx = r["size"].astype(int)

# --- 3) GT: 総当たりの厳密最大と一致 --------------------------------------
bf = brute_force_max_box(V)
print(f"inner_box3 体積          : {r['volume']:.0f}  (size {r['size'].astype(int).tolist()} @ min {r['min'].astype(int).tolist()})")
print(f"総当たり厳密最大         : {bf}")
assert r["volume"] == bf, f"厳密最大と一致しない: {r['volume']} vs {bf}"

# 返ってきたボックスが本当に全前景(中実)であること
assert V[z0:z0 + dz, y0:y0 + dy, x0:x0 + dx].all(), "内接ボックスが空洞を含んでしまっている"

# beat-the-null: 前景全体のバウンディングボックスは空洞をまたぐ(中実でない)
occ = np.argwhere(V)
bbox_size = occ.max(0) - occ.min(0) + 1
bbox_vol = float(np.prod(bbox_size))
bbox_all_solid = V[occ.min(0)[0]:occ.max(0)[0] + 1,
                   occ.min(0)[1]:occ.max(0)[1] + 1,
                   occ.min(0)[2]:occ.max(0)[2] + 1].all()
print(f"前景bbox 体積 (null)     : {bbox_vol:.0f}  (全中実? {bbox_all_solid})")
assert not bbox_all_solid, "この例の前提が崩れる(bbox が空洞を含まない)"
assert r["volume"] < bbox_vol, f"内接ボックスが null bbox 以上: {r['volume']} vs {bbox_vol}"

print(f"PASS: 最大内接ボックス(体積 {r['volume']:.0f})が総当たり厳密最大と一致し、全ボクセルが中実。"
      f"空洞をまたぐ前景bbox(体積 {bbox_vol:.0f}・非中実)を判別的に下回る = 保証できる最大の中実ブロック")
