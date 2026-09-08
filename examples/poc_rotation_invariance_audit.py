# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_rotation_invariance_audit — 「回転しても同じ」と言える量はどれか(実写で監査)。

    py -3.11 examples/poc_rotation_invariance_audit.py

【なぜ要るか】
著者の指摘(2026-09-08)「PoC の評価に回転成分が入っていないのが、良くない感じは
ありますね」。形の特徴量は当たり前のように「回転不変」と呼ばれるが、**画素の格子は
回転で不変ではない**。不変性の主張は、たいてい下請け(境界の数え方・補間・しきい値)
の任意性のところで壊れる。ここではその壊れ方を、角度を振って数える。

【素材 —— 合成ではなく実写】
「カクカクのボックスでできたような画像よりは、実際の写真とかのほうが説得力はある」
(著者、2026-09-08)。主役は **scikit-image 同梱の実写 `coins`**(大英博物館、ポンペイ
出土のギリシャ硬貨。追加ダウンロードなし)。閉形式の錨がどうしても要るところにだけ、
合成の正方形を**対照**として置く。

【グラウンドトゥルース(すべて assert で落とす)】
0. **回す道具は fullseye ではない**。刺激(独立変数)の生成に `scipy.ndimage.rotate` を
   使い、測るほうだけを fullseye にする —— 自分の回転で自分の不変性を測ると、
   両方同じ向きに間違っても気づけない。
1. **対照群 = 90 度の倍数**(`np.rot90`、補間なし・情報損失なし)。ここでばらつけば
   **測り方が向きに依存**している。ここが平らで途中の角度だけばらつくなら、犯人は
   **補間**であって測り方ではない。この 2 つを分けずに 1 つの数字で語らない。
2. **面積**: 連続では厳密に不変。格子では境界 1 画素の不確かさが効くので、相対ばらつきは
   おおよそ ``P*0.5/A`` = 等価直径 d の円なら ``2/d``。
3. **周囲長**: 4 連結の階段長は向きで変わる ―― 一辺 L の正方形を 45 度回すと
   ``4L -> 4L*sqrt(2)`` の **+41.4 %**。ただし `blob_features` の下請け
   (`skimage.measure.regionprops` の `perimeter`)は Crofton 流の重みで補正して
   いるので、**実測がこの上限を大きく下回るならそれが答え**。予測を先に出して、
   外れたら外れたと書く。
4. **円形度** ``4*pi*A/P^2``: 周囲長の誤差が 2 乗で効くので、相対ばらつきは周囲長の
   おおよそ 2 倍。
5. **領域モーメント不変量**(`moments_region_2nd_invar` /
   `moments_region_central_invar`、HALCON 流): 解析的に回転不変。実測のばらつきは
   補間の分だけのはず。★3-D 点群用の `moment_invariants` とは**別物**で、名前だけで
   選ぶと ``(N,3)`` を要求されて落ちる(この PoC を書くときに実際に踏んだ)。

【読み方】各節は「予測 → 実測 → 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

ANGLES = np.arange(0.0, 360.0, 5.0)          # 72 通り(5 度刻み)
QUARTERS = (0, 90, 180, 270)                 # 補間なしの対照群


# --------------------------------------------------------------------------- #
# 刺激をつくる —— 回すのは scipy(fullseye で fullseye を測らない)
# --------------------------------------------------------------------------- #
def _rotate(img, deg, exact=False):
    """``deg`` 度回した画像。``exact`` なら 90 度の倍数を ``np.rot90`` で厳密に。"""
    if exact:
        k = int(round(deg / 90.0)) % 4
        return np.rot90(np.asarray(img), k)
    from scipy import ndimage
    return ndimage.rotate(np.asarray(img, dtype=np.float64), deg, reshape=True,
                          order=1, mode="constant", cval=0.0)


def _biggest_blob(mask):
    """一番大きい連結成分だけを残す(端に触れているものは捨てる)。"""
    lbl = np.asarray(fs.ledger.blob_label(np.asarray(mask, dtype=bool)))
    if lbl.max() == 0:
        return None, None
    f = fs.ledger.blob_features(lbl)
    area = np.asarray(f["area"], dtype=np.float64)
    keep = np.asarray(f["touches_border"]) == 0
    if not np.any(keep):
        return None, None
    idx = int(np.argmax(np.where(keep, area, -1.0)))
    return (lbl == int(np.asarray(f["label"])[idx])), {k: np.asarray(v)[idx]
                                                       for k, v in f.items()
                                                       if k not in ("n", "spacing", "units")}


def _measure(mask):
    """1 つの領域から、不変だと**言われている**量を取り出す。"""
    one, feat = _biggest_blob(mask)
    if one is None:
        return None
    # ★HALCON 流の**領域**モーメント不変量。3-D 点群用の `moment_invariants` とは
    #   別物(同じ語で呼ばれるので、名前だけで選ぶと (N,3) を要求されて落ちる)。
    m2 = float(fs.op.moments_region_2nd_invar(one.astype(np.float64)))
    mc = float(fs.op.moments_region_central_invar(one.astype(np.float64)))
    return {"area": float(feat["area"]), "perimeter": float(feat["perimeter"]),
            "circularity": float(feat["circularity"]),
            "solidity": float(feat["solidity"]),
            "eccentricity": float(feat["eccentricity"]),
            "m2_invar": m2, "mc_invar": mc, "mask": one}


def _spread(vals):
    """相対ばらつき [%](最大 - 最小 / 中央値)。0 除算は nan で返す。"""
    v = np.asarray(vals, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    med = float(np.median(v))
    if abs(med) < 1e-12:
        return float("nan")
    return 100.0 * float(v.max() - v.min()) / abs(med)


# --------------------------------------------------------------------------- #
# 1. 閉形式の錨 —— 合成の正方形(ここだけ実写ではない、理由つき)
# --------------------------------------------------------------------------- #
def section_square_anchor():
    """一辺 L の正方形。**予測を先に印字してから**測る。"""
    L = 80
    pad = 60
    sq = np.zeros((L + 2 * pad, L + 2 * pad), dtype=np.float64)
    sq[pad:pad + L, pad:pad + L] = 1.0
    ceil_p = 4.0 * L * math_sqrt2()
    print("1) 閉形式の錨(合成の正方形 L=%d、ここだけ実写でないのは上限が要るから)" % L)
    print("   予測: 面積は不変(格子の境界 1 px で ±%.1f %%)、"
          "4 連結の階段周囲長は 45 度で 4L=%.0f -> 4L√2=%.0f の **+41.4 %%** が上限"
          % (100.0 * (4.0 * L * 0.5) / (L * L), 4.0 * L, ceil_p))

    got = {}
    for deg in ANGLES:
        m = _measure(_rotate(sq, float(deg)) > 0.5)
        if m is not None:
            got.setdefault("area", []).append(m["area"])
            got.setdefault("perimeter", []).append(m["perimeter"])
            got.setdefault("circularity", []).append(m["circularity"])
    sa, sp, sc = (_spread(got[k]) for k in ("area", "perimeter", "circularity"))
    print("   実測: 面積 %.2f %% / 周囲長 %.2f %% / 円形度 %.2f %%(72 角度)" % (sa, sp, sc))
    print("   -> 周囲長の実測 %.2f %% は階段の上限 41.4 %% を **%.1f 倍下回る**"
          " —— 下請け(regionprops の perimeter)が Crofton 流に補正しているため。"
          % (sp, 41.4 / max(sp, 1e-9)))
    assert sa < 6.0, sa
    assert sp < 41.4, (sp, "階段の上限を超えたら、補正が効いていないということ")
    assert sc > sa, (sc, sa, "円形度は周囲長の誤差を 2 乗で拾うので面積より荒れる")
    return {"square_area_spread": sa, "square_perimeter_spread": sp,
            "square_circularity_spread": sc}


def math_sqrt2():
    import math
    return math.sqrt(2.0)


# --------------------------------------------------------------------------- #
# 2. 実写(coins)—— 主役
# --------------------------------------------------------------------------- #
def _coin_mask(gray):
    """一番手前の硬貨を 1 枚取り出すための二値化(単純な固定しきい値)。"""
    return np.asarray(gray) > 0.42


def section_real_coins():
    photo = realdata.sample_photo("coins")
    # 端に触れない大きめの硬貨が 1 枚だけ入るように切り出す(回転で外へ出ないよう余白つき)
    crop = np.asarray(photo)[10:100, 8:98]
    big = np.zeros((160, 160), dtype=np.float64)
    big[35:35 + crop.shape[0], 35:35 + crop.shape[1]] = crop

    base = _measure(_coin_mask(big))
    assert base is not None, "0 度で硬貨が取れていない"
    d = 2.0 * (base["area"] / np.pi) ** 0.5
    print("2) 実写(scikit-image `coins`: 大英博物館、ポンペイ出土のギリシャ硬貨)")
    print("   0 度の硬貨: 面積 %.0f px、等価直径 %.1f px、周囲長 %.1f px、円形度 %.3f"
          % (base["area"], d, base["perimeter"], base["circularity"]))
    print("   予測: 面積の相対ばらつき ≈ 2/d = %.2f %%、円形度はその 2 倍あたり"
          % (200.0 / d))

    keys = ("area", "perimeter", "circularity", "solidity", "eccentricity", "m2_invar", "mc_invar")
    full = {k: [] for k in keys}
    quarter = {k: [] for k in keys}
    frames = []
    for deg in ANGLES:
        m = _measure(_coin_mask(_rotate(big, float(deg))))
        if m is None:
            continue
        for k in keys:
            full[k].append(m[k])
        if int(deg) in QUARTERS:
            q = _measure(_coin_mask(_rotate(big, float(deg), exact=True)))
            if q is not None:
                for k in keys:
                    quarter[k].append(q[k])
        frames.append((float(deg), m))

    print("   量           全角度(補間あり)  90 度の倍数(補間なし)  犯人")
    verdict = {}
    for k in keys:
        a, b = _spread(full[k]), _spread(quarter[k])
        who = "測り方" if (b > 0.5 and b > a * 0.5) else ("補間" if a > 0.5 else "—(平ら)")
        verdict[k] = (a, b, who)
        print("   %-12s %8.2f %%          %8.2f %%            %s" % (k, a, b, who))

    # 対照群が平らなのに全角度が荒れる = 補間のせい、を面積で確かめる
    assert verdict["area"][1] <= verdict["area"][0] + 1e-9, verdict["area"]
    assert verdict["circularity"][0] > verdict["area"][0], (
        "円形度が面積より安定するのは変(周囲長の誤差を 2 乗で拾うはず)")
    return verdict, base, frames, big


# --------------------------------------------------------------------------- #
# 3. 図と GIF
# --------------------------------------------------------------------------- #
def make_figures(frames, big):
    """回る硬貨に、そのつどの測定値を焼き込んだ GIF(と静止画の完成形)。"""
    if not figs.enabled():
        return 0
    tiles = []
    for deg, m in frames:
        rot = _rotate(big, deg)
        rgb = np.repeat(np.clip(rot, 0, 1)[..., None], 3, axis=2)
        rgb = fs.annotate_invert(rgb, m["mask"], draw="margin", width=2, mode="xor")
        tsv = ("量\t値\n面積\t%.0f\n周囲長\t%.1f\n円形度\t%.3f\nHu1\t%.4f"
               % (m["area"], m["perimeter"], m["circularity"], m["m2_invar"]))
        rgb = fs.annotate_table(rgb, tsv, (4, 4), anchor="lt", font_size=11, header=True)
        rgb = fs.text_box(rgb, "%3d 度" % int(deg), (rgb.shape[1] - 4, rgb.shape[0] - 4),
                          anchor="rb", font_size=12)
        tiles.append(rgb)
    figs.save_gif("rotating_coin", tiles, fps=8,
                  caption="実写の硬貨を 5 度ずつ回し、そのつど測る。輪郭は反転色"
                          "(mode=\"xor\": 最上位 bit だけ反転するので地の模様が残り、"
                          "どの階調でも消えない)。数字がどれだけ揺れるかが見える。")
    figs.save("rotation_frames", np.concatenate(
        [tiles[0], tiles[len(tiles) // 8], tiles[len(tiles) // 4]], axis=1),
        caption="0 度 / 45 度 / 90 度。回すたびに二値化の縁が動き、面積と周囲長が揺れる。")
    return len(tiles)


def main():
    t0 = time.perf_counter()
    r1 = section_square_anchor()
    verdict, base, frames, big = section_real_coins()
    n = make_figures(frames, big)
    print("\nPASS: 回転不変の監査(実写 `coins` 72 角度 + 合成正方形の錨)。"
          "面積 %.2f %% / 周囲長 %.2f %% / 円形度 %.2f %%(全角度)、"
          "90 度の倍数だけなら面積 %.2f %%。GIF %d コマ。 実行 %.2f 秒"
          % (verdict["area"][0], verdict["perimeter"][0], verdict["circularity"][0],
             verdict["area"][1], n, time.perf_counter() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
