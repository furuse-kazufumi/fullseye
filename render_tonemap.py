# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HDR→LDR トーンマッピング(高ダイナミックレンジのレンダを [0,1] の表示画像へ圧縮)。

物理ベースのレンダ(Lambertian 拡散 + 鏡面ハイライト、複数光源、環境光)は容易に
**値 > 1 の放射輝度**を生む。これをそのままディスプレイに出すには [0,1] に収める必要が
あり、素朴な方法は各画素を ``min(x, 1)`` でクリップすることだ。だがクリップはハイライト域を
一律 1.0 に潰し、鏡面の芯・雲の縁・逆光の輪郭といった「白飛び」部分の**階調(明暗の順序)を
完全に失う**。トーンマッピングは全域を滑らかに [0,1] へ写す単調写像で、暗部のコントラストを
保ちつつハイライトの階調も残す — これが「映える静止画」を作る最後の一手になる。

本モジュールは軽量で広く使われる 2 つの演算子を numpy のみで実装する:

  * :func:`tonemap_reinhard` — Reinhard の ``x / (1 + x)`` 系(Reinhard et al. 2002)。
    ``[0, ∞)`` を狭義単調増加で ``[0, 1)`` へ写し、決してクリップしない(漸近的に 1)。
    任意で white-point 拡張 ``x(1 + x/w²)/(1 + x)`` を選ぶと、``w`` 未満の中間調に
    より多くのレンジを割り当てられる(``w`` が正確に 1.0 に写る)。
  * :func:`tonemap_aces` — ACES filmic の多項式近似(Narkowicz 2015)。フィルム的な
    S 字カーブで暗部を持ち上げ、ハイライトを緩やかに巻き取る。映画・ゲームの標準的な
    「見栄え」の当たりが出る。``x < ~7.24`` の範囲で狭義単調・出力 < 1(それ以上は 1 に
    飽和してクリップする — この閾値は docstring 冒頭のコメント参照)。

いずれも:

  * **exposure** を先に掛けてから写像する(``x = hdr * exposure``)。露出を上げれば暗部が
    持ち上がり、下げればハイライトの芯が締まる。
  * **グレースケール ``(H, W)`` と カラー ``(H, W, C)`` の両方**に対応。カラーはチャンネル
    独立に写像する(実装が単純で、各チャンネルが単調 ⇒ 画像全体でも階調順序が保たれる。
    彩度をより正確に残したい場合は輝度基準の写像もあり得るが、単調性の保証と素直さを優先した)。
  * 出力は **``[0, 1]`` の float64**(そのまま 8bit 化・保存できる表示画像)。

fail-closed 入力検証: 非有限(NaN/Inf)・負の放射輝度・空配列・非正の exposition/white は
例外で拒否する(HDR 放射輝度は非負が前提)。

Honest limitations(テストが示す範囲だけを主張する):
  * トーンマッピングは**局所適応でない**大域(グローバル)トーンマップ演算子であり、
    局所コントラスト強調(ローカルトーンマップ / bilateral 分解)は行わない。
  * カラーはチャンネル独立なので、極端なハイライトで僅かに hue がシフトしうる(白飛びが
    無彩色へ寄る、フィルム的挙動)。輝度基準写像が必要なら別途。

Reference (public):
  * E. Reinhard, M. Stark, P. Shirley, J. Ferwerda, "Photographic Tone
    Reproduction for Digital Images", SIGGRAPH 2002.
  * K. Narkowicz, "ACES Filmic Tone Mapping Curve", 2015 (公開近似式)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["tonemap_reinhard", "tonemap_aces"]

# ACES filmic の多項式近似係数(Narkowicz 2015)。f(x)=x(a x+b)/(x(c x+d)+e)。
# x→∞ で a/c≈1.033 に漸近するため、f(x)=1 となる x≈7.24 を超えると 1 にクリップする
# (0.08 x² - 0.56 x - 0.14 = 0 の正根)。それ未満では狭義単調増加・出力 < 1。
_ACES_A = 2.51
_ACES_B = 0.03
_ACES_C = 2.43
_ACES_D = 0.59
_ACES_E = 0.14


def _as_hdr(hdr) -> np.ndarray:
    """入力を float64 の HDR 配列へ検証。fail-closed(空/非有限/負の放射輝度は ValueError)。"""
    H = np.asarray(hdr, dtype=np.float64)
    if H.size == 0:
        raise ValueError("hdr image is empty")
    if H.ndim not in (2, 3):
        raise ValueError(f"hdr must be (H,W) or (H,W,C), got shape {H.shape}")
    if H.ndim == 3 and H.shape[2] == 0:
        raise ValueError(f"hdr has zero channels: shape {H.shape}")
    if not np.all(np.isfinite(H)):
        raise ValueError("hdr contains non-finite values (NaN/Inf)")
    if np.any(H < 0.0):
        raise ValueError("hdr contains negative radiance (must be >= 0)")
    return H


def _check_exposure(exposure: float) -> float:
    """exposure を正の有限スカラーへ検証(fail-closed)。"""
    e = float(exposure)
    if not np.isfinite(e) or e <= 0.0:
        raise ValueError(f"exposure must be a positive finite scalar, got {exposure!r}")
    return e


def tonemap_reinhard(hdr, exposure: float = 1.0, white: float | None = None) -> np.ndarray:
    """Reinhard トーンマップで HDR を ``[0, 1]`` の LDR へ圧縮。→ float64、入力と同形状。

    露出を掛けた ``x = hdr * exposure`` に対し:

      * ``white is None`` … 基本形 ``x / (1 + x)``。``[0, ∞)`` を**狭義単調増加**で
        ``[0, 1)`` へ写し、決してクリップしない(全域で階調順序を厳密保存)。
      * ``white`` 指定 … 拡張形 ``x (1 + x/white²) / (1 + x)``。``white`` を正確に 1.0 へ
        写し、``white`` 未満に多くのレンジを割く(``white`` を超える入力は 1 を超えるので
        ``[0, 1]`` にクリップする)。

    カラー ``(H, W, C)`` はチャンネル独立に写像する。素朴クリップ ``min(x, 1)`` と違い、
    値 > 1 のハイライト域でも単調な階調を保つ。

    Args:
        hdr: HDR 画像。``(H, W)`` グレースケール or ``(H, W, C)`` カラー、放射輝度 >= 0。
        exposure: 写像前に掛ける露出スケール(正)。
        white: 任意の white-point(正)。None なら基本 Reinhard(推奨・全域単調)。
    Returns:
        ``[0, 1]`` の float64 LDR 画像(入力と同形状)。
    Raises:
        ValueError: 空/非有限/負の放射輝度、非正の exposition/white(fail-closed)。
    """
    H = _as_hdr(hdr)
    e = _check_exposure(exposure)
    x = H * e
    if white is None:
        ld = x / (1.0 + x)
    else:
        w = float(white)
        if not np.isfinite(w) or w <= 0.0:
            raise ValueError(f"white must be a positive finite scalar, got {white!r}")
        ld = x * (1.0 + x / (w * w)) / (1.0 + x)
    return np.clip(ld, 0.0, 1.0)


def tonemap_aces(hdr, exposure: float = 1.0) -> np.ndarray:
    """ACES filmic 近似(Narkowicz 2015)で HDR を ``[0, 1]`` の LDR へ圧縮。→ float64。

    ``x = hdr * exposure`` に対し ``f(x) = x(a x + b) / (x(c x + d) + e)`` を適用する。
    フィルム的な S 字カーブで暗部を持ち上げハイライトを緩やかに巻き取り、映像制作標準の
    「見栄え」を出す。``x < ~7.24`` の範囲では狭義単調増加・出力 < 1(それ以上は 1 に
    飽和しクリップ)。カラー ``(H, W, C)`` はチャンネル独立に写像する。

    Args:
        hdr: HDR 画像。``(H, W)`` or ``(H, W, C)``、放射輝度 >= 0。
        exposure: 写像前に掛ける露出スケール(正)。
    Returns:
        ``[0, 1]`` の float64 LDR 画像(入力と同形状)。
    Raises:
        ValueError: 空/非有限/負の放射輝度、非正の exposition(fail-closed)。
    """
    H = _as_hdr(hdr)
    e = _check_exposure(exposure)
    x = H * e
    num = x * (_ACES_A * x + _ACES_B)
    den = x * (_ACES_C * x + _ACES_D) + _ACES_E
    ld = num / den
    return np.clip(ld, 0.0, 1.0)
