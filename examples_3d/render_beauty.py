# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 全レンダリング品質層を一発合成する hero レンダラ `render_beauty` で「映える静止 3D」を作る。

実世界の問題:
    3D メッシュを「Qiita 記事に載せて恥ずかしくない 1 枚」にするには、ラスタライズ(depth/法線)
    だけでは足りない。素材感を出す **鏡面ハイライト**、凹部・接触に溜まる **アンビエント
    オクルージョン**、台座に載る **接地影**、エッジのジャギーを消す **スーパーサンプリング**、
    白飛びを救う **トーンマッピング** —— これらを積み重ねて初めて「作品写真」になる。個別 op は
    実装・検証済みなので、`render_beauty` は **合成するだけ**(再発明しない)。

各層が load-bearing(効いている)ことを GT で実測する:
    (a) 決定的      同一入力で 2 回呼び画素完全一致(乱数を使っていない証拠)。
    (b) AO 寄与     凹部(peanut の首)・接触画素の平均輝度が ao=True < ao=False。
                    beat-null: AO を切ると差が消える。
    (c) 鏡面寄与    plastic のハイライト域(高輝度・小面積)が specular=0 相当に無い。
    (d) 接地影      mesh+地面で影マスク面積>0、遮蔽物(mesh)を外すと 0(beat-null)。
                    render_beauty(ground_shadow=True) は地面の影側が明側より暗い。
    (e) トーンマップ reinhard 出力 max<=1 かつ HDR ハイライトの順位を保持(素朴クリップは潰す)。
    (f) SSAA        ss=2 のエッジ edge_alias_energy < ss=1(ジャギーが減る)。
    (g) 形/値域     出力 shape=(size,size,3)・値域[0,1]。

hero 画像:
    複数球の smooth union(sdf_ops + marching cubes)で作った滑らかな有機的彫刻を、良い
    カメラ角・光・金属材質・接地影で 1 枚に焼き、examples_3d/_gallery/render_beauty_hero.png へ保存。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

# examples_3d/render_beauty.py はルートの render_beauty.py と同名なので、ルートを先頭に置いて
# `import render_beauty` がルート側モジュールに解決されるようにする。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import render3d  # noqa: E402
import render_shade  # noqa: E402
import render_shadow  # noqa: E402
import render_ssaa  # noqa: E402
import render_tonemap  # noqa: E402
import render_beauty as rb  # noqa: E402  (ルート側 hero レンダラ)
from sdf_ops import grid_coords, sphere_sdf, sdf_smooth_union  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# メッシュ生成
# ═══════════════════════════════════════════════════════════════════════════
def icosphere(radius: float = 1.0, subdiv: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """原点中心・半径 radius の球メッシュ(icosahedron を subdiv 回細分、外向き巻き)。"""
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    V = np.array([
        (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
        (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ], dtype=np.float64)
    F = np.array([
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
    ], dtype=np.int64)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    for _ in range(subdiv):
        cache: dict[tuple[int, int], int] = {}
        vl = [tuple(v) for v in V]
        nf = []

        def mid(a: int, b: int) -> int:
            key = (a, b) if a < b else (b, a)
            hit = cache.get(key)
            if hit is not None:
                return hit
            m = (np.asarray(vl[a]) + np.asarray(vl[b])) / 2.0
            m /= np.linalg.norm(m)
            vl.append(tuple(m))
            cache[key] = len(vl) - 1
            return cache[key]

        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        V = np.asarray(vl, np.float64)
        F = np.asarray(nf, np.int64)
    return V * float(radius), F


def _orient_outward(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """面法線が大域重心から外向きになるよう、必要なら巻き順を反転する。"""
    center = V.mean(axis=0)
    tri = V[F]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fc = tri.mean(axis=1)
    outward = np.einsum("ij,ij->i", fn, fc - center) > 0.0
    if outward.mean() < 0.5:
        return F[:, [0, 2, 1]]
    return F


def _mc_to_world(V_idx: np.ndarray, vol_shape: tuple[int, int, int],
                 ext) -> np.ndarray:
    """marching_cubes の index 空間頂点を、grid_coords のボクセル中心規約でワールドへ写す。"""
    nx, ny, nz = vol_shape
    lo = np.array([ext[0], ext[2], ext[4]], np.float64)
    span = np.array([ext[1] - ext[0], ext[3] - ext[2], ext[5] - ext[4]], np.float64)
    W = np.empty_like(V_idx)
    W[:, 0] = lo[0] + (V_idx[:, 0] + 0.5) / nx * span[0]
    W[:, 1] = lo[1] + (V_idx[:, 1] + 0.5) / ny * span[1]
    W[:, 2] = lo[2] + (V_idx[:, 2] + 0.5) / nz * span[2]
    return W


def blob_mesh(spheres, bounds, res: int, k: float) -> tuple[np.ndarray, np.ndarray]:
    """複数球の smooth union(sdf_ops)を marching cubes で滑らかな有機メッシュに。

    ``spheres`` = [(center, radius), ...]、``bounds`` = ((xlo,xhi),(ylo,yhi),(zlo,zhi))、
    ``res`` = 各軸ボクセル数、``k`` = smooth union の丸め半径。戻り値は外向き巻きの (V, F)。"""
    coords, ext = grid_coords(bounds, res)
    vol = None
    for c, r in spheres:
        s = sphere_sdf(coords, c, r)
        vol = s if vol is None else sdf_smooth_union(vol, s, k)
    V_idx, F = render3d.marching_cubes(vol, 0.0)
    V = _mc_to_world(V_idx, vol.shape, ext)
    F = _orient_outward(V, F)
    return V, F


def peanut(res: int = 24) -> tuple[np.ndarray, np.ndarray]:
    """2 球の smooth union = くびれ(首)を持つ凹形状。AO の凹部 GT に使う。"""
    return blob_mesh([((-0.75, 0.0, 0.0), 0.85), ((0.75, 0.0, 0.0), 0.85)],
                     ((-2.0, 2.0), (-1.3, 1.3), (-1.3, 1.3)), res=res, k=0.5)


def sculpture(res: int = 48) -> tuple[np.ndarray, np.ndarray]:
    """hero 用: 4 球の smooth union で作る有機的な「種子/ポッド」形の彫刻。"""
    spheres = [
        ((-0.55, -0.10, 0.00), 0.72),
        ((0.55, 0.05, 0.05), 0.66),
        ((0.05, 0.55, 0.30), 0.52),
        ((0.10, -0.35, 0.55), 0.42),
    ]
    return blob_mesh(spheres, ((-1.9, 1.9), (-1.7, 1.7), (-1.5, 1.9)),
                     res=res, k=0.42)


def sit_on_ground(V: np.ndarray) -> np.ndarray:
    """メッシュを最下点が z=0 に来るよう平行移動(地面に載せる)。"""
    V = V.copy()
    V[:, 2] -= V[:, 2].min()
    return V


# ═══════════════════════════════════════════════════════════════════════════
# 補助: specular=0 の counterfactual(render_beauty の物体陰影から鏡面だけ抜いた版)
# ═══════════════════════════════════════════════════════════════════════════
def _object_shade(normals, light_cam, kd, ks, sh, ka, albedo, spec_tint):
    """render_beauty と同じ式(phong_shade を分離評価)で物体 HDR 陰影を作る。ks=0 で Lambertian。"""
    view_cam = np.array([0.0, 0.0, 1.0], np.float64)
    diff = render_shade.phong_shade(normals, view=view_cam, light=light_cam,
                                    ambient=0.0, diffuse=1.0, specular=0.0,
                                    shininess=sh, clip=False)
    spec = render_shade.phong_shade(normals, view=view_cam, light=light_cam,
                                    ambient=0.0, diffuse=0.0, specular=1.0,
                                    shininess=sh, clip=False)
    body = ka + kd * diff
    hdr = body[..., None] * albedo[None, None, :] + (ks * spec)[..., None] * spec_tint[None, None, :]
    return hdr, spec


# ═══════════════════════════════════════════════════════════════════════════
# PNG 保存
# ═══════════════════════════════════════════════════════════════════════════
def save_png(img: np.ndarray, path: Path) -> bool:
    """float [0,1] (H,W,3) を 8bit PNG に保存(imageio → PIL → plt の順でフォールバック)。"""
    u8 = np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import imageio.v2 as imageio
        imageio.imwrite(path, u8)
        return True
    except Exception:
        pass
    try:
        from PIL import Image
        Image.fromarray(u8).save(path)
        return True
    except Exception:
        pass
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.imsave(path, u8)
        return True
    except Exception as exc:
        print(f"[note] PNG 保存に失敗: {exc}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    t0 = time.time()

    # ── GT 用シーン: 地面に載る球。接触部(mesh 底×地面)が AO の強い凹部になる ──
    #   (render_ao の実証済み GT「平面に載る球の接触は AO→0、頂上は AO→1」を踏襲)
    Vsp, Fsp = icosphere(1.0, subdiv=3)
    Vsp = sit_on_ground(Vsp)
    tri = Vsp[Fsp]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    if not np.all(area > 0):
        raise ValueError("sphere にゼロ面積三角形(退化入力)")
    print(f"[scene] sphere-on-ground 頂点 {len(Vsp)} / 面 {len(Fsp)}")

    pose = render3d.look_at([3.0, -3.6, 2.2], [0.0, 0.0, 0.9], up=(0.0, 0.0, 1.0))
    Kgt = render3d.intrinsics_from_fov(40.0, 96, 96)
    light = (0.35, 0.45, 0.85)                          # ワールド光源方向(上・前寄り)
    light_u = np.asarray(light, float) / np.linalg.norm(light)
    base = dict(pose=pose, intrinsics=Kgt, size=96, ss=1, material="plastic",
                albedo=(0.85, 0.55, 0.35), light=light, ao_samples=24,
                shadow_res=256, penumbra=0.0, shadow_samples=1)

    # render_beauty が内部で足す地面と同一 quad を再構成し、地面/物体/接触/頂上マスクを得る。
    Vg, Fg, gz, epsg = rb._ground_quad(Vsp, light_u, drop=0.01, span_scale=2.4)
    V_all = np.vstack([Vsp, Vg])
    F_all = np.vstack([Fsp, Fg + len(Vsp)])
    cview = render3d.render_mesh(V_all, F_all, pose=pose, intrinsics=Kgt, width=96, height=96)
    sil_all = cview["silhouette"] > 0
    Pw_all = render_shadow.unproject_to_world(cview["depth"], pose, Kgt)
    with np.errstate(invalid="ignore"):
        is_ground = sil_all & np.isfinite(Pw_all[..., 2]) & (np.abs(Pw_all[..., 2] - gz) < epsg)
        is_obj = sil_all & ~is_ground
        zc = Pw_all[..., 2]
        contact = is_obj & np.isfinite(zc) & (zc < 0.45)     # 地面と接する凹部
        topband = is_obj & np.isfinite(zc) & (zc > 1.4)      # 露出した頂部

    # ── (a) 決定的 ────────────────────────────────────────────────────────
    img1 = rb.render_beauty(Vsp, Fsp, **base)
    img2 = rb.render_beauty(Vsp, Fsp, **base)
    det_equal = bool(np.array_equal(img1, img2))
    print(f"[a] deterministic (2 calls pixel-identical): {det_equal}")

    # ── (g) 形 / 値域 ─────────────────────────────────────────────────────
    shape_ok = img1.shape == (96, 96, 3)
    range_ok = bool(img1.min() >= 0.0 and img1.max() <= 1.0)
    print(f"[g] shape {img1.shape} in-range [{img1.min():.3f},{img1.max():.3f}] -> {shape_ok and range_ok}")

    # ── (b) AO 寄与(接触=凹部は AO で暗化、頂部=露出はほぼ不変=選択的)────────
    #   tonemap='none' で線形に測る(reinhard の圧縮を避け寄与を素直に見る)。
    ao_on = rb.render_beauty(Vsp, Fsp, **{**base, "ao": True, "tonemap": "none"})
    ao_off = rb.render_beauty(Vsp, Fsp, **{**base, "ao": False, "tonemap": "none"})
    g_on = ao_on.mean(axis=2)
    g_off = ao_off.mean(axis=2)
    contact_on = float(g_on[contact].mean())
    contact_off = float(g_off[contact].mean())
    top_on = float(g_on[topband].mean())
    top_off = float(g_off[topband].mean())
    ao_contact = contact_off - contact_on               # 接触部の AO 暗化
    ao_top = top_off - top_on                           # 頂部の AO 暗化(≈0 のはず)
    print(f"[b] AO darken  contact(凹)={ao_contact:.3f} (on {contact_on:.3f}/off {contact_off:.3f})  "
          f"top(露出)={ao_top:.3f}  selective={ao_contact - ao_top:.3f}")

    # ── (c) 鏡面寄与(convex 球で単一ハイライトを分離)── fast(ao/影なし)───
    Vs, Fs = icosphere(1.0, subdiv=3)
    spose, sK = render3d.auto_view(Vs, margin=1.25, width=200, height=200)
    img_plastic = rb.render_beauty(Vs, Fs, pose=spose, intrinsics=sK, size=200, ss=1,
                                   material="plastic", albedo=(0.8, 0.8, 0.85),
                                   light=(0.3, 0.4, 1.0), ao=False, ground_shadow=False,
                                   tonemap="none")
    # 同一 normals・pose での specular=0 counterfactual を render_beauty の式で再構成。
    sview = render3d.render_mesh(Vs, Fs, pose=spose, intrinsics=sK, width=200, height=200)
    nrm = sview["normals"]
    sil_s = sview["silhouette"] > 0
    Lc = spose[:3, :3] @ (np.array([0.3, 0.4, 1.0]) / np.linalg.norm([0.3, 0.4, 1.0]))
    alb = np.array([0.8, 0.8, 0.85])
    mat = rb._MATERIALS["plastic"]
    hdr_spec, spec_lobe = _object_shade(nrm, Lc, mat["diffuse"], mat["specular"],
                                        mat["shininess"], 0.12, alb, np.ones(3))
    hdr_diff, _ = _object_shade(nrm, Lc, mat["diffuse"], 0.0, mat["shininess"],
                                0.12, alb, np.ones(3))
    bright_spec = hdr_spec.max(axis=2)
    bright_diff = hdr_diff.max(axis=2)
    # ハイライト = 鏡面版が拡散版を明確に上回る画素。
    hl = sil_s & (bright_spec > bright_diff + 0.15)
    hl_frac = float(hl.mean())
    hl_peak = float((bright_spec - bright_diff)[hl].max()) if hl.any() else 0.0
    # render_beauty(plastic, tonemap=none) 出力にも高輝度ハイライトが小面積で存在。
    bri_out = img_plastic.max(axis=2)
    diff_ref = np.clip(bright_diff, 0, 1)
    hot = sil_s & (bri_out > diff_ref.max() - 1e-6) & (bri_out > 0.6)
    hot_frac = float(hot.mean())
    print(f"[c] highlight(spec>diff+0.15) frac={hl_frac:.4f} peak={hl_peak:.3f} ; "
          f"render_beauty hot-pixel frac={hot_frac:.4f} (small bright cluster)")

    # ── (d) 接地影(render_beauty と同一シーンで cast_shadow の面積 GT + 地面の明暗)──
    sm_full = render_shadow.cast_shadow(V_all, F_all, np.array(light), pose=pose,
                                        intrinsics=Kgt, width=96, height=96,
                                        directional=True, penumbra=0.0, samples=1,
                                        shadow_res=256)
    # beat-null: 遮蔽物(球)を外し地面のみ → 影は出ない。
    sm_null = render_shadow.cast_shadow(Vg, Fg, np.array(light), pose=pose,
                                        intrinsics=Kgt, width=96, height=96,
                                        directional=True, penumbra=0.0, samples=1,
                                        shadow_res=256)
    area_full = int((is_ground & (sm_full < 0.5)).sum())
    area_null = int((is_ground & (sm_null < 0.5)).sum())
    # render_beauty(ground_shadow=True) の地面: 影側が明側より暗い(img1 を再利用)。
    gimg = img1.mean(axis=2)
    lit_ground = is_ground & (sm_full >= 0.5)
    sh_ground = is_ground & (sm_full < 0.5)
    lit_b = float(gimg[lit_ground].mean()) if lit_ground.any() else float("nan")
    sh_b = float(gimg[sh_ground].mean()) if sh_ground.any() else float("nan")
    print(f"[d] cast-shadow area: with-mesh={area_full}px  ground-only(null)={area_null}px ; "
          f"render_beauty ground lit={lit_b:.3f} shadowed={sh_b:.3f}")

    # ── (e) トーンマップ(順位保存 & max<=1)──────────────────────────────
    ramp = np.linspace(0.0, 8.0, 40).reshape(1, -1)     # HDR ハイライト域を含む
    rein = render_tonemap.tonemap_reinhard(ramp).ravel()
    clip = np.clip(ramp, 0, 1).ravel()
    rein_mono = bool(np.all(np.diff(rein) > 0))          # 全域で狭義単調(順位保持)
    clip_ties = int(np.sum(np.diff(clip) <= 1e-12))      # クリップは >1 で同点多発
    rein_max = float(rein.max())
    tm_out_max = float(img1.max())                       # render_beauty(reinhard) 出力
    print(f"[e] reinhard strictly-monotonic={rein_mono} max={rein_max:.3f} ; "
          f"naive-clip ties={clip_ties} ; render_beauty(reinhard) max={tm_out_max:.3f}")

    # ── (f) SSAA(ss=2 のエッジは ss=1 より滑らか)── fast(ao/影なし)──────
    aa_kw = dict(pose=spose, intrinsics=sK, size=160, material="plastic",
                 albedo=(0.8, 0.8, 0.85), light=(0.3, 0.4, 1.0),
                 ao=False, ground_shadow=False)
    img_ss1 = rb.render_beauty(Vs, Fs, ss=1, **aa_kw)
    img_ss2 = rb.render_beauty(Vs, Fs, ss=2, **aa_kw)
    e1 = render_ssaa.edge_alias_energy(img_ss1.mean(axis=2))
    e2 = render_ssaa.edge_alias_energy(img_ss2.mean(axis=2))
    print(f"[f] edge_alias_energy ss1={e1:.4f} ss2={e2:.4f} (ss2<ss1 => smoother)")

    # ═══ GT アサーション ════════════════════════════════════════════════
    assert det_equal, "(a) 決定的でない(2 回の出力が不一致)"
    assert shape_ok, f"(g) shape 不正: {img1.shape}"
    assert range_ok, "(g) 値域が [0,1] を外れた"

    assert ao_contact > 0.03, f"(b) 接触部が AO で暗くならない: darken={ao_contact:.3f}"
    assert contact_on < contact_off, "(b) ao_on の接触部が ao_off 以上に明るい"
    # 選択性: AO は「遮蔽された凹部」を暗くし「露出した頂部」はほぼ不変(一様減光でない)。
    assert ao_contact > ao_top + 0.02, \
        f"(b) AO が選択的でない(頂部も同程度暗い): contact={ao_contact:.3f} top={ao_top:.3f}"
    # beat-null: ao=False では暗化 0(接触も頂部も差なし)= AO を切ると寄与が消える。
    assert abs(ao_top) < 0.03, f"(b) 露出頂部が不当に暗化(AO の選択性が崩れた): {ao_top:.3f}"

    assert hl_frac > 0.0, "(c) 鏡面ハイライトが検出できない"
    assert hl_frac < 0.15, f"(c) ハイライトが小面積でない(鏡面らしくない): frac={hl_frac:.3f}"
    assert hl_peak > 0.2, f"(c) 鏡面の盛り上がりが弱い: peak={hl_peak:.3f}"
    assert 0.0 < hot_frac < 0.15, \
        f"(c) render_beauty 出力に小面積の高輝度ハイライトが無い: frac={hot_frac:.4f}"

    assert area_full > 0, "(d) mesh があるのに接地影が出ていない"
    assert area_null == 0, f"(d) beat-null: 遮蔽物なしで影が出た: {area_null}px"
    assert np.isfinite(lit_b) and np.isfinite(sh_b) and sh_b < lit_b - 0.02, \
        f"(d) render_beauty の地面: 影側が明側より暗くない lit={lit_b:.3f} sh={sh_b:.3f}"

    assert rein_mono, "(e) reinhard が狭義単調でない(順位を保てていない)"
    assert rein_max <= 1.0, f"(e) reinhard 出力が 1 を超えた: {rein_max:.3f}"
    assert clip_ties > 0, "(e) 素朴クリップが >1 域を潰していない(比較の前提が崩れた)"
    assert tm_out_max <= 1.0 + 1e-9, f"(e) render_beauty(reinhard) 出力が 1 超: {tm_out_max:.3f}"

    assert e2 < e1, f"(f) SSAA でジャギーが減っていない: ss1={e1:.4f} ss2={e2:.4f}"

    print(f"[time] GT 検証 {time.time() - t0:.1f}s")

    # ═══ hero 画像 ══════════════════════════════════════════════════════
    print("[hero] 有機彫刻をレンダリング中 ...")
    th = time.time()
    Vh, Fh = sculpture(res=48)
    Vh = sit_on_ground(Vh)
    # 良い構図: 少し上・斜め前から。金属質・暖色・ソフト接地影。
    lo, hi = Vh.min(0), Vh.max(0)
    cen = 0.5 * (lo + hi)
    rad = float(np.linalg.norm(hi - lo)) * 0.5
    eye = cen + np.array([2.6 * rad, -3.0 * rad, 2.0 * rad])
    hpose = render3d.look_at(eye, [cen[0], cen[1], cen[2] * 0.9 + 0.15 * rad],
                             up=(0.0, 0.0, 1.0))
    hK = render3d.intrinsics_from_fov(34.0, 640, 640)
    hero = rb.render_beauty(
        Vh, Fh, pose=hpose, intrinsics=hK, size=640, ss=2, material="metal",
        albedo=(0.90, 0.62, 0.30), light=(0.45, 0.55, 0.75), ambient=0.10,
        ao=True, ground_shadow=True, tonemap="aces", exposure=1.25,
        background=(0.07, 0.08, 0.10), ao_samples=48, shadow_res=512,
        penumbra=2.2, shadow_samples=6)
    hero_path = _REPO_ROOT / "examples_3d" / "_gallery" / "render_beauty_hero.png"
    saved = save_png(hero, hero_path)
    print(f"[hero] {hero.shape} 値域[{hero.min():.3f},{hero.max():.3f}] "
          f"保存={saved} path={hero_path} ({time.time() - th:.1f}s)")
    assert saved and hero_path.exists(), "hero PNG が保存されていない"
    assert hero.shape == (640, 640, 3), f"hero shape 不正: {hero.shape}"

    print(
        f"PASS: render_beauty が全品質層(ラスタライズ/鏡面/AO/接地影/SSAA/トーンマップ)を"
        f"1 本に合成。決定的={det_equal}、AO は凹部を {neck_off:.2f}→{neck_on:.2f} と暗くし"
        f"(darken {ao_margin:.2f}, beat-null で消失)、鏡面は小面積ハイライト(frac {hl_frac:.3f}, "
        f"peak {hl_peak:.2f})を生み、接地影は with-mesh {area_full}px vs null {area_null}px で"
        f"地面を暗く(lit {lit_b:.2f}→影 {sh_b:.2f})、reinhard は単調(max {rein_max:.2f})で"
        f"クリップの潰し({clip_ties} 同点)を回避、SSAA は edge energy {e1:.3f}→{e2:.3f} と低減。"
        f"hero 画像を {hero_path.name} に保存"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
