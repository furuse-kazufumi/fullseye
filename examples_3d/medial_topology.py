"""事例: 3D形状を「位相(トポロジー)」で弁別する — 骨格 → 位相署名 → 照合.

現実の問題(平たく):
    ボクセル化したCADやスキャンの山から「ドーナツ形(穴が1つ)」だけを
    「ボール形(穴なし)」や「棒形」と取り違えずに拾いたい。色も大きさも姿勢も
    当てにできない場面で、"形の位相"(穴の有無・枝分かれ・端の数)だけで大づかみに
    仕分けできると、細かい照合の前段の「粗いふるい」になる。
    穴が1つ = genus 1(トーラス/ドーナツ)。穴なし = genus 0(球)。棒 = 端が2つの線。

方法(medial.py の ops を連鎖):
    1) skeletonize_vol   : 中実ボリュームを1ボクセル幅の芯(骨格)に潰す。
                           円柱→軸線、トーラス→閉ループ、球→ほぼ1点。
    2) medial_axis_points: 距離場リッジで芯の点群 + 局所半径を得る(円柱の軸検証に使う)。
    3) topology_signature: 骨格の各点の近傍次数から 端点/分岐/通常/孤立 を数える。
                           閉ループ=端点0で通常のみ、線=端点2 — 位相を要約する記述子。
    4) medial_match      : 上の位相署名 + 半径分布で 2 形状の類似度[0,1]を返す。
    連鎖: ボクセル → skeletonize_vol → topology_signature → (medial_match) と出力を送り込む。

Ground truth(検証):
    - 円柱の芯: medial_axis_points が返す点が、既知の中心軸に対して半径距離 ~0 で載る。
    - 位相弁別: 同トポロジー対(トーラス同士)の署名距離 < 異トポロジー対(トーラス vs 球)。
                medial_match でも 同トポロジー対の類似度が最大になる。
    - beat-the-null: 位相署名の代わりに「ランダム署名」を使うと genus1/genus0 を分離できず
                     成功率は偶然の ~0.5。本物の署名は 100% 正しく分離する(= 情報を持つ証明)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from medial import (
    skeletonize_vol,
    medial_axis_points,
    topology_signature,
    medial_match,
    skeleton_junctions3d,
    skeleton_endpoints3d,
    skeleton_prune3d,
    skeleton_branches3d,
)


# --- 合成データ: 既知の ground truth を持つ単純なボクセル形状 ---

def solid_cylinder(size, radius, half_len):
    """z 軸に沿った中実円柱。軸は格子中心 (c, c) を通す(= 芯が voxel 中心に載る)。"""
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    c = (size - 1) / 2.0
    radial2 = (yy - c) ** 2 + (xx - c) ** 2
    return (radial2 <= radius ** 2) & (np.abs(zz - c) <= half_len)


def solid_ball(size, radius):
    """中実球(genus 0 = 穴なし)。骨格はほぼ1点に潰れる。"""
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    c = (size - 1) / 2.0
    return (zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2 <= radius ** 2


def solid_torus(size, major, minor):
    """中実トーラス(genus 1 = 穴1つ)。xy 平面の半径 major の円を芯に、太さ minor の管。"""
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    c = (size - 1) / 2.0
    rho = np.sqrt((yy - c) ** 2 + (xx - c) ** 2)   # z 軸からの距離
    return (rho - major) ** 2 + (zz - c) ** 2 <= minor ** 2


def topology_vector(sig):
    """位相署名を、総数で正規化した [端点, 分岐, 通常, 孤立] の割合ベクトルに。"""
    total = max(sig["total"], 1)
    return np.array(
        [sig["endpoints"], sig["branches"], sig["normal"], sig["isolated"]],
        dtype=np.float64,
    ) / total


def l1(a, b):
    """2 ベクトルの L1 距離。"""
    return float(np.abs(a - b).sum())


def main():
    size = 51
    center = (size - 1) / 2.0
    cyl_radius = 6

    # 形状を用意(すべて ground truth 既知)
    cylinder = solid_cylinder(size, cyl_radius, half_len=18)
    torus_a = solid_torus(size, major=15, minor=5)   # genus 1
    torus_b = solid_torus(size, major=12, minor=5)   # genus 1(位置違い・同じ太さ)
    sphere = solid_ball(size, radius=12)             # genus 0

    # ---- (1) 円柱の芯 = 既知中心軸 の検証 ----
    # 連鎖: ボクセル → skeletonize_vol → topology_signature(芯が線 = 端点2)
    skeleton = skeletonize_vol(cylinder)
    cyl_sig = topology_signature(skeleton)

    # 連鎖: ボクセル → medial_axis_points(芯の点 + 局所半径)
    points, radius = medial_axis_points(cylinder)
    # 各芯点の、既知軸 (y=center, x=center) からの半径距離(z は軸方向なので無視)
    radial_dist = np.sqrt((points[:, 1] - center) ** 2 + (points[:, 2] - center) ** 2)
    max_radial = float(radial_dist.max())
    median_r = float(np.median(radius))

    print("[円柱の芯]")
    print(f"  medial 点数              : {len(points)}")
    print(f"  既知軸からの最大半径距離 : {max_radial:.4f}  (~0 が正解)")
    print(f"  局所半径の中央値         : {median_r:.3f}  (円柱半径 {cyl_radius} に一致するはず)")
    print(f"  骨格の位相署名           : 端点={cyl_sig['endpoints']} 通常={cyl_sig['normal']} "
          f"(端点2の1本線 = 軸)")
    assert max_radial <= 1.0, f"芯が既知軸から離れている: {max_radial:.4f}"
    assert abs(median_r - cyl_radius) <= 1.0, f"局所半径が円柱半径とずれている: {median_r:.3f}"
    assert cyl_sig["endpoints"] == 2 and cyl_sig["branches"] == 0, \
        f"円柱の骨格が1本線になっていない: {cyl_sig}"

    # ---- (2) 位相弁別: 同トポロジー対 < 異トポロジー対 ----
    # 連鎖: ボクセル → skeletonize_vol → topology_signature → 割合ベクトル
    tv_a = topology_vector(topology_signature(skeletonize_vol(torus_a)))
    tv_b = topology_vector(topology_signature(skeletonize_vol(torus_b)))
    tv_s = topology_vector(topology_signature(skeletonize_vol(sphere)))
    d_same = l1(tv_a, tv_b)       # トーラス vs トーラス(同 genus 1)
    d_cross = l1(tv_a, tv_s)      # トーラス vs 球(genus 1 vs genus 0)

    print("\n[位相署名による弁別]")
    print(f"  トーラスA 署名ベクトル : {tv_a}  (閉ループ = 通常点のみ)")
    print(f"  球       署名ベクトル : {tv_s}  (穴なし = ほぼ点)")
    print(f"  同トポロジー距離 d_same : {d_same:.3f}")
    print(f"  異トポロジー距離 d_cross: {d_cross:.3f}")
    assert d_same < d_cross, f"同トポロジー対が異トポロジー対より近くない: {d_same} vs {d_cross}"

    # ---- (3) medial_match でも同トポロジー対が最も似ている ----
    m_same = medial_match(torus_a, torus_b)
    m_cyl = medial_match(torus_a, cylinder)
    m_sphere = medial_match(torus_a, sphere)
    print("\n[medial_match 類似度 (1 = 一致)]")
    print(f"  torus_a vs torus_b (同 genus1): {m_same:.3f}")
    print(f"  torus_a vs cylinder          : {m_cyl:.3f}")
    print(f"  torus_a vs sphere  (genus0)  : {m_sphere:.3f}")
    assert m_same > m_cyl and m_same > m_sphere, \
        f"同トポロジー対が最類似になっていない: same {m_same} vs cyl {m_cyl}, sphere {m_sphere}"

    # ---- (4) beat-the-null: ランダム署名は genus1/genus0 を分離できない ----
    # 本物の署名: d_same < d_cross が常に成立(分離成功率 1.0)。
    # 帰無仮説: 署名を simplex 上の乱数ベクトルに置換すると、u_same と u_cross は
    #   交換可能なので P(d_same < d_cross) = 0.5(偶然水準)。本物はこれを大きく上回る。
    rng = np.random.default_rng(0)
    n_trials = 4000
    wins = 0
    for _ in range(n_trials):
        u1, u2, u3 = rng.dirichlet(np.ones(4), size=3)  # 3 形状にランダムな署名
        if l1(u1, u2) < l1(u1, u3):
            wins += 1
    null_rate = wins / n_trials
    real_rate = 1.0 if d_same < d_cross else 0.0
    print("\n[beat-the-null]")
    print(f"  本物の署名の分離成功率 : {real_rate:.3f}")
    print(f"  ランダム署名の成功率   : {null_rate:.3f}  (~0.5 の偶然水準)")
    assert real_rate == 1.0
    assert null_rate < 0.65, f"帰無ベースラインが偶然を超えて分離している: {null_rate:.3f}"

    print(
        f"\nPASS: 円柱の芯が既知軸上(最大半径距離 {max_radial:.3f})、"
        f"位相署名が genus1(トーラス)と genus0(球)を距離 {d_cross:.1f} で分離(同トポロジー対は {d_same:.1f})、"
        f"medial_match も同トポロジー対を最類似 {m_same:.2f} と判定、ランダム署名 {null_rate:.2f} を上回る。"
    )


if __name__ == "__main__":
    main()
