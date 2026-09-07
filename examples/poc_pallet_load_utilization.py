# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする。

(所見は実行後に転記する)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger

# --- パレットと規約 ---------------------------------------------------------- #
PW, PD = 1200.0, 1000.0      # パレットの平面寸法 [mm](ISO 1200x1000)
HMAX = 1800.0                # 積み付けの高さ制限 [mm](デッキ上面から)
V_ENV = PW * PD * HMAX       # 使える体積 [mm^3]

# --- 走査 -------------------------------------------------------------------- #
GS = 3.0                     # センサの標本間隔 [mm](真上から)
GC = 10.0                    # 高さマップのセル寸法 [mm](既定)
SIG_Z = 3.0                  # 測距の雑音 σ [mm]
H_FLOOR = 30.0               # この高さ以下は「デッキ」= 荷ではない [mm](10σ)
SCAN_X = (-200.0, 1400.0)    # 走査範囲(パレットより広く取る = はみ出しを見るため)
SCAN_Y = (-150.0, 1150.0)
SEED = 17

# --- 隙間の幅(崖の予測を突き合わせる相手)------------------------------------ #
SLOTS = (20.0, 50.0, 120.0)  # 上段の柱のあいだの隙間 [mm]

#: 荷 A —— 「隙間だらけ」。中段が上に架かるので**中の空洞は上から見えない**。
#: 直方体は (x0, y0, z0, x1, y1, z1) [mm]、重なりなし。
LOAD_A = [
    # 下段: 中央 400 x 400 x 420 mm を空けたリング(= 上から見えない空洞)
    (0.0, 0.0, 0.0, 400.0, 1000.0, 420.0),
    (800.0, 0.0, 0.0, 1200.0, 1000.0, 420.0),
    (400.0, 0.0, 0.0, 800.0, 300.0, 420.0),
    (400.0, 700.0, 0.0, 800.0, 1000.0, 420.0),
    # 中段: 全面のスラブ(空洞に架かる)
    (0.0, 0.0, 420.0, 1200.0, 1000.0, 820.0),
    # 上段: 幅の違う隙間を 3 本あける 4 本の柱
    (0.0, 0.0, 820.0, 300.0, 1000.0, 1180.0),
    (320.0, 0.0, 820.0, 600.0, 1000.0, 1180.0),      # 隙間 20 mm
    (650.0, 0.0, 820.0, 900.0, 1000.0, 1180.0),      # 隙間 50 mm
    (1020.0, 0.0, 820.0, 1200.0, 1000.0, 1180.0),    # 隙間 120 mm
]

#: 荷 B —— 「はみ出し」。中身は詰まっているが、下段が 90 mm 出て、
#: 一角が高さ制限 1800 mm を 100 mm 超える。中段の高さ ``H2`` は
#: **見かけの積載率が荷 A と一致するように閉形式で解いた**値。
OVERHANG = 90.0              # 下段の張り出し [mm](-x 側)
TOWER = (900.0, 300.0, 1200.0, 700.0)   # 突出する柱の平面範囲
TOWER_TOP = 1900.0           # その天端 [mm](制限を 100 mm 超える)


def solve_h2() -> float:
    """荷 B の中段の高さを、**見かけの積載率が荷 A と一致する**ように解く。

    上から見える体積は中段の高さ ``h2`` の 1 次式なので、連立でなく
    割り算 1 回で決まる。「同じ数字になる 2 つの荷」を偶然でなく
    **作れる**ことを示すのがこの PoC の主題なので、ここは閉形式で解く。
    """
    a_tower = (TOWER[2] - TOWER[0]) * (TOWER[3] - TOWER[1])
    a_flat = PW * PD - a_tower
    const = a_tower * TOWER_TOP + OVERHANG * PD * 500.0
    return (seen_volume(LOAD_A) - const) / a_flat


def load_b() -> list:
    """荷 B の直方体一覧(``solve_h2`` の答えを使う)。"""
    h2 = round(solve_h2(), 1)
    tx0, ty0, tx1, ty1 = TOWER
    return [
        (-OVERHANG, 0.0, 0.0, PW, PD, 500.0),          # 下段(-x 側へ張り出す)
        (0.0, 0.0, 500.0, PW, PD, h2),                 # 中段
        (tx0, ty0, h2, tx1, ty1, TOWER_TOP),           # 突出する柱
    ]


# --------------------------------------------------------------------------- #
# 真値 —— 積んだ箱そのもの                                                      #
# --------------------------------------------------------------------------- #
def box_volume(boxes) -> float:
    """箱の体積の合計 [mm^3](重なりが無い前提)。"""
    return float(sum((b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2]) for b in boxes))


def height_at(boxes, X, Y) -> np.ndarray:
    """平面位置 (X, Y) での荷の天端 [mm](荷が無ければ 0 = デッキ)。"""
    h = np.zeros(np.shape(X), float)
    for x0, y0, z0, x1, y1, z1 in boxes:
        m = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
        h = np.where(m, np.maximum(h, z1), h)
    return h


def solid_at(boxes, X, Y, Z) -> np.ndarray:
    """点 (X, Y, Z) が箱の中か。**中の空洞**を数えるのに要る。"""
    m = np.zeros(np.shape(X), bool)
    for x0, y0, z0, x1, y1, z1 in boxes:
        m |= ((X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
              & (Z >= z0) & (Z < z1))
    return m


def seen_volume(boxes, step: float = 5.0) -> float:
    """**上から見える**体積 [mm^3] = 天端マップを押し出した体積(真値側)。

    中の空洞は天端に現れないので、この量は箱の体積より必ず大きいか等しい。
    走査ではなく箱の一覧から積分するので、分解能の影響を受けない。
    """
    xs = np.arange(SCAN_X[0] + step / 2, SCAN_X[1], step)
    ys = np.arange(SCAN_Y[0] + step / 2, SCAN_Y[1], step)
    X, Y = np.meshgrid(xs, ys)
    return float(height_at(boxes, X, Y).sum() * step * step)


# --------------------------------------------------------------------------- #
# 走査(真上から)—— 見えるのは天端だけ                                        #
# --------------------------------------------------------------------------- #
def scan(boxes, gs: float = GS, sig: float = SIG_Z, seed: int = SEED) -> np.ndarray:
    """真上からの測距。**側面も内部も見えない**(天端の点だけ返る)。"""
    rng = np.random.default_rng(seed)
    xs = np.arange(SCAN_X[0] + gs / 2, SCAN_X[1], gs)
    ys = np.arange(SCAN_Y[0] + gs / 2, SCAN_Y[1], gs)
    X, Y = np.meshgrid(xs, ys)
    Z = height_at(boxes, X, Y) + rng.normal(0.0, sig, X.shape)
    return np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])


def height_map(pts: np.ndarray, gc: float = GC, offset: float = 0.0):
    """点群 → 高さマップ。**セルの中は最大値**(高さと はみ出しに安全側)。

    ★この規約は高さには安全側だが、**隙間には危険側**になる —— 幅 ``w`` の
    隙間は、セルが丸ごと隙間に収まったときしか床が見えない。それが §4 の崖。
    """
    x0 = SCAN_X[0] + offset
    y0 = SCAN_Y[0] + offset
    nx = int(np.ceil((SCAN_X[1] - x0) / gc))
    ny = int(np.ceil((SCAN_Y[1] - y0) / gc))
    ix = np.clip(((pts[:, 0] - x0) / gc).astype(int), 0, nx - 1)
    iy = np.clip(((pts[:, 1] - y0) / gc).astype(int), 0, ny - 1)
    k = iy * nx + ix
    hm = np.zeros(nx * ny)
    np.maximum.at(hm, k, pts[:, 2])
    seen = np.zeros(nx * ny, bool)
    seen[k] = True
    # ★デッキの点は雑音で +3σ まで浮くので、床のしきい値で切る。これを
    #   入れないと、はみ出しゼロの荷にも 0.006 m3 の「はみ出し」が出る。
    hm = np.where(seen & (hm > H_FLOOR), hm, 0.0).reshape(ny, nx)

    # セルとパレット外形の**重なり面積**(端のセルを丸ごと内 / 外にしない)
    cx0 = x0 + gc * np.arange(nx)
    cy0 = y0 + gc * np.arange(ny)
    ox = np.clip(np.minimum(cx0 + gc, PW) - np.maximum(cx0, 0.0), 0.0, gc)
    oy = np.clip(np.minimum(cy0 + gc, PD) - np.maximum(cy0, 0.0), 0.0, gc)
    inside = np.outer(oy, ox)
    return {"h": np.maximum(hm, 0.0), "inside": inside,
            "outside": gc * gc - inside, "gc": gc, "x0": x0, "y0": y0}


def account(hm: dict) -> dict:
    """高さマップ → **種類別**の体積 [mm^3]。1 つの数字に畳まない。"""
    h, ins, out = hm["h"], hm["inside"], hm["outside"]
    legal_h = np.minimum(h, HMAX)
    return {
        "total": float((h * (ins + out)).sum()),          # 見かけの積載体積
        "legal": float((legal_h * ins).sum()),            # 制限内・パレット上
        "overhang": float((h * out).sum()),               # はみ出し
        "over_height": float((np.maximum(h - HMAX, 0.0) * ins).sum()),
        "max_h": float(h.max()),
    }


# --------------------------------------------------------------------------- #
# 1. 場面 —— 上から見えるものと、見えないもの                                   #
# --------------------------------------------------------------------------- #
def _section_raster(boxes, y: float, nz: int = 120, nx: int = 180,
                    seen: bool = False) -> np.ndarray:
    """y = 一定の断面図(縦 z、横 x)。``seen=True`` は天端の押し出し。"""
    xs = np.linspace(SCAN_X[0], SCAN_X[1], nx)
    zs = np.linspace(0.0, HMAX + 200.0, nz)
    X, Z = np.meshgrid(xs, zs)
    Y = np.full_like(X, y)
    if seen:
        img = (Z < height_at(boxes, X, Y)).astype(float)
    else:
        img = solid_at(boxes, X, Y, Z).astype(float)
    return img[::-1]


def section_scene(lb: list) -> dict:
    print("\n" + "=" * 78)
    print("1) 場面 —— 真上からの走査で見えるのは天端だけ")
    print("=" * 78)

    for name, boxes in (("荷 A(隙間だらけ)", LOAD_A), ("荷 B(はみ出し)", lb)):
        vt, vs = box_volume(boxes), seen_volume(boxes)
        print("  %-18s 箱の体積 %.4f m3 / 上から見える体積 %.4f m3 "
              "-> 見えない空洞 %.4f m3 (%.2f %s)"
              % (name, vt / 1e9, vs / 1e9, (vs - vt) / 1e9,
                 100 * (vs - vt) / vs, "%"))

    ha = height_map(scan(LOAD_A))["h"]
    hb = height_map(scan(lb))["h"]
    figs.save_grid("scene", [ha, hb],
                   ["荷 A の高さマップ [mm]", "荷 B の高さマップ [mm]"],
                   title="真上から測った高さマップ(セル %.0f mm)" % GC, ncols=2)
    figs.save_grid("hidden_void_section",
                   [_section_raster(LOAD_A, 500.0),
                    _section_raster(LOAD_A, 500.0, seen=True)],
                   ["真の断面(y = 500 mm)", "上から見て押し出した断面"],
                   title="荷 A —— 中段が架かるので下の空洞は上から見えない",
                   ncols=2)
    return {"a": box_volume(LOAD_A), "b": box_volume(lb)}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— 外形から積載率を出す 3 通り                                      #
# --------------------------------------------------------------------------- #
def section_zero_points(lb: list) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 「荷を 1 個の外形とみなす」3 通りと、高さマップ")
    print("=" * 78)
    print("  荷の点(天端)+ **既知のパレット外形(z=0)** を 1 つの塊とみなす。"
          "\n  デッキを入れないと、外形は天端の起伏だけを囲む薄い板になる"
          "(実際に一度そうなった)。")
    print("\n   荷    やり方          体積 [m3]   積載率 [%s]   真値との差 [pt]" % "%")

    # 既知のパレットデッキ(4 隅、z = 0)。実機でも架台の位置は決まっている。
    deck = np.array([[0.0, 0.0, 0.0], [PW, 0.0, 0.0],
                     [0.0, PD, 0.0], [PW, PD, 0.0]])
    rows = []
    for name, boxes in (("A", LOAD_A), ("B", lb)):
        pts = scan(boxes)
        on = np.vstack([pts[pts[:, 2] > H_FLOOR], deck])
        lo, hi = L.aabb(on)
        v_aabb = float(np.prod(hi - lo))
        sub = np.vstack([on[::37], deck])     # 凸包は間引いてから(Qhull)
        V, F = L.convex_hull(sub)
        v_hull = abs(float(L.mesh_volume((V, F))))
        ob = L.obb(sub)
        v_obb = float(np.prod(2.0 * np.asarray(ob["extents"])))
        v_map = account(height_map(pts))["total"]
        v_true = box_volume(boxes)
        for how, v in (("外接直方体 AABB", v_aabb), ("凸包", v_hull),
                       ("主軸の箱 OBB", v_obb), ("高さマップ", v_map),
                       ("真値(箱の合計)", v_true)):
            u = 100 * v / V_ENV
            rows.append([name, how, "%.4f" % (v / 1e9), "%.2f" % u,
                         "%+.2f" % (u - 100 * v_true / V_ENV)])
            print("   %-4s  %-14s  %8.4f    %8.2f     %+8.2f" % (
                name, how, v / 1e9, u, u - 100 * v_true / V_ENV))
    print("\n  ★外形 3 通りはどれも**荷を 1 個の凸な塊とみなす**ので、"
          "隙間もはみ出しも\n     同じ向き(過大)に効く。荷 B の AABB は"
          "**積載率 100 %s を超える**\n     —— はみ出しと突出を体積として"
          "数え込んでしまうから。高さマップだけが\n     "
          "**上から見える形**を保つ(A +3.6 pt / B +0.5 pt)。" % "%")
    figs.save_table("zero_points", ["荷", "やり方", "体積 m3", "積載率 %",
                                    "真値との差 pt"], rows,
                    title="外形から出す積載率(高さ制限 %.0f mm を分母に)" % HMAX)
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 3. 同じ積載率、違う中身                                                       #
# --------------------------------------------------------------------------- #
def section_same_number(lb: list) -> dict:
    print("\n" + "=" * 78)
    print("3) ★★同じ積載率の 2 つの荷 —— 中身を種類別に分けて初めて分かれる")
    print("=" * 78)

    out = {}
    print("   荷   見かけの積載率   内訳: 実の箱 / 見えない空洞 / はみ出し / 高さ超過")
    for name, boxes in (("A", LOAD_A), ("B", lb)):
        pts = scan(boxes)
        acc = account(height_map(pts))
        v_true = box_volume(boxes)
        hidden = seen_volume(boxes) - v_true
        f = lambda v: 100 * v / V_ENV                        # noqa: E731
        out[name] = {"acc": acc, "true": v_true, "hidden": hidden}
        print("   %-3s   %8.2f %s      %6.2f / %6.2f / %6.2f / %6.2f  [%s of 使える体積]"
              % (name, f(acc["total"]), "%", f(v_true), f(hidden),
                 f(acc["overhang"]), f(acc["over_height"]), "%"))

    d = abs(out["A"]["acc"]["total"] - out["B"]["acc"]["total"]) / V_ENV * 100
    print("\n  ★見かけの積載率の差は **%.2f pt**(閉形式で一致させた)。"
          "同じ数字なのに:" % d)
    print("     荷 A は %.2f pt が**上から見えない空洞**で、はみ出しも高さ超過も無い。"
          % (100 * out["A"]["hidden"] / V_ENV))
    print("     荷 B は空洞ゼロだが、**はみ出し %.2f pt(%.0f mm 張り出し)**と"
          "\n     **高さ超過 %.2f pt(天端 %.0f mm / 制限 %.0f mm)**を含む。"
          % (100 * out["B"]["acc"]["overhang"] / V_ENV, OVERHANG,
             100 * out["B"]["acc"]["over_height"] / V_ENV,
             out["B"]["acc"]["max_h"], HMAX))
    print("  ★処置も逆: A は**積み方を変えれば載る**(空洞を埋める)。"
          "B は**降ろすしかない**。")

    # はみ出しを起こしている塊を数える(1 つの体積に畳まない)
    for name, boxes in (("A", LOAD_A), ("B", lb)):
        pts = scan(boxes)
        bad = pts[(pts[:, 2] > 20.0)
                  & ((pts[:, 0] < 0) | (pts[:, 0] > PW)
                     | (pts[:, 1] < 0) | (pts[:, 1] > PD))]
        n = 0
        if len(bad) >= 8:
            lab = L.euclidean_cluster(bad[::5], tol=40.0, min_size=20)
            n = int(lab.max()) + 1 if lab.size and lab.max() >= 0 else 0
        print("   荷 %s のはみ出し点 %6d 点 -> 塊 %d 個" % (name, len(bad), n))

    rows = []
    for name in ("A", "B"):
        o = out[name]
        rows.append([name, "%.2f" % (100 * o["acc"]["total"] / V_ENV),
                     "%.2f" % (100 * o["true"] / V_ENV),
                     "%.2f" % (100 * o["hidden"] / V_ENV),
                     "%.2f" % (100 * o["acc"]["overhang"] / V_ENV),
                     "%.2f" % (100 * o["acc"]["over_height"] / V_ENV),
                     "合格" if (o["acc"]["overhang"] + o["acc"]["over_height"])
                     < 1e6 else "不合格"])
    figs.save_table("breakdown",
                    ["荷", "見かけ %", "実の箱 %", "見えない空洞 %",
                     "はみ出し %", "高さ超過 %", "判定"], rows,
                    title="同じ見かけの積載率が、種類別では別物になる")
    return out


# --------------------------------------------------------------------------- #
# 4. 崖 —— 格子の刻みで隙間が消える                                             #
# --------------------------------------------------------------------------- #
def slot_recovered(pts: np.ndarray, gc: float, slot: tuple, offsets) -> float:
    """隙間 1 本の空所のうち、高さマップが**取り戻した体積の割合**(0〜1)。

    真の空所は ``w x 奥行 x 深さ``。高さマップから取り戻せる空所は
    ``Σ (天端 - h) x (セル ∩ 隙間の面積)``。セルの中は最大値なので、
    **セルが丸ごと隙間に収まったときだけ**床が見える —— 期待値は
    ``max(0, 1 - g/w)``。
    """
    x_lo, x_hi, floor_z, top_z = slot
    w = x_hi - x_lo
    true_void = w * PD * (top_z - floor_z)
    got = []
    for off in offsets:
        hm = height_map(pts, gc, off)
        ny, nx = hm["h"].shape
        cx0 = hm["x0"] + gc * np.arange(nx)
        cy0 = hm["y0"] + gc * np.arange(ny)
        ox = np.clip(np.minimum(cx0 + gc, x_hi) - np.maximum(cx0, x_lo), 0.0, gc)
        oy = np.clip(np.minimum(cy0 + gc, PD) - np.maximum(cy0, 0.0), 0.0, gc)
        depth = np.clip(top_z - hm["h"], 0.0, top_z - floor_z)
        got.append(float((depth * np.outer(oy, ox)).sum() / true_void))
    return float(np.mean(got))


def section_gsd_slots() -> dict:
    print("\n" + "=" * 78)
    print("4) ★崖 —— 格子の刻みが隙間の幅を超えると、隙間は消える")
    print("=" * 78)
    print("  最大値プーリングは**高さには安全側**だが、隙間には危険側。"
          "\n  幅 w の隙間はセルが丸ごと収まったときしか床が見えないので、"
          "\n  取り戻せる割合の予測は **max(0, 1 - g/w)**。")
    print("\n   セル g [mm]   隙間 20 mm(実測/予測)  50 mm(実測/予測)  "
          "120 mm(実測/予測)")

    pts = scan(LOAD_A)
    slot_x = ((300.0, 320.0), (600.0, 650.0), (900.0, 1020.0))
    offsets = np.linspace(0.0, 1.0, 5, endpoint=False)
    gcs, series = [], {w: ([], []) for w in SLOTS}
    for gc in (5.0, 10.0, 20.0, 40.0, 80.0, 160.0):
        gcs.append(gc)
        line = "   %8.0f    " % gc
        for w, (x_lo, x_hi) in zip(SLOTS, slot_x):
            rec = slot_recovered(pts, gc, (x_lo, x_hi, 820.0, 1180.0),
                                 offsets * gc)
            pred = max(0.0, 1.0 - gc / w)
            series[w][0].append(rec)
            series[w][1].append(pred)
            line += "  %5.2f / %5.2f   " % (rec, pred)
        print(line)

    err = max(abs(a - b) for w in SLOTS
              for a, b in zip(series[w][0], series[w][1]))
    print("\n  ★予測との差は最大 %.2f。**崖の位置は隙間の幅そのもの**"
          "(g = w で 0 になる)。" % err)
    print("     20 mm の隙間は g = 20 mm で既に見えない。40 mm のセルで測ると"
          "\n     **荷 A の隙間は 3 本中 1 本しか残らない**ので、"
          "積載率は隙間のぶんだけ高く出る。")

    figs.save_plot("gsd_slot_cliff",
                   [("w = 20 mm(実測)", gcs, series[20.0][0]),
                    ("w = 50 mm(実測)", gcs, series[50.0][0]),
                    ("w = 120 mm(実測)", gcs, series[120.0][0]),
                    ("予測 1 - g/w(w = 120 mm)", gcs, series[120.0][1])],
                   xlabel="高さマップのセル寸法 g [mm]",
                   ylabel="取り戻せた隙間の割合",
                   title="隙間は g = w で消える(崖の位置は幅そのもの)")

    frames, caps = [], []
    for gc in (5.0, 40.0, 160.0):
        frames.append(height_map(pts, gc)["h"])
        caps.append("g = %.0f mm" % gc)
    figs.save_grid("heightmap_frames", frames, caps,
                   title="セルを粗くすると隙間が埋まっていく(荷 A)", ncols=3)
    return {"gc": gcs, "series": series, "err": err}


# --------------------------------------------------------------------------- #
# 5. 逆向きの崖 —— 粗い格子は、出ていない荷に「はみ出し」を作る                 #
# --------------------------------------------------------------------------- #
def section_gsd_overhang(lb: list) -> dict:
    print("\n" + "=" * 78)
    print("5) ★★同じつまみが逆向きにも壊す —— 粗い格子は偽のはみ出しを作る")
    print("=" * 78)
    print("  荷 A は 1 mm もはみ出していない。境界をまたぐセルには荷の天端が"
          "\n  入るので、外側の面積ぶんが「はみ出し」に数えられる。"
          "\n  予測は **周長 P x g/2 x 天端 h**(オフセットの平均)。")
    true_over = OVERHANG * PD * 500.0 / 1e9      # 荷 B の**真の**はみ出し [m3]
    print("\n   セル g [mm]   荷 A の偽はみ出し [m3](実測/予測)   "
          "荷 B の実測 [m3](真値 %.4f)" % true_over)

    pa, pb = scan(LOAD_A), scan(lb)
    peri = 2.0 * (PW + PD)
    h_edge = 1180.0
    gcs, meas, pred, real = [], [], [], []
    offsets = np.linspace(0.0, 1.0, 5, endpoint=False)
    for gc in (5.0, 10.0, 20.0, 40.0, 80.0, 160.0):
        va = float(np.mean([account(height_map(pa, gc, o * gc))["overhang"]
                            for o in offsets]))
        vb = float(np.mean([account(height_map(pb, gc, o * gc))["overhang"]
                            for o in offsets]))
        gcs.append(gc)
        meas.append(va / 1e9)
        pred.append(peri * gc / 2.0 * h_edge / 1e9)
        real.append(vb / 1e9)
        print("   %8.0f      %8.4f / %8.4f              %8.4f" % (
            gc, meas[-1], pred[-1], real[-1]))

    cross = [g for g, m in zip(gcs, meas) if m > true_over]
    print("\n  ★予測は実測を %.0f〜%.0f %s で追う(オフセット平均)。"
          % (100 * min(m / p for m, p in zip(meas, pred)),
             100 * max(m / p for m, p in zip(meas, pred)), "%"))
    if cross:
        print("  ★★g = %.0f mm から、**1 mm も出ていない荷 A の偽はみ出しが、"
              "\n     本当に %.0f mm 出ている荷 B の真のはみ出しを上回る**"
              "(%.4f > %.4f m3)。" % (
                  cross[0], OVERHANG, meas[gcs.index(cross[0])], true_over))
    print("  ★荷 B の実測も同じ偽の分を丸ごと含む(真値 %.4f に対し "
          "g = 160 mm で %.4f m3)。\n     **粗い格子では、どちらの荷も"
          "「はみ出している」で埋まる**。" % (true_over, real[-1]))
    print("  ★同じ 1 つのつまみ(セル寸法)が、**隙間は見えなくし、"
          "はみ出しは作る**。\n     どちらも「粗いほど積載率が良く見える」"
          "とは限らない —— 向きが逆。")

    figs.save_plot("gsd_false_overhang",
                   [("荷 A の偽はみ出し(実測)", gcs, meas),
                    ("予測 P x g/2 x h", gcs, pred),
                    ("荷 B の実測", gcs, real),
                    ("荷 B の真値 %.3f m3" % true_over, gcs,
                     [true_over] * len(gcs))],
                   xlabel="高さマップのセル寸法 g [mm]",
                   ylabel="はみ出し体積 [m3]",
                   title="粗い格子は、出ていない荷にはみ出しを作る")
    return {"gc": gcs, "meas": meas, "pred": pred, "real": real,
            "true_over": true_over}


# --------------------------------------------------------------------------- #
# 6. 一致度 1 個は種類別の内訳に盲目                                            #
# --------------------------------------------------------------------------- #
def _voxel(boxes, extruded: bool, nz=72, ny=40, nx=48) -> np.ndarray:
    """(z, y, x) の占有ボクセル。``extruded=True`` は天端の押し出し。"""
    zs = (np.arange(nz) + 0.5) * (HMAX / nz)
    ys = (np.arange(ny) + 0.5) * (PD / ny)
    xs = (np.arange(nx) + 0.5) * (PW / nx)
    X, Y = np.meshgrid(xs, ys)
    if extruded:
        h = height_at(boxes, X, Y)
        return zs[:, None, None] < h[None, :, :]
    Z = np.broadcast_to(zs[:, None, None], (nz, ny, nx))
    return solid_at(boxes, np.broadcast_to(X, (nz, ny, nx)),
                    np.broadcast_to(Y, (nz, ny, nx)), Z)


def section_iou(lb: list) -> dict:
    print("\n" + "=" * 78)
    print("6) 一致度を 1 個だけ見ると、この違いは**構造的に見えない**")
    print("=" * 78)

    out = {}
    for name, boxes in (("A", LOAD_A), ("B", lb)):
        iou = float(L.voxel_iou(_voxel(boxes, False).astype(float),
                                _voxel(boxes, True).astype(float)))
        out[name] = iou
        print("   荷 %s  真の中身 vs 上から押し出した形の IoU = %.4f" % (name, iou))
    print("\n  ★荷 A の IoU %.4f / 荷 B %.4f —— どちらも 0.9 台で、"
          "**「よく合っている」**\n     としか読めない。ところが A の"
          "食い違いは全部「中の空洞」で、\n     B は 0 —— 1 個の一致度は"
          "**何が違うか**を持っていない。")

    # 荷 A の自由空間に**あと 1 個入る最大の箱**(inner_box3、50 mm 格子)
    nz, ny, nx = 36, 20, 24
    free = ~_voxel(LOAD_A, True, nz, ny, nx)
    top = int(np.ceil(1180.0 / (HMAX / nz)))
    free_below = free.copy()
    free_below[top:] = False                # 天端より上(単なる余高)は除く
    got = {}
    for tag, vol in (("荷の中(天端より下)", free_below), ("制限まで全部", free)):
        try:
            ib = L.inner_box3(vol.astype(np.uint8))
            size = np.asarray(ib["size"]) * np.array([HMAX / nz, PD / ny, PW / nx])
            got[tag] = size
            print("   %-20s あと 1 個入る最大の箱 %.0f x %.0f x %.0f mm "
                  "(高さ x 奥行 x 幅)" % (tag, size[0], size[1], size[2]))
        except ValueError as exc:
            print("   %-20s 内接箱なし (%s)" % (tag, exc))

    figs.save_grid("free_space",
                   [_section_raster(LOAD_A, 500.0, seen=True),
                    _section_raster(lb, 500.0, seen=True)],
                   ["荷 A(隙間だらけ)", "荷 B(はみ出し・高さ超過)"],
                   title="断面 y = 500 mm —— 同じ積載率の 2 つの荷", ncols=2)
    return {"iou": out, "boxes": got}


# --------------------------------------------------------------------------- #
# 7. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 公開経路に無かった処理(この PoC が自前で書いたもの)")
    print("=" * 78)
    for name in ("height_map_from_points", "extruded_volume",
                 "footprint_excess", "packing_report"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (a) height_map_from_points(points, cell, reduce='max'|'min')"
          " —— 真上からの\n      点群を 2.5-D の高さマップにする。"
          "``occupancy_grid`` は 3-D の bool を返すが、\n      物流・"
          "デパレタイズ・建て入れは **2.5-D のほうが素直**(押し出し体積・"
          "\n      はみ出し・高さ超過が 1 枚の (H,W) から出る)。"
          "``reduce`` の選択が\n      §4/§5 の崖そのものなので、"
          "**規約を引数に出す**のが要点。")
    print("  (b) extruded_volume(height_map, cell) —— 高さマップの押し出し体積。"
          "\n      1 行だが、**セルとパレット外形の重なり面積**を扱わないと"
          "端で嘘になる\n      (この PoC は自前で clip している)。")
    print("  (c) footprint_excess(height_map, rect) —— 決められた外形から"
          "はみ出した\n      体積と最大張り出し。安全判定の基本量。")
    print("  (d) packing_report(...) —— 「見かけの積載率」を"
          "**実の箱 / 見えない空洞 /\n      はみ出し / 高さ超過**へ"
          "分解して返す層。個々の量は書けるが、"
          "\n      **1 つの数字に畳まない**という規約を道具側が持っていない。")
    print("  (e) inner_box3 は voxel 添字で返るので、mm へ戻すのに"
          "格子の刻みを\n      呼び手が持ち回る。物理単位を持った"
          "``bounds`` 付きの版が欲しい。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    lb = load_b()
    print("=" * 78)
    print("パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする")
    print("パレット %.0f x %.0f mm / 高さ制限 %.0f mm / 使える体積 %.3f m3"
          % (PW, PD, HMAX, V_ENV / 1e9))
    print("走査は真上から(標本間隔 %.0f mm、雑音 σ = %.0f mm)、"
          "高さマップのセル %.0f mm" % (GS, SIG_Z, GC))
    print("=" * 78)
    print("  荷 B の中段の高さは、見かけの積載率が荷 A と一致するよう"
          "閉形式で解いた: %.1f mm" % lb[1][5])

    section_scene(lb)
    section_zero_points(lb)
    same = section_same_number(lb)
    slots = section_gsd_slots()
    over = section_gsd_overhang(lb)
    iou = section_iou(lb)
    section_tool_gaps()

    # --- 所見を固定する assert -------------------------------------------- #
    # 1) 2 つの荷の「見かけの積載率」は 0.1 pt 以内で一致する(閉形式で作った)
    du = abs(same["A"]["acc"]["total"] - same["B"]["acc"]["total"]) / V_ENV * 100
    assert du < 0.10, du
    # 2) それでも中身は正反対 —— A は空洞だけ、B ははみ出しと高さ超過だけ
    assert same["A"]["hidden"] > 0.05 * same["A"]["true"]
    assert same["A"]["acc"]["overhang"] < 1e6 and same["A"]["acc"]["over_height"] < 1e3
    assert same["B"]["hidden"] < 1e6
    assert same["B"]["acc"]["overhang"] > 0.03 * same["B"]["true"]
    assert same["B"]["acc"]["over_height"] > 1e7
    # 3) 隙間の崖は max(0, 1 - g/w) で予測できる
    assert slots["err"] < 0.12, slots["err"]
    for w in SLOTS:
        i = slots["gc"].index(w) if w in slots["gc"] else None
        if i is not None:
            assert slots["series"][w][0][i] < 0.10, (w, slots["series"][w][0][i])
    # 4) 粗い格子は偽のはみ出しを作り、どこかで B の真のはみ出しを追い越す
    assert all(b >= a for a, b in zip(over["meas"], over["meas"][1:]))
    assert any(m > r for m, r in zip(over["meas"], over["real"]))
    assert all(0.5 < m / p < 1.5 for m, p in zip(over["meas"], over["pred"]))
    # 5) IoU は両方 0.9 台 —— 1 個の一致度は種類別の違いに盲目
    assert 0.90 < iou["iou"]["A"] < 0.99, iou["iou"]
    assert iou["iou"]["B"] > 0.999, iou["iou"]

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 見かけの積載率が同じ 2 つの荷を作れる(差 %.2f pt)。"
          "処置は「積み直す」と「降ろす」で正反対。" % du)
    print("  * 隙間は g = w で消え、はみ出しは g に比例して増える —— "
          "同じつまみが逆向きに壊す。")
    print("  * 1 個の一致度(IoU %.4f / %.4f)は、その違いを持っていない。"
          % (iou["iou"]["A"], iou["iou"]["B"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
