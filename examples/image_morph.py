# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""image_morph — 2人の顔の「中間の顔」を作り、比率を段階的に変えて見せる。

    py -3.11 examples/image_morph.py            # GT検証(数値)だけ
    py -3.11 examples/image_morph.py --save out.png  # モーフ列の画像も保存(matplotlib)

【この例が解く問題】
2枚の顔画像 A, B の「中間」を作りたい。単純な半透明合成(alpha ブレンド)は
目や鼻の位置がズレたまま重なって二重像(ゴースト)になり、"中間の顔" に見えない。
:mod:`imagemorph` は対応点(ランドマーク)で特徴を中間形状へワープしてから
ディゾルブするので、特徴が 1 つに揃った本物の中間顔になる(Beier & Neely 1992)。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 端点: morph(alpha=0)==A, morph(alpha=1)==B(最大差 ~1e-13)。
2. 中点整列(beat-the-null): alpha=0.5 で、目マーカーが「単一」で中点に来る。
   一方 naive blend は「二重」に見える → 連結成分数 morph=1 / blend=2 で判別。
3. 単調性: モーフ列で目の中心 x が A の位置から B の位置へ単調移動する。

対応点は本例では既知(合成顔なので真値がある)。実写では手動指定 or 顔ランドマーク
検出器(dlib/mediapipe = optional な重い依存)を使う。ワープ/モーフの核は対応点さえ
あれば顔に限らず動く汎用op(登録・データ拡張・テンプレート整列にも使える)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imagemorph as M  # noqa: E402

H = W = 200


def _ell(cx, cy, rw, rh):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((xx - cx) / rw) ** 2 + ((yy - cy) / rh) ** 2 <= 1.0


def _thick(pts, r=2):
    m = np.zeros((H, W), bool)
    for x, y in pts:
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < W and 0 <= yi < H:
            m[yi, xi] = True
    return ndimage.binary_dilation(m, iterations=r)


def synth_face(p):
    """パラメトリックな合成顔(RGB)と、その真のランドマーク (x,y) を返す。"""
    img = np.ones((H, W, 3)) * np.array([0.93, 0.93, 0.96])
    cx, cy = 100, p["cy"]
    img[_ell(cx, cy, p["fw"], p["fh"])] = p["skin"]
    ey = cy - p["fh"] * 0.12
    for sx in (-1, 1):
        exc = cx + sx * p["eye_dx"]
        img[_ell(exc, ey, p["eye_r"] * 1.4, p["eye_r"])] = [1, 1, 1]
        img[_ell(exc, ey, p["eye_r"] * 0.5, p["eye_r"] * 0.5)] = [0.08, 0.08, 0.12]
    ny = cy + p["nose_len"]
    img[_thick(zip(np.full(16, cx), np.linspace(ey + p["eye_r"], ny, 16)), 1)] = np.array(p["skin"]) * 0.7
    my = cy + p["fh"] * 0.45
    mx = np.linspace(cx - p["mouth_w"], cx + p["mouth_w"], 40)
    myv = my - p["smile"] * (1 - ((mx - cx) / p["mouth_w"]) ** 2)
    img[_thick(zip(mx, myv), 2)] = [0.6, 0.15, 0.15]
    img = ndimage.gaussian_filter(img, sigma=(0.7, 0.7, 0), mode="nearest").clip(0, 1)
    lm = np.array([
        [cx - p["eye_dx"], ey], [cx + p["eye_dx"], ey], [cx, ny],
        [cx - p["mouth_w"], my], [cx + p["mouth_w"], my],
        [cx, cy + p["fh"]], [cx, cy - p["fh"]],
        [cx - p["fw"], cy], [cx + p["fw"], cy],
    ], float)
    return img, lm


FACE_A = dict(cy=98, fw=52, fh=66, skin=[0.95, 0.80, 0.66], eye_dx=20, eye_r=7,
              nose_len=14, mouth_w=18, smile=10)
FACE_B = dict(cy=104, fw=66, fh=60, skin=[0.72, 0.54, 0.42], eye_dx=30, eye_r=10,
              nose_len=8, mouth_w=27, smile=-6)


def main(save=None):
    A, lmA = synth_face(FACE_A)
    B, lmB = synth_face(FACE_B)
    print("2つの合成顔を生成(目間隔/顔幅/口/肌色が異なる)。ランドマーク %d 点。" % len(lmA))

    # 1) 端点
    m0 = M.morph(A, B, lmA, lmB, 0.0, method="tps", lam=1.0)
    m1 = M.morph(A, B, lmA, lmB, 1.0, method="tps", lam=1.0)
    e0, e1 = float(np.abs(m0 - A).max()), float(np.abs(m1 - B).max())
    print(f"端点   : |morph(0)-A|={e0:.2e}  |morph(1)-B|={e1:.2e}")
    assert e0 < 1e-6 and e1 < 1e-6, "端点がA/Bに一致しない"

    # 2) 中点整列 vs 素朴ブレンド(beat-the-null)。目だけの明マーカーで連結成分を数える。
    eyeA = np.zeros((H, W)); eyeB = np.zeros((H, W))
    for exc in (100 - FACE_A["eye_dx"], 100 + FACE_A["eye_dx"]):
        eyeA[int(FACE_A["cy"] - FACE_A["fh"] * 0.12) - 3:int(FACE_A["cy"] - FACE_A["fh"] * 0.12) + 4, exc - 3:exc + 4] = 1
    for exc in (100 - FACE_B["eye_dx"], 100 + FACE_B["eye_dx"]):
        eyeB[int(FACE_B["cy"] - FACE_B["fh"] * 0.12) - 3:int(FACE_B["cy"] - FACE_B["fh"] * 0.12) + 4, exc - 3:exc + 4] = 1
    lmA_eye = lmA[:2]; lmB_eye = lmB[:2]
    mh = M.morph(eyeA, eyeB, lmA_eye, lmB_eye, 0.5, method="affine")
    bl = M.blend(eyeA, eyeB, 0.5)
    _, n_m = ndimage.label(mh > 0.25)
    _, n_b = ndimage.label(bl > 0.25)
    print(f"中点   : モーフの目マーカー連結成分={n_m}(揃って単一) / 素朴ブレンド={n_b}(二重=ゴースト)")
    assert n_m == 2 and n_b == 4, \
        f"判別に失敗(morph目数={n_m} 期待2 / blend目数={n_b} 期待4)"

    # 3) 単調性: 片目マーカーの x 中心がモーフ列で A -> B へ単調移動
    a1 = np.zeros((H, W)); b1 = np.zeros((H, W))
    a1[95:101, 60:66] = 1.0   # A の左目あたり
    b1[95:101, 120:126] = 1.0  # B の左目あたり(より外側)
    seq = M.morph_sequence(a1, b1, np.array([[63, 98]], float), np.array([[123, 98]], float), n=5)
    xs = [np.where(im > 0.5)[1].mean() for im in seq]
    print(f"単調性 : 目 x 中心 = {[round(x, 1) for x in xs]}(A={xs[0]:.0f} → B={xs[-1]:.0f})")
    assert xs[0] < xs[2] < xs[-1], "モーフ列で特徴が単調移動していない"

    print("\nPASS: モーフは端点でA/Bに厳密一致し、中点で特徴を単一像に揃える"
          "(素朴ブレンドは二重像)。段階的な比率で滑らかに中間顔へ遷移する。")

    if save:
        _save_figure(A, B, lmA, lmB, bl, save)
    return 0


def _save_figure(A, B, lmA, lmB, blend_half, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
    seq = [M.morph(A, B, lmA, lmB, a, method="tps", lam=1.0) for a in alphas]
    fig, ax = plt.subplots(1, 5, figsize=(15, 3.4))
    for a, im, al in zip(ax, seq, alphas):
        a.imshow(im); a.set_title(f"α={al:.2f}"); a.axis("off")
    plt.suptitle("Feature-based face morph — warp to mid-shape THEN dissolve")
    plt.tight_layout(); plt.savefig(path, dpi=90, bbox_inches="tight"); plt.close()
    print(f"saved: {path}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None, help="モーフ列の画像を保存するパス(matplotlib)")
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
