# -*- coding: utf-8 -*-
"""chain_fuzz — 型で op を繋ぐ拡散・収束ファザー(ops3d + ops1d)。

進化レジストリの流儀を目録全体へ: 型互換な op をランダムに連鎖(拡散)し、
失敗を署名でまとめて最小再現に絞る(収束)。狙いは「単体テストは通るが
**op の出力を次の op が食うと壊れる**」クラスの不具合 — 型契約の嘘、
タプル/リスト梱包の不一致、NaN の漏出、想定外の例外種。

判定の分類:
  CONTRACT  ValueError で明確な文言 = fail-closed が仕事をした(白)
  SUSPECT   それ以外の例外(TypeError/IndexError/KeyError/…)= 契約の穴
  NONFINITE 有限入力から NaN/Inf が無言で出た = 毒の漏出
  TYPEMISS  目録の宣言 out 型と実際の返りが違う = 型の嘘
  GROWTH    産物が pool 上限超(拡大系の指数増殖)= 記録して捨てる
  SLOW      1 op が閾値超(既定 10s)= 性能スメル

再現性: 連鎖 i は master seed から導いた **連鎖固有 seed** で回る(共有 rng
だと i 番目だけを後から再現できないため)。各 findings はその ``seed`` を
持つので、``--minimize`` が正確に再走できる。

使い方:
    py -3.11 tools/chain_fuzz.py --chains 400 --length 6 --seed 0
    py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl   # 全署名を短縮
    py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl --only vol_frangi
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SLOW_S = 10.0


# --------------------------------------------------------------------------- #
# 型 → 生成器(小さく・決定的に。voxel は 16^3 で全 op が秒未満)               #
# --------------------------------------------------------------------------- #
def _ball_vol(rng, n=16):
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    c = n / 2.0
    v = ((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2 <= (n * 0.3) ** 2).astype(np.float64)
    return np.clip(v + 0.05 * rng.standard_normal(v.shape), 0.0, 1.0)


def _points(rng, n=160):
    return rng.random((n, 3)) * 10.0


def _mesh(rng):
    import meshrepair
    return meshrepair.convex_hull(_points(rng, 60))


def _score_volume(rng):
    """ピークを 1 つ持つ異方性ガウスの相関 volume(サブボクセル精緻化の入力)。

    軸ごとに幅を変えてあるので、軸別の放物線当てはめと全 Hessian 法の差が
    実際に現れる。中心は格子からわざと外して置く(整数ピークにすると
    サブボクセル精緻化が「何もしない」経路しか通らない)。
    """
    n = 16
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    c = 7.5 + rng.uniform(-1.5, 1.5, size=3)
    s = rng.uniform(1.5, 3.0, size=3)
    return np.exp(-(((z - c[0]) / s[0]) ** 2 + ((y - c[1]) / s[1]) ** 2
                    + ((x - c[2]) / s[2]) ** 2) / 2.0)


def _photon_counts(rng):
    """光子カウントヒストグラム(非負・時間 bin 添字)。

    合成ではなく **実データと同じ作り方**にしてある: 既知距離の dToF 復路と
    背景光を足して Poisson 標本化する。適当な非負乱数を渡すと「山が 1 つある」
    という前提の op(ピーク探索・寿命フィット)が現実に無い形を食うことになる。
    """
    import photoncount                                   # noqa: PLC0415
    return photoncount.tcspc_simulate(
        distance_m=float(rng.uniform(0.5, 3.5)), bins=256, bin_ps=100.0,
        signal_photons=float(rng.uniform(100.0, 2000.0)),
        ambient_photons=float(rng.uniform(0.0, 500.0)),
        irf_fwhm_ps=500.0, seed=int(rng.integers(0, 1 << 31)))


def _jones_vec(rng):
    """Jones ベクトル (Ex, Ey): 長さ 2 の complex。単位強度に正規化。"""
    v = rng.standard_normal(2) + 1j * rng.standard_normal(2)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else np.array([1.0 + 0j, 0.0 + 0j])


def _stokes_vec(rng):
    """Stokes ベクトル (S0..S3): 長さ 4 の実で、偏光度 <= 1 を必ず満たす。

    ここを満たさない値を入れると mueller_apply/stokes_analyze の fail-closed が
    正しく発火するだけで、偏光ファミリの実経路は一度も通らない。"""
    d = rng.standard_normal(3)
    d /= max(float(np.linalg.norm(d)), 1e-12)
    return np.concatenate([[1.0], d * float(rng.uniform(0.0, 1.0))])


def make_generators():
    return {
        "voxel": _ball_vol,
        "points": _points,
        "image2d": lambda rng: rng.random((32, 32)),
        "depth": lambda rng: 1.0 + rng.random((32, 32)),
        "images": lambda rng: [rng.random((32, 32)) for _ in range(4)],
        "normals": lambda rng: (lambda v: v / np.linalg.norm(v, axis=1, keepdims=True))(
            rng.standard_normal((160, 3))),
        "signal": lambda rng: np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256),
        "vector": lambda rng: (lambda v: v / np.linalg.norm(v))(rng.standard_normal(3)),
        "pose": lambda rng: (np.eye(3), np.zeros(3)),
        "measurement": lambda rng: float(rng.random()),
        "angle": lambda rng: float(rng.uniform(0, 90)),
        "position": lambda rng: (8.0, 8.0, 8.0),
        "sdf": lambda rng: _ball_vol(rng) - 0.5,
        "gaussians": lambda rng: {"mu": _points(rng, 40), "sigma": np.full(40, 0.3),
                                  "w": np.full(40, 1.0 / 40)},
        # HALCON の complex 画像形式に対応(cx_fft の出力レイアウト = 中心 DC)
        "cimage": lambda rng: np.fft.fftshift(np.fft.fft2(rng.random((32, 32)))),
        # organized 系(H,W,3)— (N,3) の points/normals とは別型
        "pointmap": lambda rng: rng.random((16, 16, 3)) * 8.0,
        "normalmap": lambda rng: np.dstack([np.zeros((16, 16)), np.zeros((16, 16)),
                                            np.ones((16, 16))]),
        # 数学ファミリ(opsmath): matrix は image2d(32²固定)より小さい一般行列
        "matrix": lambda rng: rng.standard_normal(
            (int(rng.integers(2, 12)), int(rng.integers(2, 12)))),
        "roots": lambda rng: rng.standard_normal(6) + 1j * rng.standard_normal(6),
        # cpoints = 複素平面の順序つき点列(閉曲線)。tier2 複素解析の入口は
        # 「一様サンプルの単位円」— これなら Laurent 係数(円限定)も通り、
        # 写像 op の像(退化した輪郭)が下流へ回って敵対入力にもなる
        "cpoints": lambda rng: np.exp(
            2j * np.pi * np.arange(64, dtype=np.float64) / 64.0),
        # 光学ファミリ(opsoptics)の偏光 2 語。長さ固定 + 物理制約つきなので
        # signal/cpoints へ相乗りさせると常に CONTRACT にしかならない(=偏光
        # 連鎖を一度も通らない)ため専用プールにする
        "jones": _jones_vec,
        "stokes": _stokes_vec,
        # ライトフィールド = 4-D (V,U,H,W)。空間サイズを image2d と揃えた 32x32
        # にしてあるので、2 入力の lf_all_in_focus(lightfield + image2d)が
        # ファザーの中で実際に噛み合う
        "lightfield": lambda rng: __import__("lightfield").lf_synthesize(
            (0.0, 1.0), angular=(3, 3), shape=(32, 32),
            seed=int(rng.integers(0, 1000)))[0],
        # score = ピークを持つ 3-D 相関/スコア volume。**カタログのどの op も
        # score を出力しない**ので、種を置かないと `refine_peak_newton` が
        # 構造的に到達不能なまま「発見ゼロ」に数えられる(型到達可能性の
        # 不動点計算で実測: 434 op 中これ 1 件だけが blocked だった)。
        # 一様乱数ではピーク精緻化が意味を持たないので、異方性ガウス山にする
        "score": _score_volume,
        # 光子カウント列。既知距離の dToF 復路 + 背景光を Poisson 標本化した
        # もの = 実データと同じ形と統計(実測 shape (256,)、値域 [0, 303])
        "counts": _photon_counts,
        # SPAD の計数レート列 [Hz]。既定デッドタイム 50 ns の飽和 2e7 Hz の
        # 半分までしか置かないので逆変換が必ず定義域に入る
        "countrate": lambda rng: np.sort(10.0 ** rng.uniform(3.0, 7.0, size=32)),
        # histcube = (H, W, T) の到達時刻ヒストグラム立方体。時間軸が最後で、
        # 128 bin x 200 ps = 一意測距範囲 3.84 m(深度 1-2 m は必ず窓に収まる)
        "histcube": lambda rng: __import__("photoncount").dtof_cube_simulate(
            1.0 + rng.random((16, 16)), bins=128, bin_ps=200.0,
            signal_photons=60.0, ambient_photons=10.0,
            seed=int(rng.integers(0, 1 << 31))),
    }


#: 必須スカラ引数の名前 → 値サンプラ(署名 introspection で束縛)
PARAM_HINTS = {
    "center": lambda rng: 0.5, "width": lambda rng: 0.5,
    "gamma": lambda rng: float(rng.uniform(0.5, 2.0)),
    "cutoff": lambda rng: 0.1, "low": lambda rng: 0.05, "high": lambda rng: 0.2,
    "sigma": lambda rng: 1.0, "scale": lambda rng: 2.0,
    "angle_deg": lambda rng: float(rng.uniform(-90, 90)),
    "factor": lambda rng: 2, "matrix": lambda rng: np.eye(3),
    "p0": lambda rng: (2.0, 2.0, 2.0), "p1": lambda rng: (13.0, 13.0, 13.0),
    "iterations": lambda rng: 3, "psf": lambda rng: None,   # None -> skip op
    "markers": lambda rng: None,
    "rate": lambda rng: 100.0, "new_rate": lambda rng: 50.0,
    "x": lambda rng: 1.0, "step": lambda rng: 2,
    "radius": lambda rng: 1.5, "ratio": lambda rng: 0.2,
    # 励起サイクル数(パイルアップ補正の分母)。tcspc_simulate 既定の総カウント
    # ~87 に対して十分大きくないと Coates 逆変換が定義域を外れる
    "cycles": lambda rng: 1_000_000,
    # 角度分解能。既定の (5,5) はファザーの 32x32 image2d を割り切れず
    # lf_from_mla が必ず ValueError になるので、割り切れる (4,4) を渡す
    "angular": lambda rng: (4, 4),
    "extent": lambda rng: 1.0, "lo": lambda rng: 0.8, "hi": lambda rng: 1.2,
    "strength": lambda rng: 0.5, "voxel": lambda rng: 0.5,
    "lights": lambda rng: (lambda L: L / np.linalg.norm(L, axis=1, keepdims=True))(
        np.array([[0.3, 0.3, 1.0], [-0.3, 0.3, 1.0], [0.3, -0.3, 1.0],
                  [-0.2, -0.2, 1.0]])),
    "k": lambda rng: 8, "n": lambda rng: 64, "size": lambda rng: 8,
}

#: シグネチャが「型リスト=先頭位置引数」の素直な形でない op の専用ビルダー。
#: pool と rng から (args, kwargs) を組み立てる(None を返すとこの回スキップ)
def _b_fuse(pool, rng):
    pts = pool.get("points")
    if not pts:
        return None
    return ([(pts[int(rng.integers(len(pts)))], "points", {})],), {"size": 8}


def _b_register_cross(pool, rng):
    cands = [p for p in pool.get("points", []) if _is_pts(p)]
    if not cands:
        return None
    a = cands[int(rng.integers(len(cands)))]
    b = a + rng.standard_normal(a.shape) * 0.1
    return (a, "points", b, "points"), {"method": "icp"}


def _b_abcd(pool, rng):
    """ABCD 素子リスト。半分は妥当な系(実経路を通す)、半分は pool の table
    (dict や他 op の返り)= 敵対入力で fail-closed を叩く。"""
    if rng.random() < 0.5:
        tables = pool.get("table") or []
        if tables:
            return (tables[int(rng.integers(len(tables)))],), {}
    kinds = [("free", float(rng.uniform(0.0, 200.0))),
             ("lens", float(rng.uniform(10.0, 200.0)) * rng.choice([-1.0, 1.0])),
             ("mirror", float(rng.uniform(10.0, 500.0))),
             ("interface", 1.0, float(rng.uniform(1.1, 2.0))),
             ("curved", 1.0, float(rng.uniform(1.1, 2.0)),
              float(rng.uniform(10.0, 500.0)))]
    k = int(rng.integers(1, 4))
    return ([kinds[int(rng.integers(len(kinds)))] for _ in range(k)],), {}


def _b_wavefront(pool, rng):
    """Zernike 係数 dict。半分は妥当な波面(match3d.fit_zernike と同形式)、
    半分は pool の table = 敵対入力。"""
    if rng.random() < 0.5:
        tables = pool.get("table") or []
        if tables:
            return (tables[int(rng.integers(len(tables)))],), {}
    idx = [(0, 0), (2, 0), (2, 2), (2, -2), (3, 1), (4, 0)]
    k = int(rng.integers(1, len(idx) + 1))
    return ({idx[i]: float(rng.normal(0.0, 0.05)) for i in range(k)},), {}


def _b_shaped(kind, shape, make, *extra):
    """先頭引数が **形の決まった行列**の op 用 builder を作る。

    光学の abcd_trace(2x2)/ jones_apply(2x2)/ mueller_apply(4x4)は、
    pool の一様抽選では実経路をまず通らない: 目録 400 op × 連鎖長 8 では
    「生成元の op(abcd_matrix / jones_element / mueller_element)と消費側が
    同一連鎖に、しかもこの順で入る」確率が ~0.03% しかなく、800 連鎖でも
    happy path 0 回・CONTRACT だけ、と実測した。そこで半分は *make* が作る
    妥当な行列(実経路)、半分は pool の一様抽選(敵対入力 → fail-closed)。
    ``_b_abcd`` / ``_b_wavefront`` と同じ「半分は妥当・半分は敵対」方針。"""
    def build(pool, rng):
        m = None
        if rng.random() < 0.5:
            fit = [c for c in (pool.get(kind) or [])
                   if isinstance(c, np.ndarray) and c.shape == shape]
            m = fit[int(rng.integers(len(fit)))] if fit else make(rng)
        else:
            cands = pool.get(kind) or []
            if cands:
                m = cands[int(rng.integers(len(cands)))]
        if m is None:
            return None
        args = [m]
        for t in extra:
            vals = pool.get(t) or []
            if not vals:
                return None
            args.append(vals[int(rng.integers(len(vals)))])
        return tuple(args), {}
    return build


def _mk_abcd(rng):
    import optics
    return optics.abcd_matrix([("free", float(rng.uniform(0.0, 200.0))),
                               ("lens", float(rng.uniform(10.0, 200.0)))])


def _mk_jones(rng):
    import optics
    return optics.jones_element(str(rng.choice(list(optics.JONES_KINDS))),
                                float(rng.uniform(-90.0, 90.0)),
                                float(rng.uniform(0.0, 360.0)))


def _mk_mueller(rng):
    import optics
    return optics.mueller_element(str(rng.choice(list(optics.MUELLER_KINDS))),
                                  float(rng.uniform(-90.0, 90.0)),
                                  float(rng.uniform(0.0, 360.0)))


OP_ARG_BUILDERS = {
    "abcd_matrix": _b_abcd,
    "wavefront_stats": _b_wavefront,
    "abcd_trace": _b_shaped("matrix", (2, 2), _mk_abcd),
    "jones_apply": _b_shaped("cimage", (2, 2), _mk_jones, "jones"),
    "mueller_apply": _b_shaped("matrix", (4, 4), _mk_mueller, "stokes"),
    "fuse_to_voxel": _b_fuse,
    "register_cross": _b_register_cross,
    "to_points": lambda pool, rng: ((pool["points"][0], "points"), {})
    if pool.get("points") else None,
}

#: op 固有の引数(名前が汎用ヒントと衝突する/型が op ごとに違うもの)。
#: **既定値つきの引数もここに書けば上書きできる**(名前レベルの PARAM_HINTS は
#: 必須引数にしか効かない — 詳細は `_bind_args`)。
OP_PARAM_HINTS = {
    # 既定 (5,5) はプールの 32x32 を割り切れず毎回 ValueError になり、この op が
    # 一度も実行されないまま「発見ゼロ」に見えていた。32 を割り切る (4,4) にする
    ("lf_from_mla", "angular"): lambda rng: (4, 4),
    ("vol_richardson_lucy", "psf"): lambda rng: __import__("volrestore").vol_gaussian_psf(1.0),
    ("cx_wiener_deconvolve", "psf"): lambda rng: (lambda k: k / k.sum())(
        np.outer(*(np.exp(-np.linspace(-2, 2, 5) ** 2),) * 2)),
    ("cx_apply_transfer_function", "H"): lambda rng: rng.random((32, 32)),
    # tier2 複素解析: w = 輪郭の内側にありそうな点(外・線上なら fail-closed
    # の CONTRACT が出るのが正しい)。Möbius の 4 係数は ad-bc≠0 の実例
    ("cplx_cauchy_value", "w"): lambda rng: 0.1 + 0.1j,
    ("cplx_mobius", "a"): lambda rng: 1.0,
    ("cplx_mobius", "b"): lambda rng: -1j,
    ("cplx_mobius", "c"): lambda rng: 1.0,
    ("cplx_mobius", "d"): lambda rng: 1j,
}

#: 文書化済みの非有限を返す op(光学)。docstring が契約として明記している:
#: depth_of_field は過焦点距離以遠で far/depth = inf(それが過焦点距離の定義)、
#: gaussian_beam はウエストで wavefront_radius = inf(平面波面の曲率半径)。
#: どちらも有限の逆数(curvature_per_mm)や bool を併せて返す。
NONFINITE_BY_CONTRACT_OPTICS = {"depth_of_field", "gaussian_beam"}

#: 出力を pool 型へ合わせる梱包アダプタ。基本はレジストリの RESULT_ADAPTERS
#: (型忠実の一級メタデータ)に委譲し、ファザー固有の追加だけここに置く
def _registry_adapters():
    import ops1d
    import ops3d
    import opsmath
    d = dict(ops3d.RESULT_ADAPTERS)
    d.update(ops1d.RESULT_ADAPTERS)
    d.update(opsmath.RESULT_ADAPTERS)
    import opsoptics
    d.update(opsoptics.RESULT_ADAPTERS)
    import opslightfield
    d.update(opslightfield.RESULT_ADAPTERS)
    import opsphoton
    d.update(opsphoton.RESULT_ADAPTERS)     # 現状は空(全 op が宣言型を素で返す)
    d["vol_rle_components"] = lambda r: r[0] if r else None
    d["label_components"] = lambda r: r[0] if isinstance(r, tuple) else r
    return d


ADAPTERS = _registry_adapters()


def catalog():
    """(name, module, in_types, out_type, fn) を ops3d + ops1d から集める。"""
    import ops1d
    import ops3d
    ops = []
    for n, m in ops3d.OPS3D.items():
        if m["func"] is not None:
            ops.append((n, "3d", list(m["in"]), m["out"], m["func"]))
    for n, m in ops1d.OPS1D.items():
        if m["func"] is not None and m["category"] != "io":   # ファイル I/O は除外
            ops.append((n, "1d", list(m["in"]), m["out"], m["func"]))
    # complexops = HALCON の complex 画像形式(2-D)。image2d <-> cimage の橋
    import complexops as cx
    for name, ins, out in [
        ("cx_fft", ["image2d"], "cimage"),
        ("cx_ifft", ["cimage"], "image2d"),
        ("cx_magnitude", ["cimage"], "image2d"),
        ("cx_phase", ["cimage"], "image2d"),
        ("cx_real", ["cimage"], "image2d"),
        ("cx_imag", ["cimage"], "image2d"),
        ("cx_log_magnitude", ["cimage"], "image2d"),
        ("cx_from_mag_phase", ["image2d", "image2d"], "cimage"),
        ("phase_unwrap", ["image2d"], "image2d"),
        ("cx_apply_transfer_function", ["cimage"], "cimage"),
        ("cx_bandpass", ["image2d"], "image2d"),
        ("cx_wiener_deconvolve", ["image2d"], "image2d"),
    ]:
        ops.append((name, "2d", ins, out, getattr(cx, name)))
    # 数学ファミリ(opsmath 台帳)。adapter 層を持たない=素の返りが宣言型で
    # あることを TYPEMISS 検査がそのまま機械検証する
    import opsmath
    for n, m in opsmath.OPSMATH.items():
        if m["func"] is not None:
            ops.append((n, "math", list(m["in"]), m["out"], m["func"]))
    # 光学ファミリ(opsoptics 台帳)。opsmath と同じく adapter 層を持たない=
    # 素の返りが宣言型であることを TYPEMISS 検査がそのまま機械検証する
    import opsoptics
    for n, m in opsoptics.OPSOPTICS.items():
        if m["func"] is not None:
            ops.append((n, "optics", list(m["in"]), m["out"], m["func"]))
    # ライトフィールドファミリ(opslightfield 台帳)。4-D (V,U,H,W) の新語彙
    # `lightfield` を持ち込む唯一の族で、`images` へ潰すと「どの視点か」が
    # 消えて refocus も EPI も定義できなくなるため型を分けている
    import opslightfield
    for n, m in opslightfield.OPSLIGHTFIELD.items():
        if m["func"] is not None:
            ops.append((n, "lightfield", list(m["in"]), m["out"], m["func"]))
    # 光子計数・時間分解(opsphoton 台帳)。新語彙 `histcube` は (H,W,T) で
    # **時間軸が最後**。voxel と ndim==3 の構造は同じだが軸の意味が違い、
    # (D,H,W) を渡すと例外ではなく「もっともらしく間違った深度」が出るため
    # 型を分ける(pointmap / normalmap を分けたのと同じ判断)
    import opsphoton
    for n, m in opsphoton.OPSPHOTON.items():
        if m["func"] is not None:
            ops.append((n, "photon", list(m["in"]), m["out"], m["func"]))
    return ops


def _bind_args(op_name, fn, data_args, rng):
    """先頭の必須位置引数へ data_args を割り当て、残る必須引数を op 固有 →
    名前ヒントの順で束縛。束縛できない必須引数が残れば None(スキップ)。"""
    import inspect
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return list(data_args), {}
    args = list(data_args)
    kwargs = {}
    params = [p for p in sig.parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    for p in params[len(args):]:
        if p.default is not inspect.Parameter.empty:
            # 既定値つきの引数は原則そのまま使う。ただし **op 固有ヒントがあれば
            # 上書きする**。既定値がプールの固定サイズと噛み合わない op は、
            # 上書きできないと毎回 ValueError になって「一度も実行されない」まま
            # 発見ゼロに見える(実測: lf_from_mla の既定 angular=(5,5) は 32x32 を
            # 割り切れず、1200 連鎖で覆われた 16/17 の残り 1 がこれだった)。
            # 名前レベルの PARAM_HINTS は既存 op の挙動を一斉に変えてしまうので
            # ここでは効かせない — 上書きは op 名で狙い撃ちしたものに限る。
            hint = OP_PARAM_HINTS.get((op_name, p.name))
            if hint is not None:
                val = hint(rng)
                if val is not None:
                    kwargs[p.name] = val
            continue
        hint = OP_PARAM_HINTS.get((op_name, p.name)) or PARAM_HINTS.get(p.name)
        if hint is None:
            return None
        val = hint(rng)
        if val is None:
            return None
        kwargs[p.name] = val
    return args, kwargs


#: pool 投入前の型検証(catalog の out 申告と実際の返りの乖離 = TYPEMISS を検出)
def _is_pts(v):
    return isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 3


TYPE_CHECKS = {
    "points": _is_pts,
    "normals": _is_pts,
    "keypoints": lambda v: _is_pts(v) or (isinstance(v, np.ndarray) and v.ndim == 2),
    "voxel": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    "sdf": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    "labels": lambda v: isinstance(v, np.ndarray) and v.ndim >= 1,
    "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "depth": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "cimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 2 and v.dtype.kind == "c",
    "signal": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
    # measurement = スカラのみ(tuple/dict がここに紛れると下流 op が生 TypeError
    # で落ちる — 第 3 波でプール汚染として実測)
    "measurement": lambda v: isinstance(v, (int, float, np.floating, np.integer)),
    "indices": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
    "table": lambda v: isinstance(v, (list, dict)),
    "rle_region": lambda v: type(v).__name__ == "VolRLE",
    "pointmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
    "normalmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
    "images": lambda v: isinstance(v, (list, tuple)) and all(
        isinstance(x, np.ndarray) and x.ndim == 2 for x in v),
    "vector": lambda v: isinstance(v, np.ndarray) and v.shape == (3,),
    "pairs": lambda v: True,
    "matrix": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "roots": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "c",
    # cpoints = 複素 1-D の**順序つき**点列(閉曲線)。roots と同じ形だが別プール:
    # roots は順序に意味の無い解集合で、周回積分・巻き数は順序と閉性が答えそのもの
    "cpoints": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "c",
    # cscalar = 複素スカラ(∮f dz / f(w) / 留数)。measurement(実スカラのみ)へ
    # 混ぜると下流の実数 op が生 TypeError で落ちるため型を分ける
    "cscalar": lambda v: isinstance(v, complex) and not isinstance(v, np.ndarray),
    # lightfield = 4-D (V, U, H, W)。角度 2 軸 × 空間 2 軸
    "lightfield": lambda v: isinstance(v, np.ndarray) and v.ndim == 4,
    # score = ピークを持つ相関 volume。voxel と同じ 3-D だが、意味は「マッチの
    # 良さ」でありサブボクセル精緻化の入力になる
    "score": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    # counts = 時間 bin で添字づけられた**非負**の光子カウント列。既存 signal と
    # 構造は同じだが、signal プール(正弦波 = 負値あり)を渡すと必ず CONTRACT に
    # なり photon 族が一度も実行されない(実測 7/17 未到達)。jones/stokes と同じ判断
    "counts": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "f" and v.size >= 2 and (v >= 0.0).all(),
    # countrate = SPAD の計数レート列 [Hz]。counts と形は同じだが値域が 7 桁違い、
    # counts を渡すとデッドタイム則が恒等写像に潰れて物理が一度も踏まれない
    # (実測: ヒストグラムを渡すと相対変化 1.1e-4、本物のレートなら 33%)
    "countrate": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "f" and v.size >= 1 and (v >= 0.0).all(),
    # histcube = (H, W, T) の到達時刻ヒストグラム。voxel と ndim は同じだが
    # 時間軸が最後という約束が違う(voxel を渡すと黙って間違った深度が出る)
    "histcube": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.shape[2] >= 2 and v.dtype.kind == "f" and (v >= 0.0).all(),
    # jones = Jones ベクトル(長さ 2 固定の complex)。cpoints(輪郭)と形は
    # 同じでも意味が違い、長さが違えば必ず ValueError なので別プール
    "jones": lambda v: isinstance(v, np.ndarray) and v.shape == (2,)
    and v.dtype.kind == "c",
    # stokes = Stokes ベクトル(長さ 4 固定の実、偏光度 <= 1 が物理制約)
    "stokes": lambda v: isinstance(v, np.ndarray) and v.shape == (4,)
    and v.dtype.kind == "f",
}


#: docstring が非有限を明示契約している op(例: esdf は「全自由なら +inf」、
#: register_spin/register_fpfh は「対応なしなら rmse=inf」の文書化済み番兵値、
#: sdf_* は esdf の契約 inf を min/max 代数で厳密伝播 — sdf_ops モジュール docstring)
#: mat_cond は「厳密特異なら inf を返す(raise しない)」を docstring 契約
NONFINITE_BY_CONTRACT = {"esdf", "register_spin", "register_fpfh",
                         "sdf_union", "sdf_intersect", "sdf_subtract",
                         "sdf_smooth_union", "sdf_offset", "mat_cond"
                         } | NONFINITE_BY_CONTRACT_OPTICS

#: pool へ入れる 1 産物の上限バイト数。拡大系 op(upsample/uncrop/resize)の連鎖で
#: 体積が指数増殖し、後段の全 op が実質ハングする(wave-4 実測: ~34GB の voxel に
#: r=1 の morph_blackhat3d が 20 分+スラッシング)。上限超過は黙って捨てず
#: GROWTH として記録する(silent cap 禁止)。128MB ≈ float32 で 320³ 相当。
MAX_POOL_BYTES = 128 * 2 ** 20


def _nbytes(val):
    """産物の概算バイト数(ndarray は厳密、入れ物は再帰和、その他 0)。"""
    if isinstance(val, np.ndarray):
        return val.nbytes
    if isinstance(val, (list, tuple)):
        return sum(_nbytes(v) for v in val)
    if isinstance(val, dict):
        return sum(_nbytes(v) for v in val.values())
    return 0


def _classify(exc):
    if isinstance(exc, ValueError):
        return "CONTRACT"
    if isinstance(exc, (ImportError, ModuleNotFoundError, NotImplementedError)):
        return "OPTIONAL"      # optional 依存の明示エラーは白
    return "SUSPECT"


def _finite_ok(val):
    """ndarray(を含む入れ物)に NaN/Inf が無いか。数値以外は不問。"""
    if isinstance(val, np.ndarray):
        return val.dtype.kind not in "fc" or bool(np.isfinite(val).all())
    if isinstance(val, (list, tuple)):
        return all(_finite_ok(v) for v in val)
    if isinstance(val, dict):
        return all(_finite_ok(v) for v in val.values())
    if isinstance(val, float):
        return np.isfinite(val)
    return True


def _step_rng(chain_seed, name, occurrence, fallback):
    """引数束縛用の**位置に依存しない**乱数源。

    候補抽選(連鎖 rng)と引数抽選を分けるのが肝: 連鎖 rng は「次にどの op を
    引くか」で消費量が変わるため、op を 1 つ外すと以降の抽選が全部ずれ、
    最小化の再走が原理的に再現しなくなる(実測: 再現 48/65)。鍵を
    (連鎖 seed, op 名, その op の出現回数)にすると、**無関係な前段を落としても
    当該 op の引数抽選は不変**になり、pool の中身の違いだけが再現可否を決める
    = 削り込みが本来見たい依存関係そのものになる。
    """
    if chain_seed is None:
        return fallback                    # 旧来の呼び方(再現性を要求しない)
    key = zlib.crc32(name.encode("utf-8"))
    return np.random.default_rng((int(chain_seed) & 0xFFFFFFFF, key, occurrence))


def run_chain(ops, gens, rng, length, log, chain_seed=None, script=None,
              explore=0.0):
    """1 連鎖 = 型付き pool を育てながら op を実行。発見は log に積む。

    *script* に op 名の列を渡すと**その順で強制実行**する(--minimize の再走)。
    型が揃わない step は黙って飛ばす = その短縮では再現しない、と判定される。
    *chain_seed* は findings に載せて再現に使う。
    """
    pool = {}
    for t, g in gens.items():
        pool[t] = [g(rng)]
    trace = []
    occ = {}
    by_name = {o[0]: o for o in ops} if script is not None else None
    # この連鎖が狙う op(決定的: 連鎖固有 seed から引く)。script 再走のときは
    # 狙いを持たない — 再現は与えられた op 列がすべてだから。
    target = None
    if script is None and explore > 0.0 and ops:
        target = ops[int(np.random.default_rng(
            zlib.crc32(b"target|%d" % (chain_seed or 0))).integers(len(ops)))]
    for i in range(len(script) if script is not None else length):
        if script is not None:
            op = by_name.get(script[i])
            if op is None:
                continue
            name, dim, ins, out, fn = op
            if not all((t in pool and pool[t]) or t == "any" for t in ins):
                continue          # 入力型が揃わない = この短縮では到達不能
        else:
            # pool にある型を食える op を候補化
            cands = [o for o in ops
                     if all((t in pool and pool[t]) or t == "any" for t in o[2])]
            if not cands:
                break
            # **狙いを持った拡散**。一様に引くと、候補が数百ある中から特定の op
            # が長さ 6 の枠内で選ばれる確率は低く、実測では 1500 連鎖でも 112 op
            # が「構造的には到達可能なのに一度も引かれない」ままだった。
            #
            # 最初は「まだプールに無い型を産む op を優先する」型空間バイアスを
            # 試したが、**効かなかった**(321 → 322 op、1500 連鎖で +1)。プールは
            # 最初から全生成器型で埋まっているので、優先対象がすぐ尽きるため。
            #
            # そこで **連鎖ごとに目標 op を 1 つ決め、そこへ寄せる**方式にした。
            # 目標は連鎖固有 seed から決めるので chain_seed だけで再現でき、
            # --minimize / --replay の前提を壊さない。1500 連鎖 / 434 op なら
            # 1 op あたり平均 3.5 連鎖が狙ってくれる勘定になる。
            if target is not None and rng.random() < explore:
                hit = [o for o in cands if o[0] == target[0]]
                if hit:
                    cands = hit
                else:
                    # 目標が食う型を**産む** op を優先 = 1 手ぶん近づく
                    want = set(target[2])
                    step = [o for o in cands if o[3] in want]
                    if step:
                        cands = step
            name, dim, ins, out, fn = cands[rng.integers(len(cands))]
        occ[name] = occ.get(name, 0) + 1
        arng = _step_rng(chain_seed, name, occ[name], rng)
        if name in OP_ARG_BUILDERS:
            bound = OP_ARG_BUILDERS[name](pool, arng)
        else:
            data_args = []
            for t in ins:
                src = pool[t] if t != "any" else pool[arng.choice(sorted(pool))]
                data_args.append(src[arng.integers(len(src))])
            bound = _bind_args(name, fn, data_args, arng)
        if bound is None:
            continue
        args, kwargs = bound
        big = sum(_nbytes(a) for a in args)
        if big > 32 * 2 ** 20:
            # 重い入力は実行前に予告(万一のストールでもログだけで犯人が判る)
            print(f"  big-input: {name} ({big / 2**20:.0f} MB)", flush=True)
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — ファザーの本懐
            kind = _classify(exc)
            if kind != "OPTIONAL":
                log.append({"kind": kind, "op": name, "dim": dim,
                            "exc": type(exc).__name__, "msg": str(exc)[:200],
                            "trace": trace + [name], "seed": chain_seed,
                            "tb": traceback.format_exc(limit=3)})
            continue
        dt = time.perf_counter() - t0
        if dt > SLOW_S:
            log.append({"kind": "SLOW", "op": name, "dim": dim, "sec": round(dt, 1),
                        "trace": trace + [name], "seed": chain_seed})
        if name in ADAPTERS:
            result = ADAPTERS[name](result)
        if result is None:
            continue
        if not _finite_ok(result) and name not in NONFINITE_BY_CONTRACT:
            log.append({"kind": "NONFINITE", "op": name, "dim": dim,
                        "trace": trace + [name], "seed": chain_seed})
            continue                      # 毒は pool に入れない
        nb = _nbytes(result)
        if nb > MAX_POOL_BYTES:
            log.append({"kind": "GROWTH", "op": name, "dim": dim,
                        "mb": round(nb / 2 ** 20, 1),
                        "trace": trace + [name], "seed": chain_seed})
            continue                      # 巨大産物は pool に入れない(指数増殖防止)
        check = TYPE_CHECKS.get(out)
        if check is not None and not check(result):
            log.append({"kind": "TYPEMISS", "op": name, "dim": dim,
                        "exc": out, "msg": "declared %r but returned %s%s" % (
                            out, type(result).__name__,
                            getattr(result, "shape", "")),
                        "trace": trace + [name], "seed": chain_seed})
            continue                      # 型の嘘も pool に入れない
        trace.append(name)
        pool.setdefault(out, []).append(result)
    return trace


# --------------------------------------------------------------------------- #
# 収束フェーズ: 発見を「最小再現の連鎖」へ削る(delta debugging)               #
# --------------------------------------------------------------------------- #
#: 署名を作るときにメッセージから消す可変部分。良いエラーメッセージほど
#: 「負の bin が 127 個、最小 -1.176」のように**その実行固有の数**を含むので、
#: 素のメッセージで同一視すると同じ 1 件の問題が実行のたびに別署名になる
#: (実測: photon 族を足した波で署名が 99 → 238 に膨れ、増分のほぼ全部が
#: 「dtof_depth: hist has N negative bin(s) (min -X)」の N と X 違いだった)。
_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")


def signature(finding):
    """findings を同一視する鍵(main の集約と --minimize で同じ定義を使う)。

    メッセージ中の**数値を伏せて**から比べる。伏せないと、実行ごとに違う数を
    含むメッセージが別々の署名になり、収束(拡散 → 署名でまとめる)が機能しない。
    """
    msg = _NUM_RE.sub("#", finding.get("msg", ""))
    return (finding["kind"], finding["op"], finding.get("exc", ""), msg[:80])


def reproduces(ops, gens, script, seed, target):
    """*script* を強制実行して *target* 署名が再現するか。"""
    log = []
    run_chain(ops, gens, np.random.default_rng(seed), 0, log,
              chain_seed=seed, script=script)
    return any(signature(f) == target for f in log)


def minimize_finding(ops, gens, finding, verbose=True):
    """1 件の発見を最小の op 列へ削る。→ (script or None, 再現したか)。

    貪欲な delta debugging: 末尾(当該 op)は残したまま、前段を 1 つずつ外して
    署名が再現し続けるかを試す。**再現しなかった場合は正直に None を返す**
    (この段階で「短縮できた」と嘘をつくと、その後の推測パッチを誘発する)。
    """
    target = signature(finding)
    seed = finding.get("seed")
    script = list(finding.get("trace") or [])
    if seed is None or not script:
        return None, False
    if not reproduces(ops, gens, script, seed, target):
        return None, False              # trace 単独では再現しない(honest)
    i = 0
    while i < len(script) - 1:          # 末尾 = 当該 op は落とさない
        trial = script[:i] + script[i + 1:]
        if reproduces(ops, gens, trial, seed, target):
            script = trial              # 外しても再現 = その op は無関係
            if verbose:
                print(f"    - drop {len(script) + 1}->{len(script)} ops", flush=True)
        else:
            i += 1
    return script, True


def minimize_file(path, ops, gens, only=None):
    """署名 jsonl の各行を最小化し、再現スクリプトを書き出す。"""
    findings = [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()]
    if only:
        findings = [f for f in findings if f.get("op") == only]
    print(f"== 最小化 {len(findings)} 署名 <- {path}")
    out_lines, n_ok = [], 0
    for f in findings:
        head = f"[{f['kind']}] {f['op']}"
        script, ok = minimize_finding(ops, gens, f, verbose=False)
        if not ok:
            print(f"  {head}: 再現せず(seed/trace 不足 or 非決定的)— 短縮なし")
            out_lines.append(dict(f, minimal=None, reproduced=False))
            continue
        n_ok += 1
        print(f"  {head}: {len(f.get('trace') or [])} -> {len(script)} ops  {script}")
        out_lines.append(dict(f, minimal=script, reproduced=True))
    dst = os.path.splitext(path)[0] + "_minimal.jsonl"
    with open(dst, "w", encoding="utf-8") as fh:
        for rec in out_lines:
            rec.pop("tb", None)
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    print(f"== 再現できた {n_ok}/{len(findings)} 件 -> {dst}")
    if n_ok:
        print("== 再走コマンド例:")
        for rec in out_lines[:3]:
            if rec.get("minimal"):
                print(f"   py -3.11 tools/chain_fuzz.py --replay {rec['seed']} "
                      f"--script {','.join(rec['minimal'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", type=int, default=200)
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "chain_fuzz.jsonl"))
    ap.add_argument("--minimize", metavar="JSONL",
                    help="署名 jsonl を読み、各発見を最小の op 列へ削る")
    ap.add_argument("--only", metavar="OP", help="--minimize をこの op に絞る")
    ap.add_argument("--replay", type=int, metavar="SEED",
                    help="--script を指定 seed で強制実行(最小再現の確認)")
    ap.add_argument("--script", help="--replay で実行する op 名のカンマ区切り")
    ap.add_argument("--explore", type=float, default=0.5,
                    help="型空間の探索バイアス [0,1]。まだプールに無い型を"
                         "産む op を優先する確率。0 で一様(旧挙動)")
    ap.add_argument("--coverage-out", metavar="JSON",
                    help="どの op が走り、どの op が一度も走らなかったかを書き出す。"
                         "「304/417」という数だけでは、残る 113 が頑健なのか"
                         "そもそも到達不能なのかが区別できない")
    args = ap.parse_args()
    if args.minimize:
        minimize_file(args.minimize, catalog(), make_generators(), only=args.only)
        return 0
    if args.replay is not None:
        if not args.script:
            print("--replay には --script が要る", file=sys.stderr)
            return 2
        script = [s for s in args.script.split(",") if s]
        log = []
        run_chain(catalog(), make_generators(), np.random.default_rng(args.replay),
                  0, log, chain_seed=args.replay, script=script)
        print(f"== replay seed={args.replay} script={script}")
        for f in log:
            print(f"  [{f['kind']}] {f['op']}: {f.get('exc', '')} {f.get('msg', '')[:120]}")
        if not log:
            print("  発見なし(この seed/script では再現しない)")
        return 0
    ops = catalog()
    gens = make_generators()
    log = []
    used = set()
    t0 = time.perf_counter()
    for i in range(args.chains):
        # 連鎖固有 seed: 後から i 番目だけを正確に再走できる(--minimize の前提)
        chain_seed = args.seed * 1_000_003 + i
        trace = run_chain(ops, gens, np.random.default_rng(chain_seed),
                          args.length, log, chain_seed=chain_seed,
                          explore=args.explore)
        used.update(trace)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{args.chains} chains, findings {len(log)}, "
                  f"ops covered {len(used)}", flush=True)
    wall = time.perf_counter() - t0

    # 収束: 署名(kind, op, exc)でまとめる
    sig = {}
    for f in log:
        key = signature(f)
        sig.setdefault(key, {"n": 0, "sample": f})
        sig[key]["n"] += 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for key, v in sorted(sig.items()):
            rec = dict(v["sample"])
            rec["count"] = v["n"]
            rec.pop("tb", None)
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    kinds = {}
    for f in log:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    print(f"\n== 拡散 {args.chains} 連鎖 x len {args.length}(seed {args.seed}, "
          f"{wall:.0f}s)")
    print(f"== op カバレッジ: {len(used)}/{len(ops)}")
    # 未到達を族ごとに出す。到達 0 の族は「頑健だから発見が無い」のではなく
    # 「そもそも連鎖が入ってこない」= 狭い sort の症状で、意味がまるで違う
    by_family = {}
    for name, fam, _ins, _out, _fn in ops:
        hit, miss = by_family.setdefault(fam, ([], []))
        (hit if name in used else miss).append(name)
    print("== 族ごとの到達: " + "  ".join(
        f"{fam} {len(h)}/{len(h) + len(m)}"
        for fam, (h, m) in sorted(by_family.items())))
    if args.coverage_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.coverage_out)), exist_ok=True)
        with open(args.coverage_out, "w", encoding="utf-8") as fh:
            json.dump({"total": len(ops), "covered": sorted(used),
                       "uncovered": sorted(n for n, *_ in ops if n not in used),
                       "by_family": {f: {"covered": sorted(h), "uncovered": sorted(m)}
                                     for f, (h, m) in sorted(by_family.items())}},
                      fh, ensure_ascii=False, indent=1)
        print(f"== カバレッジ内訳 -> {args.coverage_out}")
    print(f"== 発見(生): {kinds} / 署名数 {len(sig)}")
    print(f"== 署名一覧 -> {args.out}")
    order = {"SUSPECT": 0, "NONFINITE": 1, "SLOW": 2, "CONTRACT": 3}
    for key, v in sorted(sig.items(), key=lambda kv: (order.get(kv[0][0], 9), -kv[1]["n"])):
        kind, op, exc, msg = key
        if kind == "CONTRACT":
            continue                      # 白は件数のみ(ファイルには残す)
        print(f"  [{kind}] {op} x{v['n']} {exc}: {msg}")
    if len(sig) > sum(1 for k in sig if k[0] == "CONTRACT"):
        print("\n== 収束(最小再現): py -3.11 tools/chain_fuzz.py "
              f"--minimize {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
