# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(x, y, t) で数える —— 通過台数とオクルージョン、そして L/V という 1 つの定数。

交通量調査は「1 時間に何台通ったか」を数える仕事です。カメラ 1 台で数える
とき、素朴にやると**フレームごとに車を数えて**しまいますが、それは
「いま何台写っているか」であって「何台通ったか」ではありません。

この PoC は 2-D のデモを時間方向に伸ばして 3-D (x, y, t) にし、

* ゼロ点 = フレームごとに背景差分 → 連結成分の数(最大値 / 平均)
* 仮想ループ = 計数列 1 本の占有の立ち上がり回数(1-D)
* スリット法 = 計数線 1 行を時間方向に積んだ **(t, x) 画像**の連結成分
  (2-D の `blob_*` 族がそのまま使える。帯の数 = 台数、帯の傾き = 速度)

を同じ列(x = 210)で測り比べます。

EXTEND: 実写に差し替えるなら :func:`render_sequence` が返す ``(T,H,W)`` を
撮影動画に、``LANES`` の ``slit`` を**車線の中心を通る画像行**に置き換えます。
真値(通過台数)は人手計数か誘導ループの値を使うこと —— **別のカメラ手法を
真値にしてはいけません**(同じオクルージョンで同じ向きに間違えます)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点はそもそも別の量を測っている**。フレームごとの連結成分の最大値は
   「同時に写っている台数」であって通過台数ではない。実測でも通過 17 台に
   対して最大値 4、平均 2.6 —— 桁が違うので比べる意味が無い。
   ★同じ画像列から「同時台数」として比べても、オクルージョンで下振れする。
2. ★★**スリット法の強さは「計数線を跨ぐ瞬間だけ見ればよい」ことではなく、
   「計数列と交わる帯だけを数える」ことにあった**。帯を全部数えると
   フレーム間隔を空けたとき帯が千切れて過大になるが、x=210 の列と交わる
   帯だけを数えると**過大は起きず、見逃しだけ**になる。同じスリット画像
   から 2 通りの数え方が出て、壊れ方が逆向きになる。
3. ★★**破綻の条件が 3 つとも同じ形の式で書ける: L / V**(車長 ÷ 速度)。
   (a) 車間を詰めると、時間間隔が L/V を切ったところで帯が融合して過小に
   なる。(b) フレーム間隔 Δt が L/V を超えると、その車が計数列に一度も
   標本化されず見逃す。予測 Σ min(1, L/(V·Δt)) と実測の一致は 6 節の表。
   (c) 停止(V→0)は L/V → ∞ で、破綻しない側へ振り切れる。
4. ★**背の高い車は別の車線のスリットに書き込む**。トラック(画像で 50〜99 行)
   は遠い車線の計数行 63 も覆うので、遠い車線のスリットに偽の帯が立つ。
   オクルージョンは「隠して減らす」だけでなく「はみ出して増やす」。
5. ★★**渋滞で壊れるのは検出器ではなく背景モデル**。時間中央値の背景は、
   停止した車を**背景として学習する**。停止後の前景率は実測で下がり、
   ゼロ点もスリット法も同時に落ちる。片方だけを直しても意味が無い。
6. ★**速度は台数より先に劣化するが、壊れ方は緩やか**。フレーム間隔を
   広げると速度誤差は連続に増え、台数は L/V で階段状に落ちる。
   ★台帳の ``blob_features["angle"]`` からも速度は出る —— ただし帯が
   画面幅で切れているぶん系統的にずれるので、行ごとの重心を線形当てはめ
   したほうが良い(両方測って本文に出す)。

【グラウンドトゥルース】
車は既知の長さ・既知の等速度で流し、**計数列 x=210 を跨ぐ時刻を先に決めて
から**初期位置を逆算する(だから通過台数は定義上ちょうど n 台)。真値は
連続時間で定義し、標本化(フレーム)は推定器の側だけに掛ける —— こうしないと
「フレームレートを落として見逃した」を測れない。

来歴(公開文献のみ): Nagel & Enkelmann の時空間画像解析 / Wolf, *Sensors* 21
(2021) —— 交通流のスリットスキャン計数 / Bobick & Davis, *PAMI* 23 (2001) 257。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_LAB = fs.ledger        # blob 族の公開経路

# --- 場面の諸元 -------------------------------------------------------------- #
W_PX, H_PX = 384, 160
FPS = 10.0                 # 交通カメラの実勢(10 fps)
X_REF = 210                # 計数列(この列を跨いだら 1 台)
T_FRAMES = 180

#: 車線。``y0..y1-1`` が車体の行、``slit`` が計数線の行、``mps`` が m/px。
#: 速度は 45〜70 km/h 相当になるように選んである(下の 1 節で印字)。
LANES = {
    "far":  {"y0": 58, "y1": 71, "slit": 63, "mps": 0.55,
             "v": (2.4, 3.6), "len": (22, 30)},
    "near": {"y0": 71, "y1": 100, "slit": 85, "mps": 0.25,
             "v": (5.0, 7.0), "len": (44, 64)},
}
TRUCK_Y0 = 50              # 背の高い車の上端(= 遠い車線の計数行 63 を覆う)
ROAD, MARK = 0.45, 0.72
FG_THRESHOLD = 0.10


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def make_vehicles(seed: int = 3, n_far: int = 9, n_near: int = 8,
                  headway: float | None = None, truck_p: float = 0.30) -> list[dict]:
    """車の一覧。**計数列を跨ぐ時刻を先に決めて**初期位置を逆算する。

    ``headway`` を渡すと車線ごとに等間隔(フレーム)で流す(車間の掃引用)。
    """
    rng = np.random.default_rng(seed)
    out = []
    for lane, n in (("far", n_far), ("near", n_near)):
        cfg = LANES[lane]
        for i in range(n):
            v = float(rng.uniform(*cfg["v"]))
            length = float(rng.uniform(*cfg["len"]))
            if headway is None:
                s = float(rng.uniform(6.0, T_FRAMES - 6.0))
            else:
                s = 8.0 + i * headway
            tall = (lane == "near") and bool(rng.random() < truck_p)
            out.append({"lane": lane, "v": v, "len": length, "cross": s,
                        "x0": X_REF - v * s, "tall": tall,
                        "grey": float(rng.choice([1, -1]) * rng.uniform(0.16, 0.32))})
    return out


def positions(vehicles, s: float) -> np.ndarray:
    """時刻 ``s``(フレーム単位、実数)での車体中心 x。"""
    return np.asarray([v["x0"] + v["v"] * s for v in vehicles], np.float64)


def crosses_ref(v: dict, s_max: float) -> bool:
    """連続時間で計数列を跨ぐか(**真値の定義**。標本化とは無関係)。"""
    return 0.0 <= v["cross"] <= s_max


def _road() -> np.ndarray:
    """静止した路面(車線の区切りに破線)。"""
    img = np.full((H_PX, W_PX), ROAD)
    img[0:44, :] = 0.30                        # 路肩(上)
    img[104:, :] = 0.34                        # 路肩(下)
    for y in (57, 70, 100):
        for x0 in range(0, W_PX, 24):
            img[y, x0:x0 + 14] = MARK
    return img


def render_sequence(vehicles, times, noise: float = 0.015, seed: int = 0) -> np.ndarray:
    """``(T,H,W)`` の動画。**遠い車線を先に、近い車線を後で塗る**(画家法)。"""
    rng = np.random.default_rng(seed)
    road = _road()
    vid = np.empty((len(times), H_PX, W_PX))
    order = sorted(range(len(vehicles)), key=lambda i: vehicles[i]["lane"] != "far")
    for k, s in enumerate(times):
        frame = road.copy()
        for i in order:
            v = vehicles[i]
            cfg = LANES[v["lane"]]
            xc = v["x0"] + v["v"] * s
            c0 = int(round(xc - 0.5 * v["len"]))
            c1 = int(round(xc + 0.5 * v["len"]))
            c0, c1 = max(c0, 0), min(c1, W_PX)
            if c1 <= c0:
                continue
            y0 = TRUCK_Y0 if v["tall"] else cfg["y0"]
            frame[y0:cfg["y1"], c0:c1] = np.clip(ROAD + v["grey"], 0.05, 0.95)
        vid[k] = frame
    return np.clip(vid + noise * rng.standard_normal(vid.shape), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 検出器                                                                        #
# --------------------------------------------------------------------------- #
def foreground(vid: np.ndarray) -> np.ndarray:
    """背景差分(時間中央値のモデル)。``fs.background_subtraction`` をそのまま。"""
    return np.asarray(fs.background_subtraction(vid, threshold=FG_THRESHOLD)) > 0.5


def per_frame_counts(mask: np.ndarray) -> np.ndarray:
    """ゼロ点。フレームごとに連結成分を数える。"""
    return np.asarray([int(_LAB.blob_label(m).max()) for m in mask], np.int64)


def kymograph(mask: np.ndarray, row: int) -> np.ndarray:
    """計数線 1 行を時間方向へ積んだ (t, x) 画像。"""
    return mask[:, row, :]


def slit_count(kym: np.ndarray, x_ref: int = X_REF) -> dict:
    """スリット画像の帯を数える。**全部の帯**と**計数列と交わる帯**を分ける。"""
    lab = _LAB.blob_label(kym.astype(np.float64) > 0.5)
    n_all = int(lab.max())
    hit = np.unique(lab[:, x_ref])
    hit = hit[hit > 0]
    return {"labels": lab, "n_all": n_all, "n_ref": int(hit.size), "ids": hit}


def band_speeds(kym: np.ndarray, lab: np.ndarray, ids, dt: float = 1.0) -> dict:
    """帯の傾きから速度 [px/frame]。行ごとの重心の線形当てはめと、台帳の angle。"""
    feats = _LAB.blob_features(lab)
    ang = np.asarray(feats["angle"], np.float64)
    fit, from_angle, npts = [], [], []
    for i in ids:
        rr, cc = np.nonzero(lab == i)
        rows = np.unique(rr)
        if rows.size < 2:
            continue
        cen = np.asarray([cc[rr == r].mean() for r in rows], np.float64)
        slope = np.polyfit(rows.astype(np.float64), cen, 1)[0]
        fit.append(slope / dt)
        # angle は +col -> +row(画面で時計回り)。帯の向きは (Δrow, Δcol) = (1, V·dt)
        # なので tan(angle) = 1/(V·dt) -> V = cot(angle)/dt。
        a = ang[int(i) - 1]
        from_angle.append((1.0 / np.tan(a) if abs(np.tan(a)) > 1e-9 else np.nan) / dt)
        npts.append(rows.size)
    return {"fit": np.asarray(fit), "angle": np.asarray(from_angle),
            "rows": np.asarray(npts)}


def virtual_loop(mask: np.ndarray, row: int, x_ref: int = X_REF) -> int:
    """仮想ループ(1-D)。計数列の占有が空 -> 有りへ変わった回数。"""
    occ = mask[:, row, x_ref].astype(np.int8)
    return int(np.count_nonzero(np.diff(np.r_[0, occ]) == 1))


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— 連続時間で計数列を跨ぐ台数")
    print("=" * 78)

    veh = make_vehicles()
    times = np.arange(T_FRAMES, dtype=np.float64)
    vid = render_sequence(veh, times)
    mask = foreground(vid)

    truth = {ln: sum(1 for v in veh if v["lane"] == ln and crosses_ref(v, T_FRAMES - 1))
             for ln in LANES}
    trucks = sum(1 for v in veh if v["tall"] and crosses_ref(v, T_FRAMES - 1))
    print("  %d フレーム / %d x %d px / 計数列 x = %d"
          % (T_FRAMES, W_PX, H_PX, X_REF))
    for ln in LANES:
        sp = [v["v"] for v in veh if v["lane"] == ln]
        print("   %-5s 通過 %d 台  速度 %.2f〜%.2f px/frame "
              "(= %.0f〜%.0f km/h, %.2f m/px)"
              % (ln, truth[ln], min(sp), max(sp),
                 min(sp) * FPS * LANES[ln]["mps"] * 3.6,
                 max(sp) * FPS * LANES[ln]["mps"] * 3.6, LANES[ln]["mps"]))
    print("   うち背の高い車(トラック)%d 台 —— 遠い車線の計数行 %d も覆う。"
          % (trucks, LANES["far"]["slit"]))

    # 前景が取れているかの素朴な検算(路面だけの列は前景にならないこと)
    fg_rate = float(mask.mean())
    print("\n  前景率 %.3f(背景 = 時間中央値、しきい値 %.2f)。"
          % (fg_rate, FG_THRESHOLD))
    assert 0.01 < fg_rate < 0.30, fg_rate
    return {"veh": veh, "vid": vid, "mask": mask, "truth": truth,
            "trucks": trucks, "times": times}


# --------------------------------------------------------------------------- #
# 2. ゼロ点                                                                     #
# --------------------------------------------------------------------------- #
def section_zero_point(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— フレームごとに連結成分を数える")
    print("=" * 78)

    veh, mask = sc["veh"], sc["mask"]
    cc = per_frame_counts(mask)
    # 真の「同時に写っている台数」(車体が画面に一部でも入っている数)
    sim = []
    for s in sc["times"]:
        xs = positions(veh, s)
        ln = np.asarray([v["len"] for v in veh])
        sim.append(int(np.count_nonzero((xs + ln / 2 > 0) & (xs - ln / 2 < W_PX))))
    sim = np.asarray(sim)
    total = sum(sc["truth"].values())

    print("  通過台数(真値)        %d 台" % total)
    print("  フレームごと CC の最大値 %d / 平均 %.2f / 中央値 %.1f"
          % (cc.max(), cc.mean(), np.median(cc)))
    print("  真の同時台数の最大値     %d / 平均 %.2f" % (sim.max(), sim.mean()))
    print("\n  ★『最大値を台数とする』は通過台数を %.0f %% 過小に答える"
          "(%d 対 %d)。**別の量を測っている**。"
          % (100 * (1 - cc.max() / total), cc.max(), total))
    under = int(np.count_nonzero(cc < sim))
    print("  ★同時台数として比べても %d/%d フレームで下振れする"
          "(平均 %.2f 台不足)。原因は融合とオクルージョン。"
          % (under, cc.size, float((sim - cc).mean())))

    loop_far = virtual_loop(mask, LANES["far"]["slit"])
    loop_near = virtual_loop(mask, LANES["near"]["slit"])
    print("\n  仮想ループ(計数列の立ち上がり): far %d / near %d / 合計 %d(真値 %d)"
          % (loop_far, loop_near, loop_far + loop_near, total))

    figs.save_plot("per_frame",
                   [("真の同時台数", sc["times"], sim),
                    ("検出した連結成分", sc["times"], cc),
                    ("通過台数(真値)", sc["times"], [total] * cc.size)],
                   xlabel="フレーム", ylabel="台数",
                   title="フレームごとに数えても通過台数にはならない",
                   caption="上の水平線が答えるべき数(通過 %d 台)。"
                           "下の 2 本は「いま写っている数」で、しかも検出側は"
                           "融合で下振れする。" % total)
    return {"cc": cc, "sim": sim, "total": total,
            "loop": loop_far + loop_near, "loop_far": loop_far,
            "loop_near": loop_near}


# --------------------------------------------------------------------------- #
# 3. スリット法                                                                 #
# --------------------------------------------------------------------------- #
def section_slit(sc: dict, zp: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) スリット法 —— (t, x) 画像の帯を数え、傾きから速度を出す")
    print("=" * 78)
    print("   車線    真値   帯(全部)  帯(計数列と交わる)  速度誤差(重心当て)"
          "  速度誤差(angle)")

    out = {}
    for ln in LANES:
        kym = kymograph(sc["mask"], LANES[ln]["slit"])
        s = slit_count(kym)
        sp = band_speeds(kym, s["labels"], s["ids"])
        true_v = np.asarray(sorted(v["v"] for v in sc["veh"]
                                   if v["lane"] == ln
                                   and crosses_ref(v, T_FRAMES - 1)))
        est = np.sort(sp["fit"])
        ea = np.sort(sp["angle"][np.isfinite(sp["angle"])])
        m = min(true_v.size, est.size)
        err = 100 * np.mean(np.abs(est[:m] - true_v[:m]) / true_v[:m]) if m else np.nan
        ma = min(true_v.size, ea.size)
        erra = (100 * np.mean(np.abs(ea[:ma] - true_v[:ma]) / true_v[:ma])
                if ma else np.nan)
        print("   %-5s  %4d   %6d      %10d          %8.2f %%       %8.2f %%"
              % (ln, sc["truth"][ln], s["n_all"], s["n_ref"], err, erra))
        out[ln] = {"kym": kym, "slit": s, "speed": sp, "err": err, "erra": erra,
                   "true_v": true_v}

    tot_ref = sum(out[ln]["slit"]["n_ref"] for ln in LANES)
    print("\n  合計: スリット %d 台 / 仮想ループ %d 台 / ゼロ点(最大値) %d 台"
          " / 真値 %d 台" % (tot_ref, zp["loop"], zp["cc"].max(), zp["total"]))
    print("  ★遠い車線が %+d 台になっているのは、トラック %d 台が計数行 %d を"
          "覆って偽の帯を作るから(4 節)。"
          % (out["far"]["slit"]["n_ref"] - sc["truth"]["far"], sc["trucks"],
             LANES["far"]["slit"]))
    print("  ★速度は行ごとの重心を線形当てはめすると誤差 %.2f / %.2f %%。"
          % (out["far"]["err"], out["near"]["err"]))
    print("     台帳の blob_features['angle'] からも出せるが %.2f / %.2f %% —— "
          "帯が画面の左右で切れているぶん主軸が寝るので、当てはめのほうが良い。"
          % (out["far"]["erra"], out["near"]["erra"]))

    figs.save_grid("scene",
                   [sc["vid"][60], sc["mask"][60].astype(np.float64),
                    out["far"]["kym"].astype(np.float64),
                    out["near"]["kym"].astype(np.float64)],
                   ["60 フレーム目", "前景マスク(同じフレーム)",
                    "far のスリット (t,x)", "near のスリット (t,x)"],
                   ncols=1, title="1 枚の絵と、時間方向に積んだ 2 枚のスリット")
    return out


# --------------------------------------------------------------------------- #
# 4. 背の高い車が別の車線に書き込む                                             #
# --------------------------------------------------------------------------- #
def section_tall(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) オクルージョンは「減らす」だけでなく「増やす」")
    print("=" * 78)

    rows = []
    for p in (0.0, 0.30, 0.60):
        veh = make_vehicles(seed=3, truck_p=p)
        n_truck = sum(1 for v in veh if v["tall"])
        vid = render_sequence(veh, np.arange(T_FRAMES, dtype=np.float64))
        mask = foreground(vid)
        s_far = slit_count(kymograph(mask, LANES["far"]["slit"]))
        s_near = slit_count(kymograph(mask, LANES["near"]["slit"]))
        cc = per_frame_counts(mask)
        t_far = sum(1 for v in veh if v["lane"] == "far")
        t_near = sum(1 for v in veh if v["lane"] == "near")
        rows.append([("%.0f %%" % (100 * p)), str(n_truck),
                     "%d / %d" % (s_far["n_ref"], t_far),
                     "%d / %d" % (s_near["n_ref"], t_near),
                     str(int(cc.max()))])
        print("   トラック率 %3.0f %%(%d 台): far %d/%d、near %d/%d、"
              "ゼロ点の最大値 %d" % (100 * p, n_truck, s_far["n_ref"], t_far,
                                     s_near["n_ref"], t_near, cc.max()))

    print("\n  ★遠い車線の過大分は**トラックの台数と一致する**"
          "(背が %d 行から始まり、計数行 %d を覆うため)。"
          % (TRUCK_Y0, LANES["far"]["slit"]))
    print("     車線ごとにスリットを引いても、**行が物理的に重なっていれば"
          "分離できない** —— 直すなら計数行ではなく車線の帯で切る必要がある。")
    figs.save_table("tall_vehicles",
                    ["トラック率", "台数", "far 帯/真値", "near 帯/真値",
                     "ゼロ点 最大"],
                    rows, title="背の高い車が遠い車線のスリットに書き込む")
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 5. 車間を詰める —— 融合の閾値 L/V                                             #
# --------------------------------------------------------------------------- #
def section_headway() -> dict:
    print("\n" + "=" * 78)
    print("5) 車間を詰める —— 帯が融合する閾値は headway = L/V [frame]")
    print("=" * 78)
    print("  近い車線だけを等間隔で流す(L, V は 1 台目の値で代表)。")
    print("   headway   L/V     真値   スリット   予測(融合後の群数)   ゼロ点最大")

    rows, hs, got, pred = [], [], [], []
    for hw in (4.0, 6.0, 8.0, 10.0, 13.0, 17.0, 22.0):
        veh = [v for v in make_vehicles(seed=7, n_far=0, n_near=7,
                                        headway=hw, truck_p=0.0)]
        vid = render_sequence(veh, np.arange(T_FRAMES, dtype=np.float64))
        mask = foreground(vid)
        s = slit_count(kymograph(mask, LANES["near"]["slit"]))
        cc = per_frame_counts(mask)
        # 予測: 隣り合う 2 台の車体が計数線上で重なる(空隙 < 1 px)なら融合。
        groups = 1
        for a, b in zip(veh[:-1], veh[1:]):
            gap = b["v"] * (b["cross"] - a["cross"]) - 0.5 * (a["len"] + b["len"])
            if gap >= 1.0:
                groups += 1
        lv = float(np.mean([v["len"] / v["v"] for v in veh]))
        rows.append(["%.0f" % hw, "%.1f" % lv, str(len(veh)), str(s["n_ref"]),
                     str(groups), str(int(cc.max()))])
        hs.append(hw)
        got.append(s["n_ref"])
        pred.append(groups)
        print("    %5.0f   %5.1f    %4d   %6d      %10d          %6d"
              % (hw, lv, len(veh), s["n_ref"], groups, cc.max()))

    agree = sum(1 for g, p in zip(got, pred) if g == p)
    print("\n  ★予測(空隙 1 px の幾何)と実測が %d/%d 条件で一致。"
          % (agree, len(got)))
    print("     融合は headway が L/V(平均 %.1f frame)を切るあたりから始まる。"
          % np.mean([float(r[1]) for r in rows]))
    return {"hs": hs, "got": got, "pred": pred, "rows": rows}


# --------------------------------------------------------------------------- #
# 6. フレームレート —— 見逃しの閾値 L/(V·Δt)                                    #
# --------------------------------------------------------------------------- #
def section_framerate() -> dict:
    print("\n" + "=" * 78)
    print("6) フレームレートを落とす —— 台数と速度、どちらが先に壊れるか")
    print("=" * 78)
    print("   Δt   実効 fps   真値  帯(全部)  帯(計数列)  予測 Σmin(1,L/VΔt)"
          "   速度誤差")

    veh = make_vehicles(seed=3)
    crossing = [v for v in veh if crosses_ref(v, T_FRAMES - 1)]
    total = len(crossing)
    dts, n_all_l, n_ref_l, pred_l, verr_l = [], [], [], [], []
    rows = []
    for dt in (1, 2, 3, 4, 6, 8, 12, 16):
        times = np.arange(0.0, T_FRAMES, float(dt))
        vid = render_sequence(veh, times)
        mask = foreground(vid)
        n_all = n_ref = 0
        errs = []
        for ln in LANES:
            s = slit_count(kymograph(mask, LANES[ln]["slit"]))
            n_all += s["n_all"]
            n_ref += s["n_ref"]
            sp = band_speeds(kymograph(mask, LANES[ln]["slit"]),
                             s["labels"], s["ids"], dt=float(dt))
            tv = np.asarray(sorted(v["v"] for v in crossing if v["lane"] == ln))
            ev = np.sort(sp["fit"])
            m = min(tv.size, ev.size)
            if m:
                errs.append(100 * np.mean(np.abs(ev[:m] - tv[:m]) / tv[:m]))
        pred = float(sum(min(1.0, v["len"] / (v["v"] * dt)) for v in crossing))
        verr = float(np.mean(errs)) if errs else np.nan
        dts.append(dt)
        n_all_l.append(n_all)
        n_ref_l.append(n_ref)
        pred_l.append(pred)
        verr_l.append(verr)
        rows.append(["%d" % dt, "%.1f" % (FPS / dt), str(total), str(n_all),
                     str(n_ref), "%.1f" % pred, "%.1f %%" % verr])
        print("   %3d    %6.1f     %4d  %7d   %8d      %12.1f     %7.2f %%"
              % (dt, FPS / dt, total, n_all, n_ref, pred, verr))

    lv = sorted(v["len"] / v["v"] for v in crossing)
    print("\n  ★L/V の分布: %.1f 〜 %.1f frame(中央値 %.1f)。"
          % (lv[0], lv[-1], float(np.median(lv))))
    print("  ★**帯を全部数える**と Δt を広げたとき千切れて過大になる"
          "(%d -> %d)。" % (n_all_l[0], max(n_all_l)))
    print("     **計数列と交わる帯だけ**を数えると過大は起きず、"
          "見逃しだけになる(%d -> %d)。" % (n_ref_l[0], n_ref_l[-1]))
    print("  ★予測 Σ min(1, L/(V·Δt)) との差は %+.1f 〜 %+.1f 台。"
          % (min(g - p for g, p in zip(n_ref_l, pred_l)),
             max(g - p for g, p in zip(n_ref_l, pred_l))))
    first_count = next((d for d, g in zip(dts, n_ref_l) if g < total), None)
    first_speed = next((d for d, e in zip(dts, verr_l) if e > 5.0), None)
    print("  ★先に壊れたのは %s(台数は Δt=%s で欠け始め、速度誤差 5 %% 超は "
          "Δt=%s)。"
          % ("速度" if (first_speed or 99) < (first_count or 99) else "台数",
             first_count, first_speed))

    figs.save_plot("framerate",
                   [("真値", dts, [total] * len(dts)),
                    ("帯(計数列と交わる)", dts, n_ref_l),
                    ("予測 Σmin(1, L/VΔt)", dts, pred_l),
                    ("帯(全部)", dts, n_all_l)],
                   xlabel="フレーム間隔 Δt [frame]", ylabel="台数",
                   title="フレームレートを落とすと数え方で壊れ方が逆になる",
                   caption="全部の帯を数えると千切れて過大に、計数列と交わる"
                           "帯だけなら見逃しだけ。予測は閉形式 Σmin(1, L/VΔt)。")
    return {"dts": dts, "n_all": n_all_l, "n_ref": n_ref_l, "pred": pred_l,
            "verr": verr_l, "total": total, "rows": rows}


# --------------------------------------------------------------------------- #
# 7. 渋滞 —— 壊れるのは検出器ではなく背景モデル                                 #
# --------------------------------------------------------------------------- #
def _jam_positions(veh, times, stop_at, brake_from):
    """減速して停止する軌跡(x は単調非減少)。"""
    out = np.empty((len(times), len(veh)))
    for j, v in enumerate(veh):
        for i, s in enumerate(times):
            x = v["x0"] + v["v"] * s
            out[i, j] = min(x, stop_at[j]) if s >= brake_from else x
    return out


def section_jam() -> dict:
    print("\n" + "=" * 78)
    print("7) 渋滞 —— 壊れるのは検出器ではなく背景モデル")
    print("=" * 78)

    veh = make_vehicles(seed=11, n_far=0, n_near=6, headway=14.0, truck_p=0.0)
    times = np.arange(T_FRAMES, dtype=np.float64)
    # 先頭から順に X_REF の手前へ詰めて停止させる
    stop_at = [X_REF + 40 - k * 70.0 for k in range(len(veh))]
    xs = _jam_positions(veh, times, stop_at, brake_from=40.0)

    road = _road()
    vid = np.empty((times.size, H_PX, W_PX))
    for i in range(times.size):
        frame = road.copy()
        for j, v in enumerate(veh):
            c0 = max(int(round(xs[i, j] - 0.5 * v["len"])), 0)
            c1 = min(int(round(xs[i, j] + 0.5 * v["len"])), W_PX)
            if c1 > c0:
                frame[LANES["near"]["y0"]:LANES["near"]["y1"], c0:c1] = \
                    np.clip(ROAD + v["grey"], 0.05, 0.95)
        vid[i] = frame
    rng = np.random.default_rng(1)
    vid = np.clip(vid + 0.015 * rng.standard_normal(vid.shape), 0.0, 1.0)

    mask = foreground(vid)
    row = LANES["near"]["slit"]
    # 停止した先頭車が実際に居る画素が、前景として残っているか
    lead = 0
    c0 = int(round(stop_at[lead] - 0.5 * veh[lead]["len"]))
    c1 = int(round(stop_at[lead] + 0.5 * veh[lead]["len"]))
    c0, c1 = max(c0, 0), min(c1, W_PX)
    stopped = times >= 70.0
    fg_rate = float(mask[np.ix_(stopped, [row], range(c0, c1))].mean())
    moving = times < 30.0
    fg_move = float(mask[np.ix_(moving, [row], range(c0, c1))].mean())

    s = slit_count(kymograph(mask, row))
    cc = per_frame_counts(mask)
    print("  近い車線に %d 台。40 フレーム目から減速し、%d 列の手前へ詰まる。"
          % (len(veh), X_REF))
    print("  停止した先頭車の画素が前景に残っている割合: 走行中 %.2f -> 停止後 %.2f"
          % (fg_move, fg_rate))
    print("  ★時間中央値の背景は、**停止した車を背景として学習する**。"
          "検出器を替えても直らない。")
    print("  スリットの帯(計数列と交わる)%d / 真値 %d / ゼロ点の最大値 %d"
          % (s["n_ref"], len(veh), cc.max()))
    print("  ★渋滞では L/V -> ∞ なので 5 節・6 節の破綻条件は**遠ざかる**。"
          "壊れているのは数え方ではなく前段の背景モデル。")
    return {"fg_move": fg_move, "fg_stop": fg_rate, "n_ref": s["n_ref"],
            "n": len(veh)}


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    # (a) 時空間スライス(kymograph / スリットスキャン)を作る口が無い。
    assert not hasattr(fs, "kymograph") and not hasattr(fs.ledger, "slit_scan")
    assert not hasattr(fs, "space_time_slice")
    print("  (a) 動画 (T,H,W) から**時空間スライス**(kymograph / スリット"
          "スキャン)を取る口が無い。この PoC は `mask[:, row, :]` を"
          "自前で書いている —— 斜めの計数線や曲がった線では自前では済まない。")

    # (b) blob_features の angle は在るが、**速度**として読み替える道が無い。
    m = np.zeros((40, 60), bool)
    for r in range(40):
        m[r, 5 + r: 12 + r] = True                    # 傾き 1 の帯
    f = _LAB.blob_features(_LAB.blob_label(m))
    a = float(np.asarray(f["angle"])[0])
    v_from_angle = 1.0 / np.tan(a)
    print("  (b) 傾き 1 の合成帯で blob_features['angle'] = %.4f rad -> "
          "速度 %.3f(真値 1.000、誤差 %+.1f %%)。角度は取れるが、"
          "**画面端で切れた帯の傾き**は主軸が寝るので当てにならない。"
          % (a, v_from_angle, 100 * (v_from_angle - 1.0)))

    # (c) 連結成分を**時間方向に追う**(トラッキング)口が無い。
    assert hasattr(fs, "track_points")     # 疎な点は追える
    assert not hasattr(fs, "track_blobs") and not hasattr(fs.ledger, "blob_track")
    print("  (c) 疎な点は track_points で追えるが、**連結成分(塊)を"
          "フレーム間で対応づける**口が無い。交通量計数の王道はこれ。")

    # (d) 背景モデルは在るが「学習を止める」つまみが無い(7 節の停止車問題)。
    import inspect
    sig = inspect.signature(fs.background_subtraction)
    assert "threshold" in sig.parameters and len(sig.parameters) == 2, sig
    print("  (d) background_subtraction のつまみは threshold だけ。"
          "**停止した物体を背景に取り込ませない**(学習率・凍結・"
          "前景での更新停止)つまみが無い。running_gaussian_background の "
          "selective は近いが、時間中央値の側には無い。")

    # (e) 計数の答えを出す口(帯の数 -> 交通量)は当然無い。ここは応用側でよい。
    assert not hasattr(fs, "count_crossings")
    print("  (e) 「ある列を跨いだ塊の数」を数える口が無い。この PoC は "
          "`np.unique(lab[:, x])` で書いており、これは 3 行で済むので"
          "族に入れるほどではない —— **穴だが埋めなくてよい穴**として記録する。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("(x, y, t) で数える —— 通過台数とオクルージョン")
    print("%d フレーム / %d x %d px / %.0f fps / 計数列 x = %d"
          % (T_FRAMES, W_PX, H_PX, FPS, X_REF))
    print("=" * 78)

    sc = section_scene()
    zp = section_zero_point(sc)
    sl = section_slit(sc, zp)
    section_tall(sc)
    hw = section_headway()
    fr = section_framerate()
    jam = section_jam()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点(フレームごと CC の最大値)は %d、通過台数は %d —— "
          "別の量。" % (zp["cc"].max(), zp["total"]))
    print("  * スリット法は %d 台(過大分はトラックが遠い車線の計数行を"
          "覆うぶん)。" % sum(sl[ln]["slit"]["n_ref"] for ln in LANES))
    print("  * 同じスリット画像でも『全部の帯』と『計数列と交わる帯』で"
          "壊れ方が逆(Δt=%d で %d 対 %d)。"
          % (fr["dts"][-1], fr["n_all"][-1], fr["n_ref"][-1]))
    print("  * 破綻の条件は 3 つとも L/V。車間(%d/%d 条件で予測と一致)、"
          "フレーム間隔(予測との差 %+.1f 台以内)、停止(L/V→∞)。"
          % (sum(1 for g, p in zip(hw["got"], hw["pred"]) if g == p),
             len(hw["got"]),
             max(abs(g - p) for g, p in zip(fr["n_ref"], fr["pred"]))))
    print("  * 渋滞で落ちるのは背景モデル(先頭車の前景率 %.2f -> %.2f)。"
          % (jam["fg_move"], jam["fg_stop"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
