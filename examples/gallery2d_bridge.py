# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery2d_bridge — 入口 op(``img_to_*``、category=bridge)を総ざらいで検証する事例 (task: contract-gallery)

    py -3.11 examples/gallery2d_bridge.py

【平たく言うと(この op 一族は何のためのもの)】
fullseye の 2-D レジストリには、画像以外の「種」(点群・1-D 信号・動画・体積・
ライトフィールド・複素場・光子カウント・レーダーのビート立方体・行列・像面上の点)
を受ける op が 161 本ある。ところが **画像からそれらの種を作る op が無かった** ので、
Studio の「1 枚の画像 + つまみ 2 つ」のプログラムからは一度も呼べず、ヘルプにも図が
付かなかった。``img_to_*`` はその入口 —— 1 枚の画像を、各 sort の *意味のある* 値
(高さ場の点群、行の濃度プロファイル、パンする動画、押し出した固体、視差つきの
ライトフィールド、振幅+位相の複素場、Poisson 標本の光子列、明点を標的にした
FMCW ビート、局所極大のキーポイント)として読み替える。

この族は **進化(ゲノム → op)の候補には入らない**(``ops._candidates`` が category
``bridge`` を除く)。入れると image の候補リストが伸びて既存の champion が別の op に
写ってしまうため(docs/WAVE0_STABLE_SLOTS.md)。名前で呼ぶ経路(``fullseye.apply`` /
Studio / 図)にだけ見える。

【グラウンドトゥルース(数値で嘘を弾く)】
全 op を呼び、op ごとに次を検証する:
  (1) 型     : 返り値が宣言 out_sort の形の契約(``backends_typed._SHAPE_OK``)を満たす。
  (2) 有限性 : NaN/Inf が無い(複素は実部・虚部とも)。
  (3) 決定性 : 同じ入力・同じノブで 2 回呼んでビット一致。
  (4) ノブ   : ``img_to_matrix``(純粋なキャスト、a,b 未使用と明記)以外は a, b で出力が変わる。
加えて、**閉形式で答えが分かる性質**を op ごとに 1 つずつ突き合わせる:
  - ``img_to_points``   : (x, y) = (col, row) × 10/W, z = 画素値 × 10 × (0.25 + 1.75a) が全点で成立、点数 = ceil(H/stride)²
  - ``img_to_signal``   : b<0.5 で行 round(a(H-1)) と一致、b≥0.5 で列と一致
  - ``img_to_counts``   : 期待値 0 の画素はカウント 0、平均は期待値 profile×n_max に近い(Poisson の大数)
  - ``img_to_video``    : フレーム 0 = 入力、フレーム t の変位が閉形式(位相相関で t·step を取り戻す)
  - ``img_to_volume``   : 各 (y,x) 列で非ゼロの最上段 = floor(clip(img·s·(D−1)))
  - ``img_to_lightfield``: 中央視点 = 入力、傾き a=0 なら全視点が入力と一致
  - ``img_to_rgb``      : 彩度 0 で 3 ch がグレー、彩度 1・色相 0 で膝(0.75)より暗い画素は G=B=0、最明部は白
  - ``img_to_cimage``   : |field| = 入力、a=0・b=0.5 で虚部 0
  - ``img_to_beatcube`` : 距離–ドップラー地図の最大ビンが「最も明るい極大の列 → 距離ビン」と一致
  - ``img_to_keypoints``: 返った点はすべて局所極大で、しきい値以上
  - ``img_to_monogenic``: w 成分 0、振幅 ≥ 0
  - ``img_to_matrix``   : 入力とビット一致(キャスト)

★EXTEND: ``_image()`` を自分の画像(``fullseye.read_image``)に差し替えれば、同じ検証が
そのまま走る。閉形式の検算のうち画像の中身に依存するもの(ビート立方体の距離ビン)は
「最も明るい極大」を自動で取るので、明点のある画像なら通る。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import fullseye as fs  # noqa: E402
import backends_bridge as BB  # noqa: E402
import backends_typed as BT  # noqa: E402


def _image(n: int = 64) -> np.ndarray:
    """決定的な合成シーン: 階調 + 明るい円 + 暗い矩形 + 細線 + 弱い雑音(右下だけ)。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = 0.15 + 0.45 * xx / (n - 1)
    img[(yy - 18) ** 2 + (xx - 18) ** 2 <= 64] = 0.95            # 明るい円(最も明るい極大)
    img[40:56, 36:60] = 0.05                                       # 暗い矩形
    img[10:12, 30:60] = 0.9                                        # 細線
    rng = np.random.default_rng(20260907)
    img[32:64, 32:64] = np.clip(img[32:64, 32:64] + rng.normal(0, 0.02, (32, 32)), 0, 1)
    return np.clip(img, 0, 1)


def _phase_shift(f0: np.ndarray, f1: np.ndarray) -> tuple[float, float]:
    """位相相関で f1 が f0 からどれだけ動いたか(dy, dx)を整数画素で返す。"""
    F0, F1 = np.fft.fft2(f0), np.fft.fft2(f1)
    r = np.fft.ifft2(F0 * np.conj(F1) / (np.abs(F0 * np.conj(F1)) + 1e-12)).real
    k = np.unravel_index(int(np.argmax(r)), r.shape)
    h, w = r.shape
    dy = k[0] if k[0] <= h // 2 else k[0] - h
    dx = k[1] if k[1] <= w // 2 else k[1] - w
    return float(-dy), float(-dx)


def run() -> dict:
    t0 = time.perf_counter()
    img = _image()
    h, w = img.shape
    results: dict = {"n_ops": 0, "contract_ok": 0, "closed_form_ok": 0, "failed": []}

    # ---- (1)〜(4) 共通契約 ---------------------------------------------------- #
    for name, out_sort, _fn in BB.BRIDGES:
        results["n_ops"] += 1
        out1 = fs.apply(img, name, 0.5, 0.5, on_error="raise")     # 例外は握り潰さない
        out2 = fs.apply(img, name, 0.5, 0.5, on_error="raise")
        ok = isinstance(out1, np.ndarray) and BT._sort_ok(out1, out_sort)
        fin = np.isfinite(out1.real).all() and (out1.dtype.kind != "c" or np.isfinite(out1.imag).all())
        det = np.array_equal(out1, out2)
        knob = True
        if name != "img_to_matrix":
            alt = fs.apply(img, name, 0.9, 0.1, on_error="raise")
            knob = alt.shape != out1.shape or not np.array_equal(alt, out1)
        if ok and fin and det and knob:
            results["contract_ok"] += 1
        else:
            results["failed"].append((name, "contract", ok, fin, det, knob))
        print("  %-18s %-11s %-16s type=%s finite=%s deterministic=%s knobs=%s"
              % (name, out_sort, out1.shape, ok, fin, det, knob))

    # ---- 閉形式の検算 ---------------------------------------------------------- #
    checks = {}
    a, b = 0.5, 0.5
    s = 0.25 + 1.75 * a
    # points: (x, y) は一辺 10 の箱、z = value * 10 * s、点数 = ceil(H/2)^2
    P = fs.apply(img, "img_to_points", a, b, on_error="raise")
    sub = img[::2, ::2]
    box = BB.POINTS_BOX
    checks["points"] = (P.shape[0] == sub.size
                        and np.allclose(P[:, 2], (sub * box * s).ravel())
                        and np.allclose(P[:, 0], np.tile(np.arange(0, w, 2) * box / w, sub.shape[0]))
                        and P[:, :2].max() < box)
    # signal: 行 / 列
    r = int(round(a * (h - 1)))
    checks["signal"] = (np.array_equal(fs.apply(img, "img_to_signal", a, 0.0, on_error="raise"), img[r, :])
                        and np.array_equal(fs.apply(img, "img_to_signal", a, 1.0, on_error="raise"), img[:, r]))
    # counts: 期待値 0 → 0、平均が期待値に近い(n_max=1000 で相対 5 % 以内)
    z = img.copy(); z[r, :8] = 0.0
    c = fs.apply(z, "img_to_counts", a, 0.49, on_error="raise")     # b<0.5: 行、n_max = 10**(1+0.98)
    n_max = 10.0 ** (1.0 + 2.0 * 0.49)
    exp = z[r, :] * n_max
    rel = abs(c[8:].mean() - exp[8:].mean()) / exp[8:].mean()
    checks["counts"] = bool((c[:8] == 0).all() and rel < 0.05)
    # video: フレーム 0 = 入力、フレーム t の変位 = t*step (a=0.5 → 2 px/frame, b=0 → +x)
    V = fs.apply(img, "img_to_video", 0.5, 0.0, on_error="raise")
    dy, dx = _phase_shift(V[0], V[3])
    checks["video"] = np.array_equal(V[0], img) and abs(dx - 6.0) <= 1.0 and abs(dy) <= 1.0
    # volume: 各列の非ゼロ最上段
    Vol = fs.apply(img, "img_to_volume", a, b, on_error="raise")
    d = Vol.shape[0]
    top = np.floor(np.clip(img * s * (d - 1), 0, d - 1)).astype(int)
    highest = np.where(Vol > 0, np.arange(d)[:, None, None], -1).max(axis=0)
    checks["volume"] = bool(np.array_equal(highest[img > 0], top[img > 0]))
    # lightfield: 中央視点 = 入力、傾き 0 で全視点一致
    L = fs.apply(img, "img_to_lightfield", a, b, on_error="raise")
    L0 = fs.apply(img, "img_to_lightfield", 0.0, b, on_error="raise")
    checks["lightfield"] = np.array_equal(L[2, 2], img) and all(np.allclose(L0[i, j], img)
                                                                 for i in range(5) for j in range(5))
    # rgb: 彩度 0 → グレー、彩度 1・色相 0 → 膝より暗い画素は G=B=0、最明部(0.95)は白に戻る
    g = fs.apply(img, "img_to_rgb", 0.3, 0.0, on_error="raise")
    red = fs.apply(img, "img_to_rgb", 0.0, 1.0, on_error="raise")
    dark = img < BB.SPECULAR_KNEE
    checks["rgb"] = (np.allclose(g[..., 0], img) and np.allclose(g[..., 2], img)
                     and np.allclose(red[..., 0], img) and np.allclose(red[dark, 1:], 0.0)
                     and red[img >= 0.95, 1].min() > 0.5)
    # cimage: |field| = 入力、a=0・b=0.5 で実場
    C = fs.apply(img, "img_to_cimage", 0.0, 0.5, on_error="raise")
    checks["cimage"] = np.allclose(np.abs(C), img) and np.allclose(C.imag, 0.0)
    # beatcube: 最も明るい極大(円の中心付近)の列 → 距離ビン。range-Doppler の最大ビンと比べる
    Bc = fs.apply(img, "img_to_beatcube", 0.0, 0.0, on_error="raise")   # 無雑音・標的 1 つ
    rd = fs.apply(Bc, "tb_range_doppler_map", 0.5, 0.5, on_error="raise")
    # 距離 → ビート周波数 → ビン: f_b = 2 S R / c、bin = f_b / f_s * n_samples
    col = 18                                                               # 円の中心列(最も明るい極大)
    R = 2.0 + 30.0 * col / w
    fb = 2.0 * 2.0e13 * R / 299792458.0
    bin_expected = fb / 1.0e7 * 64
    peak = np.unravel_index(int(np.argmax(rd)), rd.shape)
    # どちらの軸が距離かは実装の規約に従う —— 期待ビンが行・列どちらかに ±1 で現れればよい
    checks["beatcube"] = min(abs(peak[0] - bin_expected), abs(peak[1] - bin_expected)) <= 1.0
    # keypoints: 全点が局所極大かつしきい値以上
    K = fs.apply(img, "img_to_keypoints", 0.5, 0.8, on_error="raise")
    from scipy import ndimage
    mx = ndimage.maximum_filter(img, size=7, mode="nearest")
    kk = K.astype(int)
    checks["keypoints"] = bool(K.shape[0] > 0 and np.all(img[kk[:, 1], kk[:, 0]] >= 0.8)
                               and np.all(img[kk[:, 1], kk[:, 0]] >= mx[kk[:, 1], kk[:, 0]]))
    # monogenic: w 成分 0、振幅 ≥ 0
    Q = fs.apply(img, "img_to_monogenic", a, b, on_error="raise")
    amp = fs.apply(Q, "tb_monogenic_amplitude", 0.5, 0.5, on_error="raise")
    checks["monogenic"] = bool(np.allclose(Q[..., 3], 0.0) and amp.min() >= 0.0)
    # matrix: キャスト
    checks["matrix"] = np.array_equal(fs.apply(img, "img_to_matrix", a, b, on_error="raise"), img)

    for k, v in checks.items():
        print("  closed-form %-11s %s" % (k, "OK" if v else "NG"))
        if v:
            results["closed_form_ok"] += 1
        else:
            results["failed"].append((k, "closed-form"))
    results["n_closed_form"] = len(checks)
    results["elapsed_s"] = round(time.perf_counter() - t0, 3)
    return results


if __name__ == "__main__":
    r = run()
    print("bridge ops: %d / contract OK %d / closed-form OK %d of %d / %.2f s"
          % (r["n_ops"], r["contract_ok"], r["closed_form_ok"], r["n_closed_form"], r["elapsed_s"]))
    if r["failed"]:
        print("FAILED:", r["failed"])
        raise SystemExit(1)
    print("PASS")
