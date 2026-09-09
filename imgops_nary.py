"""N-ary HALCON-parity capability tier (image arithmetic, region set theory).

The single-image evolution pipeline threads ONE value, so it cannot host HALCON
operators that take two images (add_image, sub_image, ...) or two regions
(union2, intersection, ...). Those are still real HALCON capabilities the user
wants imgevolve to *do* — so they live here as genuine multi-argument functions
with an honest, separate coverage count. They are difftest-able and codegen-able
even though evolution does not select them.

Every op is a real numpy/scipy implementation (never a stub); `verify()` runs each
on canonical inputs and `coverage()` reports how many distinct real HALCON n-ary
operators are implemented. Fail-closed: names not in the scraped reference are
dropped, never counted.

    py -3.11 imgops_nary.py            # self-report: ops, coverage, verify
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))


def _f(x):
    return np.clip(np.asarray(x, np.float64), 0.0, 1.0)


def _b(x):
    return np.asarray(x) > 0.5


def _u8(x):
    return (_f(x) * 255).astype(np.uint8)


@dataclass
class NaryOp:
    name: str
    halcon: str
    arity: int
    in_sorts: tuple
    out_sort: str
    fn: Callable          # fn(inputs: list, a: float, b: float) -> output
    desc: str = ""


# --- image (x2) -> image : HALCON arithmetic (Mult, Add parameters via a,b) --- #
def _add(io, a, b):
    return np.clip((_f(io[0]) + _f(io[1])) * (0.5 + a) + (b - 0.5), 0, 1)


def _sub(io, a, b):
    return np.clip((_f(io[0]) - _f(io[1])) * (0.5 + a) + (b), 0, 1)


def _mult(io, a, b):
    return np.clip(_f(io[0]) * _f(io[1]) * (0.5 + 1.5 * a) + (b - 0.5), 0, 1)


def _div(io, a, b):
    return np.clip(_f(io[0]) / np.maximum(_f(io[1]), 1e-3) * (0.1 + 0.9 * a), 0, 1)


def _abs_diff(io, a, b):
    return np.clip(np.abs(_f(io[0]) - _f(io[1])) * (0.5 + 1.5 * a), 0, 1)


def _max_img(io, a, b):
    return np.maximum(_f(io[0]), _f(io[1]))


def _min_img(io, a, b):
    return np.minimum(_f(io[0]), _f(io[1]))


def _and_img(io, a, b):
    return (np.bitwise_and(_u8(io[0]), _u8(io[1])).astype(np.float64)) / 255.0


def _or_img(io, a, b):
    return (np.bitwise_or(_u8(io[0]), _u8(io[1])).astype(np.float64)) / 255.0


def _convol(io, a, b):
    # HALCON convol_image applies the mask as a CORRELATION (the mask is laid
    # over the image as written, not flipped): out[r,c] = sum_ij m[i,j] *
    # img[r+i-cr, c+j-cc]. scipy's `convolve` flips the mask, which mirrors any
    # asymmetric filter (a mask with its weight right of centre would shift the
    # image the wrong way) — so `correlate` it is.
    ker = np.asarray(io[1], np.float64)
    ker = ker / (np.abs(ker).sum() + 1e-8)
    return np.clip(ndimage.correlate(_f(io[0]), ker, mode="reflect"), 0, 1)


# --- region (x2) -> region : HALCON set theory ------------------------------- #
def _union2(io, a, b):
    return (_b(io[0]) | _b(io[1])).astype(np.float64)


def _intersection(io, a, b):
    return (_b(io[0]) & _b(io[1])).astype(np.float64)


def _difference(io, a, b):
    return (_b(io[0]) & ~_b(io[1])).astype(np.float64)


def _symm_difference(io, a, b):
    return (_b(io[0]) ^ _b(io[1])).astype(np.float64)


# --- image + region -> image ------------------------------------------------- #
def _reduce_domain(io, a, b):
    return _f(io[0]) * _b(io[1]).astype(np.float64)


def _overpaint_region(io, a, b):
    out = _f(io[0]).copy()
    out[_b(io[1])] = a
    return out


def _paint_gray(io, a, b):
    # HALCON paint_gray(ImageSource, ImageDestination) paints the source's gray
    # values into the destination over the source's whole DOMAIN. Images here
    # carry no explicit domain; this tier's own convention (`reduce_domain`
    # multiplies by the region) is "outside the domain = 0", so every non-zero
    # source pixel — dark ones included — is painted. (Until 2026-09-03 only
    # source pixels > 0.5 were painted, so a dark source vanished.)
    src = _f(io[1])
    return np.where(src > 0.0, src, _f(io[0]))


IMG, REG = "image", "region"

_DEFS = [
    ("add_image", "add_image", 2, (IMG, IMG), IMG, _add, 
     "2 枚の画像を加算する。HALCON の ``add_image`` に相当。``out = clip((I1 + I2) * (0.5 + a) + (b - 0.5), 0, 1)`` —— ``a`` がゲイン(0.5〜1.5 倍)、``b`` がオフセット(-0.5〜+0.5)。飽和は 0/1 で切る。"),
    ("sub_image", "sub_image", 2, (IMG, IMG), IMG, _sub, 
     "2 枚の画像を減算する。HALCON の ``sub_image`` に相当。``out = clip((I1 - I2) * (0.5 + a) + b, 0, 1)`` —— 負になる差を ``b`` で持ち上げないと 0 に潰れる(既定 ``b=0.5`` で中央値が灰色になる)。"),
    ("mult_image", "mult_image", 2, (IMG, IMG), IMG, _mult, 
     "2 枚の画像を画素ごとに掛ける。HALCON の ``mult_image`` に相当。``out = clip(I1 * I2 * (0.5 + 1.5a) + (b - 0.5), 0, 1)``。積は必ず暗くなるので ``a`` のゲイン幅を広く取ってある。"),
    ("div_image", "div_image", 2, (IMG, IMG), IMG, _div, 
     "2 枚の画像を画素ごとに割る。HALCON の ``div_image`` に相当。``out = clip(I1 / max(I2, 1e-3) * (0.1 + 0.9a), 0, 1)`` —— ゼロ割を避けるため分母に下限 ``1e-3`` を敷く(そこでは商が最大 1000 倍になり飽和する)。``b`` は未使用。"),
    ("abs_diff_image", "abs_diff_image", 2, (IMG, IMG), IMG, _abs_diff, 
     "2 枚の画像の差の絶対値。HALCON の ``abs_diff_image`` に相当。``out = clip(|I1 - I2| * (0.5 + 1.5a), 0, 1)``。変化検出の基本形で、符号を捨てる代わりに明暗どちらの変化も拾う。``b`` は未使用。"),
    ("max_image", "max_image", 2, (IMG, IMG), IMG, _max_img, 
     "2 枚の画像の画素ごとの最大値。HALCON の ``max_image`` に相当。``a``, ``b`` は未使用。明るい方を残すので、複数露光の合成や欠損の穴埋めに使う。"),
    ("min_image", "min_image", 2, (IMG, IMG), IMG, _min_img, 
     "2 枚の画像の画素ごとの最小値。HALCON の ``min_image`` に相当。``a``, ``b`` は未使用。暗い方を残すので、反射ハイライトの抑制に使う。"),
    ("bit_and", "bit_and", 2, (IMG, IMG), IMG, _and_img, 
     "2 枚の画像のビット単位 AND。HALCON の ``bit_and`` に相当。★一度 8bit 整数に量子化してから演算し 255 で割って戻すので、**浮動小数の階調は失われる**(0.501 と 0.503 は同じ値になる)。``a``, ``b`` は未使用。"),
    ("bit_or", "bit_or", 2, (IMG, IMG), IMG, _or_img, 
     "2 枚の画像のビット単位 OR。HALCON の ``bit_or`` に相当。★``bit_and`` と同じく 8bit へ量子化してから演算するため階調が落ちる。``a``, ``b`` は未使用。"),
    ("convol_image", "convol_image", 2, (IMG, IMG), IMG, _convol, 
     "第 2 入力をフィルタマスクとして畳み込む。HALCON の ``convol_image`` に相当。★HALCON と同じく**相関**(マスクを書いたまま重ねる)で計算する —— scipy の ``convolve`` はマスクを反転するので、非対称なマスクだと画像が逆向きにずれる。マスクは絶対値の総和で正規化し、端は ``reflect``。``a``, ``b`` は未使用。"),
    ("union2", "union2", 2, (REG, REG), REG, _union2, 
     "2 つの領域の和(どちらかに入る画素)。HALCON の ``union2`` に相当。入力は ``> 0.5`` で二値化する。``a``, ``b`` は未使用。"),
    ("intersection", "intersection", 2, (REG, REG), REG, _intersection, 
     "2 つの領域の積(両方に入る画素)。HALCON の ``intersection`` に相当。入力は ``> 0.5`` で二値化する。``a``, ``b`` は未使用。"),
    ("difference", "difference", 2, (REG, REG), REG, _difference, 
     "2 つの領域の差(第 1 に入り第 2 に入らない画素)。HALCON の ``difference`` に相当。**順序が意味を持つ**(引く側と引かれる側を入れ替えると別の結果)。``a``, ``b`` は未使用。"),
    ("symm_difference", "symm_difference", 2, (REG, REG), REG, _symm_difference, 
     "2 つの領域の対称差(どちらか一方だけに入る画素)。HALCON の ``symm_difference`` に相当。重なりを消すので、2 つのマスクのずれを見るのに使う。``a``, ``b`` は未使用。"),
    ("reduce_domain", "reduce_domain", 2, (IMG, REG), IMG, _reduce_domain, 
     "画像の定義域を領域で絞る。HALCON の ``reduce_domain`` に相当。この層は明示的な定義域を持たないので、**領域外を 0 にする**(画像に領域を掛ける)ことで表す。``a``, ``b`` は未使用。"),
    ("overpaint_region", "overpaint_region", 2, (IMG, REG), IMG, _overpaint_region, 
     "画像の領域の中を一定値で塗りつぶす。HALCON の ``overpaint_region`` に相当。塗る値は ``a``(0〜1)。``b`` は未使用。"),
    ("paint_gray", "paint_gray", 2, (IMG, IMG), IMG, _paint_gray, 
     "第 2 画像(source)の濃淡を第 1 画像へ塗り込む。HALCON の ``paint_gray`` に相当。★塗る範囲は source の**非ゼロ画素すべて**(この層の約束「定義域の外は 0」に合わせた)。2026-09-03 までは ``> 0.5`` の画素だけを塗っていたため、**暗い source が消えていた**。``a``, ``b`` は未使用。"),
]


def _real_ops() -> set:
    """Real HALCON names — generated py-module first, flat data/ JSON second.

    `halcon_names_data` ships in the wheel, `data/halcon_operators.json` does not,
    so reading only the JSON returned an EMPTY set on a pip-installed package and
    the fail-closed guard in `build_nary` admitted everything instead.
    """
    try:
        from halcon_names_data import HALCON_NAMES
        return set(HALCON_NAMES)
    except Exception:
        pass
    p = os.path.join(HERE, "data", "halcon_operators.json")
    if not os.path.exists(p):
        return set()
    return {o["name"] for o in json.load(open(p, encoding="utf-8"))["operators"]}


def build_nary() -> list[NaryOp]:
    """Compile n-ary ops, dropping any whose HALCON name is not real (fail-closed).

    An unavailable reference set drops everything rather than admitting everything
    — an unverifiable name is not a verified one.
    """
    real = _real_ops()
    out, dropped = [], []
    for (n, h, ar, ins, o, fn, d) in _DEFS:
        if h not in real:
            dropped.append(h)
            continue
        out.append(NaryOp(n, h, ar, ins, o, fn, d))
    build_nary.dropped = dropped
    return out


build_nary.dropped = []


def coverage() -> dict:
    ops = build_nary()
    return {"n_ops": len(ops), "dropped": build_nary.dropped,
            "halcon_names": sorted({o.halcon for o in ops})}


def verify() -> dict:
    """Run every op on canonical inputs; count those returning the declared sort.

    Fail-closed on both counts a "region" claim can be faked with: the output must
    be BINARY ({0,1}), not merely inside [0,1] (any grayscale image satisfies the
    range test), and an op that returns its first input unchanged is an identity,
    not an implementation, so it is failed rather than counted.
    """
    n = 48
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    i1 = np.clip(xx / n + 0.2, 0, 1)
    i2 = np.clip(((yy - n / 2) ** 2 + (xx - n / 2) ** 2 < 120).astype(float) * 0.8 + 0.1, 0, 1)
    r1 = (i1 > 0.5).astype(np.float64)
    r2 = (i2 > 0.5).astype(np.float64)
    passed, failed = [], []
    for op in build_nary():
        io = [i1 if s == IMG else r1 for s in op.in_sorts]
        io[1] = i2 if op.in_sorts[1] == IMG else r2
        try:
            out = op.fn([x.copy() for x in io], 0.5, 0.4)
            ok = isinstance(out, np.ndarray) and out.ndim == 2 and np.all(np.isfinite(out))
            if ok and op.out_sort == REG:
                ok = set(np.unique(np.round(out, 6)).tolist()) <= {0.0, 1.0}
                if not ok:
                    failed.append("%s:region not binary {0,1}" % op.halcon)
                    continue
            if ok and out.shape == io[0].shape and float(np.max(np.abs(out - io[0]))) <= 1e-9:
                failed.append("%s:identity on canonical inputs" % op.halcon)
                continue
            (passed if ok else failed).append(op.halcon)
        except Exception as e:  # noqa: BLE001
            failed.append("%s:%r" % (op.halcon, e))
    return {"n": len(build_nary()), "pass": len(passed), "fail": failed}


if __name__ == "__main__":
    cov = coverage()
    v = verify()
    print("n-ary capability tier: %d ops (dropped %s)" % (cov["n_ops"], cov["dropped"]))
    print("  functional gate: %d/%d pass" % (v["pass"], v["n"]))
    if v["fail"]:
        print("  FAIL:", v["fail"])
    print("  HALCON names:", ", ".join(cov["halcon_names"]))
