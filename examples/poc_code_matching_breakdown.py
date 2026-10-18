# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""明るさの値ではなく「変化の向き」で探す —— 符号系の頑健照合 4 種と NCC の破綻点を並べる。

    py -3.11 examples/poc_code_matching_breakdown.py

テンプレート照合の定番の正規化相互相関(NCC)は、明るさの**値**を比べる。照明がテンプレートの
一部だけ変わる・光沢が飛ぶ・手前に物が入ると、値の相関は大きく崩れる。明るさの**変化の向き**を
符号にして比べる照合の族は、学習した特徴を使わずに、どこまで残り、どこで壊れるか。
:mod:`codematch` の 6 op をこの PoC で採点する。式は次の文献から再実装した(文・図・数値表は
写していない。著者が再現を承認したものではない):

  [1] F. Ullah, S. Kaneko, S. Igarashi, "Orientation Code Matching for Robust Object Search",
      IEICE Trans. Inf. & Syst. E84-D(8), 2001.(方向符号照合 OCM)
  [2] S. Kaneko, I. Murase, S. Igarashi, "Robust image registration by increment sign
      correlation", Pattern Recognition 35(10), 2002.(増分符号相関 ISC)
  [3] S. Kaneko, Y. Satoh, S. Igarashi, "Using selective correlation coefficient for robust
      image registration", Pattern Recognition 36(5), 2003.(選択的相関係数 SCC、拡張マスク)
  [4] Y. Satoh, S. Kaneko, Y. Niwa, K. Yamamoto, "Robust object detection using a Radial Reach
      Filter (RRF)", Systems and Computers in Japan 35(10), 2004.(背景との比較 RRF)

この PoC が測る主張:

1. **式どおりに数えている**(第 1 章)。画素ごとの総当たり(第 2 実装)と OCM / ISC は整数で一致、
   SCC は 1e-12 以内。マスクが全部立つとき SCC は既存の NCC(``find_ncc_model`` の核)と 1e-9 で一致。
   ISC と RRF は狭義単調な明るさの変換で 1 ビットも変わらない。OCM は rot90 と可換で、巡回差を
   絶対差にすり替えた探針ではその門が落ちる。
2. **確率モデルが当たる**(第 2 章)。正解位置の ISC の値と SCC のマスク率は、雑音の無い場面の増分と
   雑音 σ から閉形式で予言でき、全試行の z が ±4.5 に収まる。
3. **どこで壊れるか**(第 3 章)。公開の実写 5 枚から切ったテンプレートに、遮蔽(別の写真の質感)・
   局所の飽和ハイライト・照明のむら(ガンマ × 片側の減光)・回転を段階的に掛け、1 px 以内で
   当たった割合を数える。NCC が最初に崩れ、符号系(OCM / ISC)が残る。SCC は NCC より残るが
   OCM / ISC には届かない。回転には 4 種とも弱い(10° で半分を割る)。
4. **決まらないものは決めない**(第 4 章)。平坦なテンプレートには符号系 3 種が値を返さず拒否し、
   NCC は自信ありげにどこかを返す。
5. **背景との比較**(第 5 章)。RRF は全体のガンマ変化と影の内側を前景にせず、差分の閾値は崩れる。

素材: scikit-image 同梱の camera / astronaut / coffee / chelsea / clock(CC0・パブリックドメイン)、
遮蔽物の質感は gravel(CC0)。テンプレートは元画像の切り抜き(雑音なし)、場面は σ = 0.01 の
正規雑音を足したもの。scikit-image が無ければ止まる(実写でしか意味が無いので黙って通さない)。
``CI=1`` ではテンプレートの数を減らして短く走らせる(門の閾値は試行数から決まるので、そのまま効く)。
"""
from __future__ import annotations

import itertools
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import codematch as C  # noqa: E402
import examplefig as figs  # noqa: E402
import matching  # noqa: E402
import ops  # noqa: E402
import realdata  # noqa: E402

TS = 32                      # テンプレートの一辺 [px](偶数 = SCC の組が全列を覆う)
NOISE = 0.01                 # 場面の雑音 σ([0, 1] の明るさ)
NAMES = ("camera", "astronaut", "coffee", "chelsea", "clock")
METHODS = ("NCC", "OCM", "ISC", "SCC")
COLORS = {"NCC": (0.90, 0.62, 0.0), "OCM": (0.0, 0.45, 0.70), "ISC": (0.0, 0.62, 0.45),
          "SCC": (0.80, 0.47, 0.65), "truth": (1.0, 1.0, 1.0)}
GRIDS = {
    "occlusion": ([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], "遮蔽率(テンプレートの面積比)"),
    "highlight": ([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6], "飽和したハイライトの面積比"),
    "shading": ([0.0, 0.3, 0.6, 0.8, 0.9, 0.95], "片側の減光の深さ(× ガンマ 0.5〜2)"),
    "rotation": ([0.0, 5.0, 10.0, 15.0, 20.0, 30.0], "回転 [度]"),
}
Z_MAX = 4.5                  # 正規なら 1,000 試行で 1 回超える確率 0.7 %
Z_PAIR = 3.0                 # 2 群の比率の差の片側 z


# --------------------------------------------------------------------------- #
# 素材                                                                         #
# --------------------------------------------------------------------------- #
def _half(a):
    h, w = a.shape
    a = a[: h // 2 * 2, : w // 2 * 2]
    return a.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def load_images():
    out = {}
    for n in NAMES:
        a = realdata.sample_photo(n)
        while max(a.shape) > 300:
            a = _half(a)
        out[n] = a
    return out


def pick_templates(img, n, seed):
    """質感のある 32 x 32 を n 枚(標準偏差 ≥ 0.06 かつ Sobel の和 > 0.05 の画素が 3 割以上)。"""
    rr = np.random.default_rng(seed)
    gx = ndimage.sobel(img, axis=1, mode="nearest")
    gy = ndimage.sobel(img, axis=0, mode="nearest")
    strong = (np.abs(gx) + np.abs(gy)) > 0.05
    out = []
    for _ in range(20000):
        if len(out) >= n:
            break
        y = int(rr.integers(8, img.shape[0] - TS - 8))
        x = int(rr.integers(8, img.shape[1] - TS - 8))
        t = img[y:y + TS, x:x + TS]
        if t.std() >= 0.06 and strong[y:y + TS, x:x + TS].mean() >= 0.3:
            if all(max(abs(y - a), abs(x - b)) > TS // 2 for a, b in out):
                out.append((y, x))
    return out


def perturb(img, y, x, kind, level, rr, occ_tex):
    """場面(雑音なし)を返す。雑音は呼び手が足す(確率モデルの章が雑音なしの場面を使う)。"""
    s = img.copy()
    if kind == "occlusion":
        wcol = int(round(level * TS))
        if wcol > 0:
            oy = int(rr.integers(0, occ_tex.shape[0] - TS))
            ox = int(rr.integers(0, occ_tex.shape[1] - TS))
            tex = occ_tex[oy:oy + TS, ox:ox + TS]
            tex = (tex - tex.mean()) / (tex.std() + 1e-9) * rr.uniform(0.05, 0.2) + rr.uniform(0.2, 0.8)
            side = int(rr.integers(0, 4))
            blk = s[y:y + TS, x:x + TS]
            if side == 0:
                blk[:, :wcol] = tex[:, :wcol]
            elif side == 1:
                blk[:, TS - wcol:] = tex[:, TS - wcol:]
            elif side == 2:
                blk[:wcol, :] = tex[:wcol, :]
            else:
                blk[TS - wcol:, :] = tex[TS - wcol:, :]
    elif kind == "highlight":
        if level > 0:
            rad = math.sqrt(level * TS * TS / math.pi)
            cy = y + rr.uniform(0.25, 0.75) * TS
            cx = x + rr.uniform(0.25, 0.75) * TS
            yy, xx = np.mgrid[:s.shape[0], :s.shape[1]]
            d = np.hypot(yy - cy, xx - cx)
            w = np.clip((rad + 1.5 - d) / 3.0, 0, 1)
            s = np.minimum(s * (1 - w) + w + 0.6 * np.exp(-(d / (rad + 4)) ** 2), 1.0)
    elif kind == "shading":
        ang = rr.uniform(0, 2 * math.pi)
        yy, xx = np.mgrid[:s.shape[0], :s.shape[1]]
        u = np.clip(((yy - y - TS / 2) * math.sin(ang) + (xx - x - TS / 2) * math.cos(ang)) / TS + 0.5, 0, 1)
        s = (s ** rr.uniform(0.5, 2.0)) * (1 - level * u)
    elif kind == "rotation":
        phi = math.radians(level) * (1 if rr.random() < 0.5 else -1)
        cy, cx = y + (TS - 1) / 2, x + (TS - 1) / 2
        yy, xx = np.mgrid[:s.shape[0], :s.shape[1]].astype(float)
        ys = cy + (yy - cy) * math.cos(phi) - (xx - cx) * math.sin(phi)
        xs = cx + (yy - cy) * math.sin(phi) + (xx - cx) * math.cos(phi)
        s = ndimage.map_coordinates(img, [ys, xs], order=3, mode="reflect")
    return s


def ncc_locate(scene, tpl):
    """既存の NCC(``ops._ncc_map``、``ncc_locate`` の核)。同点は 12 桁に丸めて raster 順。"""
    m = ops._ncc_map(scene, tpl)
    i = int(np.argmax(np.round(m, 12)))
    r, c = np.unravel_index(i, m.shape)
    return int(r) - TS // 2, int(c) - TS // 2, m


def run_methods(scene, tpl):
    out = {}
    r, c, _ = ncc_locate(scene, tpl)
    out["NCC"] = (r, c)
    for name, f in (("OCM", C.ocm_match), ("ISC", C.isc_match), ("SCC", C.scc_match)):
        try:
            res = f(scene, tpl)
            out[name] = (res["row_tl"], res["col_tl"])
        except ValueError:
            out[name] = None
    return out


def _phi(z):
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(z) / math.sqrt(2.0)))


def predicted_z(clean, noisy, y, x, tpl):
    """正解位置の ISC と SCC のマスク率(基本・拡張)の z(閉形式の期待値と分散)。"""
    win = clean[y:y + TS, x:x + TS]
    s2 = math.sqrt(2.0) * NOISE
    # ISC(行方向の増分)。隣の増分は画素を 1 つ共有するので分散は独立の 3 倍以下で抑える
    p1 = _phi(np.diff(win, axis=1) / s2)
    pa = np.where(np.diff(tpl, axis=1) >= 0, p1, 1 - p1)
    meas = C.isc_match(noisy[y:y + TS, x:x + TS], tpl)["score"]
    z_isc = (meas - pa.mean()) / math.sqrt(3 * (pa * (1 - pa)).sum() / pa.size ** 2)
    # SCC の組(画素を共有しない → 独立)
    p1 = _phi((win[:, 1::2] - win[:, 0::2]) / s2)
    pa = np.where(tpl[:, 1::2] >= tpl[:, 0::2], p1, 1 - p1)
    sub = noisy[y:y + TS, x:x + TS]
    zs = {}
    for ext in (False, True):
        mf = C.scc_match(sub, tpl, mask_extension=ext, min_mask_fraction=0.0)["mask_fraction"]
        if not ext:
            mean, var = 2 * pa.sum() / tpl.size, 4 * (pa * (1 - pa)).sum() / tpl.size ** 2
        else:
            q = np.stack([pa[0::2, 0::2], pa[0::2, 1::2], pa[1::2, 0::2], pa[1::2, 1::2]])
            keep = np.zeros(q.shape[1:])
            for c in itertools.product([0, 1], repeat=4):
                if sum(c) >= 3:
                    keep += np.prod([q[i] if c[i] else 1 - q[i] for i in range(4)], axis=0)
            mean, var = 8 * keep.sum() / tpl.size, 64 * (keep * (1 - keep)).sum() / tpl.size ** 2
        zs[ext] = (mf - mean) / math.sqrt(var)
    return z_isc, zs[False], zs[True]


# --------------------------------------------------------------------------- #
# 第 1 章: 式どおりに数えている                                                  #
# --------------------------------------------------------------------------- #
def chapter_exact(imgs, tpls):
    print("== 第 1 章: 第 2 実装・既存の NCC・定理 ==")
    img = imgs["camera"][100:140, 100:144]
    tpl = img[9:21, 7:21]
    noisy = img + NOISE * np.random.default_rng(1).standard_normal(img.shape)
    # 総当たり(論文の式を画素ごとに)
    n = 16
    ci, ct = C._codes(noisy, n, 0.05), C._codes(tpl, n, 0.05)
    oh, ow = noisy.shape[0] - 11, noisy.shape[1] - 13
    bo = np.zeros((oh, ow))
    bi = np.zeros((oh, ow))
    for yy in range(oh):
        for xx in range(ow):
            m, q = ct.astype(int), ci[yy:yy + 12, xx:xx + 14].astype(int)
            d = np.where(m == n, 0.0, np.where(q == n, n / 4, np.minimum(abs(m - q), n - abs(m - q))))
            bo[yy, xx] = 1 - d.sum() / tpl.size / (n / 2)
            w = noisy[yy:yy + 12, xx:xx + 14]
            bi[yy, xx] = ((np.diff(w, axis=1) >= 0) == (np.diff(tpl, axis=1) >= 0)).mean()
    ro = C.ocm_match(noisy, tpl, min_valid=1, min_valid_fraction=0)["score_map"]
    ri = C.isc_match(noisy, tpl, min_valid=1)["score_map"]
    assert np.array_equal(ro, bo) and np.array_equal(ri, bi)
    print("OCM / ISC = 画素ごとの総当たり(%d 位置すべて、整数で完全一致)" % bo.size)

    # SCC = 既存の NCC(マスクが全部立つとき): 全テンプレートで、ガンマ 2.2 の場面の正解位置
    worst = 0.0
    cnt = 0
    for name, lst in tpls.items():
        for (y, x) in lst:
            t = imgs[name][y:y + TS, x:x + TS]
            sc = imgs[name] ** 2.2
            sub = sc[y - 4:y + TS + 4, x - 4:x + TS + 4]
            r = C.scc_match(sub, t)
            assert r["mask_fraction_map"][4, 4] == 1.0          # 正解位置でマスクが全部立つ
            ref = matching._ncc_map(t, sub)[4, 4]
            worst = max(worst, abs(r["score_map"][4, 4] - ref))
            cnt += 1
    assert worst < 1e-9
    print("SCC = 既存の NCC(matching._ncc_map)、マスクが全部立つ %d 件で最大差 %.1e" % (cnt, worst))

    # 定理: 単調な明るさ変換で ISC と RRF は不変
    maps = [lambda a: a ** 0.4, lambda a: a ** 2.5, lambda a: 3 * a + 0.2, lambda a: np.log1p(30 * a)]
    name = "camera"
    y, x = tpls[name][0]
    t = imgs[name][y:y + TS, x:x + TS]
    sc = np.clip(imgs[name] + NOISE * np.random.default_rng(2).standard_normal(imgs[name].shape), 1e-6, 1)
    base = C.isc_match(sc, t, direction="hv")["score_map"]
    for g in maps:
        assert np.array_equal(C.isc_match(g(sc), t, direction="hv")["score_map"], base)
    bg = imgs["coffee"]
    cur = bg.copy()
    cur[60:100, 80:130] = imgs["clock"][20:60, 30:80]
    cur = np.clip(cur + NOISE * np.random.default_rng(3).standard_normal(cur.shape), 1e-6, 1)
    rb = C.radial_reach_filter(bg, cur)
    for g in maps:
        assert np.array_equal(C.radial_reach_filter(bg, g(cur))["foreground"], rb["foreground"])
    print("ISC の点数地図(%d 位置)と RRF の前景は、単調な変換 4 種で 1 ビットも変わらない" % base.size)

    # rot90 と巡回差。探針: 絶対差にすり替える
    sub = sc[max(0, y - 20):y + TS + 20, max(0, x - 20):x + TS + 20]

    def rot_mismatch():
        a = C.ocm_match(sub, t)["score_map"]
        b = C.ocm_match(np.rot90(sub), np.rot90(t))["score_map"]
        return int((np.rot90(a) != b).sum()), a.size
    bad, tot = rot_mismatch()
    assert bad == 0
    keep = C._code_distance
    C._code_distance = lambda a, b, n: np.abs(np.asarray(a, np.int64) - np.asarray(b, np.int64))
    try:
        bad_abs, _ = rot_mismatch()
    finally:
        C._code_distance = keep
    assert bad_abs > tot // 2
    print("OCM は rot90 と可換(%d 位置で差 0)。探針: 巡回差を絶対差にすると %d / %d 位置で崩れる"
          % (tot, bad_abs, tot))
    return {"scc_ncc_max_diff": worst, "rot_probe_broken": bad_abs / tot}


# --------------------------------------------------------------------------- #
# 第 2・3 章: 確率モデルと破綻点                                                 #
# --------------------------------------------------------------------------- #
def chapter_breakdown(imgs, tpls, occ):
    print("\n== 第 2・3 章: 確率モデルと、どこで壊れるか ==")
    rr = np.random.default_rng(20261018)
    table = {}
    zs = {"isc": [], "scc": [], "scc_ext": []}
    shown = {}
    for kind, (levels, _lab) in GRIDS.items():
        for lv in levels:
            cnt = {m: {"hit": 0, "wrong": 0, "refused": 0} for m in METHODS}
            for name in NAMES:
                img = imgs[name]
                for (y, x) in tpls[name]:
                    tpl = img[y:y + TS, x:x + TS]
                    clean = perturb(img, y, x, kind, lv, rr, occ)
                    noisy = clean + NOISE * rr.standard_normal(clean.shape)
                    res = run_methods(noisy, tpl)
                    for m, v in res.items():
                        if v is None:
                            cnt[m]["refused"] += 1
                        elif max(abs(v[0] - y), abs(v[1] - x)) <= 1:
                            cnt[m]["hit"] += 1
                        else:
                            cnt[m]["wrong"] += 1
                    a, b, c = predicted_z(clean, noisy, y, x, tpl)
                    zs["isc"].append(a)
                    zs["scc"].append(b)
                    zs["scc_ext"].append(c)
                    # 図に出す 1 例: 遮蔽 40 % で NCC が外れ、OCM と ISC が当たった最初の場面(割合は図 1 が示す)
                    ok = {m: (res[m] is not None and max(abs(res[m][0] - y), abs(res[m][1] - x)) <= 1)
                          for m in METHODS}
                    if (kind == "occlusion" and abs(lv - 0.4) < 1e-9 and "occ" not in shown
                            and ok["OCM"] and ok["ISC"] and not ok["NCC"]):
                        shown["occ"] = (noisy, tpl, y, x)
            table[(kind, lv)] = cnt
            n = sum(cnt["NCC"].values())
            print("  %-9s %5.2f  " % (kind, lv) + "  ".join(
                "%s %3.0f%%" % (m, 100 * cnt[m]["hit"] / n) for m in METHODS)
                + "   (n=%d, 拒否 SCC %d)" % (n, cnt["SCC"]["refused"]))
    # 第 2 章の門: z
    zsum = {}
    for k, v in zs.items():
        v = np.array(v)
        zsum[k] = (float(np.abs(v).max()), float(v.mean()), float(v.std()), len(v))
        assert np.abs(v).max() < Z_MAX, (k, np.abs(v).max())
        assert abs(v.mean()) < Z_MAX / math.sqrt(len(v)), (k, v.mean())
    print("確率モデル: 正解位置の ISC / SCC のマスク率(基本・拡張)の z —— "
          + "、".join("%s 最大 |z| %.2f・平均 %+.2f・標準偏差 %.2f(%d 試行)" % (k, a, b, c, d)
                     for k, (a, b, c, d) in zsum.items()))
    return table, zsum, shown, zs


def _rate(cnt, m):
    n = sum(cnt[m].values())
    return cnt[m]["hit"] / n, n


def breakdown_point(table, kind, m):
    levels = GRIDS[kind][0]
    prev = None
    for lv in levels:
        r, _ = _rate(table[(kind, lv)], m)
        if r < 0.5:
            if prev is None:
                return lv
            l0, r0 = prev
            return l0 + (r0 - 0.5) / (r0 - r) * (lv - l0)
        prev = (lv, r)
    return float("inf")


def pooled(table, kind, m, lo=1e-9):
    h = n = 0
    for lv in GRIDS[kind][0]:
        if lv > lo:
            c = table[(kind, lv)][m]
            h += c["hit"]
            n += sum(c.values())
    return h, n


def two_prop_z(h1, n1, h2, n2):
    p = (h1 + h2) / (n1 + n2)
    se = math.sqrt(max(p * (1 - p) * (1 / n1 + 1 / n2), 1e-300))
    return (h1 / n1 - h2 / n2) / se


def gate_breakdown(table):
    out = {}
    for kind in ("occlusion", "highlight", "shading"):
        hn, nn = pooled(table, kind, "NCC")
        best = max(("OCM", "ISC"), key=lambda m: pooled(table, kind, m)[0])
        hb, nb = pooled(table, kind, best)
        z = two_prop_z(hb, nb, hn, nn)
        hs, ns = pooled(table, kind, "SCC")
        zs = two_prop_z(hs, ns, hn, nn)
        assert z > Z_PAIR, (kind, z)
        out[kind] = (best, hb / nb, hn / nn, z, hs / ns, zs)
        print("  %-9s 掛けた全段の合計: %s %.0f%% 対 NCC %.0f%%(z = %.1f)/ SCC %.0f%%(NCC との z = %+.1f)"
              % (kind, best, 100 * hb / nb, 100 * hn / nn, z, 100 * hs / ns, zs))
    # 回転: どれも回転不変ではない(15° 以上の合計が 0° より有意に低い)
    for m in METHODS:
        h0, n0 = table[("rotation", 0.0)][m]["hit"], sum(table[("rotation", 0.0)][m].values())
        h1, n1 = pooled(table, "rotation", m, lo=14.9)
        z = two_prop_z(h0, n0, h1, n1)
        assert z > Z_PAIR, (m, z)
        out["rotation_" + m] = (h1 / n1, z)
    print("  回転 15° 以上: " + "、".join("%s %.0f%%" % (m, 100 * out["rotation_" + m][0]) for m in METHODS)
          + " —— 4 種とも回転不変ではない(回転を探す OCDH 系は別の op)")
    return out


# --------------------------------------------------------------------------- #
# 第 4 章: 決まらないものは決めない                                              #
# --------------------------------------------------------------------------- #
def chapter_refusal(imgs):
    print("\n== 第 4 章: 平坦なテンプレート ==")
    img = imgs["camera"]
    rr = np.random.default_rng(44)
    flats = []
    for y in range(4, img.shape[0] - TS - 4, 6):
        for x in range(4, img.shape[1] - TS - 4, 6):
            t = img[y:y + TS, x:x + TS]
            if t.std() < 0.01:
                if all(max(abs(y - a), abs(x - b)) > TS // 2 for a, b in flats):
                    flats.append((y, x))
    assert len(flats) >= 3, len(flats)
    ref = {m: 0 for m in METHODS}
    wrong = {m: 0 for m in METHODS}
    wrong_ncc = 0
    scores = []
    first = None
    for (y, x) in flats:
        t = img[y:y + TS, x:x + TS]
        sc = img + NOISE * rr.standard_normal(img.shape)
        res = run_methods(sc, t)
        for m, v in res.items():
            if v is None:
                ref[m] += 1
            elif max(abs(v[0] - y), abs(v[1] - x)) > 1:
                wrong[m] += 1
        r, c, mp = ncc_locate(sc, t)
        scores.append(float(mp.max()))
        if max(abs(r - y), abs(c - x)) > 1:
            wrong_ncc += 1
            if first is None:
                first = (sc, t, y, x, r, c, float(mp.max()))
    for m in ("OCM", "ISC", "SCC"):
        assert wrong[m] == 0, (m, wrong[m])               # 拒否か正解か。誤答は 0
        assert ref[m] >= len(flats) // 2, (m, ref[m])
    assert ref["NCC"] == 0
    print("空の平坦な 32 x 32(標準偏差 < 0.01)を %d 枚: 拒否 OCM %d・ISC %d・SCC %d 枚、残りは正解(誤答 0)。"
          "NCC は全部に答え、%d 枚で 1 px より外した(最大相関の中央値 %.2f)"
          % (len(flats), ref["OCM"], ref["ISC"], ref["SCC"], wrong_ncc, float(np.median(scores))))
    return {"n_flat": len(flats), "ncc_wrong": wrong_ncc, "ncc_median_score": float(np.median(scores)),
            "refused": dict(ref), "first": first}


# --------------------------------------------------------------------------- #
# 第 5 章: 背景との比較(RRF)                                                    #
# --------------------------------------------------------------------------- #
def chapter_rrf(imgs, n_scenes):
    print("\n== 第 5 章: 背景との比較(RRF 対 差分の閾値) ==")
    bg = imgs["camera"]
    obj_src = imgs["coffee"]
    rr = np.random.default_rng(55)
    gammas = (0.5, 0.7, 1.0, 1.4, 2.0)
    tau = 4.0 * NOISE                                 # 差分の閾値 = 雑音の 4σ
    rows = []
    wins = n_pairs = 0
    shown = None
    yy, xx = np.mgrid[:bg.shape[0], :bg.shape[1]]
    for k in range(n_scenes):
        cy, cx = rr.uniform(60, bg.shape[0] - 40), rr.uniform(40, bg.shape[1] - 40)
        obj = np.hypot(yy - cy, xx - cx) < 22
        oy, ox = int(rr.integers(0, obj_src.shape[0] - bg.shape[0] // 2)), int(rr.integers(0, obj_src.shape[1] - bg.shape[1] // 2))
        patch = ndimage.zoom(obj_src[oy:oy + bg.shape[0] // 2, ox:ox + bg.shape[1] // 2], 2, order=1)[:bg.shape[0], :bg.shape[1]]
        ang = rr.uniform(0, math.pi)
        band = np.abs((yy - bg.shape[0] / 2) * math.cos(ang) - (xx - bg.shape[1] / 2) * math.sin(ang) - rr.uniform(-40, 40)) < 18
        for g in gammas:
            cur = bg.copy()
            cur[obj] = patch[obj] * 0.8 + 0.1
            cur = np.where(band & ~obj, cur * 0.45, cur)
            cur = np.clip(cur, 0, 1) ** g + NOISE * rr.standard_normal(bg.shape)
            r = C.radial_reach_filter(bg, cur)
            base = np.abs(cur - bg) > tau
            f_r, f_b = _f1(r["foreground"], obj), _f1(base, obj)
            sh = band & ~obj
            rows.append((k, g, f_r, f_b, float(r["foreground"][sh].mean()), float(base[sh].mean()),
                         r["decided_fraction"]))
            if g != 1.0:
                n_pairs += 1
                wins += int(f_r > f_b)
            if k == 0 and g == 0.5:
                shown = (cur, obj, base, r)
    p = sum(math.comb(n_pairs, i) for i in range(wins, n_pairs + 1)) / 2 ** n_pairs
    assert p < 1e-3, (wins, n_pairs, p)
    fr = np.array([r[2] for r in rows])
    fb = np.array([r[3] for r in rows])
    print("場面 %d × ガンマ %s: F1 の中央値 RRF %.2f 対 差分 %.2f。ガンマ ≠ 1 の %d 組中 %d 組で RRF が上"
          "(符号検定 p = %.1e)" % (n_scenes, gammas, float(np.median(fr)), float(np.median(fb)), n_pairs, wins, p))
    shf_r = float(np.mean([r[4] for r in rows]))
    shf_b = float(np.mean([r[5] for r in rows]))
    print("影だけの画素を前景にした割合: RRF %.1f %% / 差分 %.1f %%。RRF が判定した画素 %.0f %%"
          "(空の平坦な所は判定しない)" % (100 * shf_r, 100 * shf_b, 100 * float(np.mean([r[6] for r in rows]))))
    return {"rows": rows, "wins": wins, "pairs": n_pairs, "p": p, "shown": shown,
            "shadow_fp": (shf_r, shf_b)}


def _f1(pred, truth):
    tp = float((pred & truth).sum())
    fp = float((pred & ~truth).sum())
    fn = float((~pred & truth).sum())
    return 2 * tp / max(2 * tp + fp + fn, 1.0)


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _rgb(gray):
    g = np.clip(gray, 0, 1)
    return np.dstack([g, g, g])


def _box(rgb, r, c, h, w, color, t=1):
    H, W = rgb.shape[:2]
    for k in range(t):
        r0, c0, r1, c1 = r - k, c - k, r + h - 1 + k, c + w - 1 + k
        if 0 <= r0 < H:
            rgb[r0, max(c0, 0):min(c1 + 1, W)] = color
        if 0 <= r1 < H:
            rgb[r1, max(c0, 0):min(c1 + 1, W)] = color
        if 0 <= c0 < W:
            rgb[max(r0, 0):min(r1 + 1, H), c0] = color
        if 0 <= c1 < W:
            rgb[max(r0, 0):min(r1 + 1, H), c1] = color


#: 札の文字色(札の地 = 手法の色に対してコントラスト比 4.5 以上になる方)
_INK = {"NCC": (0.0, 0.0, 0.0), "OCM": (1.0, 1.0, 1.0), "ISC": (0.0, 0.0, 0.0), "SCC": (0.0, 0.0, 0.0)}


def _label(rgb, text, xy, method=None, size=13, anchor="lt"):
    """文字の札。読めない色の組なら annotate が例外を出す(黙って札を落とさない)。"""
    import annotate
    kw = {}
    if method is not None:
        kw = {"box_color": COLORS[method], "text_color": _INK[method], "box_alpha": 1.0}
    return annotate.text_box(rgb, text, xy, font_size=size, anchor=anchor, **kw)


def figures(imgs, tpls, occ, table, zs, refusal, rrf, credit):
    if not figs.enabled():
        return
    # 1) 破綻点の曲線(4 本)
    for kind, (levels, lab) in GRIDS.items():
        series = []
        for m in METHODS:
            series.append((m, list(levels), [100 * _rate(table[(kind, lv)], m)[0] for lv in levels]))
        series.append(("50 %(破綻点の定義)", [levels[0], levels[-1]], [50, 50]))
        figs.save_plot("breakdown_%s" % kind, series, xlabel=lab, ylabel="1 px 以内で当たった割合 [%]",
                       title="破綻点: %s" % lab, ylim=(0, 102), size=(720, 420),
                       styles=[None, None, None, None, "dashed"],
                       colors=["neutral", "emphasis", "right", "wrong", "reference"],
                       caption="公開の実写 5 枚から切った 32 x 32 のテンプレートを、雑音 σ = 0.01 の場面で探す。"
                               "点 = 段ごとの割合(各段 %d 試行)。50 %% を割る所が破綻点。" %
                               sum(table[(kind, levels[0])]["NCC"].values()),
                       source=credit)
    # 2) 照明を振る GIF: ハイライトを広げる。箱 = 各手法の答え、白 = 正解
    name = "camera"
    y, x = tpls[name][0]
    img = imgs[name]
    tpl = img[y:y + TS, x:x + TS]
    y0, x0 = max(0, y - 48), max(0, x - 48)
    frames = []
    rr = np.random.default_rng(7)
    for lv in np.linspace(0.0, 0.6, 16):
        rq = np.random.default_rng(99)               # 同じ場所・同じ形のハイライトを広げる
        clean = perturb(img, y, x, "highlight", float(lv), rq, occ)
        sc = clean + NOISE * rr.standard_normal(clean.shape)
        res = run_methods(sc, tpl)
        crop = _rgb(sc[y0:y0 + 128, x0:x0 + 128])
        crop = np.kron(crop, np.ones((3, 3, 1)))
        _box(crop, 3 * (y - y0), 3 * (x - x0), 3 * TS, 3 * TS, COLORS["truth"], 2)
        for m in METHODS:
            v = res[m]
            if v is not None:
                _box(crop, 3 * (v[0] - y0), 3 * (v[1] - x0), 3 * TS, 3 * TS, COLORS[m], 2)
        crop = _label(crop, "ハイライト %2.0f %%" % (100 * lv), (6, 6))
        yl = 6
        for m in METHODS:
            v = res[m]
            ok = v is not None and max(abs(v[0] - y), abs(v[1] - x)) <= 1
            crop = _label(crop, "%s %s" % (m, "当たり" if ok else ("拒否" if v is None else "外れ")),
                          (crop.shape[1] - 6, yl), method=m, anchor="rt")
            yl += 24
        frames.append(np.clip(crop, 0, 1))
    figs.save_gif("highlight_sweep", frames, fps=3.0,
                  caption="飽和したハイライトを 0 → 60 % まで広げる(camera、CC0)。白 = 正解、橙 = NCC、青 = OCM、"
                          "緑 = ISC、紫 = SCC。NCC は最初の数コマで光の縁へ飛ぶ。")
    # 3) 点数地図: 遮蔽 40 % の 1 場面。正解の周り 96 x 96 位置を 3 倍で。白枠 = 正解、色枠 = 各手法の最良
    sh = getattr(figures, "_shown", None)
    if sh is not None:
        import fullseye as fs
        noisy, t, oy, ox = sh
        oh, ow = noisy.shape[0] - TS + 1, noisy.shape[1] - TS + 1
        _, _, mn = ncc_locate(noisy, t)
        maps = {"NCC": mn[TS // 2:TS // 2 + oh, TS // 2:TS // 2 + ow]}
        maps["OCM"] = C.ocm_match(noisy, t)["score_map"]
        maps["ISC"] = C.isc_match(noisy, t)["score_map"]
        rs = C.scc_match(noisy, t)
        maps["SCC"] = np.where(rs["valid_map"], rs["score_map"], np.nan)
        S = 96
        y0 = int(np.clip(oy - S // 2, 0, oh - S))
        x0 = int(np.clip(ox - S // 2, 0, ow - S))
        k = 3
        scene = np.kron(_rgb(noisy[y0:y0 + S + TS, x0:x0 + S + TS]), np.ones((k, k, 1)))
        _box(scene, k * (oy - y0), k * (ox - x0), k * TS, k * TS, COLORS["truth"], 2)
        panels = [scene, np.kron(_rgb(t), np.ones((4, 4, 1)))]
        caps = ["場面(遮蔽 40 %、白 = 正解。NCC が外れ符号系が当たった 1 例)", "テンプレート(32 x 32 を 4 倍)"]
        for m in METHODS:
            v = maps[m][y0:y0 + S, x0:x0 + S]
            ok = np.isfinite(v)
            lo, hi = float(np.nanmin(v)), float(np.nanmax(v))
            u = np.where(ok, (v - lo) / max(hi - lo, 1e-12), 0.0)
            rgb = fs.colorize_depth(u)
            rgb[~ok] = 0.25
            rgb = np.kron(rgb, np.ones((k, k, 1)))
            full = np.where(np.isfinite(maps[m]), maps[m], -np.inf)
            br, bc = np.unravel_index(int(np.argmax(np.round(full, 12))), full.shape)
            _box(rgb, k * (oy - y0) - 3, k * (ox - x0) - 3, 7, 7, COLORS["truth"], 2)
            inside = 0 <= br - y0 < S and 0 <= bc - x0 < S
            if inside:
                _box(rgb, k * (br - y0) - 6, k * (bc - x0) - 6, 13, 13, COLORS[m], 2)
            hit = max(abs(br - oy), abs(bc - ox)) <= 1
            panels.append(rgb)
            caps.append("%s(%s%s)" % (m, "当たり" if hit else "外れ", "" if inside else "、最良は枠の外")
                        + (" 灰 = 採点しない位置" if m == "SCC" else ""))
        figs.save_grid("score_maps_occlusion40", panels, caps,
                       title="同じ場面の点数地図(正解の周り、明るいほど似ている。白の小枠 = 正解、色の枠 = 最良)",
                       ncols=3)
    # 4) 平坦なテンプレート
    if refusal["first"] is not None:
        sc, t, fy, fx, r, c, s = refusal["first"]
        rgb = _rgb(sc)
        rgb = np.kron(rgb, np.ones((2, 2, 1)))
        _box(rgb, 2 * fy, 2 * fx, 2 * TS, 2 * TS, COLORS["truth"], 2)
        _box(rgb, 2 * r, 2 * c, 2 * TS, 2 * TS, COLORS["NCC"], 2)
        rgb = _label(rgb, "白 = テンプレートを切った所 / 橙 = NCC の答え(相関 %.2f)" % s, (8, rgb.shape[0] - 8),
                     anchor="lb")
        rgb = _label(rgb, "OCM / ISC / SCC: 拒否(有効な符号が足りない)", (8, rgb.shape[0] - 34), anchor="lb")
        figs.save("flat_template_refusal", np.clip(rgb, 0, 1),
                  "空の平坦な所(標準偏差 < 0.01)を切ったテンプレート。NCC は別の空を高い相関で返し、符号系は値を返さない。",
                  source=credit)
    # 5) RRF
    if rrf["shown"] is not None:
        cur, obj, base, r = rrf["shown"]
        und = np.where(r["decided"], r["foreground"].astype(float), 0.5)
        figs.save_grid("rrf_vs_difference", [imgs["camera"], cur, obj.astype(float), base.astype(float), und],
                       ["背景", "現在(ガンマ 0.5・帯状の影・物)", "真値(物)",
                        "差分 > 4σ(F1 %.2f)" % _f1(base, obj),
                        "RRF(灰 = 判定しない、F1 %.2f)" % _f1(r["foreground"], obj)],
                       title="背景との比較: 照明が変わっても影の内側も前景にしない", ncols=3, gray=True)
    # 6) 確率モデル
    z = np.array(zs["scc"])
    zi = np.array(zs["isc"])
    xs = np.arange(len(z))
    figs.save_plot("closed_form_z", [("SCC マスク率の z", list(xs), list(z)), ("ISC の z(分散は上界)", list(xs), list(zi)),
                                     ("+4.5", [0, len(z)], [Z_MAX, Z_MAX]), ("−4.5", [0, len(z)], [-Z_MAX, -Z_MAX])],
                   xlabel="試行(章 3 の全場面)", ylabel="(実測 − 閉形式の期待値)/ 標準偏差",
                   title="正解位置の値は確率モデルどおり", kinds=["scatter", "scatter", "line", "line"],
                   styles=[None, None, "dashed", "dashed"], colors=["emphasis", "right", "reference", "reference"],
                   size=(720, 420), caption="雑音の無い場面の増分 Δ と σ から、組ごとの一致確率 Φ(Δ/(√2σ)) が決まる。")
    # 7) 表
    rows = []
    for kind in GRIDS:
        rows.append([{"occlusion": "遮蔽(面積比)", "highlight": "ハイライト(面積比)", "shading": "減光(深さ)",
                      "rotation": "回転 [度]"}[kind]] + ["%.2f" % breakdown_point(table, kind, m) if math.isfinite(breakdown_point(table, kind, m))
                              else "> %g" % GRIDS[kind][0][-1] for m in METHODS])
    figs.save_table("breakdown_table", ["軸"] + list(METHODS), rows, title="破綻点(当たりが 50 % を割る所)",
                    caption="線形補間。遮蔽・ハイライトは面積比、減光は深さ、回転は度。")


def main():
    t0 = time.process_time()
    w0 = time.perf_counter()
    ci = os.environ.get("CI", "") not in ("", "0", "false")
    n_tpl = 2 if ci else 8
    imgs = load_images()
    occ = realdata.sample_photo("gravel")
    tpls = {n: pick_templates(imgs[n], n_tpl, sum(map(ord, n))) for n in NAMES}
    assert all(len(v) == n_tpl for v in tpls.values()), {k: len(v) for k, v in tpls.items()}
    credit = realdata.sample_photo_credit(list(NAMES) + ["gravel"])
    ex = chapter_exact(imgs, tpls)
    table, zsum, shown, zs = chapter_breakdown(imgs, tpls, occ)
    print("\n破綻点(当たりが 50 % を割る所、線形補間):")
    for kind in GRIDS:
        print("  %-9s " % kind + "  ".join("%s %s" % (m, ("%.2f" % breakdown_point(table, kind, m))
                                                     if math.isfinite(breakdown_point(table, kind, m)) else "なし")
                                          for m in METHODS))
    gb = gate_breakdown(table)
    refusal = chapter_refusal(imgs)
    rrf = chapter_rrf(imgs, 3 if ci else 6)
    figures._shown = shown.get("occ")
    figures(imgs, tpls, occ, table, zs, refusal, rrf, credit)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    cpu = time.process_time() - t0
    print("\n所要: CPU %.1f s(壁時計 %.1f s)" % (cpu, time.perf_counter() - w0))
    occ_g = gb["occlusion"]
    hl_g = gb["highlight"]
    print("\nPASS: 総当たり・既存の NCC と一致(差 %.0e)/ 単調変換で ISC・RRF 不変 / 探針で rot90 が崩れる %.0f %% /"
          " 確率モデル max|z| %.2f / 遮蔽 %s %.0f %% 対 NCC %.0f %%、ハイライト %s %.0f %% 対 NCC %.0f %% /"
          " 平坦 %d 枚で符号系の誤答 0(NCC は %d 枚で誤答)/ RRF 対 差分 %d / %d。"
          % (ex["scc_ncc_max_diff"], 100 * ex["rot_probe_broken"], max(v[0] for v in zsum.values()),
             occ_g[0], 100 * occ_g[1], 100 * occ_g[2], hl_g[0], 100 * hl_g[1], 100 * hl_g[2],
             refusal["n_flat"], refusal["ncc_wrong"], rrf["wins"], rrf["pairs"]))


if __name__ == "__main__":
    main()
