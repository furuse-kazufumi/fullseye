# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ハエ(雄)の脳を、細胞体 12 万 6 千個の点のまま描く —— 点群を描く op `points_render` で

ハエの脳の全体像は、ニューロンの細胞体(soma)の位置だけでも見える。MaleCNS v1.0(Janelia FlyEM ほか、
雄の全中枢神経系、CC BY 4.0。出典は下)の注釈には soma の座標と上位クラス(視葉の内在・中枢脳の内在・
視覚の投射・下行など)が付いている。これを**点群のまま**、上位クラスで色を分けて正面・側面・背面と回転で描く。

それまで Fullseye には点群を色の絵にする op が無かった(``render_point_depth`` は 1 点 1 画素の深度だけ、
``points_activity_video`` は活動の動画の出口、``gs_render`` は 3DGS の dict が要る)。ViEW 2026 の名刺の裏の
脳の絵は、手書きの numpy で点を置いていた。この PoC で使う ``points_render``(ops3d / render)は、小数画素の
足跡(gaussian / disc / point)を深さの順にアルファ合成するか、光の総量を保って足す。

**門は絵の外から当てる**(どれも描画器が自分で計算していない値):

1. 左右: 注釈の somaSide(座標とは独立のラベル)で L の細胞体が正面図の右半分に、R が左半分に入る
   (正面から見るとハエの左は見る人の右)。背面図では逆。
2. 2 台のカメラの一致: 正面図と背面図は同じ x を別の向きから写すので、加算の像の列ごとの和は
   **左右を反転して厳密に一致**する(足跡の形も向きも違う 2 回の描画)。
3. 光の保存: 加算の像の総和 = 点の色の総和(足跡を和 1 に正規化した約束)。
4. 重心: 上位クラスごとの像の重心 = そのクラスの点の平均を閉じた式で射影した位置(gaussian の足跡)。
5. 前後・背腹(実データだけ): 細胞型の名前で引いた Kenyon 細胞(キノコ体、脳の後ろ・背側)は触角葉の
   投射・局所ニューロン(前・腹側)より、正面図で上に、側面図で右(後ろ)に写る。

データ: MaleCNS v1.0 ``body-annotations-male-cns-v1.0-minconf-0.5.feather``(13 MB)。**repo には入れない**
(図と集計だけ)。環境変数 ``FULLSEYE_MALECNS_DIR`` に feather のあるディレクトリを指すと、soma の座標・
上位クラス・左右を ``FULLSEYE_DATA_DIR``(既定 ``~/.cache/fullseye``)にキャッシュする(pyarrow が要る)。
無いときは、``poc_malecns_activity_wave`` のキャッシュに soma の全数があればそれを使い、それも無ければ
**合成の代替**(視葉 2 つと中枢脳の形の点群、同じクラス名)で同じ門を走らせ、実データの章は記録値を印字する。

出典: Male CNS dataset v1.0, Janelia FlyEM / Google Research, https://male-cns.janelia.org/ (CC BY 4.0,
creativecommons.org/licenses/by/4.0). 座標は 8 nm のボクセル。図は soma の位置を描いたもので、データの改変は
「脳(VNC・上行・VNC 側の z ≥ 60,000 を除く)だけを選んだ」ことのみ。

使い方:
    py -3.11 examples/poc_flybrain_pointcloud.py
    FULLSEYE_MALECNS_DIR=C:/dev/data/malecns FULLSEYE_FIGURE_DIR=out/poc_flybrain_pointcloud py -3.11 examples/poc_flybrain_pointcloud.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
ANNOT = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
UM_PER_VOXEL = 0.008                       # MaleCNS の座標は 8 nm のボクセル
VNC_Z = 60000.0                            # これより後ろ(z が大きい)は首から VNC 側
SOURCE = ("Male CNS dataset v1.0 (minconf 0.5), Janelia FlyEM / Google Research, https://male-cns.janelia.org/, "
          "CC BY 4.0 (creativecommons.org/licenses/by/4.0) - soma positions and superclass labels; brain somata "
          "selected (VNC, ascending and z >= 60,000 excluded), otherwise unchanged")
SEED = 20261018
BUDGET_S = 60.0 if REDUCED else 240.0

#: 実データで測った値(データが無い環境ではこれを印字する)。2026-10-18、MaleCNS v1.0 minconf 0.5。
RECORDED = {
    "n_brain": 126104,
    "classes": {"ol_intrinsic": 81055, "visual_projection": 9162, "visual_centrifugal": 563,
                "cb_intrinsic": 31997, "descending_neuron": 1308, "other": 2019},
    "left_on_right_front": 0.99548, "right_on_left_front": 0.99957,
    "kenyon_vs_antennal_lobe": "front rows 166 < 237 (KC dorsal), side columns 281 < 384 (AL anterior)",
    "marginal_rel_err": 1.8e-15, "energy_rel_err": 1.2e-16, "centroid_err_px": 1.4e-05,
    "mirror_iou_front": 0.862,
}

#: 上位クラス → (色, 日本語の札)。その他は灰。
CLASSES = [
    ("ol_intrinsic", (0.25, 0.70, 1.00), "視葉の内在ニューロン"),
    ("visual_projection", (0.78, 0.48, 1.00), "視覚の投射ニューロン(視葉→中枢)"),
    ("visual_centrifugal", (1.00, 0.42, 0.78), "視覚の遠心性ニューロン(中枢→視葉)"),
    ("cb_intrinsic", (1.00, 0.66, 0.25), "中枢脳の内在ニューロン"),
    ("descending_neuron", (0.35, 0.95, 0.55), "下行ニューロン(脳→VNC)"),
]
OTHER = ((0.70, 0.72, 0.76), "その他・未分類")
BG = (0.05, 0.055, 0.075)

FAILS: list[str] = []
GATES: list[str] = []


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- data
def _cache_dir() -> str:
    base = os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye")
    return os.path.join(base, "poc_flybrain_pointcloud")


def _brain_mask(P: np.ndarray, sc: np.ndarray) -> np.ndarray:
    """脳だけ: VNC・上行(efferent_ascending を含む)の上位クラスと、z ≥ VNC_Z の細胞体を除く。"""
    vnc = np.array([s.startswith(("vnc", "ascending", "efferent_asc")) for s in sc])
    return (~vnc) & (P[:, 2] < VNC_Z)


def load_somata() -> tuple[dict | None, str]:
    """{P (n,3) voxel, superclass (n,), side (n,)} を脳だけに絞って返す。無ければ (None, 理由)。"""
    npz = os.path.join(_cache_dir(), "malecns_somata.npz")
    src = os.environ.get("FULLSEYE_MALECNS_DIR")
    try:
        stale = os.path.exists(npz) and "type" not in np.load(npz).files
        if (stale or not os.path.exists(npz)) and src and os.path.exists(os.path.join(src, ANNOT)):
            import pyarrow.ipc as ipc

            ann = ipc.open_file(os.path.join(src, ANNOT)).read_pandas()
            s = ann[ann["somaLocation"].notna()]
            body = s["bodyId"].to_numpy().astype(np.int64)
            o = np.argsort(body, kind="stable")
            os.makedirs(_cache_dir(), exist_ok=True)
            np.savez_compressed(npz, P=np.stack(s["somaLocation"].values).astype(np.float32)[o],
                                superclass=s["superclass"].fillna("?").to_numpy().astype(str)[o],
                                side=s["somaSide"].fillna("?").to_numpy().astype(str)[o],
                                type=s["type"].fillna("").to_numpy().astype(str)[o])
        if os.path.exists(npz):
            z = np.load(npz)
            P, sc, side = z["P"].astype(np.float64), z["superclass"], z["side"]
            typ = z["type"] if "type" in z.files else np.full(len(P), "")
            how = "MaleCNS v1.0 annotations (cache: %s)" % npz
        else:
            alt = os.path.join(os.path.dirname(_cache_dir()), "poc_malecns_activity_wave", "malecns_top3000.npz")
            z = np.load(alt) if os.path.exists(alt) else None
            if z is None or "superclass_all" not in z.files:
                raise FileNotFoundError("no MaleCNS annotations: set FULLSEYE_MALECNS_DIR to the folder with " + ANNOT)
            P, sc, side = z["P_all"].astype(np.float64), z["superclass_all"], z["side_all"]
            typ = np.full(len(P), "")
            how = "MaleCNS v1.0 somata via the poc_malecns_activity_wave cache (%s)" % alt
        m = _brain_mask(P, sc)
        return {"P": P[m], "superclass": sc[m], "side": side[m], "type": typ[m], "voxel_um": UM_PER_VOXEL}, how
    except Exception as exc:                                       # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, str(exc)[:120])


def synthetic_brain(n: int = 24000) -> dict:
    """合成の代替: 中枢脳(扁平な楕円体)+ 左右の視葉(縦長の楕円体の殻)+ 投射と下行。単位はボクセル。"""
    rng = np.random.default_rng(SEED)
    parts = []

    def blob(m, c, ax, cls, side, shell=False):
        v = rng.normal(size=(m, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        r = rng.uniform(0.82, 1.0, m) if shell else rng.uniform(0.0, 1.0, m) ** (1 / 3)
        parts.append((np.asarray(c) + v * r[:, None] * np.asarray(ax), [cls] * m, [side] * m))

    k = n // 24
    blob(5 * k, (34000, 30000, 30000), (9000, 11000, 6000), "ol_intrinsic", "R", shell=True)
    blob(5 * k, (64000, 30000, 30000), (9000, 11000, 6000), "ol_intrinsic", "L", shell=True)
    blob(4 * k, (44000, 20000, 26000), (5000, 7000, 7000), "cb_intrinsic", "R")
    blob(4 * k, (54000, 20000, 26000), (5000, 7000, 7000), "cb_intrinsic", "L")
    blob(2 * k, (40000, 26000, 32000), (3000, 5000, 4000), "visual_projection", "R")
    blob(2 * k, (58000, 26000, 32000), (3000, 5000, 4000), "visual_projection", "L")
    blob(k, (46000, 36000, 34000), (2500, 4000, 3000), "descending_neuron", "R")
    blob(k, (52000, 36000, 34000), (2500, 4000, 3000), "descending_neuron", "L")
    P = np.vstack([p for p, _c, _s in parts])
    sc = np.concatenate([np.array(c) for _p, c, _s in parts])
    side = np.concatenate([np.array(s) for _p, _c, s in parts])
    return {"P": P, "superclass": sc, "side": side, "voxel_um": UM_PER_VOXEL}


def colours_of(sc: np.ndarray) -> np.ndarray:
    lut = {name: col for name, col, _lab in CLASSES}
    return np.array([lut.get(s, OTHER[0]) for s in sc], dtype=np.float64)


# --------------------------------------------------------------------------- cameras
#: カメラ座標の行 = (画面の右, 画面の下, 奥)。MaleCNS の座標は x = 左右(ハエの左が大)、
#: y = 背 → 腹、z = 前 → 後ろ(VNC 側が大)。正面図は前から後ろを見る = R は単位行列。
VIEWS = {
    "front": np.eye(3),
    # 左の側面(ハエの左から見る): 奥 = −x、下 = +y、右 = 下 × 奥 = +z(後ろが右)
    "side": np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]),
    # 背面(上から見る、前が上): 奥 = +y、下 = +z(後ろが下)、右 = 下 × 奥 = −x(ハエの左が左)
    "top": np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]),
}
VIEW_LABEL = {"front": "正面(前から。ハエの左が右)", "side": "側面(ハエの左から。前が左)",
              "top": "背面(上から。前が上)"}


def yaw_R(deg: float) -> np.ndarray:
    """正面図から、背腹の軸(y)まわりに回したカメラ。"""
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def camera(P: np.ndarray, H: int, W: int, fill: float = 0.92):
    """全ビュー共通の正射影カメラ(倍率は 3 次元の外接球で決めるので、どの向きでも同じ縮尺)。"""
    c = 0.5 * (P.min(axis=0) + P.max(axis=0))
    rad = float(np.linalg.norm(P - c, axis=1).max())
    s = fill * (min(H, W) - 1) / (2.0 * rad)
    K = np.array([[s, 0.0, (W - 1) / 2.0], [0.0, s, (H - 1) / 2.0], [0.0, 0.0, 1.0]])
    return c, K, s


def render(P, cols, R, c, K, size, **kw):
    return fs.ledger.points_render(P, colors=cols, size=size, K=K, R=R, t=-(R @ c), **kw)


# --------------------------------------------------------------------------- gates
def check(d: dict, label: str, H: int, W: int) -> dict:
    P, sc, side = d["P"], d["superclass"], d["side"]
    cols = colours_of(sc)
    c, K, s = camera(P, H, W)
    out = {"n": len(P), "scale_px_per_voxel": s}
    names = [n for n, _c, _l in CLASSES]
    counts = {n: int((sc == n).sum()) for n in names}
    counts["other"] = int(len(sc) - sum(counts.values()))
    out["classes"] = counts
    print("   細胞体 %s 個: %s" % (format(len(P), ","), ", ".join("%s %s" % (k, format(v, ",")) for k, v in counts.items())))

    # 1. 左右(注釈のラベル vs 座標から作った絵)
    for view, want_left_on_right in (("front", True), ("top", False)):
        R = VIEWS[view]
        u = s * ((P - c) @ R.T)[:, 0] + K[0, 2]
        mid = s * ((np.median(P[side == "M"], axis=0) - c) @ R.T)[0] + K[0, 2] if (side == "M").any() else K[0, 2]
        L, Rr = side == "L", side == "R"
        fl = float((u[L] > mid).mean())
        fr = float((u[Rr] < mid).mean())
        if view == "front":
            out["left_on_right_front"], out["right_on_left_front"] = fl, fr
        if want_left_on_right:
            gate("%s %s: 注釈で L の細胞体が右半分・R が左半分に(正面から見るとハエの左は右)" % (label, view),
                 fl > 0.99 and fr > 0.99, "L→右 %.5f / R→左 %.5f" % (fl, fr))
        else:
            gate("%s %s: 背面図では L が左半分・R が右半分(前が上)" % (label, view),
                 (1 - fl) > 0.99 and (1 - fr) > 0.99, "L→左 %.5f / R→右 %.5f" % (1 - fl, 1 - fr))

    # 1b. 前後・背腹(細胞型の解剖学: キノコ体の Kenyon 細胞の細胞体は脳の後ろ・背側の皮質に、
    #     触角葉の投射ニューロン・局所ニューロンの細胞体は前・腹側にある)。座標の軸の向きを、型の名前で確かめる
    typ = d.get("type")
    if typ is not None and (np.char.str_len(typ.astype(str)) > 0).any():
        typ = typ.astype(str)
        kc = np.char.startswith(typ, "KC")
        al = np.array([("adPN" in x) or ("lPN" in x) or x.startswith("lLN") for x in typ])
        cam = {v: s * ((P - c) @ VIEWS[v].T)[:, :2] + K[:2, 2] for v in ("front", "side")}
        kc_v, al_v = cam["front"][kc, 1].mean(), cam["front"][al, 1].mean()      # 正面図の行(下が腹)
        kc_u, al_u = cam["side"][kc, 0].mean(), cam["side"][al, 0].mean()        # 側面図の列(左が前)
        out["anatomy"] = {"n_kc": int(kc.sum()), "n_al": int(al.sum()), "front_row_kc": float(kc_v),
                          "front_row_al": float(al_v), "side_col_kc": float(kc_u), "side_col_al": float(al_u)}
        gate("%s 正面図で Kenyon 細胞(%d)が触角葉ニューロン(%d)より上(背側)" % (label, kc.sum(), al.sum()),
             kc_v < al_v, "平均の行 %.0f < %.0f" % (kc_v, al_v))
        gate("%s 側面図で触角葉ニューロンが Kenyon 細胞より左(前)" % label, al_u < kc_u,
             "平均の列 %.0f < %.0f" % (al_u, kc_u))

    # 2. 2 台のカメラの一致(正面と背面の列の和は左右反転で一致)
    kw = dict(composite="add", footprint="gaussian", radius_px=1.5, opacity=1.0, background=(0.0, 0.0, 0.0))
    ones = np.ones((len(P), 3))
    af = render(P, ones, VIEWS["front"], c, K, (H, W), **kw)[:, :, 0]
    at = render(P, ones, VIEWS["top"], c, K, (H, W), **kw)[:, :, 0]
    mf, mt = af.sum(axis=0), at.sum(axis=0)[::-1]
    rel = float(np.abs(mf - mt).max() / mf.max())
    out["marginal_rel_err"] = rel
    gate("%s 正面図と背面図(別のカメラ)の列ごとの和が左右反転で一致" % label, rel < 1e-9, "最大の相対差 %.1e" % rel)

    # 3. 光の保存
    tot = float(af.sum())
    erel = abs(tot - len(P)) / len(P)
    out["energy_rel_err"] = erel
    gate("%s 加算の像の総和 = 点の数(足跡は和 1)" % label, erel < 1e-9, "%.6f / %d、相対差 %.1e" % (tot, len(P), erel))

    # 4. 重心 = 閉じた式の射影(クラスごと)
    worst = 0.0
    rr, cc = np.mgrid[0:H, 0:W]
    for n in names:
        m = sc == n
        if m.sum() < 10:
            continue
        img = render(P[m], ones[m], VIEWS["front"], c, K, (H, W), **kw)[:, :, 0]
        cu, cv = (img * cc).sum() / img.sum(), (img * rr).sum() / img.sum()
        Xc = (P[m].mean(axis=0) - c)
        eu, ev = s * Xc[0] + K[0, 2], s * Xc[1] + K[1, 2]
        worst = max(worst, abs(cu - eu), abs(cv - ev))
    out["centroid_err_px"] = worst
    gate("%s クラスごとの像の重心 = 点の平均の射影(閉じた式)" % label, worst < 1e-3, "最大 %.1e 画素" % worst)

    # 観察(門ではない): 正面図の占有の左右対称さ(正中の M の細胞体の列で折り返した IoU)
    occ = af > 0.05
    if (side == "M").any():
        mid = s * (np.median(P[side == "M"], axis=0) - c)[0] + K[0, 2]
    else:
        mid = K[0, 2]
    k0 = int(round(mid))
    w = min(k0, W - 1 - k0)
    left, right = occ[:, k0 - w:k0], occ[:, k0 + 1:k0 + 1 + w][:, ::-1]
    iou = float((left & right).sum() / max(1, (left | right).sum()))
    out["mirror_iou"] = iou
    print("   (観察)正面図の占有を正中で折り返した IoU %.3f —— 細胞体の配置は左右でここまで揃う" % iou)
    return out


# --------------------------------------------------------------------------- figures
def legend_panel(img: np.ndarray, counts: dict, n: int) -> np.ndarray:
    y = 8
    out = img
    for name, col, lab in CLASSES:
        out = fs.text_box(out, "●  %s  %s" % (lab, format(counts.get(name, 0), ",")), (8, y),
                          text_color=col, box_color=(0.0, 0.0, 0.0), font_size=13)
        y += 24
    out = fs.text_box(out, "●  %s  %s" % (OTHER[1], format(counts.get("other", 0), ",")), (8, y),
                      text_color=OTHER[0], box_color=(0.0, 0.0, 0.0), font_size=13)
    return out


def figures(d: dict, real: bool) -> None:
    if not figs.enabled():
        return
    P, sc = d["P"], d["superclass"]
    cols = colours_of(sc)
    counts = {n: int((sc == n).sum()) for n, _c, _l in CLASSES}
    counts["other"] = int(len(sc) - sum(counts.values()))
    src = SOURCE if real else ""
    tag = "MaleCNS v1.0(CC BY 4.0)" if real else "合成の代替(実データ無し)"
    H, W = 520, 700
    c, K, s = camera(P, H, W)
    look = dict(composite="over", footprint="gaussian", radius_px=1.6, opacity=0.3, depth_cue=0.5,
                background=BG)
    panels, caps = [], []
    for view in ("front", "side", "top"):
        img = render(P, cols, VIEWS[view], c, K, (H, W), **look)
        img = fs.annotate_scale_bar(img, UM_PER_VOXEL / s, unit="µm")
        if view == "front":
            img = legend_panel(img, counts, len(P))
        panels.append(img)
        caps.append(VIEW_LABEL[view])
    fig = fs.annotate_figure_grid(panels, captions=caps, ncols=3,
                                  title="ハエ(雄)の脳の細胞体 %s 個を points_render で描く —— %s"
                                  % (format(len(P), ","), tag))
    figs.save("three_views", fig, "正面・側面・背面。1 点 = 1 個の細胞体、色 = 上位クラス。gaussian の足跡(半径 1.6 画素)を"
              "不透明度 0.3 で深さの順に重ね、奥ほど暗く(depth_cue 0.5)。縮尺は 3 面で共通。" + tag, source=src)

    # 回転(背腹の軸まわり、正面から 1 周)
    nf = 24 if REDUCED else 36
    Hg, Wg = 380, 460
    cg, Kg, sg = camera(P, Hg, Wg, fill=0.96)
    frames = []
    for i in range(nf):
        R = yaw_R(360.0 * i / nf)
        frames.append(render(P, cols, R, cg, Kg, (Hg, Wg), composite="over", footprint="gaussian",
                             radius_px=1.2, opacity=0.35, depth_cue=0.5, background=BG))
    first = fs.text_box(frames[0], "正面(前から)", (8, 8), font_size=13, box_color=(0.0, 0.0, 0.0),
                        text_color=(0.95, 0.95, 0.95))
    figs.save("rotation_first_frame", first, "回転の 1 コマ目(静止画の代わり)。正面から見たところ。" + tag, source=src)
    figs.save_gif("rotation", frames, "背腹の軸まわりに 1 周(%d コマ)。どのコマも points_render の 1 回の呼び出し。%s"
                  % (nf, tag), fps=10.0)

    # 同じ点で、足跡と重ね方を変える(op のノブが絵の何を決めるか)
    Hz, Wz = 360, 360
    cz, Kz, sz = camera(P, Hz, Wz, fill=0.92)
    Kz = Kz.copy()
    Kz[0, 0] = Kz[1, 1] = sz * 2.6                                  # 中央を 2.6 倍に拡大(右の視葉と中枢の境)
    off = (np.array([-0.18, -0.02, 0.0]) * (P.max(axis=0) - P.min(axis=0)))
    cz2 = cz + off
    v1 = render(P, cols, VIEWS["front"], cz2, Kz, (Hz, Wz), footprint="point", background=BG)
    v2 = render(P, cols, VIEWS["front"], cz2, Kz, (Hz, Wz), footprint="disc", radius_px=2.0, background=BG)
    v3 = render(P, cols, VIEWS["front"], cz2, Kz, (Hz, Wz), footprint="gaussian", radius_px=2.0, opacity=0.5,
                depth_cue=0.6, background=BG)
    dens = render(P, np.ones((len(P), 3)), VIEWS["front"], cz2, Kz, (Hz, Wz), composite="add",
                  footprint="gaussian", radius_px=2.0, background=(0.0, 0.0, 0.0))[:, :, 0]
    v4 = fs.colorize_depth(np.log1p(dens) / np.log1p(dens.max()))
    v4 = np.asarray(v4, dtype=np.float64)
    v4 = v4 / 255.0 if v4.max() > 1.0 else v4
    fig2 = fs.annotate_figure_grid([v1, v2, v3, v4], ncols=4,
                                   captions=["point(1 点 1 画素)", "disc 不透明(手前が隠す)",
                                             "gaussian 半透明 + 奥を暗く", "add(数の密度、対数)"],
                                   title="同じ 12 万点・同じカメラで、足跡と重ね方だけを変える(右の視葉と中枢脳の境を 2.6 倍)")
    figs.save("footprints", fig2, "points_render のノブ: footprint(point / disc / gaussian)と composite(over / add)。"
              "point は render_point_depth と同じ画素に落ち、隙間が残る。add は光の総量を保つので密度の地図になる。" + tag,
              source=src)


def main() -> None:
    t0 = time.process_time()
    w0 = time.time()
    print("PoC ハエ(雄)の脳を細胞体の点群のまま描く(予算 %s)" % ("reduced" if REDUCED else "full"))
    print("\n[1] 合成の代替で門を回す(どの環境でも走る)")
    syn = synthetic_brain(12000 if REDUCED else 24000)
    check(syn, "合成", 300, 400)

    print("\n[2] 実データ(MaleCNS v1.0)")
    d, how = load_somata()
    if d is None:
        print("   DATA: 無し(%s)—— 記録値(2026-10-18 実測)を印字して飛ばす" % how)
        for k, v in RECORDED.items():
            print("   recorded %s = %s" % (k, v))
        figures(syn, real=False)
    else:
        print("   DATA: %s" % how)
        H, W = (300, 400) if REDUCED else (520, 700)
        got = check(d, "MaleCNS", H, W)
        gate("MaleCNS 脳の細胞体の数が記録値どおり(VNC・上行・z ≥ 60,000 を除く)",
             got["n"] == RECORDED["n_brain"], "%s 個(記録 %s)" % (format(got["n"], ","), format(RECORDED["n_brain"], ",")))
        figures(d, real=True)
    used = time.process_time() - t0
    gate("所要(この PoC の CPU 時間)%.0f s 以内" % BUDGET_S, used <= BUDGET_S,
         "CPU %.1f s / 壁時計 %.1f s" % (used, time.time() - w0))
    print("\n門 %d 件中 NG %d 件" % (len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
