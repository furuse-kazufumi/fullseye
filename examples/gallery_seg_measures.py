# -*- coding: utf-8 -*-
"""事例: 分割の評価(分割表・Hausdorff・平均表面距離)・Chan–Vese のエネルギー・成分木・円の重なり・ボロノイを独立の検算で確かめる

平たく言うと:
  セグメンテーションの台帳 op(segeval / segcontour / seggraph / segworld)を、答えが手計算か総当たりで出せる入力で
  1 本ずつ呼ぶ。各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * seg_confusion_table        —— 手で作った 2 つのラベル画像の画素数の表、1 つの大きな予測を 2 つの真が選ぶ(claims = 2)
  * seg_hausdorff              —— 同じ境界の規約で取り出した画素を scipy の cdist(総当たりの距離)で測った最大・95 百分位
  * seg_mean_surface_distance  —— 同じ総当たりの平均と RMS、同一の分割で 0
  * chan_vese_energy           —— 正方形の 2 値画像: 鋭い版は 周長 4s・内外の平均 1 / 0・当てはめ 0、
                                  滑らかな版は H_ε・δ_ε・前進差分を式どおりに書き直した値と 1e-9 で一致
  * max_tree                   —— 各しきい値 h で {f ≥ h} を ndimage.label した成分の数・面積を総当たりで数えたものと一致
  * lens_area                  —— d = 0 で πr²、d = r で r²(2π/3 − √3/2)、d ≥ 2r で 0、細かい格子の数え上げと
  * voronoi_cells              —— 2 つの種で 20×20 を半分ずつ(内部の辺 1 本・長さ 20)、4 つの種で 100 ずつ(辺 4 本・計 40)

    py -3.11 examples/gallery_seg_measures.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial.distance import cdist  # noqa: E402

import segcontour as SC  # noqa: E402
import segeval as SE  # noqa: E402
import seggraph as GR  # noqa: E402
import segworld as SW  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_confusion() -> None:
    t = np.zeros((6, 8), int)
    t[:, :4] = 1
    t[:, 4:] = 2
    p = np.zeros((6, 8), int)
    p[:, 1:7] = 5                                            # 1 つの大きな予測が両方にまたがる
    r = SE.seg_confusion_table(p, t)
    # 行 = 真 (1, 2)、列 = 予測 (0, 5): 真 1 は列 0 が 6 画素・列 5 が 18 画素、真 2 も同じ
    want = np.array([[6, 18], [6, 18]])
    check("seg_confusion_table", "真 = 左右 2 枚、予測 = 中央の 1 枚(背景 0 が両端)", f"表 {want.tolist()}、claims[5] = 2、1 対 1 でない",
          f"{r['table'].tolist()}、claims {r['claims'].tolist()}、unique {r['unique_matching']}",
          np.array_equal(r["table"], want) and r["labels_pred"].tolist() == [0, 5] and r["claims"].tolist() == [0, 2]
          and not r["unique_matching"] and r["pred_of_true"].tolist() == [5, 5])
    p2 = np.where(t == 1, 7, 9)
    r2 = SE.seg_confusion_table(p2, t)
    check("seg_confusion_table", "番号だけ違う同じ分割(1→7、2→9)", "対角 24 / 24、1 対 1、相手 (7, 9)",
          f"{r2['table'].tolist()}、unique {r2['unique_matching']}、{r2['pred_of_true'].tolist()}",
          np.array_equal(r2["table"], [[24, 0], [0, 24]]) and r2["unique_matching"] and r2["pred_of_true"].tolist() == [7, 9])


def _bnd(lab):
    """境界画素 = 右か下の隣とラベルが違う画素(segeval の docstring の規約を書き直したもの)。"""
    b = np.zeros(lab.shape, bool)
    b[:, :-1] |= lab[:, 1:] != lab[:, :-1]
    b[:-1, :] |= lab[1:, :] != lab[:-1, :]
    return np.argwhere(b)


def demo_surface() -> None:
    yy, xx = np.mgrid[0:40, 0:40]
    t = ((yy - 20) ** 2 + (xx - 18) ** 2 <= 10 ** 2).astype(int)
    p = ((np.abs(yy - 21) <= 8) & (np.abs(xx - 22) <= 9)).astype(int)
    D = cdist(_bnd(p), _bnd(t))
    d_pt, d_tp = D.min(axis=1), D.min(axis=0)
    hd = max(d_pt.max(), d_tp.max())
    h95 = max(np.percentile(d_pt, 95), np.percentile(d_tp, 95))
    r = SE.seg_hausdorff(p, t)
    check("seg_hausdorff", "円(r = 10)と、ずらした長方形", f"総当たり: HD {hd:.6f}、HD95 {h95:.6f}",
          f"{r['hausdorff']:.6f}、{r['hausdorff_percentile']:.6f}",
          abs(r["hausdorff"] - hd) < 1e-12 and abs(r["hausdorff_percentile"] - h95) < 1e-12
          and abs(r["directed_pred_to_true"] - d_pt.max()) < 1e-12)
    allv = np.concatenate([d_pt, d_tp])
    m = SE.seg_mean_surface_distance(p, t)
    check("seg_mean_surface_distance", "同じ 2 つ", f"総当たり: ASSD {allv.mean():.6f}、RMS {math.sqrt(np.mean(allv ** 2)):.6f}",
          f"{m['assd']:.6f}、{m['rms']:.6f}、境界 {m['n_pred_boundary']} / {m['n_true_boundary']}",
          abs(m["assd"] - allv.mean()) < 1e-12 and abs(m["rms"] - math.sqrt(np.mean(allv ** 2))) < 1e-12
          and m["n_pred_boundary"] == len(d_pt) and m["n_true_boundary"] == len(d_tp))
    z = SE.seg_mean_surface_distance(t, t)
    zh = SE.seg_hausdorff(t, t)
    check("seg_mean_surface_distance", "同一の分割", "ASSD = HD = 0", f"{z['assd']}、{zh['hausdorff']}", z["assd"] == 0.0 and zh["hausdorff"] == 0.0)
    sh = np.roll(t, 3, axis=1)
    check("seg_hausdorff", "円を右へ 3 画素ずらす", "HD = 3(縁の画素が 3 だけ動く)", f"{SE.seg_hausdorff(sh, t)['hausdorff']}",
          abs(SE.seg_hausdorff(sh, t)["hausdorff"] - 3.0) < 1e-12)


def demo_chan_vese() -> None:
    H = W = 32
    s = 12
    img = np.zeros((H, W))
    img[10:10 + s, 8:8 + s] = 1.0
    mask = img > 0.5
    r = SC.chan_vese_energy(img, mask, mu=0.5, nu=0.25)
    check("chan_vese_energy", f"{s}×{s} の正方形(マスクで渡す)、μ = 0.5、ν = 0.25", f"鋭い版: 周長 4s = {4 * s}、c1 = 1、c2 = 0、E = 0.5·48 + 0.25·144 = 60",
          f"{r['perimeter_sharp']}、{r['c1_sharp']}、{r['c2_sharp']}、{r['energy_sharp']}",
          r["perimeter_sharp"] == 48 and r["c1_sharp"] == 1.0 and r["c2_sharp"] == 0.0 and r["energy_sharp"] == 60.0)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    phi = np.maximum(np.abs(yy - 15.5), np.abs(xx - 13.5)) - 6.0    # 内側 < 0 の正方形(チェビシェフ距離)
    mu, nu, l1, l2, eps, eta = 0.2, 0.05, 1.0, 2.0, 1.0, 0.1
    rs = SC.chan_vese_energy(img, phi, mu=mu, nu=nu, lambda1=l1, lambda2=l2, eps=eps, eta=eta)
    hin = 0.5 * (1 + (2 / math.pi) * np.arctan(-phi / eps))
    dl = (eps / math.pi) / (eps ** 2 + phi ** 2)
    dx = np.zeros_like(phi)
    dy = np.zeros_like(phi)
    dx[:, :-1] = np.diff(phi, axis=1)
    dy[:-1, :] = np.diff(phi, axis=0)
    length = float(np.sum(dl * np.sqrt(dx ** 2 + dy ** 2 + eta ** 2)))
    c1 = float((img * hin).sum() / hin.sum())
    c2 = float((img * (1 - hin)).sum() / (1 - hin).sum())
    E = mu * length + nu * hin.sum() + l1 * np.sum((img - c1) ** 2 * hin) + l2 * np.sum((img - c2) ** 2 * (1 - hin))
    check("chan_vese_energy", "φ = チェビシェフ距離 − 6、λ2 = 2", f"式 (H_ε, δ_ε, 前進差分) を書き直した E = {E:.9f}",
          f"{rs['energy']:.9f}、c1 {rs['c1']:.6f}(手 {c1:.6f})", abs(rs["energy"] - E) < 1e-9 and abs(rs["c1"] - c1) < 1e-12
          and abs(rs["c2"] - c2) < 1e-12 and abs(rs["length"] - length) < 1e-9)


def demo_max_tree() -> None:
    img = np.zeros((12, 14))
    img[2:6, 2:6] = 3
    img[3:5, 3:5] = 5
    img[7:11, 3:12] = 2
    img[8:10, 4:6] = 4
    img[8:10, 9:11] = 4
    img[8, 10] = 6
    r = GR.max_tree(img, connectivity=4)
    nodes, areas = 0, []
    for h in np.unique(img):
        lab, n = ndi.label(img >= h)
        for k in range(1, n + 1):
            comp = lab == k
            if np.any(img[comp] == h):                    # その値の画素を含む成分 = 木の節
                nodes += 1
                areas.append(int(comp.sum()))
    can = r["canonical"]
    got_areas = sorted(r["area"][can].tolist())
    check("max_tree", "段々の山 12×14(値 0..6、4 連結)", f"総当たりの節 {nodes} 個、面積 {sorted(areas)}",
          f"{r['n_nodes']} 個、{got_areas}", r["n_nodes"] == nodes and got_areas == sorted(areas))
    par = r["parent"].ravel()
    f = img.ravel()
    check("max_tree", "親の値 ≤ 子の値、根は最小値で面積 = 画素数", f"違反 0、根の面積 {img.size}",
          f"違反 {int(np.count_nonzero(f[par] > f))}、根の面積 {r['area'].ravel()[r['root']]}",
          not np.any(f[par] > f) and r["area"].ravel()[r["root"]] == img.size)


def demo_lens_voronoi() -> None:
    r = 2.0
    check("lens_area", "d = 0(同じ円)", f"πr² = {math.pi * r * r:.12f}", f"{SW.lens_area(r, 0.0):.12f}", abs(SW.lens_area(r, 0.0) - math.pi * r * r) < 1e-12)
    want = r * r * (2 * math.pi / 3 - math.sqrt(3) / 2)
    check("lens_area", "d = r", f"r²(2π/3 − √3/2) = {want:.12f}", f"{SW.lens_area(r, r):.12f}", abs(SW.lens_area(r, r) - want) < 1e-12)
    check("lens_area", "d = 2r と d = 5", "0(接するだけ・離れている)", f"{SW.lens_area(r, 2 * r)}、{SW.lens_area(r, 5.0)}",
          SW.lens_area(r, 2 * r) == 0.0 and SW.lens_area(r, 5.0) == 0.0)
    g = (np.arange(4000) + 0.5) / 4000 * 4.0 - 2.0                 # 格子の中点(x ∈ [−2, 2])
    X, Y = np.meshgrid(g, g)
    d = 1.3
    cnt = np.count_nonzero((X ** 2 + Y ** 2 <= r * r) & ((X - d) ** 2 + Y ** 2 <= r * r)) * (4.0 / 4000) ** 2
    check("lens_area", f"d = {d}、4000² の格子で数える", f"格子 {cnt:.5f}(± 1e-3)", f"{SW.lens_area(r, d):.5f}", abs(SW.lens_area(r, d) - cnt) < 1e-3)

    v2 = SW.voronoi_cells([[9.5, 4.0], [9.5, 15.0]], (20, 20))
    check("voronoi_cells", "種 (9.5, 4)・(9.5, 15)、20×20(op の下限は 16×16)", "x = 9.5 で二分: 面積 200 / 200、内部の辺 1 本・長さ 20",
          f"{v2['areas'].tolist()}、{v2['n_edges']} 本・{v2['edge_length_total']}",
          np.allclose(v2["areas"], [200, 200]) and v2["n_edges"] == 1 and abs(v2["edge_length_total"] - 20) < 1e-12)
    seeds = [[4.5, 4.5], [4.5, 14.5], [14.5, 4.5], [14.5, 14.5]]
    v4 = SW.voronoi_cells(seeds, (20, 20))
    check("voronoi_cells", "格子状の 4 つの種", "面積 100 ずつ(和 400)、内部の辺 4 本・計 40、各セルの内部の辺 20",
          f"{v4['areas'].tolist()}、{v4['n_edges']} 本・{v4['edge_length_total']}、{v4['perimeter_internal'].tolist()}",
          np.allclose(v4["areas"], 100) and v4["n_edges"] == 4 and abs(v4["edge_length_total"] - 40) < 1e-12
          and np.allclose(v4["perimeter_internal"], 20))


def main() -> int:
    t0 = time.time()
    demo_confusion()
    demo_surface()
    demo_chan_vese()
    demo_max_tree()
    demo_lens_voronoi()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
