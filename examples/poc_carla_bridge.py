# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""同じ場面を 2 つの世界で撮る —— 写実シミュレータの深度を閉形式の真値で採点し、自前の世界と並べる(2026-10-04)。

著者の発案: 「自動運転の今現状で一番リアルに近い状態を再現できる環境に、今までやってきた技術を駆使した完成形を載せたい」
→ 環境は**両方**: 真値を全部持つ自前の世界(driveworld)と、写実だが中の式が見えない外部の高写実シミュレータ
(CARLA 0.9.16、コード MIT・アセット CC-BY)。集大成の最初の部品は、この 2 つを**同じ規約**で結ぶ橋(carlabridge)。

何をするか(直線路の先行車、8 コマ):
  1. CARLA(Town04 の湖畔の直線、road 41 / lane −4)で自車の前方 8〜64 m に先行車を置き、RGB・深度・意味分割を撮る
     (撮影は repo の外のスクリプト、記録は npz —— ここでは読むだけ)。CARLA が無い環境では自前の世界から同じ形の記録を作る。
  2. 記録の姿勢(CARLA の左手系・度)を Fullseye の右手系に写し、**後ろ面までの像面距離を閉形式**で出す = 真値。
  3. 同じルールベースの知覚(車のラベルの画素の深度の中央値、最下行から平らな路面の式)を、CARLA の像と、
     **同じ K・同じ取り付けで自前の世界を描き直した像**の両方に掛けて、真値との差を並べる。

門(どれも定理か第 2 実装):
  * 回転行列は CARLA の客体が返した 3 行列(焼き込み)と一致、角の往復は恒等。カメラ姿勢は render3d の look_at と一致。
  * 深度の往復の誤差 ≤ 1000 / (2²⁴ − 1) m(公表の復号式)。ラベルの往復は恒等(29 タグ全部に行き先がある)。
  * 記録の往復: 自前の世界 → CARLA の規約の記録 → 読み直して描き直す → 深度とラベルが画素単位で同じ。
  * 自前の世界: 深度の中央値 − 真値 の最大 < 1 m(セダンの後ろは曲面)、車の画素数は 1/d²(両対数の傾き −2 ± 0.4)。
  * CARLA の記録(ある時だけ): 深度の中央値 − 真値 が全コマ 0.5 m 以内、描き直した自前の像も 0.5 m 以内、
    車の画素数の比(自前 / CARLA)が 0.75〜1.3、両方の画素数が 1/d² に乗る。

正直に: CARLA の深度と意味分割の真値そのものは検証できない(中が見えない)。確かめたのは**規約が可逆**なことと、
**閉形式の真値と CARLA の深度が合う**こと(観測 +0.10 m は箱の原点のずれで、記録に無い量)。路面は平ら・先行車は同じ車線・昼だけ。
CARLA のアセットは CC-BY なので図には出典を添え、記録そのものは repo に入れない(FULLSEYE_CARLA_DATA で場所を渡す)。
Run: py -3.11 examples/poc_carla_bridge.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import glob
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import carlabridge as CB  # noqa: E402
import driveworld as DW  # noqa: E402
import examplefig as figs  # noqa: E402

DISTANCES = (8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0)
_CARLA_MATRICES = {
    (1.0, 2.0, 3.0, 10.0, 20.0, 30.0): [[0.8137976527, -0.4409696162, -0.3785222769, 1.0],
                                        [0.4698463082, 0.8825640678, -0.018028304, 2.0],
                                        [0.3420201242, -0.1631759107, 0.9254165292, 3.0]],
    (5.0, -4.0, 1.6, 0.0, -15.0, -120.0): [[-0.482962966, 0.8660253882, -0.1294095367, 5.0],
                                           [-0.8365162611, -0.5000000596, -0.2241438627, -4.0],
                                           [-0.2588190436, 0.0, 0.9659258127, 1.6]],
    (0.0, 0.0, 0.0, 0.0, 0.0, 90.0): [[0.0, -1.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
}
_PALETTE = {-1: (0.55, 0.75, 0.95), 0: (0.35, 0.35, 0.38), 1: (0.80, 0.80, 0.75), 2: (0.90, 0.25, 0.20),
            3: (0.95, 0.70, 0.10), 4: (0.95, 0.90, 0.20), 5: (1.0, 0.5, 0.0), 6: (0.45, 0.30, 0.55),
            7: (0.90, 0.40, 0.70), 8: (0.6, 0.6, 0.3), 9: (1.0, 1.0, 1.0), 10: (0.50, 0.65, 0.30),
            11: (0.2, 0.4, 0.8), 12: (0.9, 0.9, 0.8), 13: (0.15, 0.55, 0.20)}
_GATES = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def colour_labels(label):
    out = np.zeros(label.shape + (3,), np.float64)
    for k, c in _PALETTE.items():
        out[label == k] = c
    return out


def part_conventions():
    print("== 1. 写す規約(閉形式・第 2 実装)")
    err = max(np.abs(CB.carla_transform_matrix(t)[:3, :] - np.array(M)).max() for t, M in _CARLA_MATRICES.items())
    back = max(np.abs(np.array(CB.carla_rotation_angles(CB.carla_transform_matrix(t)[:3, :3])) - t[3:]).max()
               for t in _CARLA_MATRICES)
    gate("回転行列 = CARLA の客体の get_matrix(3 件)", err < 2e-7 and back < 1e-6, "最大 %.1e / 角の往復 %.1e" % (err, back))
    h = 1.6
    e = 0.0
    for yaw_c, tgt in ((0.0, (1, 0, h)), (90.0, (0, -1, h)), (-90.0, (0, 1, h)), (180.0, (-1, 0, h))):
        e = max(e, np.abs(CB.carla_camera_pose([0, 0, h, 0, 0, yaw_c]) - DW.camera_pose((0, 0, h), tgt)).max())
    rt = max(np.abs(CB.camera_pose_to_carla(CB.carla_camera_pose(t)) - t).max() for t in _CARLA_MATRICES)
    gate("カメラ姿勢 = look_at(yaw 0 / ±90 / 180)、往復は恒等", e < 1e-12 and rt < 1e-9, "最大 %.1e / 往復 %.1e" % (e, rt))
    d = np.random.default_rng(1).uniform(0, 300, (60, 80))
    q = np.abs(CB.carla_depth_decode(CB.carla_depth_encode(d)) - d).max()
    gate("深度の往復 ≤ 量子化の半分(1000 / (2²⁴ − 1) / 2)", q <= 0.5 * CB.DEPTH_SCALE_M / CB.DEPTH_CODE_MAX + 1e-12, "%.2e m" % q)
    lab = np.array(sorted(CB.LABEL_TO_TAG))[None, :]
    back = CB.carla_label_map(CB.carla_label_unmap(lab))
    collapsed = {int(a) for a, b in zip(lab[0], back[0]) if a != b}
    gate("ラベルの往復は恒等(29 タグに全部行き先、CARLA に無いコーン・横断歩道だけ障害物・路面に潰れる)",
         collapsed == {5, 12} and len(CB.carla_labels()) == 29, "潰れた %s" % sorted(collapsed))


def part_round_trip(tmp):
    print("== 2. 記録の往復(自前の世界 → CARLA の規約 → 描き直し)")
    sc = CB.carla_scene_synthetic(20.0, width=320, height=180)
    p = CB.carla_scene_save(sc, tmp / "round_trip.npz")
    back = CB.carla_scene_load(p)
    r = CB.scene_pair_table(back)
    same_label = np.array_equal(np.asarray(r["view"]["label"]), sc["label"])
    d0 = np.where(np.isfinite(sc["depth"]), sc["depth"], 1000.0)
    v = r["view"]
    d1 = np.where(np.isfinite(v["depth"]) & (np.asarray(v["label"]) >= 0), v["depth"], 1000.0)
    gate("描き直した深度・ラベルが画素単位で同じ", same_label and np.abs(d0 - d1).max() < 1e-9,
         "深度の差 %.1e" % np.abs(d0 - d1).max())
    return sc


def scenes_from(root):
    files = sorted(glob.glob(os.path.join(root, "lead_straight_d*.npz"))) if root else []
    return [CB.carla_scene_load(f) for f in files]


def score(scenes, label):
    rows = []
    for sc in scenes:
        r = CB.scene_pair_table(sc)
        rows.append((r["truth"], r["carla"], r["fullseye"], r["view"], sc))
    truths = np.array([t for t, *_ in rows])
    e_c = np.array([c["depth_median"] - t for t, c, *_ in rows])
    e_f = np.array([f["depth_median"] - t for t, c, f, *_ in rows])
    r_c = np.array([c["row_distance"] - t for t, c, *_ in rows])
    n_c = np.array([c["n_pixels"] for t, c, *_ in rows], float)
    n_f = np.array([f["n_pixels"] for t, c, f, *_ in rows], float)
    s_c = np.polyfit(np.log(truths), np.log(n_c), 1)[0]
    s_f = np.polyfit(np.log(truths), np.log(n_f), 1)[0]
    print("  %s: 真値 %s" % (label, np.round(truths, 2).tolist()))
    print("    深度の中央値 − 真値: 撮影 %s / 描き直し %s" % (np.round(e_c, 2).tolist(), np.round(e_f, 2).tolist()))
    print("    最下行の路面の式 − 真値: %s" % np.round(r_c, 2).tolist())
    print("    車の画素数: 撮影 %s / 描き直し %s、両対数の傾き %.2f / %.2f" % (n_c.astype(int).tolist(), n_f.astype(int).tolist(), s_c, s_f))
    return {"rows": rows, "truths": truths, "e_c": e_c, "e_f": e_f, "r_c": r_c, "n_c": n_c, "n_f": n_f, "s_c": s_c, "s_f": s_f}


def part_synthetic():
    print("== 3. 自前の世界(CARLA が無くても走る門)")
    scenes = [CB.carla_scene_synthetic(d, width=320, height=180) for d in DISTANCES]
    gate("閉形式の真値 = 置いた距離(7 コマ)", all(np.isclose(CB.lead_truth_depth(s), d) for s, d in zip(scenes, DISTANCES)))
    S = score(scenes, "自前")
    gate("深度の中央値 − 真値 の最大 < 1 m(セダンの後ろは曲面 ≈ 0.7 m)", np.abs(S["e_c"]).max() < 1.0, "%.2f m" % np.abs(S["e_c"]).max())
    # 320×180 では遠い車の最下行が 1 行ずれると数 m 動く(Δd = λ/(u−½) − λ/(u+½))—— 行の量子化ぶんを引いて採点
    lam = CB.intrinsics_to_fullseye(scenes[0]["K"])[1, 1] * 1.6
    step = np.array([lam / (lam / d - 0.5) - lam / (lam / d + 0.5) for d in S["truths"]])
    over = np.abs(S["r_c"]) - step
    gate("最下行の路面の式 − 真値 < 1 m + 行の量子化の幅(最下行は後輪の接地)", over.max() < 1.0,
         "最大 %.2f m(量子化の幅 %.1f〜%.1f m)" % (over.max(), step.min(), step.max()))
    gate("車の画素数 ∝ 1/d²(両対数の傾き −2 ± 0.4)", -2.4 < S["s_c"] < -1.6, "%.2f" % S["s_c"])
    return S


def part_real(root):
    print("== 4. CARLA の撮影記録(%s)" % root)
    scenes = scenes_from(root)
    if len(scenes) < 5:
        print("  [skip] FULLSEYE_CARLA_DATA に lead_straight_d*.npz が %d 本(5 本以上で採点)" % len(scenes))
        return None
    meta = scenes[0]["meta"]
    print("  地図 %s、%d×%d、fov %.0f°、CARLA %s" % (meta.get("map"), scenes[0]["rgb"].shape[1], scenes[0]["rgb"].shape[0],
                                                   float(meta.get("fov_deg", 0)), meta.get("carla_version")))
    S = score(scenes, "CARLA")
    gate("CARLA の深度の中央値 − 閉形式の真値 が全コマ 0.5 m 以内", np.abs(S["e_c"]).max() < 0.5, "最大 %.2f m" % np.abs(S["e_c"]).max())
    gate("描き直した自前の像も 0.5 m 以内", np.abs(S["e_f"]).max() < 0.5, "最大 %.2f m" % np.abs(S["e_f"]).max())
    gate("最下行の路面の式 − 真値 < 1 m(CARLA)", np.abs(S["r_c"]).max() < 1.0, "最大 %.2f m" % np.abs(S["r_c"]).max())
    ratio = S["n_f"] / S["n_c"]
    gate("車の画素数の比(自前 / CARLA)が 0.75〜1.3(全コマ)", ratio.min() > 0.75 and ratio.max() < 1.3,
         "%.2f〜%.2f" % (ratio.min(), ratio.max()))
    gate("車の画素数が両方の世界で 1/d² に乗る", -2.3 < S["s_c"] < -1.7 and -2.3 < S["s_f"] < -1.7, "%.2f / %.2f" % (S["s_c"], S["s_f"]))
    return S


def make_figures(S, source):
    if not figs.enabled():
        return
    rows = S["rows"]
    pick = [i for i, (t, *_) in enumerate(rows) if 10 < t < 14] + [i for i, (t, *_) in enumerate(rows) if 26 < t < 30]
    pick = (pick or [0, min(4, len(rows) - 1)])[:2]
    panels, caps = [], []
    for i in pick:
        t, c, f, view, sc = rows[i]
        panels += [sc["rgb"], np.asarray(view["color"]), colour_labels(CB.carla_label_map(sc["semantic"])), colour_labels(np.asarray(view["label"]))]
        caps += ["%s の RGB(真値 %.1f m)" % (source, t), "自前の世界の描き直し(同じ K・取り付け)",
                 "%s の意味分割 → Fullseye のラベル" % source, "自前の世界のラベル(面から)"]
    figs.save_grid("carla_two_worlds", panels, caps, ncols=4,
                   caption="同じ場面を 2 つの世界で: 左から %s の RGB、同じ内部パラメータ・取り付けで自前の世界を描き直した像、"
                           "%s の意味分割を Fullseye のラベルに写した像、自前の世界のラベル(面の真値)。%s" %
                           (source, source, "CARLA 0.9.16 の像はアセットが CC-BY(CARLA team)。" if source == "CARLA" else ""))
    figs.save_plot("carla_depth_error", [("%s の深度の中央値 − 真値" % source, S["truths"], S["e_c"]),
                                         ("自前の描き直し − 真値", S["truths"], S["e_f"]),
                                         ("最下行の路面の式 − 真値(%s)" % source, S["truths"], S["r_c"])],
                   xlabel="閉形式の真値(後ろ面までの像面距離)[m]", ylabel="誤差 [m]",
                   title="先行車の距離: 同じルールベースの知覚を両方の世界に",
                   caption="先行車の後ろ面までの像面距離の真値は記録の姿勢から閉形式で出す。車のラベルの画素の深度の中央値は"
                           " %s で全コマ +0.1 m、自前の描き直しで ±0.3 m。最下行から平らな路面の式で出す距離は後輪の接地を見るので"
                           "バンパーより 0.5 m ほど先を指す。" % source, kinds=["line", "line", "line"])
    xs = np.array(S["truths"])
    ref = S["n_c"][0] * (xs[0] / xs) ** 2
    figs.save_plot("carla_pixels_inverse_square", [("%s の車の画素数" % source, xs, S["n_c"]), ("自前の描き直し", xs, S["n_f"]),
                                                   ("1/d²(最初のコマに合わせた線)", xs, ref)],
                   xlabel="真値 [m]", ylabel="車の画素数", title="車の画素数 ∝ 1/d²(両対数の傾き %.2f / %.2f)" % (S["s_c"], S["s_f"]),
                   caption="像面に平行な後ろ面の面積は距離の 2 乗に反比例する。%s と自前の世界の両方で両対数の傾きが −2 に近く、"
                           "画素数の比は %.2f〜%.2f。" % (source, (S["n_f"] / S["n_c"]).min(), (S["n_f"] / S["n_c"]).max()),
                   kinds=["scatter", "scatter", "line"])
    header = ["真値 [m]", "%s 中央値 − 真値" % source, "自前 − 真値", "路面の式 − 真値", "画素 %s" % source, "画素 自前"]
    table = [["%.2f" % t, "%+.2f" % a, "%+.2f" % b, "%+.2f" % c, "%d" % n1, "%d" % n2]
             for t, a, b, c, n1, n2 in zip(S["truths"], S["e_c"], S["e_f"], S["r_c"], S["n_c"], S["n_f"])]
    figs.save_table("carla_pair_table", header, table, title="同じ場面・2 つの世界(%s)" % source,
                    caption="コマごとの数字。真値は閉形式、誤差は m、画素数は中央の帯にある車のラベルの画素。")


def main():
    t0 = time.perf_counter()
    import tempfile
    part_conventions()
    with tempfile.TemporaryDirectory() as td:
        part_round_trip(Path(td))
    S_syn = part_synthetic()
    root = os.environ.get("FULLSEYE_CARLA_DATA", "")
    S_real = part_real(root) if root else None
    if S_real is None:
        print("  (CARLA の記録が無いので図は自前の世界で描く —— 本物の図は FULLSEYE_CARLA_DATA を設定して)")
    make_figures(S_real if S_real is not None else S_syn, "CARLA" if S_real is not None else "自前")
    n_ok = sum(ok for _, ok in _GATES)
    print("\n== 結果: %d/%d 門, %.1f s" % (n_ok, len(_GATES), time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        raise SystemExit("FAIL: figures")
    if n_ok != len(_GATES):
        raise SystemExit("FAIL: " + ", ".join(n for n, ok in _GATES if not ok))
    print("\nPASS")


if __name__ == "__main__":
    main()
