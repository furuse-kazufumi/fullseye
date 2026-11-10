"""blob_features: ラベルの歯抜けで n と配列の長さが食い違った(2026-11-09 点検 g4_2d_stats の med)。

ラベル 2 を消した像で n = 5、配列の長さ 4。1 画素の塊の circularity が 1.75(> 1)。
"""
import numpy as np

import blob2d as B


def _labels():
    m = np.zeros((40, 60), bool)
    m[2:8, 2:8] = True
    m[2:8, 20:30] = True
    m[20:30, 5:15] = True
    m[25:35, 40:55] = True
    m[15, 35] = True
    return B.blob_label(m)


def test_gapped_labels_n_matches_the_arrays():
    lab = np.asarray(_labels()).copy()
    lab[lab == 2] = 0
    f = B.blob_features(lab)
    assert f["n"] == len(f["area"]) == len(f["label"]) == 4
    assert f["label"].tolist() == [1, 3, 4, 5]


def test_contiguous_labels_unchanged():
    f = B.blob_features(_labels())
    assert f["n"] == 5 and len(f["area"]) == 5


def test_circularity_is_at_most_one():
    one = np.zeros((5, 5), bool)
    one[2, 2] = True
    f = B.blob_features(B.blob_label(one))
    assert 0 < f["circularity"][0] <= 1.0
    f = B.blob_features(_labels())
    assert (f["circularity"] <= 1.0).all()
