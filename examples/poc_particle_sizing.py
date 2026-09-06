# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粒度分布を画像から測る —— 融合と縁切れが**逆向き**に効き、途中で打ち消し合う。

粉体・骨材・研磨材・薬品の粒子径分布(PSD)を顕微鏡や落下画像から測る、という
仕事です(ISO 13322 の画像解析法)。工程では D10 / D50 / D90 の 3 つの数字で
合否を決めるので、**その 3 つがどこで嘘になるか**を知らずには使えません。

EXTEND: 実際の顕微鏡画像に差し替えるなら :func:`make_scene` が返す辞書の
``img``(観測画像)と ``radii``(撒いた粒子の半径)の対を、撮影画像と
「実際に視野に入った粒子の一覧」に置き換えます。**ラベル画像だけでは足りません**
—— この PoC のいちばん重要な軸(どれとどれが融合したか)はラベル画像に残らない
ので、粒子の中心と半径の表も一緒に持つこと。ふるい分けやレーザー回折の結果を
真値にするのは**別の量を測っているので不可**(体積基準 vs 投影面積基準)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(しきい値 + 連結成分、そのまま数える)を先に測る**。面積率が
   低いうちは D50 が 1 % 以内で当たる。壊れるのは密度が上がってから。
2. ★**壊れ方が 2 つあり、向きが逆**。融合(触れた粒子が 1 個になる)は
   大きい側へ、縁切れ(視野の縁で切れる)は小さい側へ引く。**片方だけ直すと
   もう片方が露出して悪くなる**ことがある。
3. ★★**2 つが打ち消し合う面積率が実在する**。そこでは D50 が真値の 1 % 以内に
   合うのに、内訳は融合 N 件・縁切れ M 件で壊れている。**D50 だけを報告して
   いたら「この条件が最良」として通る**。
4. **融合は形で見つかる**。融合した塊は充填率(solidity)が落ちる ——
   単独粒子の分布とほとんど重ならないので、しきい値 1 本で切り分けられる。
   円形度でも切れるが、solidity のほうが分離が良い(実測で比べる)。
5. ★**縁の規約は 3 通りあり、どれを選ぶかで D50 が動く**。全部数える /
   触れたら捨てる / Miles-Lantuejoul(4 辺のうち 2 辺だけ許す)。**危ないのは
   規約の選択ではなく、推定と真値で違う規約を使うこと**。
6. ★★**個数基準と面積基準は別の分布**。同じ画像から出した D50 が 2 倍以上
   違う。「D50 = 24 µm」と書くとき、どちらの基準かを書かないと意味が無い。
7. **予想が外れた点**: 「解像度を上げれば融合は減る」と踏んでいたが、
   実測では**画素を細かくしても融合の件数は変わらない**。融合は幾何の問題
   (粒子が触れているかどうか)で、標本化の問題ではなかった。効くのは
   **視野あたりの粒子数を減らすこと**だけ。

★この PoC が使う `blob_*` 族は、まさにこの PoC の 1 つ前の `poc_cell_counting`
が「無い」と書いた穴を埋めたものです(2026-09-06)。末尾の「道具の穴」節に
使ってみて分かった残りを挙げてあります。

来歴(公開文献のみ): ISO 13322-1:2014 *Particle size analysis — Image analysis
methods* / Miles, *J. Microscopy* 113 (1978) 257 —— 縁の不偏標本規則 /
Allen, *Powder Sampling and Particle Size Determination* (Elsevier, 2003)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 512             # 視野 [px]
PX_UM = 2.0             # 1 画素の大きさ [µm/px] -> 視野 1.024 mm 角
R_MED = 7.0             # 半径の中央値 [px] = 28 µm 径
R_SIG = 0.42            # 対数正規の σ(自然対数)
R_LO, R_HI = 3.0, 22.0  # 半径の切り詰め [px]
SEED = 11

_LAB = fs.ledger        # blob 族の公開経路


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「撒いた粒子の半径の一覧」                                #
# --------------------------------------------------------------------------- #
def make_scene(n_particles: int, seed: int = SEED, scale: float = 1.0) -> dict:
    """円板を ``n_particles`` 個撒いた 2 値場面と、その真値を返す。

    重なりは**わざと許す**(それがこの PoC の主題)。中心は視野の外にも
    はみ出させる —— 縁で切れた粒子が出ないと縁の規約が測れない。

    ``scale`` は**画素の細かさだけ**を変える。視野も半径も同じ倍率で
    伸ばすので、写っている**物理的な場面は変わらない** —— ここを揃えないと
    「解像度を上げた」つもりで別の(もっと密な)場面を測ることになる
    (2026-09-06 に一度そう書いて、256 px の側だけ 4 倍密になった)。
    """
    rng = np.random.default_rng(seed)
    n_pix = int(round(N_PIX * scale))
    r_med, r_lo, r_hi = R_MED * scale, R_LO * scale, R_HI * scale
    radii = np.clip(r_med * np.exp(R_SIG * rng.standard_normal(n_particles)),
                    r_lo, r_hi)
    # 中心は視野を r_hi ぶん広げた範囲に置く(縁で切れる粒子を作るため)
    cy = rng.uniform(-r_hi, n_pix + r_hi, n_particles)
    cx = rng.uniform(-r_hi, n_pix + r_hi, n_particles)

    img = np.zeros((n_pix, n_pix), bool)
    yy, xx = np.mgrid[0:n_pix, 0:n_pix]
    keep = []
    for r, y0, x0 in zip(radii, cy, cx):
        disc = (yy - y0) ** 2 + (xx - x0) ** 2 <= r * r
        if disc.any():                       # 視野に一部でも入った粒子だけ真値
            img |= disc
            keep.append((r, y0, x0))
    arr = np.asarray(keep, np.float64)
    return {"img": img.astype(np.float64), "radii": arr[:, 0],
            "cy": arr[:, 1], "cx": arr[:, 2], "n_pix": n_pix,
            "px_um": PX_UM / scale,
            "area_fraction": float(img.mean())}


def _fully_inside(scene: dict) -> np.ndarray:
    """視野に**丸ごと**入っている粒子(縁の規約の真値側で使う)。"""
    r, y, x = scene["radii"], scene["cy"], scene["cx"]
    n_pix = scene["n_pix"]
    return (y - r >= 0) & (y + r <= n_pix - 1) & (x - r >= 0) & (x + r <= n_pix - 1)


# --------------------------------------------------------------------------- #
# 分布の要約 —— D10 / D50 / D90 は「どの基準か」で別物                          #
# --------------------------------------------------------------------------- #
def percentiles(diameters: np.ndarray, weights: np.ndarray | None = None) -> dict:
    """累積分布の 10 / 50 / 90 % 点。``weights`` を渡すと面積基準になる。"""
    d = np.asarray(diameters, np.float64)
    if d.size == 0:
        return {"d10": np.nan, "d50": np.nan, "d90": np.nan}
    w = np.ones_like(d) if weights is None else np.asarray(weights, np.float64)
    order = np.argsort(d)
    d, w = d[order], w[order]
    cum = np.cumsum(w)
    cum = cum / cum[-1]
    out = {}
    for key, q in (("d10", 0.10), ("d50", 0.50), ("d90", 0.90)):
        out[key] = float(np.interp(q, cum, d))
    return out


def measure(img: np.ndarray, spacing: float = PX_UM) -> dict:
    """しきい値 → 連結成分 → 物体ごとの特徴量。**この PoC の推定器そのもの**。"""
    lab = _LAB.blob_label(img > 0.5)
    return {"labels": lab, **_LAB.blob_features(lab, spacing=spacing)}


# --------------------------------------------------------------------------- #
# 1. ゼロ点 —— 薄いうちは当たる                                                 #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— しきい値 + 連結成分で D10/D50/D90 を出す")
    print("=" * 78)

    rows = []
    keep = None
    for n in (60, 400):
        sc = make_scene(n)
        f = measure(sc["img"])
        true_d = 2.0 * sc["radii"] * PX_UM
        tp = percentiles(true_d)
        ep = percentiles(f["equiv_diameter"])
        rows.append((sc["area_fraction"], len(sc["radii"]), f["n"], tp, ep))
        if n == 60:
            keep = (sc, f)
        print("  面積率 %4.1f %%  撒いた %4d 個 -> 塊 %4d 個" % (
            100 * sc["area_fraction"], len(sc["radii"]), f["n"]))
        for k in ("d10", "d50", "d90"):
            print("      %s  真値 %6.2f µm   推定 %6.2f µm  (%+6.2f %%)" % (
                k.upper(), tp[k], ep[k], 100 * (ep[k] - tp[k]) / tp[k]))

    sc, f = keep
    figs.save_grid("scene", [sc["img"], _LAB.blob_overlay(sc["img"], f["labels"])],
                   ["撒いた粒子(面積率 %.0f %%)" % (100 * sc["area_fraction"]),
                    "連結成分 %d 個" % f["n"]],
                   title="粒度分布を測る場面(1 px = %.0f µm)" % PX_UM)
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 2-3. 密度を振る —— 融合と縁切れを別々に数える                                 #
# --------------------------------------------------------------------------- #
def _merge_and_edge_counts(scene: dict, f: dict) -> tuple[int, int]:
    """融合した塊の数と、縁に触れた塊の数。

    融合の判定は**真値の側から**: 粒子の中心が同じ塊に 2 つ以上入っていたら
    その塊は融合。推定側の形(solidity)では判定しない —— それだと
    「形で融合を見つけられるか」を測るときに答えを混ぜてしまう。
    """
    lab = f["labels"]
    rr = np.clip(np.round(scene["cy"]).astype(int), 0, lab.shape[0] - 1)
    cc = np.clip(np.round(scene["cx"]).astype(int), 0, lab.shape[1] - 1)
    inside = _fully_inside(scene)
    owner = lab[rr, cc]
    merged = 0
    for idx in range(1, int(lab.max()) + 1):
        if int(np.count_nonzero((owner == idx) & inside)) >= 2:
            merged += 1
    return merged, int(np.count_nonzero(f["touches_border"]))


def section_density_sweep() -> dict:
    print("\n" + "=" * 78)
    print("2-3) 密度を振る —— 融合(過大)と縁切れ(過小)は向きが逆")
    print("=" * 78)
    print("  面積率      塊   融合  縁切れ    D50 の誤差(4 種の平均 ± 散らばり)")

    # ★種を 1 本だけにすると、この曲線の上下は**ただの揺らぎ**になる。
    #   4 本の種で平均と散らばりを分けてから「横切った」と言う。
    seeds = (11, 23, 47, 91)
    frac, d50_mean, d50_sd, merged_n, edge_n = [], [], [], [], []
    rows = []
    for n in (30, 70, 130, 210, 320, 460):
        errs, ms, es, fr, nb = [], [], [], [], []
        for sd in seeds:
            sc = make_scene(n, seed=sd)
            f = measure(sc["img"])
            m, e = _merge_and_edge_counts(sc, f)
            tp = percentiles(2.0 * sc["radii"] * PX_UM)
            ep = percentiles(f["equiv_diameter"])
            errs.append(100 * (ep["d50"] - tp["d50"]) / tp["d50"])
            ms.append(m)
            es.append(e)
            fr.append(100 * sc["area_fraction"])
            nb.append(f["n"])
        frac.append(float(np.mean(fr)))
        d50_mean.append(float(np.mean(errs)))
        d50_sd.append(float(np.std(errs)))
        merged_n.append(float(np.mean(ms)))
        edge_n.append(float(np.mean(es)))
        rows.append((frac[-1], float(np.mean(nb)), merged_n[-1], edge_n[-1],
                     d50_mean[-1], d50_sd[-1]))
        print("   %5.1f %%  %6.1f  %5.1f  %5.1f      %+6.2f %%  ± %4.2f" % rows[-1])

    # 打ち消しの点は「**両方の壊れ方が効いている中で**誤差が最小」の行。
    # 一番薄い行(融合ゼロ)は打ち消しではなく、単に壊れていないだけ。
    active = [r for r in rows if r[2] >= 5.0]
    cancel = min(active, key=lambda r: abs(r[4])) if active else rows[0]
    print("
  ★打ち消しの点: 面積率 %.1f %% で D50 誤差 %+.2f %% ± %.2f —— "
          "**内訳は融合 %.0f 件・縁切れ %.0f 件(塊 %.0f 個中)**。"
          % (cancel[0], cancel[4], cancel[5], cancel[2], cancel[3], cancel[1]))
    print("     D50 だけを見ていたら『この条件が最良』として通る。")
    print("     一番薄い %.1f %% は打ち消しではなく、そもそも壊れていない"
          "(融合 %.0f 件)。" % (rows[0][0], rows[0][2]))

    figs.save_plot("density_sweep",
                   [("D50 の誤差(4 種の平均)", frac, d50_mean),
                    ("ゼロ(真値)", frac, [0.0] * len(frac)),
                    ("+1σ", frac, [m + s for m, s in zip(d50_mean, d50_sd)]),
                    ("-1σ", frac, [m - s for m, s in zip(d50_mean, d50_sd)])],
                   xlabel="面積率 [%]", ylabel="D50 の誤差 [%]",
                   title="密度を上げると D50 は正へ動く(融合が勝つ)",
                   caption="薄いところで 0 なのは正確だから。濃いところで 0 を"
                           "またぐのは融合と縁切れが釣り合っただけ。")
    figs.save_plot("failure_counts",
                   [("融合した塊", frac, merged_n), ("縁に触れた塊", frac, edge_n)],
                   xlabel="面積率 [%]", ylabel="件数(4 種の平均)",
                   title="壊れ方の内訳(D50 の誤差には出てこない)")
    return {"frac": frac, "d50_err": d50_mean, "merged": merged_n,
            "edge": edge_n, "cancel": cancel}


# --------------------------------------------------------------------------- #
# 4. 融合を形で見つける                                                        #
# --------------------------------------------------------------------------- #
def section_detect_merges() -> dict:
    print("\n" + "=" * 78)
    print("4) 融合は形で見つかる —— solidity と circularity を比べる")
    print("=" * 78)

    sc = make_scene(340)
    f = measure(sc["img"])
    lab = f["labels"]
    rr = np.clip(np.round(sc["cy"]).astype(int), 0, lab.shape[0] - 1)
    cc = np.clip(np.round(sc["cx"]).astype(int), 0, lab.shape[1] - 1)
    inside = _fully_inside(sc)
    owner = lab[rr, cc]
    n_seed = np.bincount(owner[inside], minlength=int(lab.max()) + 1)[1:]
    is_merged = n_seed >= 2

    print("  塊 %d 個のうち 融合 %d 個 / 単独 %d 個" % (
        f["n"], int(is_merged.sum()), int((~is_merged).sum())))
    for key in ("solidity", "circularity"):
        v = np.asarray(f[key], np.float64)
        a, b = v[~is_merged], v[is_merged]
        # しきい値を全探索して最良の分離(正しく分けられた割合)を出す
        cand = np.unique(np.round(v, 3))
        acc = [(float(((v >= t) == ~is_merged).mean()), float(t)) for t in cand]
        best, thr = max(acc)
        print("    %-12s 単独 %.3f±%.3f / 融合 %.3f±%.3f  -> 最良 %.1f %% "
              "(しきい値 %.3f)" % (key, a.mean(), a.std(), b.mean(), b.std(),
                                   100 * best, thr))
        if key == "solidity":
            sol_best, sol_thr = best, thr

    # solidity で切って D50 を測り直す
    tp = percentiles(2.0 * sc["radii"][inside] * PX_UM)
    raw = percentiles(f["equiv_diameter"])
    kept = _LAB.blob_select(lab, "solidity", vmin=sol_thr)
    fk = _LAB.blob_features(kept, spacing=PX_UM)
    filt = percentiles(fk["equiv_diameter"])
    print("\n  D50: 真値(丸ごと入った粒子)%.2f µm / 素の塊 %.2f µm (%+.1f %%) / "
          "solidity>=%.3f で %.2f µm (%+.1f %%)  —— 残った塊 %d 個"
          % (tp["d50"], raw["d50"], 100 * (raw["d50"] - tp["d50"]) / tp["d50"],
             sol_thr, filt["d50"], 100 * (filt["d50"] - tp["d50"]) / tp["d50"],
             fk["n"]))

    figs.save_plot("merge_separability",
                   [("単独粒子", np.sort(np.asarray(f["solidity"])[~is_merged]),
                     np.linspace(0, 1, int((~is_merged).sum()))),
                    ("融合した塊", np.sort(np.asarray(f["solidity"])[is_merged]),
                     np.linspace(0, 1, int(is_merged.sum())))],
                   xlabel="solidity(充填率)", ylabel="累積割合",
                   title="融合した塊は充填率が落ちる(分離 %.0f %%)" % (100 * sol_best))
    figs.save_grid("merge_filter",
                   [_LAB.blob_overlay(sc["img"], lab),
                    _LAB.blob_overlay(sc["img"], kept)],
                   ["素の塊 %d 個" % f["n"], "solidity>=%.2f の %d 個" % (sol_thr, fk["n"])],
                   title="形で融合を落とす")
    return {"best": sol_best, "thr": sol_thr}


# --------------------------------------------------------------------------- #
# 5. 縁の規約 3 通り                                                            #
# --------------------------------------------------------------------------- #
def section_edge_rules() -> dict:
    print("\n" + "=" * 78)
    print("5) 縁の規約 —— 全部数える / 触れたら捨てる / Miles の 2 辺規則")
    print("=" * 78)

    sc = make_scene(160)
    f = measure(sc["img"])
    lab = f["labels"]
    inside = _fully_inside(sc)
    truth_all = percentiles(2.0 * sc["radii"] * PX_UM)
    truth_in = percentiles(2.0 * sc["radii"][inside] * PX_UM)

    touch = np.asarray(f["touches_border"], bool)
    # Miles-Lantuejoul: 4 辺のうち「上」と「左」に触れたものだけ捨てる。
    # 視野を並べたときに 1 粒子が 1 回だけ数えられる = 不偏標本になる規則。
    r0 = np.asarray(f["bbox_r0"], np.int32)
    c0 = np.asarray(f["bbox_c0"], np.int32)
    miles = ~((r0 == 0) | (c0 == 0))

    d = np.asarray(f["equiv_diameter"], np.float64)
    rules = [("全部数える", np.ones_like(touch), truth_all),
             ("触れたら捨てる", ~touch, truth_in),
             ("Miles の 2 辺規則", miles, truth_all)]
    rows = []
    print("  規約                塊    D10      D50      D90    (D50 の誤差)")
    for name, keep, truth in rules:
        p = percentiles(d[keep])
        err = 100 * (p["d50"] - truth["d50"]) / truth["d50"]
        rows.append([name, str(int(keep.sum())), "%.2f" % p["d10"],
                     "%.2f" % p["d50"], "%.2f" % p["d90"], "%+.2f %%" % err])
        print("   %-16s %4d  %6.2f   %6.2f   %6.2f   (%+.2f %%)" % (
            name, int(keep.sum()), p["d10"], p["d50"], p["d90"], err))
    print("   %-16s   -   %6.2f   %6.2f   %6.2f" % (
        "真値(全部)", truth_all["d10"], truth_all["d50"], truth_all["d90"]))
    print("   %-16s   -   %6.2f   %6.2f   %6.2f" % (
        "真値(丸ごと)", truth_in["d10"], truth_in["d50"], truth_in["d90"]))
    print("\n  ★危ないのは規約の選択ではなく、**推定と真値で違う規約を使うこと**。"
          "\n     「触れたら捨てる」を『全部』の真値と比べると %+.2f %% ずれる。"
          % (100 * (percentiles(d[~touch])["d50"] - truth_all["d50"])
             / truth_all["d50"]))

    figs.save_table("edge_rules", ["規約", "塊", "D10 µm", "D50 µm", "D90 µm", "D50 誤差"],
                    rows, title="縁の規約で D50 が動く")
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 6. 個数基準 vs 面積基準                                                       #
# --------------------------------------------------------------------------- #
def section_number_vs_area() -> dict:
    print("\n" + "=" * 78)
    print("6) 個数基準と面積基準は別の分布 —— 同じ画像で D50 が 2 倍違う")
    print("=" * 78)

    sc = make_scene(160)
    f = measure(sc["img"])
    d = np.asarray(f["equiv_diameter"], np.float64)
    a = np.asarray(f["area"], np.float64)
    num = percentiles(d)
    area = percentiles(d, weights=a)
    print("   基準       D10      D50      D90")
    print("   個数     %6.2f   %6.2f   %6.2f  µm" % (num["d10"], num["d50"], num["d90"]))
    print("   面積     %6.2f   %6.2f   %6.2f  µm" % (area["d10"], area["d50"], area["d90"]))
    print("   比       %6.2f   %6.2f   %6.2f" % (
        area["d10"] / num["d10"], area["d50"] / num["d50"], area["d90"] / num["d90"]))
    print("\n  「D50 = %.1f µm」と書くとき、どちらの基準かを書かないと"
          " %.1f µm と取り違えられる。" % (num["d50"], area["d50"]))

    order = np.argsort(d)
    figs.save_plot("number_vs_area",
                   [("個数基準", d[order], np.linspace(0, 1, d.size)),
                    ("面積基準", d[order], np.cumsum(a[order]) / a.sum())],
                   xlabel="等価直径 [µm]", ylabel="累積割合",
                   title="同じ画像・同じ塊から出した 2 本の累積分布")
    return {"num": num, "area": area}


# --------------------------------------------------------------------------- #
# 7. 予想が外れた —— 解像度では融合は減らない                                   #
# --------------------------------------------------------------------------- #
def section_resolution() -> dict:
    print("\n" + "=" * 78)
    print("7) ★予想が外れた —— 画素を細かくしても融合は減らない")
    print("=" * 78)
    print("  画素 [µm]  視野 [px]   塊    融合   縁切れ   D50 誤差")

    px_list, merged, errs = [], [], []
    for scale in (0.5, 1.0, 2.0):
        # 同じ**物理的な**場面を、粗い画素・標準・細かい画素で見る
        sc = make_scene(240, scale=scale)
        px_um = sc["px_um"]
        f = measure(sc["img"], spacing=px_um)
        m, e = _merge_and_edge_counts(sc, f)
        tp = percentiles(2.0 * sc["radii"] * px_um)
        ep = percentiles(f["equiv_diameter"])
        err = 100 * (ep["d50"] - tp["d50"]) / tp["d50"]
        px_list.append(px_um)
        merged.append(m)
        errs.append(err)
        print("   %6.2f     %5d    %4d   %4d    %4d    %+6.2f %%" % (
            px_um, sc["n_pix"], f["n"], m, e, err))
    print("\n  融合の件数は画素の細かさでほとんど動かない —— 触れているかどうかは"
          "\n  幾何の問題で、標本化の問題ではない。効くのは**視野あたりの粒子数**だけ。")
    return {"px": px_list, "merged": merged, "err": errs}


# --------------------------------------------------------------------------- #
# 8. 道具の穴 —— 使ってみて分かった残り                                         #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で `blob_*` 族を使ってみて)")
    print("=" * 78)

    m = np.zeros((40, 60), bool)
    m[5:15, 5:15] = True
    m[20:35, 30:55] = True
    lab = _LAB.blob_label(m)

    # (a) 融合した塊を**割る**口が無い(距離変換 + 分水嶺が 2-D では非公開)
    import segmentation as seg
    assert hasattr(seg, "watersheds_marker"), "モジュールから消えた"
    assert not hasattr(fs, "watersheds_marker"), "公開された(この節を書き換えること)"
    assert not hasattr(fs.ledger, "watersheds_marker")
    print("  (a) 2-D の分水嶺が公開経路に無い(segmentation.watersheds_marker は"
          "モジュールにだけ在る)。融合した塊を割れない。")

    # (b) 距離変換が最大値で正規化される(画素単位の距離が取れない)
    dn = np.asarray(fs.apply(m.astype(np.float64), "distance_transform"))
    assert abs(float(dn.max()) - 1.0) < 1e-9, float(dn.max())
    print("  (b) 進化 op の distance_transform は最大値で正規化するので、"
          "画素単位の距離が取れない(分水嶺の種を作るのに要る)。")

    # (c) 累積分布の分位点(D10/D50/D90)を出す口が無い —— この PoC は自前
    assert not hasattr(fs, "size_percentiles") and not hasattr(fs.ledger, "size_percentiles")
    print("  (c) 重みつき累積分布の分位点を出す op が無い。粒度分布の要約は"
          "この 3 つの数字なので、族に入れる価値はある(次の波)。")

    # (d) 塊を 1 つずつ切り出す口はあるが、**外接箱で切り抜く**口が無い
    reg = _LAB.blob_region(lab, 2)
    assert reg.shape == m.shape, "全画面のまま返る"
    print("  (d) blob_region は**全画面**の bool を返す。物体だけを外接箱で"
          "切り出す口が無く、呼び手が bbox_* から自分で切っている。")

    # (e) 台帳は在るのにファサード(fs.<名前>)には出ていない
    assert hasattr(fs.ledger, "blob_label") and not hasattr(fs, "blob_label")
    print("  (e) blob_* は fullseye.ledger からしか呼べない(piv 族と同じ)。"
          "1 行ファサードの規約とは食い違っている。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("粒度分布を画像から測る —— 融合と縁切れが打ち消し合う")
    print("視野 %d px x %.0f µm/px = %.2f mm 角 / 半径の中央値 %.0f px" % (
        N_PIX, PX_UM, N_PIX * PX_UM / 1000.0, R_MED))
    print("=" * 78)

    section_zero_point()
    sweep = section_density_sweep()
    section_detect_merges()
    section_edge_rules()
    section_number_vs_area()
    section_resolution()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * D50 の誤差が小さい点は「正確」ではなく「打ち消し」"
          "(面積率 %.1f %% で %+.2f %%、内訳は融合 %.0f 件・縁切れ %.0f 件)。"
          % (sweep["cancel"][0], sweep["cancel"][4],
             sweep["cancel"][2], sweep["cancel"][3]))
    print("  * 融合は充填率で見つかる。縁切れは規約を推定と真値で揃える。")
    print("  * 個数基準と面積基準を書き分ける。")
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
