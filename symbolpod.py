# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""読み取りの検出確率(POD)—— 物理劣化を 1 つ掃引し、「どの量まで 90 % で読めるか」を返す鎖。

Read-rate POD for symbols: sweep one physical degradation (defocus, motion blur,
ink spread, tilt, contrast, sensor noise, module size …) over a synthetic symbol
whose content is known, read every capture, and fit the hit/miss POD model of
MIL-HDBK-1823A (:func:`pod.pod_hitmiss_fit`, already in Fullseye) to the outcomes.
The answer is the degradation level read with 90 % probability (``level90``) and its
95 %-confidence conservative bound (``level90_95``) — the "a90/95" of NDT, with the
flaw size replaced by the degradation that the reader must survive.

★結果を 3 通りに分ける(成功 / **誤読** / 読み取り不能)。誤読は読み取り不能よりはるかに
危険なので 1 つの読取率に畳まない(``examples/poc_barcode_1d.py`` が実測で示した教訓)。
POD は成功だけを「当たり」として当て、誤読は別に数えて Clopper-Pearson の片側上限
(:func:`pod.proportion_interval`)を付ける。
Outcomes are split into success / misread / no-read; the POD uses successes only and
misreads get their own one-sided Clopper-Pearson upper bound.

試行ごとに変わるもの(既定)/ per-trial nuisance (defaults): 平面内の回転(一様 0..360°、
1-D は ±``rotate_jitter_deg``)、画素以下の位置(0..1 px)、センサのショット雑音・読み出し
雑音の種。これが無いと劣化量に対して結果が決定的になり、POD の当てはめは「完全分離」で
止まる(それは「この条件の読み取りは偶然ではなく決まっている」という情報であって、
POD ではない)。
"""
from __future__ import annotations

import numpy as np

import pod as _pod
import symrender as _sr

__all__ = ["READERS", "DEGRADATION_FACTORS", "OCR_FACTORS", "symbol_read", "symbol_read_trials",
           "symbol_read_pod", "ocr_read_trials"]

#: 劣化の因子 → (どの段の引数か, 大きいほど悪いか)。
#: factor -> (stage, worse when larger?)
DEGRADATION_FACTORS = {
    "defocus_px": ("capture", True),
    "motion_px": ("capture", True),
    "gauss_px": ("capture", True),
    "illum_slope": ("capture", True),
    "vignette": ("capture", True),
    "read_noise_e": ("capture", True),
    "full_well_e": ("capture", False),
    "tilt_deg": ("render", True),
    "ink_gain": ("render", True),
    "ink_loss": ("render", True),      # = −ink_gain(細る側)
    "module_px": ("render", False),
    "contrast": ("render", False),     # light − dark(light は固定)
}

READERS = ("barcode1d", "qr", "datamatrix", "zxing")

#: Fullseye の体系名 → zxing-cpp の形式名 / Fullseye symbology -> zxing-cpp format.
ZXING_FORMATS = {"ean13": "EAN13", "upca": "UPCA", "code128": "Code128", "code39": "Code39Std",
                 "itf": "ITF", "qr": "QRCode", "datamatrix": "DataMatrix"}


def _reader_for(symbol, reader):
    if reader not in (None, "auto") + READERS:
        raise ValueError("symbol_read: reader must be 'auto' or one of %s, got %r" % (READERS, reader))
    if reader in (None, "auto"):
        if not isinstance(symbol, dict):
            raise ValueError("symbol_read: reader='auto' needs a symbol table")
        if "edges" in symbol:
            reader = "barcode1d"
        elif "version" in symbol:
            reader = "qr"
        elif "modules" in symbol:
            reader = "datamatrix"
        else:
            raise ValueError("symbol_read: cannot tell the symbology of this table")
    return reader


def symbol_read(image, reader="barcode1d", symbologies=None):
    """画像を指定の読み取り器で読み、``{"ok", "text", "error"}`` を返す(``table``)。

    Read an image with one of the family's readers (``"barcode1d"`` =
    :func:`barcode1d.read_barcode1d`, ``"qr"`` = ``qrsym.qr_read``, ``"datamatrix"`` =
    ``dmsym.dm_read``, ``"zxing"`` = :func:`symzxing.read_symbols_zxing`, optional extra,
    restricted to ``symbologies`` mapped by :data:`ZXING_FORMATS`; its UPC-A answer is
    normalised to 12 digits) and return ``ok`` (decoded at all), ``text`` (None if not) and
    ``error`` (the reader's message on a no-read). A no-read is not an exception here —
    it is an outcome to be counted.

    空の入力は ``ValueError``(読み取り器の検査をそのまま通す)。
    拒否(``ValueError``): 未知の ``reader``、2-D でない、非有限。
    """
    if reader not in READERS:
        raise ValueError("symbol_read: reader must be one of %s, got %r" % (READERS, reader))
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or a.size == 0 or not np.isfinite(a).all():
        raise ValueError("symbol_read: image must be a finite, non-empty 2-D array")
    try:
        if reader == "barcode1d":
            import barcode1d
            r = barcode1d.read_barcode1d(a, symbologies)
            if r["conflict"]:
                # 走査線どうしが食い違う = 誤読の兆候。多数決の文字列を返しつつ旗を残す
                return {"ok": True, "text": r["text"], "error": None, "conflict": True}
        elif reader == "qr":
            import qrsym
            r = qrsym.qr_read(a)
        elif reader == "datamatrix":
            import dmsym
            r = dmsym.dm_read(a)
        else:
            import symzxing
            fm = None
            if symbologies is not None:
                fm = [ZXING_FORMATS[s] for s in symbologies if s in ZXING_FORMATS]
            z = symzxing.read_symbols_zxing(a, fm)
            if z["n"] == 0:
                return {"ok": False, "text": None, "error": "zxing-cpp found no symbol"}
            t = z["texts"][0]
            if symbologies is not None and "upca" in symbologies and len(t) == 13 and t[0] == "0":
                t = t[1:]
            return {"ok": True, "text": t, "error": None, "conflict": z["n"] > 1}
    except ValueError as exc:            # 各読み取り器の「読めない」は ValueError の派生
        return {"ok": False, "text": None, "error": str(exc)}
    return {"ok": True, "text": r["text"], "error": None}


def _levels(levels, op):
    lv = np.asarray(levels, dtype=np.float64).reshape(-1)
    if lv.size < 3:
        raise ValueError("%s: need at least 3 levels to fit a POD curve, got %d" % (op, lv.size))
    if not np.isfinite(lv).all():
        raise ValueError("%s: levels must be finite" % op)
    if np.unique(lv).size != lv.size:
        raise ValueError("%s: levels must be distinct" % op)
    return np.sort(lv)


def symbol_read_trials(symbol, factor, levels, *, trials=20, reader="auto", symbologies=None,
                       truth=None, module_px=4.0, render=None, capture=None, rotate="random",
                       rotate_jitter_deg=5.0, level_jitter=0.0, refine=False, seed=0):
    """劣化量の各水準でシンボルを ``trials`` 回撮って読み、1 行 = 1 回の結果の表を返す(``table``)。

    For each level of the degradation ``factor`` (see :data:`DEGRADATION_FACTORS`),
    render the symbol (:func:`symrender.render_symbol`), capture it
    (:func:`symrender.capture_degrade`) and read it (:func:`symbol_read`), ``trials``
    times with fresh nuisance: in-plane rotation (``rotate="random"``: uniform over
    360° for 2-D symbols, ±``rotate_jitter_deg`` around 0 for 1-D; a number fixes it),
    a sub-pixel offset in [0, 1) px and the sensor-noise seed. For a 1-D table the
    reader is restricted to the table's own symbology unless ``symbologies`` is given
    (a line reader enables only what it expects; all-symbology reading short-reads). ``render`` / ``capture``
    hold the fixed settings of the other knobs; the sensor defaults to
    ``full_well_e = 20000``, ``read_noise_e = 10``, 8 bits. ``truth`` defaults to the
    table's ``text``.

    Returns columns ``level``, ``trial``, ``hit`` (1 = read the true text), ``misread``
    (1 = read a different text), ``noread``, ``text`` (object array), plus
    ``factor``, ``worse_when_larger``, ``truth``, ``reader``, ``stage``.

    ``level_jitter`` (relative, default 0) multiplies each trial's actual level by
    ``1 + level_jitter · N(0, 1)`` while the table keeps the nominal level — the
    process variation of the line (e.g. part height moving the focus). It is a
    declared assumption, not a fit knob.

    ``refine=True`` first runs every level with ``max(4, trials // 4)`` trials, brackets
    the transition (the last level read >= 95 % and the first read <= 5 %, in the order of
    increasing degradation) and then runs ``len(levels)`` evenly spaced levels across
    that bracket with ``trials`` each (``stage`` = ``"coarse"`` / ``"fine"``; both enter
    the table). Without it a coarse sweep easily ends in complete separation.

    空の入力(``levels`` が 3 未満)は ``ValueError``。
    拒否(``ValueError``): 未知の ``factor``、``trials`` < 1、水準の重複・非有限、
    ``render`` / ``capture`` に掃引中の因子と同じ鍵、読み取り器を決められない表。
    """
    op = "symbol_read_trials"
    if factor not in DEGRADATION_FACTORS:
        raise ValueError("%s: factor must be one of %s, got %r" % (op, sorted(DEGRADATION_FACTORS), factor))
    lv = _levels(levels, op)
    if isinstance(trials, bool) or not isinstance(trials, (int, np.integer)) or trials < 1:
        raise ValueError("%s: trials must be a positive integer, got %r" % (op, trials))
    rd = _reader_for(symbol, reader)
    if rd == "zxing" and symbologies is None and isinstance(symbol, dict):
        if "symbology" in symbol:
            symbologies = ("upca",) if symbol["symbology"] == "upca" else (symbol["symbology"],)
        else:
            symbologies = ("qr",) if "version" in symbol else ("datamatrix",)
    if rd == "barcode1d" and symbologies is None and isinstance(symbol, dict) and "symbology" in symbol:
        # 現場の読み取り器は使う体系だけを有効にする / enable only the symbology in use
        symbologies = ("ean13", "upca") if symbol["symbology"] in ("ean13", "upca") \
            else (symbol["symbology"],)
    if truth is None:
        if not isinstance(symbol, dict) or "text" not in symbol:
            raise ValueError("%s: give truth= when the symbol table has no 'text'" % op)
        truth = symbol["text"]
    rkw = dict(render or {})
    ckw = {"full_well_e": 20000.0, "read_noise_e": 10.0, "bits": 8}
    ckw.update(capture or {})
    stage, worse_large = DEGRADATION_FACTORS[factor]
    key = {"ink_loss": "ink_gain", "contrast": "dark"}.get(factor, factor)
    if key in rkw or key in ckw and stage == "capture" and factor in (capture or {}):
        raise ValueError("%s: %r is being swept — do not also fix it in render/capture" % (op, factor))
    rkw.setdefault("module_px", float(module_px))
    light = float(rkw.get("light", 0.85))
    jit = float(level_jitter)
    if not np.isfinite(jit) or not 0.0 <= jit <= 0.5:
        raise ValueError("%s: level_jitter must lie in [0, 0.5], got %r" % (op, level_jitter))
    rng = np.random.default_rng(seed)
    rows = {"level": [], "trial": [], "hit": [], "misread": [], "noread": [], "text": [],
            "stage": []}
    is1d = rd == "barcode1d" or (isinstance(symbol, dict) and "edges" in symbol)

    def run(levels_, n_trials, tag):
        for L in levels_:
            for t in range(int(n_trials)):
                r = dict(rkw)
                c = dict(ckw)
                La = float(L) * (1.0 + jit * float(rng.standard_normal())) if jit > 0 else float(L)
                if factor == "contrast":
                    r["dark"] = light - La
                    r["light"] = light
                elif factor == "ink_loss":
                    r["ink_gain"] = -La
                elif stage == "render":
                    r[key] = La
                else:
                    c[key] = La if factor == "illum_slope" else max(La, 0.0)
                if rotate == "random":
                    r["rotate_deg"] = float(rng.uniform(-rotate_jitter_deg, rotate_jitter_deg)) if is1d                         else float(rng.uniform(0.0, 360.0))
                else:
                    r["rotate_deg"] = float(rotate)
                r["offset_px"] = (float(rng.uniform(0, 1)), float(rng.uniform(0, 1)))
                c["seed"] = int(rng.integers(0, 2 ** 31 - 1))
                img = _sr.capture_degrade(_sr.render_symbol(symbol, **r), **c)
                res = symbol_read(img, rd, symbologies)
                hit = bool(res["ok"] and res["text"] == truth)
                mis = bool(res["ok"] and res["text"] != truth)
                rows["level"].append(float(L))
                rows["trial"].append(t)
                rows["hit"].append(int(hit))
                rows["misread"].append(int(mis))
                rows["noread"].append(int(not res["ok"]))
                rows["text"].append(res["text"])
                rows["stage"].append(tag)

    if not refine:
        run(lv, trials, "main")
    else:
        # 粗い掃引で境目を挟み、その区間を同じ本数の水準で細かく掃引する
        # coarse bracket, then the same number of levels across the transition
        n_coarse = max(4, int(trials) // 4)
        run(lv, n_coarse, "coarse")
        lev = np.asarray(rows["level"])
        hits = np.asarray(rows["hit"])
        rate = np.array([hits[lev == v].mean() for v in lv])
        order = lv if worse_large else lv[::-1]          # 劣化の弱い順 / mild -> severe
        rate_o = rate if worse_large else rate[::-1]
        good = np.flatnonzero(rate_o >= 0.95)
        bad = np.flatnonzero(rate_o <= 0.05)
        lo_i = int(good.max()) if good.size else 0
        hi_c = bad[bad > lo_i]
        hi_i = int(hi_c.min()) if hi_c.size else order.size - 1
        if hi_i <= lo_i:
            hi_i = min(lo_i + 1, order.size - 1)
        a_, b_ = float(order[lo_i]), float(order[hi_i])
        fine = np.linspace(min(a_, b_), max(a_, b_), lv.size)
        run(fine, trials, "fine")
    out = {k: np.asarray(v) for k, v in rows.items() if k != "text"}
    out["text"] = np.asarray(rows["text"], dtype=object)
    out.update({"factor": factor, "worse_when_larger": bool(worse_large), "truth": truth,
                "reader": rd})
    return out


def symbol_read_pod(trials_table, *, link="logit", level=0.95):
    """読み取りの試行表から、POD(当たり = 真の文字列を読めた)と誤読の上限を返す(``table``)。

    Fit the hit/miss POD (:func:`pod.pod_hitmiss_fit`) to a table from
    :func:`symbol_read_trials`. When the factor is worse when larger (defocus, noise …)
    the fit runs on ``x = −level`` so that POD rises with ``x``, and the answers are
    mapped back: ``level90`` = the degradation read with 90 % probability,
    ``level90_95`` = its conservative bound at ``level`` confidence (a *smaller*
    degradation), ``level50`` likewise. When the factor is better when larger (module
    size, contrast, full well) ``level90_95`` is the *larger* value.

    ``method = "hitmiss_glm"`` then. ★When the outcome is decided by the level (complete
    separation — every capture read up to one level and none beyond), the slope is not
    estimable; the op then returns ``method = "all_success_demonstration"``: the most
    severe level at which every trial read (``separation_bracket`` = that level and the
    first one with a failure), and ``level90_95`` = that level only if it holds at least
    :func:`pod.trials_for_all_success` (0.90, ``level``) trials (29 at 95 %), else None.
    ``level50`` / ``level90`` are None in that case.

    ★``monotone`` is False when a more degraded level reads more often than a milder
    one by more than 3 standard errors (``nonmonotone_z``): the POD models assume
    monotone degradation, so the fitted numbers are then outside their premise (seen
    with a reader that cannot read sharp dot-peen marks but reads them once blur merges
    the dots). The result is still returned, flagged.

    Also returns ``per_level`` (level, n, hits, misreads, noreads, read_rate),
    ``misread_total`` / ``decoded_total`` and ``misread_rate_upper`` (one-sided
    Clopper-Pearson upper bound of misreads per decode at ``level``; with zero misreads
    in n decodes it is ``1 − (1 − level)^(1/n)``), ``fit`` (the POD table) and ``factor``.

    空の入力(0 行)は ``ValueError``。
    拒否(``ValueError``): 列の欠け、全部読めた/全部読めない、``level`` が (0, 1) の外。
    完全分離は拒否せず上の「全数成功の実証」で返す(傾きの無い POD を作らない)。
    """
    op = "symbol_read_pod"
    if not isinstance(trials_table, dict):
        raise ValueError("%s: expected the table from symbol_read_trials" % op)
    for k in ("level", "hit", "misread", "noread", "worse_when_larger", "factor"):
        if k not in trials_table:
            raise ValueError("%s: the table lacks %r" % (op, k))
    L = np.asarray(trials_table["level"], dtype=np.float64)
    if L.size == 0:
        raise ValueError("%s: the table is empty" % op)
    hit = np.asarray(trials_table["hit"]).astype(int)
    mis = np.asarray(trials_table["misread"]).astype(int)
    nor = np.asarray(trials_table["noread"]).astype(int)
    if not (L.size == hit.size == mis.size == nor.size):
        raise ValueError("%s: columns differ in length" % op)
    worse = bool(trials_table["worse_when_larger"])
    x = -L if worse else L
    lv_f = float(level)
    if not np.isfinite(lv_f) or not 0.0 < lv_f < 1.0:
        raise ValueError("%s: level must be in (0, 1), got %r" % (op, level))
    sgn = -1.0 if worse else 1.0
    per = []
    for v in np.unique(L):
        m = L == v
        n = int(m.sum())
        per.append({"level": float(v), "n": n, "hits": int(hit[m].sum()),
                    "misreads": int(mis[m].sum()), "noreads": int(nor[m].sum()),
                    "read_rate": float(hit[m].mean())})
    # 単調性: 劣化の弱い順に並べて、強い側の読取率が弱い側を 3 σ 超えて上回る組を探す。
    # POD の当てはめは単調を仮定する —— 破れていればモデルの前提の外(結果に旗を立てる)。
    # monotonicity: POD models assume reads get rarer as degradation grows.
    order = sorted(per, key=lambda d: d["level"], reverse=not worse)
    max_z = 0.0
    for a_i in range(len(order)):
        for b_i in range(a_i + 1, len(order)):
            pa, pb = order[a_i], order[b_i]
            pbar = (pa["hits"] + pb["hits"]) / float(pa["n"] + pb["n"])
            se = np.sqrt(max(pbar * (1 - pbar), 1e-9) * (1.0 / pa["n"] + 1.0 / pb["n"]))
            max_z = max(max_z, (pb["read_rate"] - pa["read_rate"]) / se)
    ndec = int(hit.sum() + mis.sum())
    ci = _pod.proportion_interval(int(mis.sum()), max(ndec, 1), confidence=lv_f, sides="upper") \
        if ndec > 0 else {"upper": 1.0}
    common = {"factor": trials_table["factor"], "worse_when_larger": worse, "per_level": per,
              "misread_total": int(mis.sum()), "decoded_total": ndec,
              "misread_rate_upper": float(ci["upper"]), "confidence": lv_f,
              "monotone": bool(max_z <= 3.0), "nonmonotone_z": float(max_z)}
    if hit.sum() == 0 or hit.sum() == hit.size:
        raise ValueError("%s: every capture was %s — a POD needs both reads and failures; "
                         "widen the levels" % (op, "read" if hit.sum() else "unread"))
    try:
        fit = _pod.pod_hitmiss_fit({"a": x, "hit": hit}, size="a", hit="hit", link=link, level=lv_f)
    except ValueError as exc:
        if "separation" not in str(exc):
            raise ValueError("%s: the POD fit failed for factor %r — %s"
                             % (op, trials_table["factor"], exc)) from exc
        # ★完全分離: 劣化量に対して読めるかどうかが決まっていて、傾きは推定できない。
        # 代わりに「全数成功の実証」(MIL-HDBK-1823A の 29/29 と同じ論法)を返す:
        # すべて読めた最も厳しい水準 L* と、そこでの試行数が p=0.90 を片側 level で
        # 示すのに足りるか(:func:`pod.trials_for_all_success`)。
        # Complete separation: report the all-success demonstration instead.
        need = _pod.trials_for_all_success(0.90, confidence=lv_f)
        order = sorted(per, key=lambda d: d["level"], reverse=not worse)   # mild -> severe
        last_ok, first_bad = None, None
        for d in order:
            if first_bad is not None:
                break
            if d["hits"] == d["n"]:
                last_ok = d
            else:
                first_bad = d
        demo = last_ok is not None and last_ok["n"] >= need
        out = dict(common)
        out.update({"method": "all_success_demonstration", "level50": None, "level90": None,
                    "level90_95": last_ok["level"] if demo else None, "level90_95_lr": None,
                    "trials_needed": int(need),
                    "separation_bracket": (None if last_ok is None else last_ok["level"],
                                           None if first_bad is None else first_bad["level"]),
                    "beyond_data": False, "fit": None})
        return out
    out = dict(common)
    out.update({"method": "hitmiss_glm", "level50": sgn * fit["a50"], "level90": sgn * fit["a90"],
                "level90_95": sgn * fit["a90_95"],
                "level90_95_lr": None if fit.get("a90_95_lr") is None else sgn * fit["a90_95_lr"],
                "beyond_data": bool(fit.get("a90_95_beyond_data", False)), "fit": fit,
                "separation_bracket": None, "trials_needed": None})
    return out


# --------------------------------------------------------------------------- #
# OCR の可読性の POD / legibility POD for classical OCR
# --------------------------------------------------------------------------- #
#: OCR の劣化の因子 → (段, 大きいほど悪いか)。
OCR_FACTORS = {
    "defocus_px": ("capture", True),
    "motion_px": ("capture", True),
    "gauss_px": ("capture", True),
    "illum_slope": ("capture", True),
    "vignette": ("capture", True),
    "read_noise_e": ("capture", True),
    "full_well_e": ("capture", False),
    "ink_gain": ("render", True),        # にじみ(ドット径・線幅が (1 + g) 倍)
    "ink_loss": ("render", True),        # = −ink_gain(かすれ)
    "char_height_px": ("render", False),
    "contrast": ("render", False),
}


def ocr_read_trials(text, factor, levels, *, model, font=None, char_height_px=24.0, trials=20,
                    render=None, capture=None, level_jitter=0.0, refine=False, seed=0):
    """印字した文字列を劣化量の各水準で ``trials`` 回撮って OCR で読み、1 行 = 1 回の表を返す(``table``)。

    Legibility trials for classical OCR: render ``text`` with the built-in font
    (``ocrclassic.ocr_render_text``; ``font`` defaults to the model's font), apply the
    capture chain (:func:`symrender.capture_degrade`, sensor 20000 e / 10 e / 8 bit by
    default) with the swept ``factor`` (:data:`OCR_FACTORS`), and read the line with
    ``ocrclassic.ocr_read_line``. Each trial draws a fresh sub-pixel offset of the line
    and a sensor-noise seed. Outcomes per capture: ``hit`` = the whole string read
    exactly, ``misread`` = at least one character read as a *different* character
    (substituted or inserted, per ``ocrclassic.ocr_score``) — the dangerous case, never
    folded into the read rate —, ``noread`` = otherwise (rejects ``?`` or missing
    characters only). The table has the same columns as :func:`symbol_read_trials`
    (plus ``rejected_chars`` / ``substituted_chars``) so :func:`symbol_read_pod` fits it.
    ``refine`` and ``level_jitter`` work as in :func:`symbol_read_trials`.

    空の入力(``text == ""`` / ``levels`` が 3 未満)は ``ValueError``。
    拒否(``ValueError``): 未知の ``factor``、``trials`` < 1、水準の重複・非有限、
    字種の外の文字、``render`` / ``capture`` に掃引中の因子と同じ鍵、``level_jitter`` が
    [0, 0.5] の外、OCR の模型でない ``model``。
    """
    op = "ocr_read_trials"
    import ocrclassic
    if not isinstance(text, str) or text == "":
        raise ValueError("%s: text must be a non-empty string" % op)
    if factor not in OCR_FACTORS:
        raise ValueError("%s: factor must be one of %s, got %r" % (op, sorted(OCR_FACTORS), factor))
    if not isinstance(model, dict) or "features" not in model or "labels" not in model:
        raise ValueError("%s: model must be the table from ocr_train" % op)
    lv = _levels(levels, op)
    if isinstance(trials, bool) or not isinstance(trials, (int, np.integer)) or trials < 1:
        raise ValueError("%s: trials must be a positive integer, got %r" % (op, trials))
    jit = float(level_jitter)
    if not np.isfinite(jit) or not 0.0 <= jit <= 0.5:
        raise ValueError("%s: level_jitter must lie in [0, 0.5], got %r" % (op, level_jitter))
    stage, worse_large = OCR_FACTORS[factor]
    key = {"ink_loss": "ink_gain"}.get(factor, factor)
    rkw = dict(render or {})
    ckw = {"full_well_e": 20000.0, "read_noise_e": 10.0, "bits": 8}
    if key in rkw or (capture and key in capture):
        raise ValueError("%s: %r is being swept — do not also fix it in render/capture" % (op, factor))
    ckw.update(capture or {})
    fnt = font if font is not None else model.get("font", "dot5x7")
    rkw.setdefault("char_height_px", float(char_height_px))
    ocrclassic.ocr_render_text(text, font=fnt, **rkw)          # 字種と引数を先に検査する
    rng = np.random.default_rng(seed)
    rows = {"level": [], "trial": [], "hit": [], "misread": [], "noread": [], "text": [],
            "stage": [], "rejected_chars": [], "substituted_chars": []}

    def run(levels_, n_trials, tag):
        for L in levels_:
            for t in range(int(n_trials)):
                r = dict(rkw)
                c = dict(ckw)
                La = float(L) * (1.0 + jit * float(rng.standard_normal())) if jit > 0 else float(L)
                if factor == "ink_loss":
                    r["ink_gain"] = -La
                elif factor == "char_height_px":
                    r[key] = max(La, 6.0)              # 描画の下限(6 px)で揺らぎを切る
                elif stage == "render":
                    r[key] = La
                else:
                    c[key] = La if factor == "illum_slope" else max(La, 0.0)
                r["subpixel_offset"] = (float(rng.uniform(0, 1)), float(rng.uniform(0, 1)))
                c["seed"] = int(rng.integers(0, 2 ** 31 - 1))
                img = _sr.capture_degrade(ocrclassic.ocr_render_text(text, font=fnt, **r)["image"], **c)
                got = ocrclassic.ocr_read_line(img, model)["text"]
                sc = ocrclassic.ocr_score(got, text)
                hit = got == text
                # 「?」でない字の挿入 = 読めた字の数 − 正解 − 置換 / non-"?" insertions
                ins_real = sum(ch != "?" for ch in got) - sc["correct"] - sc["substituted"]
                mis = (not hit) and (sc["substituted"] > 0 or ins_real > 0)
                rows["level"].append(float(L))
                rows["trial"].append(t)
                rows["hit"].append(int(hit))
                rows["misread"].append(int(mis))
                rows["noread"].append(int(not hit and not mis))
                rows["text"].append(got)
                rows["stage"].append(tag)
                rows["rejected_chars"].append(int(sc["rejected"]))
                rows["substituted_chars"].append(int(sc["substituted"]))

    if not refine:
        run(lv, trials, "main")
    else:
        n_coarse = max(4, int(trials) // 4)
        run(lv, n_coarse, "coarse")
        fine = _bracket(np.asarray(rows["level"]), np.asarray(rows["hit"]), lv, worse_large)
        run(fine, trials, "fine")
    out = {k: np.asarray(v) for k, v in rows.items() if k != "text"}
    out["text"] = np.asarray(rows["text"], dtype=object)
    out.update({"factor": factor, "worse_when_larger": bool(worse_large), "truth": text,
                "reader": "ocr"})
    return out


def _bracket(lev, hits, lv, worse_large):
    """粗い掃引から境を挟み、同じ本数の細かい水準を返す(symbol_read_trials と同じ規則)。"""
    rate = np.array([hits[lev == v].mean() for v in lv])
    order = lv if worse_large else lv[::-1]
    rate_o = rate if worse_large else rate[::-1]
    good = np.flatnonzero(rate_o >= 0.95)
    bad = np.flatnonzero(rate_o <= 0.05)
    lo_i = int(good.max()) if good.size else 0
    hi_c = bad[bad > lo_i]
    hi_i = int(hi_c.min()) if hi_c.size else order.size - 1
    if hi_i <= lo_i:
        hi_i = min(lo_i + 1, order.size - 1)
    a_, b_ = float(order[lo_i]), float(order[hi_i])
    return np.linspace(min(a_, b_), max(a_, b_), lv.size)
