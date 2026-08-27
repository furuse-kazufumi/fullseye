# -*- coding: utf-8 -*-
"""事例: 大域記述子(D2/A3)による形状検索。

実問題: 3D スキャンした部品を、向きやスケールがバラバラなカタログの中から「同じ形の
ものはどれか」で引き当てたい。点群を回転・拡大しても値が変わらない大域記述子
(ペア距離の分布 D2、三点角度の分布 A3、主軸の広がり)に落とし込めば、記述子ベクトル
どうしの距離が小さいものが同形状として検索できる。ここでは球/立方体/棒のミニ形状DBを
作り、球をランダム回転+スケールしたクエリが、DB の中の球に最も近く引き当てられること、
かつ同形状の距離 < 異形状の距離になることを数値で確かめる(回転・スケール不変性)。
"""
import numpy as np
import descriptors3d as D


# --- 形状ジェネレータ(体積を一様充填した点群) ---
def sphere(n=4000, r=1.0, seed=1):
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n:
        c = rng.uniform(-r, r, size=(n, 3))
        c = c[np.einsum("ij,ij->i", c, c) <= r * r]      # 球内部だけ残す(棄却サンプリング)
        pts.extend(c.tolist())
    return np.asarray(pts[:n], dtype=np.float64)


def cube(n=4000, s=1.0, seed=2):
    return np.random.default_rng(seed).uniform(-s, s, size=(n, 3))


def rod(n=4000, length=6.0, thick=0.15, seed=3):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-length, length, size=n)
    y = rng.uniform(-thick, thick, size=n)
    z = rng.uniform(-thick, thick, size=n)
    return np.stack([x, y, z], axis=1)


def random_rotation(seed=7):
    """QR 分解で決定論的な回転行列(det=+1)を作る。"""
    rng = np.random.default_rng(seed)
    q, r = np.linalg.qr(rng.standard_normal((3, 3)))
    q *= np.sign(np.diag(r))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def main():
    # --- 形状DB: 各クラスを別サンプルで生成し、大域記述子に変換 ---
    db = {
        "sphere#1": D.describe(sphere(seed=101), bins=64, seed=0),
        "sphere#2": D.describe(sphere(seed=202), bins=64, seed=0),   # 同クラス・別サンプル
        "cube#1":   D.describe(cube(seed=303), bins=64, seed=0),
        "cube#2":   D.describe(cube(seed=404), bins=64, seed=0),
        "rod#1":    D.describe(rod(seed=505), bins=64, seed=0),
        "rod#2":    D.describe(rod(seed=606), bins=64, seed=0),
    }

    # --- クエリ: 新しい球を作り、ランダム回転 + 4.7 倍スケール(検索の頑健性を試す) ---
    q_pts = sphere(seed=999)
    q_pts = (q_pts @ random_rotation(seed=7).T) * 4.7 + np.array([12.0, -5.0, 3.0])  # 回転+スケール+並進
    q_desc = D.describe(q_pts, bins=64, seed=0)

    # --- 記述子距離で DB を検索(小さいほど同形状) ---
    ranked = sorted(db.items(), key=lambda kv: D.shape_distance(q_desc, kv[1], metric="l1"))
    print("クエリ(回転+4.7倍スケールした球)に対する検索ランキング:")
    for name, desc in ranked:
        print(f"  {name:10s}  distance = {D.shape_distance(q_desc, desc):.4f}")

    best_name = ranked[0][0]
    best_class = best_name.split("#")[0]

    # 同クラス平均距離 vs 異クラス平均距離
    same = np.mean([D.shape_distance(q_desc, db[k]) for k in db if k.startswith("sphere")])
    diff = np.mean([D.shape_distance(q_desc, db[k]) for k in db if not k.startswith("sphere")])
    print(f"\n同形状(球)への平均距離 = {same:.4f}")
    print(f"異形状(立方体/棒)への平均距離 = {diff:.4f}")

    # 回転+スケール不変性を直接確認: 元の球と、回転+スケールしたクエリの記述子距離
    base = D.describe(sphere(seed=999), bins=64, seed=0)
    inv_gap = D.shape_distance(base, q_desc)
    print(f"回転+スケール不変性: 同一球(原型 vs 変換後)の記述子距離 = {inv_gap:.4f}")

    # === GT 検証 ===
    # 1) 検索トップが球クラス(向き・スケールが違っても同形状を引き当てる)
    assert best_class == "sphere", best_name
    # 2) 同形状の距離 < 異形状の距離
    assert same < diff, (same, diff)
    # 3) 回転+スケールしても同一形状の記述子はほぼ動かない(不変性)
    assert inv_gap < 0.05, inv_gap
    print("OK: 大域記述子で回転・スケール不変な形状検索が成立(同形状 < 異形状)")


if __name__ == "__main__":
    main()