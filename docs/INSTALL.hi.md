<!-- i18n-source-sha: b5eeee92dc95 -->
# Installation / Environment Setup — पूरी गाइड

[日本語](./INSTALL.md) · [English](./INSTALL.en.md) · [简体中文](./INSTALL.zh.md) · [繁體中文](./INSTALL.tw.md) · [한국어](./INSTALL.ko.md) · [Deutsch](./INSTALL.de.md) · **हिन्दी**

यह गाइड Fullseye (working name imgevolve) को किसी भी उद्देश्य के लिए setup करने के बारे में है, development
machine से लेकर embedded Linux तक। अगर आप बस इसे पाँच मिनट में चलाना चाहते हैं, तो
[GETTING_STARTED.md](GETTING_STARTED.hi.md) shortcut है।

Fullseye का design principle है **"ऐसा core जो सिर्फ़ numpy + scipy पर चलता है" + "हर भारी
dependency optional है।"** किसी extra backend के बिना सिर्फ़ उसी backend वाले खास operators बंद
होते हैं; core हमेशा चलता है (graceful degradation)।

---

## (a) Prerequisites

| Item | ज़रूरत |
|---|---|
| Python | **3.11** (`pyproject.toml` में `requires-python = ">=3.10"` set है; development और testing 3.11 पर होती है) |
| चलाने का command | Windows: `py -3.11` / Linux: `python3.11` |
| Core dependencies | `numpy>=1.23`, `scipy>=1.9` (`pip install -e .` से अपने-आप install होती हैं) |
| OS | Windows 10/11, Linux (embedded सहित)। जहाँ Python चलता है, वहाँ macOS पर भी काम करता है |

---

## (b) pip install (extras का मतलब और कब इस्तेमाल करें)

Repository root से editable install करें।

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # core only (numpy + scipy; every op is listed, and an op that needs an optional backend names the missing extra when called)
```

अतिरिक्त backends **extras** के ज़रिए चुने जाते हैं (`pyproject.toml` के
`[project.optional-dependencies]` में defined)।

| extras | जुड़ने वाली dependencies | क्या चालू होता है |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | image file I/O (`apply`/`pipeline` CLI के लिए ज़रूरी), `cv_*` operators |
| `skimage` | `scikit-image>=0.20` | `sk_*` / `xsk_*` families (कई auto-generated operators का आधार) |
| `pil` | `Pillow>=9` | image I/O fallback, `xpil_*` family (emboss/posterize/solarize आदि) |
| `wavelets` | `PyWavelets>=1.4` | wavelet family (VisuShrink / subbands / packets आदि) |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | GPU batch backend (`accel.py`/`bench.py`), `xkor_*` (kornia) family |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*` (curvature flow आदि), mahotas से बने (Zernike / pftas आदि) |
| `gui` | `PySide6>=6.5` | **Fullseye Studio** (`studio.py` / `fullseye-studio`) |
| `all` | GUI को छोड़कर ऊपर का सब कुछ (opencv, skimage, pil, wavelets, gpu, extra) | सभी operators और backends |

मोटे तौर पर नियम:

```powershell
# the common minimum for real work + image I/O (no GUI, code/CLI-centric)
py -3.11 -m pip install -e ".[opencv]"

# also use the GUI (Studio)
py -3.11 -m pip install -e ".[opencv,gui]"

# fully loaded (GUI included; since `all` does not include GUI, add `gui`)
py -3.11 -m pip install -e ".[all,gui]"

# also try the GPU batch path (needs a CUDA-capable torch)
py -3.11 -m pip install -e ".[gpu]"
```

> `all` में `gui` शामिल **नहीं** है (GUI को अलग रखा गया है क्योंकि उसका उद्देश्य अलग है)।
> अगर आप Studio इस्तेमाल करते हैं, तो `gui` हमेशा अलग से जोड़ें।

Install सफल होने पर आपको ये **दो console scripts** मिलती हैं (`[project.scripts]`)।

| Command | पीछे का entry point | बराबर का direct invocation |
|---|---|---|
| `fullseye` | `imgevolve:main` (CLI) | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main` (GUI) | `py -3.11 studio.py` |

Install किए बिना आज़माने के लिए repository root को `PYTHONPATH` में डालें, तो `import fullseye` काम करता है
(console scripts उपलब्ध नहीं होंगी)।

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

---

## (c) Windows installer

`install\install.ps1` चलाने से environment setup और desktop integration एक ही बार में हो जाते हैं
(PowerShell)।

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

यह installer मोटे तौर पर ये काम करता है।

- जाँचता है कि Python 3.11 मौजूद है
- `pip install -e .` से Fullseye install करता है (ज़रूरी extras के साथ)
- **Fullseye Studio का shortcut (`Fullseye Studio.lnk`) बनाता है** — `pyw.exe` के ज़रिए register होता है ताकि यह
  console window के बिना launch हो, और इस पर `assets\fullseye.ico` icon लगा होता है

इसके बाद आप Start menu / desktop shortcut से Studio launch कर सकते हैं।

> अगर execution policy इसे रोकती है, तो `-ExecutionPolicy Bypass` जोड़ें (ऊपर के command में पहले से
> शामिल है)।

---

## (d) Linux installer + `.desktop` launcher

`install/install.sh` चलाने से Linux पर बराबर का setup हो जाता है।

```bash
cd /path/to/imgevolve
bash install/install.sh
```

यह script मोटे तौर पर ये काम करती है।

- जाँचती है कि `python3.11` मौजूद है
- `pip install -e .` (ज़रूरी extras के साथ)
- **`.desktop` launcher बनाती है** — `assets/fullseye.ico` icon वाली एक desktop entry
  register होती है ताकि आप application menu से Fullseye Studio launch कर सकें

इसके बाद आप अपने desktop environment की app list से Studio launch कर सकते हैं।

---

## (e) Minimal setup / embedded (embedded Linux)

Fullseye का core **सिर्फ़ numpy + scipy** पर चलने के लिए बनाया गया है। जिन embedded कामों में GUI,
GPU या भारी backends की ज़रूरत नहीं, उनके लिए सिर्फ़ core install करना काफ़ी है।

```bash
python3.11 -m pip install -e .        # numpy + scipy only. No GUI/torch/opencv needed
```

Embedded इस्तेमाल के मुख्य बिंदु:

- **Input और output पूरी तरह numpy arrays के रूप में होते हैं।** Sensor/camera से मिले numpy frames
  आप किसी file I/O के बिना सीधे pass कर सकते हैं।

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # your own float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # no disk write needed
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **जब file I/O की ज़रूरत हो** (`fullseye.load` / `fullseye.save`, `imgevolve.py run`, examples), तो यह
  **OpenCV या Pillow में से किसी एक** के होने पर चलता है (`imgio` अपने-आप fallback करता है)। अगर आप
  embedded footprint छोटा रखना चाहते हैं, तो दोनों में Pillow (`[pil]`) हल्का है।
- आप काम को **dev machine पर design, embedded machine पर execution** में बाँट सकते हैं। Dev machine पर
  Studio में pipeline बनाकर JSON export करें; embedded machine पर बस
  `FullseyeEngine.load("pipeline.json").run(frame)` चलाएँ (GUI नहीं)। विवरण के लिए [ENGINE.md](ENGINE.md) देखें।
- **Perception stack** (stereo / terrain / flow / detect / registration / pose) भी
  numpy + scipy पर चलता है (`fullseye.disparity_map` आदि)। यह extra dependencies के बिना
  robotics/vision के लिए इस्तेमाल हो सकता है।

> GPU (`torch`) path सिर्फ़ **batch speedup के लिए opt-in** है। Embedded devices पर
> single-image processing के लिए इसकी ज़रूरत नहीं; इसके बिना भी हर operator CPU पर चलता है।

---

## (f) आम समस्याएँ

| लक्षण | कारण | समाधान |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | install नहीं हुआ / path set नहीं | `pip install -e .`, या repository root को `PYTHONPATH` में जोड़ें |
| `fullseye` / `fullseye-studio` command नहीं मिलता | console scripts register नहीं हुईं | `pip install -e .` चलाएँ। Install नहीं किया है तो `py -3.11 imgevolve.py` / `py -3.11 studio.py` इस्तेमाल करें |
| Studio launch करते समय PySide6 ImportError | GUI extras install नहीं | `pip install -e ".[gui]"` |
| `apply` / `pipeline` पर `cannot read <path>` | कोई image I/O backend नहीं | `pip install -e ".[opencv]"` (या `[pil]`) |
| `read_image` / `write_image` (API) से cv2 ImportError | ये **सिर्फ़ OpenCV** वाले हैं | `pip install -e ".[opencv]"`। अगर Pillow से काम चलाना है, तो `fullseye.load` / `fullseye.save` इस्तेमाल करें |
| अपेक्षित operator `list_ops` में नहीं है / `has` unknown लौटाता है | संबंधित backend install नहीं | मेल खाते extras जोड़ें (`skimage`/`wavelets`/`extra` आदि) |
| GPU batch (`accel`/`bench`) CPU पर धीमा है | `torch` CPU build है | GPU पर `--device cuda` इस्तेमाल करें। CPU पर साधारण pointwise काम conversion cost से हार जाता है (by design) |
| Studio का 3D surface नहीं खुलता | `QtDataVisualization` मौजूद नहीं | best-effort feature है। यह PySide6 के version/build पर निर्भर है और न होने पर चुपचाप skip हो जाता है |

### Image I/O dependencies (ज़रूरी)

Files पढ़ने और लिखने के लिए ज़रूरी backend path के हिसाब से अलग है।

| Path | ज़रूरी backend |
|---|---|
| `fullseye.load` / `fullseye.save` (= `imgio`), `imgevolve.py run`, examples | **OpenCV या Pillow** (कोई भी एक चलेगा / automatic fallback) |
| `imgevolve.py apply` / `pipeline` | **OpenCV ज़रूरी** |
| `fullseye.read_image` / `fullseye.write_image` (API) | **OpenCV ज़रूरी** |

`apply` / `run_pipeline` / `FullseyeEngine.run`, जो सीधे numpy array लेते हैं, उन्हें **किसी भी image
I/O backend की ज़रूरत नहीं** (ये सिर्फ़ core numpy + scipy पर चलते हैं)।

---

## Sanity check

```powershell
py -3.11 imgevolve.py coverage        # honest coverage count (979/2313 HALCON ops genuinely implemented)
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()` `0.1.0` लौटाता है, और `op_names()` 860 registry operators लौटाता है
(2026-09-03 तक)।
