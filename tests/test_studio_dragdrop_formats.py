# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio のドラッグ・アンド・ドロップと、扱えるファイル形式の**ASCII / バイナリ両方**(2026-10-03)。

ユーザー: 「画像をドラッグ・アンド・ドロップして見れる」「Python スクリプトも D&D で開ける」
「3DGS のファイルとか、他の扱えるファイルも D&D 対応」「アスキー形式とバイナリ形式両方対応」。

* 3DGS(INRIA 形式の PLY)は ASCII・binary_little_endian・binary_big_endian の 3 通りで**同じ値**に読める
  (書き出しは独立の素朴なコード、読みは gsplatnp.gs_read_file)。``.splat`` はバイナリしか無い形式。
* 点群・メッシュ: PLY(ASCII / バイナリ)、STL(ASCII / バイナリ)、PCD(ASCII / バイナリ)を Studio の
  ドロップから 3-D ビューアで開き、点の数と座標が書いたものと一致する。
* 振り分け: 画像 / フォルダ / .py / .json / 3-D / 動画(アニメーション GIF)/ .npy の形。
* 以前の経路は 3DGS の PLY を**色無し**の点群として読んでいた(read_points の色が None)。
"""
import os
import struct

import numpy as np
import pytest

import studio

SH_C0 = 0.28209479177387814
NAMES = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
         "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _gaussians(n=200, seed=0):
    rng = np.random.default_rng(seed)
    m = rng.normal(size=(n, 3))
    rgb = rng.random((n, 3)) * 0.8 + 0.1
    opl = rng.normal(size=n)
    sc = np.log(rng.random((n, 3)) * 0.05 + 0.01)
    q = rng.normal(size=(n, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    data = np.column_stack([m, np.zeros((n, 3)), (rgb - 0.5) / SH_C0, opl, sc, q]).astype(np.float32)
    return data, m.astype(np.float32), rgb, 1 / (1 + np.exp(-opl.astype(np.float32)))


def _write_3dgs_ply(path, data, fmt):
    """3DGS の PLY を**独立の素朴なコード**で書く(fmt = ascii / binary_little_endian / binary_big_endian)。"""
    head = ["ply", "format %s 1.0" % fmt, "element vertex %d" % len(data)]
    head += ["property float %s" % n for n in NAMES] + ["end_header"]
    with open(path, "wb") as f:
        f.write(("\n".join(head) + "\n").encode("ascii"))
        if fmt == "ascii":
            for row in data:
                f.write((" ".join(repr(float(v)) for v in row) + "\n").encode("ascii"))
        else:
            f.write(data.astype(">f4" if fmt == "binary_big_endian" else "<f4").tobytes())


@pytest.mark.parametrize("fmt", ["ascii", "binary_little_endian", "binary_big_endian"])
def test_3dgs_ply_reads_identically_in_ascii_and_both_binary_endians(tmp_path, fmt):
    import gsplatnp
    data, m, rgb, op = _gaussians()
    p = str(tmp_path / ("g_%s.ply" % fmt))
    _write_3dgs_ply(p, data, fmt)
    assert gsplatnp._gs_is_splat_ply(p)
    g = gsplatnp.gs_read_file(p)
    assert g["n_total"] == len(data) and g["format"] == "ply"
    assert np.abs(g["xyz"] - m).max() < 1e-6
    assert np.abs(g["rgb"] - rgb).max() < 1e-5                      # rgb = 0.5 + C0·f_dc
    assert np.abs(g["opacity"] - op).max() < 1e-6                   # sigmoid(logit)
    assert np.abs(np.linalg.norm(g["rot"], axis=1) - 1).max() < 1e-9
    assert len(gsplatnp.gs_read_file(p, min_opacity=0.5)["xyz"]) == int((op >= 0.5).sum()) > 0


def test_splat_binary_format(tmp_path):
    """.splat(antimatter15): 1 個 32 バイト。色は 8 bit なので 1/255 の量子化の範囲で一致。"""
    import gsplatnp
    data, m, rgb, op = _gaussians(seed=1)
    p = str(tmp_path / "g.splat")
    with open(p, "wb") as f:
        for i in range(len(m)):
            f.write(struct.pack("<6f", *m[i], *np.exp(data[i, 10:13])))
            f.write(bytes(int(round(v * 255)) for v in (*rgb[i], op[i])))
            f.write(bytes(int(np.clip(round(v * 128 + 128), 0, 255)) for v in data[i, 13:17]))
    g = gsplatnp.gs_read_file(p)
    assert g["format"] == "splat" and g["n_total"] == len(m)
    assert np.abs(g["xyz"] - m).max() == 0.0
    assert np.abs(g["rgb"] - rgb).max() < 1 / 255 + 1e-9
    with pytest.raises(ValueError):
        bad = str(tmp_path / "bad.splat")
        open(bad, "wb").write(b"\0" * 33)
        gsplatnp.gs_read_file(bad)


def test_old_point_reader_lost_the_3dgs_colours(tmp_path):
    """以前の経路(mesh.read_points)は 3DGS の PLY から色を取れない —— 専用の読み手が要った理由。"""
    import mesh
    data, *_ = _gaussians(n=50)
    p = str(tmp_path / "g.ply")
    _write_3dgs_ply(p, data, "binary_little_endian")
    assert mesh.read_points(p, with_colors=True)[1] is None


def test_classify_dropped_paths(tmp_path):
    from PIL import Image
    import imgio
    d = tmp_path / "imgs"
    d.mkdir()
    for k in range(3):
        imgio.save(str(d / ("a%d.png" % k)), np.full((8, 8), 40 * k, np.uint8))
    (d / "notes.txt").write_text("x")
    single = str(tmp_path / "one.gif")
    Image.fromarray(np.zeros((8, 8), np.uint8)).save(single)
    anim = str(tmp_path / "anim.gif")
    fr = [Image.fromarray(np.full((8, 8), v, np.uint8)) for v in (0, 120, 240)]
    fr[0].save(anim, save_all=True, append_images=fr[1:])
    np.save(str(tmp_path / "pts.npy"), np.random.rand(100, 3))
    np.save(str(tmp_path / "img.npy"), np.random.rand(16, 16))
    np.save(str(tmp_path / "vol.npy"), np.random.rand(8, 8, 8))
    paths = [str(d), single, anim, str(tmp_path / "s.py"), str(tmp_path / "p.json"), str(tmp_path / "g.splat"),
             str(tmp_path / "m.stl"), str(tmp_path / "c.mp4"), str(tmp_path / "pts.npy"), str(tmp_path / "img.npy"),
             str(tmp_path / "vol.npy"), str(tmp_path / "x.zip")]
    k = studio._classify_dropped_paths(paths)
    assert [os.path.basename(p) for p in k["images"]] == ["a0.png", "a1.png", "a2.png", "one.gif"]
    assert [os.path.basename(p) for p in k["videos"]] == ["anim.gif", "c.mp4"]
    assert [os.path.basename(p) for p in k["models3d"]] == ["g.splat", "m.stl", "pts.npy", "vol.npy"]
    assert [os.path.basename(p) for p in k["arrays"]] == ["img.npy"]
    assert k["scripts"] and k["pipelines"] and [os.path.basename(p) for p in k["other"]] == ["x.zip"]


_ERRORS = []


@pytest.fixture(autouse=True)
def _no_modal_dialogs(monkeypatch):
    """読み込みの失敗はモーダルの QMessageBox を開く —— offscreen では誰も閉じないのでテストが永久に止まる
    (2026-10-03、MJCF で 10 分止まった)。失敗は記録して、テストの表明で名指しする。"""
    _ERRORS.clear()
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda _parent, title, text: _ERRORS.append((title, text)))


def _drop_and_get_viewer(win, path):
    before = list(win._graphics_windows)
    win.drop_handler([path])
    new = [s for s in win._graphics_windows if s not in before]
    assert len(new) == 1, (path, _ERRORS)
    return new[0]._fs_viewer3d


def test_drop_3d_files_in_ascii_and_binary(tmp_path):
    """PLY / STL / PCD を ASCII とバイナリで書き、Studio に落とすと 3-D ビューアが同じ形で開く。3DGS は色つき。"""
    _app()
    import mesh
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    P = np.random.default_rng(3).random((60, 3))
    for binary in (False, True):
        tag = "bin" if binary else "asc"
        p = str(tmp_path / ("pts_%s.ply" % tag))
        mesh.write_points(p, P, binary=binary)
        v = _drop_and_get_viewer(win, p)
        assert v.info["kind"] == "points" and np.abs(v._P - P).max() < 1e-12
        V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
        F = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        for ext in (".ply", ".stl"):
            pm = str(tmp_path / ("tet_%s%s" % (tag, ext)))
            mesh.write_mesh(pm, V, F, binary=binary)
            v = _drop_and_get_viewer(win, pm)
            assert v.info["kind"] == "mesh", (pm, v.info)
    # PCD: ASCII と binary を素朴に書く
    for data_kind in ("ascii", "binary"):
        p = str(tmp_path / ("c_%s.pcd" % data_kind))
        hdr = ("# .PCD v0.7\nVERSION 0.7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\nWIDTH %d\nHEIGHT 1\n"
               "VIEWPOINT 0 0 0 1 0 0 0\nPOINTS %d\nDATA %s\n" % (len(P), len(P), data_kind))
        with open(p, "wb") as f:
            f.write(hdr.encode("ascii"))
            if data_kind == "ascii":
                f.write("".join("%r %r %r\n" % tuple(float(v) for v in r) for r in P.astype(np.float32)).encode())
            else:
                f.write(P.astype("<f4").tobytes())
        v = _drop_and_get_viewer(win, p)
        assert np.abs(v._P - P).max() < 1e-6, data_kind
    # 3DGS: ASCII も binary も、点は中心・色は SH DC(不透明度 5% 未満は落ちる)
    data, m, rgb, op = _gaussians(n=120, seed=4)
    for fmt in ("ascii", "binary_little_endian"):
        p = str(tmp_path / ("scene_%s.ply" % fmt))
        _write_3dgs_ply(p, data, fmt)
        v = _drop_and_get_viewer(win, p)
        keep = op >= 0.05
        assert v._colors is not None and len(v._P) == int(keep.sum())
        assert np.abs(v._colors - rgb[keep]).max() < 1e-5


def test_drop_python_script_opens_an_editor_tab_and_images_open_the_viewer(tmp_path):
    _app()
    import imgio
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    py = tmp_path / "hello.py"
    py.write_text("print('hi')\n", encoding="utf-8")
    win.drop_handler([str(py)])
    tabs = win._pyedit["tabs"]
    assert tabs.widget(tabs.currentIndex()).toPlainText() == "print('hi')\n"
    ed = tabs.widget(tabs.currentIndex())
    assert ed.on_drop_files is not None                       # 編集中のタブに落としても開く(パスを文字で貼らない)
    a = str(tmp_path / "a.png"); b = str(tmp_path / "b.png")
    imgio.save(a, np.full((10, 12), 50, np.uint8)); imgio.save(b, (np.arange(120).reshape(10, 12) * 2).astype(np.uint8))
    win.drop_handler([a, b])
    dlg = win._viewer_dlg
    assert dlg._list.count() == 2
    dlg._list.setCurrentRow(1)
    dlg._hover(3.0, 2.0)
    assert dlg._pixel.text().startswith("x=3  y=2") and "8-bit 54" in dlg._pixel.text()
    assert "12 × 10" in dlg._info.toPlainText()
    dlg._use()
    assert model.image.shape == (10, 12)


def test_viewer_headless_helpers():
    a = np.zeros((4, 5)); a[2, 3] = 0.5
    assert studio._viewer_pixel_text(a, 3.2, 1.8).startswith("x=3  y=2   value 0.5000")
    assert studio._viewer_pixel_text(a, 9, 9) == ""
    rgb = np.zeros((2, 2, 3)); rgb[0, 1] = (1, 0.5, 0)
    assert "R 1.0000  G 0.5000  B 0.0000" in studio._viewer_pixel_text(rgb, 1, 0)
    counts, edges = studio._viewer_histogram(rgb, 8)
    assert counts.shape == (3, 8) and counts.sum() == 12 and edges[0] == 0 and edges[-1] == 1
    assert studio._viewer_image_info(rgb)["channels"] == 3


# ── Physical AI 系(glTF / LAS・LAZ / MJCF / URDF)。任意の依存が無ければ飛ばす ─────────────────── #
MJCF = """<mujoco model="t">
  <worldbody>
    <body name="base" pos="0 0 0.5">
      <geom type="box" size="0.2 0.1 0.05"/>
      <body name="arm" pos="0.3 0 0"><geom type="sphere" size="0.05"/></body>
    </body>
  </worldbody>
</mujoco>
"""
URDF = """<?xml version="1.0"?>
<robot name="r">
  <link name="base"><visual><geometry><box size="0.4 0.2 0.1"/></geometry></visual>
    <collision><geometry><box size="0.4 0.2 0.1"/></geometry></collision>
    <inertial><mass value="1"/><inertia ixx="0.01" ixy="0" ixz="0" iyy="0.01" iyz="0" izz="0.01"/></inertial></link>
</robot>
"""


def test_robot_xml_kind_sniffs_the_root_element(tmp_path):
    a = tmp_path / "m.xml"; a.write_text(MJCF, encoding="utf-8")
    b = tmp_path / "r.xml"; b.write_text(URDF, encoding="utf-8")
    c = tmp_path / "o.xml"; c.write_text("<?xml version='1.0'?><!-- x --><svg/>", encoding="utf-8")
    assert studio._robot_xml_kind(str(a)) == "mjcf" and studio._robot_xml_kind(str(b)) == "urdf"
    assert studio._robot_xml_kind(str(c)) is None
    k = studio._classify_dropped_paths([str(a), str(b), str(c)])
    assert len(k["models3d"]) == 2 and [os.path.basename(p) for p in k["other"]] == ["o.xml"]


def test_drop_physical_ai_formats_opens_the_3d_viewer(tmp_path):
    _app()
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    import test_meshio_opt as TM                                    # 既存の glTF / LAS の fixture をそのまま使う
    if pytest.importorskip("pygltflib"):
        v = _drop_and_get_viewer(win, TM._save_glb(tmp_path))
        assert v.info["kind"] == "mesh" and np.allclose(v._V.min(0), TM.CUBE_V.min(0) + [10, 0, 0])
    if pytest.importorskip("laspy"):
        v = _drop_and_get_viewer(win, TM._write_las(tmp_path))
        assert v.info["kind"] == "points" and len(v._P) == len(TM.LAS_XYZ) and v._colors is not None
    pytest.importorskip("mujoco"); pytest.importorskip("open3d")
    p = tmp_path / "r.urdf"; p.write_text(URDF, encoding="utf-8")
    v = _drop_and_get_viewer(win, str(p))                          # .urdf(拡張子が .xml でない)もパスとして読む
    assert v.info["kind"] == "mesh" and np.allclose(np.ptp(v._V, axis=0), [0.4, 0.2, 0.1])
    # MJCF: 子の球は親(z 0.5)+ (0.3, 0, 0) にある —— 姿勢を MuJoCo が組み立てている
    p = tmp_path / "m2.xml"; p.write_text(MJCF, encoding="utf-8")
    v = _drop_and_get_viewer(win, str(p))
    assert abs(v._V[:, 0].max() - 0.35) < 1e-6 and abs(v._V[:, 2].max() - 0.55) < 1e-6


# ── 第 2 陣: BVH・イベントカメラ・SWC・Markdown / SVG ───────────────────────────────────────── #
BVH = """HIERARCHY
ROOT hip
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT spine
  {
    OFFSET 0 1 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 2 0
    }
  }
}
MOTION
Frames: 3
Frame Time: 0.0333333
0 0 0 0 0 0 0 0 0
5 0 0 90 0 0 0 0 0
0 0 0 90 0 0 90 0 0
"""


def test_bvh_forward_kinematics_matches_hand_computation(tmp_path):
    """根を Z まわりに 90° 回すと (0, 1, 0) の子は (−1, 0, 0)。子も 90° 回すと末端 (0, 2, 0) は 180° 回って (−1, −2, 0)。"""
    import motionio
    p = tmp_path / "t.bvh"; p.write_text(BVH, encoding="ascii")
    b = motionio.read_bvh(str(p))
    assert b["names"] == ["hip", "spine", "spine_end"] and b["parents"].tolist() == [-1, 0, 1]
    P = b["positions"]
    assert np.allclose(P[0], [[0, 0, 0], [0, 1, 0], [0, 3, 0]])
    assert np.allclose(P[1], [[5, 0, 0], [4, 0, 0], [2, 0, 0]])
    assert np.allclose(P[2], [[0, 0, 0], [-1, 0, 0], [-1, -2, 0]])
    bad = tmp_path / "bad.bvh"; bad.write_text(BVH.replace("0 0 0 90 0 0 90 0 0", "0 0 0 90"), encoding="ascii")
    with pytest.raises(ValueError):
        motionio.read_bvh(str(bad))


@pytest.mark.parametrize("layout", ["x y t p", "x,y,p,t", "t,x,y,p header"])
def test_event_columns_are_found_by_name_or_by_content(tmp_path, layout):
    import motionio
    rng = np.random.default_rng(0)
    n = 500
    x, y = rng.integers(0, 34, n), rng.integers(0, 30, n)
    t, p = np.sort(rng.integers(0, 300000, n)), rng.integers(0, 2, n)
    f = tmp_path / "ev.csv"
    if layout == "x y t p":
        np.savetxt(f, np.column_stack([x, y, t, p]), fmt="%d")
    elif layout == "x,y,p,t":
        np.savetxt(f, np.column_stack([x, y, p, t]), fmt="%d", delimiter=",")
    else:
        np.savetxt(f, np.column_stack([t, x, y, p]), fmt="%d", delimiter=",", header="t,x,y,p", comments="")
    e = motionio.read_events(str(f))
    assert (e["x"] == x).all() and (e["y"] == y).all() and (e["t"] == t).all()
    assert (e["p"] == np.where(p > 0, 1, -1)).all() and e["guessed"] == ("header" not in layout)
    fr = motionio.events_to_frames(e, 10)
    assert fr.shape == (10, 30, 34) and fr.sum() == np.where(p > 0, 1, -1).sum()   # 1 個も落とさない
    assert studio._events_kind(str(f))


def test_drop_wave2_bvh_events_swc_and_documents(tmp_path):
    _app()
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    p = tmp_path / "walk.bvh"; p.write_text(BVH, encoding="ascii")
    v = _drop_and_get_viewer(win, str(p))
    assert len(v._P) == 9 and v._colors is not None                  # 3 関節 × 3 コマ、時間の色
    swc = tmp_path / "n.swc"
    swc.write_text("# soma + 2\n1 1 0 0 0 1 -1\n2 3 1 0 0 0.5 1\n3 3 2 1 0 0.5 2\n", encoding="ascii")
    v = _drop_and_get_viewer(win, str(swc))
    assert np.allclose(v._P, [[0, 0, 0], [1, 0, 0], [2, 1, 0]])
    rng = np.random.default_rng(1)
    ev = tmp_path / "ev.txt"
    np.savetxt(ev, np.column_stack([rng.integers(0, 20, 300), rng.integers(0, 10, 300),
                                    np.sort(rng.integers(0, 9000, 300)), rng.integers(0, 2, 300)]), fmt="%d")
    win.drop_handler([str(ev)])
    clip = win._video_cube_dialog._state["clip"]
    assert clip.shape == (48, 10, 20) and 0.0 <= clip.min() and clip.max() <= 1.0, (clip.shape, _ERRORS)
    md = tmp_path / "r.md"; md.write_text("# Title\n\n* one\n* two\n\n```python\nx = 1\n```\n", encoding="utf-8")
    win.drop_handler([str(md)])
    assert "Title" in win._last_document._browser.toPlainText() and not _ERRORS
    svg = tmp_path / "c.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="20" height="20" '
                   'fill="#ff0000"/></svg>', encoding="utf-8")
    win.drop_handler([str(svg)])
    img = win._last_document._image
    left = QtGui_pixel(img, 0.25, 0.5); right = QtGui_pixel(img, 0.75, 0.5)
    assert left[0] > 200 and left[1] < 60 and right == (255, 255, 255), (left, right)


def QtGui_pixel(img, fx, fy):
    c = img.pixelColor(int(img.width() * fx), int(img.height() * fy))
    return (c.red(), c.green(), c.blue())


# ── 第 3 陣: 音声(波形 + スペクトログラム)─────────────────────────────────────────────────── #
def _write_wav(path, x, rate):
    import wave
    a = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(a.tobytes())


def test_audio_view_data_puts_a_tone_at_its_frequency():
    """1 kHz の正弦波: スペクトログラムの最大は 1 kHz の行(窓の分解能 rate/win の範囲)、包絡は ±振幅。"""
    rate = 16000
    t = np.arange(rate) / rate
    d = studio._audio_view_data(0.5 * np.sin(2 * np.pi * 1000 * t), rate)
    f_peak = d["freqs"][np.argmax(d["spec_db"].mean(axis=1))]
    assert abs(f_peak - 1000) <= rate / 1024
    assert abs(d["env_max"].max() - 0.5) < 1e-3 and abs(d["env_min"].min() + 0.5) < 1e-3
    assert d["spec_db"].max() == 0.0 and d["spec_db"].min() >= -80.0
    assert d["info"]["duration"] == "1.000 s"


def test_drop_wav_opens_the_audio_window_and_feeds_the_pipeline(tmp_path):
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    rate = 8000
    t = np.arange(rate // 2) / rate
    chirp = 0.4 * np.sin(2 * np.pi * (200 * t + 3000 * t ** 2))      # 200 Hz → 3.2 kHz
    p = tmp_path / "chirp.wav"
    _write_wav(p, chirp, rate)
    win.drop_handler([str(p)])
    dlg = win._last_audio
    assert dlg is not None and not _ERRORS, _ERRORS
    spec = dlg._data["spec_db"]
    early = dlg._data["freqs"][np.argmax(spec[:, 1])]; late = dlg._data["freqs"][np.argmax(spec[:, -2])]
    assert early < 800 < 2000 < late                                  # チャープは時間とともに上がる(0.4 s で 2.6 kHz)
    dlg._use()
    assert model.image.shape == spec.shape and 0.0 <= model.image.min() and model.image.max() <= 1.0
    bad = tmp_path / "x.mp3"; bad.write_bytes(b"\0" * 64)
    win.drop_handler([str(bad)])
    assert _ERRORS and "soundfile" in _ERRORS[-1][1]                  # 読めない時は入れ方を名指し


# ── 第 3 陣: ロボットのモデル + qpos 軌跡の再生 ───────────────────────────────────────────────── #
ARM = """<mujoco model="arm">
  <worldbody>
    <body name="link" pos="0 0 0">
      <joint name="hinge" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.05" pos="1 0 0"/>
    </body>
  </worldbody>
</mujoco>
"""


def test_scene_mesh_follows_qpos():
    """ヒンジを z まわりに 90° 回すと、(1, 0, 0) の球は (0, 1, 0) へ。メッシュの中心で確かめる(手計算)。"""
    pytest.importorskip("mujoco"); pytest.importorskip("open3d")
    import mujoco
    import sim_source
    src = sim_source.MuJoCo(mujoco.MjModel.from_xml_string(ARM))
    for q, c in ((0.0, (1, 0, 0)), (np.pi / 2, (0, 1, 0)), (np.pi, (-1, 0, 0))):
        V, F = src.scene_mesh([q])
        assert np.allclose(V.mean(axis=0), c, atol=1e-6), (q, V.mean(axis=0))
    with pytest.raises(ValueError):
        src.scene_mesh([0.0, 1.0])                                  # nq と違う長さ
    src.close()


def test_drop_model_with_qpos_plays_the_trajectory(tmp_path):
    pytest.importorskip("mujoco"); pytest.importorskip("open3d")
    _app()
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    xml = tmp_path / "arm.xml"; xml.write_text(ARM, encoding="utf-8")
    q = np.linspace(0, np.pi, 20)[:, None]                            # (T, nq) = (20, 1)
    qp = tmp_path / "arm_qpos.npy"; np.save(qp, q)
    win.drop_handler([str(xml), str(qp)])
    dlg = win._last_robot_player
    assert dlg is not None and not _ERRORS, _ERRORS
    assert np.allclose(dlg._last_V.mean(axis=0), (1, 0, 0), atol=1e-6)
    dlg._slider.setValue(19)
    assert np.allclose(dlg._last_V.mean(axis=0), (-1, 0, 0), atol=1e-6)
    bad = tmp_path / "bad.npy"; np.save(bad, np.zeros((5, 3)))
    win.drop_handler([str(xml), str(bad)])
    assert _ERRORS and "nq" in _ERRORS[-1][1]                           # 列の数が合わなければ名指しで断る


# ── ヘルプの「開けるファイル」表(2026-10-03、ユーザー「ヘルプにも機能として書いておいたほうがいい」)──────── #
def test_help_table_lists_every_extension_studio_opens():
    """表は拡張子の定数から組み立てる —— 定数に足したのに表から漏れた拡張子が 1 つでもあれば落ちる。"""
    rows = studio._drop_format_rows()
    listed = {e for _k, _w, exts, _n in rows for e in exts}
    every = set(studio.IMAGE_FILE_EXTS + studio.MODEL3D_FILE_EXTS + studio.VIDEO_FILE_EXTS
                + studio.DOCUMENT_FILE_EXTS + studio.AUDIO_FILE_EXTS) | {".py", ".pyw", ".json", ".xml", ".npy"}
    assert len(every) > 60
    assert every - listed == set(), every - listed
    cats = set(studio._classify_dropped_paths([])) - {"other"}
    assert len(cats) == 9
    assert cats - {k for k, *_ in rows} == set()                      # 振り分けの全分類に行がある


def test_help_table_rows_agree_with_the_classifier(tmp_path):
    """表が「3-D ビューアで開く」と言う拡張子は、本当に 3-D に振り分けられる(中身で見分ける物は除く)。"""
    sniffed = {"events", "arrays", "player"}                          # 中身・組み合わせで決まる行
    checked = 0
    for key, _what, exts, _note in studio._drop_format_rows():
        if key in sniffed:
            continue
        for e in exts:
            if e in (".gif", ".xml"):                                 # 1 コマか / 根の要素で決まる
                continue
            got = studio._classify_dropped_paths([str(tmp_path / ("f" + e))])
            assert got[key] == [str(tmp_path / ("f" + e))], (e, key, {k: v for k, v in got.items() if v})
            checked += 1
    assert checked > 50


def test_help_menu_opens_the_formats_table_in_the_ui_language():
    _app()
    win, _model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    texts = [a.text() for a in win._menus["help"].actions()]
    assert "Files you can open (drag & drop)…" in texts
    dlg = win._show_drop_formats()
    html = dlg._browser.toPlainText()
    assert ".splat" in html and ".bvh" in html and "binary_compressed" in html
    win._apply_language("ja")
    try:
        assert "開けるファイル(ドラッグ・アンド・ドロップ)…" in [a.text() for a in win._menus["help"].actions()]
        txt = win._show_drop_formats()._browser.toPlainText()
        assert "画像ビューア" in txt and "ASCII とバイナリの両方" in txt
    finally:
        win._apply_language("en")


def test_quick_guide_mentions_drag_and_drop_in_every_language():
    names = {"en": "Files you can open"}
    for lang, guide in studio.HELP_I18N.items():
        assert ".splat" in guide and "MJCF" in guide, lang
        want = names.get(lang) or studio.STRINGS_I18N["Files you can open"][lang]
        assert want in guide, lang
    assert len(studio.HELP_I18N) == 6
