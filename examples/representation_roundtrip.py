# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""representation_roundtrip — 表現変換(reprconv)op を「往復させて嘘を露見させる」筋で
一巡し、**可逆なものは誤差 0、不可逆なものは何がどれだけ落ちるか**を数値に出す。

    py -3.11 examples/representation_roundtrip.py

【この例が解く問題】
fullseye の op 目録は型で繋がっている。だが 2026-09-02 の実測では、**産む op は
あるのに食う op が 1 つも無い型**が 25 個あった(pairs / indices / curvature /
descriptor / keypoints / normals / position / flow / gaussians / score …)。
そこから先へ進めない型を「死んだ語彙」と呼ぶ。reprconv はそこに出口を作る。

なぜ変換を重点的に増やすのか —— **変換は入口の型と出口の型の両方を主張するので、
嘘をつく面が 2 つある**。実際この repo で直近に見つかった実バグは全部が変換 op
だった(voxel_to_mesh / render_beauty / project_points / alpha_shape_boundary)。
変換を増やすことは、検査面を増やすことでもある。

(1) 死んだ語彙の実測: 台帳を機械集計して「出口 0」の型を数える。
(2) 可逆な変換: normals ⇄ pairs、curvature ⇄ pairs、keypoints ⇄ points、
    countrate ⇄ counts。**往復誤差を数字で**出す。
(3) 不可逆な変換: keypoints → image2d(画素格子への量子化)、
    points → position(広がりを捨てる)、gaussians → voxel(質量)。
    「戻らない」で終わらせず**この量がこれだけ落ちる**まで書く。
(4) ★表現をまたいで一周: voxel → mesh → points → gaussians → voxel。
    **変換の連鎖こそが嘘の出る場所**なので、一周して何が残るかを見る。
(5) 軸と単位: (z,y,x) と (u,v)、spacing、度/ラジアンの取り違えが
    **例外を出さずに**どれだけずれるかを実際に見せる。
(6) fail-closed: 非有限・空・巨大 shape・密/散在フローの取り違えを拒否すること。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 形状指数は atan2 形なので臍点・平面を含めて往復が厳密(< 1e-15)。
   球 (1,1) は S=+1、杯 (-1,-1) は S=-1、鞍 (1,-1) は S=0 —— 閉形式の真値。
2. 画素格子への量子化誤差は軸あたり RMS = 1/sqrt(12) = 0.2887 px(一様量子化)。
3. ガウシアンの 3σ **箱**打ち切りで残る質量は erf(3/√2)³ = 99.194%
   (**球**の 97.07% ではない —— ここは一度間違えて、格子を細かくして反証した)。
4. 既知の巡回シフトを与えた体積の相関ピークは、そのシフトに**厳密に**立つ。
5. 90 度の回転行列は軸2 を軸1 へ送る(度であることが全内容)。
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import opsreprconv                                              # noqa: E402
import reprconv as R                                            # noqa: E402


def _rule(title):
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


# --------------------------------------------------------------------------- #
def step1_dead_vocabulary():
    """(1) 死んだ語彙を機械集計する ―― 「出口 0」の型を数える。"""
    _rule("(1) 死んだ語彙 ―― 産む op はあるのに、そこから先へ行けない型")
    import chain_fuzz                                            # noqa: PLC0415

    base = chain_fuzz.catalog()

    def out_edges(ops):
        e = collections.defaultdict(set)
        for _, _, ins, out, _ in ops:
            if len(ins) == 1 and ins[0] != out:
                e[ins[0]].add(out)
        return e

    new = [(n, "rc", m["in"], m["out"], m["func"])
           for n, m in opsreprconv.OPSREPRCONV.items()]
    before, after = out_edges(base), out_edges(base + new)
    types = sorted({t for _, _, ins, out, _ in base + new for t in list(ins) + [out]})
    dead_b = [t for t in types if not before[t]]
    dead_a = [t for t in types if not after[t]]
    fixed = [t for t in dead_b if after[t]]

    print(f"  台帳 op 数        : {len(base)} -> {len(base) + len(new)} "
          f"(reprconv {len(new)} 追加)")
    print(f"  変換ペア(単入力): {sum(len(v) for v in before.values())} -> "
          f"{sum(len(v) for v in after.values())} 種")
    print(f"  出口 0 の型       : {len(dead_b)} -> {len(dead_a)} 個")
    print(f"  出口ができた型 {len(fixed)} 個:")
    for t in fixed:
        print(f"      {t:14s} -> {', '.join(sorted(after[t]))}")
    print(f"  まだ出口が無い型  : {', '.join(dead_a)}")
    print("    (埋めなかった理由は opsreprconv のモジュール docstring。"
          "埋めないことも判断である)")


# --------------------------------------------------------------------------- #
def step2_exact_roundtrips():
    """(2) 可逆な変換 ―― 往復誤差を数字で出す。"""
    _rule("(2) 可逆な変換 ―― 往復して戻るか(誤差は数字で)")
    rng = np.random.default_rng(0)

    n = rng.standard_normal((4096, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    e1 = float(np.max(np.abs(R.angles_to_normals(R.normals_to_angles(n)) - n)))

    k = np.concatenate([rng.standard_normal((400, 2)),
                        np.repeat(rng.standard_normal((40, 1)), 2, 1),   # 臍点
                        np.zeros((5, 2))])                                # 平面
    k = np.stack([k.max(1), k.min(1)], 1)
    si = R.curvature_to_shape_index(k)
    e2 = float(np.max(np.abs(R.shape_index_to_curvature(si) - k)))

    kp = rng.random((1024, 2)) * 100.0
    z = rng.random(1024) * 5.0
    e3 = float(np.max(np.abs(
        R.points_zyx_to_keypoints_uv(R.keypoints_uv_to_points(kp, z)) - kp)))

    cr = 10.0 ** rng.uniform(3.0, 7.0, size=512)
    e4 = float(np.max(np.abs(
        R.counts_to_countrate(R.countrate_to_counts(cr, 1e-3), 1e-3) / cr - 1.0)))

    pts = rng.standard_normal((512, 3)) * 3.0
    e5 = float(np.max(np.abs(R.gaussians_to_points(R.points_to_gaussians(pts)) - pts)))

    print("  往復                                        誤差")
    print(f"  normals (N,3) -> pairs(度) -> normals       max|Δ| = {e1:.3e}")
    print(f"  curvature -> 形状指数 -> curvature          max|Δ| = {e2:.3e}"
          f"   (臍点 40 + 平面 5 を含む)")
    print(f"  keypoints(u,v) -> points(z,y,x) -> keypoints max|Δ| = {e3:.3e}"
          f"   (bit 一致)")
    print(f"  countrate[Hz] -> counts -> countrate        相対 = {e4:.3e}"
          f"   (絶対だと 1e-9、桁が広い量は相対で言う)")
    print(f"  points -> gaussians -> points               max|Δ| = {e5:.3e}"
          f"   (中心は bit 一致)")

    print("\n  形状指数の閉形式の真値(Koenderink & van Doorn 1992):")
    for lbl, kk in (("球  (k1= 1, k2= 1)", (1.0, 1.0)), ("杯  (k1=-1, k2=-1)", (-1.0, -1.0)),
                    ("鞍  (k1= 1, k2=-1)", (1.0, -1.0)), ("稜  (k1= 1, k2= 0)", (1.0, 0.0))):
        s, c = R.curvature_to_shape_index(np.array([kk]))[0]
        print(f"    {lbl}  ->  S = {s:+.6f}   C = {c:.6f}")


# --------------------------------------------------------------------------- #
def step3_lossy_roundtrips():
    """(3) 不可逆な変換 ―― 「戻らない」でなく「この量がこれだけ落ちる」。"""
    _rule("(3) 不可逆な変換 ―― 何がどれだけ落ちるか")
    from scipy.spatial import cKDTree                             # noqa: PLC0415

    rng = np.random.default_rng(1)

    # (a) 画素格子への量子化。**離した点**で測る(融合を混ぜると理論値と比べられない)
    g = np.stack(np.meshgrid(np.arange(3.0, 122.0, 4.0),
                             np.arange(3.0, 122.0, 4.0), indexing="ij"), -1).reshape(-1, 2)
    kp = g + rng.uniform(-0.5, 0.5, size=g.shape)
    back = R.keypoints_from_image2d(R.keypoints_to_image2d(kp, shape=(128, 128)))
    _, j = cKDTree(back).query(kp, k=1)
    axis_rms = float(np.sqrt(np.mean((back[j] - kp) ** 2)))
    print(f"  keypoints -> image2d -> keypoints(4 px 間隔で離した {kp.shape[0]} 点)")
    print(f"      軸あたり量子化 RMS = {axis_rms:.4f} px "
          f"(一様量子化の理論 1/sqrt(12) = {1 / math.sqrt(12):.4f})")
    print(f"      点数 {kp.shape[0]} -> {back.shape[0]}(融合なし)")

    kp2 = rng.random((80, 2)) * 50.0 + 5.0
    back2 = R.keypoints_from_image2d(R.keypoints_to_image2d(kp2, shape=(64, 64)))
    print(f"      ランダム配置 {kp2.shape[0]} 点なら {back2.shape[0]} 点 "
          f"(8 近傍で融合。**量子化と融合は別の損失**なので混ぜて測らない)")

    # (b) 重心。捨てた広がりを測る
    cloud = rng.standard_normal((500, 3)) * 2.0 + 6.0
    pos = R.points_to_position(cloud)
    spread = float(np.sqrt(np.mean(np.sum((cloud - np.asarray(pos)) ** 2, 1))))
    print(f"\n  points -> position -> points")
    print(f"      捨てた広がり RMS = {spread:.4f}(N {cloud.shape[0]} -> 1 点)")

    # (c) ガウシアン -> voxel の質量。★一度間違えた数字
    box = math.erf(3.0 / math.sqrt(2.0)) ** 3
    ball = math.erf(3 / math.sqrt(2)) - math.sqrt(2 / math.pi) * 3 * math.exp(-4.5)
    one = {"mu": np.array([[8.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
    print(f"\n  gaussians -> voxel(質量保存)。3σ の**箱**打ち切りの理論値 "
          f"erf(3/√2)³ = {box * 100:.3f}%")
    print(f"      (**球** 3σ の {ball * 100:.2f}% ではない ―― "
          f"最初こちらと書いて、刻みを細かくして反証した)")
    for sp in (1.0, 0.5, 0.25, 0.125):
        nn = int(round(16 / sp))
        m = float(R.gaussians_to_voxel(one, shape=(nn,) * 3, spacing=(sp,) * 3).sum())
        print(f"      刻み {sp:<6} -> 質量 {m * 100:.3f}%  "
              f"(箱との差 {abs(m - box) * 100:+.3f} pt)")
    edge = {"mu": np.array([[1.0, 8.0, 8.0]]), "sigma": np.array([1.5]), "w": np.array([1.0])}
    print(f"      中心を縁から 1 voxel に置くと "
          f"{float(R.gaussians_to_voxel(edge, shape=(16,) * 3).sum()) * 100:.2f}% "
          f"(境界の切り落としは打ち切りより遥かに大きい)")


# --------------------------------------------------------------------------- #
def step4_cross_representation_loop():
    """(4) ★表現をまたいで一周する ―― 変換の連鎖こそが嘘の出る場所。"""
    _rule("(4) 表現をまたいで一周 ―― voxel -> mesh -> points -> gaussians -> voxel")
    import fuse3d                                                # noqa: PLC0415
    import meshrepair                                            # noqa: PLC0415
    import ops3d                                                 # noqa: PLC0415

    n = 32
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(float)
    c, r = (n - 1) / 2.0, n * 0.30
    vox = ((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2 <= r ** 2).astype(float)
    v_true = float(vox.sum())
    print(f"  出発: 半径 {r:.1f} voxel の球  体積 = {v_true:.0f} voxel "
          f"(解析値 4/3 π r³ = {4 / 3 * math.pi * r ** 3:.0f})")

    verts, faces = ops3d.OPS3D["voxel_to_mesh"]["func"](vox, 0.5)[:2]
    print(f"  -> mesh      : 頂点 {len(verts)}  面 {len(faces)}  "
          f"表面積 = {float(ops3d.OPS3D['mesh_area']['func']((verts, faces))):.1f}")

    pts = fuse3d.to_points((verts, faces), "mesh")
    print(f"  -> points    : {pts.shape[0]} 点 (z,y,x)  "
          f"重心 = ({R.points_to_position(pts)[0]:.3f}, "
          f"{R.points_to_position(pts)[1]:.3f}, {R.points_to_position(pts)[2]:.3f})"
          f"  ※真の中心 {c:.3f}")

    gs = R.points_to_gaussians(pts, k=6)
    print(f"  -> gaussians : {gs['mu'].shape[0]} 個  "
          f"sigma 中央値 = {float(np.median(gs['sigma'])):.4f} voxel  "
          f"重み和 = {float(gs['w'].sum()):.6f}")

    back = R.gaussians_to_voxel(gs, shape=(n, n, n), truncate=3.0)
    filled = back > (0.5 * float(np.percentile(back[back > 0], 90)))
    print(f"  -> voxel     : 質量 {float(back.sum()):.4f}  "
          f"(表面殻なので体積でなく殻が戻る)")
    print(f"                 殻の体積 {int(filled.sum())} voxel  "
          f"元の球 {int(v_true)} voxel")

    # 一周して**戻らないもの**を明示する
    print("\n  一周して戻らないもの(これを書かないと「一周した」が嘘になる):")
    print("    * 中身       —— mesh は表面だけを持つ。球の内部は 2 段目で消えている。")
    print("      戻ってくるのは体積ではなく**殻**で、質量 1.0 は「重み和」であって")
    print("      「体積」ではない(単位が違うものを同じ数として読まないこと)。")
    print("    * 面の接続   —— points 段で三角形の接続が消える(頂点の集合になる)。")
    print("    * 向き       —— 法線も同じ段で消える。")
    print(f"    * 位置       —— 重心は {abs(R.points_to_position(pts)[0] - c):.2e} voxel しか")
    print("      ずれない(球は対称なので、ここは**厳密に近い**のが正しい)。")
    print("    → 一周で「同じものが戻った」ように見える指標(重心)と、")
    print("      「別物になった」指標(体積 vs 殻)を**両方**出すのが正直な報告。")


# --------------------------------------------------------------------------- #
def step5_axes_and_units():
    """(5) 軸と単位 ―― 取り違えても例外は出ない。だから数値で見せる。"""
    _rule("(5) 軸・単位・spacing ―― 例外を出さずにずれる")
    import match3d                                               # noqa: PLC0415
    import volregion                                             # noqa: PLC0415

    v = np.zeros((20, 30, 40))
    v[2:4, 10:12, 30:32] = 1.0
    pos = volregion.vol_rle_centroid(volregion.vol_rle_encode(v > 0.5))
    print(f"  position は (z, y, x)  : vol_rle_centroid -> {pos}  "
          f"(真値 (2.5, 10.5, 30.5))")

    K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 40.0], [0.0, 0.0, 1.0]])
    uv, _ = match3d.project_points(np.array([[0.0, 0.0, 5.0], [1.0, 0.0, 5.0]]), K)
    print(f"  keypoints は (u, v)     : project_points -> {uv.tolist()}  "
          f"(X を +1 動かすと**列**が動く)")

    kp = np.array([[10.0, 40.0]])
    right = R.keypoints_uv_to_points(kp, 0.0)
    wrong = R.keypoints_uv_to_points(kp[:, ::-1], 0.0)
    print(f"\n  ★誤り例: (u,v) を (v,u) と読む")
    print(f"      正 : {right[0].tolist()}      誤 : {wrong[0].tolist()}")
    print(f"      ずれ {float(np.linalg.norm(right - wrong)):.4f}(例外は出ない)")

    g = {"mu": np.array([[10.0, 12.0, 14.0]]), "sigma": np.array([0.4]),
         "w": np.array([1.0])}
    ok = R.gaussians_to_voxel(g, shape=(16,) * 3, origin=(2.0,) * 3,
                              spacing=(2.0,) * 3, truncate=4.0)
    ng = R.gaussians_to_voxel(g, shape=(16,) * 3)
    print(f"\n  ★誤り例: spacing を無視する(既定 1.0 のまま渡す)")
    print(f"      正 (origin=2, spacing=2): ピーク "
          f"{np.unravel_index(int(np.argmax(ok)), ok.shape)}  ← (mu-origin)/spacing")
    print(f"      誤 (既定のまま)          : ピーク "
          f"{np.unravel_index(int(np.argmax(ng)), ng.shape)}  ← 世界座標をそのまま添字に")
    print(f"      どちらも有限で、どちらも「もっともらしい密度」を返す")

    print(f"\n  ★誤り例: 角度にラジアンを渡す")
    print(f"      角度 90 度  -> 復元 {R.matrix_to_angle(R.angle_to_matrix(90.0)):.6f} 度")
    print(f"      π/2 を「度」として渡す -> 復元 "
          f"{R.matrix_to_angle(R.angle_to_matrix(math.pi / 2)):.6f} 度  "
          f"(例外は出ず、57.3 分の 1 だけ回る)")

    cr = np.array([1.0e6])
    print(f"\n  ★誤り例: 積算窓 [s] を取り違える([Hz] x [s] = [counts])")
    print(f"      gate 1 ms -> {R.countrate_to_counts(cr, 1e-3)[0]:.1f} counts")
    print(f"      gate 1 s  -> {R.countrate_to_counts(cr, 1.0)[0]:.1f} counts  "
          f"(1000 倍。どちらも非負の 1-D なので型検査は通る)")


# --------------------------------------------------------------------------- #
def step6_fail_closed():
    """(6) fail-closed ―― 黙って通さないことを実際に確かめる。"""
    _rule("(6) fail-closed ―― 黙って通さない")
    dense = np.zeros((3, 4, 5, 6))
    scattered = np.zeros((7, 3))
    cases = [
        ("非有限の法線", lambda: R.normals_to_angles(np.array([[1.0, np.nan, 0.0]]))),
        ("零ベクトルの法線", lambda: R.normals_to_angles(np.array([[0.0, 0.0, 0.0]]))),
        ("空配列", lambda: R.pairs_to_signal(np.zeros((0, 2)))),
        ("仰角 100 度", lambda: R.angles_to_normals(np.array([[0.0, 100.0]]))),
        ("形状指数 |S|>1", lambda: R.shape_index_to_curvature(np.array([[1.5, 1.0]]))),
        ("長さ違いの「対」", lambda: R.pairs_to_signal((np.zeros(10), np.zeros(11)))),
        ("小入力から巨大割当", lambda: R.keypoints_to_image2d(np.array([[1.0, 1.0]]),
                                                              shape=(40000, 40000))),
        ("画像外の keypoint", lambda: R.keypoints_to_image2d(
            np.array([[3.0, 3.0], [99.0, 3.0]]), shape=(16, 16))),
        ("散在フローを密 op へ", lambda: R.flow_magnitude(scattered)),
        ("密フローを散在 op へ", lambda: R.flow_speed(dense)),
        ("重複点から sigma", lambda: R.points_to_gaussians(np.zeros((8, 3)))),
        ("定数体積の相関", lambda: R.correlation_score(np.ones((8,) * 3), np.ones((8,) * 3))),
        ("dict 記述子", lambda: R.descriptor_to_matrix({(0, 0): 0.5})),
        ("gate 0 秒", lambda: R.countrate_to_counts(np.array([1.0]), gate_s=0.0)),
    ]
    bad = 0
    for label, fn in cases:
        try:
            fn()
        except ValueError as exc:
            msg = str(exc)
            print(f"  拒否 {label:22s}: {msg[:76]}")
        else:
            bad += 1
            print(f"  ★通過 {label:22s}: 拒否されなかった")
    print(f"\n  {len(cases) - bad}/{len(cases)} が文書化された ValueError で拒否")
    return bad


# --------------------------------------------------------------------------- #
def main():
    print(__doc__.split("【グラウンドトゥルース")[0].strip())
    step1_dead_vocabulary()
    step2_exact_roundtrips()
    step3_lossy_roundtrips()
    step4_cross_representation_loop()
    step5_axes_and_units()
    bad = step6_fail_closed()

    _rule("まとめ ―― 往復誤差表(reprconv.selftest と同じ実測)")
    R.selftest()
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
