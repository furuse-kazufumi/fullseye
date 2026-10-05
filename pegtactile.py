# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegtactile — ペグ挿入を 2 本指の指先の弾性膜で読む: 膜のせん断から接触レンチ、Whitney の接触状態、壁の摩擦、手首剛性まで(2026-10-05)。

物理シミュ × Fullseye 系列(柔らかい手首のペグ挿入 :mod:`pegsim` → 失敗の分類 :mod:`pegfail`)と、視触覚の 3 本(:mod:`tacsim` 押し込み、
:mod:`tacslip` せん断、:mod:`tactorque` ねじり)を 1 本に繋ぐ集大成。2 本指の指先に弾性膜を付け、ペグが穴から受ける接触レンチを
**膜の像だけ**から復元し、Whitney の接触状態(無接触 / 面取り / 一点 / 二点、止まった時のくさび / かじり)を学習なしの規則で当てる。
同じ挿入で手首剛性 k を「手首カメラのたわみ × 触覚の力」から同定し、ペグの形の対称性と装置の対称性を同変性の門で測る。

外から来る真値:
  * **定理**: Whitney 1982(原著は有料で未読。式は著者本人の MIT OCW 2.875 Class 3 スライド本文、pegsim と同じ出典)の二点接触の深さ
    l₂(θ) = (2R − r(cosθ + secθ))/tanθ(:func:`pegsim.two_point_depth`)とくさびの境目 θ = c/μ。閉形式の接触レンチ
    (:func:`whitney_wrench`、平面の準静的な釣り合い + 下へ滑る Coulomb 摩擦)を真値つきの合成に使う。
  * **閉形式の接触力学**(K. L. Johnson, *Contact Mechanics*, CUP 1985): Hertz(:mod:`tacsim`)、Cattaneo–Mindlin の部分滑りと
    Cerruti 核(:mod:`tacslip`)、無滑りねじり(:mod:`tactorque`)、Hertz 接触のねじりの全滑りトルク (3π/16)μPa(Lubkin 1951)。
  * **群の作用**: 回した形・回した場面の答えは同じだけ回る(:func:`equivariance_check`)。
  * **物理エンジン(mujoco 層、facade のみ)**: MuJoCo の接触点・世界系の接触力・手首の力・トルクセンサ・手首ばねの設定値(k_t, k_r)。

膜は MuJoCo に無い(正直に): ペグは手首の剛体で、指先パッドの力は「露光平均の接触レンチ + 重力」を 2 つのパッドへ静力学で配る写像で作る
(:func:`peg_wrench_to_pad_loads`)。法線は把持力 G₀ ∓ F_x/2(対称に分ける仮定、不静定)、F_y・F_z はせん断の共通成分、M_y・M_z は
せん断の偶力(指の間隔 2w)、M_x(指の軸まわり)は各パッドのねじり。ドーム状パッドは転がりに抵抗しないので、パッド面内の軸まわりの
モーメントは偶力で運ぶ。合成と逆算は同じ閉形式族なので、膜の模型の誤り(有限厚、大変形)はここでは見えない(:mod:`tacslip` の
有限要素の比較が担当)。

numpy 層(台帳 opsdrive ``pegtactile``、19 op):
  パッドと静力学 :func:`pad_params` / :func:`pad_context` / :func:`peg_wrench_to_pad_loads` / :func:`pad_loads_to_peg_wrench` /
  :func:`pad_shear_asymmetry`;膜の合成と読み :func:`pad_marker_displacement` / :func:`pad_tactile_frame` / :func:`pad_tactile_read`;
  接触状態 :func:`contact_candidates` / :func:`contact_state_from_wrench` / :func:`two_point_forces` / :func:`whitney_wrench` /
  :func:`friction_from_single_contact` / :func:`stall_verdict`;手首 :func:`wrist_stiffness_fit` / :func:`wrist_deflection_from_rgbd`;
  対称性 :func:`symmetric_peg_shape` / :func:`symmetry_order_contour` / :func:`equivariance_check`。
mujoco 層(facade のみ、台帳の外): :func:`pegtactile_episode_run`(露光平均つきの挿入 1 走行)/ :func:`pegtactile_prefetch`(全フレームの
  膜の合成と読みを並列で先に)/ :func:`pegtactile_process_episode`(2 段の後処理: k̂ の同定 → 姿勢の補正 → 接触状態)/
  :func:`pegtactile_cutaway_xml`(穴の断面を見る描画専用の MJCF 文字列)。

踏んで直した罠(PoC の門に固定): 規則格子のマーカーは重心の pixel-locking が場全体の共通モードになり、せん断ゼロでも偽のせん断が出る
(印刷のばらつき程度のジッタで消える)。向きを先に決めて 1 成分で当てると偏る(:func:`tacslip.mindlin_fit_vector` の 2 係数)。半径ビンの
接触半径は P̂ の傾きを狂わせ 2 パッドの差 F_x で致命的(:func:`tacsim.contact_radius_fit_pixelwise`)。瞬間の接触力は撃力なので露光で
平均する。手首の z 圧縮はカメラに見えない(k̂ と触覚の F_z で補う)。くさびの境目 θ = c/μ では二点のレンチが口の一点と区別できない
(レンチだけの規則の原理的な死角、Whitney の幾何で解く)。

規約: 長さ m、力 N、角 rad。穴の口の面 z = 0、穴の軸 = 世界 z、``depth`` は口の面からの先端深さ。グリッパ系 = 手首 body の軸
(x = パッドの法線、z = ペグ軸の上向き)。パッド R は +x 側、L は −x 側。パッド像の座標 (u, v) = グリッパの (y, z)。``q`` は**膜が受ける**
せん断(= ペグがパッドから受けるせん断の逆向き)。画素座標は (x, y) = (列, 行)、輪郭は (row, col)。
"""
from __future__ import annotations

import math

import numpy as np

import pegsim as PS
import tacsim as T
import tacslip as S
import tactorque as TQ

__all__ = [
    "SHAPES", "CONTACT_STATES",
    "pad_params", "pad_context", "peg_wrench_to_pad_loads", "pad_loads_to_peg_wrench", "pad_shear_asymmetry",
    "pad_marker_displacement", "pad_tactile_frame", "pad_tactile_read",
    "contact_candidates", "contact_state_from_wrench", "two_point_forces", "whitney_wrench", "friction_from_single_contact",
    "stall_verdict", "wrist_stiffness_fit", "wrist_deflection_from_rgbd",
    "symmetric_peg_shape", "symmetry_order_contour", "equivariance_check",
    # mujoco が要る(facade のみ、台帳の外)。cutaway_xml と process_episode は numpy だけで動くが、mujoco の走行の付属品
    "pegtactile_episode_run", "pegtactile_prefetch", "pegtactile_process_episode", "pegtactile_cutaway_xml",
]

#: :func:`symmetric_peg_shape` が描ける断面(n 回対称の次数 0 / 3 / 4 / 6 / 1)
SHAPES = ("circle", "triangle", "square", "hexagon", "keyed")
#: :func:`contact_state_from_wrench` の語彙
CONTACT_STATES = ("none", "chamfer", "one_point", "two_point", "unknown")

_AMB, _ELEV = 0.03, 55.0
_PAD_KEYS = ("R", "E", "nu", "mu", "grip", "w", "grasp_below_top", "fov", "n", "pitch", "Es", "G", "marker_pitch", "pitch_px",
             "marker_r_px", "dark", "peg_mass", "com_below_top", "a_grip")


def _vec(x, n: int, name: str) -> np.ndarray:
    v = np.asarray(x, np.float64).reshape(-1)
    if v.shape != (n,) or not np.all(np.isfinite(v)):
        raise ValueError("%s must be a finite %d-vector, got %r" % (name, n, x))
    return v


def _pad(pad) -> dict:
    if not isinstance(pad, dict) or any(k not in pad for k in _PAD_KEYS):
        raise ValueError("pad must be the dict from pad_params()")
    return pad


def _rot(phi: float) -> np.ndarray:
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[c, -s], [s, c]])


# ======================================================================================================================
# 1. パッドの寸法と、接触レンチ ⇄ パッド荷重の静力学
def pad_params(R: float = 20.0e-3, E: float = 3.0e6, nu: float = 0.48, mu: float = 1.0, grip: float = 4.0, w: float = 5.0e-3,
               grasp_below_top: float = 8.0e-3, fov: float = 16.0e-3, n: int = 256, marker_pitch: float = 0.5e-3,
               marker_r_px: float = 2.5, dark: float = 0.85, peg_mass: float = 0.04, com_below_top: float = 14.25e-3) -> dict:
    """指先パッドの表: ドームの半径 R、ゲルの E・ν、パッドとペグの摩擦 μ、把持力 G₀ [N]、指の半間隔 w(ペグの平取りの半幅)、
    把持点のペグ上端からの距離、膜カメラの視野と画素数、マーカー(ピッチ・半径 [px]・濃さ)、ペグの質量と重心(pegfail の既定と同じ)。

    寸法の根拠: G₀ = 4 N で a ≈ 2.5 mm(a/R 0.13、Hertz の範囲)、視野 16 mm ≥ 5a(tacsim の窓の条件)、マーカー 0.5 mm = 8 px。
    返りに Hertz の複合弾性率 ``Es``・せん断弾性率 ``G``・画素ピッチ ``pitch``・把持だけの接触半径 ``a_grip`` を足す。
    **Raises** ValueError: 正であるべき量が正でない、ν が [0, 0.5] の外、n < 64、マーカー間隔が 4 px 未満、
    把持力の 1.5 倍で視野が 5a に足りない。"""
    vals = dict(R=R, E=E, mu=mu, grip=grip, w=w, fov=fov, marker_pitch=marker_pitch, marker_r_px=marker_r_px, dark=dark,
                peg_mass=peg_mass, grasp_below_top=grasp_below_top, com_below_top=com_below_top)
    for k, v in vals.items():
        if not (float(v) > 0.0 and math.isfinite(float(v))):
            raise ValueError("pad_params: %s must be finite and > 0, got %r" % (k, v))
    if not (0.0 <= float(nu) <= 0.5):
        raise ValueError("pad_params: nu must be in [0, 0.5], got %r" % (nu,))
    if int(n) < 64:
        raise ValueError("pad_params: n must be >= 64, got %r" % (n,))
    pitch = float(fov) / int(n)
    if float(marker_pitch) / pitch < 4.0:
        raise ValueError("pad_params: marker pitch %.3g m is < 4 px at %d px over %.3g m" % (marker_pitch, n, fov))
    Es = T.combined_modulus(float(E), float(nu))
    a0 = T.hertz_sphere(float(grip), float(R), Es)["a"]
    if float(fov) < 5.0 * a0 * (1.5 ** (1.0 / 3.0)):
        raise ValueError("pad_params: fov %.4g m is < 5a at 1.5 x grip (a = %.4g m)" % (fov, a0))
    G = float(E) / (2.0 * (1.0 + float(nu)))
    return {"R": float(R), "E": float(E), "nu": float(nu), "mu": float(mu), "grip": float(grip), "w": float(w),
            "grasp_below_top": float(grasp_below_top), "fov": float(fov), "n": int(n), "pitch": pitch, "Es": Es, "G": G,
            "marker_pitch": float(marker_pitch), "pitch_px": float(marker_pitch) / pitch, "marker_r_px": float(marker_r_px),
            "dark": float(dark), "peg_mass": float(peg_mass), "com_below_top": float(com_below_top), "a_grip": a0}


def pad_context(pad: dict, jitter_px: float = 0.5, seed: int = 7) -> dict:
    """膜の合成と読みで 1 回だけ作る道具: 画素中心の格子 (X, Y)、Cerruti 核、3 色の光源、無荷重の膜の背景とマーカーの基準像。

    マーカーは ``jitter_px`` の一様ジッタで位相を散らす(印刷のばらつき程度)。**規則格子(0 px)は全マーカーが同じ副画素位相なので、
    重心の pixel-locking が場全体の共通モードになり、せん断ゼロでも偽のせん断が出る**(PoC の門で 11 mN → 0.9 mN)。
    ``seed`` はジッタの乱数。返りの ``_model_cache``・``_sr_cache`` は読みの内部キャッシュ。**Raises** ValueError: jitter < 0。"""
    pad = _pad(pad)
    if not (float(jitter_px) >= 0.0):
        raise ValueError("pad_context: jitter_px must be >= 0")
    n, fov, pitch = pad["n"], pad["fov"], pad["pitch"]
    X, Y, r, _ = T._grid(n, fov)
    kern = S.cerruti_kernel(n, pitch, pad["G"], pad["nu"])
    lights = T.membrane_lights(_ELEV)
    flat_n = np.zeros((n, n, 3))
    flat_n[..., 2] = 1.0
    bg_flat = T.membrane_render_rgb(flat_n, lights, ambient=_AMB)
    pts = S.membrane_markers(n, pad["pitch_px"], 0.3, 0.6)
    if float(jitter_px) > 0:
        pts = pts + np.random.default_rng(int(seed)).uniform(-float(jitter_px), float(jitter_px), pts.shape)
    m_ref = S.marker_image(S.membrane_render_markers(bg_flat, pts, pad["marker_r_px"], pad["dark"]), bg_flat)
    return {"X": X, "Y": Y, "r": r, "kern": kern, "lights": lights, "bg_flat": bg_flat, "pts_flat": pts, "m_ref": m_ref,
            "c0": (n - 1) / 2.0, "jitter_px": float(jitter_px), "_model_cache": {}, "_sr_cache": {}}


_CTX_CACHE: dict = {}


def _ctx_for(pad: dict, ctx):
    """ctx が無ければ pad ごとに 1 回だけ作って使い回す(op として単独で呼ばれたとき用)。"""
    if ctx is not None:
        if not isinstance(ctx, dict) or "pts_flat" not in ctx:
            raise ValueError("ctx must be the dict from pad_context()")
        return ctx
    key = tuple((k, pad[k]) for k in _PAD_KEYS)
    if key not in _CTX_CACHE:
        if len(_CTX_CACHE) >= 4:
            _CTX_CACHE.clear()
        _CTX_CACHE[key] = pad_context(pad)
    return _CTX_CACHE[key]


def peg_wrench_to_pad_loads(F_pad, M_pad, pad: dict) -> dict:
    """2 つのパッドがペグに加えるレンチ(グリッパ系、把持点まわり)→ 各パッドの (法線力 P、膜が受けるせん断 q = (q_u, q_v))。

    釣り合い(導出): パッド R(+x)はペグに −N_R x̂ と T_R、L(−x)は +N_L x̂ と T_L。F_x = N_L − N_R、F_y = T_Ry + T_Ly、
    F_z = T_Rz + T_Lz、M_y = −w(T_Rz − T_Lz)、M_z = w(T_Ry − T_Ly)、M_x = ねじり(半分ずつ)。法線は把持力で N = G₀ ∓ F_x/2。
    返り: ``R``・``L``(各 ``P``・``q``(膜が受ける = −T)・``slip_ratio`` = |q|/(μP)・``torsion``(膜が受けるねじり)・``torsion_ratio``
    = |ねじり| / 全滑りトルク (3π/16)μPa)、``torsion``(ペグへのねじりの半分 M_x/2)、``ok``(両方 |q| < μP)、``min_margin``、
    ``torsion_ok``。滑り(|q| ≥ μP)とねじりの全滑りは**印**で返す(例外にしない: 合成は比例載荷・無滑りねじりの模型)。
    **Raises** ValueError: 形が (3,) でない・有限でない、どちらかのパッドの法線力が 0 以下(パッドが離れる = この写像の外。fail-closed)。"""
    pad = _pad(pad)
    F = _vec(F_pad, 3, "peg_wrench_to_pad_loads: F_pad")
    M = _vec(M_pad, 3, "peg_wrench_to_pad_loads: M_pad")
    G0, w, mu = pad["grip"], pad["w"], pad["mu"]
    NR, NL = G0 - F[0] / 2.0, G0 + F[0] / 2.0
    if not (NR > 0.0 and NL > 0.0):
        raise ValueError("peg_wrench_to_pad_loads: a pad loses contact (N_R=%.4g, N_L=%.4g N); grip %.3g N too small for F_x=%.4g"
                         % (NR, NL, G0, F[0]))
    TRz, TLz = F[2] / 2.0 - M[1] / (2.0 * w), F[2] / 2.0 + M[1] / (2.0 * w)
    TRy, TLy = F[1] / 2.0 + M[2] / (2.0 * w), F[1] / 2.0 - M[2] / (2.0 * w)
    qR, qL = -np.array([TRy, TRz]), -np.array([TLy, TLz])
    sR, sL = float(np.hypot(*qR) / (mu * NR)), float(np.hypot(*qL) / (mu * NL))
    tau = float(M[0]) / 2.0

    def cap(P_):
        return (3.0 * math.pi / 16.0) * mu * P_ * T.hertz_sphere(P_, pad["R"], pad["Es"])["a"]
    tR, tL = abs(tau) / cap(NR), abs(tau) / cap(NL)
    return {"R": {"P": float(NR), "q": qR, "slip_ratio": sR, "torsion": -tau, "torsion_ratio": tR},
            "L": {"P": float(NL), "q": qL, "slip_ratio": sL, "torsion": -tau, "torsion_ratio": tL},
            "torsion": tau, "ok": bool(sR < 1.0 and sL < 1.0), "min_margin": float(1.0 - max(sR, sL)),
            "torsion_ok": bool(max(tR, tL) < 1.0)}


def pad_loads_to_peg_wrench(PR: float, qR, PL: float, qL, pad: dict, torsion: float = 0.0) -> dict:
    """:func:`peg_wrench_to_pad_loads` の逆: 2 パッドの (P, q) と膜が受けるねじり(パッド 1 枚あたり、グリッパ x まわり)→ パッドが
    ペグに加えるレンチ(グリッパ系、把持点まわり)と把持力。ペグへのねじり = −2·torsion。返り ``F``・``M``(3,)、``grip`` = (N_R + N_L)/2。
    **Raises** ValueError: q が有限の 2 成分でない、P か torsion が有限でない。"""
    pad = _pad(pad)
    qR = _vec(qR, 2, "pad_loads_to_peg_wrench: qR")
    qL = _vec(qL, 2, "pad_loads_to_peg_wrench: qL")
    PR, PL, torsion = float(PR), float(PL), float(torsion)
    if not (math.isfinite(PR) and math.isfinite(PL) and math.isfinite(torsion)):
        raise ValueError("pad_loads_to_peg_wrench: PR, PL and torsion must be finite")
    w = pad["w"]
    TR, TL = -qR, -qL
    F = np.array([PL - PR, TR[0] + TL[0], TR[1] + TL[1]])
    M = np.array([-2.0 * torsion, -w * (TR[1] - TL[1]), w * (TR[0] - TL[0])])
    return {"F": F, "M": M, "grip": 0.5 * (PR + PL)}


def pad_shear_asymmetry(qR, qL) -> dict:
    """2 パッドの膜のせん断を共通成分(= 軸方向の力、F_z/2 の向き)と差分(= 偶力、M/(2w))に分ける: 共通 = (q_R + q_L)/2、
    差分 = (q_R − q_L)/2。``ratio_v`` = |差分_v| / (|共通_v| + |差分_v|)(0 = 同じ向き、1 = 純粋な偶力)、``opposite_v`` = v 成分の
    符号が左右で逆か。**Raises** ValueError: 有限の 2 成分でない。"""
    qR = _vec(qR, 2, "pad_shear_asymmetry: qR")
    qL = _vec(qL, 2, "pad_shear_asymmetry: qL")
    com, dif = 0.5 * (qR + qL), 0.5 * (qR - qL)
    den = abs(com[1]) + abs(dif[1])
    return {"common": com, "diff": dif, "ratio_v": float(abs(dif[1]) / den) if den > 0 else 0.0,
            "opposite_v": bool(qR[1] * qL[1] < 0.0)}


# ======================================================================================================================
# 2. 膜の合成と逆算(tacsim + tacslip + tactorque を被験者として、向きを持つせん断とねじりへ)
def pad_marker_displacement(P: float, q_uv, pad: dict, ctx=None, pts=None, torsion: float = 0.0) -> dict:
    """膜の表面変位をマーカー位置で(閉形式 + Cerruti 畳み込み): 向き φ のせん断 |q| は x 向きの Mindlin 場を φ だけ回したもの
    u(p) = R(φ) u_x(R(−φ)p)(核は等方な半空間なので回転で閉じる)、法線荷重の半径変位 ūr(Johnson 式 3.41b)と無滑りねじりの場
    (:func:`tactorque.torsion_stick_field`)を足す。``pts`` はマーカー中心(px、省略時は ``ctx`` の基準位置)。返り ``u_m``(N, 2)[m]、
    ``hz``・``mp``(Hertz と Mindlin の表)、``phi``・``Q``・``torsion``。全滑り(|q| ≥ μP)は ``mp['slipping']`` の印(場は c = 0)。
    **Raises** ValueError: P ≤ 0(パッドが離れている)、q が有限の 2 成分でない。"""
    pad = _pad(pad)
    ctx = _ctx_for(pad, ctx)
    if not (float(P) > 0.0 and math.isfinite(float(P))):
        raise ValueError("pad_marker_displacement: P must be finite and > 0 (pad not in contact), got %r" % (P,))
    q = _vec(q_uv, 2, "pad_marker_displacement: q_uv")
    pts = ctx["pts_flat"] if pts is None else np.asarray(pts, np.float64)
    hz = T.hertz_sphere(float(P), pad["R"], pad["Es"])
    Q = float(np.hypot(*q))
    phi = math.atan2(q[1], q[0]) if Q > 0 else 0.0
    mp = S.mindlin_partial_slip(Q, hz, pad["mu"], pad["G"], pad["nu"])
    c0, pitch = ctx["c0"], pad["pitch"]
    d = pts - c0
    u = np.zeros_like(d)
    if Q > 0:
        trac = S.mindlin_traction(ctx["r"], mp)
        f = S.cerruti_surface_displacement(trac, ctx["kern"])
        dp = d @ _rot(-phi).T + c0
        u = np.column_stack([S._sample(f["ux"], dp), S._sample(f["uy"], dp)]) @ _rot(phi).T
    if float(torsion) != 0.0:
        tf = TQ.torsion_stick_field(ctx["X"], ctx["Y"], hz["a"], float(torsion), ctx["kern"], pad["G"])
        u = u + np.column_stack([S._sample(tf["ux"], pts), S._sample(tf["uy"], pts)])
    rr = np.hypot(d[:, 0], d[:, 1])
    ur = S.hertz_surface_ur(rr * pitch, hz["a"], hz["p0"], pad["G"], pad["nu"])
    dirn = d / np.maximum(rr[:, None], 1e-12)
    u = u + ur[:, None] * dirn
    return {"u_m": u, "hz": hz, "mp": mp, "phi": phi, "Q": Q, "torsion": float(torsion)}


def pad_tactile_frame(P: float, q_uv, pad: dict, ctx=None, noise: float = 0.0, seed: int = 0, torsion: float = 0.0) -> dict:
    """パッド 1 枚の合成像: Hertz 押し込みの陰影(:func:`tacsim.membrane_render_rgb`)+ 変位で中心を移したマーカー
    (:func:`tacslip.membrane_render_markers`、補間で歪めない)。``noise`` は画素の正規雑音の σ。
    返り ``rgb``(マーカー入り、(n, n, 3))、``shading``(マーカー無し = 力の読み取り用、実機はマーカーの除去が要る)、``pts``
    (マーカー中心の真値 [px])、``truth``(P・q・φ・Q・c/a・滑りの印・a・ねじり)。**Raises** ValueError: P ≤ 0、noise < 0。"""
    pad = _pad(pad)
    ctx = _ctx_for(pad, ctx)
    if not (float(noise) >= 0.0):
        raise ValueError("pad_tactile_frame: noise must be >= 0")
    disp = pad_marker_displacement(P, q_uv, pad, ctx, torsion=torsion)
    ind = T.membrane_indent_sphere(disp["hz"], pad["n"], pad["fov"])
    shading = T.membrane_render_rgb(ind["normals"], ctx["lights"], ambient=_AMB)
    pts = ctx["pts_flat"] + disp["u_m"] / pad["pitch"]
    rgb = S.membrane_render_markers(shading, pts, pad["marker_r_px"], pad["dark"])
    if float(noise) > 0:
        rng = np.random.default_rng(int(seed))
        shading = shading + rng.normal(0.0, float(noise), shading.shape)
        rgb = rgb + rng.normal(0.0, float(noise), rgb.shape)
    return {"rgb": rgb, "shading": shading, "pts": pts,
            "truth": {"P": float(P), "q": np.asarray(q_uv, np.float64).reshape(2), "phi": disp["phi"], "Q": disp["Q"],
                      "c_over_a": disp["mp"]["c_over_a"], "slipping": disp["mp"]["slipping"], "a": disp["hz"]["a"],
                      "torsion": float(torsion)}}


def _model_for(pad, ctx, a_hat, hz):
    cache = ctx.setdefault("_model_cache", {})
    key = round(a_hat / pad["pitch"] * 50.0)
    if key not in cache:
        if len(cache) > 64:
            cache.clear()
        cache[key] = S.mindlin_model(hz, ctx["X"], ctx["Y"], ctx["kern"], pad["G"], pad["nu"])
    return cache[key]


def pad_tactile_read(frame: dict, pad: dict, ctx=None, track=None, pixelwise: bool = True) -> dict:
    """パッド 1 枚の像 → (P̂, q̂, ねじり)。

    P̂ = 陰影 → photometric の法線(:func:`tacsim.membrane_recover`)→ 接触半径(中心は既知 = パッド中央;``pixelwise`` なら
    :func:`tacsim.contact_radius_fit_pixelwise`、偽ならビン版 :func:`tacsim.contact_radius_fit` = 罠の対照)→ :func:`tacsim.hertz_force`。
    q̂ = マーカー追跡(:func:`tacslip.marker_track`、``track`` で渡せば省く)→ 法線荷重の ūr(P̂ から閉形式)を引く → 2 成分の Mindlin
    当てはめ(:func:`tacslip.mindlin_fit_vector`)。ねじり = 当てはめたせん断場を引いた残りに、固着核(r < 0.6 â)で剛体回転
    (:func:`tactorque.rigid_rotation_fit`)→ M = (16Gâ³/3)ω(Reissner–Sagoci)。第 2 実装 ``Q_stick`` = 固着核の一様変位 δ̂ を
    Mindlin の δx 式で逆に解いた値(μ は較正値)。返り ``P``・``a``・``q``(2,)・``Q``・``phi``・``torsion``・``c_over_a``・``Q_stick``・
    ``matched``・``rms_px``(当てはめの残差)・``track``。**Raises** ValueError: frame に ``rgb``・``shading`` が無い、追跡できたマーカーが 3 未満。"""
    pad = _pad(pad)
    ctx = _ctx_for(pad, ctx)
    if not isinstance(frame, dict) or "rgb" not in frame or "shading" not in frame:
        raise ValueError("pad_tactile_read: frame must be the dict from pad_tactile_frame (needs 'rgb' and 'shading')")
    rec = T.membrane_recover(frame["shading"], ctx["lights"], pad["pitch"], ambient=_AMB)
    fit_a = T.contact_radius_fit(rec["normals"], ctx["X"], ctx["Y"], pad["R"], pad["pitch"], centre_xy=(0.0, 0.0))
    a_hat = T.contact_radius_fit_pixelwise(rec["normals"], ctx["X"], ctx["Y"], pad["R"], fit_a["a"])["a"] if pixelwise else fit_a["a"]
    P_hat = T.hertz_force(pad["R"], pad["Es"], a=a_hat)
    hz = T.hertz_sphere(P_hat, pad["R"], pad["Es"])
    tr = track
    if tr is None:
        m_cur = S.marker_image(frame["rgb"], frame["shading"])
        tr = S.marker_track(ctx["m_ref"], m_cur, pad["dark"], pad["pitch_px"], pad["marker_r_px"])
    p0, u = np.asarray(tr["p0"], np.float64), np.asarray(tr["u"], np.float64).copy()
    if len(p0) < 3:
        raise ValueError("pad_tactile_read: only %d markers tracked (need >= 3)" % len(p0))
    c0, pitch = ctx["c0"], pad["pitch"]
    d = p0 - c0
    rr = np.hypot(d[:, 0], d[:, 1])
    ur = S.hertz_surface_ur(rr * pitch, hz["a"], hz["p0"], pad["G"], pad["nu"])
    u = u - ur[:, None] * (d / np.maximum(rr[:, None], 1e-12)) / pitch
    model = _model_for(pad, ctx, a_hat, hz)
    fit = S.mindlin_fit_vector(model, p0, u * pitch)
    phi = fit["phi"]
    core = rr * pitch < 0.5 * a_hat
    if core.sum() < 3:
        core = rr * pitch < a_hat
    ub = u[core].mean(axis=0) if core.any() else np.zeros(2)
    Q = max(fit["Q"], 0.0)
    delta = float(np.hypot(*ub)) * pitch
    muP = pad["mu"] * P_hat
    d_full = 3.0 * muP * (2.0 - pad["nu"]) / (16.0 * pad["G"] * a_hat)
    Q_stick = muP * (1.0 - max(0.0, 1.0 - delta / d_full) ** 1.5) if d_full > 0 else 0.0
    fx, fy = S._model_unit_field(model, p0, fit["c_over_a"])
    p90 = np.column_stack([d[:, 1], -d[:, 0]]) + c0
    gx, gy = S._model_unit_field(model, p90, fit["c_over_a"])
    gv = np.column_stack([-gy, gx])
    A_, B_ = fit["muP"] * math.cos(phi), fit["muP"] * math.sin(phi)
    u_fit = (A_ * np.column_stack([fx, fy]) + B_ * gv) / pitch
    core6 = rr * pitch < 0.6 * a_hat
    torsion_hat = 0.0
    if core6.sum() >= 3:
        rf = TQ.rigid_rotation_fit(d[core6] * pitch, (u - u_fit)[core6] * pitch)
        torsion_hat = 16.0 * pad["G"] * a_hat ** 3 / 3.0 * rf["omega"]
    return {"P": float(P_hat), "a": float(a_hat), "q": Q * np.array([math.cos(phi), math.sin(phi)]), "Q": float(Q), "phi": phi,
            "torsion": float(torsion_hat), "c_over_a": fit["c_over_a"], "Q_stick": float(Q_stick), "matched": int(tr["matched"]),
            "rms_px": fit["rms_m"] / pitch, "track": tr}


# ======================================================================================================================
# 3. 接触レンチ → Whitney の接触状態
def _perp_basis(a):
    a = np.asarray(a, np.float64) / np.linalg.norm(a)
    b1 = np.cross(a, [0.0, 1.0, 0.0]) if abs(a[1]) < 0.9 else np.cross(a, [1.0, 0.0, 0.0])
    b1 /= np.linalg.norm(b1)
    return b1, np.cross(a, b1)


def _axis(axis, name):
    a = _vec(axis, 3, name)
    nrm = float(np.linalg.norm(a))
    if not (nrm > 1e-12):
        raise ValueError("%s must be non-zero" % name)
    return a / nrm


def contact_candidates(kp, tip, axis, n_az: int = 144, tol: float = 0.08e-3) -> dict:
    """単一接触の候補点(世界系)と、その点が**幾何的に触れうるか**の印。``tip_rim`` = 先端の縁の円(半径 r、軸に垂直)で、縁の点が
    壁(最狭部より深い: 半径 ≥ R − tol)か面取り面(半径 ≥ R + (W − 深さ) − tol)に届くものだけ有効。``mouth`` = 穴の最狭部の縁の円
    (半径 R、z = −W)で、胴の表面が通る(軸の直線からの距離が r ± tol、先端が最狭部より深い)ものだけ有効。
    候補を絞らないと、二点接触の合力の作用線が「壁に触れていない側の先端の縁」を通る偶然を一点と読む(試作のくさびで実測)。
    ``tol`` は MuJoCo の柔らかい接触のめり込みと 36 角形の壁(頂点で +0.02 mm)ぶん。返り ``tip_rim``・``rim_ok``・``mouth``・
    ``mouth_ok``・``depth``。**Raises** ValueError: tip・axis が有限の 3 成分でない、n_az < 8、tol < 0。"""
    kp = PS._kp(kp)
    tip = _vec(tip, 3, "contact_candidates: tip")
    a = _axis(axis, "contact_candidates: axis")
    if int(n_az) < 8 or not (float(tol) >= 0.0):
        raise ValueError("contact_candidates: need n_az >= 8 and tol >= 0")
    if a[2] < 0:
        a = -a
    b1, b2 = _perp_basis(a)
    ps = np.linspace(0.0, 2.0 * math.pi, int(n_az), endpoint=False)
    rim = tip[None, :] + kp["r"] * (np.cos(ps)[:, None] * b1 + np.sin(ps)[:, None] * b2)
    R, W, r = kp["R"], kp["chamfer"], kp["r"]
    rho = np.hypot(rim[:, 0], rim[:, 1])
    dep = -rim[:, 2]
    rim_ok = ((dep > W) & (rho >= R - tol)) | ((dep > 0) & (dep <= W) & (rho >= R + (W - dep) - tol))
    mouth = np.column_stack([R * np.cos(ps), R * np.sin(ps), np.full(len(ps), -W)])
    dm = mouth - tip[None, :]
    dist_axis = np.linalg.norm(dm - np.outer(dm @ a, a), axis=1)
    depth = -float(tip[2])
    mouth_ok = (np.abs(dist_axis - r) < tol) & (depth > W) & ((dm @ a) > 0)
    return {"tip_rim": rim, "rim_ok": rim_ok, "mouth": mouth, "mouth_ok": mouth_ok, "depth": depth}


def contact_state_from_wrench(kp, F, M_g, g, tip, axis, f_air: float = 0.05, tau: float = 0.35, tol: float = 0.08e-3,
                              geometry: bool = True, tol_l: float = 0.05e-3) -> dict:
    """接触レンチ(ペグが穴から受ける F と把持点 g まわりの M、世界系)→ 接触状態(学習なしの規則)。

    単一の点接触なら、その点まわりのモーメントは 0(点に偶力なし)。**幾何的に触れうる**候補点 c(:func:`contact_candidates`)ごとの
    正規化残差 e(c) = |M_g − (c − g) × F| / (|F| r) の最小が ``tau`` 未満なら一点(先端の縁で深さ < W なら面取り)、どの候補でも説明
    できず先端と胴の両方に有効な候補があれば二点、|F| < ``f_air`` なら無接触。``geometry`` なら Whitney の幾何を優先する: 傾き θ で
    先端が最狭部から l₂(θ) − ``tol_l`` より深ければ両側に触れるしかない(二点を強制)。くさびの境目 θ = c/μ では先端の摩擦円錐の縁が
    口の接触点を通り(口と先端を結ぶ線の傾き c/θ = μ)、二点のレンチが「口の一点」と区別できない —— レンチだけの規則の原理的な死角。
    返り ``state``(:data:`CONTACT_STATES`)、``e_tip``・``e_mouth``、``where``("none" / "tip" / "mouth" / "tip+mouth" / "?")、
    ``c``(当たった点、一点のとき)、``Fmag``・``depth``・``forced``。**Raises** ValueError: ベクトルが有限の 3 成分でない、tau ≤ 0。"""
    kp = PS._kp(kp)
    F = _vec(F, 3, "contact_state_from_wrench: F")
    M = _vec(M_g, 3, "contact_state_from_wrench: M_g")
    g = _vec(g, 3, "contact_state_from_wrench: g")
    a_ = _axis(axis, "contact_state_from_wrench: axis")
    if not (float(tau) > 0.0 and float(f_air) >= 0.0):
        raise ValueError("contact_state_from_wrench: need tau > 0 and f_air >= 0")
    Fm = float(np.linalg.norm(F))
    cand = contact_candidates(kp, tip, a_, tol=tol)
    out = {"Fmag": Fm, "depth": cand["depth"], "e_tip": float("nan"), "e_mouth": float("nan"), "where": "none", "c": None,
           "forced": False}
    if Fm < float(f_air):
        return dict(out, state="none")
    scale = Fm * kp["r"]

    def resid(C, ok):
        if not ok.any():
            return float("inf"), None
        e = np.linalg.norm(M[None, :] - np.cross(C[ok] - g[None, :], F[None, :]), axis=1) / scale
        k = int(np.argmin(e))
        return float(e[k]), C[ok][k]
    et, ct = resid(cand["tip_rim"], cand["rim_ok"])
    em, cm = resid(cand["mouth"], cand["mouth_ok"])
    out.update(e_tip=et, e_mouth=em)
    forced = False
    if geometry:
        th = math.atan2(math.hypot(float(a_[0]), float(a_[1])), abs(float(a_[2])))
        th_max = math.atan2(math.sqrt(max(kp["R"] ** 2 - kp["r"] ** 2, 0.0)), kp["r"])     # cosθ = r/R(胴が穴に入れる最大の傾き)
        if 1e-4 < th < th_max:
            forced = (cand["depth"] - kp["chamfer"]) >= PS.two_point_depth(kp, th) - float(tol_l)
    out["forced"] = bool(forced)
    if forced and cand["rim_ok"].any() and cand["mouth_ok"].any():
        return dict(out, state="two_point", where="tip+mouth")
    if min(et, em) < float(tau):
        if et <= em:
            st = "chamfer" if cand["depth"] < kp["chamfer"] else "one_point"
            return dict(out, state=st, where="tip", c=ct)
        return dict(out, state="one_point", where="mouth", c=cm)
    if cand["rim_ok"].any() and cand["mouth_ok"].any():
        return dict(out, state="two_point", where="tip+mouth")
    return dict(out, state="unknown", where="?")


def friction_from_single_contact(F, where: str, c, axis, chamfer: bool = False) -> dict:
    """一点接触で滑っている間の接触力から壁の摩擦係数(滑りの間だけ Coulomb の限界に張り付く、固着中は下限)。
    先端の縁が壁(``where="tip"``)なら法線 = 水平(穴の中心へ)、摩擦 = 鉛直 → μ̂ = |F_z|/|F_水平|。胴が最狭部の縁(``"mouth"``)なら
    法線 = 軸に垂直、摩擦 = 軸方向 → μ̂ = |F·a|/|F_⊥|。``chamfer`` なら 45° の面取り面の上(法線 = (−r̂, 1)/√2、``c`` = 接触点が要る)。
    ``"none"`` は None。返り ``mu``(None 可)。**Raises** ValueError: where が語彙の外、F・axis が有限の 3 成分でない、面取りで c が無い。"""
    if where not in ("tip", "mouth", "none"):
        raise ValueError("friction_from_single_contact: where must be 'tip' | 'mouth' | 'none', got %r" % (where,))
    F = _vec(F, 3, "friction_from_single_contact: F")
    a = _axis(axis, "friction_from_single_contact: axis")
    if where == "tip" and chamfer:
        if c is None:
            raise ValueError("friction_from_single_contact: chamfer needs the contact point c")
        c_ = _vec(c, 3, "friction_from_single_contact: c")
        rh = np.array([c_[0], c_[1], 0.0])
        rh /= max(1e-12, float(np.linalg.norm(rh)))
        nv = (-rh + np.array([0.0, 0.0, 1.0])) / math.sqrt(2.0)
        fn = float(F @ nv)
        ft = float(np.linalg.norm(F - fn * nv))
        return {"mu": ft / fn if fn > 1e-9 else None}
    if where == "tip":
        fh = float(np.hypot(F[0], F[1]))
        return {"mu": abs(float(F[2])) / fh if fh > 1e-9 else None}
    if where == "mouth":
        fa = float(F @ a)
        fp = float(np.linalg.norm(F - fa * a))
        return {"mu": abs(fa) / fp if fp > 1e-9 else None}
    return {"mu": None}


def stall_verdict(kp, theta: float, mu_hat) -> dict:
    """二点接触で止まった時の Whitney の判定(OCW p.28): θ > c/μ̂ ならくさび(力を抜いても抜けない側)、以下ならかじり(力の向きで
    解ける)。c = (R − r)/R。μ̂ は同じ挿入の滑りの区間で触覚から読んだ値(:func:`friction_from_single_contact`)、None か ≤ 0 なら
    推測せず ``"unknown"``。返り ``verdict``("wedging" / "jamming" / "unknown")・``theta_limit``。**Raises** ValueError: θ が有限でないか負。"""
    kp = PS._kp(kp)
    th = float(theta)
    if not (math.isfinite(th) and th >= 0.0):
        raise ValueError("stall_verdict: theta must be finite and >= 0, got %r" % (theta,))
    if mu_hat is None or not (float(mu_hat) > 0):
        return {"verdict": "unknown", "theta_limit": float("nan")}
    c = (kp["R"] - kp["r"]) / kp["R"]
    lim = c / float(mu_hat)
    return {"verdict": "wedging" if th > lim else "jamming", "theta_limit": lim}


def two_point_forces(kp, F, M_g, g, tip, axis, mu_grid=None) -> dict:
    """二点接触(Whitney)のレンチを 2 つの接触力と壁の摩擦 μ に分解する(平面、両点が下へ滑る Coulomb の仮定)。

    傾きの面(軸の水平成分 e)で、先端の縁は −e 側の壁(法線 = 水平、摩擦 = 上向き)、胴は +e 側の最狭部の縁(法線 = 軸に垂直、摩擦 =
    軸の上向き)。各 μ で (f_n1, f_n2) は 3 式(F_e, F_z, M)の最小二乗、残差最小の μ を放物線で詰める(既定の格子 0〜1.5、301 点)。
    返り ``mu``・``fn_tip``・``fn_mouth``・``resid``(N)・``p_tip``・``p_mouth``。
    **Raises** ValueError: 軸が鉛直すぎて傾きの面が決まらない、ベクトルが有限の 3 成分でない、μ の格子が 3 点未満。"""
    kp = PS._kp(kp)
    F = _vec(F, 3, "two_point_forces: F")
    M = _vec(M_g, 3, "two_point_forces: M_g")
    g = _vec(g, 3, "two_point_forces: g")
    tip = _vec(tip, 3, "two_point_forces: tip")
    a = _axis(axis, "two_point_forces: axis")
    e = np.array([a[0], a[1], 0.0])
    if np.linalg.norm(e) < 1e-6:
        raise ValueError("two_point_forces: peg axis is vertical; tilt plane undefined")
    e /= np.linalg.norm(e)
    ez = np.array([0.0, 0.0, 1.0])
    nrm = np.cross(ez, e)
    perp_e = e - (e @ a) * a
    perp_e /= np.linalg.norm(perp_e)
    p1 = tip - kp["r"] * perp_e
    p2 = np.array([0.0, 0.0, -kp["chamfer"]]) + kp["R"] * e
    n1, n2 = e, -perp_e
    t1, t2 = ez, a
    mus = np.linspace(0.0, 1.5, 301) if mu_grid is None else np.asarray(mu_grid, np.float64).reshape(-1)
    if len(mus) < 3:
        raise ValueError("two_point_forces: mu_grid needs >= 3 values")
    obs = np.array([F @ e, F @ ez, M @ nrm])

    def col(p, n_, t_, mu):
        f = n_ + mu * t_
        return np.array([f @ e, f @ ez, np.cross(p - g, f) @ nrm])

    res = []
    for mu in mus:
        A = np.column_stack([col(p1, n1, t1, mu), col(p2, n2, t2, mu)])
        x, *_ = np.linalg.lstsq(A, obs, rcond=None)
        res.append((float(np.linalg.norm(A @ x - obs)), x))
    rv = np.array([r_[0] for r_ in res])
    k = int(np.argmin(rv))
    mu_b = float(mus[k])
    if 0 < k < len(mus) - 1:
        den = rv[k - 1] - 2 * rv[k] + rv[k + 1]
        if den > 1e-15:
            mu_b = float(mus[k] + 0.5 * (rv[k - 1] - rv[k + 1]) / den * (mus[1] - mus[0]))
    A = np.column_stack([col(p1, n1, t1, mu_b), col(p2, n2, t2, mu_b)])
    x, *_ = np.linalg.lstsq(A, obs, rcond=None)
    return {"mu": mu_b, "fn_tip": float(x[0]), "fn_mouth": float(x[1]), "resid": float(np.linalg.norm(A @ x - obs)),
            "p_tip": p1, "p_mouth": p2}


def whitney_wrench(kp, state: str, theta: float, depth: float, mu: float, fn_tip: float, fn_mouth: float = 0.0, g=None) -> dict:
    """閉形式の接触レンチ(Whitney の準静的な平面、真値つきの合成): 傾き θ(軸の上端が +x へ)・先端深さ ``depth``(口の面から)の
    ペグに、``state`` = ``"one_point"``(先端の縁が −x の壁)/ ``"mouth"``(胴が +x の最狭部の縁)/ ``"two_point"``(両方)で、法線力
    ``fn_tip``・``fn_mouth`` と下へ滑る Coulomb 摩擦 μ を与える。二点は depth = W + l₂(θ) で胴も縁に触れる(閉形式)。``g`` は把持点
    (省略時は先端から軸に沿って ペグ長 − 8 mm)。返り ``F``・``M_g``(把持点まわり)・``g``・``tip``・``axis``・``points``。
    **Raises** ValueError: state が語彙の外、θ が (0, π/2) の外、depth・μ・法線力が有限でないか負。"""
    if state not in ("one_point", "mouth", "two_point"):
        raise ValueError("whitney_wrench: state must be one_point | mouth | two_point, got %r" % (state,))
    kp = PS._kp(kp)
    vals = {"theta": theta, "depth": depth, "mu": mu, "fn_tip": fn_tip, "fn_mouth": fn_mouth}
    for k_, v in vals.items():
        if not (math.isfinite(float(v)) and float(v) >= 0.0):
            raise ValueError("whitney_wrench: %s must be finite and >= 0, got %r" % (k_, v))
    if not (0.0 < float(theta) < 0.5 * math.pi):
        raise ValueError("whitney_wrench: theta must be in (0, pi/2)")
    theta, depth, mu = float(theta), float(depth), float(mu)
    a = np.array([math.sin(theta), 0.0, math.cos(theta)])
    tip = np.array([0.0, 0.0, -depth])
    g = tip + (kp["peg_length"] - 8.0e-3) * a if g is None else _vec(g, 3, "whitney_wrench: g")
    e = np.array([1.0, 0.0, 0.0])
    ez = np.array([0.0, 0.0, 1.0])
    perp_e = e - (e @ a) * a
    perp_e /= np.linalg.norm(perp_e)
    if state == "mouth":
        # 胴を +x 側の最狭部の縁に触れさせる: 軸が z = −W を通る点の x = R − r/cosθ(水平断面は長半径 r/cosθ の楕円)
        p_a = np.array([kp["R"] - kp["r"] / math.cos(theta), 0.0, -kp["chamfer"]])
        tip_new = p_a - ((depth - kp["chamfer"]) / math.cos(theta)) * a
        g = g + (tip_new - tip)
        tip = tip_new
    else:
        shift = -kp["R"] - (tip - kp["r"] * perp_e)[0]
        tip = tip + np.array([shift, 0.0, 0.0])
        g = g + np.array([shift, 0.0, 0.0])
    p1 = tip - kp["r"] * perp_e
    p2 = np.array([kp["R"], 0.0, -kp["chamfer"]])
    f1 = float(fn_tip) * (e + mu * ez)
    f2 = float(fn_mouth) * (-perp_e + mu * a)
    F, M, pts = np.zeros(3), np.zeros(3), []
    if state in ("one_point", "two_point"):
        F += f1
        M += np.cross(p1 - g, f1)
        pts.append(p1)
    if state in ("mouth", "two_point"):
        F += f2
        M += np.cross(p2 - g, f2)
        pts.append(p2)
    return {"F": F, "M_g": M, "g": g, "tip": tip, "axis": a, "points": pts}


# ======================================================================================================================
# 4. 手首剛性の同定と手首カメラのたわみ
def wrist_stiffness_fit(dx, F, min_span: float = 0.02e-3) -> dict:
    """手首のたわみ Δx(手首カメラ)と、ペグが受ける接触力の同じ成分 F から k = Σ FΔx / ΣΔx²(原点を通る最小二乗、準静的な釣り合い
    F_contact + F_spring ≈ 0 ⇒ F_contact = kΔx)。回転(角と モーメント)にも同じ式で使える。返り ``k``・``r2``・``rms_N``・``n``・``span``。
    **Raises** ValueError: 点が 3 未満、形が違う、有限でない、Δx の幅が ``min_span`` 未満(悪条件: 動いていないばねの k は決まらない)。"""
    x = np.asarray(dx, np.float64).reshape(-1)
    f = np.asarray(F, np.float64).reshape(-1)
    if x.shape != f.shape or x.size < 3:
        raise ValueError("wrist_stiffness_fit: need >= 3 paired samples")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(f))):
        raise ValueError("wrist_stiffness_fit: samples must be finite")
    span = float(x.max() - x.min())
    if span < float(min_span):
        raise ValueError("wrist_stiffness_fit: deflection span %.3g < %.3g (ill-conditioned)" % (span, min_span))
    k = float((f * x).sum() / (x * x).sum())
    res = f - k * x
    ss = float(((f - f.mean()) ** 2).sum())
    return {"k": k, "r2": 1.0 - float((res ** 2).sum()) / ss if ss > 0 else float("nan"), "rms_N": float(np.sqrt(np.mean(res ** 2))),
            "n": int(x.size), "span": span}


def wrist_deflection_from_rgbd(rgb, depth, K, R_cam_to_world, cam_w, carriage_pos, r_peg: float, hinge_z: float = 0.0) -> dict:
    """手首 RGB-D 1 枚から手首の並進たわみと傾き: ペグの画素(pegsim の色分類)→ depth の点群 → PCA の軸 → 既知半径の円柱当てはめ
    (:func:`pegsim.cylinder_fit_known_radius`)→ 世界系の軸の直線 → 搬送台の系(エンコーダで既知の位置 ``carriage_pos`` を引く)で
    ヒンジの高さ z = ``hinge_z`` を通る点 = (Δx, Δy)。軸の向きから傾き (θ_x, θ_y) を atan2 で。円柱の軸方向の位置は見えないので
    Δz は出さない(正直に: 手首の z 圧縮は k̂ と触覚の F_z で補う、:func:`pegtactile_process_episode`)。
    返り ``dx``・``dy``・``axis``・``tilt_x``・``tilt_y``・``rms_cyl``・``n_pts``。
    **Raises** ValueError: 形が合わない、ペグの画素が 50 未満(見えない)。"""
    import camera
    rgb = np.asarray(rgb)
    depth = np.asarray(depth, np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or depth.shape != rgb.shape[:2]:
        raise ValueError("wrist_deflection_from_rgbd: rgb (H, W, 3) and depth (H, W) must agree")
    if not (float(r_peg) > 0.0):
        raise ValueError("wrist_deflection_from_rgbd: r_peg must be > 0")
    cam_w = _vec(cam_w, 3, "wrist_deflection_from_rgbd: cam_w")
    carriage_pos = _vec(carriage_pos, 3, "wrist_deflection_from_rgbd: carriage_pos")
    _, _, peg = PS._classify(rgb)
    core = PS._erode(peg, 2)
    ys, xs = np.nonzero(core)
    if len(ys) < 50:
        raise ValueError("wrist_deflection_from_rgbd: peg not visible (%d px, need >= 50)" % len(ys))
    Pc = camera.backproject(np.column_stack([xs, ys]), depth[ys, xs], np.asarray(K, np.float64))
    c0 = Pc.mean(axis=0)
    _, _, vt = np.linalg.svd(Pc - c0, full_matrices=False)
    a = vt[0]
    e1 = np.cross(a, [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    q = np.column_stack([(Pc - c0) @ e2, (Pc - c0) @ e1])
    cq = PS.circle_fit_known_radius(q, float(r_peg))
    fit = PS.cylinder_fit_known_radius(Pc, float(r_peg), c0 + cq["cx"] * e1 + cq["cy"] * e2, a)
    Rcw = np.asarray(R_cam_to_world, np.float64)
    pw = Rcw @ fit["axis_point"] + cam_w
    aw = Rcw @ fit["axis"]
    if aw[2] < 0:
        aw = -aw
    pc = pw - carriage_pos
    t = (float(hinge_z) - pc[2]) / aw[2]
    h = pc + t * aw
    return {"dx": float(h[0]), "dy": float(h[1]), "axis": aw, "tilt_y": math.atan2(aw[0], aw[2]), "tilt_x": math.atan2(-aw[1], aw[2]),
            "rms_cyl": fit["rms"], "n_pts": int(len(Pc))}


# ======================================================================================================================
# 5. 対称性: 形の n 回対称の次数と向き、同変性の門
def symmetric_peg_shape(name: str, size: int = 160, radius: float = 50.0, angle: float = 0.0, centre=None, ss: int = 8) -> np.ndarray:
    """ペグの断面(真値つきの合成、反エイリアスの被覆率 0..1、(size, size)): 円・正三角形・正方形・正六角形(外接円半径 ``radius``
    [px])・キー付きの円(D カット: 円の一部を弦で切る、n = 1)。``angle`` [rad] だけ**形を回して描く**(画像を回すと補間が入る)。
    ``centre`` = (col, row)、``ss`` = 画素あたりの副標本の 1 辺。**Raises** ValueError: 未知の形、size < 16、radius ≤ 0、ss < 1。"""
    if name not in SHAPES:
        raise ValueError("symmetric_peg_shape: name must be one of %r, got %r" % (SHAPES, name))
    if int(size) < 16 or not (float(radius) > 0.0) or int(ss) < 1:
        raise ValueError("symmetric_peg_shape: need size >= 16, radius > 0, ss >= 1")
    size, ss = int(size), int(ss)
    c = ((size - 1) / 2.0, (size - 1) / 2.0) if centre is None else (float(centre[0]), float(centre[1]))
    off = (np.arange(ss) + 0.5) / ss - 0.5
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    acc = np.zeros((size, size))
    ca, sa = math.cos(float(angle)), math.sin(float(angle))
    rad = float(radius)
    for dy in off:
        for dx in off:
            x = xx + dx - c[0]
            y = yy + dy - c[1]
            xr, yr = ca * x + sa * y, -sa * x + ca * y
            if name == "circle":
                inside = xr * xr + yr * yr <= rad * rad
            elif name == "keyed":
                inside = (xr * xr + yr * yr <= rad * rad) & (xr <= 0.6 * rad)
            else:
                nn = {"triangle": 3, "square": 4, "hexagon": 6}[name]
                ap = rad * math.cos(math.pi / nn)
                inside = np.ones_like(xr, bool)
                for k in range(nn):
                    th = 2.0 * math.pi * k / nn
                    inside &= (xr * math.cos(th) + yr * math.sin(th)) <= ap
            acc += inside
    return acc / (ss * ss)


def _level_contour(img, level: float = 0.5) -> np.ndarray:
    """被覆率の像の副画素の等値線(最長の閉輪郭、(N, 2) = (row, col))を Fullseye の op ``threshold_sub_pix``(マーチング
    スクエア、レベル = 0.2 + 0.5a)で取る。**Raises** ValueError: レベルが (0.2, 0.7) の外、輪郭が無い。"""
    if not (0.2 < float(level) < 0.7):
        raise ValueError("_level_contour: level must be in (0.2, 0.7) (threshold_sub_pix maps a in (0, 1) to 0.2 + 0.5a)")
    op = _THRESHOLD_SUB_PIX.get("fn")
    if op is None:
        # 登録 op と同じ実装(backends_auto の xld 族の ``threshold_sub_pix`` 分岐)を直接引く —— ops の登録表を組むと
        # 1 s かかり CI の門の時間を食うため。登録表経由と同じ輪郭になることは PoC の --full で確かめる
        import backends_auto
        op = backends_auto._sh_xld({"kind": "threshold_sub_pix"})
        _THRESHOLD_SUB_PIX["fn"] = op
    xld = op(np.asarray(img, np.float64), (float(level) - 0.2) / 0.5, 0.5)
    cs = [np.asarray(c_, np.float64) for c_ in (xld.get("cs", []) if isinstance(xld, dict) else [])]
    if not cs:
        raise ValueError("_level_contour: no contour at level %.3g" % level)
    return max(cs, key=len)


_THRESHOLD_SUB_PIX: dict = {}


def symmetry_order_contour(contour, K: int = 24, rel: float = 0.01) -> dict:
    """閉輪郭 (N, 2) = (row, col) の複素フーリエ係数(:func:`fourierdesc.contour_fourier_complex`、弧長で打ち直し、±K 次)から n 回対称の
    次数を読む: n 回対称なら非零の係数は k ≡ 1 (mod n) だけ。有意(|c_k| > rel·|c_1|、k ≠ 0, 1)な k の (k − 1) の最大公約数が n。
    有意な k が無ければ円(``n`` = 0 = 連続)。向き α̂ = arg(c₁₋ₙ c₁ⁿ⁻¹)/n(始点の取り方に依らない不変量、mod 2π/n)。n = 1 は
    c₂ c₁⁻² から α̂ = −arg(·) —— k = −1(振幅は 3 倍)は形ごとの定数位相が違い、枝(α / α + π)を参照なしに決められない(試作で
    180° 取り違えた)。返り ``n``・``angle``(rad、n = 0 は nan)・``amps``(k → |c_k|/|c_1|)・``sig``・``centroid``(c₀ = (row, col))。
    2 次モーメントの向きは n ≥ 3 で慣性が等方になり使えない(PoC の罠の門)。**Raises** ValueError: 輪郭が (N ≥ 8, 2) でない、K < 6。"""
    import fourierdesc as FD
    c = np.asarray(contour, np.float64)
    if c.ndim != 2 or c.shape[1] != 2 or len(c) < 8 or not np.all(np.isfinite(c)):
        raise ValueError("symmetry_order_contour: contour must be finite (N >= 8, 2)")
    if int(K) < 6 or not (float(rel) > 0.0):
        raise ValueError("symmetry_order_contour: need K >= 6 and rel > 0")
    sp = FD.contour_fourier_complex(c, n_harmonics=int(K), parametrisation="arclength")
    coef = {int(round(k)): complex(re, im) for k, re, im in sp}
    c1 = coef[1]
    amps = {k: abs(v) / abs(c1) for k, v in coef.items() if k not in (0, 1)}
    sig = [k for k, v in amps.items() if v > float(rel)]
    n = 0
    for k in sig:
        n = math.gcd(n, abs(k - 1))
    angle = float("nan")
    if n >= 2 and (1 - n) in coef:
        z = coef[1 - n] * c1 ** (n - 1)
        angle = (math.atan2(z.imag, z.real) / n) % (2 * math.pi / n)
    elif n == 1:
        z2 = coef[2] * c1 ** (-2)
        angle = (-math.atan2(z2.imag, z2.real)) % (2 * math.pi)
    c0 = coef[0]                                              # 複素平面: 実軸 = col、虚軸 = row
    return {"n": n, "angle": angle, "amps": amps, "centroid": (c0.imag, c0.real), "sig": sorted(sig)}


def equivariance_check(render, op, angles, n: int, centre) -> dict:
    """同変性の門の部品: 形を角 θ だけ回して描き(``render(θ)`` → 画像)、知覚 op(``op(画像)`` → (row, col, 向き))の答えが群の作用
    どおりに変わるか。期待 = 位置は ``centre`` = (row, col) まわりに θ 回る、向きは θ 進む(mod 2π/n、n = 0 なら向きは比べない)。
    返り ``pos_err_px``(最大)、``ang_err_deg``(最大、mod 2π/n の最短距離、比べなければ nan)、``rows``(角ごと)。
    **Raises** ValueError: render・op が呼べない、角が 1 つも無い・有限でない、n < 0、centre が 2 成分でない。"""
    if not (callable(render) and callable(op)):
        raise ValueError("equivariance_check: render and op must be callable")
    ang = np.asarray(angles, np.float64).reshape(-1)
    if ang.size < 1 or not np.all(np.isfinite(ang)):
        raise ValueError("equivariance_check: need >= 1 finite angle")
    if int(n) < 0:
        raise ValueError("equivariance_check: n must be >= 0")
    cr, cc = _vec(centre, 2, "equivariance_check: centre")
    base = op(render(0.0))
    rows = []
    for th in ang:
        r_, c_, a_ = op(render(float(th)))
        dr, dc = base[0] - cr, base[1] - cc
        exp_c = cc + math.cos(th) * dc - math.sin(th) * dr
        exp_r = cr + math.sin(th) * dc + math.cos(th) * dr
        pe = math.hypot(r_ - exp_r, c_ - exp_c)
        ae = float("nan")
        if int(n) >= 1 and np.isfinite(a_) and np.isfinite(base[2]):
            per = 2 * math.pi / int(n)
            dd = (a_ - (base[2] + th)) % per
            ae = math.degrees(min(dd, per - dd))
        rows.append({"theta": float(th), "pos_err": pe, "ang_err": ae})
    pes = [r_["pos_err"] for r_ in rows]
    aes = [r_["ang_err"] for r_ in rows if np.isfinite(r_["ang_err"])]
    return {"pos_err_px": float(max(pes)), "ang_err_deg": float(max(aes)) if aes else float("nan"), "rows": rows}


# ======================================================================================================================
# 6. mujoco 層(facade のみ): 挿入の走行と、各フレームの接触レンチを膜の像に写して読み戻す後処理
def pegtactile_cutaway_xml(xml: str, alpha: float = 0.22, width: int = 480, height: int = 400) -> str:
    """描画専用の場面(numpy だけ、mujoco 不要): 穴の板(``plate`` の body の geom)を半透明にし、穴の中を真横から見る断面カメラ ``cut``
    (y = −45 mm、水平、fovy 34°)を足した MJCF 文字列。物理は元の場面で回し、qpos を写して描くだけ(接触は元の場面のもの)。
    **Raises** ValueError: XML が読めない、``plate`` の body・``visual/global`` が無い、alpha が [0, 1] の外。"""
    import xml.etree.ElementTree as ET
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError("pegtactile_cutaway_xml: alpha must be in [0, 1]")
    try:
        root = ET.fromstring(str(xml))
    except ET.ParseError as exc:
        raise ValueError("pegtactile_cutaway_xml: not an XML string (%s)" % exc) from exc
    plate = next((b for b in root.iter("body") if b.get("name") == "plate"), None)
    wb = root.find("worldbody")
    glob = root.find("visual/global")
    if plate is None or wb is None or glob is None:
        raise ValueError("pegtactile_cutaway_xml: needs a 'plate' body, worldbody and visual/global (the pegfail scene)")
    for gm in plate.iter("geom"):
        rgba = gm.get("rgba")
        if rgba:
            v = rgba.split()
            a_ = float(alpha) if gm.get("name") else 0.04            # 無名 = 四角い枠(手前を塞ぐ)はほぼ透明に
            gm.set("rgba", " ".join(v[:3] + [str(a_)]))
    ET.SubElement(wb, "camera", {"name": "cut", "pos": "0 -0.045 -0.004", "xyaxes": "1 0 0 0 0 1", "fovy": "34"})
    glob.set("offwidth", str(max(int(glob.get("offwidth", "0")), int(width))))
    glob.set("offheight", str(max(int(glob.get("offheight", "0")), int(height))))
    return ET.tostring(root, encoding="unicode")


def _wrench_on_peg(sc, cons, pad):
    """接触の世界系の力 → ペグが穴から受けるレンチ(F、把持点 g まわりの M)と、パッドが加えるべきレンチ(グリッパ系)。"""
    d, ids = sc["data"], sc["ids"]
    top = d.site_xpos[ids["top"]].copy()
    tip = d.site_xpos[ids["tip"]].copy()
    a = top - tip
    a /= np.linalg.norm(a)
    g = top - pad["grasp_below_top"] * a
    com = top - pad["com_below_top"] * a
    Fc, Mc = np.zeros(3), np.zeros(3)
    for c in cons:
        Fc += c["f_world"]
        Mc += np.cross(c["pos"] - g, c["f_world"])
    Fg = np.array([0.0, 0.0, -pad["peg_mass"] * 9.81])
    Mg = np.cross(com - g, Fg)
    Rw = d.xmat[sc["model"].body("wrist").id].reshape(3, 3).copy()
    F_pad_w, M_pad_w = -(Fc + Fg), -(Mc + Mg)
    return {"Fc": Fc, "Mc": Mc, "g": g, "tip": tip, "top": top, "axis": a, "com": com, "Rw": Rw,
            "F_pad": Rw.T @ F_pad_w, "M_pad": Rw.T @ M_pad_w, "F_pad_w": F_pad_w, "M_pad_w": M_pad_w}


def pegtactile_episode_run(kp=None, pad=None, eps_mm=(0.6, 0.0), tilt_deg: float = 3.0, mu: float | None = None, v: float = 3e-3,
                           t_max: float = 4.0, f_max: float = 6.0, v_fast: float = 12e-3, frame_every: float = 0.02,
                           render_wrist: bool = True, render_side: bool = False, release: bool = False, stall_window: float = 0.3,
                           stall_min: float = 0.05e-3, stop_depth: float = 14e-3, azimuth_deg: float = 0.0, exposure: float = 0.01,
                           keep_images: bool = False) -> dict:
    """柔らかい手首の挿入 1 走行(mujoco が要る、場面は :func:`pegfail.pegfail_scene_build`): 構え → 横ずれ ``eps_mm`` → 一定速度 ``v``
    で降下(接触力の和が ``f_max`` を超えたら押すのを止める、空中と面取りの 1 mm 上までは ``v_fast``)。``frame_every`` ごとに 1 フレーム:
    接触(点・世界系の力)、**露光 ``exposure`` の平均の接触レンチ**(膜カメラは露光の間を積分する: 一点の区間ではペグが口の縁で
    10 ms 単位で跳ね、瞬間の接触力は撃力でばね力より大きい)と状態の多数決、手首ばねの関節値、手首の力・トルクセンサ、手首カメラの
    たわみ(:func:`wrist_deflection_from_rgbd`、その場で計測して画像は ``keep_images`` の時だけ残す)、断面の像(``render_side``)。
    ``azimuth_deg`` は場面をグリッパに対して回す(横ずれと傾きの向きを一緒に)。``release`` なら停滞(``stall_window`` の間の進み <
    ``stall_min``)で押す力を抜く探針(手首ばねの z 圧縮ぶん搬送台を上げ 0.6 s → さらに 2 mm 引いて 0.6 s)を行う。
    返り ``frames``・``kp``・``pad``・``wall_s``・``sim_s``・``status``("inserted" / "stalled" / "timeout")・``eps_mm``・``tilt_deg``・
    ``azimuth_deg``。**Raises** ImportError: mujoco が無い。ValueError: 時間・速度が正でない。"""
    import collections
    import time

    import pegfail as PF
    mujoco = PS._mujoco()
    for k_, v_ in {"v": v, "t_max": t_max, "frame_every": frame_every, "exposure": exposure, "v_fast": v_fast}.items():
        if not (float(v_) > 0.0):
            raise ValueError("pegtactile_episode_run: %s must be > 0" % k_)
    t_wall = time.perf_counter()
    kp = PS._kp(kp)
    if mu is not None:
        kp = dict(kp, mu=float(mu))
    pad = pad_params() if pad is None else _pad(pad)
    sc = PF.pegfail_scene_build(kp)
    m, d, ids = sc["model"], sc["data"], sc["ids"]
    qa = ids["qadr"]
    psi = math.radians(float(azimuth_deg))
    th0 = math.radians(float(tilt_deg))
    m.qpos_spring[qa["wry"]] = th0 * math.cos(psi)
    d.qpos[qa["wry"]] = th0 * math.cos(psi)
    m.qpos_spring[qa["wrx"]] = -th0 * math.sin(psi)
    d.qpos[qa["wrx"]] = -th0 * math.sin(psi)
    eps = (eps_mm[0] * math.cos(psi) - eps_mm[1] * math.sin(psi), eps_mm[0] * math.sin(psi) + eps_mm[1] * math.cos(psi))
    mujoco.mj_forward(m, d)
    dt = float(m.opt.timestep)
    cid = m.body("carriage").id
    frames = []
    phase = ["approach"]
    expo = collections.deque(maxlen=max(1, int(round(float(exposure) / dt))))

    def kind_now(cons, tip, a, depth):
        tip_side = mouth_side = cham = 0
        for c in cons:
            if c["kind"] not in ("wall", "chamfer"):
                continue
            if float((c["pos"] - tip) @ a) < 1.5e-3:
                tip_side += 1
                cham += int(c["kind"] == "chamfer")
            else:
                mouth_side += 1
        if any(c["kind"] == "floor" for c in cons):
            return "floor"
        if tip_side and mouth_side:
            return "two_point"
        if tip_side or mouth_side:
            return "chamfer" if (cham and not mouth_side and depth < kp["chamfer"]) else "one_point"
        return "plate" if cons else "none"

    def step():
        mujoco.mj_step(m, d)
        cons = PF._contacts(sc)
        wr = _wrench_on_peg(sc, cons, pad)
        expo.append((wr["Fc"], wr["Mc"], kind_now(cons, wr["tip"], wr["axis"], -float(wr["tip"][2]))))

    def snap():
        obs = PF._observe(sc, np.zeros(2))
        cons = PF._contacts(sc)
        wr = _wrench_on_peg(sc, cons, pad)
        inst = {"Fc_inst": wr["Fc"].copy(), "Mc_inst": wr["Mc"].copy(), "state_inst": obs["contact_kind"]}
        if expo:
            Fc = np.mean([e[0] for e in expo], axis=0)
            Mc = np.mean([e[1] for e in expo], axis=0)
            kinds = [e[2] for e in expo if e[2] != "none"]
            state = max(set(kinds), key=kinds.count) if kinds else "none"
            Fg = np.array([0.0, 0.0, -pad["peg_mass"] * 9.81])
            Mg = np.cross(wr["com"] - wr["g"], Fg)
            wr.update(Fc=Fc, Mc=Mc, F_pad_w=-(Fc + Fg), M_pad_w=-(Mc + Mg))
            wr.update(F_pad=wr["Rw"].T @ wr["F_pad_w"], M_pad=wr["Rw"].T @ wr["M_pad_w"])
            duty = len(kinds) / len(expo)
        else:
            state, duty = obs["contact_kind"], 1.0
        q = d.qpos
        fr = {"t": float(d.time), "phase": phase[0], "state": state, "duty": duty, **inst, "depth": obs["depth"], "tilt": obs["tilt"],
              "contacts": [{"pos": c["pos"].copy(), "f": c["f_world"].copy(), "kind": c["kind"], "fn": c["fn"],
                            "normal": c["normal"].copy()} for c in cons],
              "q_slide": np.array([q[qa["wx"]], q[qa["wy"]], q[qa["wz"]]]),
              "q_hinge": np.array([q[qa["wrx"]], q[qa["wry"]], q[qa["wrz"]]]),
              "q_rest": np.array([m.qpos_spring[qa["wrx"]], m.qpos_spring[qa["wry"]], m.qpos_spring[qa["wrz"]]]),
              "carriage": d.xpos[cid].copy(), "sensor_force": obs["sensor_force"].copy(), "sensor_torque": obs["sensor_torque"].copy(),
              "vel_z": float(d.qvel[m.jnt_dofadr[m.joint("cz").id]]), **wr}
        if render_wrist:
            img = PF._render(sc, "wrist", depth=True)
            cam_w = -img["R"].T @ img["t"]
            try:
                fr["cam"] = wrist_deflection_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], cam_w,
                                                       d.xpos[cid].copy(), kp["r"])
            except ValueError as exc:
                fr["cam"] = None
                fr["cam_error"] = repr(exc)
            if keep_images:
                fr["wrist"] = {"rgb": img["rgb"]}
        if render_side:
            import render3d
            if "_cut" not in sc:
                mc = mujoco.MjModel.from_xml_string(pegtactile_cutaway_xml(sc["xml"]))
                sc["_cut"] = {"m": mc, "d": mujoco.MjData(mc), "ren": mujoco.Renderer(mc, height=400, width=480)}
            cu = sc["_cut"]
            cu["d"].qpos[:] = d.qpos
            mujoco.mj_forward(cu["m"], cu["d"])
            cu["ren"].update_scene(cu["d"], camera="cut")
            cidc = cu["m"].camera("cut").id
            ext = PS.camera_world_to_cv(cu["d"].cam_xmat[cidc].reshape(3, 3), cu["d"].cam_xpos[cidc])
            fr["side"] = {"rgb": cu["ren"].render().copy(), "K": render3d.intrinsics_from_fov(34.0, 480, 400), "R": ext["R"], "t": ext["t"]}
        frames.append(fr)
        return fr

    def settle(n_steps, record=False):
        last = d.time
        for _ in range(int(n_steps)):
            step()
            if record and d.time - last >= frame_every - 1e-9:
                last = d.time
                snap()

    try:
        settle(0.4 / dt)
        for _ in range(3):
            tip = d.site_xpos[ids["tip"]]
            d.ctrl[0] += eps[0] * 1e-3 - tip[0]
            d.ctrl[1] += eps[1] * 1e-3 - tip[1]
            settle(0.3 / dt)
        phase[0] = "descend"
        snap()
        status = "timeout"
        t0 = d.time
        hist = []
        last_rec = d.time
        while d.time - t0 < t_max:
            cons = PF._contacts(sc)
            fsum = sum(c["fn"] for c in cons)
            tip_now = d.site_xpos[ids["tip"]][2]
            vv = v if (cons or tip_now < 1.0e-3) else v_fast
            if fsum <= f_max:
                d.ctrl[2] -= vv * dt * 20
            for _ in range(20):
                step()
            tip_z = d.site_xpos[ids["tip"]][2]
            hist.append((d.time, -tip_z))
            if d.time - last_rec >= frame_every - 1e-9:
                last_rec = d.time
                snap()
            if -tip_z >= stop_depth:
                status = "inserted"
                break
            if release and -tip_z > kp["chamfer"] + 0.5e-3:
                old = [z for (t, z) in hist if t <= d.time - stall_window]
                if old and (-tip_z - old[-1]) < stall_min:
                    status = "stalled"
                    break
        if release and status == "stalled":
            phase[0] = "stalled"
            snap()
            phase[0] = "release"
            d.ctrl[2] += float(d.qpos[qa["wz"]])
            settle(0.6 / dt)
            snap()
            phase[0] = "pulled"
            d.ctrl[2] += 2e-3
            settle(0.6 / dt)
            snap()
    finally:
        PF._scene_close(sc)
        if "_cut" in sc:
            sc["_cut"]["ren"].close()
    return {"frames": frames, "kp": kp, "pad": pad, "wall_s": time.perf_counter() - t_wall, "sim_s": float(d.time), "status": status,
            "eps_mm": tuple(eps), "tilt_deg": float(tilt_deg), "azimuth_deg": float(azimuth_deg)}


def _synth_read_key(P, q, tq):
    return (round(float(P), 9), round(float(q[0]), 9), round(float(q[1]), 9), round(float(tq), 12))


def _synth_read(P, q, pad, ctx, tq=0.0):
    """合成 → 読み戻し(決定論なので同じ荷重は同じ結果: 空中のフレーム = 重力だけの荷重は 1 回だけ計算する)。"""
    key = _synth_read_key(P, q, tq)
    cache = ctx.setdefault("_sr_cache", {})
    if key not in cache:
        if len(cache) > 4 and not ctx.get("_sr_keep"):
            for k in list(cache)[:-2]:
                cache.pop(k)
        fr = pad_tactile_frame(P, q, pad, ctx, torsion=tq)
        rd = pad_tactile_read(fr, pad, ctx)
        rd.pop("track", None)
        cache[key] = ({"truth": fr["truth"]}, rd)
    return cache[key]


_W: dict = {}


def _worker_init(pad):
    _W["pad"] = pad
    _W["ctx"] = pad_context(pad)


def _worker_job(key):
    P, q0, q1, tq = key
    try:
        fr = pad_tactile_frame(P, (q0, q1), _W["pad"], _W["ctx"], torsion=tq)
        rd = pad_tactile_read(fr, _W["pad"], _W["ctx"])
    except MemoryError:                                       # 機械全体のコミット上限で落ちたら親が逐次でやり直す
        return key, None, None
    rd.pop("track", None)
    return key, {"truth": fr["truth"]}, rd                   # 像は持ち帰らない(1,700 枚で 1.3 GB)


def pegtactile_prefetch(episodes, pad: dict, ctx=None, workers: int = 0, torsion: bool = True, log=None) -> int:
    """全走行の全フレームのパッド荷重(決定論)を先に集め、未計算のものを ``workers`` 個のプロセスで合成 → 読み戻して ``ctx`` の
    キャッシュに入れる(結果は逐次と同じ: 同じ関数を同じ入力で呼ぶだけ)。``workers`` ≤ 1 は逐次。ワーカーがメモリ不足で落ちた分は
    逐次でやり直す。``log`` は進捗の文字列を受ける関数。返り = 新しく計算した数。**Raises** ValueError: episodes が列でない、
    ctx が無い(キャッシュの置き場が要る)。"""
    pad = _pad(pad)
    if ctx is None or not isinstance(ctx, dict) or "pts_flat" not in ctx:
        raise ValueError("pegtactile_prefetch: ctx (pad_context) is required to hold the cache")
    if not isinstance(episodes, (list, tuple)):
        raise ValueError("pegtactile_prefetch: episodes must be a list of pegtactile_episode_run results")
    say = log if callable(log) else (lambda s: None)
    keys = []
    for ep in episodes:
        for fr in ep["frames"]:
            loads = peg_wrench_to_pad_loads(fr["F_pad"], fr["M_pad"], pad)
            tq = loads["R"]["torsion"] if torsion else 0.0
            for side in ("R", "L"):
                keys.append(_synth_read_key(loads[side]["P"], loads[side]["q"], tq))
    cache = ctx.setdefault("_sr_cache", {})
    todo = sorted(set(k for k in keys if k not in cache))
    ctx["_sr_keep"] = True
    if not todo:
        return 0
    n_all = len(todo)
    if int(workers) > 1 and len(todo) > 8:
        from concurrent.futures import ProcessPoolExecutor
        try:
            with ProcessPoolExecutor(max_workers=int(workers), initializer=_worker_init, initargs=(pad,)) as ex:
                for key, fr, rd in ex.map(_worker_job, todo, chunksize=4):
                    if rd is not None:
                        cache[key] = (fr, rd)
        except Exception as exc:  # noqa: BLE001  プールごと壊れたら(初期化のメモリ不足など)残りを逐次で
            say("pool failed: %r -> the rest sequentially" % (exc,))
        todo = [k for k in todo if k not in cache]
        if todo:
            say("%d jobs failed in workers -> sequentially" % len(todo))
    for key in todo:
        fr = pad_tactile_frame(key[0], (key[1], key[2]), pad, ctx, torsion=key[3])
        rd = pad_tactile_read(fr, pad, ctx)
        rd.pop("track", None)
        cache[key] = ({"truth": fr["truth"]}, rd)
    return n_all


def _rot_z_to(a):
    """ẑ を a へ最短で回す回転(ロールは 0 と置く: 円柱のロールはカメラに見えない)。"""
    a = np.asarray(a, np.float64) / np.linalg.norm(a)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, a)
    s_ = float(np.linalg.norm(v))
    c = float(z @ a)
    if s_ < 1e-12:
        return np.eye(3)
    k = v / s_
    Km = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s_ * Km + (1 - c) * Km @ Km


def _tactile_wrench(fr, pad, ctx, Rw, com_minus_g, torsion: bool = True):
    """1 フレームのパッド荷重(真値のレンチから)→ 膜の像 2 枚 → 読み戻し → ペグが穴から受けるレンチ(世界系、把持点まわり)。
    ``Rw`` = グリッパの姿勢(推定値を渡す)。``torsion=False`` はパッドのねじりを合成も読みもしない(二本指の対称性の破れを測る対照)。"""
    loads = peg_wrench_to_pad_loads(fr["F_pad"], fr["M_pad"], pad)
    tq = loads["R"]["torsion"] if torsion else 0.0
    frR, rdR = _synth_read(loads["R"]["P"], loads["R"]["q"], pad, ctx, tq)
    frL, rdL = _synth_read(loads["L"]["P"], loads["L"]["q"], pad, ctx, tq)
    tq_hat = 0.5 * (rdR["torsion"] + rdL["torsion"]) if torsion else 0.0
    est = pad_loads_to_peg_wrench(rdR["P"], rdR["q"], rdL["P"], rdL["q"], pad, torsion=tq_hat)
    Fg = np.array([0.0, 0.0, -pad["peg_mass"] * 9.81])
    F_hat = -(Rw @ est["F"]) - Fg
    M_hat = -(Rw @ est["M"]) - np.cross(com_minus_g, Fg)
    return {"loads": loads, "reads": {"R": rdR, "L": rdL}, "F": F_hat, "M": M_hat,
            "asym": pad_shear_asymmetry(rdR["q"], rdL["q"]), "asym_true": pad_shear_asymmetry(loads["R"]["q"], loads["L"]["q"])}


def _map_state(s):
    """MuJoCo の接触の種別(pegfail の語彙)→ 判定の語彙。plate / floor はこの走行では出ない(出たら 'other')。"""
    return {"none": "none", "chamfer": "chamfer", "one_point": "one_point", "two_point": "two_point"}.get(s, "other")


def pegtactile_process_episode(ep: dict, pad: dict, ctx=None, use_camera: bool = True, torsion: bool = True, tau: float = 0.35,
                               f_air: float = 0.05, tol: float = 0.08e-3, qs_dF: float = 0.02, qs_dx: float = 10e-6) -> dict:
    """後処理(numpy だけ、mujoco 不要。入力は :func:`pegtactile_episode_run` の結果): 2 段。

    1 段目 = 各フレームの手首カメラ(軸の直線)と触覚のレンチ(膜 2 枚の合成 → 読み)→ k を当てるフレーム(触覚が 3 フレーム続けて
    二点と言った所 = 両側から拘束されて跳ねない、触覚から観測できる条件)で手首剛性 k̂。手首の z 圧縮はカメラに見えないので、
    軸の直線を z = 0 で切った点 p₀ = [(F)_xy − (a_xy/a_z)(F)_z]/k のまま k について線形に解く。2 段目 = k̂ と触覚の F_z で z 圧縮を補い、
    カメラの軸から先端・把持点の姿勢を推定 → 接触状態(触覚のレンチ + 推定姿勢)と、回転剛性 k̂_r(ヒンジまわりのモーメント vs 傾き)。
    同じ規則を真値のレンチ + 真値の姿勢に当てた状態(上限)も並べる。k が決まらなければ(フレーム不足)``k_error`` に理由を残し、
    姿勢は z 圧縮 0 で置いて ``pose_no_k`` の印(fail-closed)。返り ``rows``(フレームごと: 真値と推定の状態・レンチ・姿勢)、
    ``k_fit``・``k_fit_qs``・``k_fit_true_force``・``kr_fit``・``k_sel``・``qs``。**Raises** ValueError: ep に frames が無い。"""
    pad = _pad(pad)
    ctx = _ctx_for(pad, ctx)
    if not isinstance(ep, dict) or "frames" not in ep or "kp" not in ep:
        raise ValueError("pegtactile_process_episode: ep must be the dict from pegtactile_episode_run")
    kp = ep["kp"]
    L, gb, cb = kp["peg_length"], pad["grasp_below_top"], pad["com_below_top"]
    Fg = np.array([0.0, 0.0, -pad["peg_mass"] * 9.81])
    rows = []
    for fr in ep["frames"]:
        row = {"t": fr["t"], "phase": fr["phase"], "state_true": _map_state(fr["state"]), "depth_true": fr["depth"], "tilt_true": fr["tilt"]}
        cam = fr.get("cam") if use_camera else None
        a = cam["axis"] if cam is not None else fr["axis"]
        Rw = _rot_z_to(a) if cam is not None else fr["Rw"]
        tw = _tactile_wrench(fr, pad, ctx, Rw, -(cb - gb) * a, torsion=torsion)
        row.update(cam=cam, axis_hat=a, tw=tw)
        if cam is not None:
            Ft = tw["F"] + Fg
            row["p0"] = np.array([cam["dx"], cam["dy"]])
            row["F_eff"] = Ft[:2] - a[:2] / a[2] * Ft[2]
            Ftrue = fr["Fc"] + Fg
            row["F_eff_true"] = Ftrue[:2] - fr["axis"][:2] / fr["axis"][2] * Ftrue[2]
            q = fr["q_slide"]
            row["p0_true"] = q[:2] - q[2] * a[:2] / a[2]
            row["dtheta"] = np.array([cam["tilt_x"] - fr["q_rest"][0], cam["tilt_y"] - fr["q_rest"][1]])
        rows.append(row)
    out = {"rows": rows, "k_fit": None}
    k = None
    if use_camera and rows and all(r_["cam"] is not None for r_ in rows):
        p0 = np.array([r_["p0"] for r_ in rows])
        Fe = np.array([r_["F_eff"] for r_ in rows])
        qs = np.zeros(len(rows), bool)
        for i in range(1, len(rows) - 1):
            qs[i] = (np.abs(Fe[i] - Fe[i - 1]).max() < qs_dF and np.abs(Fe[i + 1] - Fe[i]).max() < qs_dF
                     and np.abs(p0[i] - p0[i - 1]).max() < qs_dx and np.abs(p0[i + 1] - p0[i]).max() < qs_dx
                     and rows[i]["phase"] == "descend")
        out["qs"] = qs
        stt0 = []
        for r_, fr in zip(rows, ep["frames"]):
            a = r_["axis_hat"]
            top0 = fr["carriage"] + np.array([r_["cam"]["dx"], r_["cam"]["dy"], 0.0])
            stt0.append(contact_state_from_wrench(kp, r_["tw"]["F"], r_["tw"]["M"], top0 - gb * a, top0 - L * a, a,
                                                  f_air=f_air, tau=tau, tol=tol, geometry=False)["state"])
        sel = np.array([i >= 2 and stt0[i] == stt0[i - 1] == stt0[i - 2] == "two_point" for i in range(len(rows))])
        out["k_sel"] = sel
        try:
            out["k_fit"] = wrist_stiffness_fit(p0[sel].ravel(), Fe[sel].ravel())
            out["k_fit_true_force"] = wrist_stiffness_fit(p0[sel].ravel(), np.array([r_["F_eff_true"] for r_ in rows])[sel].ravel())
            k = out["k_fit"]["k"]
        except ValueError as exc:
            out["k_error"] = repr(exc)
        try:
            out["k_fit_qs"] = wrist_stiffness_fit(p0[qs].ravel(), Fe[qs].ravel())
        except ValueError as exc:
            out["k_qs_error"] = repr(exc)
    for r_, fr in zip(rows, ep["frames"]):
        a = r_["axis_hat"]
        if k is not None and r_["cam"] is not None:
            Ft = r_["tw"]["F"] + Fg
            top = fr["carriage"] + np.array([r_["cam"]["dx"], r_["cam"]["dy"], 0.0]) + (Ft[2] / k / a[2]) * a
        elif r_["cam"] is not None:
            top = fr["carriage"] + np.array([r_["cam"]["dx"], r_["cam"]["dy"], 0.0])
            r_["pose_no_k"] = True
        else:
            top = fr["top"]
        tip, g = top - L * a, top - gb * a
        r_["tip_hat"], r_["g_hat"] = tip, g
        r_["tip_err"] = float(np.linalg.norm(tip - fr["tip"]))
        r_["st_tactile"] = contact_state_from_wrench(kp, r_["tw"]["F"], r_["tw"]["M"], g, tip, a, f_air=f_air, tau=tau, tol=tol)
        r_["st_wrench"] = contact_state_from_wrench(kp, fr["Fc"], fr["Mc"], fr["g"], fr["tip"], fr["axis"], f_air=f_air, tau=tau, tol=tol)
        if r_["cam"] is not None:
            # ヒンジ(= ペグ上端)まわりのモーメントを、k̂ で z 圧縮を補ったヒンジ点から作る(z = 0 と置くと二点の区間で腕が 2 mm ずれ
            # k_r が −14〜+5 % 振れた —— 試作で測った)
            r_["Mh"] = (r_["tw"]["M"] + np.cross(g - top, r_["tw"]["F"]) + np.cross(-cb * a, Fg))[:2]
            h_true = fr["carriage"] + fr["q_slide"]
            r_["Mh_true"] = (fr["Mc"] + np.cross(fr["g"] - h_true, fr["Fc"]) + np.cross(fr["com"] - h_true, Fg))[:2]
    if k is not None:
        sel = out["k_sel"]
        try:
            out["kr_fit"] = wrist_stiffness_fit(np.array([r_["dtheta"] for r_ in rows])[sel].ravel(),
                                                np.array([r_["Mh"] for r_ in rows])[sel].ravel(), min_span=1e-4)
            out["kr_fit_true"] = wrist_stiffness_fit(np.array([r_["dtheta"] for r_ in rows])[sel].ravel(),
                                                     np.array([r_["Mh_true"] for r_ in rows])[sel].ravel(), min_span=1e-4)
        except ValueError as exc:
            out["kr_error"] = repr(exc)
    return out
