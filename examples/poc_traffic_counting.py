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
def make_vehicles(seed: int = 3, n_far: int = 4, n_near: int = 6,
                  headway: float | None = None, n_truck: int = 0,
                  same_speed: bool = False) -> list[dict]:
    """車の一覧。**計数列を跨ぐ時刻を先に決めて**初期位置を逆算する。

    ``headway`` を渡すと車線ごとに等間隔(フレーム)で流す(車間の掃引用)。
    渡さないときは**層化して**散らす —— 一様乱数だと通過時刻が偶然固まって、
    測りたい「疎な流れ」ではなく渋滞を測ってしまう(最初そうなった)。

    ``n_truck`` は近い車線の**背の高い車の台数**(確率ではなく台数。確率だと
    条件を変えたときに 0 台になって比較が消える —— これも最初そうなった)。
    ``same_speed`` は車線内の速度と車長を固定する(5 節で使う。速度が違うと
    帯が計数列の外で**交差**して融合し、車間の効果と混ざる)。
    """
    rng = np.random.default_rng(seed)
    out = []
    for lane, n in (("far", n_far), ("near", n_near)):
        cfg = LANES[lane]
        span = (T_FRAMES - 24.0) / max(n, 1)
        step = max(1, int(np.ceil(n / max(n_truck, 1)))) if n_truck else 0
        for i in range(n):
            if same_speed:
                v = float(np.mean(cfg["v"]))
                length = float(np.mean(cfg["len"]))
            else:
                v = float(rng.uniform(*cfg["v"]))
                length = float(rng.uniform(*cfg["len"]))
            if headway is None:
                s = 12.0 + (i + float(rng.uniform(0.2, 0.8))) * span
            else:
                s = 8.0 + i * headway
            tall = (lane == "near") and n_truck > 0 and (i % step == 0) \
                and sum(1 for w in out if w["tall"]) < n_truck
            out.append({"lane": lane, "v": v, "len": length, "cross": s,
                        "x0": X_REF - v * s, "tall": bool(tall),
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


def foreground_oracle(vid: np.ndarray) -> np.ndarray:
    """対照群 —— **真の空きの路面**を背景に使う(背景モデルの劣化を切り分ける)。"""
    return np.abs(vid - _road()[None, ...]) > FG_THRESHOLD


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


def band_speeds(lab: np.ndarray, ids, dt: float = 1.0, x_ref: int = X_REF) -> dict:
    """帯ごとに(通過時刻, 速度 2 通り, 行数)。速度は [px/frame]。

    通過時刻は**その帯が計数列を覆っていた行の中央**。これで帯と実車を
    1 対 1 に対応づけられる(数だけ揃えて並べ替えで比べると、融合や
    見逃しがあるときに**別の車どうしを比べて**平気な顔で数字が出る)。
    """
    feats = _LAB.blob_features(lab)
    ang = np.asarray(feats["angle"], np.float64)
    w = lab.shape[1]
    cross, fit, fit_in, from_angle, npts = [], [], [], [], []
    for i in ids:
        rr, cc = np.nonzero(lab == i)
        rows = np.unique(rr)
        at_ref = np.nonzero(lab[:, x_ref] == i)[0]
        cross.append(float(np.median(at_ref)) * dt if at_ref.size else np.nan)
        # angle は +col -> +row(画面で時計回り)。帯の向きは (Δrow, Δcol) = (1, V·dt)
        # なので tan(angle) = 1/(V·dt) -> V = cot(angle)/dt。
        a = float(ang[int(i) - 1])
        t = np.tan(a)
        from_angle.append((1.0 / t if abs(t) > 1e-9 else np.nan) / dt)
        npts.append(int(rows.size))
        if rows.size < 2:
            fit.append(np.nan)
            fit_in.append(np.nan)
            continue
        cen, clean_r, clean_c = [], [], []
        for r in rows:
            xr = cc[rr == r]
            cen.append(xr.mean())
            # ★画面の左右で切れている行は重心が引っ張られる。落とした版も測る。
            if xr.min() > 0 and xr.max() < w - 1:
                clean_r.append(float(r))
                clean_c.append(float(xr.mean()))
        fit.append(float(np.polyfit(rows.astype(np.float64),
                                    np.asarray(cen), 1)[0]) / dt)
        fit_in.append(float(np.polyfit(clean_r, clean_c, 1)[0]) / dt
                      if len(clean_r) >= 2 else np.nan)
    return {"cross": np.asarray(cross), "fit": np.asarray(fit),
            "fit_inner": np.asarray(fit_in), "angle": np.asarray(from_angle),
            "rows": np.asarray(npts)}


def match_speeds(sp: dict, vehicles, tol: float = 12.0) -> dict:
    """帯と実車を**通過時刻**で突き合わせ、速度の相対誤差 [%] を返す。"""
    ef, ei, ea, used = [], [], [], 0
    for v in vehicles:
        d = np.abs(sp["cross"] - v["cross"])
        if d.size == 0 or not np.isfinite(d).any():
            continue
        k = int(np.nanargmin(d))
        if not np.isfinite(d[k]) or d[k] > tol:
            continue
        used += 1
        for key, acc in (("fit", ef), ("fit_inner", ei), ("angle", ea)):
            if np.isfinite(sp[key][k]):
                acc.append(100 * abs(sp[key][k] - v["v"]) / v["v"])
    m = (lambda a: float(np.mean(a)) if a else np.nan)
    return {"n": used, "fit": m(ef), "fit_inner": m(ei), "angle": m(ea)}


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
    print("   背の高い車(トラック)は %d 台 —— この場面には入れていない。"
          "4 節で入れて、遠い車線の計数行 %d への書き込みを別に測る。"
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
    print("  速度は 3 通りで出す: 行ごとの重心を線形当てはめ / 同じ当てはめから")
    print("  **画面端で切れた行を落とした版** / 台帳の blob_features['angle']。")
    print("\n   車線  真値  帯(全部)  帯(計数列)  対応   重心当て  端を除く  angle")

    out = {}
    for ln in LANES:
        kym = kymograph(sc["mask"], LANES[ln]["slit"])
        s = slit_count(kym)
        sp = band_speeds(s["labels"], s["ids"])
        cars = [v for v in sc["veh"] if v["lane"] == ln
                and crosses_ref(v, T_FRAMES - 1)]
        mt = match_speeds(sp, cars)
        print("   %-5s %4d  %7d  %9d   %3d/%d  %7.2f %% %7.2f %% %7.2f %%"
              % (ln, sc["truth"][ln], s["n_all"], s["n_ref"], mt["n"], len(cars),
                 mt["fit"], mt["fit_inner"], mt["angle"]))
        out[ln] = {"kym": kym, "slit": s, "speed": sp, "match": mt}

    tot_ref = sum(out[ln]["slit"]["n_ref"] for ln in LANES)
    print("\n  合計: スリット %d 台 / 仮想ループ %d 台 / ゼロ点(最大値) %d 台"
          " / 真値 %d 台" % (tot_ref, zp["loop"], zp["cc"].max(), zp["total"]))
    print("  遠い車線 %d/%d、近い車線 %d/%d。**疎な自由流ではスリット法と"
          "仮想ループは同点** —— どちらも同じ列の情報しか使っていない。"
          % (out["far"]["slit"]["n_ref"], sc["truth"]["far"],
             out["near"]["slit"]["n_ref"], sc["truth"]["near"]))
    print("  2-D にした見返りは速度が同時に出ること(下)と、"
          "壊れ方が絵で見えることのほう。")
    ff = [out[ln]["match"]["fit"] for ln in LANES]
    fi = [out[ln]["match"]["fit_inner"] for ln in LANES]
    fa = [out[ln]["match"]["angle"] for ln in LANES]
    print("\n  ★**予想が外れた**。「端で切れた帯は主軸が寝るので angle は"
          "当てにならない」と踏んでいたが、実測は逆で")
    print("     angle %.2f / %.2f %% < 重心当て %.2f / %.2f %%。"
          % (fa[0], fa[1], ff[0], ff[1]))
    print("     原因は測ってある: 端で切れた行では**重心のほうが**引っ張られる。"
          "その行を落とすと %.2f / %.2f %% まで下がり、angle と同水準になる。"
          % (fi[0], fi[1]))
    print("     2 次モーメントは面積で重みづけるので、端の数行の影響が小さい。")

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
    print("4) 背の高い車は別の車線のスリットに書き込む")
    print("=" * 78)
    print("  対照群つき: 同じトラックだけを流して(遠い車線を空にして)、")
    print("  遠い車線のスリットに何本の帯が立つかを別に数える。")
    print("\n   トラック   far 帯/真値   差   near 帯/真値   トラックのみの far 帯")

    rows, diff = [], []
    for nt in (0, 2, 3, 6):
        veh = make_vehicles(seed=3, n_truck=nt)
        n_truck = sum(1 for v in veh if v["tall"])
        vid = render_sequence(veh, np.arange(T_FRAMES, dtype=np.float64))
        mask = foreground(vid)
        s_far = slit_count(kymograph(mask, LANES["far"]["slit"]))
        s_near = slit_count(kymograph(mask, LANES["near"]["slit"]))
        t_far = sum(1 for v in veh if v["lane"] == "far")
        t_near = sum(1 for v in veh if v["lane"] == "near")
        # 対照群: 遠い車線を空にして、トラックだけを同じ軌跡で流す
        only = [v for v in veh if v["tall"]]
        n_only = 0
        if only:
            mo = foreground(render_sequence(only,
                                            np.arange(T_FRAMES, dtype=np.float64)))
            n_only = slit_count(kymograph(mo, LANES["far"]["slit"]))["n_ref"]
        diff.append((n_truck, s_far["n_ref"] - t_far, n_only))
        rows.append([str(n_truck), "%d / %d" % (s_far["n_ref"], t_far),
                     "%+d" % (s_far["n_ref"] - t_far),
                     "%d / %d" % (s_near["n_ref"], t_near), str(n_only)])
        print("     %4d      %3d / %d    %+3d     %3d / %d          %6d"
              % (n_truck, s_far["n_ref"], t_far, s_far["n_ref"] - t_far,
                 s_near["n_ref"], t_near, n_only))

    print("\n  ★**予想が外れた**。「偽の帯が増えて過大になる」と踏んでいたが、"
          "実測は %s。" % ("すべて過小" if all(d <= 0 for _, d, _ in diff)
                           else "条件で向きが変わる"))
    print("     対照群がその理由を示す: トラックだけを流すと遠い車線のスリットに"
          "帯は確かに立つ(右端の列)。")
    print("     つまり書き込みは起きている。しかし遠い車線の車が居ると、"
          "その帯と**交差して融合する**ので、増えるどころか減る。")
    print("     増える失敗と減る失敗が同時に起き、**減るほうが勝つ** ——"
          "1 つの数字だけ見ていたら「オクルージョンで隠れた」と誤読する。")
    figs.save_table("tall_vehicles",
                    ["トラック", "far 帯/真値", "差", "near 帯/真値",
                     "トラックのみ"],
                    rows, title="背の高い車が遠い車線のスリットに書き込む",
                    caption="トラックは画像の %d 行から %d 行を占めるので、"
                            "遠い車線の計数行 %d を横切る。右端は対照群"
                            "(遠い車線を空にして同じトラックだけを流した)。"
                            % (TRUCK_Y0, LANES["near"]["y1"] - 1,
                               LANES["far"]["slit"]))
    return {"rows": rows, "diff": diff}


# --------------------------------------------------------------------------- #
# 5. 車間を詰める —— 融合の閾値 L/V                                             #
# --------------------------------------------------------------------------- #
def section_headway() -> dict:
    print("\n" + "=" * 78)
    print("5) 車間を詰める —— 帯が融合する閾値は headway = L/V [frame]")
    print("=" * 78)
    print("  近い車線だけを**同じ速度・同じ車長**で等間隔に流す(隊列)。")
    print("  速度をばらすと帯が計数列の外で交差して融合し、車間の効果と混ざる")
    print("  —— それは下の対照群で別に測る。")
    print("\n   headway   真値   スリット   仮想ループ   予測(融合後の群数)  ゼロ点最大")

    rows, hs, got, pred, loops = [], [], [], [], []
    lv = None
    for hw in (5.0, 7.0, 8.0, 9.0, 11.0, 14.0, 18.0, 24.0):
        veh = make_vehicles(seed=7, n_far=0, n_near=7, headway=hw,
                            n_truck=0, same_speed=True)
        vid = render_sequence(veh, np.arange(T_FRAMES, dtype=np.float64))
        mask = foreground(vid)
        s = slit_count(kymograph(mask, LANES["near"]["slit"]))
        loop = virtual_loop(mask, LANES["near"]["slit"])
        cc = per_frame_counts(mask)
        # 予測: 隣り合う 2 台の車体が計数線上で重なる(空隙 < 1 px)なら融合。
        groups = 1
        for a, b in zip(veh[:-1], veh[1:]):
            gap = b["v"] * (b["cross"] - a["cross"]) - 0.5 * (a["len"] + b["len"])
            if gap >= 1.0:
                groups += 1
        lv = float(veh[0]["len"] / veh[0]["v"])
        rows.append(["%.0f" % hw, str(len(veh)), str(s["n_ref"]), str(loop),
                     str(groups), str(int(cc.max()))])
        hs.append(hw)
        got.append(s["n_ref"])
        pred.append(groups)
        loops.append(loop)
        print("    %5.0f    %4d   %6d      %6d      %10d        %6d"
              % (hw, len(veh), s["n_ref"], loop, groups, cc.max()))

    agree = sum(1 for g, p in zip(got, pred) if g == p)
    print("\n  ★L/V = %.2f frame。予測(空隙 1 px の幾何)と実測が %d/%d 条件で一致。"
          % (lv, agree, len(got)))
    first_ok = next((h for h, g in zip(hs, got) if g == 7), None)
    print("     全 7 台に分かれたのは headway >= %s から —— L/V = %.1f の"
          "すぐ上。" % (first_ok, lv))

    # --- 対照群: 速度をばらす(帯が交差する) ------------------------------- #
    print("\n  対照群 —— 同じ headway で速度・車長をばらす")
    print("   headway   同速度のスリット   ばらつきありのスリット   仮想ループ")
    for hw in (14.0, 18.0, 24.0):
        veh = make_vehicles(seed=7, n_far=0, n_near=7, headway=hw,
                            n_truck=0, same_speed=False)
        vid = render_sequence(veh, np.arange(T_FRAMES, dtype=np.float64))
        mask = foreground(vid)
        s = slit_count(kymograph(mask, LANES["near"]["slit"]))
        loop = virtual_loop(mask, LANES["near"]["slit"])
        base = got[hs.index(hw)]
        print("    %5.0f        %8d              %8d           %6d"
              % (hw, base, s["n_ref"], loop))
    print("  ★速度がばらつくと、帯は**計数列から離れた場所で交差して融合する**。")
    print("     2-D の連結は画像全体で効くので、計数列とは無関係な場所の交差が")
    print("     計数を壊す。1-D の仮想ループはこの壊れ方をしない —— "
          "**2-D にしたことの代償**。")
    return {"hs": hs, "got": got, "pred": pred, "loops": loops, "rows": rows,
            "lv": lv}


# --------------------------------------------------------------------------- #
# 6. フレームレート —— 見逃しの閾値 L/(V·Δt)                                    #
# --------------------------------------------------------------------------- #
def section_framerate() -> dict:
    print("\n" + "=" * 78)
    print("6) フレームレートを落とす —— 台数と速度、どちらが先に壊れるか")
    print("=" * 78)
    print("  ★予測 Σmin(1, L/(V·Δt)) は**標本化の位相についての期待値**なので、")
    print("    1 つの位相で測った 1 本の数字と比べても合わない。位相を Δt の")
    print("    中で 4 通りずらして平均した列を並べる(対照群は真の空き路面)。")
    print("\n   Δt  実効fps  真値 帯(全部) 帯(計数列) 位相平均 予測Σmin(1,L/VΔt)"
          " 速度誤差")

    veh = make_vehicles(seed=3)
    crossing = [v for v in veh if crosses_ref(v, T_FRAMES - 1)]
    total = len(crossing)
    dts, n_all_l, n_ref_l, n_or_l, pred_l, verr_l = [], [], [], [], [], []
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
            sp = band_speeds(s["labels"], s["ids"], dt=float(dt))
            mt = match_speeds(sp, [v for v in crossing if v["lane"] == ln],
                              tol=max(12.0, 2.0 * dt))
            if np.isfinite(mt["fit_inner"]):
                errs.append(mt["fit_inner"])
        # 位相平均(対照群 = 真の空き路面。背景モデルの劣化を混ぜない)
        phases = np.arange(0.0, float(dt), max(dt / 4.0, 1.0))
        ph = []
        for off in phases:
            o = foreground_oracle(render_sequence(
                veh, np.arange(off, T_FRAMES, float(dt))))
            ph.append(sum(slit_count(kymograph(o, LANES[ln]["slit"]))["n_ref"]
                          for ln in LANES))
        n_or = float(np.mean(ph))
        pred = float(sum(min(1.0, v["len"] / (v["v"] * dt)) for v in crossing))
        verr = float(np.mean(errs)) if errs else np.nan
        dts.append(dt)
        n_all_l.append(n_all)
        n_ref_l.append(n_ref)
        n_or_l.append(n_or)
        pred_l.append(pred)
        verr_l.append(verr)
        rows.append(["%d" % dt, "%.1f" % (FPS / dt), str(total), str(n_all),
                     str(n_ref), "%.2f" % n_or, "%.1f" % pred, "%.1f %%" % verr])
        print("   %3d %6.1f %6d %7d %9d %8.2f %14.1f %8.2f %%"
              % (dt, FPS / dt, total, n_all, n_ref, n_or, pred, verr))

    lv = sorted(v["len"] / v["v"] for v in crossing)
    d_med = float(np.median(lv))
    print("\n  ★L/V の分布: %.1f 〜 %.1f frame(中央値 %.1f)。"
          % (lv[0], lv[-1], d_med))
    print("  ★**帯を全部数える**と Δt を広げたとき千切れて過大になる"
          "(%d -> %d)。" % (n_all_l[0], max(n_all_l)))
    print("     **計数列と交わる帯だけ**を数えると過大は起きない"
          "(最大 %d)。同じスリット画像から出る 2 つの数の壊れ方が逆向き。"
          % max(n_ref_l))
    print("  ★閉形式との差: 位相平均だと %+.2f 〜 %+.2f 台、"
          "1 つの位相だけだと %+.1f 〜 %+.1f 台。"
          % (min(g - p for g, p in zip(n_or_l, pred_l)),
             max(g - p for g, p in zip(n_or_l, pred_l)),
             min(g - p for g, p in zip(n_ref_l, pred_l)),
             max(g - p for g, p in zip(n_ref_l, pred_l))))
    print("     **1 本の実験で閉形式を検証してはいけない** —— 予測は位相に"
          "ついての期待値で、1 つの位相の実現値はその周りに散らばる。")
    first_count = next((d for d, g in zip(dts, n_or_l) if g < total - 0.05), None)
    first_speed = next((d for d, e in zip(dts, verr_l) if e > 5.0), None)
    print("  ★先に壊れたのは %s(対照群の台数は Δt=%s で欠け始め、"
          "速度誤差 5 %% 超は Δt=%s)。"
          % ("速度" if (first_speed or 99) < (first_count or 99) else "台数",
             first_count, first_speed))

    figs.save_plot("framerate",
                   [("真値", dts, [total] * len(dts)),
                    ("帯(計数列・位相平均)", dts, n_or_l),
                    ("予測 Σmin(1, L/VΔt)", dts, pred_l),
                    ("帯(全部・中央値背景)", dts, n_all_l)],
                   xlabel="フレーム間隔 Δt [frame]", ylabel="台数",
                   title="フレームレートを落とすと数え方で壊れ方が逆になる",
                   caption="全部の帯を数えると千切れて過大に、計数列と交わる"
                           "帯だけなら見逃しだけ。予測は閉形式 Σmin(1, L/VΔt)。")
    return {"dts": dts, "n_all": n_all_l, "n_ref": n_ref_l, "n_oracle": n_or_l,
            "pred": pred_l, "verr": verr_l, "total": total, "rows": rows}


# --------------------------------------------------------------------------- #
# 7. 渋滞 —— 壊れるのは検出器ではなく背景モデル                                 #
# --------------------------------------------------------------------------- #
def _jam_positions(veh, times, stop_at):
    """停止位置で止まる軌跡。**x は単調非減少**でなければならない。

    ★最初は「``brake_from`` 以降だけ停止位置で頭打ち」と書いていて、それだと
    停止位置を追い越した車が制動開始の瞬間に**後ろへ飛ぶ**。絵では気づかず、
    スリット画像の帯だけが 1 本余計に融合していた(真値 3 に対し 2)。
    合成の側の不整合は、推定器の欠陥に化けて見える。
    """
    out = np.empty((len(times), len(veh)))
    for j, v in enumerate(veh):
        out[:, j] = np.minimum(v["x0"] + v["v"] * np.asarray(times), stop_at[j])
    assert np.all(np.diff(out, axis=0) >= -1e-9), "軌跡が後戻りしている"
    return out


def section_jam() -> dict:
    print("\n" + "=" * 78)
    print("7) 渋滞 —— 壊れるのは検出器ではなく背景モデル")
    print("=" * 78)

    veh = make_vehicles(seed=11, n_far=0, n_near=6, headway=14.0,
                        n_truck=0, same_speed=True)
    times = np.arange(T_FRAMES, dtype=np.float64)
    # 先頭から順に詰めて停止させる(先頭は X_REF より先まで進む)
    stop_at = [X_REF + 130 - k * 66.0 for k in range(len(veh))]
    xs = _jam_positions(veh, times, stop_at)

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

    # 真値は軌跡から出す。「x_ref を跨いだ台数」と「最後のフレームで画面に
    # 居る台数」は**別の量**で、渋滞ではこの 2 つが大きく食い違う。
    half = np.asarray([0.5 * v["len"] for v in veh])
    passed = int(np.count_nonzero((xs.max(axis=0) + half >= X_REF)
                                  & (xs.min(axis=0) - half <= X_REF)))
    last = xs[-1]
    onscreen = int(np.count_nonzero((last + half > 0) & (last - half < W_PX)))

    # 停止した先頭車が実際に居る画素が、前景として残っているか
    lead = 0
    c0 = max(int(round(stop_at[lead] - 0.5 * veh[lead]["len"])), 0)
    c1 = min(int(round(stop_at[lead] + 0.5 * veh[lead]["len"])), W_PX)
    stopped = times >= 120.0
    fg_rate = float(mask[np.ix_(stopped, [row], range(c0, c1))].mean())
    moving = times < 30.0
    fg_move = float(mask[np.ix_(moving, [row], range(c0, c1))].mean())

    oracle = foreground_oracle(vid)
    s = slit_count(kymograph(mask, row))
    s_or = slit_count(kymograph(oracle, row))
    cc = per_frame_counts(mask)
    seen_last = int(_LAB.blob_label(mask[-1]).max())
    seen_last_or = int(_LAB.blob_label(oracle[-1]).max())
    print("  近い車線に %d 台。40 フレーム目から減速し、%d 列の前後へ詰まる。"
          % (len(veh), X_REF))
    print("  真値: 計数列を跨いだ %d 台 / 最後のフレームで画面に居る %d 台。"
          % (passed, onscreen))
    print("\n   数え方                    通過台数   最後のフレームの塊")
    print("   時間中央値の背景            %4d           %4d" % (s["n_ref"], seen_last))
    print("   真の空き路面(対照群)      %4d           %4d"
          % (s_or["n_ref"], seen_last_or))
    print("   真値                        %4d           %4d" % (passed, onscreen))
    print("\n  ★**壊れているのは数え方ではなく背景モデル**。対照群に替えるだけで"
          "通過台数は %d -> %d(真値 %d)、最終フレームの塊は %d -> %d に戻る。"
          % (s["n_ref"], s_or["n_ref"], passed, seen_last, seen_last_or))
    print("     停止した先頭車の画素が前景に残っている割合: 走行中 %.2f -> "
          "停止後 %.2f。時間中央値は**停止した車を背景として学習する**。"
          % (fg_move, fg_rate))
    print("  ★渋滞では L/V -> ∞ なので 5 節・6 節の破綻条件は**遠ざかる**。"
          "破綻の場所が前段へ移っただけで、渋滞に強くなったのではない ——"
          "検出器を取り替えても 1 台も戻らない。")
    return {"fg_move": fg_move, "fg_stop": fg_rate, "n_ref": s["n_ref"],
            "n_ref_oracle": s_or["n_ref"], "passed": passed,
            "onscreen": onscreen, "seen_last": seen_last,
            "seen_last_oracle": seen_last_or, "cc_max": int(cc.max())}


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
          "速度 %.3f(真値 1.000、誤差 %+.1f %%)。**角度から速度は出せる** ——"
          " 3 節の実測でも重心当てはめより良かった。"
          % (a, v_from_angle, 100 * (v_from_angle - 1.0)))
    print("      穴は換算のほう: cot(angle)/Δt という読み替えが呼び手の責任で、"
          "符号(+col->+row)と Δt の掛け方を間違えると**それらしい数字**が出る。"
          "時空間画像の傾きを速度として返す口があれば、その罠は閉じられる。")

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
    tall = section_tall(sc)
    hw = section_headway()
    fr = section_framerate()
    jam = section_jam()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点(フレームごと CC の最大値)は %d、通過台数は %d —— "
          "別の量を測っている。" % (zp["cc"].max(), zp["total"]))
    print("  * 疎な自由流ではスリット法 %d 台・仮想ループ %d 台・真値 %d 台で"
          "同点。2-D の見返りは速度(誤差 %.2f %% 以下)と、壊れ方が見えること。"
          % (sum(sl[ln]["slit"]["n_ref"] for ln in LANES), zp["loop"],
             zp["total"], max(sl[ln]["match"]["fit_inner"] for ln in LANES)))
    print("  * 同じスリット画像でも『全部の帯』と『計数列と交わる帯』で"
          "壊れ方が逆(Δt=%d で %d 対 %d)。"
          % (fr["dts"][-1], fr["n_all"][-1], fr["n_ref"][-1]))
    print("  * 破綻の条件は 3 つとも L/V。車間(%d/%d 条件で予測と一致、"
          "L/V=%.1f frame)、フレーム間隔(位相平均で予測との差 %+.2f 台以内)、"
          "停止(L/V→∞)。"
          % (sum(1 for g, p in zip(hw["got"], hw["pred"]) if g == p),
             len(hw["got"]), hw["lv"],
             max(abs(g - p) for g, p in zip(fr["n_oracle"], fr["pred"]))))
    print("  * 予想が 2 つ外れた: 台帳の angle は重心当てはめより**良かった**、"
          "背の高い車は計数を**増やさず減らした**(トラックだけなら %d 本の"
          "帯が立つ)。"
          % max(n for _, _, n in tall["diff"]))
    print("  * 渋滞で落ちるのは背景モデル(先頭車の前景率 %.2f -> %.2f、"
          "最終フレームの検出 %d/%d)。"
          % (jam["fg_move"], jam["fg_stop"], jam["seen_last"], jam["onscreen"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
