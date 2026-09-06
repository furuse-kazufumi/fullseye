# -*- coding: utf-8 -*-
"""例が図を吐く仕組み(`examplefig`)の門。

2026-09-06、ユーザー 3 連の指摘で入れた層:
「Studio 上で動くような PoC になってる?」/「表は Excel にコピーできるといいね」/
「画像にはクリップボードにコピーする機能があるといいね(Windows)」。

ここで守るのは 3 つ:

1. **環境変数が無いときは完全に無処理**。既存 31 本の PoC の数値も速度も
   1 ビットも変えない、というのがこの設計の前提。
2. 環境変数があるときは **PNG + figures.json** が出る。表なら **CSV(BOM つき)
   と TSV** も出る(Excel へ貼るのは TSV、開くのは CSV)。
3. 図の失敗が**例を落とさない**。数値を出すのが例の仕事で、絵はおまけ。
   ただし失敗は :func:`examplefig.errors` に残す(黙って消さない)。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import examplefig

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    examplefig.reset()
    monkeypatch.delenv(examplefig.ENV_DIR, raising=False)
    yield
    examplefig.reset()


def _ramp(n=48):
    return np.linspace(0.0, 1.0, n)[None, :] * np.ones((n, 1))


# --------------------------------------------------------------------------- #
# 1. 既定では何もしない                                                         #
# --------------------------------------------------------------------------- #
def test_no_env_means_no_output_and_no_work(tmp_path):
    """環境変数が無ければ ``None`` を返し、ファイルを 1 つも作らない。"""
    assert examplefig.target_dir() is None
    assert examplefig.enabled() is False
    assert examplefig.save("x", _ramp()) is None
    assert examplefig.save_grid("g", [_ramp(), _ramp()]) is None
    assert examplefig.save_plot("p", [("a", [0, 1], [0, 1])]) is None
    assert examplefig.save_table("t", ["a"], [["1"]]) is None
    assert examplefig.manifest() == []
    assert list(tmp_path.iterdir()) == []


def test_empty_env_value_is_also_off(monkeypatch):
    """空文字は「設定されていない」と同じ扱い(誤って CWD に書かない)。"""
    monkeypatch.setenv(examplefig.ENV_DIR, "   ")
    assert examplefig.target_dir() is None


# --------------------------------------------------------------------------- #
# 2. 環境変数があるときの出力                                                   #
# --------------------------------------------------------------------------- #
def test_single_figure_writes_png_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    p = examplefig.save("ramp", _ramp(), "説明の文")
    assert p is not None and p.exists() and p.name == "01_ramp.png"
    man = json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))
    assert man[0]["name"] == "ramp" and man[0]["caption"] == "説明の文"


def test_png_is_not_black(tmp_path, monkeypatch):
    """★中身が黒くないこと。

    `colorize_depth` は **float [0,1]** を返すので `np.asarray(..., np.uint8)`
    で受けると 0.x が全部 0 に落ちて真っ黒になる。実際に踏んだ(2026-09-06)。
    """
    import cv2

    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    p = examplefig.save("ramp", _ramp())
    img = cv2.imread(str(p))
    assert img is not None
    assert img.mean() > 20.0, "真っ黒に近い(平均 %.1f)" % img.mean()
    assert img.max() > 200, "明るい画素が無い"


def test_grid_and_plot_and_table_all_write(tmp_path, monkeypatch):
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    x = np.linspace(0.0, 6.0, 40)
    assert examplefig.save_grid("g", [_ramp(), 1 - _ramp()], ["左", "右"],
                                title="題") is not None
    assert examplefig.save_plot("p", [("sin", x, np.sin(x)), ("cos", x, np.cos(x)),
                                      ("半分", x, 0.5 * np.sin(x))],
                                title="題") is not None
    assert examplefig.save_table("t", ["a", "b"], [["1", "2"]]) is not None
    assert examplefig.errors() == [], examplefig.errors()


def test_plot_colour_roles_are_valid_for_five_series(tmp_path, monkeypatch):
    """★5 本まで色役が実在すること。

    最初の版は 3 本目に ``"accent"`` を使っていて、annotate の配色表に
    その役が無いため 3 本以上のグラフが**全部**黙って落ちていた。
    """
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    x = np.linspace(0.0, 1.0, 10)
    series = [("s%d" % k, x, x * k) for k in range(5)]
    assert examplefig.save_plot("five", series) is not None
    assert examplefig.errors() == [], examplefig.errors()


# --------------------------------------------------------------------------- #
# 3. Excel へ持ち出す                                                           #
# --------------------------------------------------------------------------- #
def test_table_also_writes_csv_and_tsv(tmp_path, monkeypatch):
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    examplefig.save_table("depth", ["深さ mm", "推定 mm"], [["0.5", "0.48"],
                                                            ["1.0", "0.97"]])
    csv = tmp_path / "01_depth.csv"
    tsv = tmp_path / "01_depth.tsv"
    assert csv.exists() and tsv.exists()
    # Excel が cp932 と誤読しないよう BOM を付ける。
    assert csv.read_bytes().startswith(b"\xef\xbb\xbf")
    lines = tsv.read_text(encoding="utf-8").strip().split("\n")
    assert lines[0].split("\t") == ["深さ mm", "推定 mm"]
    assert lines[1].split("\t") == ["0.5", "0.48"]
    man = json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))
    assert man[0]["csv"] == "01_depth.csv" and man[0]["tsv"] == "01_depth.tsv"


def test_only_tables_get_csv(tmp_path, monkeypatch):
    """画像の図に CSV は付かない(付けると Studio が空の表を出す)。"""
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    examplefig.save("ramp", _ramp())
    man = json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))
    assert "csv" not in man[0] and "tsv" not in man[0]


# --------------------------------------------------------------------------- #
# 4. 失敗しても例を落とさない                                                   #
# --------------------------------------------------------------------------- #
def test_bad_shape_is_recorded_not_raised(tmp_path, monkeypatch):
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    assert examplefig.save("weird", np.zeros((2, 3, 4, 5))) is None
    assert any("weird" in e for e in examplefig.errors())


def test_figure_cap_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    monkeypatch.setattr(examplefig, "MAX_FIGURES", 2)
    for k in range(4):
        examplefig.save("f%d" % k, _ramp(16))
    assert len(examplefig.manifest()) == 2
    assert any("上限" in e for e in examplefig.errors())


# --------------------------------------------------------------------------- #
# 5. 実際の PoC が図を出す(端から端まで)                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("script", ["poc_dic_strain.py"])
def test_a_real_poc_emits_figures_only_when_asked(tmp_path, script):
    """★配線が生きていること。PoC を**別プロセスで 2 回**走らせて比べる。

    1 回目は環境変数なし(図が出ないこと)、2 回目はあり(出ること)。
    どちらも exit 0 —— 図の有無で例の合否が変わらないのが約束。
    """
    path = ROOT / "examples" / script
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT))
    env.pop(examplefig.ENV_DIR, None)
    off = tmp_path / "off"
    off.mkdir()
    r1 = subprocess.run([sys.executable, str(path)], env=env, cwd=str(off),
                        capture_output=True, timeout=600)
    assert r1.returncode == 0, r1.stderr.decode("utf-8", "replace")[-2000:]
    assert not list(off.iterdir()), "環境変数が無いのにファイルを作った"

    on = tmp_path / "on"
    env[examplefig.ENV_DIR] = str(on)
    r2 = subprocess.run([sys.executable, str(path)], env=env, cwd=str(tmp_path),
                        capture_output=True, timeout=600)
    assert r2.returncode == 0, r2.stderr.decode("utf-8", "replace")[-2000:]
    pngs = sorted(p.name for p in on.glob("*.png"))
    assert pngs, "図が 1 枚も出ていない"
    assert (on / "figures.json").exists()
    assert b"\xe5\x9b\xb3\xe3\x81\xae\xe6\x9b\xb8\xe3\x81\x8d\xe5\x87\xba" \
        not in r2.stdout, "図の書き出しで失敗している: %s" % (
            r2.stdout.decode("utf-8", "replace")[-1500:])


# --------------------------------------------------------------------------- #
# 6. Studio 側 —— 図を並べ、右クリックから持ち出せる                             #
# --------------------------------------------------------------------------- #
def test_studio_figures_tab_lists_and_offers_copy(tmp_path, monkeypatch):
    """Figures タブが図を並べ、**右クリックの品目**が揃っていること。

    この repo の Studio UI 規約 ——「表示系は右クリックからも一通り」。
    ボタンだけ足して右クリックを忘れる、が起きないように品目を数える。
    """
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtGui, QtWidgets

    import studio

    monkeypatch.setenv(examplefig.ENV_DIR, str(tmp_path))
    examplefig.save("ramp", _ramp(), "ただの画像")
    examplefig.save_table("depth", ["深さ", "推定"], [["0.5", "0.48"]], title="表")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    area, show = studio._figures_tab(QtWidgets, QtCore, QtGui)
    n = show(str(tmp_path))
    assert n == 2

    labels = area.findChildren(QtWidgets.QLabel)
    pics = [w for w in labels if w.pixmap() is not None and not w.pixmap().isNull()]
    assert len(pics) == 2, "図が 2 枚とも表示されていない"
    for w in pics:
        assert w.contextMenuPolicy() == QtCore.Qt.CustomContextMenu, \
            "図に右クリックが付いていない"

    texts = [b.text() for b in area.findChildren(QtWidgets.QPushButton)]
    assert texts.count("画像をコピー") == 2
    assert "Excel 用にコピー" in texts and "CSV を保存…" in texts
    app.processEvents()


def test_studio_figures_tab_says_so_when_there_are_none(tmp_path):
    """図を出さない例では**空白ではなく理由**を出すこと。"""
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtGui, QtWidgets

    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    area, show = studio._figures_tab(QtWidgets, QtCore, QtGui)
    assert show(str(tmp_path)) == 0
    said = [w.text() for w in area.findChildren(QtWidgets.QLabel) if w.text()]
    assert any("図を出しません" in t for t in said), said
    app.processEvents()
