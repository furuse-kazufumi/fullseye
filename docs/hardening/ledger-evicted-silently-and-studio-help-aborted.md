---
id: ledger-evicted-silently-and-studio-help-aborted
date: 2026-09-20
found_by: genspark_external_review
kind: discoverability
severity: low
where: [backend_safe.py, api.py, studio.py, fullseye/__init__.py]
ops: []
gate: [test_fallback_ring_counts_what_it_evicts, test_studio_help_and_version_answer_without_qt, test_studio_without_a_display_stops_with_a_sentence_not_an_abort, test_facade_namespace_has_no_import_tools]
status: fixed
---

# 台帳が黙って古い事象を捨て、studio の `--help` が abort し、facade に import の道具が漏れていた

## 症状

GenSpark 第 43・44・50 報(2026-09-20)。

- **N158**: fallback の台帳は 256 件の環状バッファ。257 件目から古い方が黙って消え、`fallback_counts()` の合計と
  `len(fallbacks())` が合わない理由が利用者から見えない。
- **N154**: `fullseye-studio --help` が表示の無い Linux で SIGABRT(Qt の `QApplication` が display に繋げず abort)。
  `main()` は引数を読まず、いきなり Qt を起こしていた。
- **N175 / N176**: `import fullseye; fullseye.os` / `fullseye.sys` / `fullseye.warnings` / `fullseye.annotations` が通る。
  `__init__.py` が import に使った道具がそのまま名前空間に残り、tab 補完と `dir()` を汚す。

## なぜ門が通したか

台帳の門は「記録される」「256 件で止まる」を問い、「捨てた数が分かる」を問わなかった。studio の門は
`build_window()` を offscreen で起こすところから始まり、**入口の `main()` を引数つきで叩く門が無かった**
([[feedback_gate_must_stand_where_the_accident_happens]])。名前空間は `__all__` だけを見ていた。

## 直し

1. `fullseye.fallback_overflow()`: 最後の `clear_fallbacks()` 以降に環から捨てた件数。
   `sum(fallback_counts().values()) == len(fallbacks()) + fallback_overflow()` が恒等式(門)。
2. `studio.main(argv)`: `-h` / `--help` / `--version` は Qt を起こさず答える。未知の引数は usage + rc 2。Linux で
   `DISPLAY` / `WAYLAND_DISPLAY` / `QT_QPA_PLATFORM` のどれも無ければ「no display … set QT_QPA_PLATFORM=offscreen」の
   1 文で rc 2(abort でなく)。
3. `fullseye/__init__.py` の末尾で `del os, sys, warnings, annotations`。
