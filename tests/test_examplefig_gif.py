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


def test_a_still_sequence_stays_still(_fresh):
    """★同じ絵を 5 コマ渡したら、GIF の中でも 5 コマとも同じであること。

    コマごとに正規化していると、雑音の最大値が動くだけで明るさが揺れる。
    """
    rng = np.random.default_rng(0)
    base = rng.random((24, 32)) * 0.4 + 0.3
    frames = [base.copy() for _ in range(5)]
    frames[2][0, 0] += 3.0                      # ★1 コマだけ外れ値(尺度を動かす罠)
    p = figs.save_gif("still", frames, fps=5)
    assert p is not None and p.suffix == ".gif"
    im = _open(p)
    assert im.n_frames == 5
    seen = []
    for i in range(5):
        im.seek(i)
        seen.append(np.asarray(im.convert("L"), dtype=np.int16))
    # 外れ値を仕込んだコマ以外は、互いに完全に同じ(尺度が 1 つだから)
    for k in (1, 3, 4):
        assert np.array_equal(seen[0], seen[k]), k


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
    on_disk = json.loads(io.open(os.path.join(str(_fresh), "figures.json"),
                                 encoding="utf-8").read())
    assert on_disk == man                        # figures.json と一致している


def test_it_does_nothing_without_a_target_dir(monkeypatch):
    monkeypatch.delenv("FULLSEYE_FIGURE_DIR", raising=False)
    figs.reset()
    assert figs.save_gif("nowhere", [np.zeros((4, 4))]) is None
    assert figs.errors() == []                   # 設定が無いのはエラーではない
