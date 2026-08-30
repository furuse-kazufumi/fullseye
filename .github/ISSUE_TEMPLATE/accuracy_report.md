---
name: Accuracy / honesty report / 精度・正直さ報告
about: A measured value, unit, claim or doc that doesn't match reality
labels: honesty
---

<!-- fullseye の家訓は honest disclosure です。「数字が合わない」「docstring の主張と
     実挙動が違う」「単位系が怪しい」という報告は最優先で歓迎します。
     (この分類のバグは実在しました: 曲率の絶対値が 32 倍ズレ・法線の符号が逆 …
     どちらも「比率や abs() のテストは通る」タイプでした) -->

## The claim / 問題の主張(docstring・docs/ops ノート・記事のどこか)

## Measured reality / 実測

```python
# The measurement that disagrees (ground-truth input + expected + actual).
```

## Severity guess / 影響の見立て

<!-- e.g. "wrong absolute scale, ratios unaffected" / "sign flip in the primary use case" -->
