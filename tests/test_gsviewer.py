# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""門: gsviewer(3DGS をブラウザで見せる 1 枚の HTML)。

1. 独立した検算 —— 同じ gs・同じカメラ(pose, K)で、headless Chrome が撮ったページの描画と ``gs_render``(numpy の
   EWA 参照描画)を PSNR / SSIM で比べる。**門は壊して確かめる**: 共分散の回転を転置した版・y を反転した版・色を
   BGR にした版のページを作り、同じ基準で落ちることを見る(Chrome が無い環境では飛ばす)。
2. 埋め込んだデータを Python 側で戻し、元の gs と量子化の範囲で一致すること。
3. 間引いたら返り値とページの設定に記録されていること(黙って減らさない)。
4. 外部 URL が 0 であること。
5. カタログ: サムネイル(gs_render)と、その品の最初の視点のページの描画が一致すること / 品を切り替えても GPU の
   バッファ・テクスチャの数が増え続けないこと。

基準の決め方(2026-10-25 実測、トーラス 6,301 個・240×180、背景 灰):
  正しいページ = PSNR 40.5 dB / SSIM 0.9996。壊した版は下の ``test_browser_matches_gs_render`` の表を参照。
  差の中身は (a) 並べ替えの桶(16 bit)と画素ごとの厳密な深さ順の違い、(b) 表示の 8 bit の丸め、(c) 半精度の
  足し込み、(d) 位置 16 bit・大きさ 16 bit・四元数 8 bit の量子化。基準 PSNR ≥ 34 dB・SSIM ≥ 0.98 は、正しい版から
  6 dB 余裕を取り、壊した版(どれも 25 dB 未満)を確実に落とす位置に置いた。
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import driveworld  # noqa: E402
import gsplatnp  # noqa: E402
import gsviewer  # noqa: E402
import imgmetrics  # noqa: E402
import mathgeometry  # noqa: E402

PSNR_MIN = 34.0
SSIM_MIN = 0.98


def _torus_gs():
    """赤と青の縞のトーラス(平たい円盤のガウシアン = 異方的、色は左右非対称)。"""
    V, F = mathgeometry.mesh_torus(0.05, 0.02, 64, 32)
    w = driveworld._empty_world()
    col = np.where((np.arange(len(F)) % 64 < 32)[:, None], [0.9, 0.3, 0.2], [0.2, 0.5, 0.9])
    driveworld.world_add(w, V, F, 1, col)
    return gsplatnp.gs_from_world(w, spacing=0.0025)


@pytest.fixture(scope="module")
def torus():
    return _torus_gs()


# ── 2. 量子化の範囲で戻る ──────────────────────────────────────────────── #
def test_embedded_data_roundtrips_within_quantisation(torus, tmp_path):
    r = gsviewer.gs_viewer_html(torus, tmp_path / "v.html", title="t", lang="ja")
    emb = gsviewer._read_embedded(tmp_path / "v.html")
    d, meta = emb["items"][0], emb["cfg"]["items"][0]["meta"]
    c0 = gsviewer._canon(torus)
    c = gsviewer._subset(c0, gsviewer._importance_order(c0))
    assert len(d["mu"]) == r["n_kept"] == len(c["mu"])
    step = np.asarray(meta["span"]) / 65535.0
    assert np.all(np.abs(c["mu"] - d["mu"]) <= 0.5 * step + 1e-12)
    ls_step = meta["sspan"] / 65535.0
    assert np.all(np.abs(np.log(c["scale"]) - np.log(d["scale"])) <= 0.5 * ls_step + 1e-9)
    assert np.all(np.abs(c["rgb"] - d["rgb"]) <= 0.5 / 255 + 1e-12)
    assert np.all(np.abs(c["opacity"] - d["opacity"]) <= 0.5 / 255 + 1e-12)
    # 回転: 8 bit の四元数で、共分散(向きで決まる)の相対誤差が小さいこと(q と −q は同じ回転)
    R0, R1 = gsviewer._mat_from_quat(c["rot"]), gsviewer._mat_from_quat(d["rot"])
    S0 = np.einsum("nij,nj,nkj->nik", R0, c["scale"] ** 2, R0)
    S1 = np.einsum("nij,nj,nkj->nik", R1, d["scale"] ** 2, R1)
    rel = np.linalg.norm(S0 - S1, axis=(1, 2)) / np.linalg.norm(S0, axis=(1, 2))
    assert np.quantile(rel, 0.99) < 0.05, np.quantile(rel, 0.99)


def test_world_and_file_dicts_give_same_covariance(torus):
    """gs_from_world の Σ = R diag(cov_t, σn²) Rᵀ と、そろえた形(大きさ + 四元数)の Σ が一致する。"""
    c = gsviewer._canon(torus, bake_light=None)
    r = gsviewer._renderable(c)
    Sl = np.zeros((len(c["mu"]), 3, 3))
    Sl[:, :2, :2] = torus["cov_t"]
    Sl[:, 2, 2] = torus["sigma_n"] ** 2
    Sw = np.einsum("nij,njk,nlk->nil", torus["R"], Sl, torus["R"])
    Sl2 = np.zeros_like(Sl)
    Sl2[:, :2, :2] = r["cov_t"]
    Sl2[:, 2, 2] = r["sigma_n"] ** 2
    Sw2 = np.einsum("nij,njk,nlk->nil", r["R"], Sl2, r["R"])
    assert np.allclose(Sw, Sw2, rtol=1e-6, atol=1e-14)
    assert np.allclose(c["rgb"], torus["color"])


# ── 3. 間引きの記録 ────────────────────────────────────────────────────── #
def test_thinning_is_recorded_and_drops_least_important_first(torus):
    gs = dict(torus)
    rng = np.random.default_rng(1)
    gs["opacity"] = rng.uniform(0.2, 1.0, len(gs["mu"]))
    full = gsviewer.gs_viewer_html(gs, None, lang="en")
    small = gsviewer.gs_viewer_html(gs, None, lang="en", max_bytes=full["bytes"] - 40_000)
    assert not full["thinned"] and full["n_dropped"] == 0
    assert small["thinned"] and small["n_dropped"] > 0
    assert small["n_kept"] + small["n_dropped"] == small["n_input"] == len(gs["mu"])
    assert small["bytes"] <= full["bytes"] - 40_000
    emb = gsviewer._read_embedded(small["html"])
    it = emb["cfg"]["items"][0]
    assert it["thinning"]["n_dropped"] == small["n_dropped"]       # ページにも出す(「この表示について」の文)
    assert len(emb["items"][0]["mu"]) == small["n_kept"]
    kept_min = emb["items"][0]["opacity"].min()
    dropped_max = np.sort(gs["opacity"])[small["n_dropped"] - 1]
    assert kept_min >= dropped_max - 1.0 / 255                     # 不透明度の小さい順に落とした
    with pytest.raises(ValueError):
        gsviewer.gs_viewer_html(gs, None, max_bytes=20_000)         # ページそのものより小さい上限は拒否


# ── 4. 外部 URL 0 ──────────────────────────────────────────────────────── #
def test_page_has_no_external_urls(torus):
    r = gsviewer.gs_viewer_html(torus, None, hotspots=[{"pos": (0.07, 0, 0), "label": "a", "desc": "b"}])
    page = r["html"]
    assert page.count("http://") == 0 and page.count("https://") == 0 and r["external_urls"] == 0
    assert "<script src" not in page and "<link" not in page
    assert "DecompressionStream('gzip')" in page


def test_dimensions_of_torus_match_geometry(torus):
    """寸法(smallest_box3 の上向きの箱): トーラス R=50 mm, r=20 mm → 140 × 140 × 40 mm(中心は面の上)。"""
    r = gsviewer.gs_viewer_html(torus, None, lang="en")
    mm = r["dims_mm"]
    assert abs(mm["W"] - 140) < 1.0 and abs(mm["D"] - 140) < 1.0 and abs(mm["H"] - 40) < 0.5, mm
    assert "smallest_box3" in r["dims"]["op"]
    r2 = gsviewer.gs_viewer_html(torus, None, lang="en", dims="obb")
    assert abs(r2["dims_mm"]["H"] - 40) < 0.5


def test_bad_inputs_fail_closed(torus):
    with pytest.raises(ValueError):
        gsviewer.gs_viewer_html({}, None)
    with pytest.raises(ValueError):
        gsviewer.gs_viewer_html(torus, None, lang="xx")
    with pytest.raises(ValueError):
        gsviewer.gs_viewer_html(torus, None, lang=["ja", "en"], title={"ja": "だけ"})     # 言語の欠けは補わない
    with pytest.raises(ValueError):
        gsviewer.gs_viewer_html(torus, None, bg="pink")
    bad = dict(torus)
    bad["mu"] = bad["mu"].copy()
    bad["mu"][0, 0] = np.nan
    with pytest.raises(ValueError):
        gsviewer.gs_viewer_html(bad, None)
    with pytest.raises(ValueError):
        gsviewer.gs_catalog_html([], None)


def test_reads_splat_and_ply_files(torus, tmp_path):
    """.splat(32 バイト)を書いて CLI の入口(パス)で読める / PLY の f_rest_* から捨てた SH の次数を数える。"""
    c = gsviewer._canon(torus)
    n = len(c["mu"])
    rec = np.zeros((n, 32), np.uint8)
    rec[:, :24] = np.column_stack([c["mu"], c["scale"]]).astype("<f4").view(np.uint8).reshape(n, 24)
    rec[:, 24:28] = np.rint(np.column_stack([c["rgb"], c["opacity"]]) * 255).astype(np.uint8)
    rec[:, 28:32] = np.rint(c["rot"] * 128 + 128).clip(0, 255).astype(np.uint8)
    p = tmp_path / "t.splat"
    rec.tofile(p)
    rc = gsviewer._main([str(p), "--out", str(tmp_path / "s.html"), "--title", "splat", "--lang", "en"])
    assert rc == 0 and (tmp_path / "s.html").exists()
    hdr = ("ply\nformat binary_little_endian 1.0\nelement vertex 1\n" + "".join(
        "property float %s\n" % k for k in ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2"] + ["f_rest_%d" % i for i in range(45)]
        + ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]) + "end_header\n").encode()
    q = tmp_path / "t.ply"
    q.write_bytes(hdr + np.zeros(6 + 45 + 8, "<f4").tobytes())
    assert gsviewer._ply_sh_degree(q) == 3
    r = gsviewer.gs_viewer_html(q, None, lang="en", dims=False)
    assert r["sh_degree_in"] == 3 and r["sh_degree_used"] == 0 and r["sh_dropped"]


# ── 1. / 5. ブラウザの描画との突き合わせ(Chrome が無ければ飛ばす)──────────────── #
def _chrome():
    try:
        import headless_chrome
    except ImportError:
        return None
    return headless_chrome if headless_chrome.find_chrome() else None


def _shot(ch, url, W, H):
    from PIL import Image
    ch.open(url, width=W, height=H)
    ch.wait_for("window.__gs && window.__gs.ready", timeout=90)
    png = ch.screenshot()
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), np.float64)[:H, :W] / 255.0


def _cam_query(pose, K, W, H):
    a = list(pose[:3, :3].ravel()) + list(pose[:3, 3]) + [K[0, 0], K[1, 1], K[0, 2], K[1, 2], W, H]
    return ",".join("%.10g" % v for v in a)


#: 壊した版(ページの文字列を差し替える)。どれも正しい描画から明らかに崩れる。
BREAKS = {
    "cov_rotation_transposed": ("mat3 Sc = u_R * S * transpose(u_R);", "mat3 Sc = transpose(u_R) * S * u_R;"),
    "y_flipped": ("vec2 p = vec2(gl_FragCoord.x - 0.5, u_vp.y - gl_FragCoord.y - 0.5);",
                  "vec2 p = vec2(gl_FragCoord.x - 0.5, gl_FragCoord.y - 0.5);"),
    "bgr": ("v_col = vec3(t2.z, t2.w, t3.x);", "v_col = vec3(t3.x, t2.w, t2.z);"),
}


def test_browser_matches_gs_render(torus, tmp_path):
    hc = _chrome()
    if hc is None:
        pytest.skip("Chrome / Chromium not found")
    W, H = 240, 180
    r = gsviewer.gs_viewer_html(torus, tmp_path / "ok.html", lang="en")
    cam = r["camera"]
    pose = gsviewer._orbit_pose(cam["target"], -50.0, 30.0, cam["dist"])
    K = gsviewer._intrinsics(35.0, W, H)
    c0 = gsviewer._canon(torus)
    ref = gsplatnp.gs_render(gsviewer._renderable(c0), pose, K, W, H, ambient=1.0, sky=gsviewer.BACKGROUNDS["gray"])["color"]
    page = (tmp_path / "ok.html").read_text(encoding="utf-8")
    for name, (a, b) in BREAKS.items():
        assert page.count(a) == 1, name
        (tmp_path / (name + ".html")).write_text(page.replace(a, b), encoding="utf-8")
    q = "?gate=1&bg=gray&cam=" + _cam_query(pose, K, W, H)
    res = {}
    with hc.HeadlessChrome() as ch:
        for name in ["ok"] + list(BREAKS):
            img = _shot(ch, hc.file_url(tmp_path / (name + ".html")) + q, W, H)
            res[name] = (imgmetrics.psnr(ref, img, data_range=1.0), imgmetrics.ssim(ref.mean(2), img.mean(2), data_range=1.0))
    print("PSNR / SSIM:", {k: ("%.2f dB" % v[0], "%.4f" % v[1]) for k, v in res.items()})
    assert res["ok"][0] >= PSNR_MIN and res["ok"][1] >= SSIM_MIN, res["ok"]
    for name in BREAKS:
        assert res[name][0] < PSNR_MIN, (name, res[name])           # 壊した版は門で落ちる


def test_catalog_thumbnails_match_view_and_gpu_memory_is_released(torus, tmp_path):
    hc = _chrome()
    gs2 = dict(torus)
    gs2["color"] = gs2["color"][:, ::-1].copy()                    # 色違いの 2 品目
    items = [{"gs": torus, "name": {"ja": "赤青", "en": "red-blue"}}, {"gs": gs2, "name": {"ja": "青赤", "en": "blue-red"}}]
    r = gsviewer.gs_catalog_html(items, tmp_path / "cat.html", lang=["ja", "en"], thumb_px=160)
    assert r["external_urls"] == 0 and len(r["items"]) == 2 and r["n_dropped_total"] == 0
    if hc is None:
        pytest.skip("Chrome / Chromium not found")
    from PIL import Image
    import base64
    emb = gsviewer._read_embedded(tmp_path / "cat.html")
    with hc.HeadlessChrome() as ch:
        for i, it in enumerate(emb["cfg"]["items"]):
            cam = it["camera"]
            pose = gsviewer._orbit_pose(cam["target"], cam["yaw"], cam["pitch"], cam["dist"])
            K = gsviewer._intrinsics(cam["fov"], 160, 160)
            thumb = np.asarray(Image.open(io.BytesIO(base64.b64decode(it["thumb"].split(",", 1)[1]))).convert("RGB"),
                               np.float64) / 255.0
            img = _shot(ch, hc.file_url(tmp_path / "cat.html") + "?gate=1&item=%d&cam=%s" % (i, _cam_query(pose, K, 160, 160)),
                        160, 160)
            p = imgmetrics.psnr(thumb, img, data_range=1.0)
            print("thumbnail vs view, item %d: PSNR %.2f dB" % (i, p))
            assert p >= PSNR_MIN, (i, p)
        ch.open(hc.file_url(tmp_path / "cat.html") + "?cycle=8&spin=0", width=400, height=300)
        ch.wait_for("window.__gsCycle", timeout=120)
        log = ch.eval("window.__gsCycle")
        after = ch.eval("[window.__gsStats.buffers, window.__gsStats.textures]")
    print("GPU buffers / textures per switch:", [(e["buffers"], e["textures"]) for e in log], "after back:", after)
    assert len(log) == 8
    assert len({(e["buffers"], e["textures"]) for e in log}) == 1        # 切り替えても増え続けない
    assert after[0] == log[0]["buffers"] - 1 and after[1] == log[0]["textures"] - 1   # 一覧に戻ると品の 1 組を解放
