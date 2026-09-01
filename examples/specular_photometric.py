# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""specular_photometric — 光沢面の検査を 1 本の筋で通す(specularity 13 op)。

    py -3.11 examples/specular_photometric.py

【この例が解く問題】
金属や塗装のような**テカる面**の外観検査。Lambertian を前提にした形状復元は
そこで壊れる — `photometric.py` の docstring 自身が「スペキュラは線形性を破る」と
書いているとおり。壊れる場所を数値で見せてから、3 つの逃げ道を順に通す。

(1) 順方向: 既知のアルベド・既知の法線・既知のハイライトで合成し、
    **答えを知っている画像**を作る(これが無いと以降の主張が検証できない)。
(2) 色による分離: 二色性反射モデル。鏡面成分は光源色方向の 1 次元部分空間に
    載るので、分離は最適化ではなく**射影**。機械精度で戻る。
(3) 射影だけを使う道: 光源色に直交する成分は、どんな形のハイライトを足しても
    **一切変わらない**。ローブ形状を知らなくてよいのが利点。
(4) 光源色を画像から: 2 つ以上の材質の二色性平面が交わる線が光源色そのもの。
(5) 影の下での形状復元: 8 灯のうち 3 灯を遮って、**素の最小二乗が壊れ、
    頑健版が耐える**ことを角度誤差で並べて出す。ここが本題。
(6) 破綻点の開示: 半分(4 灯)遮ると頑健版も壊れる。隠さず出す。
(7) 偏光による分離: 偏光板を回した 4 枚から無偏光成分と偏光成分を閉形式で分け、
    Stokes ベクトルを `optics.stokes_analyze` にそのまま渡す。

【グラウンドトゥルース(数値で嘘を弾く)】
1. specular_diffuse_split: 既知の鏡面成分を足した画像から拡散成分が機械精度
   (< 1e-14)で戻る。diffuse + specular == 入力。
2. specular_free_transform: 任意のハイライトを足しても出力が変わらない(< 1e-14)。
3. illuminant_from_dichromatic_planes: 3 材質から真の光源色が < 1e-12 で戻る。
4. brdf_microfacet: 法線入射で f0 / (4 pi roughness^4) の閉形式に一致。
   brdf_blinn_phong: 相反性が**厳密に** 0 差。
5. photometric_stereo_robust: 3 灯遮蔽で lstsq は平均 64 度、median/ransac は
   0.0001 度(= float32 出力の量子化下限)。遮られた灯を inlier から外す。
6. polarization_separate: polarization_render の逆で < 1e-14。
   polarization_stokes → optics.stokes_analyze が入れた方位角を返す。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optics as O  # noqa: E402
import photometric as PM  # noqa: E402
import specularity as SP  # noqa: E402

WHITE = np.ones(3) / np.sqrt(3.0)


def _bump_normals(h=64, w=64, amp=6.0, sigma=14.0):
    """ガウス丘の**float64 の**単位法線。

    photometric.surface_normals は float32 を返すので、それを使うと以下の
    「機械精度」がすべて float32 精度(~1e-7)の測定になってしまう。
    """
    y, x = np.mgrid[0:h, 0:w]
    z = amp * np.exp(-(((x - w / 2.0) ** 2 + (y - h / 2.0) ** 2)
                       / (2.0 * sigma ** 2)))
    zy, zx = np.gradient(z)
    n = np.stack([-zx, -zy, np.ones_like(zx)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def main():
    ok = True
    h = w = 64

    # ------------------------------------------------------------------ #
    # 1) 順方向: 答えを知っている検査画像を作る                            #
    # ------------------------------------------------------------------ #
    normals = _bump_normals(h, w)
    albedo = np.array([0.80, 0.55, 0.35])          # 塗装面の色(1 材質)
    light = np.array([0.3, 0.2, 1.0])
    shading = PM.render_lambertian(normals, 1.0, light).astype(np.float64)
    diffuse_true = albedo * shading[..., None]

    # ハイライトは「支持の外で厳密に 0」にする。ここが分離の可解性の条件で、
    # レンダしたローブは裾が 0 にならないので、その差は (2) の最後で測る。
    y, x = np.mgrid[0:h, 0:w]
    m_s_true = 0.7 * np.exp(-(((x - 26.0) ** 2 + (y - 24.0) ** 2) / 26.0))
    m_s_true[m_s_true < 1e-3] = 0.0
    image = diffuse_true + m_s_true[..., None] * WHITE
    free_frac = float((m_s_true == 0.0).mean())
    print(f"1) 合成: {h}x{w} 塗装面 albedo={np.round(albedo, 3).tolist()}  "
          f"ハイライト最大 m_s={m_s_true.max():.3f}  "
          f"鏡面成分ゼロの画素={free_frac:.1%}")

    # ------------------------------------------------------------------ #
    # 2) 色による分離(二色性反射モデル)                                  #
    # ------------------------------------------------------------------ #
    diffuse, specular = SP.specular_diffuse_split(image)
    err_d = float(np.abs(diffuse - diffuse_true).max())
    err_s = float(np.abs(specular - m_s_true[..., None] * WHITE).max())
    err_part = float(np.abs(diffuse + specular - image).max())
    print(f"2) 二色性分離(材質 1・光源色既知): 拡散の最大誤差={err_d:.2e}  "
          f"鏡面の最大誤差={err_s:.2e}  分割の閉じ={err_part:.2e}")
    assert err_d < 1e-14 and err_s < 1e-14 and err_part < 1e-15
    ok &= err_d < 1e-14

    coeff = SP.specular_coefficient_map(image)
    print(f"   鏡面係数マップ m_s: 最大誤差={np.abs(coeff - m_s_true).max():.2e}  "
          f"(2-D なので閾値処理でテカり領域がそのまま取れる)")
    assert np.abs(coeff - m_s_true).max() < 1e-14

    # 鏡面成分がゼロの画素が 1 つも無いとき、分離できない定数が残る。
    # これはモデルの曖昧性で、ローブを鋭くすると誤差も一緒に縮む。
    for shininess in (8.0, 200.0):
        rendered = SP.dichromatic_render(normals, albedo, light, (1, 1, 1),
                                         specular=0.6, shininess=shininess)
        floor = float(((rendered - diffuse_true) @ WHITE).min())
        bias = float(np.abs(SP.specular_diffuse_split(rendered)[0]
                            - diffuse_true).max())
        exact = float(np.abs(SP.specular_diffuse_split(rendered,
                                                       body_rgb=albedo)[0]
                             - diffuse_true).max())
        print(f"   正直な限界(shininess={shininess:5.1f}): 一番暗いハイライト"
              f"={floor:.3e} → 分離のズレ={bias:.3e}  "
              f"(body_rgb を与えれば {exact:.1e})")
        assert exact < 1e-12

    # ------------------------------------------------------------------ #
    # 3) ローブ形状を知らずに済ませる道: 光源色への射影を捨てる            #
    # ------------------------------------------------------------------ #
    rng = np.random.default_rng(0)
    weird = (rng.random((h, w)) ** 3) * 12.0        # でたらめな形のハイライト
    inv = float(np.abs(SP.specular_free_transform(diffuse_true + weird[..., None] * WHITE)
                       - SP.specular_free_transform(diffuse_true)).max())
    print(f"3) 鏡面不変な部分空間: でたらめな強さ・形のハイライトを足しても "
          f"出力の変化={inv:.2e}(射影なので恒等式)")
    assert inv < 1e-14

    # ------------------------------------------------------------------ #
    # 4) 光源色を画像から求める(2 材質以上の二色性平面の交線)             #
    # ------------------------------------------------------------------ #
    lamp = np.array([1.0, 0.92, 0.78])
    lamp = lamp / np.linalg.norm(lamp)
    labels = np.zeros((h, w), dtype=np.int32)
    labels[:, w // 3: 2 * w // 3] = 1
    labels[:, 2 * w // 3:] = 2
    multi = np.zeros((h, w, 3))
    for k, c in enumerate((np.array([0.80, 0.55, 0.35]),
                           np.array([0.25, 0.60, 0.75]),
                           np.array([0.55, 0.30, 0.70]))):
        im = c * shading[..., None] + m_s_true[..., None] * lamp
        multi[labels == k] = im[labels == k]
    est = SP.illuminant_from_dichromatic_planes(multi, labels)
    ang = float(np.degrees(np.arccos(np.clip(est @ lamp, -1.0, 1.0))))
    print(f"4) 光源色の推定(3 材質): 真値={np.round(lamp, 6)}  "
          f"推定={np.round(est, 6)}  角度誤差={ang:.3e} deg")
    assert np.abs(est - lamp).max() < 1e-12

    # 反射ローブの検算(閉形式の 2 点)
    flat = np.dstack([np.zeros((4, 4)), np.zeros((4, 4)), np.ones((4, 4))])
    peak = float(SP.brdf_microfacet(flat, roughness=0.3, f0=0.04).max())
    closed = 0.04 / (4.0 * np.pi * 0.3 ** 4)
    l1, v1 = np.array([0.4, -0.2, 1.0]), np.array([-0.3, 0.5, 1.0])
    recip = float(np.abs(SP.brdf_blinn_phong(normals, l1, v1)
                         - SP.brdf_blinn_phong(normals, v1, l1)).max())
    print(f"   BRDF: microfacet 法線入射={peak:.12f}(閉形式 {closed:.12f})  "
          f"Blinn-Phong 相反性の差={recip:.1e}")
    assert abs(peak - closed) < 1e-12 and recip == 0.0

    # ------------------------------------------------------------------ #
    # 5) 影の下での形状復元 — ここが本題                                   #
    # ------------------------------------------------------------------ #
    n_lights = 8
    L = np.array([[np.cos(a), np.sin(a), 2.2]
                  for a in np.linspace(0, 2 * np.pi, n_lights, endpoint=False)])
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    surface = _bump_normals(h, w, amp=4.0)
    alb_map = 0.7 + 0.2 * np.cos(np.linspace(0, 3, h))[:, None] * np.ones((1, w))
    ndl = np.einsum("hwc,nc->nhw", surface, L)
    assert ndl.min() > 0.0, "この配置では attached shadow は無い(cast shadow だけを見る)"
    clean = alb_map[None] * ndl
    blocked = 3
    shadowed = clean.copy()
    shadowed[:blocked] = 0.0            # 遮蔽物が 3 灯を遮った = cast shadow

    print(f"5) 影の下のフォトメトリックステレオ({n_lights} 灯中 {blocked} 灯が"
          f"遮蔽・N·L は全画素で正):")
    results = {}
    for method in ("lstsq", "median", "ransac"):
        nrm, alb, inl = SP.photometric_stereo_robust(shadowed, L, method=method)
        err = PM.angular_error_deg(nrm, surface)
        results[method] = err.mean()
        print(f"   {method:7s}: 法線の平均角度誤差={err.mean():8.4f} deg  "
              f"最大={err.max():8.4f} deg  アルベド最大誤差={np.abs(alb - alb_map).max():.2e}  "
              f"遮蔽灯を信じた率={inl[:blocked].mean():.3f}")
    assert results["lstsq"] > 25.0, "素の最小二乗が壊れていないと比較にならない"
    assert results["ransac"] < 1e-3 and results["median"] < 1e-3
    ok &= results["lstsq"] > 1e4 * results["ransac"]

    cast = PM.angular_error_deg(surface.astype(np.float32), surface).max()
    print(f"   0.0001 deg は誤差ではなく**下限**: 真の法線を float32 に丸めた"
          f"だけで {cast:.6f} deg(返り値が float32 = photometric と同じ規約)")

    resid_clean = SP.photometric_residual(clean, L, surface, alb_map).max()
    resid_shadow = SP.photometric_residual(shadowed, L, surface, alb_map).max()
    print(f"   残差マップ: 影なし={resid_clean:.2e}  影あり={resid_shadow:.3f}  "
          f"(頑健版に手を出す前に「必要か」を答える診断)")
    assert resid_clean < 1e-15 and resid_shadow > 0.1

    # ------------------------------------------------------------------ #
    # 6) 破綻点の開示 — 隠すと頑健性の主張が嘘になる                        #
    # ------------------------------------------------------------------ #
    # 遮蔽(値がゼロ)は「方程式が無い」だけなので、ゼロ判定で切り分けられる。
    # 8 灯中 6 灯が遮蔽されると生きた灯は 2 本 = 未知数 3・式 2 の劣決定になり、
    # ここでは答えを返さず NaN を返す(以前は最小ノルム解を黙って返していた)。
    for k in (4, 5, 6):
        obs = clean.copy()
        obs[:k] = 0.0
        nrm, _alb, inl = SP.photometric_stereo_robust(obs, L, method="ransac")
        nanfrac = float(np.isnan(nrm[..., 0]).mean())
        e = PM.angular_error_deg(nrm, surface)
        emean = float(np.nanmean(e)) if nanfrac < 1.0 else float("nan")
        print(f"6) 遮蔽 {k}/8 灯: 信じた灯={inl.sum(axis=0).min()} 本  "
              f"平均誤差={emean:.4f} deg  解けない画素={100 * nanfrac:.0f}%")
        if k <= 5:
            assert nanfrac == 0.0 and emean < 1e-3
        else:
            assert nanfrac == 1.0, "劣決定なら答えを返してはいけない"

    # 本当の破綻点は「ゼロ」ではなく「正の外れ値」で出る。ハイライトは方程式を
    # 持っているので、多数決が拮抗する 50% 汚染では誤った側が勝ちうる。
    spiked = clean.copy()
    spiked[:4] += 3.0
    broke = PM.angular_error_deg(
        SP.photometric_stereo_robust(spiked, L, method="ransac")[0], surface).mean()
    print(f"   破綻点(正の外れ値): 8 灯中 4 灯(半分)にハイライトを足すと"
          f" ransac は {broke:.2f} deg で壊れる — 汚染された 4 枚もそれ自体は"
          f"無矛盾なモデルなので、多数決では選び分けられない")
    assert broke > 50.0

    # ------------------------------------------------------------------ #
    # 7) 偏光による分離(色を使わない、テクスチャがあっても効く道)          #
    # ------------------------------------------------------------------ #
    pol_d = 0.4 + 0.3 * rng.random((h, w))
    pol_s = 0.5 * rng.random((h, w))
    azimuth = 30.0
    frames = SP.polarization_render(pol_d, pol_s, (0.0, 45.0, 90.0, 135.0), azimuth)
    got_d, got_s = SP.polarization_separate(frames)
    e_d = float(np.abs(got_d - pol_d).max())
    e_s = float(np.abs(got_s - pol_s).max())
    dolp = SP.polarization_dolp_map(frames)
    e_p = float(np.abs(dolp - pol_s / (pol_d + pol_s)).max())
    print(f"7) 偏光分離(偏光板 0/45/90/135 deg の 4 枚): "
          f"拡散の最大誤差={e_d:.2e}  鏡面={e_s:.2e}  偏光度={e_p:.2e}")
    assert e_d < 1e-14 and e_s < 1e-14 and e_p < 1e-14

    stokes = SP.polarization_stokes(frames)
    an = O.stokes_analyze(stokes)
    print(f"   Stokes={np.round(stokes, 6)} → optics.stokes_analyze: "
          f"偏光度={an['dop']:.6f}  方位角={an['azimuth_deg']:.6f} deg"
          f"(入れた値 {azimuth})  handedness={an['handedness']}")
    assert abs(an["azimuth_deg"] - azimuth) < 1e-9
    assert an["handedness"] == "linear"     # 直線偏光板だけでは S3 は測れない

    print("PASS: specularity 13 op すべてが閉形式のグラウンドトゥルースと一致"
          "(破綻点と分離できない定数も同じ数値で開示済み)")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
