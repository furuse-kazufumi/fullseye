"""エッジモデルのピラミッド — 「モデルを間引く」対「各階層で作り直す」。

一次ソースで確認した HALCON の設計(inspect_shape_model のドキュメント
https://www.mvtec.com/doc/halcon/2605/en/inspect_shape_model.html):

  ModelImages  = 入力画像のイメージピラミッド
  ModelRegions = 各ピラミッド階層でのモデル領域(その階層でモデルを表す領域)
  モデルの抽出は「ヒステリシス閾値法に似た方法」で **各階層ごとに** 行う

つまり **ピラミッドを作っているのは画像であって、モデルではない。**
モデルは各階層で作り直している。

pyramid_gate.py の測定と噛み合う: 「モデル点数を間引く」軸は細線で壊れたが、
HALCON はそれをやっていない。ここでエッジモデルを使って両者を直接比べる。

スコアは勾配方向の一致度(Steger 流): モデル点での勾配方向と画像の勾配方向の
内積の絶対値の平均。
"""
from __future__ import annotations

import numpy as np

import pyramid_gate as PG


def grad(a):
    gy, gx = np.gradient(a.astype(float))
    m = np.hypot(gx, gy)
    return gx, gy, m


def edge_model(patch, frac=0.25):
    """勾配の強い点をモデル点にする(ヒステリシス閾値の粗い代用)。"""
    gx, gy, m = grad(patch)
    if m.max() < 1e-9:
        return None
    thr = np.quantile(m, 1.0 - frac)
    ys, xs = np.nonzero(m >= max(thr, 1e-9))
    if ys.size < 4:
        return None
    d = np.column_stack([gx[ys, xs], gy[ys, xs]])
    d = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    return ys, xs, d


def score(model, img, r, c):
    if model is None:
        return -1.0
    ys, xs, d = model
    gx, gy, m = grad(img)
    yy = np.clip(r + ys, 0, img.shape[0] - 1)
    xx = np.clip(c + xs, 0, img.shape[1] - 1)
    e = np.column_stack([gx[yy, xx], gy[yy, xx]])
    n = np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-9)
    return float(np.abs((e / n * d).sum(1)).mean())


def box2(a):
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    return a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean((1, 3))


def scene(size=128, seed=0, target="thin"):
    rng = np.random.default_rng(seed)
    img = rng.normal(0, 0.12, (size, size))
    img[30:34, 10:110] += 1.4
    img[60:61, 10:110] += 1.4                  # 1 px の細線
    img[80:110, 40:44] += 1.4
    if target == "thin":
        box, anchors = (57, 63, 50, 70), ((57, 50), (28, 50), (78, 40))
    else:
        box, anchors = (28, 36, 50, 70), ((28, 50), (57, 50), (78, 40))
    return img, box, anchors


def run(target="thin", size=128):
    img, (r0, r1, c0, c1) = scene(size=size, target=target)[:2]
    anchors = scene(size=size, target=target)[2]
    th, tw = r1 - r0, c1 - c0
    tpl = img[r0:r1, c0:c1]
    full = edge_model(tpl)

    pos = []
    for (a, b) in anchors:
        for dr in (-3, -2, -1, 0, 1, 2, 3):
            for dc in (-4, -2, 0, 2, 4):
                pos.append((max(0, min(size - th, a + dr)),
                            max(0, min(size - tw, b + dc))))

    def fine(rc):
        return score(full, img, rc[0], rc[1])

    # (A) 全解像度でモデルを作り、**モデル点を間引く**
    def coarse_thin_model(rc):
        if full is None:
            return -1.0
        ys, xs, d = full
        k = slice(None, None, 4)
        return score((ys[k], xs[k], d[k]), img, rc[0], rc[1])

    # (B) **画像を面積平均で縮小し、その階層でモデルを作り直す**(HALCON の流儀)
    img2 = box2(img)
    tpl2 = box2(tpl)
    m2 = edge_model(tpl2)

    def coarse_rebuild(rc):
        return score(m2, img2, rc[0] // 2, rc[1] // 2)

    return {"(A) モデル点を間引く": PG.check(coarse_thin_model, fine, pos),
            "(B) 各階層で作り直す": PG.check(coarse_rebuild, fine, pos)}


def main():
    print("エッジモデルのピラミッド — モデルを間引く 対 各階層で作り直す")
    print("スコア = 勾配方向の一致度(Steger 流)")
    for t, lab in (("thick", "太い棒(4 px)"), ("thin", "**細い線(1 px)**")):
        print(f"\n=== {lab} をモデルにする ===")
        for name, r in run(target=t).items():
            print("")
            print(r.report(name))


if __name__ == "__main__":
    main()
