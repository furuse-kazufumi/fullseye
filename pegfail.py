# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegfail — ペグ挿入の失敗検出と回復を、学習なしの「失敗分類表 × 接触計測」で閉じる(2026-10-04)。

物理シミュ × Fullseye 系列、pegsim(柔らかい手首のペグ挿入)の集大成。先行研究(Shirasaka, Beltran-Hernandez, Hamaya, Ushiku,
arXiv:2509.17666、ICRA 2026 予定、コードは未公開)は柔らかい手首の挿入を「接触形成 = 自由度を順に縛る接触状態列」として構造化し、
終端姿勢と画像から **VLM** が失敗モードを判定して回復スキルを選ぶ。本モジュールはその VLM の部分を **規則の表**に置き換える:
観測(接触点数・深さの停滞・手首の力とモーメント・傾き・穴中心からのずれ)を離散の署名にし、表の 1 行だけが当たれば失敗クラスと
回復プリミティブが決まる(当たらなければ ``"unknown"``、2 行当たれば表の欠陥 —— 検証器が先に止める)。真値は 2 つの外から:

  * **定理**: D. E. Whitney, "Quasi-Static Assembly of Compliantly Supported Rigid Parts", ASME J. Dyn. Sys. Meas. Control 104(1),
    65-77, 1982(原著は有料で未読。式は著者本人の MIT OCW 2.875 Class 3 スライド本文、pegsim の docstring と同じ出典)。
    くさび(wedging)θ > c/μ(p.28)、かじり(jamming)の平行四辺形 λ = l/(2rμ)(p.34)。本モジュールでは平行四辺形の 4 頂点を
    **二点接触の平面静力学(両点が下へ滑る Coulomb 摩擦の釣り合い)から導き直し**(:func:`jamming_parallelogram_planar`)、
    pegsim の頂点(OCW の値)と 1e-9 で一致させる —— 符号の規約(F_x の向き・M の向き)はこの導出で固定する。
  * **物理エンジン**: MuJoCo の接触(点・法線力)と手首の力センサ。mujoco が要る関数は facade(``pegfail_scene_build`` 以下)で、
    台帳(opsdrive ``pegfail``)には載せない。

numpy 層(台帳 ``pegfail``、16 op): :func:`insertion_failure_table` 表 / :func:`insertion_failure_validate` 到達性と排他 /
  :func:`insertion_signature` 観測 → 署名 / :func:`insertion_failure_classify` 表引き(fail-closed)/ :func:`insertion_recovery_primitive` /
  :func:`jamming_parallelogram_planar` / :func:`jamming_force_check` / :func:`wedging_risk` / :func:`insertion_stall_detect` /
  :func:`wrist_load_from_deflection` 手首ばねのたわみ → 先端の (F_x, F_z, M) / :func:`tip_force_ratios` / :func:`insertion_episode_summary` /
  :func:`failure_confusion` / :func:`vision_boundary_flip` 視覚の雑音で境目のクラスが反転する確率 / :func:`insertion_failure_presets` /
  :func:`pegfail_scene_mjcf`(MJCF 文字列、mujoco 不要)。
mujoco 層(facade のみ): :func:`pegfail_scene_build` / :func:`pegfail_episode_run`(失敗注入 → 検出 → 分類 → 回復の 1 走行)/
  :func:`pegfail_failure_grid`。

正直に: VLM との比較は作らない(無いものを並べない)。注入格子の 5/5 は各クラス 1 条件ずつで、論文の実機の成功率とは条件が違うので
並べない。「視覚の署名」は構えた時の手首 RGB-D の錨 + エンコーダ積分(穴に入った先端はカメラに写らない)。かじりの判定は停滞中・
F_z ≥ 1 N でだけ有効(動いている間は比が悪条件)。回復プリミティブは脚本(退避量・反復回数は決め打ち)。詰まりの向きは 1 配置。
触覚(tacslip)は使っていない。

規約: 長さ m、角 rad(引数名に _deg / _mm が付くものだけ度・mm)。穴の口の面 z = 0、穴の軸 = 世界 z。``depth`` は口の面からの
先端深さ。Whitney の l(二点接触の深さ)は最狭部から。先端まわりの力の規約は :func:`jamming_force_check` に書く。
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np

import pegsim as P

__all__ = [
    "FAILURE_CLASSES", "SIGNATURE_FIELDS", "insertion_failure_table", "insertion_failure_validate",
    "insertion_signature", "insertion_failure_classify", "insertion_recovery_primitive", "jamming_parallelogram_planar",
    "jamming_force_check", "wedging_risk", "insertion_stall_detect", "wrist_load_from_deflection", "tip_force_ratios",
    "insertion_episode_summary", "failure_confusion", "vision_boundary_flip", "insertion_failure_presets", "pegfail_scene_mjcf",
    # mujoco が要る(facade のみ、台帳の外)
    "pegfail_scene_build", "pegfail_episode_run", "pegfail_failure_grid",
]

#: 失敗クラスの語彙(nominal と seated は「失敗でない」、unknown は表に無い署名 = fail-closed の出口)
FAILURE_CLASSES = ("nominal", "chamfer_sliding", "missed_hole", "wrong_hole", "wedging", "jamming", "blocked_hole",
                   "seated", "unknown")

#: 署名の欄と取りうる値(表の行はこの語彙だけで書く。綴りを壊せば検証器が止める)
SIGNATURE_FIELDS = {
    "contact": ("none", "plate", "chamfer", "one_point", "two_point", "floor"),
    "zone": ("above", "mouth", "hole", "bottom"),
    "progress": ("advancing", "stalled"),
    "wedge": ("below", "over"),
    "jam": ("inside", "outside", "na"),
    "offset": ("small", "large"),
}

_ANY = "*"


# ----------------------------------------------------------------------------------------------------------------------
# 表
def insertion_failure_table() -> list:
    """失敗分類表(データ): 各行 = {``cls``, ``when``(欄 → 許す値の集合、``"*"`` = 何でも), ``recovery``, ``basis``}。

    行の根拠(``basis``)は Whitney 1982(OCW スライドの頁)か接触形成の幾何。順番に意味は無い —— 署名に当たる行は **高々 1 行**
    (:func:`insertion_failure_validate` が全ペアで確かめる)。回復プリミティブの語彙は :func:`insertion_recovery_primitive`。

    表(接触 / 深さの帯 / 進み / くさび / かじり / ずれ → クラス → 回復):
      * none|plate, above|mouth, stalled, *, *, large → ``missed_hole`` → lift_recentre(先端が面取りに乗れない |ε₀| > W + c_r、導出 (4))
      * chamfer, above|mouth, *, *, *, small → ``chamfer_sliding`` → continue(面取り通過は正常な過程、OCW p.26)
      * plate, above|mouth, advancing, *, *, * → ``nominal`` → continue(板に触れたがまだ進んでいる = 柔らかい接触の過渡)
      * chamfer|one_point|two_point|floor, *, *, *, *, large → ``wrong_hole`` → lift_reapproach(接触はあるが治具の目標穴から W + c_r 以上離れている)
      * one_point, mouth|hole, advancing, *, *, small → ``nominal`` → continue(一点接触で進む、p.26)
      * two_point, hole, advancing, *, *, small → ``nominal`` → continue(二点接触で進む = 平行四辺形の中、p.34)
      * two_point, hole, stalled, over, *, small → ``wedging`` → retract_reduce_tilt(θ > c/μ、p.28)
      * two_point, hole, stalled, below, outside, small → ``jamming`` → steer_force(力の比が平行四辺形の外、p.34)
      * one_point, mouth|hole, stalled, *, outside, small → ``jamming`` → steer_force(一点接触の摩擦限界 |F_x/F_z| > 1/μ = 縦の辺)
      * floor, hole, *, *, *, small → ``blocked_hole`` → lift_abort(底に届く前に硬い物に当たった)
      * floor, bottom, *, *, *, small → ``seated`` → stop(底着 = 完了)
      * none, *, advancing, *, *, * → ``nominal`` → continue(空中で降下中)
    当たらない例(わざと unknown): plate・stalled・small(面取りの内側で板に乗って止まるのは幾何的に不可能 = 計測の矛盾)、
    two_point・stalled・below・inside(Whitney なら滑るはずの停滞 = 模型の外)、none・stalled・small(押していないのに止まる)。"""
    T = []

    def row(cls, contact, zone, progress, wedge, jam, offset, recovery, basis):
        T.append({"cls": cls, "when": {"contact": contact, "zone": zone, "progress": progress, "wedge": wedge, "jam": jam,
                                       "offset": offset}, "recovery": recovery, "basis": basis})

    row("missed_hole", {"none", "plate"}, {"above", "mouth"}, {"stalled"}, _ANY, _ANY, {"large"}, "lift_recentre",
        "|eps0| > W + c_r: the tip rim cannot land on the chamfer (derived from OCW p.11 definitions, pegsim.chamfer_capture)")
    row("chamfer_sliding", {"chamfer"}, {"above", "mouth"}, _ANY, _ANY, _ANY, {"small"}, "continue",
        "chamfer crossing is a normal stage of the force history (OCW p.26); 'above' = the rim on the chamfer's top edge, soft contact")
    row("nominal", {"plate"}, {"above", "mouth"}, {"advancing"}, _ANY, _ANY, _ANY, "continue",
        "touching the plate while the descent still advances (soft-contact transient, not yet a stall)")
    row("wrong_hole", {"chamfer", "one_point", "two_point", "floor"}, _ANY, _ANY, _ANY, _ANY, {"large"}, "lift_reapproach",
        "contact with a hole whose centre is farther than W + c_r from the fixture target (even if seated there)")
    row("nominal", {"one_point"}, {"mouth", "hole"}, {"advancing"}, _ANY, _ANY, {"small"}, "continue",
        "one-point contact while advancing (OCW p.26)")
    row("nominal", {"two_point"}, {"hole"}, {"advancing"}, _ANY, _ANY, {"small"}, "continue",
        "two-point contact while advancing: applied force ratio inside the parallelogram (OCW p.34)")
    row("wedging", {"two_point"}, {"hole"}, {"stalled"}, {"over"}, _ANY, {"small"}, "retract_reduce_tilt",
        "two-point contact began with theta > c/mu: friction cones overlap, compressive force is stored (OCW p.28)")
    row("jamming", {"two_point"}, {"hole"}, {"stalled"}, {"below"}, {"outside"}, {"small"}, "steer_force",
        "(F_x/F_z, M/(r F_z)) outside the jamming parallelogram, lambda = l/(2 r mu) (OCW p.34)")
    row("jamming", {"one_point"}, {"mouth", "hole"}, {"stalled"}, _ANY, {"outside"}, {"small"}, "steer_force",
        "one-point friction limit |F_x/F_z| > 1/mu: the vertical edges of the parallelogram (OCW p.34)")
    row("blocked_hole", {"floor"}, {"hole"}, _ANY, _ANY, _ANY, {"small"}, "lift_abort",
        "hard stop before the hole depth: an obstruction, not a Whitney state")
    row("seated", {"floor"}, {"bottom"}, _ANY, _ANY, _ANY, {"small"}, "stop", "bottomed at the hole depth = done")
    row("nominal", {"none"}, _ANY, {"advancing"}, _ANY, _ANY, _ANY, "continue", "free descent")
    return T


def _row_values(spec, field):
    vals = SIGNATURE_FIELDS[field]
    if spec == _ANY:
        return set(vals)
    s = set(spec)
    bad = s - set(vals)
    if bad:
        raise ValueError("insertion_failure_table: field %r has values outside the vocabulary: %s" % (field, sorted(bad)))
    return s


def insertion_failure_validate(table=None) -> dict:
    """表を検証する(fail-closed): 欄の語彙・クラス名・回復名の綴り、**全ペアの排他**(2 行が同じ署名に当たり得ないか = 全欄で
    許す集合が交わる行の組が無い)、**到達性**(unknown 以外の全クラスに ≥ 1 行)。

    返り: ``n_rows``、``classes_covered``、``classes_missing``、``n_signatures``(語彙の直積の大きさ)、``n_covered``(どれかの行に
    当たる署名の数)、``coverage``、``overlaps``(交わる行の組 —— 空でなければ下の ValueError)。
    **Raises** ``ValueError``: 綴り違い・交わる行・届かないクラス。"""
    table = insertion_failure_table() if table is None else table
    if not isinstance(table, list) or not table or not all(isinstance(r, dict) for r in table):
        raise ValueError("insertion_failure_validate: table must be a non-empty list of rows")
    fields = list(SIGNATURE_FIELDS)
    sets = []
    for i, r in enumerate(table):
        for k in ("cls", "when", "recovery", "basis"):
            if k not in r:
                raise ValueError("insertion_failure_validate: row %d lacks %r" % (i, k))
        if r["cls"] not in FAILURE_CLASSES or r["cls"] == "unknown":
            raise ValueError("insertion_failure_validate: row %d has unknown class %r" % (i, r["cls"]))
        if set(r["when"]) != set(fields):
            raise ValueError("insertion_failure_validate: row %d fields %s != %s" % (i, sorted(r["when"]), fields))
        insertion_recovery_primitive(r["recovery"])
        sets.append({f: _row_values(r["when"][f], f) for f in fields})
    overlaps = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            if all(sets[i][f] & sets[j][f] for f in fields):
                overlaps.append((i, j))
    covered = set(r["cls"] for r in table)
    missing = sorted(set(FAILURE_CLASSES) - covered - {"unknown"})
    n_sig = int(np.prod([len(v) for v in SIGNATURE_FIELDS.values()]))
    n_cov = sum(int(np.prod([len(s[f]) for f in fields])) for s in sets)
    out = {"n_rows": len(table), "classes_covered": sorted(covered), "classes_missing": missing, "n_signatures": n_sig,
           "n_covered": n_cov, "coverage": n_cov / n_sig, "overlaps": overlaps}
    if overlaps:
        raise ValueError("insertion_failure_validate: rows overlap (same signature claimed twice): %s" % overlaps)
    if missing:
        raise ValueError("insertion_failure_validate: classes without a row: %s" % missing)
    return out


def insertion_recovery_primitive(name: str) -> dict:
    """回復プリミティブの表(クラス → 動作の記述)。``name`` は表の ``recovery`` の語。

    ``lift_recentre``: 先端を板の上 6 mm まで上げ、手首 RGB-D で (dx, dy) を測って搬送台を寄せ(≤ 6 回)、再降下。
    ``lift_reapproach``: 口の上 10 mm まで上げ、治具の目標座標へ搬送台を戻し、カメラで寄せて再降下。
    ``retract_reduce_tilt``: 4 mm 退避し、手首ヒンジの角度を測って把持の傾きをその分戻し(θ → 0)、再降下(p.28 の θ ≤ c/μ へ)。
    ``steer_force``: 平行四辺形の余裕を線形模型で見て、搬送台の横移動 0.5 mm(F_x と M = L_g F_x が一緒に動く)と手首の回転 0.5°
    (M だけが k_r Δ 動く)の組 3 × 3 から余裕が最大の組を選び、進むまで ≤ 6 歩(Whitney p.34: 力の比を図の中へ)。
    ``lift_abort``: 退避して終了(障害物は押しても取れない)。``continue``: 何もしない。``stop``: 完了。
    **Raises** ``ValueError``: 未知の名(綴り壊しは fail-closed)。"""
    prims = {
        "lift_recentre": {"lift_m": 6e-3, "servo_iters": 6, "gain": 0.8, "resume": True},
        "lift_reapproach": {"lift_m": 10e-3, "servo_iters": 6, "gain": 0.8, "goto_target": True, "resume": True},
        "retract_reduce_tilt": {"lift_m": 4e-3, "zero_tilt": True, "resume": True},
        "steer_force": {"step_m": 0.5e-3, "step_rad": math.radians(0.5), "max_steps": 6, "target_margin": 0.4, "resume": True},
        "lift_abort": {"lift_m": 10e-3, "resume": False, "terminal": "aborted"},
        "continue": {"resume": True},
        "stop": {"resume": False, "terminal": "seated"},
    }
    if not isinstance(name, str) or name not in prims:
        raise ValueError("insertion_recovery_primitive: unknown primitive %r (known: %s)" % (name, sorted(prims)))
    return dict(prims[name], name=name)


# ----------------------------------------------------------------------------------------------------------------------
# 署名と分類
def insertion_signature(obs, kp=None, stall=None, lateral_tol: float = 0.0) -> dict:
    """連続の観測を表の語彙の署名に離散化する。

    ``obs``: ``contact_kind``(``"none"|"plate"|"chamfer"|"one_point"|"two_point"|"floor"``)、``depth`` [m] (口の面から、負は空中)、
    ``stalled``(bool、:func:`insertion_stall_detect`)、``theta_onset``(二点接触が始まった時の傾き [rad]、無ければ ``tilt``)、
    ``fx_over_fz``・``m_over_rfz``(先端の力の比、F_z ≤ 0 なら None)、``depth_l``(Whitney の l = 最狭部からの深さ、省略時 depth − W)、
    ``offset`` [m] (先端の穴中心からの面内ずれ)。欄の境目: zone は depth < 0 → above、< W → mouth、< hole_depth − 1 mm → hole、
    それ以上 → bottom。wedge は θ_onset > c/μ → over。jam は two_point なら :func:`jamming_force_check` の ``inside``、one_point なら
    |F_x/F_z| ≤ 1/μ、それ以外・力が無い → na。offset は |ε| > W + c_r → large(:func:`pegsim.chamfer_capture`)。
    **Raises** ``ValueError``: 未知の contact_kind、depth が無い。"""
    kp = P._kp(kp)
    if not isinstance(obs, dict):
        raise ValueError("insertion_signature: obs must be a dict")
    ck = obs.get("contact_kind")
    if ck not in SIGNATURE_FIELDS["contact"]:
        raise ValueError("insertion_signature: contact_kind must be one of %s, got %r" % (SIGNATURE_FIELDS["contact"], ck))
    if "depth" not in obs:
        raise ValueError("insertion_signature: obs lacks 'depth'")
    depth = float(obs["depth"])
    W, Hd = kp["chamfer"], kp["hole_depth"]
    zone = "above" if depth < 0.0 else "mouth" if depth < W else "hole" if depth < Hd - 1e-3 else "bottom"
    stalled = bool(obs["stalled"]) if stall is None else bool(stall)
    th = float(obs.get("theta_onset", obs.get("tilt", 0.0)))
    wedge = "over" if th > P.whitney_clearance(kp)["theta_wedge"] else "below"
    jam = "na"
    x, y = obs.get("fx_over_fz"), obs.get("m_over_rfz")
    if x is not None and np.isfinite(x):
        if ck == "two_point" and y is not None and np.isfinite(y):
            ell = float(obs.get("depth_l", depth - W))
            jam = "inside" if jamming_force_check(kp, max(ell, 0.0), x, y, tol=lateral_tol)["inside"] else "outside"
        elif ck == "one_point":
            jam = "inside" if abs(float(x)) <= 1.0 / kp["mu"] + lateral_tol else "outside"
    eps = obs.get("offset")
    offset = "small" if eps is None else ("small" if P.chamfer_capture(kp, abs(float(eps)))["captured"] else "large")
    return {"contact": ck, "zone": zone, "progress": "stalled" if stalled else "advancing", "wedge": wedge, "jam": jam,
            "offset": offset}


def insertion_failure_classify(signature, table=None) -> dict:
    """署名を表で引く(fail-closed): 当たる行が 1 つならそのクラスと回復、0 なら ``"unknown"``(推測しない)、2 つ以上なら表の
    欠陥として ``ValueError``(:func:`insertion_failure_validate` が通した表では起きない)。

    署名の欄に語彙の外の値があれば ``ValueError``(綴り壊し)。返り: ``cls``、``recovery``、``row``(当たった行の添字、無ければ −1)、
    ``n_match``、``basis``。"""
    table = insertion_failure_table() if table is None else table
    if not isinstance(signature, dict):
        raise ValueError("insertion_failure_classify: signature must be a dict of the six fields")
    for f, vals in SIGNATURE_FIELDS.items():
        if f not in signature:
            raise ValueError("insertion_failure_classify: signature lacks field %r" % f)
        if signature[f] not in vals:
            raise ValueError("insertion_failure_classify: field %r = %r is outside the vocabulary %s" % (f, signature[f], vals))
    hits = [i for i, r in enumerate(table)
            if all(r["when"][f] == _ANY or signature[f] in r["when"][f] for f in SIGNATURE_FIELDS)]
    if len(hits) > 1:
        raise ValueError("insertion_failure_classify: %d rows match the same signature %s (table defect)" % (len(hits), hits))
    if not hits:
        return {"cls": "unknown", "recovery": None, "row": -1, "n_match": 0, "basis": "no row claims this signature"}
    r = table[hits[0]]
    return {"cls": r["cls"], "recovery": r["recovery"], "row": hits[0], "n_match": 1, "basis": r["basis"]}


# ----------------------------------------------------------------------------------------------------------------------
# Whitney の量(平面静力学からの導出と検査)
def jamming_parallelogram_planar(kp, depth: float) -> dict:
    """かじりの平行四辺形を **二点接触の平面静力学から導く**(pegsim.jamming_diagram の頂点 = OCW p.34 の値と突き合わせる第 2 経路)。

    平面(x 右、z 上)で、先端の縁が −x 側の壁に深さ l で触れ(法線力 f₁ ≥ 0、+x 向き)、+x 側の口の縁が胴に触れる(f₂ ≥ 0、−x 向き)。
    両点が下へ滑る Coulomb 摩擦(上向き μf)で、先端に加える (F_x, F_z 下向き正, M 反時計回り正) の釣り合いは
        F_x = f₂ − f₁、F_z = μ(f₁ + f₂)、M = μ r f₁ − (μ r + l) f₂
    → M/(rF_z) = −λ − μ(λ + 1)·(F_x/F_z)、λ = l/(2rμ)。鏡像の配置(先端が +x の壁)は +λ − μ(λ+1)x。f₁ = 0 / f₂ = 0 が
    |F_x/F_z| = 1/μ の縦の辺(一点接触の摩擦限界)。4 頂点 = 2 本の斜辺 × 2 本の縦辺の交点 = (−1/μ, 2λ+1), (1/μ, −1), (1/μ, −(2λ+1)),
    (−1/μ, 1)(OCW の順)。返り: ``lambda``、``slope`` = −μ(λ+1)、``vertices``(4, 2)、``line_minus``・``line_plus``(切片)。
    **Raises** ``ValueError``: l < 0、μ ≤ 0。"""
    kp = P._kp(kp)
    ell, mu, r = float(depth), kp["mu"], kp["r"]
    if ell < 0.0:
        raise ValueError("jamming_parallelogram_planar: depth must be >= 0")
    if mu <= 0.0:
        raise ValueError("jamming_parallelogram_planar: mu must be > 0")
    lam = ell / (2.0 * r * mu)
    s = -mu * (lam + 1.0)

    def on_line(c0, x):
        return c0 + s * x

    xm, xp = -1.0 / mu, 1.0 / mu
    verts = np.array([[xm, on_line(lam, xm)], [xp, on_line(lam, xp)], [xp, on_line(-lam, xp)], [xm, on_line(-lam, xm)]])
    return {"lambda": lam, "slope": s, "vertices": verts, "line_minus": -lam, "line_plus": lam, "fx_limit": 1.0 / mu}


def jamming_force_check(kp, depth: float, fx_over_fz: float, m_over_rfz: float, tol: float = 0.0, side: int = 0) -> dict:
    """計測した先端の力の比 (F_x/F_z, M/(rF_z)) が Whitney の平行四辺形の内側か(pegsim.jamming_diagram を包み、どの辺に近いか・
    どちらの斜辺が今の接触配置に効くかを足す)。

    **規約**(:func:`jamming_parallelogram_planar` の導出で固定): e_x は「先端が触れている壁から反対側の口の縁へ」向かう水平単位
    ベクトル、F_x はその向きの成分、F_z は押し込み(下向き)正、M = M⃗·(e_x × e_z)(x 右・z 上の平面で反時計回り正)。この規約で
    今の配置に効く斜辺は切片 −λ の線(``side=-1``)。``side=+1`` は鏡像、``side=0`` は両方(平行四辺形の全体)。
    ``tol`` は内側判定の余裕(負なら厳しく)。返り: ``inside``、``margin``(4 辺の最小余裕、負なら外)、``edge``(最小余裕の辺の名)、
    ``margins``(dict)、``lambda``、``active_line``。**Raises** ``ValueError``: 力の比が有限でない。"""
    kp = P._kp(kp)
    x, y = float(fx_over_fz), float(m_over_rfz)
    if not (np.isfinite(x) and np.isfinite(y)):
        raise ValueError("jamming_force_check: force ratios must be finite (is F_z > 0?)")
    pg = jamming_parallelogram_planar(kp, depth)
    lam, s, mu = pg["lambda"], pg["slope"], kp["mu"]
    margins = {"fx_plus": 1.0 / mu - x, "fx_minus": x + 1.0 / mu, "line_plus": (lam + s * x) - y, "line_minus": y - (-lam + s * x)}
    if side == -1:
        margins.pop("line_plus")
    elif side == 1:
        margins.pop("line_minus")
    elif side != 0:
        raise ValueError("jamming_force_check: side must be -1, 0 or 1")
    edge = min(margins, key=margins.get)
    m = margins[edge]
    ref = P.jamming_diagram(kp, depth, x, y)
    return {"inside": bool(m + tol >= 0.0), "margin": float(m), "edge": edge, "margins": margins, "lambda": lam,
            "active_line": "line_minus", "pegsim_inside": ref["inside"], "pegsim_margin": ref["margin"]}


def wedging_risk(kp, theta: float, margin_deg: float = 0.5) -> dict:
    """傾き θ [rad] のくさびの危険度: 境目 c/μ(OCW p.28)に対する比 θ/(c/μ) と、余裕 ``margin_deg`` を見た 3 段(``safe`` /
    ``near`` / ``over``)。pegsim.wedging_check を包み、``theta_limit_deg``・``headroom_deg`` = c/μ − θ を度で足す。
    μ = 0 では境目が inf で常に safe。**Raises** ``ValueError``: θ < 0、margin_deg < 0。"""
    kp = P._kp(kp)
    th = float(theta)
    if th < 0.0 or float(margin_deg) < 0.0:
        raise ValueError("wedging_risk: theta and margin_deg must be >= 0")
    wc = P.wedging_check(kp, th)
    lim = wc["theta_limit"]
    head = math.degrees(lim - th) if np.isfinite(lim) else math.inf
    level = "over" if wc["possible"] else ("near" if head <= float(margin_deg) else "safe")
    return {"level": level, "ratio": (th / lim) if np.isfinite(lim) and lim > 0 else 0.0, "theta_deg": math.degrees(th),
            "theta_limit_deg": math.degrees(lim) if np.isfinite(lim) else math.inf, "headroom_deg": head,
            "lambda": wc["lambda"], "possible": wc["possible"]}


# ----------------------------------------------------------------------------------------------------------------------
# 停滞の検出・手首の力
def insertion_stall_detect(depth, window: int = 30, min_advance: float = 0.05e-3, arm_advance: float = 0.5e-3) -> dict:
    """深さの時系列 [m] から停滞を検出する(各刻 i で depth[i] − depth[i − window] < min_advance なら stalled)。

    降下が始まる前(構えている間)は深さが一定で、素朴な検出器は鳴る —— ``arm_advance`` だけ進んでから **武装**する(onset はそれ以後の
    最初の stalled)。返り: ``stalled``(bool の列、同じ長さ)、``onset``(最初の停滞の添字、無ければ −1)、``armed_at``(武装した添字、
    −1 なら武装せず = 一度も進まなかった)、``n_stalled``。単調降下(速度 ≥ min_advance/window)では鳴らない(門)。
    **Raises** ``ValueError``: window < 1、min_advance ≤ 0、系列が空。"""
    z = np.asarray(depth, np.float64).reshape(-1)
    w = int(window)
    if z.size == 0:
        raise ValueError("insertion_stall_detect: empty depth series")
    if w < 1 or float(min_advance) <= 0.0:
        raise ValueError("insertion_stall_detect: window >= 1 and min_advance > 0 required")
    st = np.zeros(z.size, bool)
    armed_at = -1
    z0 = z[0]
    for i in range(z.size):
        if armed_at < 0 and z[i] - z0 >= float(arm_advance):
            armed_at = i
        if armed_at >= 0 and i >= armed_at + w:
            st[i] = (z[i] - z[i - w]) < float(min_advance)
    idx = np.nonzero(st)[0]
    return {"stalled": st, "onset": int(idx[0]) if idx.size else -1, "armed_at": int(armed_at), "n_stalled": int(st.sum()),
            "window": w, "min_advance": float(min_advance)}


def wrist_load_from_deflection(kp, q_slide, q_hinge, q_hinge_rest, tip_xyz, axis, lg: float | None = None,
                               peg_mass: float = 0.04, com_from_tip: float | None = None, gravity: float = 9.81) -> dict:
    """手首ばねのたわみから、支持(+ 重力)がペグに加える荷重を先端まわりで(numpy だけ): F⃗ = −k_t q_slide − m g ẑ、
    M⃗_tip = −k_r (q_hinge − rest) + (p_hinge − p_tip) × F⃗_spring + (p_com − p_tip) × F⃗_g。

    ``q_slide`` = (wx, wy, wz) [m] (搬送台に対する手首の並進、搬送台は回らないので世界軸)、``q_hinge`` = (wrx, wry, wrz) [rad]、
    ``q_hinge_rest`` = ばねの静止角(把持の傾き)、``lg`` = 先端からヒンジまで(None → ペグ長)、``com_from_tip`` = 重心の先端からの
    距離(None → 既定のペグ 0.03 kg @ L/2 + 頭 0.01 kg @ L + 3 mm の重心)。ヒンジ 3 軸のトルクはヒンジの軸が世界軸に揃う
    小角(手首の回りは 5° 以下)の近似で世界ベクトルとして足す。返り: ``F``(3,)、``M_tip``(3,)、``F_spring``、``M_hinge``。
    **Raises** ``ValueError``: 形が違う、軸がゼロ。"""
    kp = P._kp(kp)
    q = np.asarray(q_slide, np.float64).reshape(-1)
    qh = np.asarray(q_hinge, np.float64).reshape(-1)
    qr = np.asarray(q_hinge_rest, np.float64).reshape(-1)
    tip = np.asarray(tip_xyz, np.float64).reshape(-1)
    a = np.asarray(axis, np.float64).reshape(-1)
    if q.shape != (3,) or qh.shape != (3,) or qr.shape != (3,) or tip.shape != (3,) or a.shape != (3,):
        raise ValueError("wrist_load_from_deflection: q_slide, q_hinge, q_hinge_rest, tip_xyz, axis must be 3-vectors")
    na = float(np.linalg.norm(a))
    if na < 1e-12:
        raise ValueError("wrist_load_from_deflection: axis is zero")
    a = a / na
    if a[2] < 0:
        a = -a
    L = kp["peg_length"]
    lg = L if lg is None else float(lg)
    if com_from_tip is None:
        com_from_tip = (0.03 * (L / 2) + 0.01 * (L + 3e-3)) / 0.04
    F_spring = -kp["k_trans"] * q
    M_hinge = -kp["k_rot"] * (qh - qr)
    F_g = np.array([0.0, 0.0, -float(peg_mass) * float(gravity)])
    r_h = lg * a
    r_c = float(com_from_tip) * a
    M_tip = M_hinge + np.cross(r_h, F_spring) + np.cross(r_c, F_g)
    return {"F": F_spring + F_g, "M_tip": M_tip, "F_spring": F_spring, "M_hinge": M_hinge, "F_g": F_g, "lg": lg}


def tip_force_ratios(kp, F, M_tip, e_x) -> dict:
    """先端の荷重 (F⃗, M⃗) を Whitney の比に: x = F⃗·e_x / F_z、y = M⃗·(e_x × ẑ) / (r F_z)、F_z = −F⃗·ẑ(押し込み正)。
    F_z ≤ 1e-6 N なら比は None(割れない)。``e_x`` は水平の単位ベクトル(:func:`jamming_force_check` の規約)。
    **Raises** ``ValueError``: e_x に水平成分が無い。"""
    kp = P._kp(kp)
    F = np.asarray(F, np.float64).reshape(3)
    M = np.asarray(M_tip, np.float64).reshape(3)
    ex = np.asarray(e_x, np.float64).reshape(3).copy()
    ex[2] = 0.0
    n = float(np.linalg.norm(ex))
    if n < 1e-12:
        raise ValueError("tip_force_ratios: e_x must have a horizontal component")
    ex = ex / n
    ez = np.array([0.0, 0.0, 1.0])
    Fz = -float(F @ ez)
    nrm = np.cross(ex, ez)
    if Fz <= 1e-6:
        return {"fx_over_fz": None, "m_over_rfz": None, "F_z": Fz, "F_x": float(F @ ex), "M": float(M @ nrm)}
    return {"fx_over_fz": float(F @ ex) / Fz, "m_over_rfz": float(M @ nrm) / (kp["r"] * Fz), "F_z": Fz,
            "F_x": float(F @ ex), "M": float(M @ nrm)}


# ----------------------------------------------------------------------------------------------------------------------
# 集計
def failure_confusion(true_cls, pred_cls, classes=FAILURE_CLASSES) -> dict:
    """混同行列と正答率: 行 = 注入(真)のクラス、列 = 分類。``classes`` の外の名は ValueError(綴り壊し)。
    返り: ``matrix``(n, n) int、``classes``、``accuracy``、``n``、``per_class_recall``(真の各クラスの再現率、無い行は nan)。"""
    try:
        t = [str(c) for c in true_cls]
        p = [str(c) for c in pred_cls]
    except TypeError as exc:
        raise ValueError("failure_confusion: true_cls and pred_cls must be sequences of class names") from exc
    if len(t) != len(p):
        raise ValueError("failure_confusion: true and pred lengths differ (%d vs %d)" % (len(t), len(p)))
    idx = {c: i for i, c in enumerate(classes)}
    for c in t + p:
        if c not in idx:
            raise ValueError("failure_confusion: class %r is not in %s" % (c, classes))
    M = np.zeros((len(classes), len(classes)), int)
    for a, b in zip(t, p):
        M[idx[a], idx[b]] += 1
    n = len(t)
    rec = np.array([M[i, i] / M[i].sum() if M[i].sum() else np.nan for i in range(len(classes))])
    return {"matrix": M, "classes": tuple(classes), "accuracy": (float(np.trace(M)) / n) if n else float("nan"), "n": n,
            "per_class_recall": rec}


def insertion_episode_summary(ep) -> dict:
    """1 走行の記録(:func:`pegfail_episode_run` の返り、または同じ鍵の dict)を要約: 注入クラス、最初に**検出**された失敗クラス、
    検出の遅れ(真の失敗の始まり ``failing_onset_tick`` → 検出の刻、刻 = 10 ms)、回復の回数と成否、最終深さ・最大力。

    ``ep["rec"]`` は列 ``depth``・``cls_truth``・``detected``・``force`` を持つ dict。返り: ``injected``、``first_cls``、``first_cls_tick``、
    ``stall_onset_tick``(= 使った onset)、``latency_ticks``(nan なら検出なし)、``recoveries``、``success``、``status``、
    ``final_depth_mm``、``max_force_N``、``classes_seen``。"""
    if not isinstance(ep, dict) or not isinstance(ep.get("rec"), dict) or "cls_truth" not in ep["rec"] or "depth" not in ep["rec"]:
        raise ValueError("insertion_episode_summary: ep must be the dict from pegfail_episode_run (with rec.cls_truth / rec.depth)")
    rec = ep["rec"]
    cls = list(rec["cls_truth"])
    det = list(rec.get("detected", [False] * len(cls)))
    first = next(((i, c) for i, (c, dt) in enumerate(zip(cls, det)) if dt), None)
    onset = int(ep.get("failing_onset_tick", ep.get("stall_onset_tick", -1)))
    lat = float("nan")
    if first is not None and onset >= 0:
        lat = float(first[0] - onset)
    return {"injected": ep.get("injected", "none"), "first_cls": first[1] if first else "none",
            "first_cls_tick": first[0] if first else -1, "stall_onset_tick": onset, "latency_ticks": lat,
            "recoveries": int(len(ep.get("recoveries", []))), "success": bool(ep.get("success", False)),
            "status": ep.get("status", "?"), "final_depth_mm": float(rec["depth"][-1]) * 1e3 if len(rec["depth"]) else float("nan"),
            "max_force_N": float(max(rec["force"])) if rec.get("force") else float("nan"),
            "classes_seen": sorted(set(cls))}


def vision_boundary_flip(kp, eps_true, sigma: float, n: int = 2000, seed: int = 0) -> dict:
    """「どこで壊れるか」: 真のずれ ε に標準偏差 σ の計測雑音を足したとき、offset の欄(small/large、境目 W + c_r)が真と**反転する**
    確率を各 ε で数える(numpy だけ)。境目から σ の何倍離れているか(``z``)と理論値 Φ(−|z|) も返す(雑音が正規なら一致する門)。

    返り: ``eps``(m)、``flip_rate``、``z`` = (|ε| − eps_max)/σ、``flip_theory`` = Φ(−|z|)、``eps_max``。**Raises** ``ValueError``: σ ≤ 0。"""
    kp = P._kp(kp)
    s = float(sigma)
    if s <= 0.0:
        raise ValueError("vision_boundary_flip: sigma must be > 0")
    rng = np.random.default_rng(seed)
    emax = P.chamfer_capture(kp, 0.0)["eps_max"]
    eps = np.asarray(eps_true, np.float64).reshape(-1)
    rates, zs, th = [], [], []
    for e in eps:
        truth_large = abs(e) > emax
        meas = abs(e) + s * rng.standard_normal(int(n))
        flips = (meas > emax) != truth_large
        rates.append(float(flips.mean()))
        z = (abs(e) - emax) / s
        zs.append(z)
        th.append(0.5 * math.erfc(abs(z) / math.sqrt(2.0)))
    return {"eps": eps, "flip_rate": np.array(rates), "z": np.array(zs), "flip_theory": np.array(th), "eps_max": emax}


def insertion_failure_presets(kp=None) -> dict:
    """注入する失敗の既定(各クラス → :func:`pegfail_episode_run` の引数)。数は Whitney の境目から:
    missed_hole = ε₀ 2.5 mm(> W + c_r = 1.2 mm)/ wedging = μ 0.8・θ₀ 4.5°(c/μ = 2.76°)/ jamming = θ₀ 3°(μ = 0.3 ではくさびに
    ならない 7.35° の下)で先端が 4 mm 入ってから搬送台の横目標を傾きの側へ +3.0 mm ずらして保持(手首ばね 600 N/m → F_x ≤ 1.8 N、
    ヒンジは先端から 40 mm なので M/(rF_z) が平行四辺形の斜辺を越える。実測: −3.0 mm(反対側)では滑って入る、+1.6 mm では
    止まるが比は内側 = unknown)/ blocked_hole = 深さ 6 mm に栓 / wrong_hole = 26 mm 横の囮の穴へ向かう / nominal = ε₀ 0.5 mm・θ₀ 1.5°。"""
    kp = P._kp(kp)
    return {
        "nominal": {"eps_mm": (0.5, 0.0), "tilt_deg": 1.5},
        "missed_hole": {"eps_mm": (2.5 * math.cos(0.5), 2.5 * math.sin(0.5)), "tilt_deg": 1.0},
        "wedging": {"eps_mm": (0.3, 0.0), "tilt_deg": 4.5, "mu": 0.8},
        "jamming": {"eps_mm": (0.3, 0.0), "tilt_deg": 3.0, "lateral_bias_mm": (3.0, 0.0), "bias_after_depth": 4e-3},
        "blocked_hole": {"eps_mm": (0.3, 0.0), "tilt_deg": 1.0, "blocked_depth": 6e-3},
        "wrong_hole": {"eps_mm": (0.3, 0.0), "tilt_deg": 1.0, "decoy_xy": (26e-3, 0.0), "aim_decoy": True},
    }


# ----------------------------------------------------------------------------------------------------------------------
# mujoco 層(facade のみ)
def pegfail_scene_mjcf(kp=None, lg: float | None = None, blocked_depth: float | None = None, decoy_xy=None,
                         offsamples: int = 4) -> str:
    """失敗注入つきの場面の MJCF 文字列(mujoco 不要): pegsim.peg_scene_mjcf を ElementTree で読み、(i) 手首の力・トルクセンサ
    (site ``peg_top`` = 手首原点、子 body と親の相互作用力)、(ii) ``blocked_depth`` [m] なら穴の中にその深さを上面とする栓(円柱)、
    (iii) ``decoy_xy`` なら囮の穴(壁・面取り・襟を複製して平行移動、名前に ``decoy_`` を付ける。四角い枠は囮と重なるので外す)。
    **Raises** ``ValueError``: 栓の深さが穴の外、囮が目標穴と重なる(中心距離 < 2(R + W) + 1 mm)。"""
    kp = P._kp(kp)
    root = ET.fromstring(P.peg_scene_mjcf(kp, lg=lg, offsamples=offsamples))
    plate = next(b for b in root.iter("body") if b.get("name") == "plate")
    R, W, Hd = kp["R"], kp["chamfer"], kp["hole_depth"]
    if blocked_depth is not None:
        bd = float(blocked_depth)
        if not (W < bd < Hd):
            raise ValueError("pegfail_scene_mjcf: blocked_depth must be inside the hole (W, hole_depth), got %r" % bd)
        half = (Hd - bd) / 2.0
        ET.SubElement(plate, "geom", {"name": "plug", "type": "cylinder", "size": "%.6f %.6f" % (R - 0.2e-3, half),
                                      "pos": "0 0 %.6f" % (-(bd + half)), "rgba": "0.3 0.25 0.2 1", "class": "hole"})
    if decoy_xy is not None:
        dx, dy = float(decoy_xy[0]), float(decoy_xy[1])
        if math.hypot(dx, dy) < 2.0 * (R + W) + 1e-3:
            raise ValueError("pegfail_scene_mjcf: decoy hole overlaps the target hole")
        frame_boxes = [g for g in list(plate) if g.tag == "geom" and g.get("name") is None]
        for g in frame_boxes:
            plate.remove(g)                                  # 四角い枠(無名)は囮と重なる → 2 つの穴を囲む枠に組み直す
        clones = []
        for g in list(plate):
            nm = g.get("name") or ""
            if nm.startswith(("wall", "chamf", "collar", "hole_floor")):
                c = ET.Element("geom", dict(g.attrib))
                px, py, pz = (float(v) for v in g.get("pos").split())
                c.set("pos", "%.7f %.7f %.7f" % (px + dx, py + dy, pz))
                c.set("name", "decoy_" + nm)
                clones.append(c)
        for c in clones:
            plate.append(c)
        wall_t = 6.0e-3
        inner = R + W + wall_t * 0.6                         # peg_scene_mjcf と同じ内側の半幅
        cx, cy = dx / 2.0, dy / 2.0
        hx, hy = abs(dx) / 2.0 + inner, abs(dy) / 2.0 + inner
        fx, fy = hx + 0.05, hy + 0.05
        rgba = frame_boxes[0].get("rgba") if frame_boxes else "0.55 0.55 0.53 1"
        for (px, py, sx, sy) in [(cx, cy + (fy + hy) / 2, fx, (fy - hy) / 2), (cx, cy - (fy + hy) / 2, fx, (fy - hy) / 2),
                                 (cx + (fx + hx) / 2, cy, (fx - hx) / 2, hy), (cx - (fx + hx) / 2, cy, (fx - hx) / 2, hy)]:
            ET.SubElement(plate, "geom", {"type": "box", "size": "%.5f %.5f 0.0125" % (sx, sy), "pos": "%.5f %.5f -0.0125" % (px, py),
                                          "rgba": rgba, "class": "hole"})
    sensor = ET.SubElement(root, "sensor")
    ET.SubElement(sensor, "force", {"name": "wrist_force", "site": "peg_top"})
    ET.SubElement(sensor, "torque", {"name": "wrist_torque", "site": "peg_top"})
    return ET.tostring(root, encoding="unicode")


def _mujoco():
    return P._mujoco()


def pegfail_scene_build(kp=None, lg: float | None = None, blocked_depth: float | None = None, decoy_xy=None) -> dict:
    """失敗注入つきの場面を組む(mujoco が要る): :func:`pegfail_scene_mjcf` をコンパイルし、pegsim.peg_scene_build と同じ鍵の
    ``ids`` に ``plug``・``decoy_wall_set``・``decoy_chamf_set``・``sensor``(力・トルクの adr)を足す。depth 用の offsamples=0 の
    model も同じ XML から作って持つ(pegsim.peg_wrist_render は注入物の無い場面を再コンパイルするので使わない)。"""
    mujoco = _mujoco()
    kp = P._kp(kp)
    xml = pegfail_scene_mjcf(kp, lg=lg, blocked_depth=blocked_depth, decoy_xy=decoy_xy, offsamples=4)
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    g, O = mujoco.mj_name2id, mujoco.mjtObj
    n_seg = kp["n_seg"]
    ids = {"peg": g(m, O.mjOBJ_GEOM, "peg"), "tip": g(m, O.mjOBJ_SITE, "tip"), "top": g(m, O.mjOBJ_SITE, "peg_top"),
           "hole_center": g(m, O.mjOBJ_SITE, "hole_center"), "cam_wrist": g(m, O.mjOBJ_CAMERA, "wrist"),
           "cam_side": g(m, O.mjOBJ_CAMERA, "side"), "floor": g(m, O.mjOBJ_GEOM, "hole_floor"),
           "wall": [g(m, O.mjOBJ_GEOM, "wall%d" % i) for i in range(n_seg)],
           "chamf": [g(m, O.mjOBJ_GEOM, "chamf%d" % i) for i in range(n_seg)],
           "plug": g(m, O.mjOBJ_GEOM, "plug") if blocked_depth is not None else -1,
           "decoy_floor": g(m, O.mjOBJ_GEOM, "decoy_hole_floor") if decoy_xy is not None else -1}
    ids["wall_set"], ids["chamf_set"] = set(ids["wall"]), set(ids["chamf"])
    ids["decoy_wall_set"] = set(g(m, O.mjOBJ_GEOM, "decoy_wall%d" % i) for i in range(n_seg)) if decoy_xy is not None else set()
    ids["decoy_chamf_set"] = set(g(m, O.mjOBJ_GEOM, "decoy_chamf%d" % i) for i in range(n_seg)) if decoy_xy is not None else set()
    jn = ["cx", "cy", "cz", "wx", "wy", "wz", "wrx", "wry", "wrz"]
    ids["qadr"] = {n: int(m.jnt_qposadr[g(m, O.mjOBJ_JOINT, n)]) for n in jn}
    ids["act"] = {n: g(m, O.mjOBJ_ACTUATOR, n) for n in ("ax", "ay", "az")}
    ids["sensor"] = {"force": int(m.sensor_adr[g(m, O.mjOBJ_SENSOR, "wrist_force")]),
                     "torque": int(m.sensor_adr[g(m, O.mjOBJ_SENSOR, "wrist_torque")])}
    return {"model": m, "data": d, "ids": ids, "kp": kp, "lg": lg, "xml": xml, "blocked_depth": blocked_depth,
            "decoy_xy": None if decoy_xy is None else (float(decoy_xy[0]), float(decoy_xy[1]))}


def _render(scene, cam="wrist", depth=True):
    """注入物を含む同じ XML で RGB(MSAA 4)と depth(offsamples=0)を描く(pegsim.peg_wrist_render の規約と同じ返り)。"""
    mujoco = _mujoco()
    import render3d
    m, d, kp = scene["model"], scene["data"], scene["kp"]
    W, H = kp["image_size"]
    if "_ren" not in scene:
        xml0 = scene["xml"].replace('offsamples="4"', 'offsamples="0"')
        m_dep = mujoco.MjModel.from_xml_string(xml0)
        ren_rgb = mujoco.Renderer(m, height=H, width=W)
        ren_dep = mujoco.Renderer(m_dep, height=H, width=W)
        ren_dep.enable_depth_rendering()
        scene["_ren"] = {"rgb": ren_rgb, "dep": ren_dep, "m_dep": m_dep, "d_dep": mujoco.MjData(m_dep)}
    ren = scene["_ren"]
    ren["rgb"].update_scene(d, camera=cam)
    rgb = ren["rgb"].render().copy()
    z = None
    if depth:
        ren["d_dep"].qpos[:] = d.qpos
        ren["d_dep"].qvel[:] = 0
        mujoco.mj_forward(ren["m_dep"], ren["d_dep"])
        ren["dep"].update_scene(ren["d_dep"], camera=cam)
        z = ren["dep"].render().copy()
    cid = scene["ids"]["cam_wrist" if cam == "wrist" else "cam_side"]
    K = render3d.intrinsics_from_fov(float(m.cam_fovy[cid]), W, H)
    ext = P.camera_world_to_cv(d.cam_xmat[cid].reshape(3, 3), d.cam_xpos[cid])
    return {"rgb": rgb, "depth": z, "K": K, "R": ext["R"], "t": ext["t"], "R_cam_to_world": ext["R_cam_to_world"]}


def _scene_close(scene):
    ren = scene.pop("_ren", None)
    if ren:
        ren["rgb"].close()
        ren["dep"].close()


def _contacts(scene):
    mujoco = _mujoco()
    m, d, ids = scene["model"], scene["data"], scene["ids"]
    out = []
    f6 = np.zeros(6)
    for i in range(d.ncon):
        c = d.contact[i]
        g1, g2 = int(c.geom1), int(c.geom2)
        if ids["peg"] not in (g1, g2):
            continue
        other = g2 if g1 == ids["peg"] else g1
        kind = ("wall" if other in ids["wall_set"] or other in ids["decoy_wall_set"] else
                "chamfer" if other in ids["chamf_set"] or other in ids["decoy_chamf_set"] else
                "floor" if other in (ids["floor"], ids["plug"], ids["decoy_floor"]) else "plate")
        decoy = other in ids["decoy_wall_set"] or other in ids["decoy_chamf_set"]
        mujoco.mj_contactForce(m, d, i, f6)
        frame = np.array(c.frame).reshape(3, 3)
        f_world = frame.T @ f6[:3]                           # 接触系 → 世界(法線 = frame[0]、geom1 → geom2 の向き)
        if g1 == ids["peg"]:
            f_world = -f_world                               # ペグに働く向きに揃える(実測: 板の上の静止で ΣF_contact = −F_applied)
        nz = abs(float(frame[0][2]))
        if kind == "chamfer" and nz > 0.9:
            kind = "plate"                                   # 面取りの箱の上の縁に平らな先端面が乗っただけ(法線が鉛直)= 板
        out.append({"kind": kind, "pos": np.array(c.pos), "fn": float(f6[0]), "f_world": f_world, "normal": frame[0].copy(),
                    "decoy": decoy, "other": other})
    return out


def _observe(scene, target_xy, theta_onset=None):
    """真値の観測 1 刻分: 接触の種別(センサで区別できる粒度)、深さ、傾き、手首荷重 → 先端の力の比、目標穴からの先端ずれ。"""
    m, d, ids, kp = scene["model"], scene["data"], scene["ids"], scene["kp"]
    cons = _contacts(scene)
    tip = d.site_xpos[ids["tip"]].copy()
    top = d.site_xpos[ids["top"]].copy()
    a = top - tip
    a /= np.linalg.norm(a)
    depth = -float(tip[2])
    tilt = math.atan2(math.hypot(float(a[0]), float(a[1])), abs(float(a[2])))
    W = kp["chamfer"]
    kinds = [c["kind"] for c in cons]
    tip_side, mouth_side, cham = 0, 0, 0
    tip_pts, mouth_pts = [], []
    for c in cons:
        if c["kind"] not in ("wall", "chamfer"):
            continue
        t_ax = float((c["pos"] - tip) @ a)
        if t_ax < 1.5e-3:
            tip_side += 1
            cham += int(c["kind"] == "chamfer")
            tip_pts.append(c["pos"])
        else:
            mouth_side += 1
            mouth_pts.append(c["pos"])
    if "floor" in kinds:
        ck = "floor"
    elif tip_side and mouth_side:
        ck = "two_point"
    elif tip_side or mouth_side:
        ck = "chamfer" if (cham and not mouth_side and depth < W) else "one_point"
    elif "plate" in kinds:
        ck = "plate"
    else:
        ck = "none"
    q = d.qpos
    qa = ids["qadr"]
    qs = np.array([q[qa["wx"]], q[qa["wy"]], q[qa["wz"]]])
    qh = np.array([q[qa["wrx"]], q[qa["wry"]], q[qa["wrz"]]])
    qr = np.array([m.qpos_spring[qa["wrx"]], m.qpos_spring[qa["wry"]], m.qpos_spring[qa["wrz"]]])
    load = wrist_load_from_deflection(kp, qs, qh, qr, tip, a, lg=scene.get("lg"))
    # e_x: 先端が触れている壁から反対側へ(二点なら先端点 → 口点の水平方向、一点なら接触点 → 穴中心の水平方向、無ければ傾きの向き)
    centre = np.array([target_xy[0], target_xy[1], 0.0])
    if tip_pts and mouth_pts:
        ex = np.mean(mouth_pts, axis=0) - np.mean(tip_pts, axis=0)
    elif tip_pts or mouth_pts:
        ex = centre - np.mean(tip_pts or mouth_pts, axis=0)
    else:
        ex = np.array([a[0], a[1], 0.0]) if math.hypot(a[0], a[1]) > 1e-9 else np.array([1.0, 0.0, 0.0])
    ex = np.array([ex[0], ex[1], 0.0])
    if np.linalg.norm(ex) < 1e-9:
        ex = np.array([1.0, 0.0, 0.0])
    ex = ex / np.linalg.norm(ex)                             # 単位ベクトル(操舵の線形模型が k_t δ e_x をそのまま使う)
    ratios = tip_force_ratios(kp, load["F"], load["M_tip"], ex)
    sens = d.sensordata
    sa = ids["sensor"]
    Rsite = d.site_xmat[ids["top"]].reshape(3, 3)            # 力センサは site(手首 = 傾いた)系で出る → 世界へ
    offset = float(math.hypot(tip[0] - target_xy[0], tip[1] - target_xy[1]))
    f_contact = np.sum([c["f_world"] for c in cons], axis=0) if cons else np.zeros(3)
    return {"contact_kind": ck, "n_contacts": len(cons), "kinds": kinds, "depth": depth, "tilt": tilt,
            "theta_onset": tilt if theta_onset is None else theta_onset, "fx_over_fz": ratios["fx_over_fz"],
            "m_over_rfz": ratios["m_over_rfz"], "F_z": ratios["F_z"], "F_x": ratios["F_x"], "M": ratios["M"],
            "depth_l": depth - W, "offset": offset, "tip": tip, "axis": a, "e_x": ex, "load": load,
            "force": float(sum(c["fn"] for c in cons)), "f_contact_world": f_contact,
            "sensor_force": Rsite @ sens[sa["force"]:sa["force"] + 3], "sensor_torque": Rsite @ sens[sa["torque"]:sa["torque"] + 3],
            "decoy_contact": any(c["decoy"] for c in cons), "plug_contact": any(c["other"] == ids["plug"] for c in cons),
            "q_slide": qs, "q_hinge": qh}


def pegfail_episode_run(kp=None, eps_mm=(0.5, 0.0), tilt_deg: float = 1.5, mu: float | None = None, lateral_bias_mm=(0.0, 0.0),
                          bias_after_depth: float = 0.0, blocked_depth: float | None = None, decoy_xy=None, aim_decoy: bool = False,
                          injected: str = "none", recover: bool = True, vision: bool = True, lg: float | None = None,
                          record: bool = False, frame_every: float = 0.05, v_fast: float = 12e-3, v_slow: float = 3e-3,
                          f_slow: float = 2.5, f_max: float = 12.0, success_depth: float = 15e-3, t_max: float = 9.0,
                          max_recoveries: int = 3, confirm_ticks: int = 10, stall_window: int = 30,
                          stall_min_advance: float = 0.05e-3, jam_tol: float = -0.15, release_probe: bool = False) -> dict:
    """失敗注入 → 降下 → 停滞検出 → 分類 → 回復、の 1 走行(mujoco が要る、学習なし)。

    注入: ``eps_mm``(初期横ずれ)、``tilt_deg``(把持の傾き = ヒンジばねの静止角)、``mu``(摩擦を上書き)、``lateral_bias_mm``
    (先端深さが ``bias_after_depth`` を越えてから搬送台の横目標をずらし続ける = 誤った横力・モーメント)、``blocked_depth``(栓)、
    ``decoy_xy`` + ``aim_decoy``(囮の穴へ向かう)。制御刻 10 ms。各刻で真値の観測(接触の種別・深さ・手首荷重 → 力の比・目標穴からの
    ずれ)→ 停滞(:func:`insertion_stall_detect` と同じ窓を逐次に)→ 署名 → 表引き。**検出** = nominal / chamfer_sliding 以外のクラスが
    (停滞中に出た)か(``confirm_ticks`` 刻続いた)。``recover`` なら検出で回復プリミティブを実行(≤ ``max_recoveries``、unknown は
    押すのを止めて終わる = fail-closed)。成功 = 先端深さ ≥ ``success_depth`` **かつ目標穴の中**(囮に深く入っても成功でない)。
    ``vision`` なら構えた時に手首 RGB-D で穴中心と先端を測り、以後は先端の変位(エンコーダ)で積分したずれを「視覚のずれ」とし(穴は
    動かない・先端は穴に入ると見えない)、各刻の分類を視覚版の署名でも出す(``cls_vision``)。``release_probe`` なら最初の検出で
    回復の代わりに **押す力を抜く**(搬送台を手首ばねの圧縮分だけ上げ F_z → 0、さらに 2 mm 引く)—— 抜いても深さが変わらなければ
    Whitney の意味のくさび(内部に圧縮が溜まる)、戻れば詰まり(力を変えれば解ける)。
    返り: ``status``("success" / "aborted" / "timeout" / "unknown_stop" / "failed:<cls>" / "released:<cls>")、``success``、``rec``
    (刻ごとの列、``detected``・``failing`` を含む)、``recoveries``、``stall_onset_tick``、``failing_onset_tick``(真の失敗の始まり:
    栓・囮への接触、または事後に見た「以後進まない」最初の刻)、``vision_anchor``、``frames``、``release``、``sim_time``、``wall_s``。"""
    import time as _time
    mujoco = _mujoco()
    t_wall = _time.perf_counter()
    kp = P._kp(kp)
    if mu is not None:
        kp = dict(kp, mu=float(mu))
    sc = pegfail_scene_build(kp, lg=lg, blocked_depth=blocked_depth, decoy_xy=decoy_xy)
    m, d, ids = sc["model"], sc["data"], sc["ids"]
    dt = float(m.opt.timestep)
    qa = ids["qadr"]
    m.qpos_spring[qa["wry"]] = math.radians(tilt_deg)
    d.qpos[qa["wry"]] = math.radians(tilt_deg)
    d.ctrl[:] = 0.0
    mujoco.mj_forward(m, d)
    target = np.array([0.0, 0.0])                            # 治具の目標穴(図面)
    aim = np.array(decoy_xy[:2], np.float64) if (aim_decoy and decoy_xy is not None) else target.copy()
    bias = np.array([lateral_bias_mm[0], lateral_bias_mm[1]], np.float64) * 1e-3
    table = insertion_failure_table()
    rec = {k: [] for k in ("t", "depth", "tilt", "contact", "stalled", "cls_truth", "cls_vision", "force", "F_z", "F_x",
                           "fx_over_fz", "m_over_rfz", "offset", "offset_vision", "tip_xy", "jam_margin", "sensor_force", "F_est",
                           "f_contact", "phase", "detected", "failing")}
    frames, recoveries = [], []
    nsteps = [0]
    last_frame = [-1.0]
    theta_onset = [None]
    phase = ["approach"]
    label = ["approach"]

    def settle(n):
        for _ in range(int(n)):
            mujoco.mj_step(m, d)
            nsteps[0] += 1
            if record and d.time - last_frame[0] >= frame_every:
                last_frame[0] = d.time
                frames.append({"rgb": _render(sc, "wrist", depth=False)["rgb"], "t": float(d.time), "label": label[0],
                               "tick": len(rec["t"])})

    settle(0.4 / dt)
    for _ in range(3):
        tip = d.site_xpos[ids["tip"]]
        d.ctrl[0] += aim[0] + eps_mm[0] * 1e-3 - tip[0]
        d.ctrl[1] += aim[1] + eps_mm[1] * 1e-3 - tip[1]
        settle(0.3 / dt)
    anchor = None
    if vision:
        img = _render(sc, "wrist", depth=True)
        try:
            res = P.peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=kp["r"],
                                         hole_radius=kp["R"] + kp["chamfer"])
            cam_w = -img["R"].T @ img["t"]
            hole_w = img["R_cam_to_world"] @ res["hole"]["centre_cam"] + cam_w
            tip_w = img["R_cam_to_world"] @ res["tip"]["tip_cam"] + cam_w
            anchor = {"hole_xy_vision": hole_w[:2].copy(), "tip_xy_vision": tip_w[:2].copy(),
                      "tip_xy_true": d.site_xpos[ids["tip"]][:2].copy(), "target_xy": target.copy(),
                      "dx_mm": res["dx"] * 1e3, "dy_mm": res["dy"] * 1e3, "ok": True,
                      "hole_err_mm": float(np.linalg.norm(hole_w[:2] - target)) * 1e3}
        except (RuntimeError, ValueError) as exc:
            anchor = {"ok": False, "error": repr(exc)}
    tip_anchor = d.site_xpos[ids["tip"]][:2].copy()

    def vision_offset(tip_xy_true):
        if not (anchor and anchor["ok"]):
            return None
        tip_now = anchor["tip_xy_vision"] + (tip_xy_true - tip_anchor)
        return float(np.linalg.norm(tip_now - anchor["hole_xy_vision"]))

    stall_hist = []
    armed = [False]
    z_start = [None]

    def stalled_now():
        z = stall_hist
        if z_start[0] is None:
            z_start[0] = z[0]
        if not armed[0] and z[-1] - z_start[0] >= 0.5e-3:
            armed[0] = True
        if not armed[0] or len(z) <= stall_window:
            return False
        return bool((z[-1] - z[-1 - stall_window]) < stall_min_advance)

    def tick():
        obs = _observe(sc, target, theta_onset[0])
        if obs["contact_kind"] == "two_point" and theta_onset[0] is None:
            theta_onset[0] = obs["tilt"]
            obs["theta_onset"] = obs["tilt"]
        stall_hist.append(obs["depth"])
        st = stalled_now()
        sig = insertion_signature(obs, kp, stall=st, lateral_tol=jam_tol)
        cls = insertion_failure_classify(sig, table)
        ov = vision_offset(obs["tip"][:2])
        cls_v = None
        if ov is not None:
            sig_v = insertion_signature(dict(obs, offset=ov), kp, stall=st, lateral_tol=jam_tol)
            cls_v = insertion_failure_classify(sig_v, table)["cls"]
        jm = float("nan")
        if obs["contact_kind"] == "two_point" and obs["fx_over_fz"] is not None:
            jm = jamming_force_check(kp, max(obs["depth_l"], 0.0), obs["fx_over_fz"], obs["m_over_rfz"])["margin"]
        rec["t"].append(float(d.time)); rec["depth"].append(obs["depth"]); rec["tilt"].append(obs["tilt"])
        rec["contact"].append(obs["contact_kind"]); rec["stalled"].append(st); rec["cls_truth"].append(cls["cls"])
        rec["cls_vision"].append(cls_v); rec["force"].append(obs["force"]); rec["F_z"].append(obs["F_z"]); rec["F_x"].append(obs["F_x"])
        rec["fx_over_fz"].append(obs["fx_over_fz"]); rec["m_over_rfz"].append(obs["m_over_rfz"]); rec["offset"].append(obs["offset"])
        rec["offset_vision"].append(ov); rec["tip_xy"].append(obs["tip"][:2].copy()); rec["jam_margin"].append(jm)
        rec["sensor_force"].append(obs["sensor_force"]); rec["F_est"].append(obs["load"]["F"].copy())
        rec["f_contact"].append(obs["f_contact_world"].copy()); rec["phase"].append(phase[0])
        rec["failing"].append(bool(obs["decoy_contact"] or obs["plug_contact"]))
        rec["detected"].append(False)
        return obs, sig, cls

    def lift(dz):
        d.ctrl[2] += dz
        settle(0.5 / dt)

    def servo(iters, gain):
        log = []
        for it in range(int(iters)):
            img = _render(sc, "wrist", depth=True)
            try:
                res = P.peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=kp["r"],
                                             hole_radius=kp["R"] + kp["chamfer"])
            except (RuntimeError, ValueError) as exc:
                log.append({"iter": it, "error": repr(exc)})
                break
            td = d.site_xpos[ids["tip"]][:2] - target
            log.append({"iter": it, "dx_mm": res["dx"] * 1e3, "dy_mm": res["dy"] * 1e3, "true_mm": (td * 1e3).tolist()})
            if math.hypot(res["dx"], res["dy"]) < 0.05e-3:
                break
            d.ctrl[0] -= gain * res["dx"]
            d.ctrl[1] -= gain * res["dy"]
            settle(0.3 / dt)
        return log

    def do_recovery(cls, obs):
        nonlocal bias, aim
        prim = insertion_recovery_primitive(cls["recovery"])
        entry = {"tick": len(rec["t"]) - 1, "cls": cls["cls"], "primitive": prim["name"], "t": float(d.time)}
        phase[0] = "recover:" + cls["cls"]
        label[0] = "detected: %s -> %s" % (cls["cls"], prim["name"])
        if prim["name"] == "lift_recentre":
            lift(obs["depth"] + prim["lift_m"])
            entry["servo"] = servo(prim["servo_iters"], prim["gain"])
        elif prim["name"] == "lift_reapproach":
            lift(obs["depth"] + prim["lift_m"])
            aim = target.copy()
            tip = d.site_xpos[ids["tip"]][:2]
            d.ctrl[0] += target[0] - tip[0]
            d.ctrl[1] += target[1] - tip[1]
            settle(0.6 / dt)
            entry["servo"] = servo(prim["servo_iters"], prim["gain"])
        elif prim["name"] == "retract_reduce_tilt":
            lift(prim["lift_m"])
            qy, qx = d.qpos[qa["wry"]], d.qpos[qa["wrx"]]
            entry["tilt_measured_deg"] = [math.degrees(qy), math.degrees(qx)]
            m.qpos_spring[qa["wry"]] -= qy                   # 把持の傾きを測った分だけ戻す(再把持 / 手首の回転)
            m.qpos_spring[qa["wrx"]] -= qx
            settle(0.5 / dt)
        elif prim["name"] == "steer_force":
            bias = np.zeros(2)                               # 誤った横目標は捨てる(保持している目標はそのまま: ここから操る)
            steps = []
            for _ in range(int(prim["max_steps"])):
                o = _observe(sc, target, theta_onset[0])
                if o["fx_over_fz"] is None:
                    break
                ell = max(o["depth_l"], 0.0)
                ex = o["e_x"]
                nrm = np.cross(ex, np.array([0.0, 0.0, 1.0]))   # M の正の向き(規約)
                best = None
                # 2 つの操作子を線形模型で試す: 搬送台の横移動 δ(F_x と M = L_g F_x が一緒に動く、図の中で傾き L_g/r ≈ 8 の
                # ほぼ縦の移動)と、手首の回転 Δ(ヒンジばねの静止角: M だけが k_r Δ 動く)。余裕が最大になる組を選ぶ。
                for sgn_s in (-1.0, 0.0, 1.0):
                    for sgn_r in (-1.0, 0.0, 1.0):
                        if sgn_s == 0.0 and sgn_r == 0.0:
                            continue
                        dF = kp["k_trans"] * prim["step_m"] * sgn_s * ex
                        F2 = o["load"]["F"] + dF
                        M2 = o["load"]["M_tip"] + np.cross(o["load"]["lg"] * o["axis"], dF) + kp["k_rot"] * prim["step_rad"] * sgn_r * nrm
                        rr = tip_force_ratios(kp, F2, M2, ex)
                        if rr["fx_over_fz"] is None:
                            continue
                        if o["contact_kind"] == "two_point":
                            mg = jamming_force_check(kp, ell, rr["fx_over_fz"], rr["m_over_rfz"])["margin"]
                        else:
                            mg = 1.0 / kp["mu"] - abs(rr["fx_over_fz"])
                        if best is None or mg > best[0]:
                            best = (mg, sgn_s, sgn_r)
                if best is None:
                    break
                shift = best[1] * prim["step_m"] * ex[:2]
                d.ctrl[0] += shift[0]
                d.ctrl[1] += shift[1]
                # ヒンジ(wrx, wry)の静止角: 世界の回転ベクトル Δ·nrm を成分で足す(小角)
                m.qpos_spring[qa["wrx"]] += best[2] * prim["step_rad"] * nrm[0]
                m.qpos_spring[qa["wry"]] += best[2] * prim["step_rad"] * nrm[1]
                settle(0.25 / dt)
                o2 = _observe(sc, target, theta_onset[0])
                m_after = (jamming_force_check(kp, max(o2["depth_l"], 0.0), o2["fx_over_fz"], o2["m_over_rfz"])["margin"]
                           if (o2["contact_kind"] == "two_point" and o2["fx_over_fz"] is not None) else float("nan"))
                steps.append({"shift": best[1], "rotate": best[2], "margin_pred": best[0],
                              "margin_before": (jamming_force_check(kp, ell, o["fx_over_fz"], o["m_over_rfz"])["margin"]
                                                if o["contact_kind"] == "two_point" else None),
                              "margin_after": m_after, "depth_mm": o2["depth"] * 1e3, "contact": o2["contact_kind"],
                              "x": o["fx_over_fz"], "y": o["m_over_rfz"]})
                # 目標 = 実測の余裕が prim["target_margin"] 以上(MuJoCo の滑りの境目は Whitney の線より ≈ 0.15 内側、実測)
                if o2["contact_kind"] != "two_point" or (np.isfinite(m_after) and m_after >= prim["target_margin"]):
                    break
            entry["steps"] = steps
        elif prim["name"] == "lift_abort":
            lift(obs["depth"] + prim["lift_m"])
        recoveries.append(entry)
        stall_hist.clear()                                   # 窓だけ空ける(武装は保つ: 回復が効かなければ 30 刻後にまた検出する)
        if prim["name"] in ("lift_recentre", "lift_reapproach", "retract_reduce_tilt", "lift_abort"):
            armed[0] = False                                 # 退避した後は改めて降下で武装
            z_start[0] = None
        phase[0] = "descend"
        label[0] = "descend (after %s)" % prim["name"]
        return prim

    bias_ctrl = None

    def release(cls, obs):
        """押す力を抜く探針: 手首ばねの z 圧縮分だけ搬送台を上げ(F_z → 0)、さらに 2 mm 引いて、深さが残るかを見る。"""
        out = {"cls": cls["cls"], "depth_before_mm": obs["depth"] * 1e3, "F_z_before_N": obs["F_z"], "F_x_before_N": obs["F_x"],
               "tilt_before_deg": math.degrees(obs["tilt"]), "x": obs["fx_over_fz"], "y": obs["m_over_rfz"]}
        label[0] = "release probe: " + cls["cls"]
        if bias_ctrl is not None:
            d.ctrl[0], d.ctrl[1] = bias_ctrl - bias          # 横の誤った力も抜く(全ての加える力を抜いて残るのがくさび)
        d.ctrl[2] += float(obs["q_slide"][2])
        settle(0.6 / dt)
        o = _observe(sc, target, theta_onset[0])
        out.update(depth_unloaded_mm=o["depth"] * 1e3, F_z_unloaded_N=o["F_z"], contact_unloaded=o["contact_kind"])
        d.ctrl[2] += 2e-3
        settle(0.6 / dt)
        o = _observe(sc, target, theta_onset[0])
        out.update(depth_pulled_mm=o["depth"] * 1e3, F_z_pulled_N=o["F_z"], contact_pulled=o["contact_kind"],
                   stuck=(out["depth_before_mm"] - o["depth"] * 1e3) < 0.5)
        return out

    phase[0] = "descend"
    label[0] = "descend"
    t0 = d.time
    status = "timeout"
    onset_tick = -1
    benign = {"nominal", "chamfer_sliding"}
    released = None
    while d.time - t0 < t_max:
        obs, sig, cls = tick()
        if rec["stalled"][-1] and onset_tick < 0:
            onset_tick = len(rec["t"]) - 1
        in_target = P.chamfer_capture(kp, obs["offset"])["captured"]
        if (obs["depth"] >= success_depth or cls["cls"] == "seated") and in_target:
            status = "success"
            break
        recent = rec["cls_truth"][-2 * int(confirm_ticks):]
        persistent = sum(1 for c in recent if c == cls["cls"]) >= int(confirm_ticks)   # 接触のちらつきに耐える確認
        confirmed = cls["cls"] not in benign and (rec["stalled"][-1] or persistent)
        if confirmed:
            rec["detected"][-1] = True
            label[0] = "detected: " + cls["cls"]
            if cls["cls"] == "unknown":
                if rec["stalled"][-1] and (recover or not any(rec["detected"][:-1])):
                    status = "unknown_stop"                  # 基準(回復なし)では最初の検出を保ち、押し続けて記録する
                    break
                confirmed = False
            elif release_probe and released is None:
                released = release(cls, obs)
                status = "released:" + cls["cls"]
                break
            elif recover and len(recoveries) < max_recoveries:
                prim = do_recovery(cls, obs)
                if prim["name"] != "steer_force":
                    bias_ctrl = None
                for _ in range(2 * int(confirm_ticks)):
                    rec["cls_truth"].append("nominal"); rec["detected"].append(False); rec["failing"].append(False)
                    for k in rec:
                        if k not in ("cls_truth", "detected", "failing"):
                            rec[k].append(rec[k][-1] if k != "stalled" else False)
                if not prim["resume"]:
                    status = prim["terminal"]
                    break
                continue
            elif recover:
                status = "failed:" + cls["cls"]
                break
        v = v_slow if obs["force"] > f_slow else v_fast
        if obs["force"] <= f_max:
            d.ctrl[2] -= v * dt * 20
        if obs["depth"] > float(bias_after_depth) and np.any(bias != 0.0) and bias_ctrl is None:
            bias_ctrl = d.ctrl[:2].copy() + bias             # 横目標を 1 回だけずらして保持(積分しない: 手首ばねの力は k_t·bias が上限)
            d.ctrl[0], d.ctrl[1] = bias_ctrl
        settle(20)
    if status == "timeout":
        bad = [c for c, dtc in zip(rec["cls_truth"], rec["detected"]) if dtc and c != "unknown"]
        if bad:
            status = "failed:" + bad[0]
        elif rec["depth"] and rec["depth"][-1] >= success_depth:
            status = "failed:wrong_hole"                     # 深いが目標穴でない
    tick()
    _scene_close(sc)
    # 真の失敗の始まり(事後): 栓/囮への最初の接触、または「検出時の深さの 0.3 mm 手前に初めて達した刻」(= そこで実質止まった)
    z = np.asarray(rec["depth"])
    fail_idx = [i for i, f in enumerate(rec["failing"]) if f]
    det_idx = [i for i, f in enumerate(rec["detected"]) if f]
    if fail_idx:
        failing_onset = fail_idx[0]
    elif det_idx and len(z) > 1:
        z_det = z[det_idx[0]]
        cand = [i for i in range(det_idx[0] + 1) if z[i] >= z_det - 0.3e-3]
        failing_onset = cand[0] if cand else det_idx[0]
    else:
        failing_onset = -1
    return {"status": status, "success": status == "success", "injected": injected, "eps_mm": [float(e) for e in eps_mm],
            "tilt_deg": float(tilt_deg), "mu": kp["mu"], "recover": bool(recover), "rec": rec, "recoveries": recoveries,
            "stall_onset_tick": onset_tick, "failing_onset_tick": int(failing_onset), "vision_anchor": anchor, "frames": frames,
            "steps": nsteps[0], "sim_time": float(d.time), "wall_s": _time.perf_counter() - t_wall, "theta_onset": theta_onset[0],
            "release": released}


def pegfail_failure_grid(kp=None, classes=None, recover_flags=(False, True), repeats: int = 1, log=None, keep_episodes: bool = False,
                           **kw) -> dict:
    """注入クラス × {回復なし, あり} の格子(mujoco が要る): :func:`insertion_failure_presets` の条件で :func:`pegfail_episode_run` を回し、
    走行ごとの要約(:func:`insertion_episode_summary`)と、真値署名 / 視覚署名それぞれの混同行列(:func:`failure_confusion`、回復なしの
    走行で最初に出た失敗クラス)、回復あり / なしの成功率(blocked_hole は正しく中止 = 成功と数える)を返す。
    ``repeats`` > 1 では ε₀ の向きを回して複数回。"""
    kp = P._kp(kp)
    pre = insertion_failure_presets(kp)
    classes = list(pre) if classes is None else list(classes)
    rows, truth_pairs, vision_pairs, episodes = [], [], [], []
    for cls in classes:
        for rep in range(int(repeats)):
            args = dict(pre[cls])
            if rep:
                e = np.array(args["eps_mm"])
                ang = 2.0 * math.pi * rep / max(1, repeats)
                c, s = math.cos(ang), math.sin(ang)
                args["eps_mm"] = (float(c * e[0] - s * e[1]), float(s * e[0] + c * e[1]))
            for rc in recover_flags:
                ep = pegfail_episode_run(kp, injected=cls, recover=rc, **args, **kw)
                sm = insertion_episode_summary(ep)
                sm["recover"] = bool(rc)
                sm["rep"] = rep
                sm["wall_s"] = ep["wall_s"]
                rows.append(sm)
                if keep_episodes:
                    episodes.append(ep)
                if not rc:
                    truth_pairs.append((cls, sm["first_cls"] if sm["first_cls"] != "none" else "nominal"))
                    cv = [c for c in ep["rec"]["cls_vision"] if c not in (None, "nominal", "chamfer_sliding", "seated")]
                    vision_pairs.append((cls, cv[0] if cv else "nominal"))
                if log:
                    log("%-13s recover=%-5s -> %-20s first=%-13s lat=%s rec=%d depth=%.2f mm F=%.1f N %.1f s"
                        % (cls, rc, sm["status"], sm["first_cls"], sm["latency_ticks"], sm["recoveries"], sm["final_depth_mm"],
                           sm["max_force_N"], ep["wall_s"]))
    conf_t = failure_confusion([a for a, _ in truth_pairs], [b for _, b in truth_pairs])
    conf_v = failure_confusion([a for a, _ in vision_pairs], [b for _, b in vision_pairs])
    rate = {}
    for rc in recover_flags:
        sel = [r for r in rows if r["recover"] == rc and r["injected"] != "nominal"]
        ok = sum(1 for r in sel if r["success"] or (r["injected"] == "blocked_hole" and r["status"] == "aborted"))
        rate[bool(rc)] = (ok, len(sel))
    return {"rows": rows, "confusion_truth": conf_t, "confusion_vision": conf_v, "success": rate, "episodes": episodes}
