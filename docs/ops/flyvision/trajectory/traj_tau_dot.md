---
op: traj_tau_dot
dim: flyvision
category: trajectory
in: points × signal
out: table
examples: [poc_zebra_stripes_fly_eye]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# traj_tau_dot — FLYVISION `trajectory` op

- **データ種**: `points × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.traj_tau_dot(points, t_s, target=(0.0, 0.0, 0.0), normal=None)` (実装を直接呼ぶなら `import flyvision; flyvision.traj_tau_dot(points, t_s, target=(0.0, 0.0, 0.0), normal=None)`、台帳から引くなら `opsflyvision.get("traj_tau_dot")`)

## 使い方

Distance, approach speed, tau and tau-dot along a measured 3-D trajectory.

The quantity a looming detector is supposed to deliver, computed from the
**true** path so that an eye's estimate can be scored against it. With
``d(t)`` the distance to *target* (a point, or — with *normal* — the signed
distance to the plane through *target*), the approach speed is ``v = -dd/dt``,
the time-to-contact ``tau = d/v`` and its rate ``tau-dot = d tau/dt``.
Lee's (1976) sign convention: ``tau-dot = -1`` at constant speed,
``tau-dot = -0.5`` under the constant deceleration that stops exactly at the
target (the braking law), and a value between them means the agent is
braking enough to stop short.

points: ``(N, 3)`` positions, metres, ``N >= 3``.
t_s:    ``(N,)`` strictly increasing sample times, seconds.
target: the point approached (3,), metres.
normal: ``None`` for the Euclidean distance to *target*, or a (3,) plane
        normal: the distance is then ``(p - target) . normal / |normal|``.

Returns a dict ``{"t_s", "distance_m", "speed_m_s", "tau_s", "tau_dot",
"closest_m", "t_closest_s", "n"}``. Samples where the agent is not
approaching (``v <= 0``) carry ``NaN`` in ``tau_s`` and ``tau_dot`` — a
documented non-finite: a receding agent has no time-to-contact.

Ground truth (pinned in the tests): for ``d = v0 t`` toward the target at
constant speed ``tau-dot == -1``, and for ``d = v0 t - a t^2 / 2`` with
``v0^2 = 2 a d0`` (stops exactly at the target) ``tau-dot == -0.5`` — both to
1e-9 on a uniform grid, where central differences are exact for a quadratic.

**Raises** ``ValueError``: *points* not ``(N, 3)`` with ``N >= 3`` (an empty
*points* is refused), a *t_s* that is not ``(N,)`` strictly increasing,
non-finite entries, a malformed *target* / *normal*, and a zero *normal*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_zebra_stripes_fly_eye](../../../../examples/poc_zebra_stripes_fly_eye.py) — `py -3.11 examples/poc_zebra_stripes_fly_eye.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](../selfmotion/fly_matched_filter.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_eye_merge](../selfmotion/fly_eye_merge.md) · [fly_view_plane_texture](../stimulus/fly_view_plane_texture.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_expansion_readout](../looming/fly_expansion_readout.md)

## 同カテゴリ(`trajectory`)

—

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
