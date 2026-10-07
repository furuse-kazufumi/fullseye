<!-- i18n-source-sha: c70ba3c329f3 -->
# शुरुआत करें (5 मिनट में चालू)

[日本語](./GETTING_STARTED.md) · [English](./GETTING_STARTED.en.md) · [简体中文](./GETTING_STARTED.zh.md) · [繁體中文](./GETTING_STARTED.tw.md) · [한국어](./GETTING_STARTED.ko.md) · [Deutsch](./GETTING_STARTED.de.md) · **हिन्दी**

## आपका काम कौन-सा है? (शुरू करने के तीन रास्ते)

Fullseye बहुत बड़ा है, इसलिए अगर आप तय न कर पाएँ कि **सबसे पहले कौन-सी एक file खोलें**, तो आप अटक जाते हैं। नीचे
दिए गए examples नए लिखे गए demos नहीं हैं, बल्कि **ऐसे examples हैं जिन्हें एक gate हर बार पहले से चलाता है** (अगर कोई
टूटता है, तो CI red हो जाता है)।

| रास्ता | किसके लिए | 5 मिनट: बस चलाएँ | 30 मिनट: अंदर का काम समझें | आधा दिन: अपने data पर |
|---|---|---|---|---|
| **Explainable visual inspection** | inspection / QA | `py -3.11 examples/poc_solder_fillet_aoi.py` — solder fillet का AOI | `py -3.11 examples/poc_fabric_defect.py` — misses और false alarms को अलग-अलग गिनें | [CAPABILITIES.md](CAPABILITIES.md) में "Detect" → Studio में अपनी image |
| **Robots के लिए 3-D** | robotics / 3-D metrology | `py -3.11 examples/perception_pipeline.py` — stereo → depth → point cloud → traversability | `py -3.11 examples/grasp_pose.py` — 6-DoF pose और grasp direction के लिए point cloud को model पर fit करें | [EXAMPLES_3D.md](EXAMPLES_3D.md) → अपना cloud/mesh दें |
| **Physics-based NDT** | X-ray / optics / metrology | `py -3.11 examples/ct_reconstruction.py` — projection → reconstruction → mm में dimensions और defect count | `py -3.11 examples/poc_ct_void_morphology.py` — एक अकेला pass/fail number shape को क्यों नहीं देख पाता | [CAPABILITIES.md](CAPABILITIES.md) में "Shape" → अपना volume |

हर example के साथ **ground truth होता है** (closed-form या synthetic)। यह हमेशा null case (कुछ न करना)
भी print करता है, ताकि आप खुद तय कर सकें कि कुछ "काम किया" या नहीं। हर चीज़ असल में कितनी validated है,
इसका ledger [MATURITY.md](MATURITY.md) है — यह हाथ से नहीं लिखा जाता, बल्कि चलने वाले gates और
असली data शामिल था या नहीं, इससे गिना जाता है।

---

यह गाइड Fullseye (working name imgevolve) को सबसे छोटे रास्ते से चालू करती है: **install → अपनी
पहली pipeline बनाएँ → चलाएँ → result देखें**, ऐसे क्रम में जिसमें आप अटकें नहीं। पूरे setup के लिए
[INSTALL.md](INSTALL.md) देखें, Studio की सारी सुविधाओं के लिए
[STUDIO_GUIDE.md](STUDIO_GUIDE.md), और code से चलाने के लिए [ENGINE.md](ENGINE.md)।

Fullseye एक **image-processing operator library है जिसके inputs और outputs numpy arrays हैं**,
और इसके ऊपर एक **HDevelop-style visual pipeline-design environment (Fullseye Studio)** और एक **execution
runtime (FullseyeEngine)** है। HALCON/HDevelop की भाषा में, यह
"HDevelop में procedure जोड़ें, अपनी app से HDevEngine के ज़रिए call करें" वाले दो-चरण के ढाँचे को सीधे
Python + numpy में दोहराता है।

---

## 1. Install (1 मिनट)

Prerequisite: **Python 3.11** (Windows पर `py -3.11`, Linux पर `python3.11`)।

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # core only (numpy + scipy; every op is listed, and an op that needs an optional backend names the missing extra when called)
```

Core **सिर्फ़ numpy और scipy** पर चलता है। OpenCV / scikit-image / Pillow जैसे extra backends
optional हैं; अगर कोई install नहीं है, तो सिर्फ़ उसी backend के अपने operators बंद होते हैं (graceful
degradation)। व्यवहार में image files पढ़ने और लिखने के लिए आपको कम से कम OpenCV या Pillow चाहिए,
इसलिए इनमें से एक जोड़ने से काम आसान हो जाता है:

```powershell
py -3.11 -m pip install -e ".[opencv]"    # image I/O + OpenCV-derived operators
py -3.11 -m pip install -e ".[all]"       # all backends (opencv, skimage, pil, wavelets, gpu, extra)
py -3.11 -m pip install -e ".[gui]"       # if you want Fullseye Studio (PySide6)
```

Extras की list और हर एक का मतलब [INSTALL.md](INSTALL.md) में इकट्ठा है। GUI इस्तेमाल करने के लिए
आपको `[gui]` चाहिए (या `[all]` + `[gui]`)।

> आप install किए बिना भी आज़मा सकते हैं। Repository root (`<path-to-fullseye>`) को अपनी
> working directory बनाएँ और उस path को `PYTHONPATH` environment variable में डालें, तो `import
> fullseye` काम करेगा। लेकिन `fullseye` / `fullseye-studio` commands (console scripts)
> तभी उपलब्ध होते हैं जब आप `pip install -e .` चलाते हैं।

---

## 2. पहले एक अकेला operator चलाएँ (Python)

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image (gradient magnitude)
seg   = fullseye.apply(frame, "otsu")          # image → region (0/1 binary)
n     = fullseye.apply(seg,   "count_obj")     # region → feature (object count = Python float)
print(n)                                       # e.g. 316.0
```

> **Argument का क्रम `apply(image, name, a, b)` है** — पहला argument array है,
> दूसरा op name। उल्टा pass करने पर 0.1.9 से `TypeError: ... arguments look
> swapped` के साथ रुक जाता है (0.1.8 तक यह numpy की असंबंधित "truth value of an array is
> ambiguous" error बन जाती थी)। `a`/`b` 0..1 में finite values हैं। String / `None` / NaN तुरंत
> `TypeError`/`ValueError` देते हैं; range से बाहर की values clamp होकर ledger में दर्ज होती हैं।

- `apply(image, name, a=0.5, b=0.5)` **एक operator** लागू करता है। `name` या तो
  **operator name** (जैसे `gaussian`) या **HALCON alias** (जैसे `gauss_filter`) के रूप में resolve होता है।
- `a`, `b` वे **दो knobs (0.0–1.0)** हैं जो हर operator में होते हैं। इनका मतलब हर
  operator में अलग है (radius / threshold / σ आदि)।
- Output type (sort) operator से तय होता है: `image` (gray) / `region` (binary) /
  `feature` (scalar float) / `color` (RGB) / `contour` (XLD) / `volume` (3D)।
- **Failure पर क्या होता है** (2026-09-03 से): default `on_error="fallback"` में, अगर
  कोई op अंदर fail भी हो जाए तो वह type से मेल खाती एक हानिरहित value लौटाता है (image के लिए input की copy
  आदि), और **हर op के लिए सिर्फ़ एक बार `FullseyeFallbackWarning` emit होती है**। क्या fallback हुआ और
  कितनी बार, यह `fullseye.fallbacks()` / `fullseye.fallback_counts()` से मिलता है।
  `on_error="raise"` (या environment variable `FULLSEYE_ON_ERROR=raise`) pass करने पर यह
  **fail-closed** हो जाता है: op का असली exception, dtype contract violations (integer/bool images), और
  GPU-kernel failures जैसे के तैसे propagate होते हैं। **Sort mismatches सिर्फ़ आंशिक रूप से जाँचे जाते हैं** (जैसे
  2-D op को RGB `(H,W,3)` pass करने पर उसे volume माना जाता है और `raise` में भी error नहीं आता —
  `docs/KNOWN_ISSUES.md` #32-4)। CI और validation के लिए `raise` सुझाया जाता है।
- **Multi-input ops** (`add_image` / `union2` आदि, `list_ops()` में `tier == "nary"`) अपने
  **inputs list के रूप में** लेते हैं: `fullseye.apply([img1, img2], "add_image")`।
- **Template matching** (`ncc_locate` / `shape_locate`) खोजी जाने वाली image
  `template=` से लेता है: `corr, row, col = fullseye.apply(img, "ncc_locate", template=patch)` (लौटाया गया
  row/col match का **center** है)। Template के बिना यह no-match `[0, 0, 0]` लौटाता है।

कौन-कौन से operators मौजूद हैं, यह आप ऐसे पता कर सकते हैं:

```python
fullseye.op_names()                 # all registry operator names (860, as of 2026-09-03)
fullseye.list_ops(search="edge")    # substring search over name / HALCON name / category
fullseye.list_ops(sort="region")    # filter by input sort
fullseye.categories()               # 47 categories
```

---

## 3. Pipeline बनाएँ (कई operators को जोड़ना)

किसी array को क्रम से कई operators से गुज़ारना एक "pipeline" है: यह array को
हर stage से गुज़ारकर अंतिम result लौटाती है।

```python
# same a, b across all stages (same shape as the CLI)
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# when you want different knobs per stage (specify as (name, a, b) tuples)
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

यह "smooth → edge magnitude → Otsu threshold" है, image को
binary edge map में बदलने का एक आम example। इसके साथ **20** तैयार combinations (recipes) आते हैं।

```python
import recipes
recipes.names()                                   # list of recipe names
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. इसे visually बनाएँ (Fullseye Studio)

Code लिखे बिना आप operators search करके उन्हें लगा सकते हैं, sliders से knobs घुमा सकते हैं,
उन्हें एक-एक stage करके चला सकते हैं, और intermediate results देखते हुए pipeline जोड़ सकते हैं।
GUI extras (`pip install -e ".[gui]"` = PySide6) ज़रूरी हैं।

```powershell
py -3.11 studio.py          # or, if installed: fullseye-studio
```

इसमें तीन panels हैं।

- **बायाँ (Operators)**: category / search से operators filter करें और **insert करने के लिए double-click करें**
  (Edit ▸ Focus operator search = **Ctrl+F** search box पर ले जाता है)। Sample pipelines भी
  यहीं से load होती हैं। **Insert (＋) HDevelop की operator window की तरह काम करता है**: pipeline में stage जोड़ने पर
  Program window में cursor की जगह पर एक `op (a, b)` line भी लिखी जाती है (values पूरी
  `repr` precision में; जब Program में बिना लागू किए हाथ के बदलाव हों, तो यह सिर्फ़ line insert करता है, जो
  Apply पर दिखती है)।
- **बीच (Pipeline)**: लगाए गए stages की list। Drag या Ctrl+↑/↓ से क्रम बदलें, और चुने गए stage के
  **knobs a / b** adjust करें। Knobs हमेशा 0..1 values होते हैं, लेकिन **जिन ops का
  display spec (`param_specs.py`) है, उन्हें उनकी असली units में चलाया जा सकता है** — `gaussian` के लिए px में σ
  (slider + unit spinbox); `median` के लिए 3/5/7/9 combo में kernel size; `reg_erode` के लिए
  integer spin में iteration count; `aug_barrel` के लिए b एक "pincushion" checkbox के रूप में। दाईं ओर का 0..1 spin
  हमेशा raw value होता है (सटीक input के लिए)। Specs ops.py के conversion formulas (`0.3 + 2.7·a` आदि)
  से हाथ से लिखे गए हैं और tests (`tests/test_studio_params.py`) से implementation के साथ
  cross-check किए जाते हैं। जिन ops का spec नहीं है, उनमें पहले की तरह दो 0..1 sliders रहते हैं।
  Stage list भी display units में लिखी जाती है (`gaussian (blur σ=1.08 px, b=–)`)। **Reset
  (Home) → Step (Ctrl+→) → Run all (Ctrl+Enter)** एक बार में एक stage या सब एक साथ चलाता है।
- **दायाँ (Image / Perception / Analysis)**: zoom/pan किया गया result image, histogram,
  Inspector (image / region / feature values जाँचें), और v14 perception panel (optical flow /
  stereo depth आदि)। Fit / 1:1 / Zoom / Save result / Save
  view as shown / Copy / Display mode / 3D surface (menu वाले ही actions) के लिए **image view पर right-click करें**। आप जो अतिरिक्त graphics
  windows खोलते हैं, उनमें भी Fit·1:1·±·Save की एक छोटी strip और वही right-click menu होता है, और
  3-D viewer (Ctrl+4) में right-click पर Reset view / first-person (perspective) toggle / Wireframe /
  Save screenshot होता है।

जोड़ी गई pipeline को आप `--ops` string या Python code के रूप में **Export (Ctrl+E)** कर सकते हैं, और **Save
pipeline (Ctrl+Shift+S)** से JSON के रूप में save कर सकते हैं। सारी सुविधाएँ और shortcuts
[STUDIO_GUIDE.md](STUDIO_GUIDE.md) में हैं; app के अंदर **F1** list दिखाता है।

---

## 5. Save की गई pipeline चलाएँ (CLI / code)

Studio में `Save pipeline` किया गया JSON (या एक `--ops` string) सीधे किसी file पर चलता है। यह
"जो design किया उसे दोबारा लिखे बिना चलाएँ" वाला HDevEngine-equivalent path है।

```powershell
# check the saved JSON's I/O and stages (structure check, no image)
py -3.11 imgevolve.py run edge.json --describe

# apply to an image and save the result
py -3.11 imgevolve.py run edge.json in.png --out result.png

# save the result of each stage (result_00.png, result_01.png, ...)
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# export the pipeline as a standalone Python function
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

Code से चलाने के लिए `FullseyeEngine` इस्तेमाल करें (विवरण [ENGINE.md](ENGINE.md) में)।

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # intermediate result of each stage (list)
```

---

## 6. CLI पर एक-एक करके लागू करें

जब आप किसी image file को सीधे process करना चाहते हैं, तो CLI सबसे तेज़ है (image I/O के लिए OpenCV या Pillow
ज़रूरी)।

```powershell
py -3.11 imgevolve.py ops --search edge                    # search operators
py -3.11 imgevolve.py has gauss_filter                     # is the HALCON name implemented + how to call it
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline` हर stage के लिए एक साझा `--a` / `--b` लेते हैं। जब आपको हर stage के लिए अलग knobs
चाहिए, तो ऊपर वाला `run_pipeline` (Python) या Studio इस्तेमाल करें।

---

## अगर आप अटक जाएँ

| लक्षण | क्या करें |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | `pip install -e .` चलाएँ, या repo root को `PYTHONPATH` में डालें |
| `fullseye` / `fullseye-studio` command नहीं है | console scripts `pip install -e .` से register होती हैं। Install नहीं किया है तो `py -3.11 imgevolve.py ...` / `py -3.11 studio.py` इस्तेमाल करें |
| Studio शुरू नहीं होता | GUI extras install नहीं हैं। `pip install -e ".[gui]"` (PySide6) |
| `apply` / `pipeline` में `cannot read ...` | image I/O के लिए OpenCV (`[opencv]`) या Pillow (`[pil]`) install करें |
| किसी extra backend का operator "unknown" है | वह backend install नहीं है। `.[skimage]` `.[wavelets]` `.[extra]` आदि जोड़ें |

ज़्यादा विस्तृत troubleshooting के लिए [INSTALL.md](INSTALL.md) देखें।

## आगे क्या पढ़ें

- **[INSTALL.md](INSTALL.md)** — पूरी setup गाइड (extras चुनना, Windows/Linux installers, minimal/embedded configs)
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — Fullseye Studio की पूरी गाइड
- **[ENGINE.md](ENGINE.md)** — FullseyeEngine (design → run) गाइड
- **[README.md](README.md)** — documentation index
