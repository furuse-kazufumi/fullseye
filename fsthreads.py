# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fsthreads —— 行列分解のあいだだけ BLAS のスレッド数を絞る。

## なぜ要るのか

OpenBLAS / MKL は既定でスレッド数を **論理 CPU 数**から決める。行列積では
それが正しく、24 スレッドは 768x768 で 5.8 倍速い。ところが **LAPACK の分解
(SVD / 固有値 / QR / 擬似逆行列)では一度も勝たない** —— 分解の中の GEMM が
小さすぎて、同期の費用が計算量を上回るため。

実測(24 論理 CPU / OpenBLAS 0.3.31 / numpy 2.4.6 / Windows、他の負荷を止めた
状態、中央値)::

    np.linalg.svd(n x n, full_matrices=False)          単位 ms
    n        1t      2t      4t      8t     24t   最速
    48    0.165   0.195   0.266   0.344   0.651   1t
    96    0.650   0.918   1.081   1.305   2.217   1t
    384  19.331  23.572  21.686  28.090  36.243   1t
    512   45.9    44.0    45.5    47.3   105.3    2t
    1024 351.7   320.0   259.4   262.4   868.8    4t
    2048 2675    1950    1600    1344    3263     8t

    参考: 行列積 ``a @ a`` は**逆の傾き**(768 で 1t 14.0ms / 8t 2.4ms)。
    だからプロセス全体を絞ってはいけない。分解の周りだけ絞る。

``24t`` が勝った升目は、svd / eigh / qr / pinv の 4 種類 x 7 サイズのどこにも
無かった。上限を 8 で止めるのはこの観測に基づく(外挿ではない)。

## 速さだけの話ではない —— 再現性の話でもある

スレッド数が変わると縮約の順序が変わるので、**分解の結果は下位ビットで変わる**::

    svd(64x64)   1t vs 24t   bitwise 一致 False   最大差 3.6e-16
    eigh(256)    1t vs 24t   bitwise 一致 False   最大差 1.7e-12

スレッド数は論理 CPU 数から決まるので、**何もしない状態が、機械ごとに違う値を
出している**(4 コアの CI と 24 コアの開発機で分解の下位ビットが一致しない)。
上限を固定すると、機械をまたいだ再現性は**上がる**方向に動く。緩める変更ではない。

## なぜ ``set_system`` に載せないのか

:mod:`fssystem` の表に載せられるのは「厳しくする方向のみ」か「数値に一切
影響しない」パラメータだけで、``tests/test_fssystem.py`` が機械で強制している。
スレッド数は上のとおり下位ビットを動かすので、**あの表には載せられない**。
速さのための設定を意味論の表へ混ぜると、表が「検査を切る設定」の入口になる
—— それがあの表のいちばん避けたかったことなので、別のモジュールに置く。

## 何で段を選ぶか —— 短辺。長辺でも積でもない

(m, n) の格子 92 升(svd と lstsq、**2 の冪を外した寸法**)で、予測子ごとに
「その規則だけで段を決めたときに失う時間」を測った。判定を合計だけで
やらないのは、外しても差が出ない升目と 4 倍損する升目を同じに数えたくないため::

    規則                          失う時間   1.2 倍超え   最悪
    何もしない(24t のまま)          3975ms    79/92 升   19.91x
    短辺 <512:1 <1024:4 else:8       303ms     5/92 升    1.41x   <- 採用
    積  <512:1 <1024:4 else:8        235ms    14/92 升    2.50x
    長辺 <512:1 <1024:4 else:8       241ms    ---         3.89x

**合計では積と長辺が勝つ**(235 / 241 対 303ms)。それでも短辺を採るのは、
合計の差 68ms より**最悪値の差 1.41x 対 2.50x / 3.89x** のほうが重いから。
ライブラリが最小化すべきは平均ではなく最悪で、4 倍の後退は障害報告になる。

短辺が効く理屈: LAPACK の仕事量は概ね ``長辺 x 短辺^2`` で、スレッドが効くか
どうかは短辺のブロック幅で決まる。``16384x3`` の最小二乗を長辺で「大きい行列」と
数えると 8 スレッドを許してしまうが、実際は幅 3 の QR である。

★ この規則が外す升目(採用した上で承知しておくもの): ``6528x384`` の svd で
1.41 倍、``3840x768`` で 1.30 倍。どちらも「そこそこ幅のある縦長」で、短辺だけ
見ると小さく見えるが 8 スレッドが効く形。逆に積で選ぶと ``3264x192`` で 2.50 倍
損をするので、**どちらかを選ぶなら短辺**。

## 2 の冪の辺はキャッシュ競合で遅い —— ただし段の選択は変わらない

leading dimension が 2 の冪だとキャッシュのセットが衝突する(密行列ライブラリが
lda をずらして確保するのはこのため)。実測(svd、単スレッドの実効 GFLOPS)::

    n     255    256*    257    264      -> 冪だけ 13% 遅い
        27.9    26.1    30.4   30.9
    n     511    512*    513    520      -> 18% 遅い
        41.4    34.6    41.2   44.1
    n    1023   1024*   1025   1032      -> 19% 遅い
        43.9    35.9    44.4   44.5
    n = 64 / 128 では差が出ない(キャッシュに収まるので競合が起きない)

**最速スレッド数は 4 つ組のどこでも同一**だった(255/256/257/264 は全部 1t、
1023/1024/1025/1032 は全部 4t)。したがってこの効果は段数表を歪めない。
上の 92 升の格子から 2 の冪を外してあるのは、それでも**升目の分布**が偏る
(正方 1023 のような升目が 1 つも無くなる)ため。

## 行優先 / 列優先

numpy は行優先、LAPACK は列優先なので、分解のたびに並べ替えが起きる。
列優先で渡すと ``lstsq`` で 3-10% 速い(``(4096,512)`` で 97.7 -> 89.7ms)。
**これはスレッドとは独立した別の話**で、最速スレッド数は配置を変えても
同じだった(``(65536,36)`` は行優先でも列優先でも 24t が最速)。
自分で設計行列を組み立てる場所では ``order="F"`` で作れば取れる。

## 使い方

普通は何もしなくてよい(既定で効く)。止めたい・固定したいときだけ::

    FULLSEYE_BLAS_THREADS=off   # 一切触らない(BLAS の既定のまま)
    FULLSEYE_BLAS_THREADS=1     # 分解のあいだは常に 1
    FULLSEYE_BLAS_THREADS=auto  # 既定。上の段数表

コードから明示的に絞るなら(サンプルはこの形で、理由をコメントに書く)::

    import fullseye as fs

    with fs.blas_threads(1):            # 自分で書いた numpy コードにも効く
        U, s, Vt = np.linalg.svd(m, full_matrices=False)

ライブラリ内部で分解を呼ぶときは、短辺を渡して段を選ばせる::

    import fsthreads

    with fsthreads.for_decomposition(min(m.shape)):
        U, s, Vt = np.linalg.svd(m, full_matrices=False)

    U, s, Vt = fsthreads.svd(m, full_matrices=False)   # 短辺は関数側が測る

## 実装上の注意 —— **呼び出しごとに作らない**

``threadpoolctl.threadpool_limits(...)`` は毎回**読み込み済みの共有ライブラリを
数え直す**ので 1 回 312us かかる。3x3 を 2 万回まわす経路(法線推定など)で
これを呼ぶと、絞ったせいで 1.9 倍遅くなる(実測: 58.9ms -> 112.9ms)。
``ThreadpoolController`` を 1 個だけ持って使い回すと 2.4us になり、
さらに :data:`MIN_N` 未満では**触りもしない**ので小行列の経路は素通しになる。

依存 ``threadpoolctl`` が無い環境では、この層は**静かに何もしない**
(遅いだけで、結果は変わらない)。:func:`available` が ``False`` を返す。

## 正直に書いておく弱点 —— これはスレッドごとに独立にできない

:mod:`fssystem` と :mod:`drawstyle` は :mod:`contextvars` を選んで
「並行に走る生成器がレースして、例外にならず**もっともらしく間違う**」のを
避けている。**この層は同じ手が使えない** —— BLAS のスレッド数はプロセス全体で
1 つの状態で、Python 側のスレッドごとに分けられないため。

したがって Python のスレッドを跨いで同時に使うと、ある文脈が別の文脈の上限を
見ることがある。影響するのは**速さと下位ビット**であって、形や意味は変わらない。
それでも下位ビットはこの repo が気にする対象なので、条件を書いておく:

* 単スレッドで使う限り上限は決定的で、**機械をまたいだ再現性は上がる**。
* Python のスレッドを跨ぐ同時実行では上限が不定になりうる。ただし
  **何もしなければ不定なまま**なので、この層が新しく壊すものは無い。
* 決定的にしたいなら ``FULLSEYE_BLAS_THREADS`` を整数で固定する。
"""
from __future__ import annotations

import contextlib
import os
import threading

import numpy as np

__all__ = [
    "TIERS", "MIN_N", "ENV",
    "available", "cap_for", "current_threads", "policy", "short_side",
    "for_decomposition", "blas_threads", "limited", "counters", "reset_counters",
    "svd", "eigh", "eigvalsh", "qr", "pinv", "lstsq",
]


# =========================================================================
# 方針 —— どの大きさに何スレッドまで許すか
# =========================================================================

#: ``(この短辺の長さ未満なら, この上限)``。最後の ``None`` は「それ以上すべて」。
#:
#: 同じ軸で増える分岐は表にする —— if の入れ子にすると、段を足したときに
#: 順序の取り違えが**例外にならず**、静かに違う上限を選ぶ。
#:
#: 切り方の根拠(92 升の格子、失う時間 / 1.2 倍超え / 最悪):
#:   <512:1 <1024:4 else:8  -> 303ms /  5 升 / 1.41x   <- これ
#:   <768:1 <3072:4 else:8  -> 373ms /  4 升 / 1.41x
#:   <1024:1 <4096:4 else:8 -> 429ms /  5 升 / 1.43x
#:   <256:1 <1024:4 else:8  -> 478ms / --   / 2.00x
TIERS = ((512, 1), (1024, 4), (None, 8))

#: これ未満の短辺では**何もしない**。絞る仕掛け自体が 2.4us かかるので、
#: それより速い分解に被せると損になる。
#:
#: 32 に置く根拠(同じ 92 升の格子):
#:   MIN_N=32 -> 303ms / 1.41x /  5 升
#:   MIN_N=48 -> 305ms / 3.54x /  9 升   <- 短辺 32-47 を素通しにすると最悪が悪化
#:   MIN_N=64 -> 314ms / 3.80x / 17 升
#: 下げ過ぎない根拠: この repo でいちばん多い分解は 3x3 の eigh で、スイート 1 回で
#: 247 万回(10.3 秒)。ここに 2.4us を被せると 5.9 秒増える。短辺 3 なので 32 で届かない。
MIN_N = 32

#: 環境変数。``auto``(既定) / ``off`` / 正の整数。
ENV = "FULLSEYE_BLAS_THREADS"

_CONTROLLER = None
_TRIED = False

#: 環境変数の解釈結果を**生の文字列をキーに**憶える。生文字列がキーなので、
#: 途中で環境変数を変えても次の呼び出しから効く(テストがそれに依存する)。
_POLICY_CACHE = {}

#: いま上限の中に居るか。門(``tests/test_blas_thread_discipline.py``)が
#: 「絞り忘れた大きい分解」を数えるのに使う。スレッドごとに独立させる
#: —— 上限そのものはプロセス共有だが、**この計数は文脈の話**なので。
_LOCAL = threading.local()

#: 観測用の通し数。効いているかを外から数えられるようにしておく。
_COUNTS = {"limited": 0, "skipped": 0}


def _controller():
    """``ThreadpoolController`` を 1 個だけ作って使い回す(無ければ ``None``)。"""
    global _CONTROLLER, _TRIED
    if not _TRIED:
        _TRIED = True
        try:
            from threadpoolctl import ThreadpoolController
            _CONTROLLER = ThreadpoolController()
        except Exception:                                  # noqa: BLE001
            _CONTROLLER = None                             # 無ければ何もしない層になる
    return _CONTROLLER


def available():
    """スレッド数を絞れる環境か(``threadpoolctl`` が入っているか)。"""
    return _controller() is not None


def current_threads():
    """いま BLAS が使うスレッド数(分からなければ ``None``)。"""
    ctl = _controller()
    if ctl is None:
        return None
    counts = [d["num_threads"] for d in ctl.info() if d.get("user_api") == "blas"]
    return max(counts) if counts else None


def policy():
    """環境変数の解釈: ``("auto", None)`` / ``("off", None)`` / ``("fixed", n)``。"""
    raw = (os.environ.get(ENV) or "auto").strip().lower()
    hit = _POLICY_CACHE.get(raw)
    if hit is not None:
        return hit
    _POLICY_CACHE[raw] = out = _parse_policy(raw)
    return out


def _parse_policy(raw):
    if raw in ("auto", ""):
        return ("auto", None)
    if raw in ("off", "none"):
        return ("off", None)
    try:
        n = int(raw)
    except ValueError:
        raise ValueError(
            f"{ENV}={raw!r} is not understood; use 'auto', 'off', or a positive integer "
            "(a typo must not look like it took effect)"
        ) from None
    if n < 1:
        raise ValueError(
            f"{ENV}={raw!r} must be >= 1; use 'off' to leave the BLAS threads alone")
    return ("fixed", n)


def cap_for(n):
    """短辺 ``n`` の分解に許すスレッド数の上限。``None`` は「触らない」。"""
    if n < MIN_N:                 # 先に見る —— 小行列の経路で policy() すら踏ませない
        return None
    mode, fixed = policy()
    if mode == "off":
        return None
    if mode == "fixed":
        return fixed
    for limit, cap in TIERS:
        if limit is None or n < limit:
            return cap
    raise AssertionError("TIERS must end with a (None, cap) row")   # pragma: no cover


def short_side(a):
    """配列の**最後の 2 軸のうち短い方**。2 軸未満なら 0(= 触らない)。"""
    shape = getattr(a, "shape", ())
    if len(shape) < 2:
        return 0
    return int(min(shape[-2:]))


# =========================================================================
# 文脈 —— 絞る
# =========================================================================

def limited():
    """いま「絞った文脈」の中に居るか(門が絞り忘れを数えるのに使う)。"""
    return getattr(_LOCAL, "depth", 0) > 0


def counters():
    """``{"limited": 絞った回数, "skipped": 絞らなかった回数}`` の写し。"""
    return dict(_COUNTS)


def reset_counters():
    """通し数を 0 に戻す(門と計測用)。"""
    _COUNTS["limited"] = _COUNTS["skipped"] = 0


@contextlib.contextmanager
def _apply(cap):
    ctl = _controller() if cap is not None else None
    if ctl is None:
        _COUNTS["skipped"] += 1
        yield False
        return
    _COUNTS["limited"] += 1
    _LOCAL.depth = getattr(_LOCAL, "depth", 0) + 1
    try:
        with ctl.limit(limits=cap, user_api="blas"):
            yield True
    finally:
        _LOCAL.depth -= 1


@contextlib.contextmanager
def for_decomposition(n):
    """短辺 ``n`` の分解を行うあいだだけ、BLAS のスレッド数を段数表で絞る。

    段数表が「触らない」と言う場合(``n`` が :data:`MIN_N` 未満 /
    ``FULLSEYE_BLAS_THREADS=off`` / ``threadpoolctl`` が無い)は、
    **何もしない**文脈になる。``as`` で受けると実際に絞ったかが分かる。
    """
    with _apply(cap_for(int(n))) as applied:
        yield applied


@contextlib.contextmanager
def blas_threads(n):
    """BLAS のスレッド数を ``n`` に固定する(利用者向けの明示的な入口)。

    段数表を通さず、渡した数をそのまま使う。サンプルはこちらを使い、
    **なぜ絞るのかをコメントに書く** —— 自分で書いた numpy コードにも効くので、
    ライブラリ内部の対策では届かない範囲を利用者が自分で塞げる。

    ``threadpoolctl`` が無ければ何もしない(:func:`available` で確かめられる)。
    """
    if int(n) < 1:
        raise ValueError(f"blas_threads(n) needs n >= 1, got {n!r}")
    with _apply(int(n)) as applied:
        yield applied


# =========================================================================
# 分解の薄い包み —— 呼び出し側を 1 行に保つ
# =========================================================================
#
# 短辺は包みが測るので、呼ぶ側は大きさを気にしなくてよい。段が「触らない」と
# 判断したときの追加費用は、比較 1 回と属性参照だけ(実測 0.3us 未満)。

def svd(a, full_matrices=True, compute_uv=True, hermitian=False):
    """``np.linalg.svd`` を段数表つきで。"""
    with for_decomposition(short_side(a)):
        return np.linalg.svd(a, full_matrices=full_matrices,
                             compute_uv=compute_uv, hermitian=hermitian)


def eigh(a, UPLO="L"):
    """``np.linalg.eigh`` を段数表つきで。"""
    with for_decomposition(short_side(a)):
        return np.linalg.eigh(a, UPLO=UPLO)


def eigvalsh(a, UPLO="L"):
    """``np.linalg.eigvalsh`` を段数表つきで。"""
    with for_decomposition(short_side(a)):
        return np.linalg.eigvalsh(a, UPLO=UPLO)


def qr(a, mode="reduced"):
    """``np.linalg.qr`` を段数表つきで。"""
    with for_decomposition(short_side(a)):
        return np.linalg.qr(a, mode=mode)


def pinv(a, rcond=None, hermitian=False):
    """``np.linalg.pinv`` を段数表つきで(中身は SVD)。

    ``rcond`` を渡されなければ**こちらでは既定値を作らない** —— numpy 2.x が
    ``rcond`` から ``rtol`` へ移行中で、ここで固定すると将来の既定変更を隠すため。
    """
    with for_decomposition(short_side(a)):
        if rcond is None:
            return np.linalg.pinv(a, hermitian=hermitian)
        return np.linalg.pinv(a, rcond=rcond, hermitian=hermitian)


def lstsq(a, b, rcond=None):
    """``np.linalg.lstsq`` を段数表つきで(中身は QR / SVD)。"""
    with for_decomposition(short_side(a)):
        return np.linalg.lstsq(a, b, rcond=rcond)


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    print(f"threadpoolctl available: {available()}")
    print(f"current BLAS threads   : {current_threads()}")
    print(f"policy                 : {policy()}")
    for _n in (3, 31, 32, 64, 256, 511, 512, 1023, 1024, 4096):
        print(f"  short side {_n:6d} -> cap {cap_for(_n)}")
