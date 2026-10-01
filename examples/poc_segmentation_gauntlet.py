# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC(セグメンテーション拡充 第 1 陣): 真値つきの 6 つの合成世界 × レジストリの分割手法 10 本 + ルールの直し方 3 本を
総当たりし、物差し(Dice/Jaccard・VI・ARI・境界 F・HD95・過分割/未分割・分裂/融合/欠落/偽)で採点して「どの手法がどの世界で
壊れるか」「どの物差しがどの壊れ方に盲目か」の表と、手法ごとの境界を重ねたコマ送りを出す。

方針: **学習器は載せない**。世界(:mod:`segworld`)は閉形式の真値を持ち、物差し(:mod:`segeval`)は定理か第 2 実装の門を持つ。
手法はレジストリの op(``fs.apply``)をそのまま既定のノブ(a = b = 0.5)で回す —— ノブを世界ごとに合わせないので、
「既定で壊れる」ことが見える(ノブを合わせれば直る手法もある = 限界)。直し方 3 本はルールベース:
距離変換の分水嶺(触れ合う粒)、局所の標準偏差 2 本の k-means(質感)、フラットフィールド(照明の勾配。照明は
**真値の照明場** = 検査で言う白基準画像。ラベルは使わない)。

門(真値の出どころ、自明でない):
  1. **真値どおりの世界で満点**: 6 世界すべてで 真 vs 真 が Dice = 1、VI = 0、ARI = 1、境界 F = 1、HD = 0、過分割 = 未分割 = 0、個数一致。
  2. **触れ合う粒**: Otsu は Jaccard ≥ 0.9 なのに未分割 ≥ n/2(マスクの物差しは融合に盲目、個数の物差しが見る)。距離変換の
     分水嶺は未分割 0・一致 ≥ n − 2。
  3. **結晶粒**: 勾配の分水嶺は境界 F ≥ 0.95 なのに過分割 ≥ 5n(境界の物差しは過分割に盲目、VI/過分割が見る)。大域の手法
     (Otsu・Chan–Vese・random walker)は ARI < 0.3、Sauvola は個数を全部当てる(一致 = n)が粒界の帯を背景に落とすので
     Jaccard < 0.95(個数の物差しと面積の物差しが別の答えを出す)、格子を返す手法のうち 2 本は ARI ≥ 0.8。
  4. **影のある部品**: どの手法も部品の Jaccard < 0.3。閾値を総当たりした最良(真値を見るオラクル)でも Jaccard < 0.8
     = 閾値では原理的に切れない(影と暗い面)。
  5. **質感**: マスクを返す手法 6 本は ARI < 0.3(閾値では切れない)。格子を返す手法の最良(Felzenszwalb)も ARI < 0.7 で
     過分割 ≥ 10。局所の標準偏差 2 本の k-means は ARI ≥ 0.85 で過分割 0。
  6. **照明の勾配**: 大域 Otsu は Jaccard < 0.5、フラットフィールド後の Otsu は Jaccard ≥ 0.95 で個数一致。
  7. **細い構造**: Otsu は境界 F(τ = 2) ≥ 0.95 なのに過分割(雑音の粒) ≥ 10、局所閾値 3 本は Jaccard < 0.2(既定のノブは雑音を拾う)。
  8. 図なしで 60 秒以内。

正直に書くこと:
* 手法のノブは既定(0.5)。合わせれば直る手法(局所閾値の窓・k、Chan–Vese の μ)があり、この表は「既定の挙動」の表。
* 格子(境界)を返す手法のラベルは、格子の画素を最も近い領域に配った**全画素の分割**(背景の概念が無い)なので、
  マスクの Dice/Jaccard は示さない(—)。
* 物体が暗い世界(照明の勾配・細い構造)は画像を反転して手法に渡す(世界の宣言、画素ごとの真値ではない)。

Run: py -3.11 examples/poc_segmentation_gauntlet.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import segeval as SE  # noqa: E402
import segworld as SW  # noqa: E402
from blob2d import blob_distance, blob_label  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

warnings.filterwarnings("ignore")

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
T0 = time.time()
OK = []
TAU = 2.0

#: 世界: (鍵, 題, 作る関数, 物体が明るいか)
WORLDS = [
    ("blobs", "触れ合う粒", lambda: SW.world_blobs_touching(10, 0.2, 0), True),
    ("voronoi", "結晶粒(ボロノイ)", lambda: SW.world_grains_voronoi(36, 0), True),
    ("parts", "影のある部品", lambda: SW.world_parts_with_shadow(0), True),
    ("texture", "質感だけ違う領域", lambda: SW.world_texture_regions(0, n_regions=3), True),
    ("gradient", "照明の勾配", lambda: SW.world_gradient_illumination(0), False),
    ("thin", "細い構造", lambda: SW.world_thin_structures(0), False),
]
#: レジストリの手法: 名前 → 返り値の種類(mask = 物体の領域、lattice = 境界の格子)
METHODS = {"otsu": "mask", "local_threshold": "mask", "sk_niblack": "mask", "sk_sauvola": "mask", "sk_chan_vese": "mask",
           "xsk_random_walker": "mask", "watersheds": "lattice", "sg_watershed_gradient": "lattice", "sk_felzenszwalb": "lattice",
           "sk_slic": "lattice"}


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


# ───────────────────────────── 手法 → ラベル ─────────────────────────────
def to_labels(out, kind):
    """手法の返り値(0/1 の画像)をラベル画像に。mask = 連結成分(背景 0)、lattice = 格子で分けた領域(全画素)。"""
    if kind == "mask":
        return blob_label(out > 0.5).astype(np.int64)
    reg = blob_label(out < 0.5).astype(np.int64)
    if (reg == 0).any():
        idx = ndi.distance_transform_edt(reg == 0, return_indices=True)[1]
        reg = reg[idx[0], idx[1]]
    return reg


def fix_edt_watershed(im, world):
    """直し方 1(触れ合う粒): Otsu のマスク → 距離変換 → h-maxima(h = 2)の種 → 距離の分水嶺(マスクの中)。"""
    from skimage.morphology import h_maxima
    from skimage.segmentation import watershed
    mask = fs.apply(im, "otsu") > 0.5
    dist = blob_distance(mask)
    markers = ndi.label(h_maxima(dist, 2.0))[0]
    return watershed(-dist, markers, mask=mask).astype(np.int64)


def _local_std(x, win):
    m = ndi.uniform_filter(x, win)
    return np.sqrt(np.maximum(ndi.uniform_filter(x * x, win) - m * m, 0.0))


def fix_texture_kmeans(im, world):
    """直し方 2(質感): 局所の標準偏差(窓 15)を 2 本(生とガウス σ = 1.5 の後)→ k-means(k = 領域数、分位点で初期化、決定論的)
    → 中央値フィルタ 9。白色雑音はぼかすと σ が 1/(2√π σ_g) に落ち、縞は exp(−2π²σ_g²/P²) にしか落ちない = 2 本目が分ける。"""
    k = world["truth"]["n_regions"]
    F = np.stack([_local_std(im, 15).ravel(), _local_std(ndi.gaussian_filter(im, 1.5), 15).ravel()], axis=1)
    F = F / F.std(axis=0)
    C = np.stack([np.percentile(F[:, j], np.linspace(10, 90, k)) for j in range(2)], axis=1)
    L = np.zeros(len(F), np.int64)
    for _ in range(50):
        L = ((F[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([F[L == j].mean(0) if (L == j).any() else C[j] for j in range(k)])
    return ndi.median_filter(L.reshape(im.shape) + 1, 9).astype(np.int64)


def fix_flat_field(im, world):
    """直し方 3(照明の勾配): 画像を照明場(白基準)で割ってから Otsu。物体が暗い世界なので反転してから。"""
    flat = np.clip(1.0 - world["image"] / world["illumination"], 0.0, 1.0)
    return blob_label(fs.apply(flat, "otsu") > 0.5).astype(np.int64)


FIXES = {"blobs": ("edt_watershed", fix_edt_watershed), "texture": ("texture_kmeans", fix_texture_kmeans),
         "gradient": ("flat_field_otsu", fix_flat_field)}


def oracle_threshold_jaccard(im, body):
    """閾値を 255 段すべて試し、真値との Jaccard の最大(両極性)。真値を見るので手法ではなく上界。"""
    best = 0.0
    for t in np.linspace(0.0, 1.0, 256):
        m = im > t
        best = max(best, SE.seg_dice_jaccard(m, body)["jaccard"], SE.seg_dice_jaccard(~m, body)["jaccard"])
    return best


# ───────────────────────────── 総当たり ─────────────────────────────
def run_all():
    rows = []            # (世界, 手法, 種類, card)
    labels = {}          # (世界, 手法) → ラベル画像(図用)
    worlds = {}
    for key, title, make, bright in WORLDS:
        w = make()
        worlds[key] = (title, w, bright)
        im = w["image"] if bright else 1.0 - w["image"]
        for name, kind in METHODS.items():
            t = time.time()
            out = fs.apply(im, name, 0.5, 0.5)
            lab = to_labels(out, kind)
            card = SE.seg_score_card(lab, w["labels"], tau=TAU)
            card["seconds"] = time.time() - t
            rows.append((key, name, kind, card))
            labels[(key, name)] = lab
        if key in FIXES:
            fname, fn = FIXES[key]
            t = time.time()
            lab = fn(im, w)
            card = SE.seg_score_card(lab, w["labels"], tau=TAU)
            card["seconds"] = time.time() - t
            rows.append((key, fname, "mask" if key != "texture" else "lattice", card))
            labels[(key, fname)] = lab
    return worlds, rows, labels


def fmt(card, kind):
    j = "  —  " if kind == "lattice" else "%5.2f" % card["jaccard"]
    hd = "  nan" if math.isnan(card["hausdorff95"]) else "%5.1f" % card["hausdorff95"]
    return "J=%s VI=%5.2f ARI=%5.2f BF=%4.2f HD95=%s over=%3d under=%3d n=%3d/%2d match=%2d" % (
        j, card["voi"] + 0.0, card["adjusted_rand_index"], card["boundary_f"], hd, card["over"], card["under"], card["n_pred"], card["n_true"], card["matched"])


def main() -> int:
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。この PoC は予算で変わらない)" % ("reduced" if REDUCED else "full"))
    print("== 1. 真値どおりの世界で満点か")
    worlds, rows, labels = run_all()
    perfect = []
    for key, (title, w, _b) in worlds.items():
        c = SE.seg_score_card(w["labels"], w["labels"], tau=TAU)
        ok = (c["dice"] == 1.0 and c["voi"] == 0.0 and c["adjusted_rand_index"] == 1.0 and c["boundary_f"] == 1.0
              and c["hausdorff"] == 0.0 and c["over"] == 0 and c["under"] == 0 and c["counts_match"])
        perfect.append(ok)
        print("  %-12s n=%2d  %s" % (title, int(w["labels"].max()), "満点" if ok else "満点でない"))
    gate("6 世界すべてで 真 vs 真 が全部の物差しで満点", len(perfect) == 6 and all(perfect))

    print("== 2. 総当たり(手法は既定のノブ)")
    R = {(k, m): (kind, c) for k, m, kind, c in rows}
    cur = None
    for key, name, kind, c in rows:
        if key != cur:
            cur = key
            print("  --- %s(%s)" % (worlds[key][0], key))
        print("  %-18s %-7s %s  %.2fs" % (name, kind, fmt(c, kind), c["seconds"]))

    print("== 3. どの物差しがどの壊れ方に盲目か(門)")
    n_b = int(worlds["blobs"][1]["labels"].max())
    co = R[("blobs", "otsu")][1]
    gate("触れ合う粒: Otsu は Jaccard ≥ 0.9 なのに未分割 ≥ n/2(マスクの物差しは融合に盲目)", co["jaccard"] >= 0.9 and co["under"] >= n_b // 2,
         "J=%.2f under=%d/%d" % (co["jaccard"], co["under"], n_b))
    cf = R[("blobs", "edt_watershed")][1]
    gate("触れ合う粒: 距離変換の分水嶺は未分割 0・一致 ≥ n − 2", cf["under"] == 0 and cf["matched"] >= n_b - 2,
         "under=%d matched=%d/%d" % (cf["under"], cf["matched"], n_b))
    n_v = int(worlds["voronoi"][1]["labels"].max())
    cw = R[("voronoi", "sg_watershed_gradient")][1]
    gate("結晶粒: 勾配の分水嶺は境界 F ≥ 0.95 なのに過分割 ≥ 5n(境界の物差しは過分割に盲目)", cw["boundary_f"] >= 0.95 and cw["over"] >= 5 * n_v,
         "BF=%.2f over=%d n=%d" % (cw["boundary_f"], cw["over"], n_v))
    ari_glob = [R[("voronoi", m)][1]["adjusted_rand_index"] for m in ("otsu", "sk_chan_vese", "xsk_random_walker")]
    ari_lat = sorted(R[("voronoi", m)][1]["adjusted_rand_index"] for m, k in METHODS.items() if k == "lattice")
    csv = R[("voronoi", "sk_sauvola")][1]
    gate("結晶粒: 大域の手法 3 本は ARI < 0.3、Sauvola は個数を全部当てる(一致 = n)が粒界の帯を落とし Jaccard < 0.95、格子の手法 2 本は ARI ≥ 0.8",
         max(ari_glob) < 0.3 and csv["matched"] == n_v and csv["jaccard"] < 0.95 and ari_lat[-2] >= 0.8,
         "global max %.2f / sauvola matched %d J=%.2f / lattice top2 %.2f %.2f" % (max(ari_glob), csv["matched"], csv["jaccard"], ari_lat[-1], ari_lat[-2]))
    wp = worlds["parts"][1]
    j_parts = [R[("parts", m)][1]["jaccard"] for m, k in METHODS.items() if k == "mask"]
    orc = oracle_threshold_jaccard(wp["image"], wp["labels"] > 0)
    gate("影のある部品: どの手法も Jaccard < 0.3、閾値のオラクル(真値を見る上界)でも < 0.8", max(j_parts) < 0.3 and orc < 0.8,
         "max J=%.2f oracle=%.2f" % (max(j_parts), orc))
    ari_tm = [R[("texture", m)][1]["adjusted_rand_index"] for m, k in METHODS.items() if k == "mask"]
    best_lat = max(((R[("texture", m)][1]["adjusted_rand_index"], R[("texture", m)][1]["over"]) for m, k in METHODS.items() if k == "lattice"))
    ct = R[("texture", "texture_kmeans")][1]
    gate("質感: マスクの手法 6 本は ARI < 0.3(閾値では切れない)、格子の手法の最良も ARI < 0.7 で過分割 ≥ 10、局所 σ 2 本の k-means は ARI ≥ 0.85 で過分割 0",
         len(ari_tm) == 6 and max(ari_tm) < 0.3 and best_lat[0] < 0.7 and best_lat[1] >= 10 and ct["adjusted_rand_index"] >= 0.85 and ct["over"] == 0,
         "mask max %.2f / lattice best %.2f (over %d) / kmeans %.2f" % (max(ari_tm), best_lat[0], best_lat[1], ct["adjusted_rand_index"]))
    cg, cff = R[("gradient", "otsu")][1], R[("gradient", "flat_field_otsu")][1]
    gate("照明の勾配: 大域 Otsu は Jaccard < 0.5、フラットフィールド後は ≥ 0.95 で個数一致", cg["jaccard"] < 0.5 and cff["jaccard"] >= 0.95 and cff["counts_match"],
         "global %.2f / flat %.2f" % (cg["jaccard"], cff["jaccard"]))
    cth = R[("thin", "otsu")][1]
    j_loc = [R[("thin", m)][1]["jaccard"] for m in ("local_threshold", "sk_niblack", "sk_sauvola")]
    gate("細い構造: Otsu は境界 F ≥ 0.95 なのに過分割 ≥ 10(雑音の粒)、局所閾値 3 本は Jaccard < 0.2", cth["boundary_f"] >= 0.95 and cth["over"] >= 10 and max(j_loc) < 0.2,
         "BF=%.2f over=%d / local max J=%.2f" % (cth["boundary_f"], cth["over"], max(j_loc)))
    elapsed = time.time() - T0
    gate("図なしで 60 秒以内", elapsed < 60.0, "%.1f s" % elapsed)

    if figs.enabled():
        figures(worlds, rows, labels)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("== 結果: %d / %d 門, %.1f s(CPU %.1f s)" % (sum(OK), len(OK), time.time() - T0, time.process_time()))
    print("PASS" if all(OK) else "FAIL")                    # tests/test_poc_scripts_run.py は exit 0 と PASS の両方を見る
    return 0 if all(OK) else 1


# ───────────────────────────── 図 ─────────────────────────────
def _boundary(lab):
    b = np.zeros(lab.shape, bool)
    b[:, :-1] |= lab[:, 1:] != lab[:, :-1]
    b[:-1, :] |= lab[1:, :] != lab[:-1, :]
    return b


def overlay(im, true_lab, pred_lab, text):
    """灰色の画像(3 倍に拡大、最近傍)に真の境界(緑)と手法の境界(赤、重なれば黄)を重ね、左上に手法名と採点。"""
    import annotate as AN
    rgb = np.repeat(np.clip(im, 0, 1)[:, :, None], 3, axis=2) * 0.85
    bt, bp = _boundary(true_lab), _boundary(pred_lab)
    rgb[bt] = [0.1, 0.8, 0.2]
    rgb[bp] = [0.9, 0.15, 0.1]
    rgb[bt & bp] = [1.0, 0.9, 0.1]
    rgb = np.repeat(np.repeat(rgb, 3, axis=0), 3, axis=1)
    return np.asarray(AN.text_box(rgb, text, (6, 6), anchor="lt", font_size=13, max_width=rgb.shape[1] - 12))


def figures(worlds, rows, labels):
    print("== 4. 図")
    panels, caps = [], []
    for key, (title, w, _b) in worlds.items():
        panels += [w["image"], w["labels"].astype(float)]
        caps += ["%s: 画像" % title, "%s: 真値ラベル(n = %d)" % (title, int(w["labels"].max()))]
    figs.save_grid("worlds", panels, captions=caps, title="真値つきの 6 つの合成世界(segworld)", ncols=4,
                   gray=[True, False] * 6,
                   caption="左 = 画像、右 = 真値のラベル。触れ合う粒(鎖状、重なりは閉形式のレンズ)、ボロノイ結晶粒(粒界の長さ = 多角形の辺)、"
                           "影のある部品(影は背景)、質感だけ違う 3 領域(平均は同じ)、照明の勾配の上の暗い物体、幅 1〜3 px の線とひび。")
    # ★表は世界ごとに 1 枚。examplefig.save_table は 1 セルごとに text_box を全画像に掛けるので、65 行 × 16 列の 1 枚は 100 秒を超えた
    # (実測 104 s)。11 行 × 11 列 × 6 枚なら数秒で、読む側も世界ごとに手法を比べられる。
    header = ["手法", "種類", "Jaccard", "VI", "ARI", "境界F", "HD95", "過分割", "未分割", "予測/真", "一致/分裂/融合/欠落/偽"]
    for key, (title, w, _b) in worlds.items():
        table = []
        for k2, name, kind, c in rows:
            if k2 != key:
                continue
            table.append([name, kind, "—" if kind == "lattice" else "%.3f" % c["jaccard"], "%.3f" % (c["voi"] + 0.0),
                          "%.3f" % c["adjusted_rand_index"], "%.3f" % c["boundary_f"],
                          "nan" if math.isnan(c["hausdorff95"]) else "%.1f" % c["hausdorff95"], str(c["over"]), str(c["under"]),
                          "%d/%d" % (c["n_pred"], c["n_true"]),
                          "%d/%d/%d/%d/%d" % (c["matched"], c["split"], c["merged"], c["missed"], c["false"])])
        figs.save_table("scores_%s" % key, header, table, title="%s: 手法(既定のノブ)の採点表" % title,
                        caption="Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、"
                                "HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は分割表の多数決の多重度、一致/分裂/融合/欠落/偽は主に重なる辺の次数。"
                                + ("最後の行はルールの直し方。" if key in FIXES else ""))
    for key, (title, w, bright) in worlds.items():
        im = w["image"]
        names = [m for (k, m) in labels if k == key]
        frames = [overlay(im, w["labels"], labels[(key, m)], "%s: %s  %s" % (title, m, fmt_short(rows, key, m))) for m in names]
        figs.save_gif("gauntlet_%s" % key, frames, fps=1.0,
                      caption="%s: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(%s)。" % (title, ", ".join(names)))
    print("  図 %d 枚" % len(figs.manifest()))


def fmt_short(rows, key, name):
    for k, m, kind, c in rows:
        if k == key and m == name:
            j = "" if kind == "lattice" else "J=%.2f " % c["jaccard"]
            return "%sARI=%.2f BF=%.2f n=%d/%d" % (j, c["adjusted_rand_index"], c["boundary_f"], c["n_pred"], c["n_true"])
    return ""


if __name__ == "__main__":
    sys.exit(main())
