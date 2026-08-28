# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: ノイズの乗った球メッシュを平滑化する (Laplacian / Taubin mesh smoothing).

実世界の問題:
    marching cubes(CT/ボクセル → 三角形メッシュ)やスキャン由来のメッシュは、頂点位置に
    高周波ノイズ(ボクセルの階段状アーティファクト・計測揺らぎ)が乗る。見た目もザラつき、
    法線・曲率も暴れる。頂点の接続(faces)を使って隣接頂点へ寄せる **メッシュ平滑化** で
    高周波成分だけを落としたい。

原理と 2 手法:
    - laplacian_smooth: 各頂点を隣接平均へ ``lam`` だけ寄せる素朴な Laplacian。ノイズは確実に
      減るが、閉曲面では平均曲率流と同じく **内側へ収縮(shrinkage)** する(球が縮む)。
    - taubin_smooth: 正の ``lam`` で寄せた直後に負の ``mu``(``|mu|>lam``)で押し戻す 2 段を
      交互に掛ける帯域通過フィルタ(Taubin 1995)。低周波(全体形状=球)を保ったまま高周波
      ノイズだけを落とすので **収縮しない**(球の平均半径が保たれる)。

グラウンドトゥルース(数値で嘘を弾く):
    原点(格子中心)からの距離が既知半径 R の球メッシュを voxel 球 → marching cubes で作る。
    その clean メッシュの頂点平均半径を GT 参照半径 R0 とする(離散化した実際の球面の半径)。
    頂点に等方ガウスノイズを載せてから平滑化し、
      1) 各頂点の「対 R0 半径 RMS 誤差」が **無平滑化より減る**(=ノイズを実際に落とす)。
      2) **収縮の有無**: Laplacian は平均半径が R0 から有意に縮む(収縮アーティファクト)一方、
         Taubin は平均半径 ≈ R0 を保つ(収縮しない)。
    を数値でアサートする。半径は幾何だけで決まる GT なので当てずっぽうを弾ける。

beat-the-null(下駄を履かせない基準):
    - null #1(無平滑化)= ノイズ球そのもの。RMS 誤差は高い。両手法がこれを明確に下回る。
    - null #2(収縮の判別)= Taubin の平均半径ズレ < Laplacian の平均半径ズレ。素朴な Laplacian は
      「縮めることで滑らかに見せる」ので、収縮しない Taubin と半径保持で判別できる。
    さらに退化・不正入力(空 faces・範囲外インデックス・iters<1・lam=0)は fail-closed で
    例外になることを確認する(自明入力で偽の成功を出さない)。

描画: ノイズ球(before)/ Laplacian 後(収縮)/ Taubin 後(非収縮)を同一軸スケールの trisurf で
      並置し examples_3d/_gallery/mesh_smooth.png に保存(matplotlib が無ければスキップ)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import match3d  # noqa: E402  (voxel_to_mesh; sys.path 調整後に import)
from mesh_smooth import laplacian_smooth, taubin_smooth  # noqa: E402


def build_sphere_mesh(size: int = 48, radius: float = 16.0):
    """voxel 球 → marching cubes で球メッシュを作り (verts, faces, center, R0) を返す。

    center は格子中心。R0 は clean メッシュ頂点の平均半径(= 離散化した球面の実半径)で、
    これを GT 参照半径にする(iso=0.5 面は解析半径から僅かに外れるため、mesh 自身の半径を
    真値にするのが honest)。
    """
    c = (size - 1) / 2.0
    z, y, x = np.mgrid[0:size, 0:size, 0:size]
    vol = ((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2 <= radius * radius).astype(np.float64)
    verts, faces, _ = match3d.voxel_to_mesh(vol, iso=0.5)
    center = np.array([c, c, c], dtype=np.float64)
    r0 = float(np.linalg.norm(verts - center, axis=1).mean())
    return verts.astype(np.float64), faces.astype(np.int64), center, r0


def radius_stats(verts: np.ndarray, center: np.ndarray, r0: float):
    """(RMS(対 R0 半径誤差), |平均半径 - R0|, 平均半径) を返す。"""
    r = np.linalg.norm(verts - center, axis=1)
    rms = float(np.sqrt(np.mean((r - r0) ** 2)))
    mean_r = float(r.mean())
    return rms, abs(mean_r - r0), mean_r


def save_png(verts_list, faces, titles, path: Path) -> bool:
    """noisy / Laplacian / Taubin の trisurf を同一軸スケールで並置保存。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: F401
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except Exception:
        return False

    allv = np.concatenate(verts_list, axis=0)
    ctr = allv.mean(0)
    rad = float(np.abs(allv - ctr).max()) * 1.02
    lims = [(ctr[k] - rad, ctr[k] + rad) for k in range(3)]

    fig = plt.figure(figsize=(15, 5.2))
    for i, (V, title) in enumerate(zip(verts_list, titles)):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        ax.plot_trisurf(V[:, 0], V[:, 1], V[:, 2], triangles=faces,
                        cmap="viridis", linewidth=0.0, antialiased=True,
                        edgecolor="none", alpha=0.95)
        ax.set_title(title, fontsize=12)
        ax.set_xlim(lims[0]); ax.set_ylim(lims[1]); ax.set_zlim(lims[2])
        ax.set_box_aspect((1, 1, 1))
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        ax.view_init(elev=18, azim=35)
    fig.suptitle("Mesh smoothing: Laplacian shrinks, Taubin preserves radius",
                 fontsize=13)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=95, bbox_inches="tight")
    plt.close(fig)
    return True


def expect_valueerror(fn, *args, **kwargs) -> bool:
    """fn(*args) が ValueError を上げれば True(fail-closed の確認用)。"""
    try:
        fn(*args, **kwargs)
    except ValueError:
        return True
    return False


def main() -> int:
    # --- GT: clean な球メッシュと参照半径 R0 ---
    verts, faces, center, r0 = build_sphere_mesh(size=48, radius=16.0)
    if verts.ndim != 2 or verts.shape[1] != 3:
        raise ValueError(f"verts must be (N,3), got {verts.shape}")
    if len(verts) < 100 or len(faces) < 100:
        raise ValueError("球メッシュが小さすぎます(退化入力の疑い)")

    # --- ノイズ球(null #1): 等方ガウスノイズを頂点に載せる ---
    rng = np.random.default_rng(0)
    noise_sigma = 0.6
    noisy = verts + rng.normal(0.0, noise_sigma, verts.shape)

    # --- 平滑化(同じ iters/lam。Taubin は押し戻し段 mu を足すだけ)---
    lap_verts, lap_faces = laplacian_smooth((noisy, faces), iters=30, lam=0.4)
    tau_verts, tau_faces = taubin_smooth((noisy, faces), iters=40, lam=0.33, mu=-0.34)

    n_rms, n_dev, n_mean = radius_stats(noisy, center, r0)
    l_rms, l_dev, l_mean = radius_stats(lap_verts, center, r0)
    t_rms, t_dev, t_mean = radius_stats(tau_verts, center, r0)

    print(f"[GT] verts={len(verts)}, faces={len(faces)}, 参照半径 R0={r0:.4f}")
    print(f"[null] ノイズ球       : RMS={n_rms:.4f}, 平均半径ズレ={n_dev:.4f} (mean r={n_mean:.4f})")
    print(f"[Laplacian] it=30 λ=0.4: RMS={l_rms:.4f}, 平均半径ズレ={l_dev:.4f} (mean r={l_mean:.4f})")
    print(f"[Taubin] it=40 λ=.33 μ=-.34: RMS={t_rms:.4f}, 平均半径ズレ={t_dev:.4f} (mean r={t_mean:.4f})")

    # --- 描画 ---
    png = _REPO_ROOT / "examples_3d" / "_gallery" / "mesh_smooth.png"
    drew = save_png(
        [noisy, lap_verts, tau_verts],
        faces,
        [f"noisy sphere\nRMS={n_rms:.3f}",
         f"Laplacian (shrinks)\nRMS={l_rms:.3f}, r-dev={l_dev:.3f}",
         f"Taubin (preserved)\nRMS={t_rms:.3f}, r-dev={t_dev:.3f}"],
        png,
    )
    print(f"[draw] PNG {'saved: ' + str(png) if drew else 'skipped (matplotlib 不在)'}")

    # ============================ GT アサーション ============================
    # faces はトポロジー不変(平滑化は頂点だけ動かす)
    assert np.array_equal(lap_faces, faces), "Laplacian が faces を変更した"
    assert np.array_equal(tau_faces, faces), "Taubin が faces を変更した"
    assert lap_verts.shape == verts.shape and tau_verts.shape == verts.shape, "頂点数が変化した"

    # null #1 が高誤差であること(下駄なしの正当な基準)
    assert n_rms > 0.4, f"ノイズ基準の RMS が低すぎる(ノイズ不足): {n_rms:.4f}"

    # (1) beat-the-null: 両手法とも無平滑化より RMS を明確に下げる(ノイズを実際に落とす)
    assert l_rms < 0.6 * n_rms, f"Laplacian が null を十分下回らない: {l_rms:.4f} vs {n_rms:.4f}"
    assert t_rms < 0.6 * n_rms, f"Taubin が null を十分下回らない: {t_rms:.4f} vs {n_rms:.4f}"

    # (2) 収縮アーティファクト: Laplacian は平均半径が R0 から有意に縮む(内側へ)
    assert l_mean < r0, f"Laplacian が収縮していない(mean r={l_mean:.4f} >= R0={r0:.4f})"
    assert l_dev > 3.0 * n_dev, \
        f"Laplacian の収縮が null 揺らぎと区別できない: {l_dev:.4f} vs {n_dev:.4f}"

    # (3) 非収縮: Taubin は平均半径 ≈ R0 を保ち、収縮ズレは Laplacian の 1/3 未満(判別的に上回る)
    assert t_dev < l_dev, \
        f"Taubin の半径保持が Laplacian を上回らない: {t_dev:.4f} vs {l_dev:.4f}"
    assert t_dev < 0.3 * l_dev, \
        f"Taubin と Laplacian の収縮差が小さい: {t_dev:.4f} vs {l_dev:.4f}"

    # (4) fail-closed: 退化・不正入力は例外(自明入力で偽の成功を出さない)
    bad_faces = faces.copy(); bad_faces[0, 0] = len(verts) + 5   # 範囲外インデックス
    assert expect_valueerror(laplacian_smooth, (verts, bad_faces), iters=5), \
        "範囲外 face インデックスが弾かれない"
    assert expect_valueerror(taubin_smooth, (verts, np.zeros((0, 3), int))), \
        "空 faces が弾かれない"
    assert expect_valueerror(laplacian_smooth, (verts, faces), iters=0), \
        "iters=0(自明入力)が弾かれない"
    assert expect_valueerror(laplacian_smooth, (verts, faces), iters=5, lam=0.0), \
        "lam=0(恒等・自明)が弾かれない"
    assert expect_valueerror(taubin_smooth, (verts, faces), lam=0.33, mu=-0.3), \
        "|mu|<=lam(収縮を打ち消せない)が弾かれない"

    print(
        f"PASS: 両手法とも RMS {n_rms:.3f}(null)→ Laplacian {l_rms:.3f} / Taubin {t_rms:.3f} に低減。"
        f"収縮は Laplacian 平均半径ズレ {l_dev:.3f} に対し Taubin {t_dev:.3f}"
        f"(Taubin は約 {l_dev / max(t_dev, 1e-9):.1f}倍 小さく非収縮)、beat-null 差 RMS "
        f"{n_rms - t_rms:.3f} / 半径保持 {l_dev - t_dev:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
