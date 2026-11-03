# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ocrclassic の試験 —— 真値は描画側(内蔵書体の設計と描いた字列)にあり、認識の式とは独立。

Tests for ocrclassic. The truth is the rendered string and the rendered boxes (independent of
the recognition formula). Measured rates are printed (``-s`` to see them) so that the honest
numbers stay visible next to the asserted floors.

乱数種は開発用の掃引(1000, 2000, 11)と重ならないものを使う(定数をこの試験で選んでいない)。
Seeds are disjoint from the development sweep seeds used to choose the reject constants.
"""
from __future__ import annotations

import time

import numpy as np
import pytest
from scipy import ndimage

import ocrclassic as oc

FONTS = ("dot5x7", "stroke")


@pytest.fixture(scope="module")
def models():
    """両書体の模型(学習は決定的なので 1 回だけ)。/ One model per font (training is deterministic)."""
    return {f: oc.ocr_train(f) for f in FONTS}


def _rand_text(rng, lo=4, hi=12, alphabet=oc.CHARSET):
    n = int(rng.integers(lo, hi + 1))
    return "".join(rng.choice(list(alphabet), n))


def _tot():
    return {"correct": 0, "substituted": 0, "rejected": 0, "inserted": 0, "deleted": 0,
            "n_true": 0}


def _add(tot, sc):
    for k in tot:
        tot[k] += sc[k]


def _rates(tot):
    n = max(tot["n_true"], 1)
    return {k: round(v / n, 4) for k, v in tot.items() if k != "n_true"}


def _degraded(font, text, h, blur, noise, rng):
    img = oc.ocr_render_text(text, font, char_height_px=h)["image"]
    if blur > 0:
        img = ndimage.gaussian_filter(img, blur * h, mode="nearest")
    if noise > 0:
        img = img + rng.normal(0.0, noise, img.shape)
    return img


def _iou(a, b):
    r0, c0 = max(a[0], b[0]), max(a[1], b[1])
    r1, c1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, r1 - r0) * max(0, c1 - c0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# --------------------------------------------------------------------------- #
# 書体と描画 / Fonts and rendering                                             #
# --------------------------------------------------------------------------- #

def test_fonts_cover_charset_and_designs():
    for name in FONTS:
        f = oc.ocr_font(name)
        assert f["charset"] == oc.CHARSET
        assert set(f["glyphs"]) == set(oc.CHARSET)
    dot = oc.ocr_font("dot5x7")
    assert len(dot["glyphs"]) == len(oc.CHARSET)
    for c, bm in dot["glyphs"].items():
        assert bm.shape == (7, 5) and bm.dtype == np.uint8 and bm.any(), c
    # 設計どうしが全部違う(紛らわしい対も含めて)/ all dot designs are distinct
    flat = {c: tuple(bm.ravel()) for c, bm in dot["glyphs"].items()}
    assert len(set(flat.values())) == len(flat)


def test_render_truth_boxes_and_value_range():
    r = oc.ocr_render_text("LOT-2026", "dot5x7", char_height_px=24)
    img = r["image"]
    assert img.ndim == 2 and np.isfinite(img).all()
    assert img.min() >= 0.0 and img.max() <= 1.0
    assert len(r["boxes"]) == 8
    # 余白 ~1 字高 / margin of about one char height
    assert min(b[0] for b in r["boxes"]) >= 23 and min(b[1] for b in r["boxes"]) >= 23
    # 全高の字のインクの縦幅 = 字高(±1 px)/ full-height glyph ink extent equals char height
    b = r["boxes"][0]                                        # 'L'
    assert abs((b[2] - b[0]) - 24) <= 1
    # 地 0.9、インク 0.1 / background and ink levels
    assert abs(float(np.median(img)) - 0.9) < 1e-9
    assert img.min() == pytest.approx(0.1, abs=0.02)


# --------------------------------------------------------------------------- #
# きれいな印字は全部読める / Clean prints are read exactly                      #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("font", FONTS)
def test_clean_read_100_random_strings(models, font):
    rng = np.random.default_rng(424242)
    tot = _tot()
    wrong = []
    for _ in range(100):
        text = _rand_text(rng)
        h = int(rng.integers(16, 41))
        out = oc.ocr_read_line(oc.ocr_render_text(text, font, char_height_px=h)["image"],
                               models[font])
        _add(tot, oc.ocr_score(out["text"], text))
        if out["text"] != text:
            wrong.append((text, out["text"], h))
    print(f"\n[clean {font}] {tot['n_true']} chars: {_rates(tot)}")
    assert not wrong, wrong[:5]


@pytest.mark.parametrize("font", FONTS)
def test_segmentation_matches_truth_boxes(font):
    rng = np.random.default_rng(777)
    ious = []
    for _ in range(40):
        text = _rand_text(rng)
        h = int(rng.integers(16, 41))
        r = oc.ocr_render_text(text, font, char_height_px=h)
        seg = oc.ocr_segment_line(r["image"])                # dot_font 自動判定 / auto-detect
        assert seg["dot_font"] == (font == "dot5x7")
        assert len(seg["boxes"]) == len(r["boxes"]), (text, h)
        for a, b in zip(seg["boxes"], r["boxes"]):
            ious.append(_iou(a, b))
    ious = np.asarray(ious)
    print(f"\n[seg {font}] IoU min {ious.min():.3f} median {np.median(ious):.3f} (n={ious.size})")
    assert ious.min() > 0.7


# --------------------------------------------------------------------------- #
# 字種外は棄却 / Out-of-charset glyphs are rejected, not misread                 #
# --------------------------------------------------------------------------- #

# 試験の中で手で作った字種外の字(設計は試験側の真値)/ hand-made out-of-charset glyphs
_HASH_DOT = [" # # ", " # # ", "#####", " # # ", "#####", " # # ", " # # "]
_HASH_STROKE = [[(1.3, 0), (1.3, 6)], [(2.7, 0), (2.7, 6)], [(0, 2), (4, 2)], [(0, 4), (4, 4)]]


def _font_with_hash(font):
    f = oc.ocr_font(font)
    if font == "dot5x7":
        f["glyphs"]["#"] = np.array([[1 if c == "#" else 0 for c in row] for row in _HASH_DOT],
                                    np.uint8)
    else:
        f["glyphs"]["#"] = _HASH_STROKE
    f["charset"] = f["charset"] + "#"
    return f


def _slot_outcome(out, cell, h):
    """真値の字の枠 cell (c0, c1) に重なる読みの字の結果。/ outcome of the read glyph at a cell."""
    hits = [c for c in out["chars"] if min(c["box"][3], cell[1]) - max(c["box"][1], cell[0])
            > 0.3 * (cell[1] - cell[0])]
    if not hits:
        return "dropped"
    return "rejected" if all(c["label"] == "?" for c in hits) else "misread"


@pytest.mark.parametrize("font", FONTS)
def test_reject_hash_glyph(models, font):
    f = _font_with_hash(font)
    rng = np.random.default_rng(31337)
    res = {"rejected": 0, "misread": 0, "dropped": 0}
    for _ in range(40):
        a, b = _rand_text(rng, 2, 4), _rand_text(rng, 2, 4)
        h = int(rng.integers(16, 41))
        r = oc.ocr_render_text(a + "#" + b, f, char_height_px=h)
        out = oc.ocr_read_line(r["image"], models[font])
        cl, cr = r["cells"][len(a)]
        res[_slot_outcome(out, (cl, cr), h)] += 1
        # 他の字は正しく読めている / the in-charset neighbours are still read
        others = [c["label"] for c in out["chars"]]
        assert len(others) == len(a) + 1 + len(b)
    n = sum(res.values())
    print(f"\n[reject '#' {font}] {res} -> reject rate {res['rejected'] / n:.3f}")
    assert res["rejected"] / n >= 0.9


def _random_blob(rng, hh, ww):
    """手で作るなめらかな乱数の塊(字高 x 字幅の枠に、面積 25〜60 %)。"""
    for _ in range(100):
        field = ndimage.gaussian_filter(rng.normal(size=(hh, ww)), 0.18 * hh)
        yy, xx = np.mgrid[0:hh, 0:ww]
        field = field - 0.6 * field.std() * (((yy - hh / 2) / (hh / 2)) ** 2
                                             + ((xx - ww / 2) / (ww / 2)) ** 2)
        t = np.quantile(field, 0.6)
        blob = (field > t).astype(float)
        lab, n = ndimage.label(blob)
        if n == 0:
            continue
        sizes = np.bincount(lab.ravel())[1:]
        blob = (lab == 1 + int(np.argmax(sizes))).astype(float)
        if 0.25 <= blob.mean() <= 0.6:
            return blob
    raise RuntimeError("could not make a blob")


@pytest.mark.parametrize("font", FONTS)
def test_reject_random_blob(models, font):
    rng = np.random.default_rng(2718)
    res = {"rejected": 0, "misread": 0, "dropped": 0}
    for _ in range(40):
        a, b = _rand_text(rng, 2, 4), _rand_text(rng, 2, 4)
        h = int(rng.integers(16, 41))
        r = oc.ocr_render_text(a + "-" + b, font, char_height_px=h)
        img = r["image"].copy()
        cl, cr = r["cells"][len(a)]
        lb = r["line_box"]
        c0, c1 = int(np.floor(cl)), int(np.ceil(cr))
        img[lb[0]:lb[2], c0:c1] = 0.9                         # '-' を消す / erase the '-'
        blob = _random_blob(rng, lb[2] - lb[0], c1 - c0)
        img[lb[0]:lb[2], c0:c1] = 0.9 - 0.8 * blob
        out = oc.ocr_read_line(img, models[font])
        res[_slot_outcome(out, (cl, cr), h)] += 1
    n = sum(res.values())
    print(f"\n[reject blob {font}] {res} -> reject rate {res['rejected'] / n:.3f}")
    assert res["rejected"] / n >= 0.9


# --------------------------------------------------------------------------- #
# 劣化 / Degradation                                                           #
# --------------------------------------------------------------------------- #

def test_degradation_blur_0p1_noise_0p05(models):
    """ぼけ σ = 0.1 x 字高、雑音 σ = 0.05。

    合格線は書体ごとに正解率 >= 95 %、誤読 <= 1 %。σ = 0.1h はドット書体ではドットピッチの
    0.68 倍で、ドットは完全に融ける(この条件は学習のぼけ格子 0〜0.14h の内側)。
    Floor per font: accuracy >= 95 %, misreads <= 1 %. sigma = 0.1 h lies inside the training
    blur grid (0..0.14 h); for dot5x7 it is 0.68 dot pitch, so dots merge completely.
    """
    tots = {}
    for font in FONTS:
        rng = np.random.default_rng(99)
        tot = _tot()
        for _ in range(60):
            text = _rand_text(rng)
            h = int(rng.integers(16, 41))
            out = oc.ocr_read_line(_degraded(font, text, h, 0.1, 0.05, rng), models[font])
            _add(tot, oc.ocr_score(out["text"], text))
        tots[font] = tot
        print(f"\n[blur 0.1h + noise 0.05 {font}] {tot['n_true']} chars: {_rates(tot)}")
    pooled = {k: tots["dot5x7"][k] + tots["stroke"][k] for k in tots["stroke"]}
    acc = {f: tots[f]["correct"] / tots[f]["n_true"] for f in FONTS}
    acc_pooled = pooled["correct"] / pooled["n_true"]
    print(f"[blur 0.1h + noise 0.05 pooled] {_rates(pooled)}")
    assert acc_pooled >= 0.95
    assert acc["stroke"] >= 0.95
    assert acc["dot5x7"] >= 0.95
    # 誤読は棄却と別に数え、ごく少ない / misreads are counted apart from rejects and stay rare
    for f in FONTS:
        assert tots[f]["substituted"] / tots[f]["n_true"] <= 0.01


@pytest.mark.parametrize("font", FONTS)
def test_degradation_sweep_trend(models, font):
    """ぼけ 5 段(雑音 0.05)で、正解率は下がり棄却は増える(測った傾向を門にする)。"""
    levels = (0.0, 0.05, 0.1, 0.15, 0.2)
    acc, rej, mis = [], [], []
    for bl in levels:
        rng = np.random.default_rng(5150)
        tot = _tot()
        for _ in range(30):
            text = _rand_text(rng)
            h = int(rng.integers(16, 41))
            out = oc.ocr_read_line(_degraded(font, text, h, bl, 0.05, rng), models[font])
            _add(tot, oc.ocr_score(out["text"], text))
        n = tot["n_true"]
        acc.append(tot["correct"] / n)
        rej.append(tot["rejected"] / n)
        mis.append(tot["substituted"] / n)
    print(f"\n[sweep {font}] blur/h {levels}\n  accuracy {np.round(acc, 3).tolist()}"
          f"\n  rejected {np.round(rej, 3).tolist()}\n  misread  {np.round(mis, 3).tolist()}")
    # 正解率は単調に下がる(各段 2 ポイントの揺れは許す)/ accuracy non-increasing (2 pt slack)
    assert all(a1 <= a0 + 0.02 for a0, a1 in zip(acc[:-1], acc[1:]))
    assert acc[-1] < acc[0] - 0.4
    # 棄却は増える / rejects rise
    assert rej[-1] > rej[0] + 0.1
    assert rej[3] > rej[1]


# --------------------------------------------------------------------------- #
# 紛らわしい対 / Confusable pairs                                              #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("font", FONTS)
def test_confusion_pairs_clean(models, font):
    rng = np.random.default_rng(8086)
    pairs = [("0", "O"), ("1", "I"), ("5", "S"), ("8", "B"), ("2", "Z"), ("0", "D")]
    chars = sorted({c for p in pairs for c in p})
    stats = {}
    for c in chars:
        ok = n = 0
        for _ in range(34):
            # 対象字を 3 回含む 8 字の行 / 8-char line containing the target 3 times
            body = list(_rand_text(rng, 5, 5))
            for pos in sorted(rng.choice(8, 3, replace=False)):
                body.insert(int(pos), c)
            text = "".join(body[:8])
            h = int(rng.integers(16, 41))
            out = oc.ocr_read_line(oc.ocr_render_text(text, font, char_height_px=h)["image"],
                                   models[font])
            if len(out["text"]) == len(text):
                for t, r in zip(text, out["text"]):
                    if t == c:
                        n += 1
                        ok += (r == t)
            else:
                n += text.count(c)
        stats[c] = ok / n
    print(f"\n[confusable {font}] " + " ".join(f"{c}:{v:.3f}" for c, v in stats.items()))
    assert all(v >= 0.99 for v in stats.values()), stats


# --------------------------------------------------------------------------- #
# fail-closed / fail-soft                                                      #
# --------------------------------------------------------------------------- #

def test_fail_closed_inputs(models):
    m = models["dot5x7"]
    img = oc.ocr_render_text("AB1", "dot5x7")["image"]
    bad = img.copy()
    bad[3, 3] = np.nan
    with pytest.raises(ValueError):
        oc.ocr_read_line(bad, m)
    with pytest.raises(ValueError):
        oc.ocr_segment_line(np.stack([img, img, img], axis=-1))
    with pytest.raises(ValueError):
        oc.ocr_render_text("", "dot5x7")
    with pytest.raises(ValueError):
        oc.ocr_render_text("AB", "nosuchfont")
    with pytest.raises(ValueError):
        oc.ocr_font("nosuchfont")
    with pytest.raises(ValueError):
        oc.ocr_render_text("ab", "dot5x7")                  # 小文字は字種外 / lower case
    with pytest.raises(ValueError):
        oc.ocr_render_text("A#", "stroke")
    with pytest.raises(ValueError):
        oc.ocr_render_text("A", "dot5x7", char_height_px=float("nan"))
    with pytest.raises(ValueError):
        oc.ocr_render_text("A", "dot5x7", contrast=0.95, background=0.9)
    with pytest.raises(ValueError):
        oc.ocr_features(np.zeros((4, 4, 3)))
    with pytest.raises(ValueError):
        oc.ocr_classify(np.zeros(5), m)
    with pytest.raises(ValueError):
        oc.ocr_classify(np.full(oc.FEATURE_LENGTH, np.inf), m)
    with pytest.raises(ValueError):
        oc.ocr_read_line(img, {"features": np.zeros((2, 3))})
    with pytest.raises(ValueError):
        oc.ocr_score("A", None)
    with pytest.raises(ValueError):
        oc.ocr_train("dot5x7", variants={"nosuchkey": 1})


def test_blank_image_is_fail_soft_empty(models):
    """白紙は fail-soft: 空文字・0 字(文書化した選択)。雑音だけの白紙も同じ。"""
    for img in (np.full((60, 200), 0.9),
                0.9 + np.random.default_rng(0).normal(0, 0.05, (60, 200))):
        out = oc.ocr_read_line(img, models["stroke"])
        assert out["text"] == "" and out["n_chars"] == 0 and out["n_rejected"] == 0
        seg = oc.ocr_segment_line(img)
        assert seg["boxes"] == [] and seg["line_box"] is None


# --------------------------------------------------------------------------- #
# 採点 / Scoring                                                               #
# --------------------------------------------------------------------------- #

def test_score_counts_rejects_apart_from_misreads():
    s = oc.ocr_score("A?C", "ABC")
    assert (s["correct"], s["rejected"], s["substituted"]) == (2, 1, 0)
    s = oc.ocr_score("AXC", "ABC")
    assert (s["correct"], s["rejected"], s["substituted"]) == (2, 0, 1)
    s = oc.ocr_score("AC", "ABC")
    assert (s["correct"], s["deleted"], s["inserted"]) == (2, 1, 0)
    s = oc.ocr_score("ABBC", "ABC")
    assert (s["correct"], s["deleted"], s["inserted"]) == (3, 0, 1)
    s = oc.ocr_score("", "")
    assert s["n_true"] == 0 and s["accuracy"] == 1.0
    s = oc.ocr_score("AB", "")
    assert s["inserted"] == 2 and s["accuracy"] == 0.0


# --------------------------------------------------------------------------- #
# 特徴量・決定性・速さ / Features, determinism, speed                           #
# --------------------------------------------------------------------------- #

def test_features_length_and_empty():
    f = oc.ocr_features(np.zeros((20, 15)))
    assert f.shape == (oc.FEATURE_LENGTH,) == (88,) and not f.any()
    g = np.zeros((24, 24))
    g[4:20, 10:14] = 1.0
    f = oc.ocr_features(g)
    assert f.shape == (88,) and np.isfinite(f).all() and 0 <= f.min() and f.max() <= 1


def test_determinism(models):
    # 学習の決定性(小さな設定を 2 回)/ training determinism on a small configuration
    small = {"ink_gain": (0.0,), "blur": (0.0, 0.06)}
    m1 = oc.ocr_train("dot5x7", char_height_px=(20,), variants=small)
    m2 = oc.ocr_train("dot5x7", char_height_px=(20,), variants=small)
    assert np.array_equal(m1["features"], m2["features"])
    assert np.array_equal(m1["labels"], m2["labels"])
    assert np.array_equal(m1["weights"], m2["weights"])
    assert m1["reject_distance_by_class"] == m2["reject_distance_by_class"]
    # 読みの決定性(既定の模型、劣化画像)/ reading determinism with the default model
    rng = np.random.default_rng(1)
    img = _degraded("stroke", "AB12-CD/3:4", 24, 0.06, 0.03, rng)
    a = oc.ocr_read_line(img, models["stroke"])
    b = oc.ocr_read_line(img.copy(), models["stroke"])
    assert a == b
    assert oc.ocr_segment_line(img) == oc.ocr_segment_line(img.copy())


@pytest.mark.parametrize("font", FONTS)
def test_read_line_speed(models, font):
    img = oc.ocr_render_text("LOT2611A03", font, char_height_px=24)["image"]
    oc.ocr_read_line(img, models[font])                     # 暖機 / warm-up
    ts = []
    for _ in range(7):
        t0 = time.perf_counter()
        out = oc.ocr_read_line(img, models[font])
        ts.append(time.perf_counter() - t0)
    med = float(np.median(ts)) * 1000
    print(f"\n[speed {font}] 10-char line median {med:.2f} ms")
    assert out["text"] == "LOT2611A03"
    assert med < 50.0
