# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""shapestat_landmark_tour — 形態統計(shapestats)の全 op を、真値つきの合成ランドマーク群で一巡する。

    py -3.11 examples/shapestat_landmark_tour.py

【この例が示すこと】
設計 CAD の無い形(骨・歯・生体・同型部品)を「群集平均との差」「左右対称性」
「成長の軸」で語る層の使い方。合成 → Procrustes → GPA/平均形状 → 形態 PCA →
左右非対称 → 面までの符号つき距離、の順に、**答えを自分で埋めた**データで検算する。

【グラウンドトゥルース(すべて assert で落とす)】
1. 既知の相似変換(回転 40 度・拡大 1.7・平行移動)を ``procrustes_fit`` が 1e-9 で復元し、
   ``procrustes_align`` が点を 1e-9 で重ね、``procrustes_distance`` が 0 になる。
2. ``shape_perturb`` の 4 種で「Procrustes が消す変形/消せない変形」を分ける:
   shift → 0、scale → ``scaling=True`` で 0 / ``scaling=False`` で閉形式 ``a/(1+a)``、
   bulge → 消えない。鏡映は ``reflection=False`` では消えず ``True`` では消える。
3. 個体ごとにばらばらの相似変換を掛けた群を ``generalized_procrustes`` が揃え、
   ``shape_mean`` が元の群の平均形状と Procrustes 距離 1e-6 以下で一致する
   (揃えずに取った生の平均は縮む —— 大きさの比を印字)。
4. 雑音ゼロ・2 モードの合成群(``shape_synth_family``)は ``align=False`` の
   ``shape_pca`` で寄与率 2 本の和が 1(1e-9)、投影→再構成の往復が 1e-9。
   分散比は真値 6.25 の標本ゆらぎ内(K=300)。``align=True`` は大きさを消すので
   比が変わる(印字して見せる。間違いではなく定義の帰結)。
5. ``shape_synthesize(sigmas=[2,-1])`` の再構成はスコア閉形式と一致し、その
   ``shape_mahalanobis``(2 本)は sqrt(5) に一致。モデル外の膨らみは
   Mahalanobis では見えにくいが**再構成残差**では群内の 100 倍以上離れる
   (honest: どちらを使うかで見える異常が違う)。
6. 既知の正中面で鏡映した左右ランドマークから ``mirror_plane_from_pairs`` が面を
   1e-9 で復元し、``landmark_asymmetry`` は 0。右 1 点を法線方向に 0.3 動かすと
   真の面で測れば 0.3 ちょうど、面を再当てはめすると少し縮む(印字)。
7. 球面標本を法線方向に ±0.2 動かした問い合わせ点の ``signed_surface_distance`` が
   ±0.2 ちょうど(法線を与えた場合)。法線を省いた推定でも符号が一致する。

【読み方】各節の印字は「真値 / 実測 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shapestats as S        # noqa: E402  形態統計の層(この例の主役)


def _rotation(axis, deg):
    """軸まわり回転行列(Rodrigues)。検算用の既知変換を作る。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1.0 - np.cos(th)) * (K @ K)


def _fibonacci_sphere(n):
    """単位球面上の準一様な点(決定的)。"""
    i = np.arange(n, dtype=float) + 0.5
    z = 1.0 - 2.0 * i / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = np.pi * (3.0 - np.sqrt(5.0)) * i
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


def section_procrustes(family):
    """1-2. 単体の Procrustes: 既知の相似変換の復元と、消える/消えない変形の区別。"""
    s = family[0]                                       # 個体 1 つ(N,3)
    # ★EXTEND: 自分のランドマーク (N,3) を s に入れる(点の並びが対応していること)
    R, scale, t = _rotation((1.0, 2.0, 3.0), 40.0), 1.7, np.array([3.0, -2.0, 5.0])
    moved = scale * (s @ R.T) + t                       # 真値: moved = 1.7 R s + t

    M = S.procrustes_fit(s, moved)                      # (4,4) 同次行列
    err_R = float(np.abs(M[:3, :3] - scale * R).max())
    err_t = float(np.abs(M[:3, 3] - t).max())
    aligned = S.procrustes_align(s, moved)              # 点を重ねる
    err_pts = float(np.abs(aligned - moved).max())
    d0 = S.procrustes_distance(s, moved)                # 無次元距離(0 のはず)
    print(f"1) 相似変換の復元: |sR - 真| {err_R:.1e} / |t - 真| {err_t:.1e} / "
          f"重ねた点の最大差 {err_pts:.1e} / Procrustes 距離 {d0:.1e}")
    assert err_R < 1e-9 and err_t < 1e-9 and err_pts < 1e-9 and d0 < 1e-12

    # 4 種の摂動 —— 「消える変形」と「消えない変形」
    a = 0.3
    d_shift = S.procrustes_distance(s, S.shape_perturb(s, a, mode="shift"))
    scaled = S.shape_perturb(s, a, mode="scale")
    d_scale_on = S.procrustes_distance(s, scaled, scaling=True)
    d_scale_off = S.procrustes_distance(s, scaled, scaling=False)
    want_scale_off = a / (1.0 + a)                      # 閉形式(docstring 参照)
    bulged = S.shape_perturb(s, 0.2, mode="bulge", center=(1.0, 0.0, 0.0), sigma=0.4)
    d_bulge = S.procrustes_distance(s, bulged)
    d_noise = S.procrustes_distance(s, S.shape_perturb(s, 0.02, mode="noise", seed=1))
    print(f"2) 摂動: shift→{d_shift:.1e}(消える) / scale→scaling=True {d_scale_on:.1e}(消える), "
          f"scaling=False {d_scale_off:.6f}(閉形式 a/(1+a)={want_scale_off:.6f}) / "
          f"bulge→{d_bulge:.4f}(消えない) / noise 床→{d_noise:.4f}")
    assert d_shift < 1e-12 and d_scale_on < 1e-12
    assert abs(d_scale_off - want_scale_off) < 1e-9
    assert d_bulge > 0.01 and d_noise > 0.0

    # 鏡映: 既定では消さない(左右非対称性が消えるから)
    mirrored = s * np.array([-1.0, 1.0, 1.0])
    d_refl_no = S.procrustes_distance(s, mirrored, reflection=False)
    d_refl_yes = S.procrustes_distance(s, mirrored, reflection=True)
    print(f"   鏡映: reflection=False → {d_refl_no:.4f}(残る) / reflection=True → {d_refl_yes:.1e}(消える)")
    assert d_refl_no > 0.05 and d_refl_yes < 1e-12
    return {"fit_err": max(err_R, err_t), "scale_off": d_scale_off, "scale_off_want": want_scale_off,
            "bulge": d_bulge, "reflection_kept": d_refl_no}


def section_gpa(family):
    """3. GPA と平均形状: ばらばらに置かれた群を共通の枠へ戻す。"""
    K = 12
    clean = family[:K]
    rng = np.random.default_rng(3)
    scrambled = np.empty_like(clean)
    for i in range(K):                                  # 個体ごとに別の相似変換
        R = _rotation(rng.normal(size=3), rng.uniform(-170, 170))
        sc = rng.uniform(0.5, 2.5)
        t = rng.uniform(-20, 20, size=3)
        scrambled[i] = sc * (clean[i] @ R.T) + t
    # ★EXTEND: 自分の群 (K,N,3) を scrambled に入れる(位置・向き・大きさがばらばらでよい)

    gpa = S.generalized_procrustes(scrambled)           # (K,N,3) 共通の枠
    form_err = max(S.procrustes_distance(gpa[i], clean[i]) for i in range(K))   # 形は保たれる
    mean_gpa = S.shape_mean(scrambled)                  # GPA 後の平均
    mean_clean = S.shape_mean(clean)                    # 元の群の平均
    d_mean = S.procrustes_distance(mean_gpa, mean_clean)
    raw_mean = scrambled.mean(0)                        # ★悪い例: 揃えずに平均
    size = lambda p: float(np.sqrt(np.mean(np.sum((p - p.mean(0)) ** 2, axis=1))))  # noqa: E731
    d_raw = S.procrustes_distance(raw_mean, mean_clean)
    spread_before = float(np.mean([np.sqrt(np.mean(np.sum((scrambled[i] - raw_mean) ** 2, 1)))
                                   for i in range(K)]))
    spread_after = float(np.mean([np.sqrt(np.mean(np.sum((gpa[i] - gpa.mean(0)) ** 2, 1)))
                                  for i in range(K)]))
    print(f"3) GPA: 各個体の形は保たれる(最大 Procrustes 距離 {form_err:.1e})、"
          f"平均形状は元の群と一致(距離 {d_mean:.1e})")
    print(f"   生の平均は駄目: 元の平均との距離 {d_raw:.3f}、平均まわりの散らばり "
          f"{spread_before:.2f} → GPA 後 {spread_after:.4f}")
    assert form_err < 1e-9 and d_mean < 1e-6
    assert d_raw > 10 * d_mean and spread_after < spread_before
    return {"gpa_form_err": form_err, "mean_dist": d_mean, "raw_mean_dist": d_raw,
            "raw_mean_size_ratio": size(raw_mean) / size(mean_clean)}


def section_pca(family):
    """4-5. 統計形状モデル: 分散比・往復・Mahalanobis・合成。"""
    model = S.shape_pca(family, align=False)            # 大きさを形質に数える(伸びモードがあるので)
    ev = S.shape_explained_variance(model)
    ratio = float(model["variance"][0] / model["variance"][1])
    model_al = S.shape_pca(family)                      # 既定 align=True(大きさを消す)
    ratio_al = float(model_al["variance"][0] / model_al["variance"][1])
    print(f"4) 形態 PCA(K={family.shape[0]}): 寄与率 {ev[0]:.4f} / {ev[1]:.4f}、上位 2 本の和 "
          f"{ev[:2].sum():.12f}(雑音ゼロ・2 モードなので 1)、分散比 {ratio:.3f}"
          f"(真値 6.25 = 0.30^2/0.12^2、K=300 の標本ゆらぎ内)")
    print(f"   align=True だと分散比 {ratio_al:.3f}(伸びは拡大と似ているので Procrustes の"
          f"スケール除去に食われる。定義の帰結)")
    assert abs(float(ev.sum()) - 1.0) < 1e-12
    assert float(ev[:2].sum()) > 1.0 - 1e-9
    assert 4.5 < ratio < 8.5

    # 投影 → 再構成の往復(2 本で完全に戻る)
    x = family[5]
    z = S.shape_project(model, x, align=False)
    rec = S.shape_reconstruct(model, z[:2])
    rt_err = float(np.abs(rec - x).max())
    # Mahalanobis の閉形式: sqrt(z1^2/v1 + z2^2/v2)
    v = model["variance"]
    mh = S.shape_mahalanobis(model, x, align=False, n_modes=2)
    mh_want = float(np.sqrt(z[0] ** 2 / v[0] + z[1] ** 2 / v[1]))
    print(f"   往復 |再構成 - 元| {rt_err:.1e} / Mahalanobis(2 本) {mh:.4f} = 閉形式 {mh_want:.4f}")
    assert rt_err < 1e-9 and abs(mh - mh_want) < 1e-9

    # 合成: sigmas=[2,-1] → スコア [2 sqrt v1, -sqrt v2] → Mahalanobis sqrt(5)
    syn = S.shape_synthesize(model, sigmas=[2.0, -1.0])
    syn_want = S.shape_reconstruct(model, [2.0 * np.sqrt(v[0]), -1.0 * np.sqrt(v[1])])
    syn_err = float(np.abs(syn - syn_want).max())
    mh_syn = S.shape_mahalanobis(model, syn, align=False, n_modes=2)
    syn_rand = S.shape_synthesize(model, n_modes=2, seed=11)     # 既定は ±3σ に切る
    z_rand = S.shape_project(model, syn_rand, align=False)[:2] / np.sqrt(v[:2])
    print(f"5) 合成: sigmas=[2,-1] の形は閉形式と一致(差 {syn_err:.1e})、"
          f"Mahalanobis {mh_syn:.9f}(真値 sqrt5={np.sqrt(5):.9f})、乱数合成のσ倍 {np.round(z_rand, 3)}(|.|<=3)")
    assert syn_err < 1e-12 and abs(mh_syn - np.sqrt(5.0)) < 1e-9
    assert float(np.abs(z_rand).max()) <= 3.0 + 1e-9

    # モデル外の異常(膨らみ): Mahalanobis では見えにくい、再構成残差では見える
    outlier = S.shape_perturb(family[3], 0.5, mode="bulge")
    resid = lambda p: float(np.sqrt(np.mean(np.sum(   # noqa: E731
        (p - S.shape_reconstruct(model, S.shape_project(model, p, align=False)[:2])) ** 2, 1))))
    in_resid = max(resid(family[i]) for i in range(30))
    out_resid = resid(outlier)
    in_mh = max(S.shape_mahalanobis(model, family[i], align=False) for i in range(30))
    out_mh = S.shape_mahalanobis(model, outlier, align=False)
    print(f"   モデル外の膨らみ 0.5: Mahalanobis(累積 0.99 で選んだ本数) 群内最大 {in_mh:.3f} vs 外れ {out_mh:.3f}"
          f" —— 頼りにならないことがある / 再構成残差 群内最大 {in_resid:.1e} vs 外れ {out_resid:.4f}(桁違い)")
    assert out_resid > 100.0 * max(in_resid, 1e-12)
    return {"explained_top2": float(ev[:2].sum()), "variance_ratio": ratio,
            "variance_ratio_aligned": ratio_al, "roundtrip_err": rt_err,
            "mahalanobis_synth": mh_syn, "outlier_residual": out_resid, "outlier_mahalanobis": out_mh,
            "ingroup_mahalanobis_max": in_mh}


def section_symmetry():
    """6. 左右対称性: 既知の正中面で作った対から面を戻し、非対称量を測る。"""
    rng = np.random.default_rng(5)
    n_true = np.array([1.0, 0.3, -0.2])
    n_true /= np.linalg.norm(n_true)
    c_true = np.array([0.5, -0.2, 0.1])                 # 正中面: 点 c_true、法線 n_true
    M = 10
    left = rng.uniform(-3, 3, size=(M, 3))
    sd = (left - c_true) @ n_true
    left = left - (sd + 1.0 + np.abs(sd))[:, None] * n_true   # 全部を面の負側へ(距離 >= 1)
    reflect = lambda p: p - 2.0 * ((p - c_true) @ n_true)[:, None] * n_true   # noqa: E731
    right = reflect(left)
    lm = np.vstack([left, right])                       # 前半=左、後半=右(既定の対規約)
    # ★EXTEND: 自分のランドマークを「左を全部、次に右を同じ順で」並べて lm に入れる

    plane = S.mirror_plane_from_pairs(lm)               # (2,3): 点と法線
    off = abs(float((plane[0] - c_true) @ n_true))      # 面上の点か
    cosang = float(plane[1] @ n_true)                   # 法線の向きは左→右で +1
    asym0 = S.landmark_asymmetry(lm)
    print(f"6) 正中面の復元: 点の面からのずれ {off:.1e}、法線の cos {cosang:.12f}(+1)、"
          f"対称な対の非対称量 最大 {float(np.abs(asym0).max()):.1e}")
    assert off < 1e-9 and abs(cosang - 1.0) < 1e-9 and float(np.abs(asym0).max()) < 1e-9

    # 右の 1 点を法線方向へ delta 動かす(真値: その対だけ +delta)
    delta, j = 0.3, 4
    lm2 = lm.copy()
    lm2[M + j] += delta * n_true
    true_plane = np.vstack([c_true, n_true])
    a_true = S.landmark_asymmetry(lm2, plane=true_plane)
    a_fit = S.landmark_asymmetry(lm2)                   # 面も同じ対から再当てはめ
    others = np.delete(np.arange(M), j)
    print(f"   右 {j} 番を +{delta} 張り出し: 真の面で測ると {a_true[j]:.9f}(他の対 最大 "
          f"{float(np.abs(a_true[others]).max()):.1e})、面を再当てはめすると {a_fit[j]:.4f}"
          f"(中点が delta/2 ずれるぶん縮む: 利得 {a_fit[j] / delta:.3f})")
    assert abs(a_true[j] - delta) < 1e-9 and float(np.abs(a_true[others]).max()) < 1e-9
    assert abs(a_fit[j] - delta) < 0.25 * delta and a_fit[j] > 0.0

    # midline(対にならない正中線上の点)を足しても面は変わらない
    mid_pts = c_true + np.array([[0.0, 1.0, 1.5], [0.0, -2.0, -3.0]]) @ np.eye(3)
    mid_pts = mid_pts - ((mid_pts - c_true) @ n_true)[:, None] * n_true   # 厳密に面上へ
    lm3 = np.vstack([lm, mid_pts])
    pairs = np.column_stack([np.arange(M), np.arange(M, 2 * M)])
    plane3 = S.mirror_plane_from_pairs(lm3, pairs=pairs, midline=[2 * M, 2 * M + 1])
    off3 = abs(float((plane3[0] - c_true) @ n_true))
    assert off3 < 1e-9 and abs(float(plane3[1] @ n_true) - 1.0) < 1e-9
    # 奇数個は拒否(黙って切り詰めると対がずれる)
    try:
        S.mirror_plane_from_pairs(lm[:-1])
        odd_rejected = False
    except ValueError:
        odd_rejected = True
    print(f"   midline 2 点を足しても面は同じ(ずれ {off3:.1e})、奇数個の入力は拒否: {odd_rejected}")
    assert odd_rejected
    return {"plane_offset": off, "plane_cos": cosang, "asym_true_plane": float(a_true[j]),
            "asym_refit_plane": float(a_fit[j]), "delta": delta}


def section_surface_distance():
    """7. 面までの符号つき距離: 球面標本を法線方向に ±0.2 ずらした点。"""
    surf = _fibonacci_sphere(3000)                      # 単位球面(法線 = 位置)
    normals = surf.copy()
    # ★EXTEND: surf を自分の面の点(メッシュ頂点・点群)、normals をその向き付き法線にする
    idx = np.arange(0, 3000, 60)                        # 50 点を選ぶ
    q = np.vstack([1.2 * surf[idx], 0.8 * surf[idx]])   # 外に 0.2 / 内に 0.2
    want = np.concatenate([np.full(idx.size, 0.2), np.full(idx.size, -0.2)])
    d1 = S.signed_surface_distance(q, surf, normals)            # k=1
    d3 = S.signed_surface_distance(q, surf, normals, k=3)       # 符号を 3 近傍で決める
    e1, e3 = float(np.abs(d1 - want).max()), float(np.abs(d3 - want).max())
    d_est = S.signed_surface_distance(q, surf)                  # 法線を省く(推定)
    agree = float(np.mean(np.sign(d_est) == np.sign(want)))
    print(f"7) 符号つき面距離: 真値 ±0.2 との最大差 k=1 {e1:.1e} / k=3 {e3:.1e}、"
          f"法線を推定させた場合の符号一致率 {agree:.3f}、|距離| の最大差 "
          f"{float(np.abs(np.abs(d_est) - 0.2).max()):.1e}")
    assert e1 < 1e-12 and e3 < 1e-12
    assert agree >= 0.95
    return {"signed_dist_err_k1": e1, "signed_dist_err_k3": e3, "estimated_normal_sign_agree": agree}


def run() -> dict:
    """全 7 節を回し、真値との照合結果を返す(失敗は assert で落ちる)。"""
    t0 = time.perf_counter()
    # 既知の 2 変形モード(伸び 0.30 / 曲げ 0.12)を持つ群(300 個体 x 64 点、雑音ゼロ)
    family = S.shape_synth_family(n_shapes=300, n_points=64, n_modes=2,
                                  mode_scale=(0.30, 0.12), noise=0.0, seed=7)
    # ★EXTEND: 自分の群 (K,N,3) に差し替える(点の並びが個体間で対応していること)
    out = {"family_shape": tuple(family.shape)}
    out.update(section_procrustes(family))
    out.update(section_gpa(family))
    out.update(section_pca(family))
    out.update(section_symmetry())
    out.update(section_surface_distance())
    out["elapsed_s"] = time.perf_counter() - t0
    return out


def main():
    r = run()
    print(f"\nPASS: shapestats 16 op を真値つきで一巡(相似変換の復元 1e-9、GPA 平均の一致、"
          f"PCA 往復 1e-9、Mahalanobis 閉形式、正中面 1e-9、面距離 ±0.2 厳密)。"
          f" 実行 {r['elapsed_s']:.2f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
