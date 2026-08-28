# -*- coding: utf-8 -*-
"""事例: 荒い円柱点群を掃除してから表面に沿った距離を測る (shape_analysis).

平たく言うと:
    深度センサやLiDARで円柱(缶・パイプ)を撮ると、点群には3種のゴミが乗る——
    (1) 遠くに飛んだ孤立点(飛び点)、(2) 面の上に乗ったザラザラ(センサノイズ)、
    (3) まばらな外れ値。これを順に落として整えてから、「表面をなぞって歩く距離」
    =測地距離(geodesic distance)を測る。缶の側面で2点の最短経路は、缶に定規を
    突き刺した直線(弦)ではなく、側面に沿う弧だ。円柱は切って広げると平面になる
    (可展面)ので、その弧の長さは解析式で厳密に分かる=真値がある。

    使うopを鎖にする(前処理→グラフ→測地/骨格):
      statistical_outlier_removal → radius_outlier_removal  … 飛び点・孤立点を除去
      mls_smooth                                            … 面に射影してノイズ除去
      knn_graph                                             … 掃除後の近傍グラフ
      geodesic_mesh                                         … 円柱メッシュ上の測地距離
      distance_ridge                                        … 同じ円柱(中身入り)の中心軸

検証(GT, 既知の正解):
    円柱を「表面点群」と「中身の詰まったvoxel」の2通りで持ち、真値を解析で用意する。
      * 外れ値除去: 注入した飛び点の集合はちょうど分かっているので、除去の適合率/再現率が
        1.0(飛び点を全部落とし、面の点は全部残す)。SOR→radiusの合成で面の点だけが残る。
      * MLS: 各点の「軸までの距離」の真値はR。平滑後にRからのRMSずれが減る。
      * knn_graph: 返る近傍indexが総当たりkNNと厳密一致、距離は昇順かつ再計算Euclidと一致。
      * geodesic_mesh: 測地距離が展開式 sqrt((R·Δθ)²+Δz²) と一致(代表ペアで相対誤差<3%)。
      * distance_ridge: 中身入り円柱のmedial(距離場の尾根)は中心軸そのもの。最大EDT=半径。

beat-the-null(素朴案を上回る):
      * MLS: 「何もしない」より軸ずれRMSが小さい。
      * knn_graph: kNN近傍は「ランダムな点」よりずっと近い。
      * geodesic_mesh: 直線(弦)距離は曲面を突っ切り系統的に過小評価する。角度が離れた点で
        本手法(グラフ測地)の相対誤差が弦の相対誤差を明確に下回る(弦は缶を貫通するズル)。
      * distance_ridge: 尾根は中心軸に集中(軸からの平均距離≈0)。前景voxel全体の平均半径とは桁違い。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import pcl_filter as F  # noqa: E402  SOR / radius / MLS
import geodesic3d as G  # noqa: E402  knn_graph / geodesic_mesh
import medial as M  # noqa: E402  distance_ridge

R, H = 1.0, 2.0           # 円柱の半径 / 高さ(ワールド単位)


def cylinder_surface(n_theta=60, n_z=40):
    """円柱側面を (θ, z) 格子で密サンプル。各点の真の (θ, z) も返す(GT用)。→ (N,3), θ, z。"""
    th = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    zz = np.linspace(0.0, H, n_z)
    TT, ZZ = np.meshgrid(th, zz, indexing="ij")
    TT, ZZ = TT.ravel(), ZZ.ravel()
    P = np.stack([R * np.cos(TT), R * np.sin(TT), ZZ], axis=1)
    return P, TT, ZZ


def cylinder_mesh(nt=48, nz=24):
    """閉じた円柱(θが一周)を三角メッシュ化。→ vertices (V,3), faces (F,3)。可展面なので測地=展開距離。"""
    tv = np.linspace(0.0, 2.0 * np.pi, nt, endpoint=False)
    zv = np.linspace(0.0, H, nz)
    verts = np.array([[R * np.cos(tv[it]), R * np.sin(tv[it]), zv[iz]]
                      for iz in range(nz) for it in range(nt)], dtype=float)

    def vid(iz, it):
        return iz * nt + (it % nt)      # θ を一周させる(閉じた筒)

    faces = []
    for iz in range(nz - 1):
        for it in range(nt):
            a, b = vid(iz, it), vid(iz, it + 1)
            c, d = vid(iz + 1, it), vid(iz + 1, it + 1)
            faces.append([a, b, d])
            faces.append([a, d, c])
    return verts, np.asarray(faces, dtype=int), tv, zv


def axis_radial_rms(P):
    """各点の「円柱軸(z軸)までの距離」の真値Rからのずれ RMS。→ float(小さいほど面に近い)。"""
    d_axis = np.hypot(P[:, 0], P[:, 1])       # sqrt(x²+y²) = 軸からの距離
    return float(np.sqrt(np.mean((d_axis - R) ** 2)))


def main() -> int:
    rng = np.random.default_rng(0)

    # === 1) 合成データ: 円柱の「表面点群」+ノイズ+外れ値(真値が既知) ===============
    true_surf, _, _ = cylinder_surface()
    n_surf = true_surf.shape[0]

    # (a) 半径方向のセンサノイズを面に乗せる(軸ずれの真値ノイズ)。
    rad_noise = rng.normal(0.0, 0.03, size=n_surf)
    d = np.hypot(true_surf[:, 0], true_surf[:, 1])          # = R
    scale = (d + rad_noise) / d                             # 半径を R±noise にゆらす
    noisy_surf = true_surf.copy()
    noisy_surf[:, 0] *= scale
    noisy_surf[:, 1] *= scale

    # (b) 飛び点(外れ値): 軸から半径 3〜5 の遠方に散らす(全点が明確に「面の外」)。
    n_out = 40
    ang = rng.uniform(0.0, 2.0 * np.pi, n_out)
    rr = rng.uniform(3.0, 5.0, n_out)
    outliers = np.stack([rr * np.cos(ang), rr * np.sin(ang),
                         rng.uniform(-1.0, H + 1.0, n_out)], axis=1)

    cloud = np.vstack([noisy_surf, outliers])              # (n_surf + n_out, 3)
    is_outlier = np.zeros(cloud.shape[0], dtype=bool)
    is_outlier[n_surf:] = True                             # 真値ラベル(どれが飛び点か)

    # === 2) op: statistical_outlier_removal(統計的外れ値除去) =====================
    _, keep_sor = F.statistical_outlier_removal(cloud, k=16, std_ratio=2.0)
    sor_out_removed = int((~keep_sor[is_outlier]).sum())   # 落とせた飛び点
    sor_in_removed = int((~keep_sor[~is_outlier]).sum())   # 誤って落とした面の点
    print(f"点群: 面 {n_surf} + 飛び点 {n_out}")
    print(f"SOR   飛び点除去 {sor_out_removed}/{n_out}  面の誤除去 {sor_in_removed}/{n_surf}")
    assert sor_out_removed == n_out, "SOR が飛び点を取りこぼした"
    assert sor_in_removed == 0, "SOR が面の点を誤除去した"

    # === 3) op: radius_outlier_removal(孤立点除去) — SOR の後段に鎖で繋ぐ ==========
    c1, _ = F.statistical_outlier_removal(cloud, k=16, std_ratio=2.0)
    c2, keep_rad = F.radius_outlier_removal(c1, radius=0.25, min_neighbors=4)
    print(f"radius 合成後の点数 {c2.shape[0]}  (面のみ={n_surf} が理想)")
    # SOR で飛び点は既に消えているので、radius は面の点を1つも落とさない。
    assert int((~keep_rad).sum()) == 0, "radius が面の点を誤除去した"
    assert c2.shape[0] == n_surf, "SOR→radius 合成後に面の点だけが残っていない"

    # 直接 radius 単独でも飛び点を全除去できることを確認(op 単体の GT)。
    _, keep_rad_only = F.radius_outlier_removal(cloud, radius=0.25, min_neighbors=4)
    assert int((~keep_rad_only[is_outlier]).sum()) == n_out, "radius 単独で飛び点を除去できない"
    assert int((~keep_rad_only[~is_outlier]).sum()) == 0, "radius 単独で面の点を誤除去"

    # === 4) op: mls_smooth(局所曲面へ射影してノイズ除去) ==========================
    rms_before = axis_radial_rms(c2)                       # 平滑前の軸ずれ(=null: 何もしない)
    smoothed = F.mls_smooth(c2, radius=0.30, order=2)
    rms_after = axis_radial_rms(smoothed)
    print(f"MLS   軸ずれRMS  平滑前 {rms_before:.4f} -> 平滑後 {rms_after:.4f}")
    assert rms_after < rms_before, "MLS がノイズを減らせていない(null に負けた)"
    assert rms_after < 0.6 * rms_before, f"MLS の低減が弱い: {rms_after:.4f} vs {rms_before:.4f}"

    # === 5) op: knn_graph(掃除後の点群の近傍グラフ) ==============================
    k = 8
    idx, dist = G.knn_graph(smoothed, k=k)
    assert idx.shape == (n_surf, k) and dist.shape == (n_surf, k), "knn_graph の形が不正"
    # (i) 距離は各行で昇順(最近傍が先頭)。
    assert np.all(np.diff(dist, axis=1) >= -1e-9), "knn_graph の距離が昇順でない"
    # (ii) 返る距離が index から再計算した Euclid 距離と一致(内部整合)。
    recomputed = np.linalg.norm(smoothed[:, None, :] - smoothed[idx], axis=2)
    assert np.allclose(recomputed, dist, atol=1e-9), "knn_graph の距離が index と不整合"

    # (iii) GT: 返る近傍が総当たり kNN と厳密一致(数点で確認)。
    def brute_knn(P, i, kk):
        dd = np.linalg.norm(P - P[i], axis=1)
        dd[i] = np.inf
        return set(np.argsort(dd)[:kk].tolist())

    for i in (0, 137, 900, 1500, n_surf - 1):
        assert set(idx[i].tolist()) == brute_knn(smoothed, i, k), f"knn_graph が点 {i} で総当たりと不一致"

    # beat-null: kNN 近傍平均距離は「ランダムな点対」より桁違いに近い。
    mean_knn = float(dist.mean())
    ra = rng.integers(0, n_surf, 5000)
    rb = rng.integers(0, n_surf, 5000)
    mean_rand = float(np.linalg.norm(smoothed[ra] - smoothed[rb], axis=1).mean())
    print(f"knn   近傍平均距離 {mean_knn:.4f}  << ランダム点対 {mean_rand:.4f}(null)")
    assert mean_knn < 0.25 * mean_rand, "kNN 近傍がランダム点対に対して近くない"

    # === 6) op: geodesic_mesh(円柱メッシュ上の測地距離 vs 展開の真値) ==============
    verts, faces, tv, zv = cylinder_mesh()
    source = 0                                             # (iz=0, it=0) の頂点
    geo = G.geodesic_mesh(verts, faces, source)
    assert np.all(np.isfinite(geo)), "測地距離に不達(inf)がある: メッシュが分断"

    # 展開の真値: 円柱は可展面。測地 = sqrt((R·Δθ_short)² + Δz²)。Δθ_short は短い方の周回。
    nt, nz = tv.size, zv.size
    sth, sz = tv[0], zv[0]
    dth = np.array([min(abs(tv[it] - sth), 2 * np.pi - abs(tv[it] - sth))
                    for iz in range(nz) for it in range(nt)])
    dz = np.array([abs(zv[iz] - sz) for iz in range(nz) for it in range(nt)])
    analytic = np.hypot(R * dth, dz)                       # 測地距離の真値
    chord = np.linalg.norm(verts - verts[source], axis=1)  # 直線(弦)= 素朴案

    # 弦 <= 弧: 表面をなぞる測地はどの頂点でも直線以上(可展面でも必ず成り立つ)。
    assert np.all(geo + 1e-9 >= chord), "測地距離が弦より短い点がある(弦<=弧に反する)"

    # 代表ペア = 真値が最大の点(反対側・上端)。ここで測地は真値と一致、弦は大きく過小評価。
    tgt = int(np.argmax(analytic))
    rel_geo = abs(geo[tgt] - analytic[tgt]) / analytic[tgt]
    rel_chord = abs(chord[tgt] - analytic[tgt]) / analytic[tgt]
    print(f"測地  代表ペア {source}->{tgt}: 真値 {analytic[tgt]:.4f} / 測地 {geo[tgt]:.4f}"
          f"(誤差 {rel_geo*100:.2f}%) / 弦 {chord[tgt]:.4f}(誤差 {rel_chord*100:.1f}%)")
    assert rel_geo < 0.03, f"測地距離が展開真値と乖離: {rel_geo*100:.2f}%"
    assert rel_chord > 0.15, f"この代表ペアで弦の過小評価が弱い(主張が崩れる): {rel_chord*100:.1f}%"

    # beat-null(全体): 角度が離れた点(弦が缶を貫通する)で、測地の平均相対誤差 < 弦の平均相対誤差。
    far = dth > 2.0                                        # 角度差 > ~114°
    mrel_geo = float(np.mean(np.abs(geo[far] - analytic[far]) / analytic[far]))
    mrel_chord = float(np.mean(np.abs(chord[far] - analytic[far]) / analytic[far]))
    print(f"測地  角度遠方 平均相対誤差  本手法 {mrel_geo*100:.1f}%  <  弦(null) {mrel_chord*100:.1f}%")
    assert mrel_geo < mrel_chord - 0.03, "測地が弦nullを明確に上回れていない"
    assert np.mean(chord[far] - analytic[far]) < 0, "弦が系統的に過小評価になっていない"

    # === 7) op: distance_ridge(中身入り円柱の medial = 中心軸) ====================
    # 同じ円柱を「中身の詰まった voxel」で表す。scale = 1ワールド単位あたりの voxel 数。
    D = 41
    c = D // 2
    vox_per_unit = 14.0
    r_vox = R * vox_per_unit                              # 半径を voxel 換算(=14)
    _, yy, xx = np.mgrid[0:D, 0:D, 0:D]
    solid = np.hypot(yy - c, xx - c) <= r_vox            # z 軸に沿った中身入り円柱

    ridge_mask, edt = M.distance_ridge(solid, min_radius=0.0)
    assert ridge_mask.any(), "distance_ridge が medial を1つも返さない"

    # GT(1): 中身入り円柱の medial は中心軸。尾根 voxel はすべて軸上(x=c, y=c)。
    ridge_ijk = np.argwhere(ridge_mask)
    ridge_radial = np.hypot(ridge_ijk[:, 1] - c, ridge_ijk[:, 2] - c)
    mean_ridge_radial = float(ridge_radial.mean())
    # GT(2): 最大 EDT(=中心の内接半径)は円柱半径に一致。voxel 換算を戻すと ≈ R。
    max_edt = float(edt.max())
    recovered_R = max_edt / vox_per_unit
    print(f"ridge medial voxel {int(ridge_mask.sum())} 個  軸からの平均距離 {mean_ridge_radial:.3f} voxel")
    print(f"ridge 最大EDT {max_edt:.3f} voxel -> 復元半径 {recovered_R:.4f}(真値 R={R})")
    assert mean_ridge_radial < 0.5, f"medial が中心軸に乗っていない: 平均 {mean_ridge_radial:.3f} voxel"
    assert abs(recovered_R - R) < 0.05, f"復元半径が円柱半径とずれ: {recovered_R:.4f} vs {R}"

    # beat-null: 尾根は軸に集中。前景 voxel 全体の平均半径(下記)とは桁違い=medial 抽出が効いている。
    fg_ijk = np.argwhere(solid)
    fg_radial = float(np.hypot(fg_ijk[:, 1] - c, fg_ijk[:, 2] - c).mean())
    print(f"ridge 平均半径 {mean_ridge_radial:.3f} << 前景全体の平均半径 {fg_radial:.3f}(null)")
    assert mean_ridge_radial < 0.2 * fg_radial, "medial が前景全体より軸へ集中していない"

    print(
        f"PASS: SOR/radius が飛び点 {n_out}/{n_out} を除去し面の点 {n_surf} を保持、"
        f"MLS が軸ずれRMS {rms_before:.3f}->{rms_after:.3f} に低減、"
        f"knn_graph は総当たりkNNと厳密一致(近傍 {mean_knn:.3f}<<ランダム {mean_rand:.3f})、"
        f"geodesic_mesh は展開真値と一致(代表誤差 {rel_geo*100:.1f}%)で弦null(誤差 {rel_chord*100:.0f}%)を圧倒、"
        f"distance_ridge は中心軸を復元し半径 {recovered_R:.3f}≈R={R}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
