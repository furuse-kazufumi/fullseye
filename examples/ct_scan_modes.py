# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ct_scan_modes — 1 つの幾何の記述で CT の全方式を再構成し、方式ごとに真値と比べる。

    py -3.11 examples/ct_scan_modes.py

【この例が解く問題】
工業用 CT はコーンビームが標準で、基板にはラミノグラフィ、長い部品にはヘリカルを使う。
方式ごとに別の再構成コードを持つと、どれか 1 つの直しが他へ届かない。ここでは
`ct_scan_geometry` の引数だけで方式を切り替え、再構成 op は共通のまま回す。

    ct_scan_geometry        線源・検出器の位置を view ごとに持つ dict
      → ellipsoid_projections  閉形式の線積分(投影器を通らない真値)
      → fdk_reconstruct        式のある方式
      → sirt_reconstruct / os_sart_reconstruct / tv_reconstruct  式のない方式

【グラウンドトゥルース】
楕円体の線積分は弦の長さなので、どの方式でも投影に離散化誤差が入らない。印字する
RMSE は `shepp_logan_3d` のボクセルとの差で、`<Ax, y> = <x, A^T y>` の相対差も出す。
"""
from __future__ import annotations

import numpy as np

import examplefig as figs
import fullseye as fs


def rmse(a, b):
    """二乗平均平方根誤差。"""
    return float(np.sqrt(np.mean((a - b) ** 2)))


def adjoint_gap(geom):
    """随伴性の相対差。乱数の x, y で <Ax, y> と <x, A^T y> を比べる。"""
    rng = np.random.default_rng(0)
    x = rng.random(geom["vol_shape"])
    y = rng.random((geom["n_views"], geom["n_v"], geom["n_u"]))
    lhs = float(np.sum(fs.ct_forward_project(x, geom, device="cpu") * y))
    rhs = float(np.sum(x * fs.ct_adjoint_project(y, geom, device="cpu")))
    return abs(lhs - rhs) / abs(lhs)


def main():
    size = 32
    common = {"n_u": 64, "n_v": 64, "vol_shape": size}
    truth = fs.shepp_logan_3d(size)
    half_fan = float(np.rad2deg(np.arctan(64.0 / 192.0)))
    scans = [
        ("コーン 360 度", dict(common, scan="cone", n_views=90)),
        ("ヘリカル", dict(scan="helical", n_views=240, n_u=64, n_v=24, vol_shape=size, pitch=0.5)),
        ("ラミノグラフィ 60 度", dict(common, scan="laminography", n_views=90, tilt_deg=60.0,
                                     du=1.0, dv=1.0)),
        ("ショートスキャン", dict(common, scan="cone", n_views=60, arc_deg=182.0 + 2.0 * half_fan)),
        ("検出器オフセット", dict(scan="cone", n_views=90, n_u=50, n_v=64, vol_shape=size, offset_u=14.0)),
    ]
    print("方式                     再構成   RMSE     随伴性の相対差")
    panels = [("真値(z 中央)", truth[size // 2])]
    for name, kwargs in scans:
        geom = fs.ct_scan_geometry(**kwargs)
        proj = fs.ellipsoid_projections(geom, device="cpu")
        rec = fs.fdk_reconstruct(proj, geom, device="cpu")
        print("%-20s FDK    %.4f   %.1e" % (name, rmse(rec, truth), adjoint_gap(geom)))
        panels.append((name, rec[size // 2]))

    geom = fs.ct_scan_geometry("tomosynthesis", n_views=21, n_u=64, n_v=64, vol_shape=size)
    proj = fs.ellipsoid_projections(geom, device="cpu")
    rec = fs.sirt_reconstruct(proj, geom, n_iter=30, device="cpu")
    print("%-20s SIRT   %.4f   %.1e" % ("トモシンセシス", rmse(rec, truth), adjoint_gap(geom)))
    panels.append(("トモシンセシス", rec[size // 2]))

    slice_shape = (1, 96, 96)
    flat = fs.ellipsoid_phantom(slice_shape)
    geom = fs.ct_scan_geometry("fan", n_views=20, n_u=192, n_v=1, vol_shape=slice_shape)
    proj = fs.ellipsoid_projections(geom, device="cpu")
    print("少数ビュー 20 本 FDK %.4f / SIRT %.4f / OS-SART %.4f / TV %.4f" % (
        rmse(fs.fdk_reconstruct(proj, geom, device="cpu"), flat),
        rmse(fs.sirt_reconstruct(proj, geom, n_iter=30, device="cpu"), flat),
        rmse(fs.os_sart_reconstruct(proj, geom, n_iter=10, n_subsets=5, device="cpu"), flat),
        rmse(fs.tv_reconstruct(proj, geom, n_iter=100, device="cpu"), flat)))

    for name, image in panels:
        figs.save(name, np.clip(image, 0.0, 1.0), name + "の z 中央断面")


if __name__ == "__main__":
    main()
