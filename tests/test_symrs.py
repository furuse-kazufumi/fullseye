# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Reed-Solomon(symrs)の門 —— 公開の符号語、誤り + 消失の訂正、能力の外の拒否。"""
from __future__ import annotations

import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import symrs as R  # noqa: E402


def test_published_qr_codewords():
    """thonky.com の QR の解説の "HELLO WORLD" 1-M(データ 16 語 → 訂正 10 語)。"""
    data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
    assert R.rs_encode(R.QR_FIELD, data, 10, 0) == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


@pytest.mark.parametrize("gf,fcr", [(R.QR_FIELD, 0), (R.DM_FIELD, 1)])
def test_errors_and_erasures_within_capacity_are_corrected(gf, fcr):
    """2·誤り + 消失 ≤ nsym なら元に戻り、直した語数 = 壊した語数(1500 通り)。"""
    rng = random.Random(fcr + 1)
    for _ in range(1500):
        k, ns = rng.randint(1, 40), rng.randint(2, 30)
        data = [rng.randrange(256) for _ in range(k)]
        cw = data + R.rs_encode(gf, data, ns, fcr)
        ne = rng.randint(0, ns)
        nerr = rng.randint(0, (ns - ne) // 2)
        pos = rng.sample(range(len(cw)), ne + nerr)
        bad = list(cw)
        for p in pos:
            bad[p] ^= rng.randrange(1, 256)
        out, n = R.rs_decode(gf, bad, ns, fcr, pos[:ne])
        assert out == cw and n == ne + nerr


def test_beyond_capacity_is_refused_not_miscorrected_in_this_sample():
    rng = random.Random(5)
    refused = wrong = 0
    for _ in range(400):
        data = [rng.randrange(256) for _ in range(20)]
        cw = data + R.rs_encode(R.QR_FIELD, data, 10, 0)
        bad = list(cw)
        for p in rng.sample(range(len(cw)), 6):               # 能力 5 を 1 超える
            bad[p] ^= rng.randrange(1, 256)
        try:
            out, _n = R.rs_decode(R.QR_FIELD, bad, 10, 0)
            wrong += out != cw
        except R.RSDecodeError:
            refused += 1
    assert refused + wrong == 400 and wrong <= 4               # 誤訂正は理論上ごく稀


def test_fail_closed():
    with pytest.raises(ValueError):
        R.GF256(0x100)                                         # 原始多項式でない
    with pytest.raises(ValueError):
        R.rs_encode(R.QR_FIELD, [], 4)
    with pytest.raises(ValueError):
        R.rs_encode(R.QR_FIELD, [256], 4)
    with pytest.raises(ValueError):
        R.rs_decode(R.QR_FIELD, [1, 2, 3], 3)
    with pytest.raises(R.RSDecodeError):
        R.rs_decode(R.QR_FIELD, [0] * 10, 4, 0, erase_pos=[0, 1, 2, 3, 4])
