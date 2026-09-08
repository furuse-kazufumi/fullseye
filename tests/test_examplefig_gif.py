# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""動く図(`examplefig.save_gif`)の門(著者の要望 2026-09-08)。

    「そういうものは AnimationGIF とかでも結果表示できるよね。」

★一番の落とし穴は**コマごとに別の尺度で正規化すること**。`_to_rgb8` は 1 枚
ずつ min-max で伸ばすので、そのまま並べると**中身が動いていなくても明るさが
ちらつき**、逆に本当に動いた量が見えなくなる([[feedback_ran_is_not_meaningful_output]]
の「尺度違い」)。ここでは「動いていないものは動いて見えない」ことを画素で見る。
"""
import io
import json
import os

import numpy as np
import pytest

import examplefig as figs


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_FIGURE_DIR", str(tmp_path))
    figs.reset()
    yield tmp_path
    figs.reset()


def _open(path):
    from PIL import Image
    return Image.open(str(path))


def test_every_frame_shares_one_scale(_fresh):
    """★尺度は全コマで 1 つ。1 枚だけ外れ値が入っても、他のコマは動かない。

    コマごとに min-max で伸ばしていると、外れ値のあるコマが混ざった瞬間に
    **他の全コマの明るさが変わる**(中身は何も動いていないのに)。
    """
    rng = np.random.default_rng(0)
    base = rng.random((24, 32)) * 0.4 + 0.3
    frames = []
    for i in range(5):
        f = base.copy()
        f[0, 0] = 0.3 + 0.02 * i          # コマごとに 1 画素だけ違う(畳ませない)
        frames.append(f)
    frames[2][23, 31] += 3.0              # ★1 コマだけ外れ値(尺度を動かす罠)
    p = figs.save_gif("scale", frames, fps=5)
    assert p is not None and p.suffix == ".gif"
    im = _open(p)
    assert im.n_frames == 5
    seen = []
    for i in range(5):
        im.seek(i)
        seen.append(np.asarray(im.convert("L"), dtype=np.int16))
    body = np.s_[1:23, 1:31]              # 仕掛けた 2 画素を外した本体
    for k in (1, 3, 4):
        assert np.array_equal(seen[0][body], seen[k][body]), k


def test_identical_frames_are_merged_by_pillow_and_the_ledger_says_so(_fresh):
    """★Pillow は**直前と同じコマを 1 枚に畳む**(その分の時間は前に足される)。

    畳まれること自体は害が無い(動きの速さは変わらない)が、「72 コマの GIF」と
    言いながら中身が 40 コマ、を黙って通さないために**両方**記録する。
    """
    figs.save_gif("still", [np.zeros((8, 8))] * 5, fps=5)
    m = figs.manifest()[-1]
    assert m["frames"] == 5
    assert m["frames_written"] < 5              # 実測: 畳まれる
    assert _open(figs.target_dir() / m["file"]).n_frames == m["frames_written"]


def test_frames_of_different_sizes_are_refused_not_padded(_fresh):
    """★GIF は黙って詰める。ここで止めないと、後半のコマだけ左上に寄る。"""
    assert figs.save_gif("ragged", [np.zeros((8, 8)), np.zeros((8, 9))]) is None
    assert any("そろっていない" in e for e in figs.errors()), figs.errors()


def test_an_empty_or_too_long_sequence_is_refused(_fresh):
    assert figs.save_gif("none", []) is None
    assert figs.save_gif("many", [np.zeros((4, 4))] * (figs.MAX_GIF_FRAMES + 1)) is None
    assert figs.save_gif("badfps", [np.zeros((4, 4))] * 2, fps=0) is None
    assert len(figs.errors()) == 3


def test_the_manifest_records_it_as_animated(_fresh):
    figs.save("still_one", np.zeros((8, 8)))
    figs.save_gif("moving", [np.zeros((8, 8)), np.ones((8, 8))], fps=4)
    man = figs.manifest()
    assert [m["file"] for m in man] == ["01_still_one.png", "02_moving.gif"]
    assert man[0].get("animated") is None and man[1]["animated"] is True
    assert man[1]["frames"] == 2 and man[1]["fps"] == 4.0
    assert man[1]["frames_written"] == 2      # 中身が違うので畳まれない
    on_disk = json.loads(io.open(os.path.join(str(_fresh), "figures.json"),
                                 encoding="utf-8").read())
    assert on_disk == man                        # figures.json と一致している


def test_it_does_nothing_without_a_target_dir(monkeypatch):
    monkeypatch.delenv("FULLSEYE_FIGURE_DIR", raising=False)
    figs.reset()
    assert figs.save_gif("nowhere", [np.zeros((4, 4))]) is None
    assert figs.errors() == []                   # 設定が無いのはエラーではない
