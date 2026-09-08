# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_rotation_invariance_audit — 「回転しても同じ」と言える量はどれか(実写で監査)。

    py -3.11 examples/poc_rotation_invariance_audit.py

【なぜ要るか】
著者の指摘(2026-09-08)「PoC の評価に回転成分が入っていないのが、良くない感じは
ありますね」。形の特徴量は当たり前のように「回転不変」と呼ばれるが、**画素の格子は
回転で不変ではない**。不変性の主張は、たいてい下請け(境界の数え方・補間・しきい値)
の任意性のところで壊れる。ここではその壊れ方を、角度を 72 通り振って数える。

【素材 —— 合成ではなく実写】
「カクカクのボックスでできたような画像よりは、実際の写真とかのほうが説得力はある」
(著者、2026-09-08)。主役は **scikit-image 同梱の実写 `coins`**(大英博物館、ポンペイ
出土のギリシャ硬貨。追加ダウンロードなし)。閉形式の上限がどうしても要るところにだけ、
合成の正方形を**錨**として置く。

【この PoC の肝 —— 犯人を 3 つに分ける】
「回すと 13 % ずれる」だけでは、何を直せばいいのか判らない。ずれを 3 本の腕に分ける:

* **腕 C(厳密)**: 90 度の倍数だけを `np.rot90` で回す。補間も再ラスタライズも
  起きない。**ここでばらつけば、測り方そのものが向きに依存**している。
* **腕 B(再ラスタライズだけ)**: 0 度の**二値マスク**を最近傍で回す。灰色の補間も
  しきい値の掛け直しも無く、**境界を格子に置き直す**ぶんだけが出る。
* **腕 A(現場)**: 灰色画像を線形補間で回してから二値化する。人が実際にやること。

``A - B`` が「灰色を補間して二値化し直す代償」、``B - C`` が「境界を置き直す代償」、
``C`` が「測り方の向き依存」。この 3 つを 1 つの数字に混ぜない。

【グラウンドトゥルース(すべて assert で落とす)】
0. **回す道具は fullseye ではない**。刺激(独立変数)の生成に `scipy.ndimage.rotate` を
   使い、測るほうだけを fullseye にする —— 自分の回転で自分の不変性を測ると、
   両方同じ向きに間違っても気づけない。
1. **面積**: 連続では厳密に不変。格子では境界 1 画素の不確かさが効くので、相対ばらつきは
   おおよそ ``P*0.5/A`` = 等価直径 d の円なら ``2/d``。
2. **周囲長**: 4 連結の階段長は向きで変わる ―― 一辺 L の正方形を 45 度回すと
   ``4L -> 4L*sqrt(2)`` の **+41.4 %** が上限。ただし `blob_features` の下請け
   (`skimage.measure.regionprops` の `perimeter`)は Crofton 流の重みで補正して
   いるので、**実測がこの上限を大きく下回るならそれが答え**。予測を先に出して、
   外れたら外れたと書く。
3. **円形度** ``4*pi*A/P^2``: 周囲長の誤差が 2 乗で効くので、面積より必ず荒れる。
4. **相対ばらつきの分母**: ``(最大-最小)/|中央値|`` は、中央値がほぼ 0 の量では意味を
   失う。Hu[1](``mc_invar``)は円に近い形では真値がほぼ 0 なので、ここを黙って % で
   語ると「30 % ずれた」に化ける —— 分母を先に疑う
   ([[feedback_zero_or_hundred_percent_check_the_denominator]])。
5. **領域モーメント不変量**(`moments_region_2nd_invar` /
   `moments_region_central_invar`、HALCON 流): 解析的に回転不変。★3-D 点群用の
   `moment_invariants` とは**別物**で、名前だけで選ぶと ``(N,3)`` を要求されて落ちる
   (この PoC を書くときに実際に踏んだ)。

【読み方】各節は「予測 → 実測 → 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

ANGLES = np.arange(0.0, 360.0, 5.0)          # 72 通り(5 度刻み)
QUARTERS = (0.0, 90.0, 180.0, 270.0)         # 補間なしの対照群
COIN_CROP = (110, 200, 120, 210)             # `coins` の中で 1 枚だけ綺麗に取れる場所
COIN_TH = 0.42                               # 固定しきい値(この切り出しでは十分)
KEYS = ("area", "perimeter", "circularity", "solidity", "eccentricity",
        "m2_invar", "mc_invar")


# --------------------------------------------------------------------------- #
# 刺激をつくる —— 回すのは scipy(fullseye で fullseye を測らない)
# --------------------------------------------------------------------------- #
def _rot(img, deg, order=1):
    from scipy import ndimage
    return ndimage.rotate(np.asarray(img, dtype=np.float64), float(deg), reshape=True,
                          order=int(order), mode="constant", cval=0.0)


def _clean(mask):
    """穴を埋めて小さな凹凸を均す(硬貨の刻印で輪郭が破れるのを防ぐ)。"""
    from scipy import ndimage
    b = np.asarray(mask, dtype=bool)
    return ndimage.binary_fill_holes(ndimage.binary_closing(b, np.ones((5, 5), bool)))


# --------------------------------------------------------------------------- #
# 測る —— ここだけ fullseye
# --------------------------------------------------------------------------- #
def _biggest_blob(mask):
    """端に触れていない一番大きい連結成分と、その特徴量。"""
    lbl = np.asarray(fs.ledger.blob_label(np.asarray(mask, dtype=bool)))
    if lbl.max() == 0:
        return None, None
    f = fs.ledger.blob_features(lbl)
    area = np.asarray(f["area"], dtype=np.float64)
    keep = np.asarray(f["touches_border"]) == 0
    if not np.any(keep):
        return None, None
    i = int(np.argmax(np.where(keep, area, -1.0)))
    one = lbl == int(np.asarray(f["label"])[i])
    return one, {k: np.asarray(v)[i] for k, v in f.items()
                 if k not in ("n", "spacing", "units")}


def _measure(mask):
    """1 つの領域から、不変だと**言われている**量を取り出す。"""
    one, feat = _biggest_blob(mask)
    if one is None:
        return None
    # ★HALCON 流の**領域**モーメント不変量。3-D 点群用の `moment_invariants` とは
    #   別物(名前だけで選ぶと (N,3) を要求されて落ちる)。
    f = one.astype(np.float64)
    return {"area": float(feat["area"]), "perimeter": float(feat["perimeter"]),
            "circularity": float(feat["circularity"]),
            "solidity": float(feat["solidity"]),
            "eccentricity": float(feat["eccentricity"]),
            "m2_invar": float(fs.op.moments_region_2nd_invar(f)),
            "mc_invar": float(fs.op.moments_region_central_invar(f)),
            "mask": one}


def _spread(vals):
    """相対ばらつき [%]((最大 - 最小) / |中央値|)。"""
    v = np.asarray(vals, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    med = float(np.median(v))
    if abs(med) < 1e-12:
        return float("nan")
    return 100.0 * float(v.max() - v.min()) / abs(med)


def _sweep(make_mask, angles):
    """角度ごとに測って、量ごとの並びとコマを返す。"""
    out = {k: [] for k in KEYS}
    frames = []
    for deg in angles:
        m = _measure(make_mask(float(deg)))
        if m is None:
            continue
        for k in KEYS:
            out[k].append(m[k])
        frames.append((float(deg), m))
    return out, frames


# --------------------------------------------------------------------------- #
# 1. 閉形式の錨 —— 合成の正方形(ここだけ実写ではない、理由つき)
# --------------------------------------------------------------------------- #
def section_square_anchor():
    """一辺 L の正方形。**予測を先に印字してから**測る。"""
    L, pad = 80, 60
    sq = np.zeros((L + 2 * pad, L + 2 * pad), dtype=np.float64)
    sq[pad:pad + L, pad:pad + L] = 1.0
    print("1) 閉形式の錨(合成の正方形 L=%d ―― ここだけ実写でないのは、上限の式が要るから)" % L)
    print("   予測: 面積は不変(境界 1 px の不確かさで ±%.1f %%)、4 連結の階段周囲長は"
          " 45 度で 4L=%.0f -> 4L√2=%.0f の **+41.4 %%** が上限"
          % (100.0 * (4.0 * L * 0.5) / (L * L), 4.0 * L, 4.0 * L * math.sqrt(2.0)))
    got, _ = _sweep(lambda d: _rot(sq, d) > 0.5, ANGLES)
    sa, sp, sc = (_spread(got[k]) for k in ("area", "perimeter", "circularity"))
    print("   実測(72 角度): 面積 %.2f %% / 周囲長 %.2f %% / 円形度 %.2f %%" % (sa, sp, sc))
    print("   -> 周囲長の実測 %.2f %% は階段の上限 41.4 %% を **%.1f 倍下回った** ——"
          " 下請け(regionprops の perimeter)が Crofton 流に補正しているから。"
          " 予測は「上限」であって「実測の当て」ではない、と書いておく。" % (sp, 41.4 / max(sp, 1e-9)))
    assert sa < 6.0, sa
    assert sp < 41.4, (sp, "階段の上限を超えたら、補正が効いていないということ")
    assert sc > sa, (sc, sa, "円形度は周囲長の誤差を 2 乗で拾うので面積より荒れるはず")
    return {"square_area": sa, "square_perimeter": sp, "square_circularity": sc}


# --------------------------------------------------------------------------- #
# 2. 実写(coins)—— 主役。犯人を 3 本の腕に分ける
# --------------------------------------------------------------------------- #
def section_real_coins():
    r0, r1, c0, c1 = COIN_CROP
    crop = np.asarray(realdata.sample_photo("coins"))[r0:r1, c0:c1]
    pad = 45                                   # 回しても端に触れないだけの余白
    grey = np.zeros((crop.shape[0] + 2 * pad, crop.shape[1] + 2 * pad), dtype=np.float64)
    grey[pad:pad + crop.shape[0], pad:pad + crop.shape[1]] = crop
    mask0 = _clean(grey > COIN_TH)

    base = _measure(mask0)
    assert base is not None, "0 度で硬貨が取れていない"
    d = 2.0 * math.sqrt(base["area"] / math.pi)
    print("2) 実写(scikit-image `coins` ―― 大英博物館、ポンペイ出土のギリシャ硬貨)")
    print("   0 度の硬貨: 面積 %.0f px、等価直径 %.1f px、周囲長 %.1f px、円形度 %.3f"
          % (base["area"], d, base["perimeter"], base["circularity"]))
    print("   予測: 面積の相対ばらつき ≈ 2/d = %.2f %%、円形度は周囲長の誤差を 2 乗で"
          "拾うので面積より大きい" % (200.0 / d))
    assert base["circularity"] > 0.9, (base["circularity"], "硬貨が綺麗に取れていない")

    arm_a, frames = _sweep(lambda deg: _clean(_rot(grey, deg) > COIN_TH), ANGLES)
    arm_b, _ = _sweep(lambda deg: _rot(mask0.astype(np.float64), deg, order=0) > 0.5, ANGLES)
    arm_c, _ = _sweep(lambda deg: np.rot90(mask0, int(round(deg / 90.0)) % 4), QUARTERS)

    print("   量            A 現場   B 再ラスタ  C 厳密   0 度の値      分母は健全か")
    verdict = {}
    for k in KEYS:
        a, b, c = _spread(arm_a[k]), _spread(arm_b[k]), _spread(arm_c[k])
        verdict[k] = (a, b, c)
        med = float(np.median(arm_a[k]))
        # ★相対ばらつきは分母がほぼ 0 だと意味を失う。Hu[1] は円に近い形では
        #   真値がほぼ 0 なので、ここを黙って % で語ると「30 % ずれた」に化ける。
        ok = abs(med) > 1e-3 * max(1.0, abs(base[k]))
        print("   %-13s %6.2f %% %7.2f %% %6.2f %%  %11.5g   %s"
              % (k, a, b, c, med, "健全" if ok else "★ほぼ 0 —— % は無意味"))
    healthy = [k for k in KEYS if abs(float(np.median(arm_a[k]))) > 1e-3]

    worst_c = max(verdict[k][2] for k in KEYS)
    print("   -> 厳密回転(腕 C)は全量きっかり %.4f %% ―― **測り方そのものに向き依存は無い**。"
          "揺れは全部、格子に置き直す代償。" % worst_c)
    assert worst_c < 1e-9, verdict

    # ★予測が外れたところ。書いた時点では「灰を補間して二値化し直すほうが荒れる」と
    #   思っていたが、周囲長まわりは**逆**だった。
    print("   ★予測が外れた: 「灰を補間するほう(A)が荒れる」と思っていたが、周囲長は"
          "A %.2f %% < B %.2f %%(%.1f 倍)、円形度も A %.2f %% < B %.2f %%。"
          % (verdict["perimeter"][0], verdict["perimeter"][1],
             verdict["perimeter"][1] / max(verdict["perimeter"][0], 1e-9),
             verdict["circularity"][0], verdict["circularity"][1]))
    print("     理由: 二値マスクを最近傍で回すと境界が**階段のまま置き直される**のに対し、"
          "灰を線形補間してから二値化すると、境界が下の連続信号から引き直される。"
          "→ **回すなら灰でやってから二値化する。二値マスクを回してはいけない。**")
    assert verdict["perimeter"][1] > verdict["perimeter"][0] * 2.0, verdict["perimeter"]
    assert verdict["circularity"][1] > verdict["circularity"][0] * 2.0, verdict["circularity"]
    # 面積はどちらの腕でも同じくらい(周囲長ほど境界の刻み方に効かれない)
    assert abs(verdict["area"][0] - verdict["area"][1]) < 0.5, verdict["area"]
    for arm in (0, 1):
        assert verdict["circularity"][arm] > verdict["area"][arm], (
            arm, "円形度が面積より安定するのは変(周囲長の誤差を 2 乗で拾うはず)")
    assert "mc_invar" not in healthy, "Hu[1] の分母が 0 でないなら、この注意書きは古い"
    return verdict, base, frames, grey


# --------------------------------------------------------------------------- #
# 3. 図と GIF
# --------------------------------------------------------------------------- #
def make_figures(frames, grey, verdict):
    """回る硬貨に、そのつどの測定値を並べた GIF と、静止画の完成形。

    ★表は画像の**隣**に置く(上に重ねると硬貨が隠れて、何が回っているのか
    見えなくなる)。コマは回転で大きさが変わるので、一番大きいコマに合わせて
    中央へ置いてから並べる —— 大きさがそろっていないと GIF は黙って詰める。
    """
    if not figs.enabled():
        return 0
    shots = [(deg, _rot(grey, deg), m) for deg, m in frames]
    H = max(a.shape[0] for _, a, _ in shots)
    W = max(a.shape[1] for _, a, _ in shots)
    PANEL = 150
    tiles = []
    for deg, rot, m in shots:
        canvas = np.zeros((H, W + PANEL, 3), dtype=np.float64)
        y, x = (H - rot.shape[0]) // 2, (W - rot.shape[1]) // 2
        rgb = np.repeat(np.clip(rot, 0.0, 1.0)[..., None], 3, axis=2)
        # ★地がモノクロなので、輪郭は**彩度のある色**で描く。灰色には彩度が
        # 無いので、彩度のある色はどの階調とも色相で区別がつく ―― 反転色より
        # 確実で、しかも「これは重ねた線だ」と一目で判る。反転色が本領を
        # 発揮するのは、地がカラーで「どの色を選んでも衝突しうる」とき。
        rgb = fs.annotate_outline(rgb, m["mask"], color="right", width=2.0)
        canvas[y:y + rot.shape[0], x:x + rot.shape[1]] = rgb
        tsv = ("量\t値\n面積\t%.0f\n周囲長\t%.1f\n円形度\t%.3f\n2 次不変量\t%.4f" %
               (m["area"], m["perimeter"], m["circularity"], m["m2_invar"]))
        canvas = fs.annotate_table(canvas, tsv, (W + 6, 8), anchor="lt", font_size=11,
                                   header=True, box_alpha=0.0,
                                   text_color=(0.95, 0.95, 0.98))
        canvas = fs.text_box(canvas, "%3d 度" % int(deg), (W + 6, H - 8), anchor="lb",
                             font_size=13, bold=True)
        tiles.append(canvas)
    figs.save("rotation_frames", np.concatenate(
        [tiles[0], tiles[len(tiles) // 8], tiles[len(tiles) // 4]], axis=1),
        caption="0 度 / 45 度 / 90 度。二値化の縁が回すたびに置き直され、面積 %.2f %%・"
                "周囲長 %.2f %%・円形度 %.2f %% 揺れる(90 度の倍数だけなら厳密に 0)。"
                "地がモノクロなので輪郭は彩度のある色で描いた(灰色には彩度が無いので、"
                "どの階調とも色相で区別がつく)。"
                % (verdict["area"][0], verdict["perimeter"][0], verdict["circularity"][0]))
    figs.save_gif("rotating_coin", tiles, fps=8,
                  caption="実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は"
                          "彩度のある色で描いている(灰色には彩度が無いので、どの階調"
                          "とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。")
    return len(tiles)


def main():
    t0 = time.perf_counter()
    section_square_anchor()
    verdict, base, frames, grey = section_real_coins()
    n = make_figures(frames, grey, verdict)
    print("\nPASS: 回転不変の監査(実写 `coins` 72 角度 + 合成正方形の錨)。"
          "現場(灰を補間して二値化)で 面積 %.2f %% / 周囲長 %.2f %% / 円形度 %.2f %%、"
          "厳密回転では全量が 0.00 %% ―― 揺れは測り方でなく格子への置き直し。GIF %d コマ。"
          " 実行 %.2f 秒"
          % (verdict["area"][0], verdict["perimeter"][0], verdict["circularity"][0],
             n, time.perf_counter() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
