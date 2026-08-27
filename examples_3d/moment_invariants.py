# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 置き方・向き・撮影距離が変わっても「形そのもの」で物体を同定する.

現実の問題:
    同じ部品でも、ベルト上のどこに・どの向きで置かれ、カメラからどれだけ離れて
    撮られるかで、点群の生の座標も生のモーメントも大きく変わる。生の数値で比べると
    「同じ物体を別の場所で撮っただけ」が「別の物体」に見えてしまう。位置・姿勢・
    撮影距離に依らず、形だけを数値化して同定したい。

方法 (moment_invariants):
    重心中心化(並進を除去)→ RMS 半径で正規化(一様スケールを除去)→ 正規化共分散の
    固有値と高次半径モーメントを並べる(回転で不変)。結果は並進・回転・一様スケールに
    不変な 6 次元ベクトル [λ̂1, λ̂2, λ̂3, J2, J3, m4]。

Ground-truth 検証(この事例で確認すること):
    (1) 不変性: 同一の点群に既知の (回転 R, 並進 t, 一様スケール s) を掛けても、
        moment_invariants の相対変化は 1% 未満(数学的には厳密不変なので実測は
        丸め誤差水準)。
    (2) beat-the-null: 生の(非中心・非正規化)モーメントは同じ変換で桁違いに動く。
        中心化のみ(central_moments)や慣性テンソルの生成分(inertia_tensor)でも、
        スケール・回転の正規化が無いため大きく動く。この「はしご」を並べて、
        不変量だけが動かないことを示す。
    (3) 識別性: 別形状(細長い箱 vs 等方な球)は、同形状(変換後)の距離を桁違いに
        超えて分離する(定数を返すだけの実装では通らない)。
    (4) 既知の解析値: 一様な充実球の不変量は λ̂≈(1/3,1/3,1/3), m4=25/21≈1.190 に
        一致する(不変性だけでなく、値そのものが正しいことを固定する)。

ops のチェイン:
    inertia_tensor / central_moments(はしごの途中段)→ moment_invariants(不変量)→
    shape_distance(不変量ベクトル同士の距離)を数珠つなぎに使い、段階的に変換の
    自由度を取り除く様子を示す。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

# 事例はリポジトリ直下のモジュールを実物のまま import する。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import moments3d as m3  # noqa: E402


# --------------------------------------------------------------------------- #
# 補助: 変換と合成形状                                                          #
# --------------------------------------------------------------------------- #
def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列(ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * k + (1 - np.cos(th)) * k @ k


def solid_box(dims, n, seed):
    """原点中心・辺長 dims の充実直方体から一様に n 点サンプル(非対称=固有値が明瞭)。"""
    rng = np.random.default_rng(seed)
    return (rng.random((n, 3)) - 0.5) * np.asarray(dims, float)


def solid_sphere(radius, n, seed):
    """原点中心・半径 radius の充実球から一様に n 点サンプル(等方=別形状)。"""
    rng = np.random.default_rng(seed)
    direction = rng.normal(size=(n, 3))
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    r = radius * rng.random(n) ** (1.0 / 3.0)   # 体積一様(r^2 dr の重み)
    return direction * r[:, None]


# --------------------------------------------------------------------------- #
# 補助: null baseline と相対変化                                                #
# --------------------------------------------------------------------------- #
def raw_origin_moments(points):
    """生の(非中心・非正規化)1 次・2 次モーメント(原点まわり)= null baseline。

    重心を引かない → 並進で動く。スケール正規化しない → 拡大で動く。
    「同じ物体を別の場所/距離で撮っただけ」でも大きく変化してしまう素朴な特徴。
    """
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    return np.array([
        x.mean(), y.mean(), z.mean(),
        (x * x).mean(), (y * y).mean(), (z * z).mean(),
        (x * y).mean(), (x * z).mean(), (y * z).mean(),
    ])


def second_order_vector(central_moment_dict):
    """central_moments の 2 次成分だけを並べたベクトル(中心化済・スケール正規化なし)。"""
    keys = [(2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
    return np.array([central_moment_dict[k] for k in keys])


def rel_change(a, b):
    """変換前後の相対変化 ||a-b|| / ||a||(小さいほど変換に不変)。"""
    a = np.asarray(a, float).ravel()
    b = np.asarray(b, float).ravel()
    return float(np.linalg.norm(a - b) / (np.linalg.norm(a) + 1e-12))


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    # --- 1) 合成データ: 既知の 2 形状(非対称な箱 と 等方な球) ---
    box = solid_box(dims=(4.0, 2.0, 1.0), n=6000, seed=0)
    sphere = solid_sphere(radius=1.0, n=12000, seed=1)

    # --- 2) 既知の剛体 + 一様スケール変換(同じ箱を別の場所/向き/距離で観測) ---
    rot = rotation_matrix([0.3, 1.0, 0.2], 40.0)
    trans = np.array([10.0, -5.0, 7.0])
    scale = 2.5
    box_moved = box @ rot.T * scale + trans

    # --- 3) 不変性のはしご: 特徴レベルごとに「変換前後の相対変化」を測る ---
    # ops をチェイン: inertia_tensor / central_moments(途中段)→ moment_invariants。
    rc_raw = rel_change(
        raw_origin_moments(box), raw_origin_moments(box_moved),
    )
    rc_central = rel_change(
        second_order_vector(m3.central_moments(box, 2)),
        second_order_vector(m3.central_moments(box_moved, 2)),
    )
    rc_inertia = rel_change(
        m3.inertia_tensor(box).ravel(), m3.inertia_tensor(box_moved).ravel(),
    )
    inv_box = m3.moment_invariants(box)
    inv_box_moved = m3.moment_invariants(box_moved)
    rc_invariant = rel_change(inv_box, inv_box_moved)

    print("=== 不変性のはしご(同一の箱に R,t,s を掛けた前後の相対変化)===")
    print(f"  生モーメント(非中心・非正規化) : {rc_raw:12.6f}   (並進+回転+スケールで動く / null)")
    print(f"  central_moments(中心化のみ)     : {rc_central:12.6f}   (並進は除くが回転+スケールで動く)")
    print(f"  inertia_tensor(慣性の生成分)    : {rc_inertia:12.6f}   (回転+スケールで動く)")
    print(f"  moment_invariants(不変量)        : {rc_invariant:12.3e}   (すべて除去=ほぼ不変)")

    # --- 4) 識別性: 不変量を shape_distance にチェインして別形状を分離 ---
    inv_sphere = m3.moment_invariants(sphere)
    d_same = m3.shape_distance(inv_box, inv_box_moved)   # 同形状(変換後)
    d_diff = m3.shape_distance(inv_box, inv_sphere)      # 別形状(箱 vs 球)
    separation = d_diff / (d_same + 1e-15)
    print("\n=== 識別性(不変量ベクトル間の距離)===")
    print(f"  同形状(箱 と 変換後の箱)        : {d_same:12.3e}")
    print(f"  別形状(箱 と 球)                : {d_diff:12.6f}")
    print(f"  分離比 (別形状 / 同形状)          : {separation:12.3e}")

    # --- 5) 既知の解析値: 一様充実球の不変量 ---
    lam_sphere = inv_sphere[:3]
    m4_sphere = inv_sphere[5]
    m4_analytic = 25.0 / 21.0   # = 75/63 ≈ 1.190476(充実球の mean(r^4)/mean(r^2)^2)
    print("\n=== 既知の解析値(一様充実球)===")
    print(f"  固有値 λ̂ (理論 0.3333 x3)         : {lam_sphere[0]:.4f}, {lam_sphere[1]:.4f}, {lam_sphere[2]:.4f}")
    print(f"  m4 (理論 25/21 = {m4_analytic:.4f})    : {m4_sphere:.4f}")

    # --- 6) ground-truth の assert ---
    # (1) 不変性: 不変量の相対変化 < 1%(実測は丸め誤差水準)。
    assert rc_invariant < 0.01, f"不変量が変換で動きすぎ: {rc_invariant:.3e}"
    # (2) beat-the-null: 生モーメントは同変換で桁違いに大きく動く。
    assert rc_raw > 1.0, f"null が動かない(前提崩れ): {rc_raw:.6f}"
    assert rc_central > 0.5, f"中心化のみが動かない(前提崩れ): {rc_central:.6f}"
    assert rc_inertia > 0.5, f"慣性生成分が動かない(前提崩れ): {rc_inertia:.6f}"
    # 不変量は各 null より 2 桁以上安定。
    assert rc_invariant < rc_raw / 100.0, "不変量が生モーメントを上回れていない"
    assert rc_invariant < rc_central / 100.0, "不変量が中心化のみを上回れていない"
    assert rc_invariant < rc_inertia / 100.0, "不変量が慣性生成分を上回れていない"
    # (3) 識別性: 別形状は同形状(変換後)を桁違いに超えて分離。
    assert d_diff > 0.1, f"別形状の分離が弱い: {d_diff:.6f}"
    assert separation > 1e3, f"同形状と別形状が分離できていない: {separation:.3e}"
    # (4) 既知の解析値に一致(定数を返すだけの実装では通らない)。
    assert np.allclose(lam_sphere, 1.0 / 3.0, atol=0.03), f"球の固有値が理論とずれ: {lam_sphere}"
    assert abs(m4_sphere - m4_analytic) < 0.05, f"球の m4 が理論とずれ: {m4_sphere:.4f}"

    print(
        "\nPASS: moment_invariants は剛体+一様スケール変換で相対変化 "
        f"{rc_invariant:.2e}(<1%)= 生モーメント {rc_raw:.1f} 等の null を 2 桁以上上回り、"
        f"別形状は同形状を {separation:.1e} 倍の距離で分離、"
        f"球の解析値(λ̂≈1/3, m4≈{m4_analytic:.3f})とも一致した。"
    )


if __name__ == "__main__":
    main()
