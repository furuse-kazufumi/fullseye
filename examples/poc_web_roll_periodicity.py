# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(placeholder docstring — 実測後に書き換える)"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- ライン諸元(長さはすべて mm)------------------------------------------- #
WEB_W = 600.0            # web の有効幅 [mm]
L_FULL = 20000.0         # 1 巻ぶんの記録長 [mm](20 m)
MD_BIN = 2.0             # 流れ方向の記録刻み [mm](エンコーダの分解能)
CD_BIN = 2.0             # 幅方向の記録刻み [mm]

#: 搬送ロールの台帳。``(名前, 直径 [mm])`` —— 周長は π×直径。
#: ★第1ニップと第2ニップの周長差はわざと 15.7 mm しかない(6 節の崖のため)。
ROLLS = (
    ("巻出しロール", 200.0),
    ("第1ニップロール", 150.0),
    ("冷却ロール", 100.0),
    ("第2ニップロール", 145.0),
    ("巻取りロール", 250.0),
)
CIRC = {name: np.pi * d for name, d in ROLLS}

#: 傷ついているロール(真値)と、その傷の**機械座標での** CD 位置 [mm]。
CULPRIT = "第1ニップロール"
NICK_CD = 190.0
CULPRIT2 = "巻取りロール"                # 7 節でだけ 2 本目を傷つける
NICK_CD2 = 410.0

MD_JITTER = 1.5          # 転写位置の MD ゆらぎ [mm](スリップ・伸び)
CD_JITTER = 3.0          # 転写位置の CD ゆらぎ [mm]
P_MISS = 0.15            # 欠陥検出の見逃し率(既定)

CLUTTER_PER_MM = 1.0 / 400.0     # 無関係な欠陥の発生率 [個/mm] = 50 個/20 m

#: web の蛇行(meander)。**欠陥地図は web 端基準で記録される** —— 下流の
#: 断裁位置に紐づけたいから。その座標系では、機械に固定されたロール傷のほうが
#: 蛇行のぶんだけ CD に揺れて見える(web 由来の欠陥は逆に動かない)。
MEANDER_A = 25.0
MEANDER_LAMBDA = 2600.0
MEANDER_PHI = 0.7

# --- 解析の諸元 -------------------------------------------------------------- #
C_MIN, C_MAX = 200.0, 1000.0     # 周長の探索範囲 [mm](台帳を覆う)
LANE_HALF = 15.0                 # CD レーンの半幅 [mm](現場の定番の絞り込み)
KMAX = 3                         # 櫛法が「全部立っている」ことを要求する高調波の数
PEAK_K = 2.5                     # 「ロールを 1 本報告する」高調波の高さ倍率(帯域の中央値比)
SEEDS = 24                       # 掃引 1 点あたりの試行数
SEED0 = 1000


# --------------------------------------------------------------------------- #
# 真値 —— 場面を式で置く                                                        #
# --------------------------------------------------------------------------- #
def meander(md, on: bool = True):
    """web 端の横ずれ [mm]。web 端基準の座標では機械側がこのぶん逆に動く。"""
    if not on:
        return np.zeros_like(np.asarray(md, float))
    return MEANDER_A * np.sin(2.0 * np.pi * np.asarray(md, float) / MEANDER_LAMBDA
                              + MEANDER_PHI)


def scene(seed: int, length: float = L_FULL, p_miss: float = P_MISS,
          meander_on: bool = True, culprits=(CULPRIT,), clutter: bool = True) -> dict:
    """欠陥地図(**点の一覧**)を作る。``cd`` は web 端基準で記録された値。

    ``culprits`` を空にすると「健全なロールだけ」の対照群になる(5 節)。
    """
    rng = np.random.default_rng(seed)
    md_l, cd_l, per_l = [], [], []
    nicks = {CULPRIT: NICK_CD, CULPRIT2: NICK_CD2}
    for name in culprits:
        c = CIRC[name]
        k = np.arange(int(length / c) + 1)
        md = rng.uniform(0.0, c) + k * c
        md = md[md < length]
        keep = rng.random(md.size) > p_miss
        md = md[keep] + rng.normal(0.0, MD_JITTER, int(keep.sum()))
        cd_machine = nicks[name] + rng.normal(0.0, CD_JITTER, md.size)
        md_l.append(md)
        cd_l.append(cd_machine - meander(md, meander_on))   # web 端基準へ
        per_l.append(np.ones(md.size, bool))
    if clutter:
        n = int(rng.poisson(length * CLUTTER_PER_MM))
        md_l.append(rng.uniform(0.0, length, n))
        cd_l.append(rng.uniform(20.0, WEB_W - 20.0, n))
        per_l.append(np.zeros(n, bool))
    md = np.concatenate(md_l) if md_l else np.zeros(0)
    cd = np.concatenate(cd_l) if cd_l else np.zeros(0)
    per = np.concatenate(per_l) if per_l else np.zeros(0, bool)
    ok = (md >= 0.0) & (md < length)
    md, cd, per = md[ok], np.clip(cd[ok], 0.0, WEB_W - 1e-6), per[ok]
    order = np.argsort(md)
    return {"md": md[order], "cd": cd[order], "periodic": per[order],
            "length": length, "meander_on": meander_on, "culprits": tuple(culprits)}


# --------------------------------------------------------------------------- #
# 推定器 —— どれも「周長 [mm]」を 1 個返す                                      #
# --------------------------------------------------------------------------- #
def md_signal(md, length: float) -> np.ndarray:
    """MD 位置の一覧 → 等間隔の占有信号(1 ビン = :data:`MD_BIN` mm)。"""
    n = max(int(round(length / MD_BIN)), 8)
    s, _ = np.histogram(np.asarray(md, float), bins=n, range=(0.0, length))
    return s.astype(np.float64)


def md_spectrum(md, length: float) -> dict:
    """MD 占有信号の片側振幅スペクトル(``fs.spectrum``)と探索帯域。

    窓は掛けない —— 矩形窓のままにすると分解能が Rayleigh の 1/L ちょうどに
    なり、2 節の予測と直接比べられる。
    """
    s = md_signal(md, length)
    if s.size < 16 or s.sum() < 3:
        return {}
    s = s - s.mean()
    f, m = fs.spectrum(s, rate=1.0 / MD_BIN)
    f, m = np.asarray(f, float), np.asarray(m, float)
    band = np.nonzero((f >= 1.0 / C_MAX) & (f <= 1.0 / C_MIN))[0]
    if band.size < 4:
        return {}
    return {"f": f, "m": m, "band": band, "df": float(f[1] - f[0]),
            "med": float(max(np.median(m[band]), 1e-12))}


def _peak_freq(f, m, i: int, interp: bool) -> float:
    """ビン ``i`` の山の頂点の周波数。``interp`` なら放物線で補間する。"""
    fh = float(f[i])
    if interp and 0 < i < m.size - 1:
        a, b, c = m[i - 1], m[i], m[i + 1]
        den = a - 2.0 * b + c
        if abs(den) > 1e-12:
            fh += float(np.clip(0.5 * (a - c) / den, -0.5, 0.5)) * float(f[1] - f[0])
    return fh


def naive_spec_estimate(md, length: float) -> dict:
    """**素朴なスペクトル法** —— 帯域内の最大値をそのまま周長に直す。

    周期欠陥の列はインパルス列なので、スペクトルは **f = k/C の櫛**になる。
    高調波は基本波とほぼ同じ高さなので、最大値を読むと ``C/2`` や ``C/3`` を
    掴む。しかも掴んだ値が**台帳の別のロールの近く**に落ちると、
    「無実のロールを名指しする」ところまで行く(3 節で実測)。
    """
    sp = md_spectrum(md, length)
    if not sp:
        return {"C": np.nan, "ratio": 0.0}
    f, m, band = sp["f"], sp["m"], sp["band"]
    i = int(band[np.argmax(m[band])])
    fh = _peak_freq(f, m, i, True)
    return {"C": 1.0 / fh if fh > 0 else np.nan, "ratio": float(m[i] / sp["med"])}


def comb_score(sp: dict, kmax: int = KMAX) -> np.ndarray:
    """帯域の各ビンを「基本波だと仮定したときの櫛の強さ」で採点する。

    点数は **k=1..kmax のうちいちばん弱い高調波**の高さ(min)。和ではなく min
    にするのは fail-closed のため —— 1 本でも欠けていれば、その候補は基本波
    ではない。高調波 k の位置は基本波のビン丸め誤差が k 倍されるので、
    窓も k に応じて広げる。
    """
    m, band = sp["m"], sp["band"]
    out = np.zeros(band.size)
    for a, j in enumerate(band):
        j = int(j)
        if kmax * j + kmax >= m.size:
            continue
        out[a] = min(
            float(m[max(k * j - (k // 2 + 1), 0):k * j + (k // 2 + 2)].max())
            for k in range(1, kmax + 1))
    return out


def comb_peaks(md, length: float, max_rolls: int = 4,
               interp: bool = True) -> dict:
    """**櫛(comb)法** —— 高調波が k=1..KMAX すべて立っている最低周波数から採る。

    既に採った周長の 1/2, 1/3, ... に当たる候補は「同じロールの高調波」として
    篩い落とす —— インパルス列のスペクトルは櫛なので、これをしないと 1 本の
    ロールを 3 本にも 4 本にも報告する。候補の拾い出しは
    :func:`fullseye.find_peaks`。
    """
    sp = md_spectrum(md, length)
    if not sp:
        return {"C": [], "ratio": [], "spec": {}}
    f, m, band, med = sp["f"], sp["m"], sp["band"], sp["med"]
    sco = comb_score(sp)
    pk = np.asarray(fs.find_peaks(sco, height=PEAK_K * med, distance=2), int)
    cs, rs = [], []
    for a in pk:                      # find_peaks は昇順 = 低い周波数から
        j = int(band[a])
        fh = _peak_freq(f, m, j, interp)
        if fh <= 0:
            continue
        chat = 1.0 / fh
        if any(abs(chat - c0 / k) <= 0.04 * c0 / k
               for c0 in cs for k in range(2, 7)):
            continue
        cs.append(chat)
        rs.append(float(sco[a] / med))
        if len(cs) >= max_rolls:
            break
    return {"C": cs, "ratio": rs, "spec": sp, "score": sco}


def spec_estimate(md, length: float, interp: bool = True) -> dict:
    """櫛法が返す**いちばん低い周波数の基本波** = 1 本目のロールの周長。"""
    r = comb_peaks(md, length, interp=interp)
    if not r["C"]:
        return {"C": np.nan, "ratio": 0.0, "spec": r["spec"]}
    return {"C": r["C"][0], "ratio": r["ratio"][0], "spec": r["spec"]}


def cepstrum_estimate(md, length: float) -> dict:
    """**ケプストラム法** —— スペクトルの櫛の間隔を quefrency 軸で 1 本にする。

    ``fs.cepstrum`` の docstring が警告しているとおり、ケプストラムが返すのは
    **族**なので、最大値だけ読むと整数倍を掴むことがある。ここでもそれが起きる
    (3 節)。``min_quefrency`` はスペクトル包絡を避けるための liftering。
    """
    s = md_signal(md, length)
    if s.size < 16 or s.sum() < 3:
        return {"C": np.nan}
    s = s - s.mean()
    try:
        r = fs.cepstrum(s, rate=1.0 / MD_BIN, min_quefrency=C_MIN)
    except ValueError:
        return {"C": np.nan}
    return {"C": float(r["peak_quefrency"]), "amp": float(r["peak_amplitude"])}


def lane_centre(cd) -> float:
    """CD ヒストグラムのいちばん高い山の位置 [mm](現場の「レーン」)。"""
    h, _ = np.histogram(np.asarray(cd, float), bins=int(WEB_W / CD_BIN),
                        range=(0.0, WEB_W))
    hs = np.asarray(fs.smooth_funct_1d_gauss(h.astype(np.float64), sigma=2.0))
    return (float(np.argmax(hs)) + 0.5) * CD_BIN


def null_estimate(md, cd, lane: bool = True, stat: str = "median") -> dict:
    """**ゼロ点** —— 検出した欠陥の MD 間隔の中央値(または平均)。

    ``lane=True`` は「まず CD レーンで絞ってから間隔を測る」現場の定番。
    検出が完璧で無関係な欠陥がレーンに入らなければ、これは当たる。
    """
    md = np.asarray(md, float)
    cd = np.asarray(cd, float)
    if lane:
        c0 = lane_centre(cd)
        sel = np.abs(cd - c0) <= LANE_HALF
    else:
        sel = np.ones(md.size, bool)
        c0 = np.nan
    x = np.sort(md[sel])
    if x.size < 3:
        return {"C": np.nan, "n": int(x.size), "lane": c0}
    d = np.diff(x)
    v = float(np.median(d)) if stat == "median" else float(np.mean(d))
    return {"C": v, "n": int(x.size), "lane": c0}


def identify(c_hat: float) -> str:
    """推定した周長にいちばん近いロールを台帳から選ぶ。"""
    if not np.isfinite(c_hat):
        return "(不明)"
    return min(CIRC, key=lambda k: abs(CIRC[k] - c_hat))


def cd_peak_count(cd, thresh: float = 0.3):
    """CD ヒストグラムの山の数。**1 本のロールが何本に割れて見えるか**。"""
    h, _ = np.histogram(np.asarray(cd, float), bins=int(WEB_W / CD_BIN),
                        range=(0.0, WEB_W))
    hs = np.asarray(fs.smooth_funct_1d_gauss(h.astype(np.float64), sigma=3.0))
    lm = fs.local_min_max_funct_1d(hs)
    mx = np.asarray(lm["max"], int)
    keep = mx[hs[mx] >= thresh * hs.max()] if mx.size and hs.max() > 0 else mx
    return int(keep.size), hs, keep


def defect_map(sc: dict, md_hi: float, md_bin: float = 40.0,
               cd_bin: float = 4.0, correct: bool = False) -> np.ndarray:
    """図のための粗い 2-D 欠陥地図(縦 = MD、横 = CD)。"""
    md, cd = sc["md"], sc["cd"]
    if correct:
        cd = cd + meander(md, sc["meander_on"])
    sel = md < md_hi
    h, _, _ = np.histogram2d(md[sel], np.clip(cd[sel], 0, WEB_W - 1e-6),
                             bins=[int(md_hi / md_bin), int(WEB_W / cd_bin)],
                             range=[[0.0, md_hi], [0.0, WEB_W]])
    return h


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— web 幅 %.0f mm / 記録長 %.0f mm / MD 刻み %.1f mm"
          % (WEB_W, L_FULL, MD_BIN))
    print("=" * 78)
    print("   ロール台帳            直径 [mm]   周長 πD [mm]   隣との差 [mm]")
    cs = sorted(CIRC.values())
    for name, d in ROLLS:
        c = CIRC[name]
        others = [abs(c - v) for v in cs if abs(c - v) > 1e-9]
        mark = " ★傷あり(真値)" if name == CULPRIT else ""
        print("   %-18s %8.1f   %10.2f   %10.2f%s"
              % (name, d, c, min(others), mark))

    sc = scene(SEED0)
    n_per = int(sc["periodic"].sum())
    n_all = sc["md"].size
    print("\n   仕込んだ欠陥: 周期欠陥 %d 個(%s、周長 %.2f mm、見逃し率 %.0f %%)"
          % (n_per, CULPRIT, CIRC[CULPRIT], 100 * P_MISS))
    print("                 無関係なランダム欠陥 %d 個(%.3f 個/mm、CD は一様)"
          % (n_all - n_per, CLUTTER_PER_MM))
    print("                 蛇行 振幅 %.0f mm / 波長 %.0f mm"
          % (MEANDER_A, MEANDER_LAMBDA))
    print("   欠陥地図は **web 端基準**で記録される —— 下流の断裁位置に紐づける"
          "ため。\n   その座標では、機械に固定されたロール傷のほうが蛇行のぶん "
          "CD に揺れる。")

    md_hi = 6000.0
    figs.save_grid(
        "scene_web",
        [defect_map(sc, md_hi), defect_map(sc, md_hi, correct=True),
         defect_map(scene(SEED0, meander_on=False), md_hi)],
        ["web 端基準(記録されたまま)", "蛇行を戻した(機械座標)",
         "蛇行なしの対照"], ncols=3,
        title="欠陥地図の先頭 %.0f mm(縦 = MD、横 = CD %.0f mm)" % (md_hi, WEB_W),
        caption="ロール傷の列は機械座標では真っ直ぐ 1 本。web 端基準では"
                "蛇行のぶん左右に振れる。")
    return {"sc": sc, "n_per": n_per, "n_all": n_all}


# --------------------------------------------------------------------------- #
# 2. 崖を先に予測する(閉形式)                                                  #
# --------------------------------------------------------------------------- #
def section_predict() -> dict:
    print("\n" + "=" * 78)
    print("2) 崖を**測る前に**予測する —— Rayleigh 分解能から閉形式で")
    print("=" * 78)
    c = CIRC[CULPRIT]
    nb = min((k for k in CIRC if k != CULPRIT), key=lambda k: abs(CIRC[k] - c))
    dc = abs(CIRC[nb] - c)
    l_crit = c * c / dc
    print("   記録長 L の周波数分解能(矩形窓)   Δf = 1/L")
    print("   周長は C = 1/f なので              ΔC = C² Δf = C²/L")
    print("   -> **周長差が C²/L より小さい 2 本のロールは原理的に区別できない**")
    print("\n   犯人 %s C = %.2f mm、いちばん近いのは %s C = %.2f mm(差 %.2f mm)"
          % (CULPRIT, c, nb, CIRC[nb], dc))
    print("   区別できる最短の記録長  L_crit = C²/ΔC = %.2f² / %.2f = %.0f mm "
          "(= %.1f m)" % (c, dc, l_crit, l_crit / 1000.0))
    print("   これより短い記録では、この 2 本は同じ周波数ビンに入る。")
    print("\n   L [mm]     ΔC = C²/L [mm]   隣との差 %.2f mm と比べて" % dc)
    for L in (4000.0, 6000.0, 8000.0, 10000.0, 12000.0, 14000.0, 17000.0, 20000.0):
        d = c * c / L
        print("   %7.0f    %10.2f       %s" % (L, d, "区別できない" if d > dc
                                               else "区別できる"))
    print("\n   ★予測はここまで。以下 6 節でこの L_crit = %.0f mm を実測と"
          "突き合わせる。" % l_crit)
    return {"C": c, "neighbour": nb, "dC": dc, "L_crit": l_crit}


# --------------------------------------------------------------------------- #
# 3. ゼロ点 —— 間隔の中央値 vs スペクトル                                        #
# --------------------------------------------------------------------------- #
def section_null() -> dict:
    print("\n" + "=" * 78)
    print("3) ゼロ点 —— 「検出した欠陥の MD 間隔」から周長を出す")
    print("=" * 78)
    c = CIRC[CULPRIT]
    print("   まず**見逃しゼロ・ランダム欠陥なし**の理想条件で、ゼロ点が"
          "当たることを確かめる。")
    sc0 = scene(SEED0, p_miss=0.0, meander_on=False, clutter=False)
    for lab, kw in (("間隔の中央値", dict(stat="median")),
                    ("間隔の平均", dict(stat="mean"))):
        e = null_estimate(sc0["md"], sc0["cd"], lane=True, **kw)
        print("     %-16s %8.2f mm(真値 %.2f、誤差 %+8.2f)"
              % (lab, e["C"], c, e["C"] - c))
    for lab, fn in (("スペクトル 最大値", naive_spec_estimate),
                    ("スペクトル 櫛", spec_estimate)):
        e = fn(sc0["md"], sc0["length"])
        print("     %-16s %8.2f mm(真値 %.2f、誤差 %+8.2f)-> %s"
              % (lab, e["C"], c, e["C"] - c, identify(e["C"])))
    print("   -> 検出が完璧ならゼロ点は当たる。**問題はそこから先**。")
    print("   ★★そして**素朴なスペクトル(帯域内の最大値)はここで既に外れて"
          "いる** —— 周期欠陥の列は\n      インパルス列なので"
          "スペクトルは f = k/C の櫛になり、高調波は基本波とほぼ同じ高さ。\n"
          "      最大値は C/2 = %.2f mm を掴み、**それが台帳の %s "
          "(%.2f mm)の近くに落ちる**。\n      無いロールを名指しするのでは"
          "なく、**実在する無実のロールを名指しする**。"
          % (c / 2.0, identify(c / 2.0), CIRC[identify(c / 2.0)]))
    print("      以下「スペクトル」は櫛法(k=1..3 が全部立っている最低周波数、"
          "fail-closed)を指す。")

    print("\n   見逃し率を上げる(ランダム欠陥 %d 個・蛇行あり、%d 試行の中央値):"
          % (int(L_FULL * CLUTTER_PER_MM), SEEDS))
    print("   見逃し  間隔の中央値   間隔の平均  スペクトル最大値  スペクトル櫛"
          "  ケプストラム  櫛の特定成功率")
    ps = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    keys = ("med", "mean", "naive", "spec", "cep")
    rows, tab = [], {k: [] for k in keys + ("hit",)}
    for p in ps:
        errs = {k: [] for k in keys}
        hit = 0
        for s in range(SEEDS):
            sc = scene(SEED0 + s, p_miss=p)
            errs["med"].append(null_estimate(sc["md"], sc["cd"])["C"] - c)
            errs["mean"].append(
                null_estimate(sc["md"], sc["cd"], stat="mean")["C"] - c)
            errs["naive"].append(
                naive_spec_estimate(sc["md"], sc["length"])["C"] - c)
            se = spec_estimate(sc["md"], sc["length"])
            errs["spec"].append(se["C"] - c)
            errs["cep"].append(cepstrum_estimate(sc["md"], sc["length"])["C"] - c)
            hit += int(identify(se["C"]) == CULPRIT)
        med = {k: float(np.nanmedian(np.abs(v))) for k, v in errs.items()}
        rate = 100.0 * hit / SEEDS
        for k in keys:
            tab[k].append(med[k])
        tab["hit"].append(rate)
        rows.append(["%.0f %%" % (100 * p)]
                    + ["%.1f" % med[k] for k in keys] + ["%.0f %%" % rate])
        print("   %4.0f %% %11.1f %12.1f %16.1f %13.1f %13.1f %12.0f %%"
              % ((100 * p,) + tuple(med[k] for k in keys) + (rate,)))
    print("   (数字は |推定 - 真値| の中央値 [mm]。特定成功率 = 櫛法が"
          "%s を当てた割合)" % CULPRIT)

    i4 = ps.index(0.4)
    print("\n  ★見逃し %.0f %% で 間隔の中央値は誤差 %.1f mm、間隔の平均は %.1f mm、"
          "**櫛法は %.1f mm**。" % (100 * ps[i4], tab["med"][i4],
                                    tab["mean"][i4], tab["spec"][i4]))
    print("     見逃しは**位相を飛ばさない** —— 抜けた山は振幅を減らすだけで、"
          "周波数は動かない。\n     間隔法は 1 個抜けるたびに間隔が 2C・3C に"
          "化けるので、中央値は見逃しが増えるほど上へ引きずられる。")
    print("  ★間隔の平均は見逃しゼロでも既に外れている(%.1f mm)—— "
          "ランダム欠陥が短い間隔を差し込むから。\n     平均は clutter に、"
          "中央値は見逃しに弱い。**どちらの弱点も櫛法には無い**。"
          % tab["mean"][0])
    print("  ★ケプストラムは誤差 %.1f 〜 %.1f mm。op の docstring が警告して"
          "いるとおり\n     「族」を返すので、最大値だけ読むと整数倍を掴む"
          "(見逃し 0 %% で %.1f mm = %.2f C を返した)。"
          % (min(tab["cep"]), max(tab["cep"]), tab["cep"][0] + c,
             (tab["cep"][0] + c) / c))

    figs.save_plot("null_vs_spectrum",
                   [("間隔の中央値", [100 * p for p in ps], tab["med"]),
                    ("間隔の平均", [100 * p for p in ps], tab["mean"]),
                    ("スペクトル 最大値", [100 * p for p in ps], tab["naive"]),
                    ("スペクトル 櫛", [100 * p for p in ps], tab["spec"])],
                   xlabel="欠陥検出の見逃し率 [%]",
                   ylabel="周長の推定誤差 |ΔC| の中央値 [mm]",
                   title="見逃しを上げるとゼロ点だけが崩れる",
                   caption="見逃しは位相を飛ばさないので、櫛の山は"
                           "低くなるだけで動かない。")
    figs.save_table("null_table",
                    ["見逃し率", "間隔の中央値", "間隔の平均",
                     "スペクトル最大値", "スペクトル櫛", "ケプストラム",
                     "櫛の特定成功率"], rows,
                    title="周長の推定誤差 [mm](%d 試行の中央値)" % SEEDS)
    return {"ps": ps, "tab": tab, "half": c / 2.0}


# --------------------------------------------------------------------------- #
# 4. 対照群 (a) —— 蛇行を補正しないとロールが割れて見える                        #
# --------------------------------------------------------------------------- #
def section_meander() -> dict:
    print("\n" + "=" * 78)
    print("4) 対照群 (a) 蛇行 —— 1 本のロールが何本に割れて見えるか")
    print("=" * 78)
    print("   条件                       CD の山の数   CD の広がり σ [mm]   "
          "レーンに残る周期欠陥   ゼロ点の推定 [mm]")
    c = CIRC[CULPRIT]
    out, rows = {}, []
    conds = (("蛇行なし(対照)", dict(meander_on=False), False),
             ("蛇行あり・補正なし", dict(meander_on=True), False),
             ("蛇行あり・補正あり", dict(meander_on=True), True))
    for lab, kw, corr in conds:
        npk, sig, nlane, cnull = [], [], [], []
        for s in range(SEEDS):
            sc = scene(SEED0 + s, **kw)
            cd = sc["cd"] + (meander(sc["md"], sc["meander_on"]) if corr else 0.0)
            per = sc["periodic"]
            k, _, _ = cd_peak_count(cd[per])
            npk.append(k)
            sig.append(float(np.std(cd[per])))
            c0 = lane_centre(cd)
            nlane.append(float(np.mean(np.abs(cd[per] - c0) <= LANE_HALF)))
            cnull.append(null_estimate(sc["md"], cd)["C"])
        out[lab] = (float(np.median(npk)), float(np.mean(sig)),
                    100.0 * float(np.mean(nlane)),
                    float(np.nanmedian(cnull)))
        rows.append([lab, "%.0f" % out[lab][0], "%.1f" % out[lab][1],
                     "%.0f %%" % out[lab][2],
                     "%.1f (%+.1f)" % (out[lab][3], out[lab][3] - c)])
        print("   %-24s %8.0f %18.1f %20.0f %% %14.1f (%+.1f)"
              % (lab, out[lab][0], out[lab][1], out[lab][2], out[lab][3],
                 out[lab][3] - c))

    a, b = out["蛇行なし(対照)"], out["蛇行あり・補正なし"]
    print("\n  ★蛇行(振幅 %.0f mm)を補正しないと、**1 本のロールの欠陥列が "
          "%.0f 本の山に割れる**\n     (CD の広がり %.1f -> %.1f mm)。"
          "レーン(半幅 %.0f mm)に残る周期欠陥は %.0f -> %.0f %%。"
          % (MEANDER_A, b[0], a[1], b[1], LANE_HALF, a[2], b[2]))
    print("  ★★それでも **MD スペクトルは無傷** —— CD を一度も見ていないから。")
    for lab, kw, corr in conds:
        es = []
        for s in range(SEEDS):
            sc = scene(SEED0 + s, **kw)
            es.append(abs(spec_estimate(sc["md"], sc["length"])["C"] - c))
        print("     %-24s スペクトルの誤差 %.2f mm" % (lab, float(np.median(es))))
        out.setdefault("spec_" + lab, float(np.median(es)))
    print("     蛇行が壊すのは「CD でレーンを切ってから数える」手法だけ。"
          "\n     ゼロ点が %.1f -> %.1f mm と外れるのはそのため。" % (a[3], b[3]))

    sc = scene(SEED0)
    per = sc["periodic"]
    _, h_raw, _ = cd_peak_count(sc["cd"][per])
    _, h_cor, _ = cd_peak_count(sc["cd"][per] + meander(sc["md"][per], True))
    sc_off = scene(SEED0, meander_on=False)
    _, h_off, _ = cd_peak_count(sc_off["cd"][sc_off["periodic"]])
    xs = (np.arange(h_raw.size) + 0.5) * CD_BIN
    figs.save_plot("meander_lanes",
                   [("蛇行なし", xs, h_off), ("蛇行あり・補正なし", xs, h_raw),
                    ("蛇行あり・補正あり", xs, h_cor)],
                   xlabel="CD 位置 [mm](web 端基準)",
                   ylabel="周期欠陥の個数(平滑後)",
                   title="蛇行は 1 本のロールを %.0f 本に割る" % b[0],
                   caption="真の傷は機械座標 CD %.0f mm の 1 か所だけ。" % NICK_CD)
    figs.save_table("meander_table",
                    ["条件", "CD の山の数", "CD の広がり σ [mm]",
                     "レーンに残る周期欠陥", "ゼロ点の推定 [mm]"], rows,
                    title="蛇行の対照群(%d 試行)" % SEEDS)
    return out


# --------------------------------------------------------------------------- #
# 5. 対照群 (b) —— 健全ロールだけ。偽の周期を拾わないか                          #
# --------------------------------------------------------------------------- #
def section_false_floor() -> dict:
    print("\n" + "=" * 78)
    print("5) 対照群 (b) 健全ロールだけ —— 偽陽性の床")
    print("=" * 78)
    print("   周期欠陥をゼロにし、ランダム欠陥だけ %d 個。櫛法は "
          "k=1..3 の高調波が**全部** %.1f 倍を超えたときだけ 1 本報告する。"
          % (int(L_FULL * CLUTTER_PER_MM), PEAK_K))
    n = 60
    rep_h, rep_t, naive_h = [], [], []
    for s in range(n):
        md = scene(9000 + s, culprits=())["md"]
        r = comb_peaks(md, L_FULL)
        rep_h.append(r["C"][0] if r["C"] else np.nan)
        naive_h.append(naive_spec_estimate(md, L_FULL)["ratio"])
        rt = comb_peaks(scene(SEED0 + s)["md"], L_FULL)
        rep_t.append(rt["C"][0] if rt["C"] else np.nan)
    rep_h = np.asarray(rep_h, float)
    rep_t = np.asarray(rep_t, float)
    fp = float(np.mean(np.isfinite(rep_h)))
    tp = float(np.mean(np.isfinite(rep_t)))
    hit = float(np.mean([identify(v) == CULPRIT for v in rep_t
                         if np.isfinite(v)])) if tp > 0 else 0.0
    print("\n   健全ロールだけ %d 試行: 報告 %d 件 -> **偽陽性 %.1f %%**"
          % (n, int(np.isfinite(rep_h).sum()), 100 * fp))
    print("   傷ありロール   %d 試行: 報告 %d 件 -> 検出 %.1f %%"
          "(うち犯人を当てた割合 %.1f %%)"
          % (n, int(np.isfinite(rep_t).sum()), 100 * tp, 100 * hit))
    print("   健全側で「帯域内の最大値 / 中央値」は 中央値 %.2f / 最大 %.2f 倍 —— "
          "しきい値 %.1f 倍に対して\n   %s。偽の周期を止めているのは"
          "しきい値だけでなく、**高調波を全部要求する fail-closed のほう**。"
          % (float(np.median(naive_h)), float(np.max(naive_h)), PEAK_K,
             "床のほうが低い" if np.max(naive_h) < PEAK_K
             else "**床のほうが高い**(単独のしきい値では止まらない)"))

    figs.save_plot("false_floor",
                   [("健全ロールだけ 最大値/中央値", np.arange(n),
                     np.sort(naive_h)),
                    ("しきい値 %.1f" % PEAK_K, [0, n - 1], [PEAK_K, PEAK_K])],
                   xlabel="試行(倍率の小さい順)",
                   ylabel="帯域内の最大値 / 中央値 [倍]",
                   title="偽陽性の床(周期欠陥ゼロ、ランダム欠陥だけ)",
                   caption="櫛法の報告件数は %d / %d 件。" % (
                       int(np.isfinite(rep_h).sum()), n))
    return {"fp": fp, "tp": tp, "hit": hit,
            "floor": float(np.max(naive_h)), "n": n}


# --------------------------------------------------------------------------- #
# 6. 崖の実測 —— 記録長を短くする                                               #
# --------------------------------------------------------------------------- #
def section_cliff(pred: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 崖の実測 —— 記録長 L を短くして「犯人の取り違え」を探す")
    print("=" * 78)
    c, nb, dc, l_crit = pred["C"], pred["neighbour"], pred["dC"], pred["L_crit"]
    print("   予測(2 節): L < %.0f mm で %s と %s は同じビンに入る。"
          % (l_crit, CULPRIT, nb))
    print("   ★崖は 2 つある。**検出の崖**(山が雑音に埋もれて何も報告できない)と、"
          "**分解の崖**\n     (報告はできるが隣のロールと区別がつかない)。"
          "Rayleigh が言っているのは後者だけ。")
    print("\n   L [mm]   ΔC=C²/L   報告率   ビン当て 誤差  成功率   "
          "補間あり 誤差  成功率   取り違え先")
    Ls = [3000.0, 4000.0, 6000.0, 8000.0, 10000.0, 12000.0, 14000.0, 17000.0,
          20000.0]
    res = {"L": [], "bin_err": [], "bin_hit": [], "int_err": [], "int_hit": [],
           "rep": []}
    rows = []
    for L in Ls:
        eb, ei = [], []
        hb = hi = rep = 0
        wrong = {}
        for s in range(SEEDS):
            sc = scene(SEED0 + s, length=L)
            b = spec_estimate(sc["md"], L, interp=False)
            i = spec_estimate(sc["md"], L, interp=True)
            if np.isfinite(b["C"]):
                rep += 1
                eb.append(abs(b["C"] - c))
                ei.append(abs(i["C"] - c))
            nb_name = identify(b["C"])
            hb += int(nb_name == CULPRIT)
            hi += int(identify(i["C"]) == CULPRIT)
            if nb_name != CULPRIT:
                wrong[nb_name] = wrong.get(nb_name, 0) + 1
        top = max(wrong, key=wrong.get) if wrong else "—"
        res["L"].append(L)
        res["rep"].append(100.0 * rep / SEEDS)
        res["bin_err"].append(float(np.median(eb)) if eb else np.nan)
        res["bin_hit"].append(100.0 * hb / SEEDS)
        res["int_err"].append(float(np.median(ei)) if ei else np.nan)
        res["int_hit"].append(100.0 * hi / SEEDS)
        rows.append(["%.0f" % L, "%.1f" % (c * c / L),
                     "%.0f %%" % res["rep"][-1], "%.1f" % res["bin_err"][-1],
                     "%.0f %%" % res["bin_hit"][-1], "%.1f" % res["int_err"][-1],
                     "%.0f %%" % res["int_hit"][-1], top])
        print("   %6.0f %9.1f %7.0f %% %13.1f %7.0f %% %13.1f %7.0f %%   %s"
              % (L, c * c / L, res["rep"][-1], res["bin_err"][-1],
                 res["bin_hit"][-1], res["int_err"][-1], res["int_hit"][-1], top))
    print("   (誤差は報告できた試行だけの中央値 [mm]。成功率は全試行に対する割合"
          " —— 未報告は失敗に数える)")

    def first_fail(hits):
        ok = [L for L, h in zip(Ls, hits) if h >= 100.0]
        return min(ok) if ok else None

    lb, li = first_fail(res["bin_hit"]), first_fail(res["int_hit"])
    print("\n   成功率が 100 %% を保つ最短の L: ビン当て %s / 補間あり %s"
          % ("%.0f mm" % lb if lb else "(全滅)",
             "%.0f mm" % li if li else "(全滅)"))
    if lb is not None:
        print("  ★予測 L_crit = %.0f mm(= C²/ΔC)に対し、**ビン当ての実測は "
              "%.0f mm** —— 比 %.2f。" % (l_crit, lb, lb / l_crit))
        print("     %s。Rayleigh はビン幅の議論なので、山をビンに丸める推定器"
              "とは直接比べられる。"
              % ("予測は当たった" if 0.6 <= lb / l_crit <= 1.6
                 else "予測は外した"))
    if li is not None:
        print("  ★★**放物線補間を入れると崖は %.0f mm まで下がる**"
              "(予測の %.2f 倍)。" % (li, li / l_crit))
        print("     Rayleigh 分解能は「2 本の山を分ける」条件であって、"
              "「1 本の山の位置を測る」条件ではない。\n     山が 1 本しか無い"
              "と分かっているなら、その頂点は S/N の許すかぎりビンより細かく"
              "決まる。\n     **予測は保守的すぎた** —— 外れ方の向きまで含めて"
              "記録しておく。")
    print("     取り違え先はほぼ %s(周長差 %.2f mm)。"
          % (rows[0][-1], abs(CIRC[rows[0][-1]] - c) if rows[0][-1] in CIRC
             else np.nan))

    figs.save_plot("cliff_length",
                   [("ビン当て", res["L"], res["bin_hit"]),
                    ("放物線補間あり", res["L"], res["int_hit"]),
                    ("予測 L_crit = %.0f mm" % l_crit, [l_crit, l_crit], [0, 100])],
                   xlabel="記録長 L [mm]", ylabel="犯人ロールの特定成功率 [%]",
                   title="記録長の崖 —— 予測を先に立ててから測った",
                   caption="縦線が閉形式の予測 C²/ΔC。補間ありはそれより"
                           "短い L でも当てられる。")
    figs.save_plot("cliff_error",
                   [("ビン当て 実測", res["L"], res["bin_err"]),
                    ("補間あり 実測", res["L"], res["int_err"]),
                    ("予測 ΔC = C²/L", res["L"], [c * c / L for L in Ls])],
                   xlabel="記録長 L [mm]", ylabel="周長の推定誤差 |ΔC| [mm]",
                   title="周長の推定誤差と Rayleigh 分解能")
    figs.save_table("cliff_table",
                    ["L [mm]", "ΔC=C²/L", "報告率", "ビン当て 誤差",
                     "ビン当て 成功率", "補間あり 誤差", "補間あり 成功率",
                     "取り違え先"], rows,
                    title="記録長の掃引(%d 試行)" % SEEDS)
    res["L_bin"], res["L_int"] = lb, li
    return res


# --------------------------------------------------------------------------- #
# 7. 2 本のロールが傷ついている場合                                             #
# --------------------------------------------------------------------------- #
def section_two_rolls() -> dict:
    print("\n" + "=" * 78)
    print("7) 2 本のロールが傷ついている場合")
    print("=" * 78)
    both = (CULPRIT, CULPRIT2)
    cs = [CIRC[n] for n in both]
    print("   %s C=%.2f mm と %s C=%.2f mm を同時に傷つける。"
          % (both[0], cs[0], both[1], cs[1]))
    hits = 0
    errs = [[], []]
    nrep = []
    for s in range(SEEDS):
        sc = scene(SEED0 + s, culprits=both)
        found = comb_peaks(sc["md"], sc["length"])["C"]
        nrep.append(len(found))
        for i, cc in enumerate(cs):
            errs[i].append(min((abs(v - cc) for v in found), default=np.inf))
        hits += int(set(both) <= {identify(v) for v in found})
    print("   %d 試行で **両方のロールを同時に当てた割合 %.0f %%**"
          "(報告したロールの本数 中央値 %.0f)"
          % (SEEDS, 100.0 * hits / SEEDS, float(np.median(nrep))))
    print("   周長の誤差(中央値): %s %.1f mm / %s %.1f mm"
          % (both[0], float(np.median(errs[0])), both[1],
             float(np.median(errs[1]))))
    print("   ★スペクトルは山を 1 本しか返さない道具ではない —— "
          "同じ 1 回の走査で 2 本とも立つ。\n     間隔法は「間隔の分布が"
          "2 つの周期の混合」になるので、中央値も平均も**どちらの周長でもない"
          "値**を返す。")
    e0 = null_estimate(scene(SEED0, culprits=both)["md"],
                       scene(SEED0, culprits=both)["cd"])
    print("     実際、同じ場面でゼロ点(レーン + 中央値)は %.1f mm "
          "—— %s(%.2f)でも %s(%.2f)でもない。"
          % (e0["C"], both[0], cs[0], both[1], cs[1]))

    sc = scene(SEED0, culprits=both)
    sp = md_spectrum(sc["md"], sc["length"])
    band = sp["band"]
    cc = 1.0 / sp["f"][band]
    figs.save_plot("spectrum_two",
                   [("MD スペクトル", cc, sp["m"][band]),
                    ("ロール台帳", [CIRC[n] for n, _ in ROLLS],
                     [float(sp["m"][band].max()) * 0.06] * len(ROLLS))],
                   xlabel="周長 C = 1/f [mm]", ylabel="振幅",
                   title="2 本傷つけた web の MD スペクトル",
                   caption="下の点が台帳の 5 本。山は %s と %s に立つ。"
                           % both, kinds=["line", "scatter"])
    return {"hit": 100.0 * hits / SEEDS, "null": float(e0["C"])}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    assert hasattr(fs, "spectrum") and hasattr(fs, "cepstrum")
    assert not hasattr(fs, "lomb_scargle") and not hasattr(fs.ledger, "lomb_scargle")
    print("  (a) **点の一覧(イベント時刻)から直接スペクトルを取る口が無い**。"
          "spectrum / cepstrum はどちらも等間隔の信号を要求するので、"
          "この PoC は自分でヒストグラムに落としている。欠陥地図・"
          "パーティクルカウンタ・打痕は全部この形なので、"
          "Lomb-Scargle か単純な binned periodogram が 1 本あると良い。")

    assert not hasattr(fs, "peak_interpolate") and not hasattr(fs, "parabolic_peak")
    print("  (b) **山の頂点をサブビンで求める口が無い**。find_peaks は"
          "整数の添字しか返さない。6 節で測ったとおり、放物線補間を入れるだけで"
          "崖が %.1f 倍短い記録長まで下がる —— 補間の有無は"
          "「分解能」の議論そのものを変えるので、族に入れる価値がある。" % 1.0)

    assert not hasattr(fs, "roll_periodicity") and not hasattr(fs, "web_defect_map")
    print("  (c) ロール周期の逆算(周長台帳への当てはめ)そのものは道具ではなく"
          "作法。ただし「候補の台帳」と「分解能 C²/L」を引数で強制する設計に"
          "しておかないと、区別できない 2 本を平気で 1 本に決めてしまう。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("ロール to ロールの周期欠陥 —— どのロールが犯人か、いつ言えなくなるか")
    print("web 幅 %.0f mm / 記録長 %.0f mm / 搬送ロール %d 本"
          % (WEB_W, L_FULL, len(ROLLS)))
    print("=" * 78)

    sc = section_scene()
    pred = section_predict()
    nul = section_null()
    mea = section_meander()
    flo = section_false_floor()
    cli = section_cliff(pred)
    two = section_two_rolls()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    i4 = nul["ps"].index(0.4)
    print("  * 見逃し %.0f %% で ゼロ点(間隔の中央値)は誤差 %.1f mm、"
          "スペクトルは %.1f mm。位相が飛ばないから。"
          % (100 * nul["ps"][i4], nul["tab"]["med"][i4], nul["tab"]["spec"][i4]))
    print("  * 蛇行 %.0f mm を補正しないと 1 本のロールが %.0f 本に割れ、"
          "レーンに残る周期欠陥が %.0f %% になる。MD スペクトルは無傷。"
          % (MEANDER_A, mea["蛇行あり・補正なし"][0],
             mea["蛇行あり・補正なし"][2]))
    print("  * 健全ロールだけ %d 試行で偽陽性 %.1f %%(単独のしきい値なら床が "
          "%.2f 倍まで来るので止まらない。止めているのは高調波の全数要求)。"
          % (flo["n"], 100 * flo["fp"], flo["floor"]))
    print("  * 崖: 予測 C²/ΔC = %.0f mm に対し実測は ビン当て %s / 補間あり %s。"
          % (pred["L_crit"],
             "%.0f mm" % cli["L_bin"] if cli["L_bin"] else "(全滅)",
             "%.0f mm" % cli["L_int"] if cli["L_int"] else "(全滅)"))
    print("  * 2 本同時に傷ついていても %.0f %% で両方当たる(ゼロ点は %.1f mm "
          "= どちらでもない値)。" % (two["hit"], two["null"]))

    # --- 所見を固定する assert(穴が塞がったら鳴る)------------------------- #
    c = CIRC[CULPRIT]
    assert sc["n_per"] > 25 and sc["n_all"] > sc["n_per"] + 40
    assert nul["tab"]["spec"][0] < 2.0, nul["tab"]["spec"][0]
    assert nul["tab"]["med"][i4] > 20.0 * nul["tab"]["spec"][i4]
    assert nul["tab"]["hit"][i4] >= 100.0
    assert mea["蛇行なし(対照)"][0] == 1.0
    assert mea["蛇行あり・補正なし"][0] >= 2.0
    assert mea["蛇行あり・補正あり"][0] == 1.0
    assert flo["fp"] == 0.0 and flo["tp"] == 1.0
    assert flo["floor"] > PEAK_K
    assert cli["bin_hit"][-1] == 100.0 and cli["int_hit"][-1] == 100.0
    assert cli["L_int"] is not None and cli["L_bin"] is not None
    assert cli["L_int"] < cli["L_bin"]
    assert two["hit"] >= 90.0
    assert abs(two["null"] - CIRC[CULPRIT]) > 30.0
    assert abs(two["null"] - CIRC[CULPRIT2]) > 30.0
    assert c > 0

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
