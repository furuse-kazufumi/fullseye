<!-- i18n-source-sha: bbeba242062b -->
# Fullseye Studio की पूरी गाइड

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · [简体中文](./STUDIO_GUIDE.zh.md) · [繁體中文](./STUDIO_GUIDE.tw.md) · [한국어](./STUDIO_GUIDE.ko.md) · [Deutsch](./STUDIO_GUIDE.de.md) · **हिन्दी**

**Fullseye Studio** एक HDevelop-style visual pipeline workbench है। आप operators search करके उन्हें
क्रम से लगाते हैं, sliders से दो knobs घुमाते हैं, zoom/pan के साथ intermediate results देखते हुए
एक-एक stage चलाते हैं, और जोड़ी गई pipeline को `--ops` string /
Python / JSON के रूप में export करते हैं। अंदर से यह `fullseye` API का एक पतला GUI front end है; pipeline logic
(`PipelineModel`), Inspector (`inspect_result`), और sample set (`recipes`) सभी
Qt से स्वतंत्र हैं और unit-tested हैं।

यह गाइड `studio.py` (`build_window`) को असली code से मिलाकर features की सूची देती है।
UX/design का इरादा [STUDIO_UX.md](STUDIO_UX.md) में है, और v14
perception panel की पृष्ठभूमि [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) में है।

---

## Launch कैसे करें

आपको GUI extras (PySide6) चाहिए (`pip install -e ".[gui]"`)।

```powershell
py -3.11 studio.py          # directly from the repository root
fullseye-studio             # if you have run pip install -e ., via the console script
```

Launch करने पर 1320×860 की main window खुलती है (title: Fullseye Studio)। अगर `assets/fullseye.ico`
मौजूद है, तो उसे window/taskbar icon के रूप में इस्तेमाल किया जाता है। शुरू में एक synthetic demo image load होती है
(`demo_image`, एक 256×256 image जिसमें edges, blobs और एक gradient हैं)।

---

## Screen layout (3 panels)

ऊपर एक **menu bar** (File / Edit / View / Run / Help) और एक **brand toolbar** है, और
नीचे एक **status bar** (hover पर coordinates + pixel value, और
`flash()` के अस्थायी messages)। बीच में बाएँ/दाएँ split में तीन panels हैं।

| Panel | Section (QGroupBox) | भूमिका |
|---|---|---|
| बायाँ | **SAMPLE PIPELINES** / **OPERATORS** | Samples load करना और operator browser |
| बीच | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | Pipeline बनाना, knobs adjust करना, export करना |
| दायाँ | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | Result display, colour map/perception, histogram/Inspector |

शुरुआती split widths 340 / 360 / 640 px हैं, और दायाँ panel फैलता है।

---

## बायाँ panel: Operators browser

### Sample pipelines (SAMPLE PIPELINES)
Dropdown से **20** तैयार recipes (`recipes.py`) में से एक चुनने पर
pipeline उस recipe से बदल जाती है। Examples: "Edge — Sobel + Otsu", "Denoise — bilateral + unsharp",
"Segment — blob / coin", "Count — blobs", "Texture — Gabor", आदि। पहले कुछ चलाकर फिर यह देखने के लिए
कि वह क्या करता है, यह एक अच्छा शुरुआती बिंदु है।

### Operator browser (OPERATORS)
- **Category filter**: "all categories" के साथ 31 categories (smoothing / edges / morphology /
  segmentation / features / texture / region / contour / color / frequency / restoration / 3d …)।
- **Search box**: operator names, HALCON aliases और categories को substring match से filter करता है (एक
  clear button के साथ)।
- **List**: हर row में `name [in_sort → out_sort]` दिखता है। **Insert करने के लिए double-click करें।** Hover पर एक
  tooltip "name / HALCON alias / category / sort conversion / knobs a,b का विवरण" दिखाता है।

Insert की जगह "चुने गए stage के ठीक बाद" है। अगर कोई stage चुना नहीं गया है, तो यह
अंत में जुड़ता है।

---

## बीच का panel: pipeline बनाना और step execution

### PIPELINE (stages की list)
हर row `N. op (a=…, b=…) -> result का summary` के रूप में होती है, और उस stage तक चलाने के result
की स्थिति (image/region/feature आदि) दाईं ओर दिखती है।

- **क्रम बदलना**: row को drag करके बदलें (InternalMove), या **↑ Up / ↓ Down** buttons /
  **Ctrl+↑ / Ctrl+↓** से।
- **Delete**: **Remove** button / **Del**।
- **तीन step-execution buttons**:
  - **⏮ Reset (Home)** — pipeline लागू होने से पहले की raw image दिखाएँ (step-through का
    शुरुआती बिंदु)।
  - **Step ▶ (Ctrl+→)** — एक stage आगे बढ़ें।
  - **Run all ▶▶ (Ctrl+Enter)** — सीधे अंतिम result पर जाएँ (मुख्य accent button)।

किसी stage को चुनने पर उस stage तक का intermediate result दाईं ओर के IMAGE panel में बनता है,
और नीचे का ANALYSIS (histogram / Inspector) भी sync होता है। यही "step-through
debugger" के बराबर है।

### SELECTED STAGE · KNOBS (knob adjustment)
चुने गए stage का विवरण दिखाता है (`op_detail`: name, `in → out` sort, category, HALCON
alias) और उसे **दो sliders a / b (0.00–1.00)** से adjust करता है। Value बदलते ही result
तुरंत फिर से compute होता है। जब कोई stage चुना नहीं होता, तो sliders disabled रहते हैं (ऐसा design जो किसी
बेमतलब knob को live state में नहीं छोड़ता)।

Knobs का मतलब हर operator में अलग है (radius / threshold / σ / direction आदि)। आप क्या
adjust कर रहे हैं, यह stage के detail label और tooltip में देखा जा सकता है।

### EXPORT & I/O
- **Export (ops string + Python)… (Ctrl+E)** — मौजूदा pipeline को एक dialog में (copy करने के लिए)
  `--ops "…"` string और standalone Python function, दोनों रूपों में निकालें।
- **Save pipeline… (Ctrl+Shift+S)** — pipeline को JSON के रूप में save करें
  (`{"fullseye_pipeline": 1, "stages": [...]}`)। यह JSON `FullseyeEngine.load` /
  `imgevolve.py run` का input है।
- **Open pipeline… (Ctrl+Shift+O)** — save किया गया JSON load करें।

---

## दायाँ panel: display, perception, analysis

### IMAGE (result view)
- **Load image… (Ctrl+O)** — किसी image file को reference frame के रूप में load करें (png/jpg/bmp/tif)।
- **Synthetic demo (Ctrl+D)** — synthetic demo image load करें।
- **Save result… (Ctrl+S)** — दिखाए गए result को PNG के रूप में save करें।
- **Zoom**: mouse wheel से cursor-position zoom, drag करके pan। **Zoom + (Ctrl+=) / Zoom −
  (Ctrl+-) / Fit (Ctrl+0) / 1:1 (Ctrl+1)**।
- Scalar feature result, contour result, या जब कोई image load न हो, तब view के बीच में एक message
  दिखता है (कभी खाली display नहीं)।
- Hover पर status bar `x, y, value` दिखाता है (colour के लिए RGB)।

### DISPLAY & PERCEPTION (v14)
- **Display (colour map)** — 2D result को display के लिए रंगें: `gray` / `shaded relief` / `height
  (color)` / हर colour map (jet, viridis, turbo, magma, plasma, inferno …)।
- **3D surface (Ctrl+3)** — मौजूदा result को घुमाए जा सकने वाले 3D surface के रूप में दिखाएँ (सिर्फ़ जब
  `QtDataVisualization` मौजूद हो / best-effort)। Height/depth map जाँचने के लिए।
- **Perception panel (2 frames)** — **Load frame B…** से दूसरा frame load करें, एक mode चुनें
  और **Run** दबाएँ:
  - `optical flow` — दोनों frames के बीच dense optical flow को hue के रूप में दिखाएँ।
  - `motion overlay` — चलते हुए regions को original image पर overlay करें।
  - `stereo depth` — stereo disparity से depth का अनुमान लगाकर उसे रंगें।
  - `stereo terrain` — stereo → point cloud → terrain height map, रंगीन।

  जब frame B न हो या size मेल न खाए, तो यह status bar में error दिखाता है और
  सुरक्षित रूप से रुक जाता है।

### ANALYSIS
- **Histogram** — मौजूदा 2D result का intensity histogram।
- **Inspector (variable / image / region)** — result को उसके sort के हिसाब से जाँचें।
  image/color के लिए: shape, min/max/mean, non-finite counts; region के लिए: connected components की संख्या,
  area, सबसे बड़ा region; feature के लिए: value; contour के लिए: contours की संख्या। Binary
  region के लिए यह हर region की feature table (`detect.feature_table`) भी दिखाता है।

---

## Command palette (Ctrl+P)

`Ctrl+P` एक fuzzy-search dialog खोलता है जिससे आप **किसी भी action या किसी भी operator को name से चला सकते हैं**। यह
prefix match > word-start match > substring match के क्रम में rank करता है (`palette_filter`,
Qt से स्वतंत्र रूप से unit-tested)। Actions (जैसे `▸ Open image`) पहले आते हैं, फिर सभी operators (जैसे
`op: gaussian`), और Enter उसे चलाता है। आप सिर्फ़ keyboard से operator insert करने तक
पूरा काम कर सकते हैं।

---

## Keyboard shortcuts

App के अंदर **Help ▸ Keyboard shortcuts (F1)** पूरी list एक table में दिखाता है
(self-documenting)। मुख्य shortcuts (`studio.py` की `act_*` definitions से):

| Action | Shortcut | Action | Shortcut |
|---|---|---|---|
| Open image | `Ctrl+O` | Remove stage | `Del` |
| Synthetic demo | `Ctrl+D` | Move stage up / down | `Ctrl+↑` / `Ctrl+↓` |
| Save result | `Ctrl+S` | Clear pipeline | `Ctrl+Shift+Backspace` |
| Open pipeline | `Ctrl+Shift+O` | Zoom in / out | `Ctrl+=` / `Ctrl+-` |
| Save pipeline | `Ctrl+Shift+S` | Fit / Actual size (1:1) | `Ctrl+0` / `Ctrl+1` |
| Export | `Ctrl+E` | 3D surface | `Ctrl+3` |
| Quit | `Ctrl+Q` | Reset to start | `Home` |
| Command palette | `Ctrl+P` | Step forward | `Ctrl+→` |
| Keyboard shortcuts | `F1` | Run all | `Ctrl+Enter` |
| Image Viewer | `Ctrl+Shift+I` | Run a ledger op | `Ctrl+Shift+L` |
| Pipeline as code → editor | `Ctrl+Shift+E` | | |

हर action एक ही handler से चलता है, चाहे menu से हो, toolbar से या button से (एक
action, कई entry points)।

---

## HDevelop `dev_*` display-control directives

HDevelop की तरह आप **program से display का व्यवहार control कर सकते हैं**। Program window की script में `dev_*` line
लिखने पर उसे image stage नहीं, बल्कि **display directive** माना जाता है,
जो Apply पर लागू होता है (सभी 43 `dev_*` की पूरी जानकारी `docs/HDEVELOP_DEV_OPS.md` में है)।

| Directive | असर | संबंधित UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | Graphics window का auto-update toggle करें | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | Variable window का auto-update toggle करें | वही, Variable window |
| `dev_update_pc ('off'|'on')` | Execution cursor का update toggle करें | वही, Program counter |
| `dev_update_time ('off'|'on')` | हर line के processing-time display को toggle करें | वही, Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | ऊपर के सभी को एक साथ off / on करें | toolbar का **Auto-update** toggle |
| `dev_set_part (Row1, Col1, Row2, Col2)` | Display range (zoom/pan) set करें; negative value = पूरा | mouse wheel / Fit के साथ इस्तेमाल करें |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | Colour map (LUT) बदलें | View ▸ Display mode |
| `dev_clear_window ()` | मौजूदा window साफ़ करें | — |
| `set_system ('thread_num', N)` | OpenCV worker threads की संख्या set करें (0 = default/सभी) | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | एक soft operator timeout (Run status में धीमे stage की चेतावनी देता है) | वही |
| `dev_set_draw ('fill'|'margin')` | Region overlay को fill और outline (margin) के बीच toggle करें | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | Region overlay का रंग | वही |
| `dev_set_line_width (N)` | Margin की outline width (px) | वही |
| `dev_disp_text ('label', Row, Col)` | Result के ऊपर text annotation (अगले draw / `dev_clear_window` पर साफ़ होता है) | — |
| `dev_open_window (Row, Col, W, H)` | Graphics window **खोलें, रखें और current बनाएँ** (फिर से Apply करने पर वही window फिर से रखी जाती है = बढ़ती नहीं) | Ctrl+G / Window ▸ Graphics |
| `dev_set_window (Handle)` | Handle से current window बदलें | window पर click करें |
| `dev_set_window_extents (Row, Col, W, H)` | Current window की position/size (-1 = जैसा है वैसा रखें) | window को drag करें |
| `dev_close_window ()` | Current window बंद करें (resident main window सुरक्षित है) | window का × |
| `set_system ('max_graphics_windows', N)` | Windows की संख्या की सीमा (default 256, हर path पर fail-closed) | Tools ▸ System settings ▸ Windows |

**इस्तेमाल**: सबसे ऊपर `dev_update_off ()` रखने से आप भारी processing या कई edits **बिना
drawing cost** के कर सकते हैं, फिर `dev_update_on ()` से display को एक साथ मौजूदा स्थिति पर ला सकते हैं
(HDevelop वाली ही performance technique)। जब updates off हों, तो status bar के दाईं ओर `updates off: …`
दिखता है, ताकि रुकी हुई स्थिति कभी "टूटी हुई न लगे"। Toolbar का **Auto-update**
toggle भी यही switch करता है।

**ध्यान दें** (ईमानदारी से): pipeline stage के उलट, `dev_*` `if`/`for` को नहीं मानता और
**बिना शर्त** लागू होता है (branch के अंदर रखने पर भी चलता है)। इन्हें top level पर लिखें।
Unsupported `dev_*` एक error है।

**आज़माकर देखें**: **File ▸ dev_* visualization demo** एक HDevelop program load करके लागू करता है जो
coins image पर ऊपर के `dev_*` असल में इस्तेमाल करता है (segment → regions को cyan outline
+ labels के साथ दिखाएँ)। काम करने वाली sample images **File ▸ Sample images** में हैं (8 images; provenance
`studio_assets/sample_images/manifest.json` में है। synthetic = अपना काम / `coins`, `camera` आदि =
skimage.data के BSD/public-domain। `tools/gen_sample_images.py` से फिर से बनाई जाती हैं)।

---

## कई भाषाओं का support (en / ja / zh, table-driven)

UI की भाषा **Tools ▸ Language / 言語 / 语言** पर बदली जाती है (यह याद रखी जाती है)।
Translations एक table हैं जो **`studio_assets/i18n.json` में केंद्रित** है, और इन्हें
code बदले बिना जोड़ा जा सकता है:

- `languages` — भाषाओं की list (एक जोड़ें तो वह अपने-आप menu में आ जाती है; English
  हमेशा base है)
- `tooltips` — tooltip translations (English original key है)
- `strings` — **menus, buttons और dialogs के label translations** (English original
  key है; 2026-08-30 को जोड़ा गया। 40+ Japanese items के साथ आता है; बिना अनुवाद वाली string English ही रहती है =
  graceful fallback)
- `guide` — quick guide text (Shift+F2)

अगर `op_help/<name>.<lang>.html` मौजूद है, तो op help हर भाषा में दिखती है। Honest disclosure: run के दौरान बदलने वाले status
शब्द (`running…` / `PASS` आदि) और op notes का body
अभी अनुवादित नहीं हैं (op notes को English में करना भविष्य का काम है, docstrings को
bilingual बनाने के साथ)।

## Python Editor और IDE features (2026-08-30)

Studio "आप सिर्फ़ pipeline से code call कर सकते हैं" वाले चरण से आगे जाता है और इसे
**Python development environment** के रूप में भी इस्तेमाल किया जा सकता है।

- **Python Editor** (File ▸ Python Editor… / gallery का "Open in editor"): syntax highlighting + line numbers + auto-indent वाला
  **multi-tab** editor (HDevelop की main + sub scripts की तरह,
  कई scripts एक साथ edit करना)। **F5 / Run** मौजूदा tab को subprocess में चलाता है (repo
  PYTHONPATH पर है, इसलिए `import fullseye` जैसा है वैसा काम करता है; unsaved buffer एक scratch copy से चलता है और
  Save के लिए मजबूर नहीं करता)। **Samples ▾** से आप हर worked example को नए tab में खोल सकते हैं (यह
  बिना path के खुलता है ताकि आप गलती से shipped sample overwrite न कर दें)। चलाने वाला interpreter
  System settings ▸ Editor में बदला जा सकता है।
- **MDI code windows** (gallery का "Open in window"): sample code को स्वतंत्र windows के रूप में लगाएँ,
  **जितनी चाहें उतनी**, और चुना गया हिस्सा copy करें (Window ▸ Tile/Cascade भी काम करते हैं)।
- **Execution control**: breakpoint (= pause) के लिए gutter पर click करें, **Continue** button
  चल रही line से अगले breakpoint / अंत तक फिर से शुरू करता है, और stage के right-click का **Run
  from here** किसी भी line से फिर से शुरू करता है (**Run to here** के साथ जोड़ी में)।
- **Variable watch**: Variables window में कोई भी expression register करें (`v.mean()` /
  `np.percentile(v, 99)` / `(v > 0.5).sum()` आदि; `v` = चुना गया variable, `np` = numpy, `img`
  = input), और यह हर selection change / pipeline change पर **अपने-आप फिर से evaluate होता है**।
  Fail होने वाला expression अपनी row पर ⚠ दिखाता है (panel crash नहीं होता)। Variable का **right-click ▸
  Inspect in popup…** तुरंत type के हिसाब से inspection + percentile + value preview दिखाता है। ज्ञात
  सीमा (ईमानदारी से): watch expression GUI thread पर synchronously evaluate होता है, इसलिए **बहुत
  भारी expression** (किसी बड़े array का पूरा sweep आदि) उसके दौरान UI को रुकवा देता है। Expression को
  हल्का करें, या भारी aggregation Python Editor में चलाएँ।
- **System settings** (Tools ▸ System settings… / Ctrl+,): category tree + paged layout। Execution
  (threads / timeout), Windows (window cap), Display (default LUT / region drawing), Editor (font
  size / चलाने वाला interpreter)।

## Drag and drop से क्या खोला जा सकता है (2026-10-03)

**Main window पर files या folders drop करें** और हर एक उसके लायक window में खुलता है (एक साथ कई files
कई windows खोलती हैं)। पूरी list **Help ▸ Files you can open (drag & drop)…** में है; वह table
Studio के असल में इस्तेमाल होने वाले extension constants से बनती है, इसलिए वह इस section से नई हो सकती है।

| आप क्या drop करते हैं | कहाँ खुलता है | Notes |
|---|---|---|
| Images (png / jpg / tif / webp / pgm / pfm / jp2 …), folders | Image viewer | List, zoom, pixel values, histogram, "Use as pipeline input"। Folder अपने अंदर की images सीधे खोलता है |
| `.py` | Python editor (हर file का एक tab) | |
| `.json` | Pipeline | |
| Point clouds और meshes (PLY / STL / PCD / OBJ / OFF / XYZ) | 3-D viewer | **ASCII और binary दोनों** (PLY little- और big-endian में, PCD binary_compressed भी) |
| 3DGS (`.ply` / `.splat`) | 3-D viewer | SH DC term से रंग; opacity < 0.05 वाले splats छिपे रहते हैं |
| Medical volumes (NIfTI / NRRD / MHA / DICOM) | 3-D viewer | SimpleITK या उसके जैसा चाहिए |
| glTF (`.glb` / `.gltf`), LiDAR (`.las` / `.laz`) | 3-D viewer | pygltflib / laspy चाहिए |
| Robots (MJCF / URDF) | 3-D viewer | `.xml` सिर्फ़ तब जब उसका root `<mujoco>` या `<robot>` हो। mujoco चाहिए |
| Motion capture (`.bvh`), neuron morphology (`.swc`) | 3-D viewer | BVH joint paths समय के हिसाब से रंगे जाते हैं |
| Videos, animated GIF, HDF5 | Video cube | |
| Event-camera (x, y, t, p) (txt / csv / npy / npz) | Video cube | Content से पहचाना जाता है, polarity frames में बदला जाता है |
| `.npy` | Shape के हिसाब से | 2-D → input image, (N, 3 / 6) → point cloud, 3-D → volume |
| Markdown, SVG | Document viewer | |
| Audio (wav / mp3 / flac / ogg …) | Audio window | Waveform, spectrogram, playback। Non-WAV के लिए soundfile चाहिए |
| Robot model + qpos `.npy` (T, nq) साथ में | Robot player | Slider और play button |

## कोई भी ledger op आज़माएँ (Tools ▸ Run a ledger op…, Ctrl+Shift+L) (2026-10-03)

एक window जो typed-ledger ops (PIV, math, driving, 3-D … लगभग 1,700) को **हर argument के type से मेल खाते
input fields** के साथ चलाती है। बाईं ओर के search box में name या शब्द लिखें, एक op चुनें, और उसका argument form
दाईं ओर दिखता है।

- **Data inputs** "sample (synthetic)", "current image" या "last result" से आते हैं। Sample उस op के लिए बनाया गया
  known truth वाला synthetic input है; "last result" **इस window में आखिरी बार चलाए गए op का result** है, इसलिए
  दूसरा op चुनने पर वह आगे pass हो जाता है (जैसे `ode_vector_field_grid` से flow field बनाएँ, फिर arrow plot के लिए `piv_quiver` का input
  "last result" पर set करें)। गलत type का input (flow2d slot में current image) चलाने के बजाय
  कारण बताकर मना कर दिया जाता है।
- **Arguments**: integer box, real-number box, check box, जहाँ op में choices हों वहाँ choice list, बाकी जगह
  text line। खाली का मतलब default, `None` का मतलब None, lists `1, 2, 3` के रूप में। Matrix या dict samples
  `<sample>` token के रूप में रखे जाते हैं। जो value पढ़ी न जा सके, उसे **कभी चुपचाप default से नहीं बदला जाता** — window बताती है
  कि कौन-सा argument और क्यों।
- **Run** result को picture के रूप में और उसके contents (shape, range, fields) के रूप में दिखाता है, साथ में **वही काम करने वाली
  Python की एक line** ("Copy code" उसे script में paste करता है; यह MATLAB command history है)।
- "**Re-run when a value changes**" on होने पर हर बदलाव op को फिर से चलाता है (controls से खोजबीन)।
- **एक click में editor में**: "Insert into editor" window का code (एक **script जो जैसी है वैसी चलती है**, sample भी
  फिर से बनाती है) Python Editor के cursor पर डालता है (ज़रूरत हो तो उसे खोलता है; document में जो imports नहीं हैं, सिर्फ़ वे ऊपर जोड़े जाते हैं)।
  "Session as script" इस window के हर सफल run को क्रम से इकट्ठा करता है ("last result" से जुड़े steps
  `result = …` lines का क्रम बन जाते हैं)।
- **Editor से भी**: Python Editor में `fs.ledger.` या `fs.` के बाद लिखने पर names सुझाए जाते हैं (कभी भी Ctrl+Space)।
  कोई ledger op चुनने पर **उसके data और ज़रूरी arguments के साथ call** insert होता है — जैसे `dem_slope(dem, cell_size=)` —
  और cursor पहली खाली जगह पर होता है। उस op की window खोलने के लिए op name पर right-click करें, या उस पर Ctrl+Shift+L दबाएँ।
- **Command palette (Ctrl+P)**: `ledger: name` किसी भी ledger op की window तीन keystrokes में खोलता है (Ctrl+P → name → Enter)।
- **जो result आप देख रहे हैं उससे**: main image पर right-click करें → "Pipeline as code → editor" (Ctrl+Shift+E; एक script जो खुली image पढ़कर चलती है) / "Send this result to a ledger op…" (window दिखाए गए result को image input के रूप में पहले से चुनकर खुलती है)।

कुछ ops अपने sample पर नहीं चलते (हर op का sample कैसे बनाया गया है, उसकी सीमा: 2026-10-03 को sample वाले 60 ops में से 27
जैसे के तैसे चले)। Window अपनी ओर से कोई failure नहीं जोड़ती, यह एक gate से जाँचा जाता है: इसका result sample को
सीधे op में pass करने से मेल खाना चाहिए।

### Result view चीज़ों को कैसे दिखाता है

जो results pixels नहीं हैं, वे अपने shape के हिसाब से बनाए जाते हैं (दायाँ panel और ऊपर वाली window यह साझा करते हैं)।

| Result | ऐसे दिखता है |
|---|---|
| `flow2d` `(2, h, w)` | colour wheel के ऊपर arrows (सबसे लंबा = 0.9 × spacing), जहाँ hue = direction, brightness = speed |
| 1-D numbers | एक line (MATLAB `plot(y)`) |
| table (dict) | बराबर लंबाई के उसके numeric columns lines के रूप में; x axis एक `t` / `x` / `freq` … column है, अगर हो |
| `(h, w, 4)` / `(h, w, 1)` / complex | सफ़ेद के ऊपर RGB / grey / magnitude \|z\| |
| खाली arrays, 4-D और उससे ज़्यादा | shape और range text के रूप में (पहली value को "scalar" के रूप में नहीं दिखाया जाता) |

## Export और Save/Open का संबंध

Studio में बनी pipeline को तीन रूपों में निकाला जा सकता है।

| रूप | कैसे बनाएँ | कहाँ इस्तेमाल करें |
|---|---|---|
| `--ops` string | Export (Ctrl+E) | CLI के `imgevolve.py pipeline --ops "…"` / `run "…"` में paste करें |
| Python function | Export (Ctrl+E) | अपने code में `fullseye.run_pipeline(...)` के रूप में embed करें |
| JSON | Save pipeline (Ctrl+Shift+S) | `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json` से चलाएँ |

**Studio में design, code/CLI में execute** वाला HDevelop→HDevEngine-equivalent flow
JSON के ज़रिए होता है। JSON लेकर execute करने वाले पक्ष के लिए [ENGINE.md](ENGINE.md) देखें।

---

## संबंधित documents

- [STUDIO_UX.md](STUDIO_UX.md) — design system और UX सुधारों का इरादा और पृष्ठभूमि (design view)
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — perception panel के अंदर क्या है (flow / stereo / terrain)
- [ENGINE.md](ENGINE.md) — export की गई pipeline execute करें
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5 मिनट में शुरू करें
