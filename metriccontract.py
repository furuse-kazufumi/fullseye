# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""metriccontract —— **人が呼ぶ経路**と**自動で回す経路**を、別の契約として分ける層。

## なぜ 2 つ要るのか

:mod:`imgmetrics` / :mod:`colortransport` は一貫して fail-closed に書いてある。
``data_range`` が曖昧なら例外、MS-SSIM が成立しない大きさなら例外、Sinkhorn が
収束しなければ例外 —— **人が呼ぶときはこれが正しい**。黙って推測した値を返す方が
ずっと危ない(この repo が何度も踏んできた「例外でなく、もっともらしく間違う」)。

ところが同じ op を**進化ループの目的関数**として回すと、話が逆になる。
例外 1 つで世代ごと落ちるので、ループ側は全候補に対して**定義された値**か、
少なくとも「測れなかった」を受け取れないと動かない。

これは TRIZ でいう物理的矛盾(**信頼性 27 ↑ vs 自動化のレベル 38 ↑**)で、
片方を弱めては解けない。**条件による分離** —— 呼び出し経路ごとに別の契約を
与えるのが解になる。

===================  ==========================  ================================
                     厳格な契約(既定)            寛容な契約(この層)
===================  ==========================  ================================
呼ぶのは             人・スクリプト               進化ループ・掃引・バッチ
測れないとき         ``MetricContractError``      :class:`Attempt` (``ok=False``)
値の代入             しない                       :func:`value_or_worst` で**明示**
バグが起きたら       そのまま送出                 **そのまま送出**(飲み込まない)
===================  ==========================  ================================

## 飲み込んでよいのは「契約による拒否」だけ

素朴に ``except ValueError`` で包むと、**今回のセッションで見つけたような実バグ
まで黙って握り潰す**(空間 Wiener が画像を縮小していた件、Sinkhorn が間違った
答えに収束していた件…)。それでは 2 つの契約を分けた意味が消える。

そこで拒否側だけを :class:`MetricContractError` にした。これは ``ValueError`` の
**部分型**なので、

* 既存の呼び手・テスト(``except ValueError`` / ``pytest.raises(ValueError)``)は
  **1 行も変わらず動く**、
* 一方でこの層は「契約による拒否」と「numpy から出た本物の ValueError」を
  **機械的に区別できる**。

## 代入する値は呼び手が選べない —— **向き**が決まっているから

「測れなかったので最悪値で埋める」は自動経路では必要だが、**最悪がどちら側かは
指標ごとに違う**。PSNR は大きいほど良く、MSE は小さいほど良い。適当な既定値
(``0.0`` など)で埋めると、**測れなかった候補が優秀な候補に勝つ**ことが起きる
—— しかも例外は出ない。よって向きは :data:`DIRECTIONS` に表として持ち、
``tests`` が「スカラを返す op すべてに向きの宣言があること」を機械で強制する。
宣言の無い指標を足したらテストが落ちる(黙って穴が空かない)。

使い方::

    import metriccontract as MC
    import imgmetrics as M

    att = MC.attempt(M.psnr, a, b)          # 例外を出さない(契約による拒否のみ)
    if att.ok:
        score = att.value
    else:
        score = MC.value_or_worst(att)      # 最悪側へ倒す。向きは表が知っている

    best = MC.best_of(attempts, "psnr")     # 無効な候補は必ず最下位
"""
from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "MetricContractError",
    "Attempt", "attempt", "attempt_all",
    "DIRECTIONS", "direction", "worst_case", "value_or_worst",
    "is_better", "best_of", "rank_attempts",
]


class MetricContractError(ValueError):
    """**契約による拒否**。「測れない」の意思表示であって、バグではない。

    ``ValueError`` の部分型にしてあるのは、既存の呼び手とテストを 1 行も
    変えずに済ませるため。この層だけがこの型を見分け、寛容な契約へ翻訳する。

    numpy や scipy が投げる素の ``ValueError`` は**この型ではない**ので、
    :func:`attempt` は握り潰さずそのまま送出する —— そうしないと実バグが
    「測れなかった候補」に化けて、進化ループの中で静かに消える。
    """


# =========================================================================
# 指標の向き —— 「最悪」がどちら側かは指標ごとに違う
# =========================================================================

#: 指標名 → ``"higher"``(大きいほど良い)/ ``"lower"``(小さいほど良い)。
#:
#: 適当な既定値で埋めると**測れなかった候補が優秀な候補に勝つ**ので、
#: 向きは必ずここに宣言する。``tests/test_metriccontract.py`` が
#: 「スカラを返す op すべてに宣言があること」を機械で強制している。
DIRECTIONS = {
    # imgmetrics —— 似ているほど良い側
    "psnr": "higher",
    "ssim": "higher",
    "ms_ssim": "higher",
    "mutual_information": "higher",
    "normalized_mutual_information": "higher",
    "image_entropy": "higher",
    # imgmetrics —— 違いの大きさ(小さいほど良い)
    "mse": "lower",
    "rmse": "lower",
    "ncd": "lower",
    "joint_entropy": "lower",
    "delta_e_2000_mean": "lower",
    # imgmetrics —— 良し悪しの軸ではない(順位づけに使ってはいけない)
    "compressed_size": None,
    "data_range_of": None,
    # colortransport —— 距離(小さいほど近い)
    "wasserstein_1d": "lower",
    "sinkhorn_distance": "lower",
    "sinkhorn_divergence": "lower",
    "transport_cost": "lower",
}


def direction(name):
    """指標の向きを返す。**宣言が無ければ例外**(黙って推測しない)。

    ``None`` が返るのは「良し悪しの軸ではない」と明示的に宣言された指標
    (``compressed_size`` など)。順位づけに使うと意味を持たないので、
    :func:`worst_case` や :func:`is_better` はこれを拒否する。
    """
    if name not in DIRECTIONS:
        raise MetricContractError(
            f"no direction declared for metric {name!r}; add it to DIRECTIONS "
            "(guessing would let an unmeasurable candidate outrank a good one "
            "without raising)"
        )
    return DIRECTIONS[name]


def worst_case(name):
    """その指標で**最悪**を意味する値。``higher`` なら ``-inf``、``lower`` なら ``+inf``。

    有限の代用値(0.0 など)を使わないのは、**それが実在しうる良い値**だから。
    無限大なら、どんな実測値にも必ず負ける。
    """
    d = direction(name)
    if d is None:
        raise MetricContractError(
            f"{name!r} is declared as not an ordering axis, so 'worst' is undefined; "
            "do not use it for selection"
        )
    return -math.inf if d == "higher" else math.inf


# =========================================================================
# 一回の測定
# =========================================================================

@dataclass(frozen=True)
class Attempt:
    """一回の測定の結果。**測れなかったことも値として持ち回れる**形。

    Attributes
    ----------
    ok : bool
        測れたか。
    value : float or None
        測れた値。``ok=False`` なら ``None``(0 で埋めたりしない)。
    reason : str or None
        測れなかった理由(契約側のメッセージそのまま)。
    metric : str
        指標名。向きを引くのに使う。
    """

    ok: bool
    value: float | None
    reason: str | None
    metric: str

    def __bool__(self):
        """``if att:`` で ok を見る。値の有無と真偽を取り違えないため。"""
        return self.ok


def attempt(fn, *args, metric=None, **kwargs):
    """指標 op を**例外を出さずに**試す。

    :class:`MetricContractError`(契約による拒否)だけを ``ok=False`` に翻訳し、
    **それ以外の例外はそのまま送出する** —— 素の ``ValueError`` / ``TypeError`` /
    ``RuntimeError`` は実装の不具合の合図で、握り潰すとこの層の意味が消える。

    Parameters
    ----------
    fn : callable
        ``imgmetrics`` / ``colortransport`` の op。
    metric : str, optional
        指標名。省略すると ``fn.__name__`` を使う。

    Returns
    -------
    Attempt
    """
    name = metric or getattr(fn, "__name__", None)
    if not name:
        raise MetricContractError("metric name could not be determined; pass metric=")
    try:
        v = fn(*args, **kwargs)
    except MetricContractError as e:
        return Attempt(ok=False, value=None, reason=str(e), metric=name)
    if v is None:
        return Attempt(ok=False, value=None, reason=f"{name} returned None", metric=name)
    fv = float(v)
    if not math.isfinite(fv):
        # inf/NaN は「測れた」と言えない。PSNR の inf(完全一致)だけは例外で、
        # あちらは意味のある値なので ok のまま通す(向きが higher なので最善)。
        if name == "psnr" and fv == math.inf:
            return Attempt(ok=True, value=fv, reason=None, metric=name)
        return Attempt(ok=False, value=None, reason=f"{name} returned {fv!r}", metric=name)
    return Attempt(ok=True, value=fv, reason=None, metric=name)


def attempt_all(fn, pairs, metric=None, **kwargs):
    """同じ op を複数の組に当てる。**1 つ落ちても残りは測る**(掃引向け)。"""
    return [attempt(fn, *p, metric=metric, **kwargs) for p in pairs]


def value_or_worst(att):
    """測れた値、または**その指標の最悪値**。代入していることが名前で分かる形。

    最悪値は ``±inf`` なので、**無効な候補がどんな実測値にも勝てない**。
    有限の代用値だと「たまたま良い値」に化けることがある。
    """
    if not isinstance(att, Attempt):
        raise MetricContractError(f"expected an Attempt, got {type(att).__name__}")
    return att.value if att.ok else worst_case(att.metric)


def is_better(a, b, name):
    """``a`` が ``b`` より良いか。向きは表から引く。"""
    d = direction(name)
    if d is None:
        raise MetricContractError(f"{name!r} is not an ordering axis")
    return a > b if d == "higher" else a < b


def rank_attempts(attempts):
    """良い順に並べ替える。**測れなかったものは必ず最下位**。

    同じ指標の :class:`Attempt` だけを受け取る(混ぜると順序が意味を失う)。
    """
    atts = list(attempts)
    if not atts:
        return []
    names = {a.metric for a in atts}
    if len(names) != 1:
        raise MetricContractError(
            f"rank_attempts needs one metric at a time, got {sorted(names)}; "
            "ranking two different metrics together produces an order that means nothing"
        )
    name = names.pop()
    d = direction(name)
    if d is None:
        raise MetricContractError(f"{name!r} is not an ordering axis, so it cannot be ranked")
    return sorted(atts, key=lambda a: value_or_worst(a), reverse=(d == "higher"))


def best_of(attempts):
    """最良の :class:`Attempt`。全部測れなかったときは ``None``。

    「全滅」を最悪値つきの :class:`Attempt` として返すと、**選ばれてしまう**。
    選ぶものが無いことは ``None`` で言う。
    """
    ranked = rank_attempts(attempts)
    if not ranked or not ranked[0].ok:
        return None
    return ranked[0]


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    declared = {k: v for k, v in DIRECTIONS.items() if v is not None}
    print(f"metriccontract: 向きを宣言した指標 {len(declared)} "
          f"(higher {sum(1 for v in declared.values() if v == 'higher')} / "
          f"lower {sum(1 for v in declared.values() if v == 'lower')}) / "
          f"順位づけに使わない {sum(1 for v in DIRECTIONS.values() if v is None)}")
