---
op: gcc_delay
dim: acoustics
category: dual
in: signal × signal
out: measurement
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# gcc_delay — ACOUSTICS `dual` op

- **データ種**: `signal × signal` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.gcc_delay(a, b, rate=1.0, weight='phat', band=None, interpolate=True)` (実装を直接呼ぶなら `import acoustics; acoustics.gcc_delay(a, b, rate=1.0, weight='phat', band=None, interpolate=True)`、台帳から引くなら `opsacoustics.get("gcc_delay")`)
- **台帳経由の戻り値**: `fullseye.ledger.gcc_delay(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.gcc_delay.raw(...)`、または `acoustics.gcc_delay` を直接呼ぶ。

## 使い方

2 チャンネルの**到達時間差**を一般化相互相関(GCC)で測る。→ ``(delay, table)``。

漏水の位置決め、音源の方向、超音波の肉厚、振動の伝搬 —— どれも「同じ源が 2 か所に
いつ着いたか」の差で決まる。この op はその差を**秒**(``rate`` が既定 1.0 なら標本)で
返す。位置に直すには経路長と伝搬速度を掛ける(``x = (L - c·delay) / 2`` の形)。

★**速度の仮定がそのまま位置の誤差になる**。相関がどれだけ綺麗でも、掛ける速度が
10 % 違えば位置は経路の中心からの距離に比例してずれる(`poc_leak_localization` の
実測: 中心から 18 m の漏水で +1.798 m、幾何の予測 1.800 m)。相関の質と位置の
正しさは**別の量**なので、報告では分けること。

Args:
    a, b: 同じ長さの 1-D 記録。**``b`` が ``a`` より遅れていれば ``delay`` は正**
        (``b(t) ≈ a(t - delay)``)。
    rate: 標本化周波数 [Hz]。既定 1.0 のときは返りの単位が「標本」。
    weight: 相互スペクトルの重み。
        ``"none"`` = 素の相互相関(SNR が高く反射が無ければ最良)、
        ``"phat"`` = 位相変換(振幅を白色化。残響に強いとされる)、
        ``"roth"`` = ``1/|A|²``、``"scot"`` = ``1/sqrt(|A|²|B|²)``。
        ★**PHAT が常に勝つわけではない**: 反射が非対称な経路では遅延そのものが
        偏るので、どの重みでも取り除けない(実測: 反射 0.8 で raw 0.134 m /
        PHAT 0.114 m と 1 割しか違わず、RMS はほぼ全部が偏り)。
    band: ``(lo_hz, hi_hz)`` で帯域を絞る(``rate`` が要る)。``None`` で全帯域。
        全帯域の PHAT は信号の無いビンまで持ち上げるので、**帯域を切るほうが
        効くことが多い**(実測で 8 倍)。
    interpolate: ピーク周りの放物線補間でサブ標本まで読む(既定 True)。
        切ると量子化の刻みが**散らばりでなく偏り**として残る(位置を固定すると
        毎回同じ方向に外す。PIV のピークロッキングと同じ)。
        ★**補間しても偏りは消えない**: 相関のピークは sinc 状で、放物線では
        近似しきれない。白色雑音・全帯域で 0〜1 標本を振った実測では、
        誤差が **最大 0.117 標本**の S 字(整数の近くで 0、0.3 / 0.7 付近で最大、
        向きは**整数へ引く**)。サブ標本の精度を語るときはこの偏りを含めること。

Returns:
    ``(delay, table)``: ``delay`` は秒(``rate=1.0`` なら標本)の float。
    ``table`` は ``{"lags": (2N-1,) の遅れ, "r": 相関値, "peak": ピーク値,
    "snr_peak": ピーク / 副次ピークの比}``。

    ★台帳経由(``fullseye.ledger.gcc_delay``)は宣言 out 型の ``delay`` だけを
    返す。相関曲線も要るときは ``fullseye.ledger.gcc_delay.raw(...)``。

Raises:
    ValueError: 長さが違う / 2 未満 / 非有限、``weight`` が未知、``band`` が
    ``(lo, hi)`` でない・``lo >= hi``・``rate`` に対して無効なとき。

**限界(honest)**: (1) 反射・分散・経路差が作る**偏り**は取れない ——
取れるのは雑音による散らばりだけ。(2) 相関のピークを 1 つ選ぶので、
多重路で副次ピークが勝つと**不連続に**外す(``snr_peak`` を見ること)。
(3) 遅延が記録長の半分を超えると折り返す。

Reference (public): C. H. Knapp, G. C. Carter, "The Generalized Correlation
Method for Estimation of Time Delay", IEEE Trans. ASSP 24(4), 1976, 320-327.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`dual`)

[coherence](coherence.md) · [transfer_function](transfer_function.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
