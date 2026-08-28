# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_color_artistic — 色 / 芸術 / 拡張(sim2real) / その他ライブラリ の 2次元オペレータ一族を一括実演・自己検証する(task: gallery/contract-verify)。

    py -3.11 examples/gallery2d_color_artistic.py

【平たく言うと(この一族は何のため)】
この例が回すのは registry の中でカテゴリが color / artistic / augmentation / extra の
オペレータ全部です。役割で言うと4系統:
  - color      : RGB(HxWx3)を第一級 sort として扱う HALCON 色オペレータ(色空間変換・
                 チャンネル混合・PCA・輝度化・チャンネル取り出し。Bayer デモザイクで
                 image → color へ橋渡し)。
  - artistic   : 非写実(NPR)フィルタ(OpenCV stylization / pencil sketch、PIL emboss)。
  - augmentation: 実カメラの劣化を合成する sim-to-real / ドメインランダム化
                 (ショット/読み出し/固定パターンノイズ、モーションブラー、周辺減光、
                 色収差、ローリングシャッター、JPEG ブロック、cutout、樽型歪み)。
  - extra      : 他ライブラリ(SimpleITK)由来で HALCON に無い曲率フロー拡散・再構成
                 モルフォロジ・領域拡張/エントロピー閾値など。

【グラウンドトゥルース(数値で嘘を弾く)】
一族の *全* オペを実際に呼び、各オペについて:
  (1) 有限性 … NaN/Inf を出さない、
  (2) 型 / sort … 宣言 out_sort に一致(image/region → [0,1] の 2次元 float、
      color → HxWx3 の [0,1]、region → {0,1} の二値)、
  (3) 決定性 … 同一入力で bit 完全一致(拡張ノイズ系も knob 由来シードで再現可能)、
を assert する。さらに効果が既知の代表オペ8件には「beat-the-null」を含む強い
GT を課す(ブラーは分散を下げる/周辺減光は隅が中心より暗い/閾値は二値かつ前景背景を
分離する/輝度化は 0.299R+0.587G+0.114B と厳密一致 など)。オペが例外を投げたら
静かにスキップせず OPS 一覧との差分で loud に落とす。全 GT を通れば PASS を印字して exit 0。

入力は本例内の input_for(sort) が自前生成する(tests/conftest.py の入力バンクを複製、
examples は tests/ から import しない規約のため)。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402


# --------------------------------------------------------------------------- #
# 入力ファクトリ — tests/conftest.py の per-sort バンクを複製(examples は       #
# tests/ から import しない規約)。各呼び出しで新しい配列を返す(オペの in-place   #
# 変更が次の呼び出しへ漏れないように)。                                          #
# --------------------------------------------------------------------------- #
_N = 48


def _image(n: int = _N) -> np.ndarray:
    """conftest image_bank()['normal']: 勾配 + ディスク + 市松 + 微小ノイズ。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    noise = 0.03 * np.random.default_rng(20260812).standard_normal((n, n))
    return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0.0, 1.0)


def _region(n: int = _N) -> np.ndarray:
    """conftest region_bank()['disk']: 中心の充填ディスク(二値)。"""
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)


def _color(n: int = _N) -> np.ndarray:
    """conftest color_bank()['normal']: グレー像を 3 チャンネルへ重ねた HxWx3。"""
    g = _image(n)
    return np.clip(np.stack([g, 0.7 * g + 0.1, 1.0 - g], -1), 0.0, 1.0)


def input_for(sort: str) -> np.ndarray:
    """オペの in_sort に合う妥当な入力を新規生成して返す。"""
    if sort == "image":
        return _image()
    if sort == "region":
        return _region()
    if sort == "color":
        return _color()
    raise ValueError(f"input_for: このギャラリーが想定しない in_sort={sort!r}")


# --------------------------------------------------------------------------- #
# TARGET オペ集合 — registry のカテゴリ color / artistic / augmentation / extra   #
# を成す 35 オペ。op→example 逆引きインデックス用に、名前を文字列リテラルで        #
# そのまま列挙する(len(OPS) は step1 の TARGET 件数と一致しなければならない)。     #
# --------------------------------------------------------------------------- #
OPS = [
    # --- color (8): HxWx3 を第一級 sort とする HALCON 色オペ ---
    "cfa_to_rgb",            # image  -> color : Bayer デモザイク(色 sort への橋渡し)
    "trans_from_rgb",        # color  -> color : RGB -> HSV/Lab/YUV/XYZ
    "trans_to_rgb",          # color  -> color : HSV -> RGB(逆変換)
    "linear_trans_color",    # color  -> color : 3x3 チャンネル混合
    "principal_comp",        # color  -> color : 3 チャンネルの PCA
    "rgb1_to_gray",          # color  -> image : 輝度化
    "rgb3_to_gray",          # color  -> image : 輝度化(別名エントリ)
    "access_channel",        # color  -> image : 1 チャンネル取り出し
    # --- artistic (3): 非写実(NPR)フィルタ ---
    "xcv_stylization",       # image  -> image : OpenCV stylization
    "xcv_pencil_sketch",     # image  -> image : OpenCV pencil sketch
    "xpil_emboss",           # image  -> image : PIL EMBOSS
    # --- extra (14): SimpleITK 由来(HALCON に無い)---
    "xsitk_curvature_flow",      # image  -> image : 曲率フロー平滑化
    "xsitk_minmax_curv_flow",    # image  -> image : min/max 曲率フロー
    "xsitk_curv_aniso_diff",     # image  -> image : 曲率異方性拡散
    "xsitk_laplacian_sharpen",   # image  -> image : ラプラシアン鮮鋭化
    "xsitk_grayscale_fillhole",  # image  -> image : グレースケール穴埋め
    "xsitk_grayscale_grindpeak", # image  -> image : グレースケールピーク削り
    "xsitk_opening_by_recon",    # image  -> image : 再構成オープニング
    "xsitk_closing_by_recon",    # image  -> image : 再構成クロージング
    "xsitk_signed_maurer_dist",  # region -> image : 符号付き Maurer 距離場
    "xsitk_connected_threshold", # image  -> region: 連結閾値領域拡張
    "xsitk_confidence_connected",# image  -> region: 信頼度連結領域拡張
    "xsitk_maxentropy_thresh",   # image  -> region: 最大エントロピー閾値
    "xsitk_moments_thresh",      # image  -> region: モーメント保存閾値
    "xsitk_huang_thresh",        # image  -> region: Huang 閾値
    # --- augmentation (10): 実カメラ劣化の合成(sim-to-real)---
    "aug_shot_noise",        # image  -> image : ポアソン(光子)ショットノイズ
    "aug_read_noise",        # image  -> image : ガウス読み出しノイズ
    "aug_fixed_pattern",     # image  -> image : 固定パターンノイズ(FPN/PRNU)
    "aug_motion_blur",       # image  -> image : 線形モーションブラー
    "aug_vignette",          # image  -> image : cos^4 周辺減光
    "aug_chromatic",         # image  -> image : 横色収差プロキシ
    "aug_rolling_shutter",   # image  -> image : ローリングシャッター歪み
    "aug_jpeg_blocks",       # image  -> image : JPEG ブロック/リンギング
    "aug_cutout",            # image  -> image : cutout / random erasing
    "aug_barrel",            # image  -> image : 樽型/糸巻き型レンズ歪み
]

# 汎用ループで使う knob(拡張系が恒等写像に潰れない活性値)。
_A, _B = 0.6, 0.4
_TOL = 1e-6


def _assert_finite(name: str, out) -> None:
    arr = np.asarray(out)
    if not np.all(np.isfinite(arr)):
        raise AssertionError(f"{name}: 出力に NaN/Inf が含まれる(有限性違反)")


def _assert_typed(name: str, out, out_sort: str) -> None:
    """宣言 out_sort に一致する型 / 値域か確認。"""
    if out_sort == "image":
        if not (isinstance(out, np.ndarray) and out.ndim == 2 and out.dtype.kind == "f"):
            raise AssertionError(f"{name}: image は 2次元 float 配列であるべき(得: {type(out)}, "
                                 f"ndim={getattr(out, 'ndim', None)})")
        lo, hi = float(out.min()), float(out.max())
        if lo < -_TOL or hi > 1.0 + _TOL:
            raise AssertionError(f"{name}: image は [0,1] に収まるべき(得: [{lo:.4g},{hi:.4g}])")
    elif out_sort == "region":
        if not (isinstance(out, np.ndarray) and out.ndim == 2):
            raise AssertionError(f"{name}: region は 2次元配列であるべき(得: {type(out)})")
        uniq = np.unique(out)
        if not np.all((uniq == 0.0) | (uniq == 1.0)):
            raise AssertionError(f"{name}: region は二値 {{0,1}} であるべき(得の一意値: {uniq[:6]})")
    elif out_sort == "color":
        if not (isinstance(out, np.ndarray) and out.ndim == 3 and out.shape[-1] == 3
                and out.dtype.kind == "f"):
            raise AssertionError(f"{name}: color は HxWx3 float 配列であるべき(得の shape: "
                                 f"{getattr(out, 'shape', None)})")
        lo, hi = float(out.min()), float(out.max())
        if lo < -_TOL or hi > 1.0 + _TOL:
            raise AssertionError(f"{name}: color は [0,1] に収まるべき(得: [{lo:.4g},{hi:.4g}])")
    else:
        raise AssertionError(f"{name}: このギャラリーが想定しない out_sort={out_sort!r}")


def _assert_deterministic(name: str, op, in_sort: str) -> None:
    """同一入力での 2 回呼び出しが bit 完全一致すること。"""
    o1 = op.fn(input_for(in_sort), _A, _B)
    o2 = op.fn(input_for(in_sort), _A, _B)
    if not np.array_equal(np.asarray(o1), np.asarray(o2)):
        raise AssertionError(f"{name}: 決定性違反 — 同一入力で 2 回の出力が一致しない")


# --------------------------------------------------------------------------- #
# 強い GT(効果が既知の代表オペ。beat-the-null 付き)。                            #
# 各関数は説明を返し、GT が破れれば AssertionError で loud に落ちる。              #
# --------------------------------------------------------------------------- #
def gt_motion_blur() -> str:
    inp = input_for("image")
    out = ops._BY_NAME["aug_motion_blur"].fn(inp.copy(), 0.6, 0.3)
    v_in, v_out = float(np.var(inp)), float(np.var(out))
    # beat-the-null: 平均化フィルタは高周波を潰す → 分散が明確に下がる(恒等なら下がらない)。
    if not (v_out < 0.9 * v_in):
        raise AssertionError(f"aug_motion_blur: ブラーは分散を下げるはず(in={v_in:.5f} out={v_out:.5f})")
    return f"aug_motion_blur: 分散 {v_in:.4f} -> {v_out:.4f}(ブラーで減少)"


def gt_vignette() -> str:
    one = np.ones((_N, _N), np.float64)  # 一様輝度なら出力=透過率そのもの
    out = ops._BY_NAME["aug_vignette"].fn(one.copy(), 1.0, 0.5)
    center = float(out[_N // 2, _N // 2])
    corner = float(out[0, 0])
    # beat-the-null: 恒等なら隅=中心=1。cos^4 減光なら隅が中心より暗い。
    if not (corner < 0.5 * center):
        raise AssertionError(f"aug_vignette: 隅は中心より暗いはず(center={center:.4f} corner={corner:.4f})")
    return f"aug_vignette: 中心 {center:.3f} > 隅 {corner:.3f}(cos^4 減光)"


def gt_cutout() -> str:
    inp = input_for("image")
    out = ops._BY_NAME["aug_cutout"].fn(inp.copy(), 0.4, 0.3)  # b<=0.5 -> 黒で消去
    z_in, z_out = int((inp == 0.0).sum()), int((out == 0.0).sum())
    # beat-the-null: 矩形パッチを 0 で消すので零画素が明確に増える。
    if not (z_out > z_in + 100):
        raise AssertionError(f"aug_cutout: 消去で零画素が増えるはず(in={z_in} out={z_out})")
    return f"aug_cutout: 零画素 {z_in} -> {z_out}(矩形オクルージョン)"


def gt_maxentropy_thresh() -> str:
    inp = input_for("image")
    out = ops._BY_NAME["xsitk_maxentropy_thresh"].fn(inp.copy(), 0.5, 0.4)
    uniq = np.unique(out)
    mean = float(out.mean())
    if not np.all((uniq == 0.0) | (uniq == 1.0)):
        raise AssertionError(f"xsitk_maxentropy_thresh: 出力は二値であるべき(一意値={uniq[:6]})")
    # beat-the-null: 前景も背景も存在(全 0 / 全 1 の自明解でない)。
    if not (0.0 < mean < 1.0):
        raise AssertionError(f"xsitk_maxentropy_thresh: 前景/背景を分離すべき(前景率={mean:.4f})")
    return f"xsitk_maxentropy_thresh: 二値・前景率 {mean:.3f}(0/1 双方が存在=分離成立)"


def gt_signed_maurer_dist() -> str:
    reg = input_for("region")  # 中心ディスク
    out = ops._BY_NAME["xsitk_signed_maurer_dist"].fn(reg.copy(), 0.5, 0.4)
    center = float(out[_N // 2, _N // 2])  # ディスク内部
    corner = float(out[0, 0])              # ディスク外部
    # 符号付き距離(内部<0.5<外部): 内部が中点0.5より小、外部が0.5より大。
    if not (center < 0.5 < corner):
        raise AssertionError(f"xsitk_signed_maurer_dist: 内部<0.5<外部 のはず"
                             f"(center={center:.4f} corner={corner:.4f})")
    return f"xsitk_signed_maurer_dist: 内部 {center:.3f} < 0.5 < 外部 {corner:.3f}(符号付き距離)"


def gt_rgb1_to_gray() -> str:
    col = input_for("color")
    out = ops._BY_NAME["rgb1_to_gray"].fn(col.copy(), 0.5, 0.4)
    expected = 0.299 * col[..., 0] + 0.587 * col[..., 1] + 0.114 * col[..., 2]
    if not np.allclose(out, expected, atol=1e-12):
        raise AssertionError("rgb1_to_gray: 輝度 0.299R+0.587G+0.114B と厳密一致すべき")
    return "rgb1_to_gray: 出力 = 0.299R+0.587G+0.114B(厳密一致)"


def gt_access_channel() -> str:
    col = input_for("color")
    ch0 = ops._BY_NAME["access_channel"].fn(col.copy(), 0.0, 0.0)  # a=0 -> ch0
    ch2 = ops._BY_NAME["access_channel"].fn(col.copy(), 1.0, 0.0)  # a=1 -> ch2
    if not (np.array_equal(ch0, col[..., 0]) and np.array_equal(ch2, col[..., 2])):
        raise AssertionError("access_channel: knob a で選んだチャンネルを厳密に取り出すべき")
    # beat-the-null: 別チャンネルは実際に別内容(ここでは ch0 と ch2 は 1-g と g で反転関係)。
    if np.array_equal(ch0, ch2):
        raise AssertionError("access_channel: ch0 と ch2 が同一 — チャンネル選択が効いていない")
    return "access_channel: a=0->ch0 / a=1->ch2 を厳密取り出し(別チャンネルは別内容)"


def gt_emboss_edge_response() -> str:
    flat = np.full((_N, _N), 0.42, np.float64)  # 平坦面
    textured = input_for("image")               # エッジ/市松/ディスクを含む
    emb = ops._BY_NAME["xpil_emboss"]
    v_flat = float(np.var(emb.fn(flat.copy(), 0.5, 0.4)))
    v_tex = float(np.var(emb.fn(textured.copy(), 0.5, 0.4)))
    # beat-the-null: emboss はエッジに応答。平坦面は一様(分散≈0)、エッジ有りは分散大。
    if not (v_tex > v_flat + 1e-4):
        raise AssertionError(f"xpil_emboss: エッジ有りの方が応答分散大のはず"
                             f"(flat={v_flat:.6f} textured={v_tex:.6f})")
    return f"xpil_emboss: 応答分散 平坦 {v_flat:.5f} < エッジ有り {v_tex:.5f}(エッジ応答)"


GT_CHECKS = [
    gt_motion_blur,
    gt_vignette,
    gt_cutout,
    gt_maxentropy_thresh,
    gt_signed_maurer_dist,
    gt_rgb1_to_gray,
    gt_access_channel,
    gt_emboss_edge_response,
]


def main() -> None:
    by = ops._BY_NAME

    # --- 存在確認: TARGET 名がすべて registry にあること(欠けたら loud に落とす) ---
    missing = [n for n in OPS if n not in by]
    if missing:
        raise AssertionError(f"registry に無い TARGET オペ: {missing}")

    # --- 汎用ループ: 全オペで 有限性 / 型(sort) / 決定性 を検証 ---
    for name in OPS:
        op = by[name]
        out = op.fn(input_for(op.in_sort), _A, _B)  # ← 全オペを実際に呼ぶ
        _assert_finite(name, out)
        _assert_typed(name, out, op.out_sort)
        _assert_deterministic(name, op, op.in_sort)

    # --- 強い GT(beat-the-null 付き代表オペ) ---
    print("GT checks:")
    for check in GT_CHECKS:
        print("  - " + check())

    n_ops, n_gt = len(OPS), len(GT_CHECKS)
    cats = sorted({by[n].category for n in OPS})
    print(f"categories exercised: {cats}")
    print(f"PASS: {n_ops} ops exercised, all finite/typed/deterministic; {n_gt} GT checks")


if __name__ == "__main__":
    main()
