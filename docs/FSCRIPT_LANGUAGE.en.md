<!-- i18n-source-sha: d3311f3c10f1 -->
# Fullseye Script — Language / Runtime / Watch IDE Design Specification (North Star)

[日本語](./FSCRIPT_LANGUAGE.md) · **English**

> Goal = evolve Fullseye Studio's Program from "a linear (op,a,b) pipeline wearing a scripting skin"
> into a **real programming environment on par with HALCON HDevelop**. User-decided direction (2026-08-15 dialogue):
> 1. A **dedicated language** (HDevEngine syntax is the first choice, C/C++ style is also acceptable), with named variables + real if/for/while (**branching on measured values**) + per-object iteration + I/O.
> 2. **Fullseye = image-processing library**, the language is the layer that **calls it** (do not build the logic into the language).
> 3. **A compiler approach is preferred** (over an interpreter).
> 4. **Rigorous watches**: in addition to variable watches, **image watches / Region watches / watches on a specific image domain (ROI)**.
> 5. Ultimately, **turning Fullseye into a DLL** is the most natural end state.
> 6. It should be possible to write robot-control programs (perception → decision → action loops).

External AI (Codex read-only) design consultation done (20 items, reflected in this document). **Discipline = no blind acceptance, back it up with code.**

---

## 0. Honest reality and the phased strategy

- **imgevolve is currently pure Python + numpy/scipy** (CLAUDE.md: core=numpy+scipy). **DLL-ization = rewriting the vision core into native (C/C++/Rust) + exposing a C ABI**, which is major construction work.
- However, imgevolve holds the seed of **S2 codegen (IR→Python+**C**)** (the champion is already codegen'd to C). → The path **DSL→C→native** is not fantasy but an extension of existing assets.
- imgevolve's differentiation is the **evolution engine + honest holdout gate + op registry** (mostly Python). **Not breaking these is the top priority** (Codex #17).
- **De-risk policy**: do not write a DLL right away. **First verify the hardest designs (language semantics, watch model, library API) rigorously in a Python bytecode VM**, solidify correctness and the debugging experience, then drop the hot paths into C codegen / native DLL.
  - Reason: fixing language/watch design mistakes in native code is costly. A VM iterates fast, and step/watch/exception/source mapping come naturally. Heavy pixel processing already runs on the numpy/C side, so the Python overhead of the control VM is usually small (needs benchmarking, Codex #10).

**Conclusion (Codex #1)**: **make the language primary**, and keep the linear pipeline as a "branch-free, side-effect-free serial subset (LinearSubset)" for reuse in evolution, acceleration, and the old UI.

### ★Cross-platform (Linux) and the phases of the "custom foundation" (user note 2026-08-15)
User insight = "if we're going to use it on Linux too, isn't it a form of putting the language on top of a fairly custom foundation?" → **Correct, but the foundation changes by phase**:
- **Now (foundation = Python + numpy/scipy)**: already cross-platform. **The language VM + L1 (fslib) runs everywhere Python runs = Linux support is free.** A custom native foundation is **not needed**. → A working cross-platform real-language IDE can be verified **right now**.
- **Later (foundation = native core, for DLL/speed/embedded)**: only here do we first need a portable "custom foundation". **Rust recommended** (single codebase cross-compiling to Win `.dll` / Linux `.so` / embedded, memory safety, Python interop via PyO3, C ABI exposure). **Add op by op in a performance/distribution optional layer**, and **keep the L1 API contract fixed so L2 language stays unchanged during the swap**.
- **Honest scale**: a full HALCON-class stack (native cross-platform core + language + IDE + tools) is a **platform-scale undertaking**. ∴ **Python-first to de-risk, and stage native-foundation investment when needed** is the only realistic route.

### ★★A central requirements fork: Path A (Python-native IDE) vs Path B (custom language) (user note 2026-08-15)
User insight = "**A form where a Python development platform has convenient watch features for image processing is completely viable too.**" This is **actually the wiser first goal.** Next session's requirements definition should decide this A/B first.
- **Path A (practical, recommended) = Python-native IDE**: the user calls the Fullseye library (the existing package) from **plain Python.** The differentiation the platform provides = **image-processing-aware watch/debug** (live-monitor §4's image/region/domain=ROI/XLD/objectset/handle during execution, an iconic-variable pane, step/breakpoint, ROI probe). Implementation = `sys.settrace` or a controlled exec + variable capture + per-type renderers of §4.
  - Advantages: the user requirements (Tuple/mixed types → Python, STL containers → list/dict/set/collections, type/string conversion → built-ins, a solid language → Python, speed → numpy/C + optional native) are **all satisfied by Python.** Cross-platform / major construction avoided. **Most of the value at low cost.** No design/maintenance debt of a custom language.
  - Limits: full HDevelop fidelity (4-quadrant syntax, handle semantics, a distribution engine) is not obtained. The iconic domain and such are expressed with the Fullseye library's own types (an FImage class).
- **Path B (ambitious) = a custom HALCON-class language** (the VM+compile+DLL of §1–8 of this document). Maximum fidelity, distribution, evolution integration. Platform-scale.
- **★The watch model (§4) is the reusable core common to both Paths** (A = the Python live namespace, B = observing the VM environment). ∴ **whichever way it goes, §4 and the L1 library (FImage+domain / measurement / ObjectSet) are never wasted** = they should be solidified first.
- **Recommended scenario**: incrementally, **do Path A first** (Python IDE + image watches) to produce real value, and bolt on Path B (sharing L1) if HDevelop fidelity/distribution becomes required. Finalize A/B requirements with external AI next session.

### ★Resolving interpreter vs compiler (user notes: watches are structurally hard / PyBind11 / DLL feasibility)
- **Rich live watches (image / Region / domain / object / variable) require a "live variable environment"** → **a VM / interpreter provides that naturally.** **Native-compiled code scatters variables across registers/stack, needing DWARF + a debugger (gdb-type) = structurally hard** (as the user noted). → **The watch requirement effectively makes a VM mandatory.**
- ∴ **the same two-mode operation as HALCON is the right answer**:
  - **IDE = VM execution** (interpretation): watch/step/breakpoint on the live environment at each statement boundary. ← this is the main battlefield of this design.
  - **Distribution / speed = compile**: DSL→C→native DLL (existing C codegen assets). Optimized execution without debug info.
  - This is exactly **HDevelop (interactive = interpretation) + HDevEngine (distribution = engine).**
- **PyBind11 / calling convention**: if the IDE is **unified in all-Python (VM + L1 library), PyBind11 is unnecessary.** PyBind11 / CPython embedding is needed only in the mixed case where "**a native-compiled program calls the Python-side Fullseye**" → avoid it by **turning L1 into a DLL at distribution time** (native language runtime → native Fullseye DLL direct call). **Avoiding the mix (native language + Python library)** is the crux of the trick.
- **DLL-ization difficulty (honest)**: "turning Python as-is into a clean DLL" is impossible (Cython/Nuitka are a "Python in a box" bundling CPython+numpy, not a clean C ABI). **A real DLL = re-implementing ops natively + a C ABI = major construction.** However, **pure-algorithm ops can be C→DLL-ized with the existing C codegen** (cv2/skimage/scipy-wrapping ops are out of scope). → **Natively port only hot ops, incrementally.** **A DLL is not needed to verify the design of the language / watches / library API,** so solidify that first in Python (de-risk). Fix the L1 API contract now → later swap L1 for a DLL without changing L2.

---

## 1. The 3-layer architecture

```
┌─────────────────────────────────────────────────────────────┐
│ L3  Studio IDE  … editor / run (debug|run|profile) /          │
│                   ★watch panel (§4) / breakpoints /            │
│                   execution cursor / Variable & Object panes   │
├─────────────────────────────────────────────────────────────┤
│ L2  Fullseye Script language … lexer→parser→typed AST→        │
│     bytecode compiler→VM (= the compiler). Source position     │
│     first-class. Control flow, variable env, per-object        │
│     iteration, exceptions, cancellation.                       │
│     ★Holds no logic. Only calls L1 (LanguageOperatorSpec).     │
├─────────────────────────────────────────────────────────────┤
│ L1  Fullseye library … vision/measurement/geometry/device      │
│     functions with real parameters (read_image/gauss/threshold/│
│     connection/area_center/…/comm/device/acquire). numpy/scipy │
│     implementation.                                            │
│     ★Future: hot paths to C codegen → native DLL (C ABI).      │
│     Contract kept separate from the evolution engine's          │
│     normalized-knob registry (§3).                             │
└─────────────────────────────────────────────────────────────┘
```

- **L1 = the "Fullseye library"** (user policy 2). For now the Python module `fslib.py` (+ re-exported from the `fullseye` package). **Future DLL**: expose the same function set with a C ABI (`fullseye_threshold(img, lo, hi, out)` etc.), and bind thinly on the Python side with cffi/PyO3. **Fix the API contract (types, units, outputs) now with DLL-ization in mind** (so the swap can happen without changing the L2 language).
- **L2 = the language (compiler).** Per Codex #5, a **bytecode VM** (`LOAD_VAR/CALL_OP/STORE_VAR/JUMP_IF_FALSE/ITER_OBJECTS/CALL_DEVICE`). Direct AST evaluation is a stepping stone for increment 1 (semantics verification), migrated to bytecode early.
- **L3 = the IDE.** At each statement boundary the VM fires `ExecutionEvent(span, changed_vars, removed_vars, pc, state)` → the watch/variable panes update incrementally (Codex #12).

---

## 2. Language specification (HDevEngine style, Codex #2–4)

- **Calls**: the HALCON 4-quadrant `operator (InIconic : OutIconic : InControl : OutControl)`. Quadrants may be omitted but the colon positions are kept.
  ```
  read_image (: Image : 'samples://images/parts_01.png' :)
  threshold (Image : Region : 0.42, 1.0 :)
  connection (Region : Objects : :)
  area_center (Object : : : Area, Row, Column)
  ```
  ★For compatibility, increment 1 also allows the **assignment form `Out := op(In, ctrl…)`** (C/C++ style, universal), and the 4-quadrant form is introduced gradually as op signatures mature.
- **Types** (Codex #3): **iconic** = `Image/Region/XLD` + **ObjectSet** (an iterable iconic collection) / **control** = number/string/bool/tuple/handle. Implicit iconic↔control confusion is forbidden (assignments record the sort). Do not treat numpy arrays as tuples.
- **★Image = pixels + domain (HALCON-faithful, user note 2026-08-15)**: in HALCON an **Image object embeds a domain (a Region denoting the region to process, default = the whole image).** Fullseye L1 too makes **`Image = FImage(matrix, domain: Region)`.**
  - ops **process only within the domain** (pixels outside the domain are unchanged/undefined). `reduce_domain(Image, Region : ImageReduced : :)` restricts the domain, `full_domain(Image)` makes it whole, `get_domain(Image : Region : :)` extracts the domain as a Region.
  - The output Region of `threshold`/`connection` etc. intersects the input Image's domain. This makes "inspection limited to an ROI" a first-class expression, and §4's **domain watch** (looking at an image's domain) holds natively.
  - Implementation (incremental): the default is a lightweight wrapper with domain=whole (the matrix itself + `domain=None`=full). A Region is held only on `reduce_domain`. On DLL-ization it is represented by `FImage`'s C ABI (pixels ptr + domain run-length).
- **Expressions**: `:=` (assignment) / `=` (comparison) / `# != <= >= < >` / `and or not` / `+ - * / mod` / tuple `[..]` · `t[i]` · `|t|` · concatenation / parentheses. **Unimplemented syntax is not silently interpreted — it is a syntax error.**
- **★control = the HALCON tuple model (user note 2026-08-15)**: in HALCON **every control variable is a Tuple** (a scalar = a length-1 tuple), and **integers/reals/strings can be mixed within a single tuple** (e.g. `['part', 5, 3.14, 'ok']`). → Fullseye too models control values as a **heterogeneous mixed Tuple** (elements = int / real / string, bool being int).
  - `Tuple` is an immutable value. Element types are preserved (integer 5 and real 5.0 are distinguished). `t[i]` (0-based) · `|t|` (length) · `[t1, t2]` (concatenation; `+` is elementwise addition, §2b) · `subset/remove/insert/tuple_gen_const`. Arithmetic/comparison **broadcast elementwise** (HALCON-conformant, length 1↔N · N↔N).
  - The operator `+` follows the HALCON ambiguity rule of **numeric tuples = elementwise sum, contains a string = concatenation** (stated explicitly in the spec; whether to make `.` a string-concatenation-only operator is to be decided). The empty tuple `[]` and the type-promotion rule for mixes (int→real) are defined.
  - iconic (Image/Region/XLD/ObjectSet) is a separate class, not a Tuple (§3, no mixing).
  - ★Implementation note: the current PoC (`fscript.py`) handles control as raw float/int/str/list. **The type system of increment 1 must be replaced with the HALCON Tuple** (a `Tuple` class + element-type preservation + broadcast operations).
- **★The Vector type (HDevelop 13+, user note 2026-08-15)**: HALCON has, separate from Tuple, a **Vector** (a **typed, multi-dimensional container** that stores tuples or iconics). `vector(dim)`, `Vec.at(i)`, `|Vec|`, assignment `Vec[i] := ...`, iteration with `for`. Provide Tuple (flat, mixed scalars) and Vector (nested, can also store objects) as **separate types.**
  - Use: arrays of objects/tuples (e.g. a Vector of contours per blob, a Vector of Tuple of per-row measurements). ObjectSet (§3) is a specialization of "a 1-D collection of iconics", while Vector is more general (multi-dimensional, also stores control).
  - Implementation (phased): approximated with a Python list in increment 1, tightened to **`FVector` (preserving element type + dimensions)** from increment 2 on. Watches support Vector (expanding elements for display) via §4's per-type renderers.
- **★A standard container library (C++ STL style, user note 2026-08-15)**: in addition to HALCON's Tuple/Vector, we want to provide, as a standard library, **general-purpose containers heavily used in design patterns.**
  - Candidates: `list` (variable length) · `map`/`dict` (associative) · `set` · `stack` · `queue`/`deque` · `pair`. Iterator/for-each, and STL-equivalent methods like `push/pop/insert/erase/find/size/empty`.
  - Positioning: these are **composite types of the control domain** (iconics, even if stored, are held by handle/reference). Explicitly a Fullseye extension not present in stock HALCON (labeled honestly in the spec as a "Fullseye extension", not "HALCON-compatible").
  - Implementation: an `FContainer` family on the L1/language-runtime side (internally a thin, typed wrapper over Python dict/list/set etc.). On DLL-ization, handled with the C++ STL / an equivalent C ABI. Watches use per-type renderers (map = a key/value table, set/stack/queue = an element sequence).
  - Example uses: a `map` of blob → classification label, a `queue` of ROIs awaiting processing, a state-machine `stack` (a robot-control sequence), a `set` of unique features. A foundation on which design patterns (State/Strategy/Observer etc.) can be written straightforwardly.
- **★Standard library: type conversion / string conversion (user note 2026-08-15 "we need a fairly solid language design + speed")**:
  - **Type conversion**: `int(x)`/`real(x)`/`number(x)`/`is_number/is_int/is_string`, tuple-element type detection `type_of(t[i])`, the int↔real promotion rule. Both HALCON's implicit promotion and explicit conversion.
  - **Strings**: `string(x, fmt)` (number → formatted string, HALCON `'$.3f'` style) / `str_to_number` / `split` / `join` / `regexp_match/replace` / `length` / substring / `str_upper/lower` / concatenation. Essential for robot-control I/O (command assembly/parsing) and result output.
  - **These are necessary conditions of a "solid language"**: rigorously design the type system (§2's Tuple/Vector/container + iconic/handle) + conversions + an error type + scope + procedures (spec'd from increment 2 on). **Speed is solved by §0's two modes (IDE=VM / distribution=compile→C→DLL),** natively porting only the hot path. To avoid a "language in appearance only", unimplemented features are honestly rejected with syntax/type errors.
- **Control flow**: `if/elseif/else/endif` · `for V := a to b [by s]/endfor` · `for Obj in Objects/endfor` · `while (c)/endwhile` · `repeat/until (c)` · `break/continue`.
  - ★**Factual correction (2026-08-15 verification)**: **`for Obj in Objects` is unimplemented** (`_KEYWORDS` has no `in`, and the parser accepts only `for V := a to b`).
    The current per-object iteration is written with `for I := 0 to N-1` + `select_obj(Objects, I)`. `for ... in` is an added item for increment 1.
    That unimplemented syntax becomes a syntax error is itself correct behavior (locked by `tests/test_fscript.py`). Termination: the VM has an **instruction budget + wall-clock deadline + a cancel flag**, and `while/repeat` periodically pumps the UI.
- **Measurement multi-output** (Codex #8): formally support multiple control outputs of `area_center(Region : : : Area, Row, Column)` (the current `api.apply` floats only the first element = information loss). Empty region/NaN/length mismatch is a defined exception or an empty tuple; do not implicitly coerce to truth in conditions.

### 2b. The finalized behavior of the increment-1 implementation (`fscript.py`) —— making spec and implementation agree (finalized in the 2026-09-03 audit)

§2 above is the North Star (design). **How the current implementation actually behaves** is authoritatively the following table, which `tests/test_fscript.py` /
`tests/test_fsruntime.py` lock one item at a time. Under the discipline of "never silently return a wrong answer", every ambiguous input is a `FScriptError` (with a line number).

| Item | Finalized behavior |
|---|---|
| **Gray-value units** | The language's gray value is a **fraction of the image's declared range** (0 = range bottom, 1 = top). `threshold(Image, lo, hi)` and `mean_gray/min_gray/max_gray` use the **same units.** Pixel 128 of an 8-bit image reads as `0.502`. ∴ `threshold(Image, mean_gray(Image), max_gray(Image))` means the same for 8-bit and float alike (previously only statistics used raw pixel values, and on 8-bit it silently returned area 0). |
| **Tuple arithmetic** | `+ - * / %` and unary `-` are **all elementwise** (length 1↔N broadcast; N↔N requires equal length, else an error). `[1,2] * 2 = [2,4]` (not Python's repetition `[1,2,1,2]`). Concatenation is `[t1, t2]`. |
| **String arithmetic** | `string + string` = concatenation only. `'ab' * 3` and `'a' + 1` are errors (Python's repetition / type mixing are not language features). |
| **Scalar = a length-1 tuple** | `[1] = 1` is true, `if ([0])` is false, `not [0]` is true. **A tuple of length ≠ 1 cannot be placed in a condition** (an error). In comparisons `< > <= >=`, mixing a tuple and a scalar is an error; `=`/`#` are whole-tuple equality. |
| **Indexing** | The `i` of `t[i]` / `s[i]` is a **non-negative integer** (an integer-valued real like `2.0` is allowed; `1.9`, negatives, and strings are errors). Out of range is an error (`index 3 out of range (length 3)`). There is no negative index. |
| **Index assignment** | `Name[i] := expr` is implemented (`expr` is a scalar; a tuple is flat so nesting is impossible). **Tuples are values**: `B := A` is a copy, and `B[0] := 9` does not reach `A`. A Python list passed via `images=` is also duplicated, and the script does not rewrite the caller's list. |
| **Numeric literals** | ASCII digits only: `12` / `1.5` / `1.` / `.5` / `1e-3` / `2.5E+4`. `1.2.3` / `2e` / `1e5e3` / `３` (full-width) / `²` are syntax errors. A literal that falls to infinity like `1e400` is also an error. |
| **String literals** | `'...'` **fits on one line** (crossing a line is `unterminated string`). The only escapes are **`\'` and `\\`.** Any other backslash is **that literal character** (`'<a local working path>\images\a.png'` reads as-is; `'<a local working path>\dir\'` has `\'` become an escape → an unterminated error, so write `'<a local working path>\dir\\'`). |
| **`break` / `continue`** | Outside a loop, a **syntax error** (`'break' outside loop`). |
| **Chained comparison** | `0 <= X <= 10` is forbidden (an error). **A parenthesized comparison is an explicit operand,** so `(X > 3) = true` / `(1 < 2) = (2 < 3)` are allowed. |
| **Condition header** | The condition of `if/elseif/while/until` runs to end of line. `if (X = 1) or (Y = 1)` is one condition. A header starting with `(...)` can only continue with `and`/`or`, so `if (X = 1) -1` or `for I := 0 to 2 X := I` (a statement on the header line) is `unexpected ... after statement`. |
| **`for` bounds** | start/stop/step are numeric (a string or a tuple of length ≠ 1 is an error). step 0 is an error. |
| **The radius of `dilation` / `erosion` / `mean_image`** | A **non-negative integer** (pixels). `0` is the identity (returns the region unchanged); negative or fractional (`0.4`) is an error (previously `max(1, int(r))` turned everything into 1). |
| **op arguments** | Passing a string or a tuple (length ≠ 1) to a numeric argument raises `... must be a number, got string 'x'` as a `FScriptError` (no bare `ValueError` surfaces). An error always carries the calling line. |
| **The path of `read_image`** | If `base_dir` exists it **confines to that subtree** (a relative path is base_dir-relative; `..` is judged after resolution; an absolute path is allowed only within the subtree). Otherwise `path ... is outside the script's base directory`. Only without `base_dir` (the caller explicitly omitting it) is it opened as-is. **The industrial-profile Runtime rejects loading a recipe containing `read_image`** (no file access within a cycle = FSCRIPT_DECISION.md §3.1 R4; frames are passed via `images=`). |
| **Nesting limit** | The nesting of parentheses/unary/blocks and the expression depth at evaluation time go up to **200** (`nesting too deep (limit 200)`). An expression chaining 200+ `1+1+…+1` terms hits the same error. Python's `RecursionError` never escapes. `check()` never throws and returns a string. |
| **The golden digest** (`fsruntime`) | The manifest digest is not `repr()` but a canonical byte sequence (type tag + length + `float.hex()` / `dtype.str + shape + tobytes()`). It does not depend on `np.printoptions`, and detects a single-element difference even in an array of over 1000 elements. The types that can be placed on `GoldenVector.expect` are only bool/int/float/str / their list · tuple / numpy arrays (others are a construction-time `TypeError`). **There is no compatibility with the old digest** (re-sign a signed recipe with `sign`). |

---

## 3. The L1 library = the language operator specification (Codex #6–9)

- **Do not expose 526 ops directly via `RT[name](v,a,b)`.** Put `LanguageOperatorSpec(name, in_iconic, out_iconic, in_control=[Param(name,type)], out_control, invoke)` in a separate layer.
- **Separate the normalized knobs (a/b∈[0,1], evolution-only) from the language's real arguments (sigma=1.5 etc.)** (Codex #7). For ops whose inverse mapping is inaccurate, provide a native implementation. Put `normalized_knobs` and `semantic_parameters` in separate contracts.
- **ObjectSet** (Codex #9): the current region is a binary mask with no individual identity. `ObjectSet` = a **label image + an object-ID sequence + a lazy view** (the mask is not copied but materialized when needed, copy-on-write). `connection` generates it; `select_obj/concat_obj/count_obj/for Obj in Objects`.
- **Unpolished ops** are quarantined with a warning into `legacy_apply(Image : Result : A, B :)` (not called HDevelop-compatible en masse).
- **The minimal L1 vocabulary for increment 1**: read_image/to_gray/gauss/mean_smooth/invert/threshold/binary_threshold/dilation/erosion/connection/count_obj/select_obj/area_center/area/select_shape/union_object/mean_gray/max_gray/min_gray/region_to_image.
  - ★**Factual correction (2026-08-15 verification)**: this document originally wrote this as "an implemented seed = `fslib.py`", but **`fslib.py` does not exist.**
    The above vocabulary is implemented as the `_b_*` functions + the `BUILTINS` dictionary inside `fscript.py`, and **L1 and L2 are not separated.**
    "Separate L1 into `fslib.py`" is not completed work but an **untouched task of increment 1.**

---

## 4. ★The watch model (user's top priority, rigorous design)

User requirement = not just variable watches but **image watches / Region watches / watches on a specific image domain (ROI).** The core of the debugger.

- **The observed target (Watch) is a typed expression**: `Watch(expr, kind, options)`. **Watches are a per-type extensible renderer-registration system** (a `WatchRenderer` registry) = add a new iconic/handle type and register one renderer and the IDE supports it. Responds to the user's note "HALCON has objects other than Region, and those must all be watchable too."
  - `kind=control` … the value of a number/string/tuple (a history ring + a change graph).
  - `kind=image` … an image (+ domain). Display = a thumbnail + pixel statistics (min/max/mean/hist) + a **zoomable view** + a **domain-boundary overlay.** Options: colormap, value range.
  - `kind=region` … a Region (mask). Display = a colored overlay on the original image (margin/fill) + area/centroid/bbox.
  - `kind=xld` … an **XLD (subpixel contour / polygon).** Display = a contour-polyline overlay on the original image + control-point count / length / curvature. Equivalent to HALCON's XLD_cont/XLD_poly (imgevolve already has a contour(XLD) sort).
  - `kind=domain(ROI)` … **watch a specific domain of an image**: `Watch(Image, domain=Rect(r1,c1,r2,c2))` or `Watch(Image, domain=Region)`. Display = a crop **limited** to that ROI + statistics (in-ROI mean/hist/defect rate). Non-destructive observation of **the very domain embedded in HALCON's Image (§3).**
  - `kind=objectset` … an ObjectSet (**a collection of any iconic type,** not just Region). Display = the object count + a thumbnail of each object via its per-type renderer + a feature table.
  - `kind=handle` … an **opaque handle (matching model / measure / classifier / calibration / OCR etc.).** Display = the handle's type name + main parameters + provenance (internal raw data is not shown). Corresponds to HALCON's handle family.
  - **Extensibility**: add a new type with `register_watch_renderer(type, renderer)` (imgevolve-specific iconics such as volume/point-cloud/mesh become watchable through the same mechanism).
- **Evaluation timing**: at each statement boundary of the VM, **re-evaluate the live watch expressions in the variable environment at that moment** (during a step, the environment at the current pc). Inside a loop, attach the iteration index + call depth (to distinguish the same line, Codex #13).
- **Performance/memory**: instead of copying huge arrays through the signal, pass a **value ID + generation**, and a thumbnail worker renders asynchronously after confirming the generation. History defaults to "the most recent N generations + a thumbnail", with full-value pinning only for explicit watches (Codex #12/#13). An ROI watch materializes only the crop.
- **In-language representation of watch expressions**: manage `watch Image`, `watch Region as overlay`, `watch Image[Rect(10,10,50,50)]`, `watch |Objects|` in the Studio UI (right-click → Watch / add an expression to the Watch panel). Expressions are limited to a subset of L2 (no side effects).
- **Step-linked**: moving the execution cursor → all watches + the Variable/Object panes update incrementally to the current live-variable state (Codex #12). Unreached variables are "undefined", and an ObjectSet is lazy.

---

## 5. Coexistence with the evolution North Star (Codex #16, #17)

- **The round-trip is one-directional**: `stage list → script` is always possible. `script → stage list` is only for a **LinearSubset** (single iconic in/out · serial · constant control · no branches/loops/I-O/multiple outputs). The non-convertible is presented with line numbers; do not flatten/pick a branch on its own.
- **Evolution generates only an `EvolvableBlock`** (keeping the fixed length of 6 slots × (op,a,b)). The outer language does acquisition/branching/measurement/action; only inside the block are the existing genome + train selection + holdout/locked-holdout.
  ```
  evolve_block Denoiser (Input : Output)
    gauss_filter (Input : T1 : 0.63 :)
    threshold (T1 : Output : 0.47, 1.0 :)
  endblock
  ```

## 6. Robot control (Codex #20)

- Not arbitrary Python exposure but **capability-restricted built-ins**: register `open_camera/grab_image/close_camera` (acquire.py), Modbus `read/write` (comm.py), DigitalIO `set/get/pulse/wait_input` (device.py) as LanguageOperatorSpec.
- Opaque handles + automatic close on `on_error/finally`, a monotonic-clock deadline, `wait_input(...,timeout)`, a cancelable `delay`, a simulation backend, an allowlist of motion range / speed / output pins, and a first-time arm confirmation in Studio. The image worker and the device-I/O worker are separated, the VM keeps sequential semantics and awaits future completion. → Safely writing an "acquire → measure → conditional branch → act → sensor check → timeout" loop.

---

## 7. Sample layout (Codex #14–15)

```
samples/
  scripts/     01_threshold_and_measure.fsh …            # sample code (dedicated folder)
  images/      parts_01.png defects_scratches.png …       # synthetic images (procedurally generated)
  generators/  make_inspection_samples.py                 # generators (seed/conditions)
  manifests/   samples.json                               # generation conditions / expected results / license
```
- **Image-generating AI cannot be called from this environment** (no text-to-image tool). For machine vision, **procedural synthesis is optimal** (deterministic, license-clean, ground-truth labeling = directly tied to holdout). Useful: parts with a lighting gradient / blobs differing in area / touching-overlapping parts / chips-scratches / low-contrast foreign objects / a calibration grid with known coordinates.
- `read_image` resolution rule (deterministic, safe): `samples://images/x.png` = the installed sample root, relative = the calling script's parent, absolute = within an allowed workspace. No cwd dependence, path-traversal check, extension restriction (Codex #15).

---

## 8. The phased roadmap (Codex #18 adjusted to imgevolve reality)

- **Increment 1 (language PoC, in implementation)**: the AST interpreter `fscript.py` (semantics verification) + L1 `fslib.py` (an implemented seed) + real if/elseif/else · numeric for · object for · assignment · expressions · per-object iteration. **Prove by tests that the real algorithm "blob detection → per-object area → threshold exclusion → centroid" runs.** A samples generator + 2 scripts.
- **Increment 2 (compilation + watches)**: turn into a bytecode VM, source spans first-class, ExecutionEvent, add to Studio a **watch panel (§4: image/region/domain/objectset)** + breakpoints + step-in/over/out + an execution cursor. `while/repeat`, diagnostics.
- **Increment 3 (library expansion + reconciliation)**: legacy-op adapters via LanguageOperatorSpec, measurement multi-output, ObjectSet (label sharing), LinearSubset extraction → bidirectional stage list, EvolvableBlock.
- **Increment 4 (device/robot)**: capability-restricted built-ins for acquire/comm/device, a safety policy, simulation.
- **Increment 5 (native-ization)**: hot paths to **C codegen (existing asset) → a native Fullseye DLL (C ABI)**, cffi/PyO3 binding. Applied selectively after benchmarking validates it. **Swap L1 for a DLL without changing the L2 language.**

At each stage, regress on parser golden tests / type errors / empty objects / cancellation / same-seed images / old-pipeline parity.

---

## 9. The current prototype (measured and verified 2026-08-15)

- `fscript.py` (increment 1, AST interpreter): lexer/parser/AST/evaluator + a variable environment + real if/for/while/repeat + exceptions + a step budget.
  The L1 built-ins (`_b_*` / `BUILTINS`) are also **in the same file**, so **L1/L2 are not separated.**
- `tests/test_fscript.py` (**new this session**): 22 passed / 5 xfail. Before that, **not a single fscript test existed**
  (the "smoke-test proof" was an ad-hoc run, not a committed regression test — an honest correction).
- **The measurement record = `docs/FSCRIPT_MEASUREMENTS.md`** (cycle time / jitter / cold start / distribution size / 5 defects).

### ★What the measurements changed about the design priority

The conclusions of `docs/FSCRIPT_MEASUREMENTS.md`:

1. **The language's execution method (AST interpreter) has essentially no effect on cycle time** (+0.4–4.7%).
   → The motive for a bytecode VM is **not speed but the debugging experience** (step/breakpoint/span/watch). Distinguish this honestly.
2. **The object model matters 5.8×**, and **the pixel-kernel implementation 23×.** 134× in total.
   → The priority order is **types·semantics → ObjectSet → native kernel contract → VM-ization.**
3. **5 defects that silently return wrong values** (misreading `*` as a comment = fixed, content-dependent normalization of the value range, Tuple `+`, implicit truth-coercion of iconics, `.any()` collapse in comparisons). All are semantic problems that **remain even if the implementation language changes.**
   → **"Type system first, then the VM."** Native-ization comes after.
