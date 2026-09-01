# Carrying ~1,000 Explainable Classical Vision Algorithms as "Skills" — Building Fullseye, a Self-Made Vision Workshop for Physical AI

> Japanese original: [fullseye_overview_qiita_ja.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/fullseye_overview_qiita_ja.md)

![Fullseye — a 12-tile banner of real processing results (defect inspection, sub-pixel metrology, watershed, a dinosaur X-ray, a nebula, LiDAR and more — all real outputs that appear in this article)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fullseye_banner.png)

![A real point cloud of asteroid Itokawa, spun on a turntable by a custom renderer (all hand-written in numpy)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/showcase_turntable_itokawa.gif)

This is a real point cloud of asteroid **25143 Itokawa** — the Gaskell shape model built from Hayabusa spacecraft observations, published in the JAXA DARTS archive — spinning inside the custom 3D renderer of this article's protagonist, **Fullseye**. Loading the point cloud, rendering it, the rock material, the shadows — **all of it is hand-written numpy**. This is the story of how I've been building that "eye."

## TL;DR

- **Fullseye** (a pun on "Bullseye" — the dead center of a target) is a self-built library of classical image-processing and geometric-vision algorithms: **roughly 1,000 operators, implemented from scratch in numpy, sitting behind one typed interface**. The goal is to make "explainable vision" — vision whose internals you can actually account for — something you can carry around as the eyes of **Physical AI** (AI that acts in the physical world with a body, i.e. robots).
- I use **HALCON**, the industrial machine-vision standard, as a "map of coverage." As measured, Fullseye has a self-built counterpart for **982 of 2,313 HALCON operators (42.5%)** — not a number from memory, but a mechanical tally against the operator list from the official reference.
- On top of the library sit an **evolutionary mode that "designs" algorithms through evolutionary computation**, a **Physical AI perception stack** that chains stereo → depth → point cloud → 6-DoF pose, and an **HDevelop-style IDE, Fullseye Studio**.
- **The single most recommended way to use it is as an AI's RAG knowledge base.** Feed it to Claude Code or similar, and a plain conversational request like "detect X in this image" gets you a **pipeline assembled from ~1,000 ops, executed, with the results appearing on Studio's screen** — that's the foundation this is designed to be.
- The undercurrent of this article is **making "honest disclosure" a mechanism** — never showing only the good numbers, never erasing failures, always stating the limitations. I include cases where the quality gates actually caught bugs, **including six I fixed just now**, exactly as they happened.
- Tests currently number **6,238**. Every deep dependency (OpenCV, torch, etc.) is optional — **the core runs on nothing but numpy + scipy**.

> This article isn't a victory lap over something finished. It's a record of **why I shaped it this way and where it's still weak**, at a granularity you could reproduce yourself. Every number is measured; no limitation is hidden.

First, one image. This is output from Fullseye's 3D renderer (hand-written numpy, of course) — an SDF-built shape baked with ambient occlusion, soft shadows, and ACES tone mapping:

<!-- Post-publication check: the raw URL must return HTTP 200. Images are lightweight thumbnails that click through to full size (to keep the article's memory footprint down) -->
[![Output from Fullseye's custom renderer (SDF smooth union + AO + soft shadows + ACES) — click for full size](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/render_beauty_hero_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/render_beauty_hero.png)

---

## What This Article Is (in Three Lines)

- This is an overview of my personal image-processing library **Fullseye** — a compilation covering everything **from the design philosophy to how the internals are built**.
- It's aimed at anyone working in **machine vision, robot perception, or image processing**, or anyone curious about **how to design a library so it stays maintainable for the long haul**.
- Individual techniques (3D Gaussian splatting, evolutionary computation, musculoskeletal control, etc.) are covered in depth in separate articles. This one is the **map**.

Expect roughly 20 minutes of reading. It's long, so feel free to jump from the table of contents to whichever layer interests you.

### Sorting the Claims by Maturity, Up Front

This is a long article, so let me sort **which claims sit at which stage** before we start. The same Status labels appear at the top of the relevant chapters.

| Tier | Status label | What it covers in this article |
|---|---|---|
| **Implemented & reproducible** | `Production-ready / Verified` | The 731 2-D + 265 3-D ops, type contracts and the unified interface, Studio, the PyPI release, 6,238 tests, the machine-tallied 982/2,313 HALCON mapping, and the real outputs behind every exhibit and demo |
| **Under validation** | `PoC / Research prototype` | Evolutionary pipeline design (hold-out evaluated, bounded settings), natural-language-to-pipeline via RAG, and the Physical AI perception stack (validated in simulation; real hardware and sim-to-real are untouched) |
| **Future vision** | `Roadmap / Design proposal` | A comprehensive op foundation for robots, an AI autonomously selecting and running the ~1,000 ops, and a shared perception base for industrial inspection and Physical AI |

Every number is a real measurement. This sorting is itself one of the mechanisms for not overselling.

---

## Getting Started (Installation, Up Front)

For anyone who wants to try things hands-on while reading, installation first. It's available from the public GitHub repository and from PyPI. Since **the core runs on nothing but numpy + scipy**, I'd recommend installing it bare first and adding extras (the optional dependencies) only when you need them.

```bash
# ① Get it running (core needs only numpy + scipy)
pip install fullseye

# ② Add extras if you want the Studio (IDE) or the heavier ops
pip install "fullseye[gui]"        # PySide6-based IDE only
pip install "fullseye[all]"        # OpenCV / torch / GUI / video, everything

# ③ Launch Studio
fullseye-studio
```

Let me be a bit more concrete about what command ① actually does. `pip install fullseye` pulls in **only numpy and scipy** as dependencies (no OpenCV, no torch, no PySide6). Even in this state, `import fullseye` works and **more than 500 ops are immediately usable**. As the chapters "An Honest Word on Performance (GPU)" and "The Night Before Release" will describe, this claim — "the bare install runs a working minimum" — is itself something **CI executes and verifies on every run**; it isn't a verbal promise. The extras in ② are positioned as an **add-on choice** you reach for when you need them.

And **the single most recommended way to use it is as a RAG (retrieval-augmented generation) knowledge base for an AI coding assistant such as Claude Code**. A bundled setup script installs the skill in one command:

```bash
fullseye-rag              # register the op catalog as a Claude Code skill
fullseye-rag --uninstall  # remove it cleanly
```

With that in place, you can just say "detect the scratches in this image" to the AI, and it will assemble and run an appropriate pipeline out of ~1,000 ops (more on what it can and can't do in the RAG section below). If you haven't tried Claude Code yet, starting from [this referral link](https://claude.ai/referral/0sqPw8E_lw) helps fund the author's development budget (i.e. wallet) a little.

If you'd rather install from source (for anyone who wants the full corpus of ~1,000 op docs for RAG):

```bash
git clone https://github.com/furuse-kazufumi/fullseye && cd fullseye
pip install -e ".[all]"
py -3.11 tools/update_fullseye.py --check   # use the safe updater for subsequent updates
```

The updater is built on a **never-trash-your-environment** policy (it refuses to run if there are uncommitted changes, only ever does `--ff-only`, backs up the RAG skill before updating, and never touches your Studio settings). Full usage details live in the repo's `README.md`, `docs/AI_RAG_GUIDE.md` (RAG setup), and `docs/STUDIO_GUIDE.md` (IDE guide).

The four constraints just listed (refusing uncommitted changes, fast-forward only, back up before updating, hands off Studio settings) are each unglamorous tricks on their own. I still spelled them out side by side because of one self-awareness: **an update script whose job is to grow an AI's foundation can itself become the offender that destroys a human's work.** If the RAG setup script or the Studio setup — tools that are supposed to help development — carelessly wiped unsaved changes or overwrote hand-tuned settings, the whole point would be defeated. The fail-closed designs introduced later in this article are, at bottom, the same idea repeated over and over.

**A quick link set for anyone who wants the big picture first** (all readable directly on GitHub):

| What you want | Link |
|---|---|
| The full **help index** for ~1,000 ops (2D / 3D) | [docs/ops/INDEX.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/ops/INDEX.md) |
| A **one-page catalog** of every op, with type contracts | [docs/OP_CATALOG.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/OP_CATALOG.md) |
| A **results gallery** (full-size versions of this article's figures, with commentary) | [docs/GALLERY.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/GALLERY.md) |
| A **catalog of where to get sample data** (real download URLs and licenses) | [docs/ops/SAMPLES.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/ops/SAMPLES.md) |

---

## Four Words First (A Minimal Glossary)

Just the four most frequent terms up front. **Every other term gets broken down inline the first time it appears**, so there's nothing else to memorize.

| Term | In short |
|---|---|
| **Fullseye** | The star of this article. A self-built operator library for image processing and geometric vision. The name is **a pun on Bullseye — the dead center of a target in darts or archery** (details in "The Name," below). The development repo is called `imgevolve`. |
| **Operator (op)** | "One image-processing function." Examples: Gaussian blur, Otsu thresholding, Sobel edges. Fullseye has roughly 1,000 of them. |
| **HALCON** | The industrial machine-vision standard from Germany's MVTec. A giant with **2,313 operators**. Fullseye uses it as the **yardstick** for measuring "how much of this ground have I covered with my own implementations?" |
| **Studio (Fullseye Studio)** | The IDE (integrated development environment) for **looking at, trying out, and doing real work with** Fullseye. The equivalent of HDevelop in industrial vision. |

---

## The Name — Fullseye = Bullseye + Eye

The name's origin, first. **Fullseye** is a pun on **Bullseye** — the dead center of a target in archery or darts, and by extension "spot on, a direct hit." The pronunciation leans into that too: "full's eye."

There's a triple meaning packed in:

- **Full (everything) + eye**: "**an eye that can see everything**." The goal itself — holding every kind of image processing and geometric vision as a "skill," all of it.
- **The precision of hitting Bullseye's dead center**. The implication that this should be an eye that's **explainable and doesn't miss** — the standard demanded by industrial inspection and robot perception.
- And the echo of my own surname, **Furuse**, joined to **eye** — "Furuse's eye." As a solo project, I've woven myself into the name.

From a name that described the *means* — "designing by evolution" (`imgevolve`) — to a name that describes the *goal* — "an eye that hits its target" (Fullseye). The change in name itself mirrors the project's change in direction.

Keeping the development repo named `imgevolve` is, in fact, deliberate. Changing the name doesn't mean I want to erase the accumulation that led here — the assets and lessons from the era when evolutionary computation searched over ops. The public product name switches to Fullseye, while the internal name keeps a trace of the original idea — I think of this, too, as a kind of provenance record.

---

## Why I Built This — From "Designing by Evolution" to "An Explainable Eye"

Fullseye has a predecessor. It started life as **`imgevolve`** — an experiment in **automatically designing image-processing pipelines with evolutionary computation**. The idea: let a genetic algorithm search for "the processing sequence that maximizes this metric on this data."

The turning point was when I **redefined the direction**. To "search" via evolution, you first need the search's building blocks — the ops — to be **abundant, consistently typed, and honestly evaluated**. As I kept assembling those building blocks, I realized: **the component library itself was the real star.**

Then, in August 2026, I redefined Fullseye's mission as follows:

> **Hold every kind of image-processing and vision algorithm as a "skill," ready to use, in one comprehensive library. Build an explainable, robot-purposed "private HALCON."**

That redefinition was a big call for me. I'd been stacking up general-purpose algorithms (sorting, compression, and the like), and I cut that — "that's the wrong lane" — and decided to **concentrate entirely on image and geometric vision**. Deciding **what not to build** turned out to be the single most effective decision.

Behind this is **evis**, the musculoskeletal humanoid (a 700-muscle model, among others) I've been building in a separate series of articles — Fullseye's **customer number one**. Getting a robot to pick up a bean with chopsticks, or to walk, requires **an eye that sees the world correctly**.

![A procedurally generated hand skeleton (8 carpal bones, 5 metacarpals, 14 phalanges, capsule SDFs) rendered by Fullseye's custom renderer](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/examples_3d/_gallery/hand_hero.png)

*↑ That "hand," seen from Fullseye's side. A procedurally generated hand skeleton (8 carpal bones, 5 metacarpals, 14 phalanges), rendered — again — with the custom renderer.*

Deep-learning vision is powerful, but when it **can't explain why it decided on a given pose**, it's hard to trust it with decisions that affect a body's safety. That's why I want **explainable classical vision, held entirely in hand as a set of skills** — that's the core of Fullseye.

To break it down a bit further, the reasoning goes in this order. Whether a robot is picking up a bean with chopsticks or walking on two legs, nothing starts until it knows "what is in front of me right now, and where." **Seeing (perception) has to come before moving (control)** — obvious as that sounds, there were many moments across the evis experiments where this hit home hard. However clever the motion planner, if the input point cloud is warped or the pose estimate is flipped, everything stacked on top loses its meaning. That's exactly why I decided to build the perception foundation **first, not later, and as an independent library**. A customer named evis raises the requirements, and a supplier named Fullseye answers them — with the same one person wearing both hats. That's the most accurate description of how this actually runs.

Here is that "pick up a bean with chopsticks" experiment, seen through Fullseye's eye (click to play the video):

[![evis's chopstick-tip camera footage with Fullseye's segment_objects → draw_objects applied every frame to track the bean (click to play mp4)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_bean_track_fullseye_thumb.jpg?v=2)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/evis_bean_track_fullseye.mp4)

*↑ ▶ Chopstick-tip camera footage from the ChopMimic experiment (experimental material from the evis_chopstick project), with Fullseye's `segment_objects → draw_objects` applied every frame to track the bean. Left = third-person view (context, unprocessed); right = the bean bbox Fullseye detected. Detected in all 163 frames where the bean is visible (100% visible-frame detection rate; centroid error vs. ground truth: median 0.10px, max 14.5px on partially occluded frames). No detections in the 78 frames where it's genuinely occluded by chopsticks or plate — nothing is fabricated.*

---

## The Big Picture — Fullseye Has Three Layers

```mermaid
flowchart TB
    subgraph L0["Foundation: ~1,000 typed ops"]
        OPS["The typed operator library<br/>731 2D ops + 265 3D ops<br/>hand-written numpy / wired together by type (sort)"]
    end
    subgraph L1["Two ways to use it"]
        APPLY["① Apply a known op<br/>fullseye.apply / run_pipeline"]
        EVO["② Design a pipeline by evolution<br/>evolve / robust (evaluated honestly on held-out data)"]
    end
    subgraph L2["Application: robot eyes"]
        PERC["Physical AI perception stack<br/>stereo → depth → point cloud →<br/>6-DoF pose → muscle actuation (evis)"]
    end
    STUDIO["Fullseye Studio (HDevelop-style IDE)<br/>look, try, and work"]

    OPS --> APPLY --> PERC
    OPS --> EVO --> PERC
    OPS -.display & test.-> STUDIO
    PERC -.visualize.-> STUDIO
```

- **Layer 1: the typed operator library** — the foundation, roughly 1,000 ops connected by **type** (I call these "sorts" — the kind of data: `image / region / feature / contour / volume`).
- **Layer 2: two ways to use it** — most of the time you just **apply a known op** (`apply` / `run_pipeline`). Only when a single op can't solve the problem do you **design a pipeline via evolutionary computation** (`evolve` / `robust`).
- **Layer 3: the Physical AI perception stack** — the components that turn frames into geometry and objects. The toolkit a robot needs to **see, measure, and act**.
- And running across all of it, **Fullseye Studio** — an IDE, equivalent to HDevelop in industrial vision, for grasping, testing, and using the functionality in real work.

One tip for reading this diagram. Read the arrows not as "the direction data flows" but as **"the direction types are guaranteed."** Every Layer-1 op, called through `apply`, returns a typed result — which is why the evolutionary computation in Layer 2 can search over "arrangements of ops whose types connect" without caring what's inside each part. For the same reason, the Physical AI perception stack in Layer 3 can call Layer-1 ops **directly as components**. If Layer 1 offered no type guarantee, Layers 2 and 3 would both be stuck in a state of "you don't know if it actually works until you try it, every time." The reason a library at the ~1,000-op scale keeps growing without collapsing is that **every one of these arrows is backed by a type contract** — hold that thought, and the layer-by-layer explanations below should click together.

Let's dig into each layer.

---

## Layer 1: A Ready-to-Use Operator Library (~1,000 Ops)

> **Status: Production-ready / Verified** — installable from PyPI; 6,238 tests; every number is machine-tallied.

### What Is an Op? (In Three Passes)

1. **One-liner**: an op is "a single function — image in, image (or region, or number) out."
2. **A bit more**: in Fullseye, ops carry a **type (sort)**. "Image → region" (e.g. thresholding), "region → number" (e.g. counting objects) — **the input and output types are fixed**. That means ops whose types line up can be **chained like beads on a string**.
3. **Precisely**: every op can be called through one unified signature, `apply(image, name, a=0.5, b=0.5)`. `a` and `b` are two dials in `[0,1]`. Feature ops return a Python float, contour ops return a dict — a **type contract that every op honors**.

```python
import fullseye, numpy as np

frame = np.asarray(img, np.float64)              # H×W grayscale image [0,1]
edges = fullseye.apply(frame, "sobel_amp")       # image -> image (edge magnitude)
seg   = fullseye.apply(frame, "otsu")            # image -> region (binary {0,1})
n     = fullseye.apply(seg,   "count_obj")       # region -> feature (object count, float)

# Chain ops whose types line up: blur -> edges -> threshold
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
```

A word on the two dials `a, b` that appeared in the code. Why **exactly two knobs, `a, b ∈ [0,1]`, shared by every op**, instead of free-form parameter names per op? The reason is simple: so that **when evolutionary computation (Layer 2) searches over pipelines, it can search mechanically without knowing what any parameter means**. `gaussian`'s `a` is "blur strength"; `otsu`'s `a` might be a meaningless dummy that gets ignored, or repurposed as a threshold adjustment — the meaning differs per op, but **from the searcher's point of view, every op is just "two knobs between 0 and 1."** Standardizing the parameter count and range means the evolution code never has to care about any op's internals. This, too, is a design decision on the same line as Layer 1's "connect by type" philosophy.

Actual output is worth more than description. Here are the usual suspects — edge detection, segmentation, contour measurement — laid out in one montage (all real output from the `apply` / `run_pipeline` calls above; the input is the `coins` sample image bundled with scikit-image):

[![Real output montage from 2D classical vision ops (edges / segmentation / contour measurement, and more) — click for full size](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/vision_ops_montage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/vision_ops_montage.png)

A detailed breakdown of every panel (which op produced which value) lives in the repo's **[results gallery (docs/GALLERY.md)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/GALLERY.md)**.

### The Type (Sort) as a Backbone

Having 1,000 ops means nothing if each is an isolated island. What actually makes this work is one thing: **connecting by type (sort)**. Let me dig into that.

1. **One-liner**: every Fullseye op takes one of **six types** — `image / color / region / feature / contour / volume` — at its entrance, and returns one of them at its exit. "Thresholding (`otsu`) eats an image and spits out a region"; "counting objects (`count_obj`) eats a region and spits out a number" — the input/output types are **fixed** per op.
2. **A bit more**: the constraint that only type-compatible ops can be **chained** works in your favor. Just as a chessboard is readable because each piece has fixed moves, the rule "after this type, only that type can follow" means pipelines can be **searched without getting lost, even inside a combinatorial explosion**. The search space of Layer 2's evolutionary computation is, at bottom, an enumeration of "arrangements of ops whose types connect."
3. **Precisely**: type consistency is enforced as a **contract** by `tests/test_op_contracts.py`. `image`/`color` are floats in `[0,1]`, `region` is binary `{0,1}`, `feature` is a scalar float, `contour` is a dict with `{"shape","cs"}`, `volume` is a 3-dimensional float stack — **the shape of the output is itself the spec**. And the spec also demands finiteness (never return NaN/Inf) and determinism (same input, same knobs, same output). Ops that lean on luck, or ops that occasionally break, **cannot be registered in the first place**.

How type-incompatible connections get rejected matters just as much. Try to feed the output of `otsu` (image → region) straight into `sobel_amp` (image → image), and `run_pipeline` **fails explicitly, right there**. Not "it sort of runs but the numbers are wrong," but "the types don't connect, so it's refused before execution" — in cooking terms, it's like keeping the cutting board for raw fish separate from the one for bread. Things that must not be mixed are made **physically** unmixable. The fail-closed design philosophy (an idea that recurs throughout this article) does its first work at this smallest unit: the seam between op and op.

### The Six Types, Seen Through Concrete Connections

`image / color / region / feature / contour / volume` — six names alone won't mean much, so here's how they actually connect.

- **`image`**: an H×W float array in `[0,1]`. Ops like `gaussian` and `sobel_amp` that take an image and return an image belong here. It's exactly the first code example in Layer 1.
- **`color`**: the 3-channel version of `image` (H×W×3). Separating grayscale-only ops from color-only ops at the type level catches the classic accident — passing a color image where a grayscale one was expected — before execution.
- **`region`**: a binary `{0,1}` array. It's the exit of thresholding ops like `otsu` (image → region), and the entrance of measurement ops like `count_obj` (the HALCON counterpart; region → feature). Think of it as the type that answers "which pixels are the object?"
- **`feature`**: a single scalar float. It's often a pipeline's **final output**. "Object count," "mean brightness," "curvature correlation coefficient" — most of the measured values in the Layer-3 sections arrive as this `feature` type.
- **`contour`**: a dict with `{"shape", "cs"}`. It's the exit of edge-detection ops (`edges_sub_pix`) and the entrance of contour-selection ops (`select_contours`). The flow shown in the opening montage — subpixel contour extraction, then dropping short contours — is relayed precisely through this type.
- **`volume`**: a 3-dimensional float stack. The type for data with resolution along depth, like a CT volume. Many of the ops in the Layer-3 3D sections pass through it.

Line the types up and you notice that **common processing flows read directly as type sequences**: `image → region → feature` ("take a picture → separate out the objects → count them"), or `image → contour → feature` ("take a picture → extract contours → measure them"). Conversely, once you can read the types, you can **guess what could follow a given op without reading its implementation**. That reading works identically whether an AI is choosing ops as a RAG or a human is assembling a pipeline in Studio.

### What Happens When You Add One Op

Writing "there are 1,000 ops" makes it sound like they appeared all at once, but in reality this is the accumulated history of **adding them one at a time**. So what happens behind the scenes when you add one? Here it is, at a granularity a reader could retrace (`docs/ADDING_OPS.md` is the actual procedure; what follows is that, broken down).

```mermaid
flowchart TD
    A["Implement one op<br/>(write a function in ops.py /<br/>add a spec to backends_auto.py)"]
    B["It lands in the registry<br/>(a _DEFS tuple or a one-line spec)"]
    C["Instantly callable from<br/>apply / run_pipeline"]
    D["The evolution (evolve) search space<br/>grows by one<br/>(insertable anywhere the types connect)"]
    E["verify_auto.py runs it on real data and<br/>checks it returns its declared type<br/>(crashing or type-violating ops aren't counted)"]
    F["opdocs.py all auto-generates<br/>a Markdown note"]
    G["Reflected in Studio's help HTML<br/>(same path for 2D and 3D)"]
    H["Automatically included in the<br/>docs/ops/INDEX.md table of contents (folder walk)"]
    I["The drift CI compares<br/>committed notes == notes regenerated<br/>from current code"]
    J["Without a worked example it fails<br/>test_op_example_coverage"]

    A --> B --> C
    B --> D
    A --> E
    A --> F --> G
    F --> H
    F --> I
    A --> J
```

**There are two entrances for adding an op.** **Path A** (hand-written): write a function `_myop(v, a, b)` in `ops.py` and add one tuple to `_DEFS` — `("myop", "category", "halcon-name-or-empty", input sort, output sort, _myop)`. The `REGISTRY` is **rebuilt automatically** from these tuples, so there's nothing else to touch. **Path B** (data-driven) applies when the op fits one of the **already-validated templates**: pointwise / linfilter / rank / graymorph / edge / freq / diffusion / texture / geom / threshold / segment / binmorph / region_trans / region_feat / img_feat / xld. No code — add a **spec** with just a name, shape, and parameters, and it becomes an op. If it claims a HALCON alias, it is **checked against the list of real operators**, and if the operator doesn't exist, the spec is **dropped on the spot** (fail-closed, to prevent padding the count).

From here on, **everything follows automatically, with no human involvement**.

- **The evolution search space**: a new op becomes a candidate that can be inserted anywhere the types connect. Layer 2's `evolve.py` is a program that "searches for good arrangements of the ops that exist," so adding one op **silently widens the search space by one step** — the same feeling as dropping a new Lego brick into the bin.
- **The functional gate**: `verify_auto.py` runs the op, on the spot, against real image / region / contour data and confirms it **actually returns its declared type**. Ops that crash, or ops that betray their type, **are not counted**. It's the mechanism that keeps "the number registered = the number that works," by measurement.
- **Documentation**: running `py -3.11 tools/opdocs.py all` auto-generates the **Markdown note**, and from it, **Studio's help HTML** (2D and 3D through the same path) and the **table of contents (INDEX.md)** are updated in one sweep. Zero hand-written indices, as noted earlier — this auto-generation is what's behind that.
- **The CI drift test** (`tests/test_opdocs.py`) compares — with no side effects — "the committed notes" against "notes regenerated from the current registry," and fails CI on any mismatch. It mechanically prevents the **classic form of rot**: changing an op's spec and forgetting to update its note.
- Finally, `tests/test_op_example_coverage.py` checks: "does this op have a worked example with ground truth?" **An op without an example fails CI** — the last gate, which refuses to let "an op that works but that nobody knows how to use" exist.

Add one op, and the registry, the search space, code generation, documentation, the table of contents, CI, and Studio help all **update in a chain** — this "touch one point and the whole follows" design is exactly why a library at the 1,000-op scale **can be maintained by one person**. The fewer places a human hand has to intervene, the less room there is for the **seeds of rot** — "only the docs are stale," "only this op has no example" — to sprout.

### How Big Is It, Really? (Measured)

- **2D operators: 731** (of 735 registry entries, 731 are distinct by name), across **46 categories**.
- **3D operators: 265** (point clouds, meshes, volumes, SDFs, and more), across **55 categories**.
- Roughly **1,000 total**, covering denoising / smoothing / sharpening / thresholding & segmentation / morphology / edge, corner, and blob detection / distance transforms / color spaces / texture and shape features / contours / 3D geometry.

This "breadth" is faster to see than to describe, so here's a **treemap tallied mechanically from the actual registries** (area = number of ops per category; the script asserts the totals match 731/46 and 265/55 before drawing — a construction that can't inflate the numbers).

[![Fullseye operator taxonomy — a treemap of 731 2D ops / 46 categories and 265 3D ops / 55 categories (click for full size)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/op_taxonomy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/op_taxonomy.png)

*↑ Op taxonomy treemap — left, the 2D registry (halcon_ext 81, region 76, features 71, ...); right, the 3D registry (geometry 23, render 14, ...). Area = op count.*

And "what does the output actually look like?" in one image too: a sampler that **mechanically picks one representative op from each of 24 categories and applies it, for real, to the same coin photo** (zero skips; ops that return contours have their real XLD points baked in, and ops that return numbers — counting, matching, shape descriptors — are applied "the proper way" and shown as input + detection overlay + measured value: `blob_count` reads **count = 24 on a preprocessed region (asserted to equal the number of coins)**, `ncc_locate` draws a box at the position found with a real template, and `decode_barcode` runs on a synthetic barcode input, reading bars = 12).

[![2D op sampler — representative ops from 24 categories applied to coins (click for full size)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/op_sampler_2d_720.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/op_sampler_2d.png)

*↑ The 2D op sampler — from `gaussian` to `decode_barcode` to `xmh_zernike` (Zernike moments), 24 categories, 24 ways of "seeing." All real output.*

### The Workhorses of Factory Inspection Lines, One pip Away

Fullseye's op system, at bottom, was built having learned a great deal from **the HALCON lineage of industrial machine vision**. So ops corresponding to the "standard jobs" that have run on factory inspection lines come with a bare `pip install fullseye`. Let me be specific, with the names of implemented ops.

- **Defect detection**: `tophat` / `bothat` (grayscale-morphology top-hat and bottom-hat — the standard trick for lifting unevenness and small scratches off the background) and `morph_grad` (morphological gradient), plus **blob detection** (`xsk_blob_log` / `xsk_blob_dog` / `xsk_blob_doh`, which pick out blob-like defect candidates from scale-space extrema) and `blob_count` (the counterpart of HALCON's `count_obj`) — combine them and you have the inspection-line staple, "detect and count small stains, holes, and scratches."
- **Subpixel dimensional metrology**: counterparts of HALCON's `measure_pos` / `measure_thresh` / `measure_pairs` / `fuzzy_measure_pos` (**caliper measurement** — finding edge positions at subpixel precision inside a specified search window, to measure dimensions and positions) are implemented as `m1_measure_pos` / `m1_measure_thresh` / `m1_measure_pairs` / `m1_fuzzy_measure_pos`. The `subpix` op family — `sp_local_max_sub_pix` / `sp_saddle_points_sub_pix` / `sp_critical_points_sub_pix`, which find contour extrema and saddle points at subpixel precision — is there too.
- **Alignment (shape matching)**: `ncc_locate` (the counterpart of HALCON's `find_ncc_model`, template matching by normalized cross-correlation) and `shape_locate` (the counterpart of HALCON's `find_shape_model`, contour-based shape matching) handle **position and orientation finding** — the job at the entrance of every inspection line, working out "where is it right now?" before a robot grabs a part.
- **Code reading**: `decode_barcode` (the counterpart of HALCON's `find_bar_code`) covers **barcode reading** as well.

Individually these are unglamorous ops, but **the bulk of what actually runs day after day on factory inspection lines is, at bottom, combinations of exactly this kind of unglamorous classic**. There are still plenty of sites where combining **explainable, lightweight, deterministic** ops beats training a deep-learning object detector. Fullseye does lean toward Physical AI in Layer 3, that's true — but **the op system at its foundation has stood on the industrial-vision lineage from the very beginning** — which also resonates with the name's implication: "Bullseye = precision that doesn't miss."

The reason classical algorithms are still on active duty on inspection lines is simple. **On an inspection jig with fixed lighting and a fixed camera, looking for a known defect on a known part**, there's usually just not enough complexity to justify the cost of collecting training data and retraining. What matters more, on a mass-production line, is being able to **explain outright, in the language of thresholds and algorithms, why this part was judged defective**. As written in Layer 1's "The Type (Sort) as a Backbone," Fullseye's ops are deterministic — same input, same knobs, always the same result. That's a property trained models don't have, and it matters more the more a site is held accountable for its **inspection criteria**.

Words alone stay abstract, so here are these "inspection-line standards" actually assembled and run (all real processing on synthetic data; detection and measurement results are checked against known ground truth — for example, defect detection is confirmed at 6/6 and particle counting at 60/60 by asserts).

[![Surface defect inspection — background subtraction + blob analysis](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_defect_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_defect.png)

*↑ **Surface defect inspection** — 3 scratches, 2 dents, and 1 foreign particle on a synthetic metal surface: estimate the base texture with a median filter → difference heatmap → blob analysis detects 6/6. A truth-free feature classifier (eccentricity, redness) then assigns **the correct type to every defect** — shown with type-colored boxes and 3× zoom insets. Ops used: `median_image`, `dilation_circle`, `segment_objects`.*

[![Subpixel dimensional metrology — 1D measuring calipers](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_metrology_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_metrology.png)

*↑ **Subpixel dimensional metrology** — edge pairs extracted by subpixel interpolation of the derivative extrema of the gray profile along a measurement rectangle. The diameters of a 3-step shaft are measured, with a maximum error of 0.02px against the drawn dimensions. The same manner as HALCON's 1D Measuring. Ops used: `m1_measure_pairs` and others.*

[![Alignment — shape matching with rotation search](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_align_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_align.png)

*↑ **Alignment** — an edge-gradient shape model matched by pyramid search detects the position and angle of 3 rotated workpieces (agreeing with ground truth to 0.0px and 0.0°). It does not react to the confusable decoy parts — the disk and the rectangle. Ops used: `create_shape_model`, `find_shape_model`.*

[![Blob analysis — particle counting and size distribution](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_blobs_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_blobs.png)

*↑ **Particle counting** — 60 particles (6 pairs touching) split apart by marker-based watershed, counted 60/60, and color-coded into 3 sizes by area. The standard pattern for quality inspection of powders and granules. Ops used: `otsu`, `xcv_watershed_markers`, `segment_objects`.*

[![The foundation of code reading — bar detection by scanline edge pairs](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_barcode_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/industrial_barcode.png)

*↑ **Bar detection** — just like a real reader, bar edge pairs are detected from the gray profile along a scanline. Both ends of all 45 bars located within ±1.5px (this is the raw material for bar detection and width measurement, not a full decoder). Ops used: `decode_barcode`, `m1_measure_pairs`.*

### The Yardstick Is HALCON (42.5%, Measured)

To avoid talking about "coverage" subjectively, I use the industrial-vision giant **HALCON** as a yardstick. Against the list of **2,313 operators** compiled from the official reference, each Fullseye op is tagged with "which real operator does this correspond to?", and the tally is done mechanically.

Let me pause on why a yardstick is needed at all. "There are about 1,000 ops" tells a reader nothing on its own — is that a lot, or a little? **The number 1,000 has no meaning until it's compared against something.** But declaring "it's comprehensive" subjectively would violate this article's undercurrent, honest disclosure. So the method I chose was: **measure with the same yardstick as the giant actually used in industry, and produce the number by mechanical tally**. I picked HALCON not merely because it's famous, but because **its operator list is organized and published as an official reference** — that is, for its high comparability.

> **imgevolve maps to 982 / 2313 HALCON operators (42.5%)** — not from memory, but measured against the scraped list.

To be honest, that's **still under half**. Chapters like Tuple handling, System, Classification, and OCR are almost entirely untouched (they sit outside the core of image processing, so I've deprioritized them). Matching, Morphology, Filtering, and geometric measurement, on the other hand, are where I've built thick. The heart of this number is that **a per-chapter table showing "what's filled in and what's empty" stays open for anyone to see, at all times.**

### The Per-Chapter Map — Thick Spots and Empty Spots

HALCON's 2,313 operators are divided into **30 chapters**. Fullseye's 982 counterparts are **not** spread evenly across them.

Where I've built thick is the chapters at the heart of image processing: **Filtering** (smoothing, edges, frequency-domain filters), **Morphology** (dilation, erosion, opening, closing), **Regions** (region operations and feature measurement), **Segmentation** (thresholding and region splitting), and **Matching** (template and deformable matching) — all painted **far denser** than the overall 42.5% average. The thin spots are chapters like **Tuple handling** (numeric-tuple operations, the programming-language side of HDevelop), **System** (process and thread control), and **Classification / OCR** (machine-learning-based classification and character recognition). Those are nearly untouched — that's the honest state of things.

The skew described in words is disclosed as-is in a **per-chapter coverage bar chart** (the drawing script asserts agreement with the measured numbers in `docs/HALCON_COVERAGE.md`).

[![HALCON per-chapter coverage — the breakdown of 982/2313 (42.5%) (click for full size)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/halcon_coverage_chart_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/halcon_coverage_chart.png)

*↑ The thick spots (Regions 105/106, Morphology 42/44, Filters 186/196) and the deliberately empty ones (System 0/141, OCR 0/96, Tuple 0/165) are visible at a glance.*

This skew is not because **I haven't gotten around to it** — it's a skew **I aimed for from the start**. The next section explains the reasoning behind that call.

### Deciding What Not to Build

The moment you pick HALCON as a yardstick, a question arises: "So — are you going to build all 2,313?" The answer is **no**.

Chapters like Tuple, System, File, Develop, and Control are **not image processing itself — they're the plumbing that runs HDevelop, the development environment**. Launching processes, opening files, saving variables — these are areas Python's ecosystem is already good at, and there's little point in a numpy-based vision-skill library reinventing them. Classification, OCR, and Deep Learning are a different domain that **requires trained models**, falling outside Fullseye's very axis of "classical algorithms whose internals can be explained." Legacy is, literally, deprecated.

This is the same call, repeated, as the **change of direction** described in "Why I Built This" (the redefinition from `imgevolve` to Fullseye). Just as when I cut general-purpose algorithms (sorting, compression, and so on), the house rule at work here is: **deciding what not to build does more than deciding what to build**. Widening the scope would grow the headline number, but it would mean **scattering shots away from the target of image and geometric vision — the very target the name Fullseye is about**. I write "still under half" about the 42.5% while refusing to widen the scope, because **the denominator of that number is itself deliberately narrowed**.

Of course, this wasn't a monolithic, obvious call. A design aiming for "full HALCON compatibility, Tuple and System included" was conceivable in principle. I didn't choose it because Fullseye's reason for existing is not "build a HALCON substitute" but "**make explainable algorithms something you can carry around as a robot's eyes**." Borrow HALCON as a yardstick, but never try to become HALCON — and keeping that line **permanently disclosed, in the form of the per-chapter table**, is, I believe, the plainest and most effective mechanism for "not inflating claims of coverage."

### Making Docs a Single Source of Truth (md = SoT)

With 1,000 ops, **the library is unusable without help text**. But maintaining help HTML and AI-facing descriptions as two separate things guarantees one of them rots. So the approach I took was **making Markdown the single source of truth**.

```mermaid
flowchart LR
    MD["docs/ops/**/*.md<br/>Per-op Markdown notes<br/>(author, license, version, references,<br/>sample-data download URL, related-op links)"]
    MD -->|bulk conversion| HTML["Studio help HTML<br/>(2D + 3D)"]
    MD -->|walk folder hierarchy| TOC["Auto-generated INDEX"]
    MD -->|hierarchical clustering| RAD["A navigable corpus<br/>an AI can query"]
    MD -->|drift test| CI["CI fails if versions drift<br/>(pins docs and code to the same version)"]
```

- **A Markdown note per op** (roughly 1,000 of them) is the source of truth. Frontmatter carries **author, license (Apache-2.0), library version, references, real sample-data download URLs, and links to related ops**.
- From there, **Studio's help HTML is generated in bulk** (2D and 3D through the same path). **There is no dual maintenance.**
- **The table of contents is auto-generated by walking the folder hierarchy.** Zero hand-written indices.
- **Version pinning** matters more than it sounds. Image processing is a domain where "a tiny spec change translates directly into different results." So CI includes a **drift test that compares "committed notes == notes regenerated from the current registry," with no side effects** — change an op's spec, and the notes fall out of sync and the test fails. In other words, **docs and code stay pinned to the same version**.

This "md as source of truth" work was finished during **the very sequence of work that produced this overview article** — related-op links, references (Tomasi & Manduchi 1998, Serra 1982, Sobel & Feldman 1968, and so on — **real classical papers, cited accurately, no fabricated DOIs**), and real sample-data URLs, all brought into a shape that can **stay maintainable for years**.

(One more word, from experience.) I once tried "write the help HTML by hand, write the AI-facing descriptions separately." The result was an instructive failure. Change one op parameter, and you **fix the HTML, feel satisfied**, and forget the AI-facing description. Or fix the AI-facing one and forget the HTML. Within half a year, **even the author can no longer tell which one to believe** — dual-maintained documentation always ends up here if left alone. Unless the structure makes one the truth and the other a mere projection, **both gradually start lying**.

Since moving to md=SoT, this class of accident — "one side quietly went stale" — has become structurally impossible. Fix the note, and the HTML and the table of contents follow. Forget to fix the note, and the CI drift test **tells you** (it fails, so you can't not notice). Replacing "be careful" with "guaranteed by a mechanism" — this shares a root with the article's undercurrent, honest disclosure. Don't rely on human attentiveness.

Having read Layer 1 this far, I hope it's visible that the three ideas — "type (sort)," "the chain of automation when one op is added," and "md=SoT" — are really **three faces of one and the same design decision**. Types guarantee the seams between op and op; md=SoT guarantees the seam between code and documentation — each **by mechanical contract, not human attentiveness**. It's because this foundation exists that Layer 2's evolutionary computation and Layer 3's Physical AI perception stack can be stacked on top without worrying about Layer 1's internals. In Layer 2, next, a different kind of honesty is demanded: honesty in "searching for good arrangements" on top of that foundation.

---

## Layer 2: Designing Pipelines by "Evolution" (with Honest Evaluation)

> **Status: PoC** — validated in **bounded settings** with hold-out evaluation. I'm not yet claiming general-purpose automatic design.

Only for problems a single op can't solve — "I want to find the processing sequence that maximizes this metric on this data" — does **evolutionary computation** come in. As stated in Layer 1, "most of the time you just apply a known op": this is **a supporting role, not the lead**. Picking and chaining from 1,000 ops covers most needs; the search machinery is kept in reserve for the cases where even that falls short — where the optimal combination is hard for human intuition to find.

```bash
py -3.11 baseline.py --problem denoise --workdir out/mine     # measure an honest floor first
py -3.11 evolve.py   --problem denoise --workdir out/mine --gens 40 --pop 24
py -3.11 robust.py   --problem denoise --workdir out/mine --seeds 5
```

The thing I care most about here is **honesty in evaluation**.

- **Fitness is measured only on the training split.**
- **The hold-out split is tracked, but never, ever used for selection.**

This keeps the generalization performance I report from being "overfit to the evaluation set" — it stays an **honest number**. "When a good result comes in, doubt the breakdown before feeling like you've won" — that's a house rule for the whole development effort.

### What Each of the Three Commands Does

Let's break those three command lines down one more level.

1. **`baseline.py`** — first, measure **what score you get by doing nothing, or by the most naive method**. In Go or shogi terms, it's like first measuring how well a novice who knows no established openings can play. Without this, "evolutionary computation produced a good number" is undecidable — is it **impressive, or just what anyone would get?** "Measure the baseline first" is, of the house rules that recur throughout this article, the plainest and the most effective. When an unusually good number appears, the first response is "and the baseline was...?" — that's the habitual retort inside this development team (of, effectively, one).
2. **`evolve.py`** — a **genetic algorithm** evolves the arrangement of ops (the pipeline) itself. Each generation (`--gens`), a population of pipelines (`--pop`) is mutated and crossed over, and the individuals with the best fitness on the training data survive. The key point: **the object of the search is "an arrangement of ops," not "the weights of one giant model."** The solutions that come out are **human-readable sequences of ops**, so why a solution works can be **verified after the fact**.
3. **`robust.py`** — runs `evolve` independently multiple times with multiple seeds (`--seeds`), and picks one best individual **selected on the training data** (best-of-N, train-selected). The goal is to average out the luck of the random draw.

The `--problem denoise` in the example specifies noise removal as the objective — one example among several. `baseline.py` first measures the score of a naive method (say, a single Gaussian blur with fixed parameters); `evolve.py` starts from there and searches, generation by generation, for a **better pipeline** chaining Layer-1 ops (a combination like "median filter → bilateral filter → unsharp mask," for instance). Some combinations a human would think of from the start; others come out in an **order that surprises a human** — that's the fun of using a genetic algorithm, and being able to read back, op by op, *why* that order works is the payoff of Layer 1's typed design.

### Why "Never Select on Held-Out Data" Works (Intuitively)

Why is this seemingly roundabout rule — "track the hold-out but never use it for selection" — necessary? Let me attempt an intuitive explanation.

Imagine a student cramming for an exam who **solves past papers over and over until they've memorized the answers**. Their score on the past papers (the training data) keeps rising — but is that "deeper understanding" or "mere memorization"? The past papers alone can't tell you. The only way to tell is to measure on **new problems they haven't seen (the hold-out)**. Here's the trap: if you re-select your study method in the direction that "raises the hold-out score" — say, by repeatedly keeping only the textbooks that scored well on the hold-out — then **the hold-out itself becomes something being memorized**, and it loses its meaning as a measurement.

The same thing happens in evolutionary computation. If per-generation selection (which individuals survive) is driven by the hold-out score, then over many generations, **the only pipelines left standing are the ones that "work on" that one particular hold-out dataset**. That isn't generalization — it's **overfitting to the hold-out**. So in Fullseye, selection is always done on training data alone, and the hold-out sits **outside the selection process**, as "the window you peek through at the end to see whether it truly generalizes." Think of it as the evolutionary-computation version of the statistical-testing discipline "don't run multiple comparisons on the data you set aside for validation."

To be honest, keeping this discipline tends to make **the headline numbers more modest**. There really have been moments where selecting toward the hold-out would have made the reported performance look better. I still don't use the hold-out for selection, because a number that **won't betray you later** is worth far more, for keeping development going, than a number that flatters you now.

---

## Layer 3: The Physical AI Perception Stack (a Robot's Eyes)

> **Status: Research prototype** — everything demonstrated in this chapter runs **in simulation**. Real hardware and sim-to-real are untouched.

The components that turn frames into **geometry and objects**. The toolbox a robot needs to see, measure, and act.

```python
import fullseye as fs
disp  = fs.disparity_map(left, right, max_disp=16)          # stereo disparity
Z     = fs.depth_from_disparity(disp, focal=f, baseline=B)  # depth  Z = f·B/d
pts   = fs.reproject_to_points(Z, fx=f, fy=f)               # point cloud (N,3)
grid,_= fs.elevation_map(world_pts, cell=0.05)              # 2.5D terrain height map
ok    = fs.traversability(grid, cell=0.05, max_step=0.1)    # foothold/obstacle mask
objs  = fs.segment_objects(frame, threshold="otsu")        # per-object geometry + descriptors
```

These six lines actually run the whole way from **"seeing" to one step short of "walking / grasping."** From the two camera images (`left, right`), compute the disparity `disp`; convert it to depth `Z` (this is exactly the $Z = f \cdot B / d$ introduced in the stereo section below); back-project the depth into a 3D point cloud `pts`. From there, build the terrain height map `grid`, and let `traversability` decide "where can be walked and where can't." The last line, `segment_objects`, splits the image into objects and extracts each one's geometry (position, size, and so on) and descriptors (the features used for identification) — in factory bin-picking terms, this is precisely the "which part is where?" computation. What these six lines expose is the structure: Layer 3 calls Layer-1 ops **through a thin facade (an outer interface) renamed to match the purpose**.

This layer also includes a **full sensor-simulation suite**. Without owning any hardware, you can synthesize the output of **pseudo-LiDAR, stereo cameras, event cameras (DVS), photometric stereo, TSDF fusion, polarization cameras, and focus stacking** from a synthetic scene, and develop and validate perception pipelines **with no hardware in the loop** — a practice ground for Physical AI development. Every image below is real output from Fullseye's own ops:

[![Physical AI sensor-simulation montage (pseudo-LiDAR / stereo depth / event-camera DVS / focus stacking / polarization camera / camera+IMU fusion) — click for full size](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/physical_ai_montage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/physical_ai_montage.png)

Panel-by-panel explanations, and the other results (3D rendering, mesh processing, turntable GIFs, etc.), live in the **[results gallery (docs/GALLERY.md)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/GALLERY.md)**.

### The Six Sensors, One at a Time

The montage's six panels are six independent sensor simulations. The point of the picture: take the same synthetic MuJoCo scene (a green box, a yellow cylinder, a blue sphere, an orange crate, a purple slab) and see how it changes through the eyes of six different sensors. Let's take them one by one — each principle broken down in three passes, with the measured values baked into each panel.

#### LiDAR (Light-Based Ranging)

1. **One-liner**: a sensor that fires laser light in all directions and measures **distance** from the time (or phase) it takes to bounce back. The thing on the roof of self-driving cars.
2. **A bit more**: Fullseye's simulation renders the scene as a **range image** (an image where each pixel holds a distance) and **back-projects it into a 3D point cloud**. Just as a real LiDAR's resolution is set by its channel count (how many lasers are stacked vertically), the simulation mimics **32 channels**.
3. **Measured**: the output of `lidar_sim.py` shows **2,965 points, 32 channels, hit ratio 26%**. Hit ratio is "of the rays fired, the fraction that actually struck an object" — the other 74% flew into the background or out of the field of view, which is **natural for an indoor scene of sparse objects**. In a scene crowded with dense objects, the ratio climbs.

#### Stereo Depth (Two-Camera Depth Estimation)

1. **One-liner**: computing distance from the **offset (disparity)** between the images of two cameras — the same principle as your own two eyes.
2. **A bit more**: find the same pattern in the left and right images (block matching) and measure the offset (disparity). The closer the object, the larger the offset; the farther, the smaller — and the formula $Z = f \cdot B / d$ (focal length × baseline ÷ disparity) converts that into distance $Z$. This is exactly the `depth_from_disparity` from this layer's opening code example.
3. **Measured**: `stereo_sim.py` outputs **depth corr 0.55, median err 1.3cm**. Depth corr is the correlation between estimated depth and true depth (the answer MuJoCo knows); median err is the median of the error. **Matching is hard on low-texture flat surfaces (the white block at the top center of the montage), and error creeps in there** — a classic weakness of stereo vision, and one that shows honestly in the numbers.

#### Event Camera (DVS — a Sensor That Emits Only Motion)

1. **One-liner**: instead of spitting out "30 frames per second" like an ordinary camera, each pixel emits an event asynchronously **only at the moment its brightness changes**.
2. **A bit more**: each pixel independently fires one event — + (brighter / ON) or − (darker / OFF) — whenever its log-luminance changes past a threshold. No motion, no output — **it fundamentally cannot see a static scene, but it is extremely strong on motion** (microsecond-order temporal resolution, wide dynamic range).
3. **Measured**: `event_camera.py` outputs **247,189 events, edge-corr 0.56**. Edge-corr is the correlation between "where events fired densely" and "the edge strength at that location (contour strength à la Sobel)" — corroborating that **events fire along contours**. The number matches intuition, but "back up designs that seem intuitively right with measurements anyway" is how honest disclosure works.

This DVS is **easiest to appreciate in motion**, so a streaming gif follows below.

#### Focus Stacking (and Depth-from-Focus)

1. **One-liner**: shoot many frames while varying the focus distance, then **collect from each photo only the places that are in focus** and stitch them together. Common in macro photography and microscopy.
2. **A bit more**: from the image at each focus distance, measure per-pixel **sharpness (local contrast)**, adopt the sharpest focus position, and stitch — the result is an **all-in-focus image** (focus stacking). At the same time, if you record per pixel *which* focus distance was sharpest, that is directly an **estimate of the distance to that pixel** (depth-from-focus).
3. **Measured**: `focus_stack.py` composites from 3 focus distances — near (0.91m), middle (3.33m), far (5.74m) — with a **sharpness gain of ×1.27 and depth corr 0.89**. The ×1.27 is "how much sharper the composite is than any single-focus frame"; depth corr is the correlation between depth back-computed from focus and MuJoCo's ground-truth depth. **0.89 is on the high side among the six panels** — it stands to reason that using multiple focus distances is steadier than single-shot stereo.

#### Polarization Camera (DoLP / AoLP — Seeing Light's "Oscillation Direction")

1. **One-liner**: an ordinary camera sees only light's **intensity**; a polarization camera also sees its **oscillation direction (polarization)**. At equal brightness, reflected light polarizes differently depending on **surface orientation** — so this oddball sensor can recover **normals (surface orientation) even on smooth, textureless surfaces**.
2. **A bit more**: from images taken through polarizers at 4 orientations, reconstruct the Stokes vector, and from it compute **DoLP (degree of linear polarization, 0–1)** and **AoLP (angle of linear polarization)**. Following the Fresnel reflection equations, DoLP lets you back out the **surface tilt (zenith angle)** and AoLP the **tilt direction (azimuth)** — that's the physical model.
3. **Measured**: `polar_cam.py` outputs **mean DoLP 0.79, Stokes round-trip 1.00**. Round-trip 1.00 means the round conversion — build the Stokes vector from the 4 polarizer images, then recompute the original 4 images from it — **matched perfectly** (an internal consistency check of the implementation). The high DoLP is consistent with physics: the montage's sphere material is on the glossy side, and **polarization gets stronger near grazing angles (viewing directions nearly parallel to the surface)**.

#### Camera + IMU Sensor Fusion (Kalman Filter)

1. **One-liner**: the classic technique of fusing a camera-only position estimate (noisy) with an IMU-only estimate (drifting — error accumulating over time) so that **each covers the other's weakness**.
2. **A bit more**: a Kalman filter alternates "predict" and "correct with an observation." Predict the motion from the IMU, correct with the camera's observation — both sources are imperfect, but **their error characters differ (noise vs. drift)**, and exploiting that difference produces an estimate better than either alone.
3. **Measured**: `sensor_fusion.py` is a demo tracking the parabolic flight of a thrown ball. Against a **position-sensor-only RMSE of 22.6cm** and an **IMU-dead-reckoning-only RMSE of 8.4cm**, **Kalman fusion lands at RMSE 6.1cm**. Smaller error than either source alone — one picture that shows the payoff of sensor fusion, in numbers.

Six different principles, but the implementation footing is shared: **no external simulator or sensor-vendor SDK is being called — every sensor model is written in the same numpy as Layer 1's typed ops**. The LiDAR raycasts, the stereo block matching, the polarization Stokes-vector math — at bottom, each is nothing more than a composition of "functions that take arrays and return arrays." Wildly different physical phenomena being simulated per sensor, yet **the way you call them and the way you verify them is uniform** — I take that as evidence that the design principles repeated throughout Layer 1 ("connect by type," "verify via md=SoT") keep functioning, unbroken, even when carried into the more complex destination that is Physical AI.

### Simulation and the Factory Line Stand on the Same Op System

The six sensors above were introduced in a Physical AI (robot perception) context, but the same ops are built to serve just as well in the context of **factory inspection and picking lines**.

- **Stereo disparity → depth → point cloud** (the same path as this section's `stereo_sim.py`) feeds directly into **bin picking**. In fact, a worked example ships with the library (`examples_3d/object_segmentation.py`) for the workflow "remove the table plane, then split the objects into clusters" using `euclidean_cluster` (an op that distance-clusters a point cloud via connected components of a proximity graph). It also includes the honest-gate comparison against the "do nothing" zero point: cluster without removing the table plane, and every object fuses into a single blob.
- **Clustering LiDAR point clouds** is the same `euclidean_cluster`'s territory. There's a worked example for the outdoor-scene case — ground removal followed by object segmentation, the situation robots in warehouses and open yards actually face (`examples_3d/lidar_scene_segmentation.py`). In this example, a LiDAR cloud of 5,316 points covering 4 objects (sphere, box, cylinder, cone) resting on sloped ground (about 5.4°) is processed by detecting the ground with `fit_plane_ransac`, keeping only points above it, then splitting with `euclidean_cluster`. As measured, the number of detected clusters matches the true object count (4), and cluster centroids map one-to-one onto the true objects with a maximum error of 0.128m. **Skip the ground removal and cluster all points as-is, and every object fuses into one blob** — the comparison against this "do nothing" case backs the value of that one extra step with numbers.
- For **grasp-point detection**, there's a path using curvature analysis (`principal_curvatures` / `gaussian_curvature`) — the `curvature_grasp` worked example. It's the classical approach of narrowing candidate points from the target's shape: "a graspable spot = a smoothly convex spot."
- The **event camera (DVS)** also gets along well with the industrial side, in the role of **capturing motion without blur on high-speed conveyor lines** (by principle, it has no motion blur at all).

A robot-vision pipeline grown inside simulation can be reused, as-is, as a component of an inspection line — that's not a bonus; it's a direct consequence of the design: **both stand on the same typed op system.**

Here is that consequence, actually assembled and run in simulation (all real processing on MuJoCo physics, real raycasts, real renders; cluster counts and object counts checked against ground truth).

[![Bin picking — depth segmentation and grasp-candidate scoring](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_binpick_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_binpick.png)

*↑ **The front half of bin picking** — 10 parts dropped into a bin under physics simulation, observed by an overhead depth camera → depth segmentation → 8 grasp candidates scored by "surrounding clearance + height" (green = top priority). Gripper-jaw orientation comes from the long axis of a rectangle fit. Ops used: `segment_objects`, `fit_rectangle2`, `colorize_depth`.*

And from these scores there's also a video of the **full cycle — actually grasping and carrying out with 6-DoF IK** → [phai_bin_pick.mp4 (plays inline on GitHub)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/phai_bin_pick.mp4). Plain physics with no adhesion tricks, and only parts that end up outside the bin count as successes: 3 parts carried out, honestly tallied.

[![LIDAR point cloud → ground removal → clustering](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_lidar_clusters_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_lidar_clusters.png)

*↑ **LIDAR obstacle recognition** — over 20,000 rays actually cast, mimicking a ring LiDAR; RANSAC ground removal → Euclidean clustering resolves 6 objects into 6 clusters. Each cluster gets an OBB, shown in bird's-eye view. Ops used: `remove_ground`, `euclidean_clusters`, `obb`.*

[![Stereo disparity → 3D reconstruction → bird's-eye obstacle map](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_stereo_obstacles_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_stereo_obstacles.png)

*↑ **Stereo obstacle map** — disparity → depth via $Z = f \cdot B / d$ → 3D point cloud → clustering everything above 12cm resolves 4 objects into 4 clusters (the reconstructed ground height has a median error of 3mm). The disparity panel shows only the disparities that survive a speckle filter + confidence gate — invalid pixels are masked gray. Ops used: `disparity_subpixel`, `disparity_confidence`, `euclidean_clusters`.*

[![Focus stacking — one all-in-focus frame from 7 blurry ones](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_focus_stack_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/phai_focus_stack.png)

*↑ **Focus stacking** — from 7 frames with swept focus positions, pick the sharpest per pixel and composite (sharpness 1.27× a single shot). The mechanism used in microscope inspection and PCB inspection.*

One of these, the **event camera (DVS)** — the sensor that asynchronously emits nothing but per-pixel brightness changes — is easiest to appreciate in motion. As the camera pans, ON events (cyan) and OFF events (magenta) stream along the edges:

![Event-camera (DVS) simulation — ON (cyan) and OFF (magenta) events firing along edges as the camera pans](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/dvs_stream.gif)

A smoother **mp4 version**, along with the turntable videos including Itokawa, lives in the repo's [docs/articles/assets/media/](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/media) (playable directly on GitHub).

### How Far the 3D Stack Goes Custom-Built (the Biggest Differentiator)

I think Fullseye's differentiation shows up most in the **3D side**. Classical 2D image processing is already broadly covered by powerful OSS — OpenCV and scikit-image. Merely stacking numpy reimplementations there would, frankly, invite a fair accusation of "reinventing the wheel." 3D is different: it spans multiple data formats — point clouds, meshes, volumes — and as far as I've been able to find, there aren't many libraries that cover that ground while holding the whole set of conditions "typed, pure numpy, with machine-readable notes." That's why this section runs a bit longer than the other layers and spends its pages on demonstrations with real data.

Apply 3D ops to the real Itokawa point cloud from the opening GIF, and you get this:

[![3D ops on the real asteroid Itokawa point cloud (curvature analysis / ICP self-registration / PCA canonical pose) — click for full size](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/itokawa_montage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/itokawa_montage.png)

On a real point cloud of 3,000 points: **curvature analysis** (neighborhood-curvature correlation r=0.87 — evidence of a real surface), **ICP self-registration** (recovering an unknown 30° rotation plus noise down to 0.027° rotation error), **PCA canonical pose** (fully recovering the principal axes after an unknown 50° rotation). All measured values, executed on the spot.

Let's look at the four panels a bit more carefully.

- **① The raw point cloud**: `itokawa_points.npy` holds 3,000 points, with a bounding extent of **559×301×242 m** — Itokawa is an elongated, "sea-otter-shaped" asteroid just under 600m along its long axis, and these dimensions capture that shape well. Color encodes distance from the origin (near the centroid); the rocky shading comes from the 3D renderer.
- **② Curvature analysis**: `curvature3d.curvedness` is an op that quantifies each point's **degree of bending** (one of the curvature notions touched on again in the Layer-3 details). Measured: **mean curvedness 0.0102, standard deviation 0.0059**, and **curvature correlation with neighboring points r=0.87**. Put into words, a high correlation here means "adjacent points bend in similar ways" — a property **peculiar to a real, continuous surface**. If this were just a random scatter of points, curvatures would be all over the place and the correlation would sit near zero. r=0.87 is indirect but quantitative evidence that this point cloud **was sampled from the surface of a real rock**.
- **③ ICP self-registration**: make a copy of the same cloud with an **unknown 30° rotation and sensor noise** added, and test whether it can be registered back onto the original (ICP — Iterative Closest Point). Measured: **rotation error 0.027°, RMSE 4.27m**. For a sense of how small 0.027° is: it's roughly **1/13,000 of a full 360° turn** — under noisy conditions, essentially a complete recovery.
- **④ PCA canonical pose**: compute the cloud's principal inertial axes (three orthogonal axes, the eigenvectors of the moment of inertia) and test whether they can be recovered after an **unknown 50° rotation**. Measured: **principal-axis ratio 4.02:1** (the eigenvalue ratio of the longest to the next-longest axis — a number expressing Itokawa's elongation), **axis recovery |cos| ≥ 1.0000** (the principal axes recovered with perfect alignment even after the 50° rotation).

The heart of it: all three analyses cross-examine **the same 3,000-point real cloud from different angles for realness and reproducibility**. Curvature asks "is this consistent as a surface?", ICP asks "can this be identified as the same object?", PCA asks "can orientation be recovered when it's been lost?" — each with different mathematics (differential geometry, nearest-neighbor search, eigendecomposition). Rather than just enumerating 3D op coverage, I believe **cutting into the same data from multiple angles, live**, conveys the value of explainable vision better.

### The Renderer Is Custom Too — Decomposing "Appearance" Into Measurable Parts

The image at the top of this article (SDF smooth union + AO + soft shadows + ACES) and the Itokawa turntable GIF are both output of the **custom renderer**. What matters here is less "it looks pretty" than the fact that **every element that produces the "appearance" is decomposed into its own independent op**. The results gallery (`docs/GALLERY.md`) carries figures where each element can be verified on its own.

- **Ambient occlusion (AO)**: fire rays per vertex into the hemisphere, measure how occluded the surroundings are, and selectively darken contact areas and concavities. Easier to grasp as visualizing "places where light has trouble arriving because something is there" than as a shadow.
- **Shading**: Phong specular highlights over normal maps, and MatCap shading (approximating material response with a spherical texture that has the environment pre-baked in) — held as separate ops.
- **Shadow mapping**: cast shadows determined by visibility from the light source, with soft shadows (blurred-edge shadows) available by approximating an area light.
- **SSAA (supersampling anti-aliasing)**: render at higher resolution and downscale, erasing the jaggies along mesh silhouettes.
- **Tone mapping**: compress HDR renders (wide exposure range) into the normal display range while **preserving gradation**, via Reinhard or ACES, where naive clipping would blow out highlights and crush shadows. The gradation preservation is confirmed by measurement against the naive clip.

These are not "decoration for looks" — **each is an independently verifiable op**. For AO, "are the more-occluded vertices actually darker?"; for tone mapping, "is gradation restored in regions that used to blow out?" — both check out numerically. Behind the single hero image at the top of the article sits a stack of **measurable parts written as typed ops** — Layer 1's "type (sort) as a backbone" philosophy applied consistently even to rendering, a field that looks far removed from it.

3D ops currently number 265. Spanning point clouds, meshes, volumes, and SDFs, the library carries **3D feature descriptors** like SHOT, FPFH, and spin images, **TSDF fusion**, **fringe projection**, **photometric stereo**, **superquadric fitting**, **medial axis**, **geodesic distance**, **visual hull**, and **QEM mesh simplification (boundary-preserving, strictly manifold)**.

There's also a one-image sampler that **applies the basic 3D ops in sequence to the same real Itokawa cloud** (normal estimation, shape index, voxel decimation 3,000 → 635 points, OBB, convex hull — all actual execution results).

[![3D op sampler — normal estimation / shape index / voxel decimation / OBB / convex hull on the real Itokawa point cloud (click for full size)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/op_sampler_3d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/op_sampler_3d.png)

*↑ The 3D op sampler — the measured OBB extents are 281×149×122 m. Not a textbook figure: numbers measured on this asteroid's real data.*

A few more, in the flesh:

![Two touching objects separated by distance transform + watershed. A case where connected-component labeling would merge them into one](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/examples_3d/_gallery/watershed3d.png)

*↑ 3D watershed segmentation — splitting two touching objects along the "valleys" of the distance transform. The tool for that bin-picking situation where parts overlap.*

![Measured comparison of QEM edge-collapse mesh simplification, boundary-preserving and strictly manifold](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/examples_3d/_gallery/mesh_decimate.png)

*↑ A measured comparison of QEM mesh simplification. Decimating while confirming, by measurement, that boundaries are preserved and manifoldness isn't broken — this op is also the stage for Bug 6 in this article (later).*

![A procedural hand skeleton, voxelized → marching_cubes → spun on a museum-specimen-style turntable with a bone-colored material (laid palm-up)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/examples_3d/_gallery/showcase_turntable_skeleton.gif?v=2)

*↑ The procedurally generated hand skeleton (8 carpals, 5 metacarpals, 14 phalanges = 27 bones in all — the same subject as `hand_hero.png` from "The Name" section), its SDF dropped into an occupancy voxel grid, meshed with `marching_cubes` (isosurface level 0.5), and spun like a skeleton specimen. Laid palm-up and rotated once under a high-angle view. Volume → mesh → render, straight through.*

The individual algorithms are scattered across PCL (C++) and Open3D, but **one library holding this range as "pure numpy, typed, with machine-readable notes on every op" is a configuration I don't see much of**. The aim is for the same writing feel to reach from industrial fringe-projection metrology to a robot's grasp pose.

The **3D data to try this on is available free from public sources.** The usual suspects:

- **[Stanford 3D Scanning Repository](https://graphics.stanford.edu/data/3Dscanrep/)** — bunny / dragon / armadillo. The "Lenna" images of the 3D world.
- **[JAXA DARTS Hayabusa archive](https://data.darts.isas.jaxa.jp/pub/hayabusa/shape/gaskell/)** — the source of this article's Itokawa shape model ([the PDS-side documentation is here](https://sbn.psi.edu/pds/resource/itokawashape.html)).
- **[NASA 3D Resources](https://nasa3d.arc.nasa.gov/)** — 3D models of spacecraft, terrain, and other space-related subjects.
- **[The Cancer Imaging Archive (TCIA)](https://www.cancerimagingarchive.net/)** — research-grade CT/MRI **DICOM volumes** (a real-data source for the volume sort).
- **Robot models** are publicly available too: **[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie)** (high-quality MJCF of real robots), **[MyoSuite](https://github.com/MyoHub/myosuite)** (musculoskeletal models), **[LocoMuJoCo](https://github.com/robfiras/loco-mujoco)** (locomotion benchmark environments).

A curated list of licenses and direct download URLs lives in the repo's [docs/ops/SAMPLES.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/ops/SAMPLES.md), and anything fetchable with the one-liner `sample_data.download('bunny', yes=True)` is registered in code as well (explicit error if not yet downloaded — never fetching on its own; fail-closed by design).

This layer's customer number one is **evis**, the musculoskeletal humanoid. Its vision pipeline runs **stereo → depth → point cloud → segmentation → 6-DoF pose → motion planning → realization through 700 muscles**. This layer supplies the "eyes" for tasks like getting a robot to use chopsticks or to walk.

Here are the first two stages — **stereo → depth** — demonstrated with evis's own two eyes (click to play the video):

[![evis's binocular captures with Fullseye's disparity_sgm → depth_from_disparity applied every frame (click to play mp4)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_stereo_fullseye_thumb.jpg?v=2)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/evis_stereo_fullseye.mp4)

*↑ ▶ The ChopMimic scene — evis striking a bean with chopsticks — captured by evis's own binocular cameras (64mm interpupillary distance), 241 real experiment frames, with Fullseye's `disparity_sgm → speckle_filter → fill_disparity → depth_from_disparity` applied to every frame. Left = evis's left-eye view; center = the disparity Fullseye computed; right = depth. The "distance to bean" HUD reads $Z = f \cdot B / d$ from the disparity of `segment_objects` centroids in each eye; error vs. simulator ground truth over 229 frames: median 0.66%, max 1.91% (the 12 frames where the bean is occluded by chopsticks honestly display "bean not in view").*

What I care about here is **not reinventing OSS**. Standards like PCL, OpenCV, and MoveIt2 are used as **a map of fidelity and coverage, plus thin adapters** — hidden behind the **unified interface**, so the caller never has to care whether the implementation underneath is hand-written numpy or an OSS wrapper. It's the same writing feel either way.

The call described in "the HALCON coverage story" — **deciding what not to build** — surfaces here too. There's no need to wholesale-replace the areas PCL and MoveIt2 already cover (parts of point-cloud processing, parts of motion planning) with in-house implementations. The value Fullseye should add there is "making it callable with the same writing feel," not "adding one more implementation to the world." Where to draw the line between hand-written numpy and thin adapters is **a decision that touches all four pillars of the design philosophy**, and here again the honest-disclosure spirit applies — "this one is in-house, this one is an OSS wrapper," always distinguished and disclosed in the machine-readable notes (Layer 1's md=SoT).

---

## Fullseye Studio — an IDE for Looking, Trying, and Working

> **Status: Production-ready** — ships with v0.1.3. Every screenshot in this chapter is a real screen.

Having the algorithms isn't enough. You need a layer for **seeing and confirming**. That's **Fullseye Studio**. Its positioning:

> **A fusion of HDevelop (industrial vision's 2D-image IDE) and the robot world's RViz2 (3D perception visualization: point clouds, depth, 6-DoF pose axes, terrain layers).**

- On the left, an **operator/sample list**; in the center, **code editing plus parameter sliders**; on the right, a **drawing pane**. Pick a sample → the code appears → Run renders instantly, and sliders re-render instantly.
- Every one of the ~1,000 ops has a **generated help page**, and **both 2D and 3D** pull from the same help dictionary (the 3D side was unified during the work on this overview).
- Hovering over an image shows **pixel coordinates and values**, and detected regions can be **overlaid on the input image** — the HDevelop-style "inspection" conventions are in here too.
- And a **Python Editor** (a Qt-Creator-style edit-and-run environment). Previously, sample code could only be **read, or invoked as a pipeline**; now you can open a gallery's worked example **in an editable editor, rewrite it, and run it instantly with F5** (syntax highlighting, line numbers, and a run console included; execution runs in a subprocess, so the UI never freezes). Just like HDevelop's "main plus sub-scripts," you can **open and edit multiple scripts in tabs at once**, and samples open as **independent MDI windows, as many as you like, side by side**, so you can select-copy fragments while you write. It's the layer that lets the **staircase between learning and real work** — "run the sample as-is → tweak it toward your own problem" — complete entirely inside Studio (added during the work on this overview).
- **Debugger-grade execution control and a variable watch** went in too. Pause at a breakpoint, **resume from the current line (Continue)**, **restart from an arbitrary line (Run from here)**. Variables can be **right-clicked for a popup inspection of their contents**, and **watch expressions** (arbitrary expressions like `v.mean()` or `np.percentile(v, 99)`) are **automatically re-evaluated against the selected variable on every pipeline change**.
- **Multiple drawing windows can be driven from a script.** In the same manner as HDevelop, `dev_open_window (row, column, width, height)` in a program opens and places a window, `dev_set_window` switches between them, and `dev_set_window_extents` moves one. In real image-processing work, "input, intermediate, and result in separate windows side by side" is everyday practice, so this is reproducible from code (the cap against opening too many is adjustable in system settings, default 256).

Here's the actual screen (not a mockup — a straight capture of the real UI assembled by `studio.build_window()`). Result view on the left (wheel to zoom, drag to pan), Program panel at the bottom, operator browser on the right; pick ops, wire them up, turn the knobs, and the result updates live.

![Fullseye Studio main window](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_main_thumb.jpg)

*↑ The Studio main window — a blob-splitting pipeline (gaussian → otsu → opening_circle → sk_clear_border) applied to the coins sample, with the 21 detected coins overlaid as a region overlay. The status bar reads "21 obj."*

### The Tabbed Editor — Inheriting HDevelop's "Main Plus Sub-Scripts"

For readers who have used HDevelop, here's how Studio's Python Editor maps onto it.

In HDevelop, the standard style is one main program calling several sub-programs (subroutines), each edited in its own tab. Studio's **Python Editor** (`File ▸ Python Editor…`, or "Open in editor" from the gallery) follows the same idea: **multiple Python scripts open and editable in tabs at once**. **F5 (Run)** executes the current tab in a subprocess — and because it's a subprocess, heavy jobs never freeze the main UI. The repository lands on `PYTHONPATH` automatically, so `import fullseye` just works in every tab. Unsaved buffers execute as a **scratch copy**, so "rewrite it a little and see what happens" never forces a save first.

![Studio Python Editor](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_python_editor_thumb.jpg)

*↑ The Python Editor — right after running `itokawa_curvature.py` with F5 (PASS, exit 0). The console below streams curvature statistics from the real data.*

There's one more option: **MDI code windows** ("Open in window" from the gallery). These let you lay out any number of samples as **independent windows**, and `Window ▸ Tile/Cascade` arranges them. Tabs suit "reading and writing in sequence"; MDI windows suit "comparing several samples while copying fragments" — the two uses are kept deliberately distinct.

### The Variable Watch and Debugger-Grade Execution Control

One of HDevelop's strengths is executing a program line by line while **peeking into variables on the spot**. Studio has the same kind of machinery.

- **Breakpoints**: click the gutter (left of the line numbers) and execution pauses at that line.
- **Continue**: resume from the paused line to the next breakpoint or the end.
- **Run from here / Run to here**: right-click a stage to **restart execution from an arbitrary line** (or run **up to** it). When you want to iterate on just the back half of a pipeline, you're spared re-running it from the top every time.
- **Variable watch**: register **arbitrary expressions** in the Variables window — `v.mean()`, `np.percentile(v, 99)`, `(v > 0.5).sum()` — where `v` is the selected variable, `np` is numpy, `img` is the input image. These expressions **re-evaluate automatically every time the selection changes or the pipeline changes**. If an expression fails, that row just gets a warning marker — the panel as a whole never crashes.
- **Right-click ▸ Inspect in popup…**: right-click a variable for an instant type-aware inspection popup (shape, min/max/mean, percentiles, a value preview).

One honest caveat here too. Watch expressions are **evaluated synchronously on the GUI thread**, so registering a **heavy expression** that scans a huge array end to end will make the UI wait for it. For heavy aggregations, the practical tip is to lighten the expression or run it in the Python Editor instead.

### Turning It by Hand — the 3D Surface (Ctrl+3)

Studio's right panel can **open the current result as a rotatable 3D surface** (`Ctrl+3` under `DISPLAY & PERCEPTION`; internally a best-effort implementation on Qt's `Q3DSurface`). Usage is simple. When the displayed result carries **one height value per pixel** — a depth map, a terrain height map, a curvature-colored height field — press `Ctrl+3` and it opens in a separate window as **solid terrain**.

From there, **dragging the mouse swings the viewpoint around** and **the wheel zooms in and out** — instead of squinting at a colormap thinking "that's probably a dent," you can **actually grab the thing, change the angle, and confirm the relief by watching how the light falls on it**. The places where stereo-depth error creeps in, the steps in a terrain height map, the ridges and valleys of a curvature map — these can **look flat in a single static color image**. Rotate the same data and re-light it, and the shadows make them jump out. The single step from "staring at results as a still image" to "picking results up and checking them by hand" is plain, but it earns its keep in real work. (In environments where a real offscreen GPU context can't be acquired, the feature disables itself safely — best-effort; if it's not there, it's quietly not there.) Height is colored with a terrain-style gradient (low = deep blue → green → sand → summit = white), so high and low read off the colors as well.

![Studio 3D surface view (Itokawa)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_surface_thumb.jpg)

*↑ The Ctrl+3 3D surface view — the relief of a depth render of asteroid Itokawa's real shape model (JAXA Hayabusa / Gaskell model). In the app you rotate this very scene by mouse drag and zoom with the wheel (the image is a `renderToImage` still of the same GL scene).*

### Meshes and Point Clouds You Can Spin — the Interactive 3D Viewer (Ctrl+4)

The 3D surface (Ctrl+3) was height-fields only. In the final stretch of this compilation's work I added an **interactive 3D viewer that lets you spin meshes and point clouds directly with the mouse** (`Ctrl+4`, or the View menu): left-drag orbits, wheel zooms, Shift+drag pans, R resets, W toggles wireframe.

[![Studio's interactive 3D viewer — the 49,152-face Itokawa mesh](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_viewer_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_viewer.png)

*↑ The interactive 3D viewer showing the real Itokawa mesh (24,578 vertices, 49,152 faces). You turn it with the mouse and read the relief from how the Lambert lighting falls.*

Honestly stated, the implementation is a **software rasterizer — no GPU**. The choice was made by measurement, not resignation: a GL implementation's test path dies completely in CI's offscreen environment and is fragile over remote desktop, while the software path means **tests and the real machine share one code path**. Measured: 66 ms at 200k points, 349 ms at 1M (480px) — 1M points is not interactive at full resolution, so during drag/zoom the viewer shows a uniform 250k-point decimated preview (honestly labeled in the HUD) and re-renders in full the moment you release. Mesh drawing is a Lambert splat of vertices + face centroids, not filled-triangle rendering (high-quality stills remain the job of the existing `render3d.render_mesh`).

(A depth-sort inversion bug in the viewer's first version was proven and fixed during pre-publication adversarial review, and is pinned by an occlusion regression test.)

### Crossing Between Regions and Features — Feature Inspection (Ctrl+F5)

One of HDevelop's staple tools inspects the features of multiple labeled regions in a table. Studio now has the same (`Ctrl+F5`, Tools menu).

[![Feature Inspection — bidirectional region-and-feature-table navigation](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_feature_inspection_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_feature_inspection.png)

*↑ 2D Feature Inspection — pick features from the checklist (area, centroid, circularity, eccentricity, gray statistics and more — reusing the existing regionprops / gray_features implementations) and get a sortable table of rows = regions, columns = features. **Select a row and the matching region lights up amber in the image; click the image and the table jumps to that region's row.** CSV copy included.*

[![3D Feature Inspection — per-cluster features + viewer highlight](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_feature_inspection_3d_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_feature_inspection_3d.png)

*↑ The same dialog's 3D tab — cluster a point cloud with `euclidean_clusters` and tabulate per-cluster point counts, centroid, extents, and OBB dimensions (strictly what the existing ops3d ops provide). **Selecting a row highlights that cluster in the embedded interactive 3D viewer.***

The same idiom works from scripts too. A **disp directive family** matching HDevelop's `disp_image` / `disp_object_model_3d` (`disp_image (n)` / `disp_region (n)` / `disp_points3d ('file')` / `disp_mesh3d ('file')`) now rides the dev-window system, so a program can lay out "input, intermediate, result in separate windows" in 3D as well as 2D (Python API: `studio.disp_points3d(P)` etc. Being side-effecting display operators, they are deliberately kept out of the pure-transform op registry — and out of the HALCON coverage count).

### System Settings — the Settings Tree

`Tools ▸ System settings…` (`Ctrl+,`) is a category-tree settings screen. **Execution** (worker thread count, operator timeout), **Windows** (the cap on graphics windows), **Display** (default colormap, region drawing mode), **Editor** (font size, the Python Editor's interpreter) — the settings corresponding to HDevelop's `set_system`, gathered on one screen. The **Command palette** on `Ctrl+P` fuzzy-searches any action or any operator by name and runs it immediately, so a full session's worth of operations can stay on the keyboard without walking menus.

### The Gallery and Help — 105 Worked Examples and a 265-Op Reference

On the 3D side, 105 worked examples (real Itokawa point cloud, skeleton volume, synthetic data) can be picked from the gallery and Run on the spot, and each of the 265 3D ops has a generated help page (signature, usage, links to verified samples, and the type-compatible next ops).

![Studio 3D Examples gallery](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_examples_thumb.jpg)

*↑ The 3D Examples gallery — right after selecting and running itokawa_curvature (Output shows a PASS with ground-truth verification).*

![Studio 3D Operators reference](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/studio_3d_ops_thumb.jpg)

*↑ The 3D Operators reference — the help page for `icp_point2plane`.*

### One Workflow, Followed From an Inspection-Line Practitioner's Seat

Here's how the features above chain together in real work — written for someone who has built inspection programs in HDevelop.

Search the left **OPERATORS** panel for `shape_locate` or `m1_measure_pos` and double-click to insert into the pipeline. Move the knobs a, b in the central **SELECTED STAGE / KNOBS** while checking the result in the right **IMAGE** panel each time. Once the thresholds are settled, `Ctrl+E` (Export) writes out both the `--ops` string and a Python function, ready to embed into your own inspection program. If dialing in a parameter takes a while, register `region.sum()` or `np.percentile(v, 95)` in the **variable watch** and watch the statistics move in real time as you slide the threshold. If some stage misbehaves, right-click it and **Run from here** to redo just that part — anyone who has built inspection programs in HDevelop's Program window with breakpoints will find this whole sequence immediately familiar.

**Design in Studio, run in code** — the same division of labor as exporting from HDevelop to HDevEngine. Trial and error in the GUI; integration into the production line via the exported Python function or JSON. Because both share the same ops and the same parameters, **"it runs on the floor exactly as confirmed in Studio"** is guaranteed by construction.

Layer the RAG from the "Letting AI Do Image Processing" section over this flow, and it gets one step shorter still. Ask Claude Code to "build a pipeline that detects scratches in this image, and make it inspectable in Studio," and the AI drafts pipeline candidates from `docs/ops` and saves them in Studio's JSON format — from there, a human fine-tunes in Studio. This division — **the AI drafts, the human finishes in Studio** — also stands only because both share the same ops and the same parameter space. The "unified interface" from the design-philosophy section is what lets Studio, the AI, and the production line speak the same language.

---

<!-- EXHIBITS:BEGIN (generated by tools/build_exhibits.py — do not edit by hand) -->

## A Science Museum on Paper — 41 Exhibits of Playing With Ops

Time to relax the shoulders a little. This corner is meant to be wandered **the way you'd wander the exhibit halls of a science museum**. Everything below is **real output** from Fullseye's registered ops — not a single mockup. The provenance of the materials splits two ways:

- **Real data**: public data from the Smithsonian (CC0), the Metropolitan Museum of Art (CC0), and NASA (public domain) only. Source links are in the captions. (One cell-microscopy dataset was initially included under a CC-BY label, but checking its official page revealed it is actually CC BY-NC-SA — incompatible with this repository's licensing — so the exhibit was withdrawn before publication. That kind of check-and-retract is part of honest disclosure too.)
- **AI-generated simulated data**: for fields where license-clean real data is hard to find (medical imaging, for example), the materials were produced with an image-generation AI (Google gemini-2.5-flash-image), and **"AI-generated" is stated both inside the image and in the caption**. These are not real specimens, patients, or scans.

The star throughout is **the processing**. Each caption names the ops used, so you can reverse-look-up "which op makes this picture?" Full resolution and additional exhibits are in the [results gallery (docs/GALLERY.md)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/GALLERY.md).

### The Science-Museum Wing — Image-Processing Principles as "Beautiful Pictures"

[![Rainbow ripples of the distance transform](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_distance_ripple.png)

*↑ **Rainbow ripples of the distance transform** — split a coin photo into black and white, then paint "how many pixels from the edge?" in rainbow colors, and ripple-like contour lines emerge. Ops used: `otsu`, `fill_up`, `distance_transform`.*

[![The Fourier world](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_fourier_stars.png)

*↑ **The Fourier world** — view an image in frequency space, and "what fineness of pattern, in what direction" becomes points of light. A regular weave glows like a constellation (the weave panel only is synthetic). Op used: `fft_image`.*

[![Watershed — coloring-book segmentation of coins](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_watershed_foam.png)

*↑ **Watershed's coloring-book segmentation** — mimic water flowing downhill and pooling, and each coin gets its own color. Ops used: `otsu`, `distance_transform`, `watersheds`, `colorize_labels`.*

[![The edge compass](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_edge_compass.png)

*↑ **The edge compass** — paint contour direction with the colors of a hue wheel, and lines pointing the same way glow the same color. Ops used: `sobel_amp`, `sobel_dir`.*

[![Six universes born from simple rules](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_alife_worlds.png)

*↑ **Six universes born from simple rules** — from nothing more than "look at your neighbors and decide your own color" come fractals, chaos, sandpile mandalas, dendrites, and coral patterns (simulation imagery). Ops used: `alife_wolfram1d`, `alife_sandpile`, `alife_dla`, `alife_lenia`, `alife_cyclic_ca`.*

[![An X-ray photograph of a Triceratops](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_xray.png)

*↑ **An X-ray photograph of a Triceratops** — pack the Smithsonian's real skeleton scan (CC0) into voxels and take a maximum-intensity projection (MIP), and it comes out looking just like an X-ray. Ribs and horns both show. Ops used: `voxelize`, `vol_gaussian`, `vol_mip`.*

[![A dragon that pops out with red-blue glasses](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dragon_anaglyph.png)

*↑ **A dragon that pops out with red-blue glasses** — the real Stanford dragon scan rendered from 2 viewpoints and overlaid in red-cyan as an anaglyph. Put on red-blue glasses and it floats. Ops used: `read_mesh`, `look_at`, `render_mesh`.*

[![The Triceratops mountain range](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_terrain.png)

*↑ **The Triceratops mountain range** — turn the skeleton into a 600,000-point cloud and build an elevation map from directly above, and the spine becomes a mountain range, the ribs its ridgelines. The same ops a robot uses to read terrain. Ops used: `sample_surface`, `elevation_map`, `colorize_height`.*

![Shapes growing and shrinking (morphology)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_morph_pulse.gif)

*↑ **Shapes growing and shrinking** — coins puff up and merge under dilation, then slim down under erosion. Fundamental ops used in factory image inspection too. Ops used: `dilation_circle`, `erosion_circle`.*

[![Space gone wobbly — three deformation algorithms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_wobble_warp.png)

*↑ **Space gone wobbly** — imagine an invisible rubber sheet under the image, then pinch and pull it in three different styles: TPS / FFD / MLS. Ops used: `deform_tps`, `deform_ffd`, `deform_mls`.*

[![Extracting a skeleton from a dinosaur silhouette](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_dino_skeleton.png)

*↑ **Extracting a skeleton from a dinosaur silhouette** — the centerline (skeleton) of a Triceratops skeleton's shadow, extracted at 1-pixel width. Legs, horns, and tail remain like wirework. Ops used: `sk_skeleton`, `distance_transform`, and others.*

### The Museum Wing — 30 Exhibits Across the Academic Disciplines

Now the discipline-by-discipline exhibit rooms. Medicine, archaeology, biology, space, paleontology, geology, meteorology, oceanography, botany — this corner exists to show that **the same op system cuts straight into images from any field**. Caption conventions from here on are the same as above (real data gets a source link; AI-generated is labeled as such).

#### Paleontology

[![Spiral extraction from an ammonite fossil](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_real.png)

*↑ The spiral of an ammonite fossil ([Smithsonian Open Access, CC0](http://n2t.net/ark:/65665/34afa6692-b3f9-408d-90dc-cc53097171b6)) extracted with `canny`. Ops used: `rgb1_to_gray`, `canny`, `overlay_mask`.*

[![Skin-texture analysis of a T. rex life reconstruction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trex.png)

*↑ Skin texture of a Tyrannosaurus life reconstruction analyzed with `std_filter` / `texture_laws`. The material is **AI-generated (gemini-2.5-flash-image) simulated data** (not a real specimen).*

[![Multi-Otsu classification of a Triceratops life reconstruction](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_triceratops.png)

*↑ A Triceratops life reconstruction region-classified by multi-Otsu. The material is **AI-generated simulated data**. Ops used: `xsk2_multiotsu`, `colorize_labels`.*

[![Feather-flow analysis of a feathered dinosaur](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_feathered.png)

*↑ The flow of a feathered dinosaur's plumage analyzed with Gabor filters. The material is **AI-generated simulated data**. Ops used: `sk_gabor`, `std_filter`.*

[![Log-spiral FFT of an ammonite cross-section](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_ammonite_section.png)

*↑ The logarithmic spiral of an ammonite cross-section observed through its FFT spectrum. The material is **AI-generated simulated data**. Ops used: `cv_clahe`, `cx_fft`, `cx_magnitude`.*

[![Relief-enhancing a trilobite's segments](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_paleo_trilobite.png)

*↑ A trilobite's body segments relief-enhanced with `gray_tophat`. The material is **AI-generated simulated data**.*

#### Space

[![Filament extraction in the Carina Nebula](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_carina.png)

*↑ The filament structure of the Carina Nebula ([NASA/STScI Webb, public domain](https://images.nasa.gov/details/carina_nebula)) extracted with `sk_frangi` — an op originally for enhancing blood vessels. A case of a medical op cutting into astronomy.*

[![Texture analysis of the Nili Patera dunes on Mars](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_mars.png)

*↑ The texture of Martian dunes ([NASA/JPL-Caltech/Univ. of Arizona, public domain](https://images.nasa.gov/details/PIA18244)) analyzed with `std_filter` / `texture_laws`.*

[![FFT spectrum of the Sunflower Galaxy](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_space_galaxy.png)

*↑ The frequency structure of a spiral galaxy ([NASA GSFC, public domain](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o)) visualized with `cx_fft`.*

#### Medicine (Everything in This Block Is AI-Generated Simulated Data)

[![Enhancement and edge extraction of a chest-X-ray-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_chest_xray.png)

*↑ A chest-X-ray-**style** image enhanced and edge-extracted with `cv_clahe` + `sobel_amp`. **AI-generated simulated data** (not a real patient or scan).*

[![Multi-Otsu classification of an H&E-histology-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_histology.png)

*↑ An H&E-tissue-section-**style** image tissue-classified by multi-Otsu. **AI-generated simulated data**.*

[![Contrast enhancement of a brain-MRI-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_brain_mri.png)

*↑ A brain-MRI-**style** image with tissue contrast enhanced by `cv_clahe` + `unsharp`. **AI-generated simulated data**.*

[![Blood-cell counting on a blood-smear-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_blood_smear.png)

*↑ Blood cells in a blood-smear-**style** image segmented and counted (131 detected). **AI-generated simulated data**. Ops used: `segment_objects(otsu)`, `colorize_labels`.*

[![Contour extraction of an anatomical-illustration-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_med_anatomy_heart.png)

*↑ The contours of an anatomical-illustration-**style** image extracted with `canny`. **AI-generated simulated data**.*

#### Biology

[![Tracing a neuron's dendrites](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_neuron.png)

*↑ The dendrites in a neuron fluorescence image traced with `sk_frangi`. **AI-generated simulated data**.*

[![Segmenting and counting diatoms](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_diatoms.png)

*↑ A diatom micrograph segmented and counted (123 detected). **AI-generated simulated data**.*

[![Shadow-region enhancement of a deep-sea anglerfish](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_deepsea.png)

*↑ The dark regions of a deep-sea creature enhanced with `cv_clahe`. **AI-generated simulated data**.*

[![Periodic-structure analysis of butterfly wing scales](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bio_butterfly.png)

*↑ The periodic structure of a butterfly's wing scales analyzed with `sk_gabor`. **AI-generated simulated data**.*

#### Archaeology

[![Elliptic Fourier descriptors of a pottery silhouette](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_amphora.png)

*↑ The silhouette of an amphora ([The Metropolitan Museum of Art Open Access, CC0](https://www.metmuseum.org/art/collection/search/254896)) shape-reconstructed with elliptic Fourier descriptors (EFD). Raising the harmonics 2 → 8 → 32 makes the curve cling ever closer to the contour — a method actually used in archaeological pottery-shape classification. Ops used: `otsu`, `fourierdesc.elliptic_fourier`, `fourierdesc.reconstruct`.*

[![Relief enhancement of a stone stele](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_relief.png)

*↑ The carving of an Assyrian stone relief ([The Metropolitan Museum of Art, CC0](https://www.metmuseum.org/art/collection/search/322611)) relief-enhanced with `gray_tophat`.*

[![Pigment enhancement of a cave painting (the DStretch approach)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cave_painting.png)

*↑ The fading pigments of a cave painting enhanced with decorrelation stretch (the same family of technique as DStretch, the rock-art survey standard). **AI-generated simulated data**. Op used: `principal_comp`.*

[![Enhancing the impressions on a cuneiform tablet](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_arch_cuneiform.png)

*↑ The character impressions of a cuneiform clay tablet enhanced with `gray_tophat`. **AI-generated simulated data**.*

#### Geology, Meteorology, Oceanography, Botany

[![Decorrelation stretch of satellite-image lithology](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_earth.png)

*↑ The lithology in a satellite image ([NASA JSC, public domain](https://images.nasa.gov/details/SL2-04-018)) enhanced with decorrelation stretch (a remote-sensing standard).*

[![Extracting facet ridgelines of a mineral crystal](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_mineral.png)

*↑ The facet ridgelines of an amethyst crystal extracted with `canny`. **AI-generated simulated data**.*

[![Mineral-grain classification of a rock thin section](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_geo_thin_section.png)

*↑ A rock thin section (polarized-microscope style) classified into mineral grains by multi-Otsu. **AI-generated simulated data**.*

[![Gradient-direction wheel of a hurricane's vortex structure](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_hurricane.png)

*↑ The vortex structure of a hurricane ([NASA JSC, public domain](https://images.nasa.gov/details/iss056e162187)) visualized with a gradient-direction wheel (`sobel_dir` + `colorize_flow`).*

[![Structure enhancement of a supercell thunderstorm](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_met_supercell.png)

*↑ A supercell thunderstorm structure-enhanced with `cv_clahe` + `unsharp`. **AI-generated simulated data**.*

[![Coral-reef coverage classification](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_ocean_coral.png)

*↑ A coral reef coverage-classified by multi-Otsu (marine-survey style). **AI-generated simulated data**.*

[![Extracting fern leaf veins](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern_thumb.jpg?v=2)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_fern.png)

*↑ The leaf veins of a fern extracted with `sk_frangi`. **AI-generated simulated data**.*

[![Segmenting and counting a pollen-SEM-style image](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/academic_bot_pollen.png)

*↑ A pollen-SEM-**style** image segmented and counted (41 detected). **AI-generated simulated data**.*

Across these 41 exhibits, **every piece of real data carries its source and license** (the detailed attribution table is in [ACADEMIC_ATTRIBUTION.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/ACADEMIC_ATTRIBUTION.md)), and **every AI-generated piece is labeled as such**. One bonus — this exercise of "running diverse real data through the ops" turned out to be a **bug detector** in its own right. Five op defects that had never surfaced on synthetic data showed up on real data, and **all five were fixed before publication** (the discovery stories and regression tests are in [docs/KNOWN_ISSUES.md](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/KNOWN_ISSUES.md)). Behind the pretty exhibits, it doubled as a test — two birds with one stone.

---

<!-- EXHIBITS:END -->

## Design Philosophy (Four Pillars)

The backbone that keeps Fullseye from becoming "just a pile of functions."

1. **Honest by construction**
   Hold-out data is never used for selection. Coverage and benchmarks are **measured, never merely claimed**. Limitations are **disclosed, not hidden**. Results that look too good get their breakdowns doubted.
2. **A unified interface**
   Whether the implementation underneath is hand-written or an OSS wrapper, **the caller uses the same naming and signature conventions**. And it must be **an API that's natural for a human to write** — something like `fs.stereo.SGM(num_disparities=128).compute(l, r)`, readable and completion-friendly (with any mechanical string dispatch hidden behind it). This is a point I especially cared about.
3. **Every heavy dependency is optional**
   **The core runs on nothing but numpy + scipy.** OpenCV, scikit-image, torch, and GPU support are opt-in; without them, only the affected ops quietly disable themselves (graceful degradation).
4. **Reimplemented from public knowledge**
   Everything is implemented from **public knowledge — papers, OSS, and the like**. Nothing is derived from any specific commercial product (that line is drawn clearly).

I wrote "four pillars," but in truth they aren't four independent columns — it's closer to **one spine with branches reaching in four directions**. Let me dig a little deeper.

**"Honest by construction"** is the thickest trunk, showing its face in nearly every section of this article. Layer 2's hold-out discipline, the per-chapter HALCON coverage disclosure, the "Night Before Release" CI chapter, the reproduction notes for Bugs 1–6 — they all share one root: the wariness that "if you show only the good numbers, eventually you fool yourself too." I think of this less as a technical choice than as **a lifestyle habit for keeping development going long-term**. Producing one good number once is easy; repeating the same discipline a hundred times doesn't happen unless the structure forces it.

The reason I insisted on **"a unified interface"** is that Fullseye is ultimately aimed at being used as **an AI's toolbox**. A library where the calling convention changes depending on whether the internals are hand-written numpy or an OpenCV wrapper means **more to memorize — for humans and for AIs alike**. With one uniform calling convention, an AI can go from "I want to do this processing" straight to the correct call without getting lost. The insistence on a writing feel like `fs.stereo.SGM(num_disparities=128).compute(l, r)` comes from wanting **Python's completion machinery to function as documentation in its own right**. If the IDE tells you the types, that by itself is a minimal onboarding.

**"Every heavy dependency is optional"** looks unglamorous, but it's actually the pillar that sits closest to honest disclosure. Rather than the honest-but-blunt "it doesn't work without torch," it opts for a **graduated honesty**: "without torch it runs on the numpy path; with torch, a faster path opens up." The flip side: many of the CI bugs recounted in "The Night Before Release" grew precisely out of **lapses in operating this pillar** (missing guards on optional imports). Raising a pillar is easy; **verifying you're actually honoring the pillar you raised** is a separate job — the CI episode drove that home.

[![The dependency map: numpy+scipy core and the optional extras](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_optional_extras_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_optional_extras.png)

*↑ This pillar as a picture — the only required dependencies are numpy + scipy; OpenCV / scikit-image / torch / GUI / point-cloud I/O / industrial I/O are all opt-in extras. Generated mechanically from the actual `pyproject.toml` definitions (if an extra is added and the figure goes stale, the generating script fails).*

**"Reimplemented from public knowledge"** is the plainest pillar and the least negotiable line. Lifting code from commercial industrial software might have let me "catch up" faster on the surface. I don't do it because it's an **ethical line**, and at the same time **the road on which my own understanding deepens over the long run**. By never skipping the step of reading the paper and rewriting the algorithm with my own hands, I keep myself in a state where I can **genuinely explain** why a given op returns a given result.

---

## Letting AI Do Image Processing — Using Fullseye as a RAG

> **Status: PoC** — the RAG setup itself ships and is verified to work. **Letting an AI pick ops and run them autonomously** is still experimental.

This is Fullseye's hidden advantage. As mentioned earlier, each of the ~1,000 ops carries a **Markdown note** (usage, type contract, related ops, references), and the algorithms themselves are **classical and explainable**. Put those two together, and the library functions as-is as a **RAG (Retrieval-Augmented Generation) knowledge base for AI coding assistants like Claude Code**.

Broken down in three passes:

1. **One-liner**: ask the AI to "detect X in this image," and it **retrieves** Fullseye's op documentation, **writes and runs** a pipeline combining the appropriate ops.
2. **A bit more**: because the AI can read each op's **type (sort)**, it can pick ops in an order where the types connect — "image → region → feature" — and follow related-op links to offer alternatives. Unlike deep learning's "one black-box function," **each stage is explainable and intermediate results can be inspected**, so when the AI goes wrong, **you can see exactly where it went off track**.
3. **Why it works**: because the documentation is a machine-readable single source of truth (md=SoT), and the ops are deterministic, typed, and contract-tested. It's **a parts bin that's easy for an AI to retrieve from, compose with, and verify against.** A human trying things in Studio and an AI composing via RAG stand on **the same ops and the same documentation**.

### What SKILL.md Pins Down

"The AI retrieves Fullseye's op docs" doesn't happen on slogans alone. Here's how it's actually pinned down.

Run `fullseye-rag` in a `pip install fullseye` environment, and the bundled skill `skills/fullseye-ops` is copied to `~/.claude/skills/fullseye-ops`. At that moment, **the single line `FULLSEYE_REPO =` in the skill's `SKILL.md` is automatically rewritten to the corpus location for that environment**. What this means: the AI (Claude Code), **whatever project folder it's working in**, knows without hesitation "the Fullseye op corpus is here." If the path weren't pinned, the AI would hunt for the repository every time — and retrieve nothing when it couldn't find it. **One pinned path line** is what separates a RAG that works in practice from one that doesn't.

One more fail-closed touch: if the corpus itself (`docs/ops` or `OP_CATALOG.md`) can't be found, the installation is **refused outright**. If a skill already exists, it's **set aside with a timestamp** before being overwritten, so a reinstall (i.e. an update) never silently erases hand edits. Never create the half-state of "installed, but empty inside" — if it goes in, it goes in working; if it can't work, it doesn't go in. That's the discipline.

### Checkout Mode and Wheel Mode — Two Ways In

`fullseye-rag` (in reality `fullseye/rag_setup.py`) **looks at how the package was installed and adapts the corpus contents automatically**.

- **Checkout mode**: in a git-cloned or `pip install -e .` environment, `docs/ops/INDEX.md` really exists next to the package. In that case the **full corpus of `docs/ops` (about 1,000 per-op notes)** is pinned as-is.
- **Wheel mode**: in an environment that only ran `pip install fullseye` from PyPI, `docs/ops` isn't bundled (the corpus is repository content, not wheel content). In that case the package-bundled **`OP_CATALOG.md` (the one-page all-ops catalog for AI)** is pinned instead, and the SKILL.md gets an explicit note written into it: "if you want the full per-op notes, clone the repository."

In either mode, if the corpus body (`docs/ops/INDEX.md` or `OP_CATALOG.md`) can't be found, installation is **refused on the spot** — never install an empty skill and let someone puzzle over "it doesn't work" later. Fail-closed, all the way through.

### What Actually Comes Back When You Ask

Here's the concrete feel, with real example prompts. Run `pip install fullseye` once and `fullseye-rag` once, and from then on, in whatever directory you open Claude Code, exchanges like this work:

> **Human**: "I want to detect scratch-like defects in this PCB image."
>
> **AI (via the `fullseye-ops` skill)**: searches `docs/ops` and picks ops whose `in:`/`out:` types chain as "image → image (enhance) → region (binarize) → contour (measure)." For example: "`bilateral` or `gaussian` for noise suppression, `sobel_amp` or `dog` (Difference of Gaussians) for edge enhancement, `otsu` or adaptive thresholding for binarization, `edges_sub_pix` → `select_contours` for contour extraction" — presenting the candidates **grounded in each op's type contract and HALCON alias**, then writing and running the `fullseye.run_pipeline(img, [...])` code on the spot.

One more, on the industrial side:

> **Human**: "This part isn't placed in a fixed orientation — before grasping it, I first need its position and orientation."
>
> **AI (via the `fullseye-ops` skill)**: pulls the `matching` category of `docs/ops` and offers `shape_locate` (the counterpart of HALCON's `find_shape_model`, contour-based shape matching) or `ncc_locate` (the counterpart of HALCON's `find_ncc_model`, template matching) as candidates. After confirming the types chain as `image → match`, it writes and runs code that returns position and angle.

In both examples, what the AI grounds itself in is **the same corpus (`docs/ops`) and the same type contracts**. "Defect detection on an inspection line" and "alignment for a robot" are, from the AI's seat, **the same kind of question answered by the same RAG** — the op system from Layer 1 serving both Physical AI and industrial vision owes a lot to this RAG machinery.

What the AI is doing behind these responses is not vector search, not embedding-similarity computation. **It greps `docs/ops` and reads each note's `in:`/`out:` lines to chain the types — that's all** (the "Retrieval recipes" in SKILL.md are the literal procedure). Which is exactly why no special vector DB or embedding service is needed: **any environment that can grep functions as the RAG**. In a checkout environment it draws evidence from ~1,000 per-op notes; in a wheel environment, from the `OP_CATALOG.md` listing. Nor do you have to take the proposed code on faith. **Every op ships with a ground-truth-verified worked example**, so a self-verification loop — the AI itself runs `py -3.11 examples/<id>.py` and confirms "PASS" before replying — can be built right in.

[![The RAG corpus itself: a per-op note and the three steps](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_rag_corpus_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_rag_corpus.png)

*↑ The RAG corpus itself — `docs/ops/2d/smoothing/bilateral.md` with its frontmatter (type contract `in:`/`out:`, HALCON alias, author/license/version) and the "next ops whose types connect" links. Right: the three steps the AI performs; the PASS line in step 3 is the actual output of running the worked example while generating this figure.*

And what if the AI mistakenly picks an op whose type doesn't connect? The answer is as simple as the "type contract" section in Layer 1 said: `run_pipeline` **fails explicitly at run time**. For the AI, that's not an unfriendly error aimed at humans — it is itself **machine-readable feedback: "the types don't connect here."** The AI reads the error message and re-selects an op whose type connects — a correction loop that can run **without a human stepping in**. Unlike a deep-learning function that "returns a vaguely wrong answer," a type contract **refuses to swallow mistakes silently and surfaces them on the spot**, which makes "where did it get lost?" easy to trace — for the AI and for the human alike.

### Fail-Closed Design — No Silent Giving-Up When the Corpus Is Missing

The RAG machinery, too, is threaded through with the fail-closed philosophy that recurs across this article. Installation is refused in environments where the corpus body can't be found. The update script (`tools/update_fullseye.py`) **refuses to run when there are uncommitted changes**, advances only via `--ff-only` (fast-forward), updates the RAG skill **only after taking a backup**, and never touches Studio settings. The accident where "an update meant to strengthen the AI's foundation destroys the human's working environment" is made structurally impossible.

So Fullseye is a "library for humans" and, at the same time, **"a foundation for letting an AI do image processing freely."** Assembling explainable classical vision as skills turns out to translate directly into affinity with AI.

And **the recommended mode of operation is this RAG style**. Combine it with Studio, and the results of a pipeline assembled by an AI agent (Claude Code, say) can be **put in front of a human as image windows and 3D views** — not closed off inside code and conversation; the human can inspect "what the AI is seeing" on the same screen. The position I'm aiming for: **an integrated environment for Physical AI (robot perception)**.

Concretely, the picture looks like this. Ask Claude Code, with Studio open alongside: "count the parts in this bin, and give me poses I can grasp them at" → the AI pulls the op notes, writes and runs a segmentation → 3D-pose-estimation pipeline → the results land in Studio's image window and 3D view → the human looks at the screen and, if something's off, asks for a redo in plain language. **Image processing that runs on conversation and a screen** — that's the operation this is built for (and every part of it was introduced in this article: ~1,000 ops × type contracts × machine-readable notes × Studio's rendering layer).

Incidentally, this development itself proceeds the same way — the design calls and direction stay with me, with Claude Code as the implementation partner. If you'd like to try it, starting from [the author's referral link](https://claude.ai/referral/0sqPw8E_lw) chips in a little toward keeping this development going (honest disclosure: it's a referral link).

One more thing I keep in mind is **academic use**. Every op has a machine-readable note with references (md=SoT), versions are pinned to code by fingerprint, and evaluation is honest with held-out data — in other words, it's built from the start to be **citable and reproducible**. The repo carries a `CITATION.cff`, and the references cite only real classical works (no fabricated DOIs). Used as a research tool, and cited — if that happens, I'll be glad. That's the design.

Academic use and RAG operation are, in fact, a good match. When trying a new preprocessing pipeline in research, comparisons against existing methods eat your time — with Fullseye, ask the AI to "assemble a preprocessing pipeline close to this paper's method," and it proposes candidates from **ops whose sources are explicitly cited**. The code that comes out is a composition of parts verified by worked examples, so **the anxiety of "is this baseline even implemented correctly?" no longer has to be re-checked from zero**. From the standpoint of research reproducibility, this is another place the md=SoT structure pays off directly.

---

## Building "Honesty" Into the System — Bugs It Actually Caught

Throughout this project I've placed what I call **honest gates** — checkpoints where expected behavior must be verified numerically before it's accepted. And whether they actually work should be judged by **the record of bugs they've caught**.

**In the course of preparing this overview article alone, the quality checks caught six confirmed bugs.** I'm publishing them without hiding anything. The first two are lessons in how tests get slipped past; the latter four are lessons in a discovery route — **have an AI do adversarial review, then manually verify each finding against primary evidence**.

### Bug 1: The Hessian in 3D Topographic Classification Was Asymmetric

An op that classifies terrain relief into "peak, valley, ridge, saddle" was pulling the **cross term of the Hessian matrix** from the **wrong axis** of `np.gradient`. `np.gradient` returns `[∂/∂y, ∂/∂x]` in that order, but where the code meant to compute the cross term ∂²/∂x∂y, it was picking up ∂²/∂y² (a duplicate of a different term).

- **Impact**: on structure diagonal to the axes, eigenvalues would halve or flip sign, causing misclassification.
- **How to confirm it (reproducible)**: a correct classification should be **the same under transpose** (an image and its transpose don't swap "peak" and "valley"). Measured: the old code misclassified **46 of 576 pixels** on a 24×24 diagonal structure; the fixed version is **perfectly transpose-symmetric**.
- **Fix**: take the cross term from the correct axis, and **pin transpose symmetry as a regression test**.

The choice of "how to confirm it" is itself a good expression of the honest-gate mindset, I think. Directly re-deriving whether the Hessian cross term is computed correctly is hard work if you're just eyeballing formulas. Far better to **find one symmetry that must hold if the code is correct, and check mechanically that it isn't broken** — a much more reproducible test. That mixing up the axes breaks transpose symmetry is a check **derivable deductively from this op's mathematics** — a different animal from a test that concludes "it ran, so it's correct."

### Bug 2: Studio's Op-Help Dropdown Was Broken for Every Op

While unifying op-help lookup across 2D and 3D, a `(dimension, name)` tuple was being **unpacked directly into `display_fn(name, dimension)`** — arguments reversed. Both being strings, **no error was ever raised** — instead, every op you selected showed an empty card: a **user-visible defect**.

- **Why the tests missed it**: the existing tests called the display function **directly, with the correct argument order**, and never went through the actual dropdown interaction (via the signal).
- **Fix**: corrected the argument order and added a **regression test that reproduces the actual dropdown interaction**. And since "the same failure recurs in similar places," I **swept every dispatch site for the same class of argument-order mistake** (confirmed there were no others).

This one leaves a different kind of lesson than Bug 1 (the mixed-up axis in a formula). Bug 1 was wrong **computation**; Bug 2's computation was fine — the **GUI wiring** (which value gets passed in which position) was wrong. And since `(dimension, name)` and `(name, dimension)` are both just pairs of strings, Python raises no type error at all. Breakage of the form **"correct as a type, swapped as a meaning"** lies outside what Layer 1's type contracts (the `image`/`region`/`feature` sorts) can detect. Unit tests that call functions directly aren't enough — you have to go as far as **exercising the real GUI path (signal → slot)** to catch this class of wiring mistake. That's the lesson.

### Bug 3: PCA Pose Estimation Silently Returned a "Do-Nothing Rotation" About Half the Time

An op that aligns a point cloud's principal axes to estimate its pose (rotation) wasn't accounting for the **handedness (right- or left-handed) of the frame** returned by eigendecomposition (`eigh`). Mathematically, the construction was such that the determinant of the sign-candidate matrix came out **identically +1** — so whenever a left-handed frame was drawn, all four candidates were **rejected**, and the code **fell back to the identity rotation (i.e. doing nothing) with no error and no warning**.

- **Measured**: 200 trials with random point clouds and rotations → **92 (46%) returned the identity rotation**. After the fix: **200/200 recover to machine precision (order 1e-15)**.
- **Why the tests missed it**: the existing test's random seed happened to land on the "lucky 54%" side. **Passing on one seed does not mean it isn't broken for half of all inputs.**
- **Fix**: canonicalize the frame to right-handed immediately after decomposition. The regression test now **sweeps 40 random trials**, guaranteed to step on both handednesses.

### Bug 4: Curvature's "Absolute Value" Was Off by 32× (Only the Ratio Was Right)

An op computing surface curvedness was mixing a **gradient filter with a gain of 32** (a deliberate convention — other consumers explicitly divide by 32 to compensate) with an **already-normalized Hessian**. The surface-shape classification (shape index), being a **ratio**, came out correct — but **the absolute value alone was off by 1/32**: a sphere of radius R should have curvature 1/R, and it was coming out 1/(32R).

- **How it was found**: check the **absolute value** on a synthetic sphere of known radius — measured 0.0022 vs. true 0.0714, **precisely a 32.2× gap** (matching the gain's origin, 2×4×4=32).
- **Lesson**: the "ratio tests" had been passing. Some bugs are **only caught once you verify units and absolute values against ground truth**. After the fix, c·R = 1.004 (measured on the spherical shell), and the regression test now pins the **absolute value**.

[![Post-fix verification of bug ④: sphere curvature lands on 1/R (measured)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_bug4_curvature_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_bug4_curvature.png)

*↑ Post-fix verification, re-measured for this figure: running `curvedness` on synthetic spheres of radius R (2,000 points) puts the measured medians on the theoretical 1/R line (median × R = 1.009). The dashed line marks the pre-fix systematic error 1/(32R) — ratios were right, absolute values off by 32×.*

The discovery route for Bugs 3 and 4 differs from 1 and 2: **have an AI do adversarial code review, then never swallow its findings — manually verify each one against primary evidence (numerical reproduction) before fixing anything.** AI-review findings are often wrong, so the gate — **"finding → reproduce it myself → only then adopt"** — is always inserted.

A **pre-publication full sweep (round 2)** in the same style caught and fixed two more confirmed bugs. **Bug 5: the viewpoint sign on point-cloud normals was inverted** (in a single-viewpoint scan — precisely the intended use of the `viewpoint` argument — every point's normal faced backwards. The existing test absorbed the sign with `abs()`: the same species as Bug 3, "a test that hides the coin flip"). **Bug 6: mesh simplification's boundary preservation self-destructed at high decimation ratios** (the solution of an ill-conditioned quadric was placed several edge-lengths away from where it belonged, and the rim that was supposed to "preserve the boundary" collapsed. The outlier-position guard was hardened, and the breaking condition itself pinned as a regression test). In both cases, the essence was replacing **"tests that happen to pass" with tests that verify signs, absolute values, and the conditions under which things break**.

Bugs 5 and 6 deserve their "how to confirm it" notes at the same granularity as 1–4.

### How to Confirm Bug 5 (Reproducible)

A point cloud's normal vectors should, by rights, be aligned "outward as seen from the sensor (viewpoint)." In a single-viewpoint scan — in the real world, a point cloud captured by one camera or LiDAR seeing one side — the `viewpoint` argument exists precisely to enforce that outward alignment. The bug was that this sign-alignment logic pointed the wrong way: **every point's normal faced away from the viewpoint** — a breakage that's hard to notice by eye.

- **Why the tests missed it**: the existing tests looked only at the normals' **absolute values** (`abs()`). Whether a normal points the right way or exactly backwards, its components' absolute values don't change — so **the tests stayed green even with the sign flipped**. Exactly the same species as Bug 3 (PCA handedness): "a test that looks at only one side of the coin flip."
- **Fix**: replaced it with a regression test that explicitly verifies the sign relative to `viewpoint` — making **the sign itself** the test subject. Round things off with absolute values, and in many geometric operations the "orientation" information vanishes wholesale — the lesson from Bug 3, reappearing verbatim in another op.

### How to Confirm Bug 6 (Reproducible)

QEM (Quadric Error Metric) edge-collapse is the simplification algorithm that thins a mesh's triangles while preserving shape as well as possible. When collapsing an edge, "where should the merged vertex go to minimize error?" is solved as the **minimization of a quadratic form (the quadric)**. The bug: at **high decimation ratios** (aggressive thinning), this quadric became ill-conditioned, and its solution **jumped to a position several edge-lengths away** from where it belonged. Result: the rim — the part meant to "preserve the boundary (the mesh's edge)" — crumbled more the harder you compressed.

- **How it was found**: this op is the very stage of this article's `mesh_decimate.png` (from "How Far the 3D Stack Goes Custom-Built"), which compares naive random decimation, the existing `decimate_qem`, and the boundary-preserving `decimate_qem_manifold` side by side. Adversarial review flagged the high-decimation regime as suspect, and actually confirming the boundary collapse was the starting point of the discovery.
- **Fix**: added an **outlier-position guard** that checks the quadric's solution stays within a sane range, and pinned the exact high-decimation condition where the collapse reproduces as a **regression test**. Even when the design intent "preserve the boundary" is right, **the numerically ill-conditioned regime needs its own guard** — a case of an honest gate revealing the "edge where the optimization stops working."

For both 5 and 6, the essence is the same: **doubt the assumptions of tests that happened to be passing, and re-verify against the concrete ways things break — sign, absolute value, ill-conditioning.**

These six are stories that **would never appear in an article that only shows good results**. But I believe stories like these are exactly what's worth keeping — as **evidence that the quality assurance actually runs**.

---

## The Night Before Release — the Story of CI Digging Up 80 Landmines

Having read this far, you might be thinking, "this person talks with a lot of confidence." What follows is the opposite kind of story. In the same session in which I was finishing this overview, I ran GitHub Actions CI in earnest for the first time, heading toward the PyPI release — and **a huge number of tests in the full suite failed**. I eventually drove it to zero, but many of the mines found along the way were of the kind that had "never caused a single problem locally." Following the honest-disclosure house rule, here is what actually happened — recorded **not celebratorily, but plainly and with interest**. CI failures aren't a disgrace; they're **proof the quality gates actually did their job**.

Let me first be honest about why I hadn't been running CI seriously until now. In solo development, the temptation is constant: **if the local full suite passes, that's good enough**. Your own PC is the environment you know best; dependencies and the GPU are always lined up the same way. Setting up CI is **unglamorous work, easy to defer**, compared with adding one more feature. But publishing to PyPI is a promise that the thing will run **in environments you know nothing about, in combinations you never anticipated**. The comfort of having verified only the single point called "local" becomes **no guarantee at all** the moment you publish — this whole sequence of events was the work of closing that gap the hard way.

### Wave 1: Dependencies "Resident" Locally Get Peeled Away by CI for the First Time

The first wall: on the initial CI run (GitHub Actions, ubuntu, no torch), **the full suite failed en masse**. Tracing the cause: the 3D feature-descriptor modules — `feat_harris` / `feat_spin` / `feat_shot` / `feat_fpfh` — were **importing torch unconditionally at the top of the file**. In an environment without torch installed, the error fires at that import statement, and **`import ops3d` — the load of the entire 3D registry — dies on the spot**. One module's carelessness was dragging down the loading of all 265 3D ops with it.

My development machine has torch permanently installed, so this problem **never once surfaced locally**. The lesson, put into words: **"optional dependencies that are resident locally get peeled away for the first time by CI."** "It runs on my PC" and "the assumptions under which it runs are correct" are different things. The fix: **guard** the torch imports, and raise a **clear ImportError** — "please install `fullseye[gpu]`" — at the moment of actual use. With one deliberate exception: the predicate function `is_tensor` alone **plainly returns False** in torch-less environments. It's used by the numpy path's input guard (the branch "is this a torch tensor? if not, treat it as numpy"), and throwing there would break things that work perfectly well in a numpy-only environment.

### Wave 2: The Remaining 9 — Ratios Pass; Absolute Values and Signs Catch

Clearing Wave 1 still left **nine** failures. From here, each one is a different species of breakage.

**(a) numpy 2.x removed `np.cross`'s support for 2D vectors.** In numpy's major-version bump, the cross product of 2D vectors (`np.cross` — nominally for 3D, but it had historically worked in 2D) became unsupported. Sweeping for call sites that actually passed 2D vectors: **of about 180 `np.cross` calls overall, exactly 2 were affected** — both in the contour Douglas-Peucker (line-segment approximation) code. The fix was local: replace just those two with the **explicit scalar cross product z = ax·by − ay·bx**. This one is an example of a dependency's **breaking change** being caught by tests — the kind of failure whose origin is momentarily hard to place, because "my code didn't change, yet CI fails." Locating 2 sites out of 180 was possible because **I traced from the exact lines the error messages pointed to** — not because I eyeballed all 180.

**(b) `fit_plane_3d` returns `nan` only on CI.** Fit a plane to a perfectly flat point cloud, and the **smallest eigenvalue** of the cloud's covariance matrix is theoretically zero. The computation takes a square root of a quantity derived from that eigenvalue — and **the local BLAS (basic linear-algebra library) implementation rounds that eigenvalue to the +ε side (a tiny positive value)**, while **the BLAS used by the CI runner can round it to the −1e-16 side (a tiny negative value)**. The square root of a negative number is `nan`. Same formula, same input — yet **the direction of the rounding error depends on the runtime's BLAS implementation**. This is a class of breakage that simply does not reproduce locally. The fix: clamp the eigenvalue non-negative with `max(w, 0)` — simple, but it works. Because the root cause was that **the dev machine and the CI runner run different BLAS implementations outright**, no amount of re-running the same test locally would reproduce it. The general rule you can extract: whenever code handles "a value that should theoretically be zero," write the guard on the assumption that **in practice it will not be exactly zero**.

**(c) The camera degeneracy check (rejecting pure-rotation pairs) slips through only on Python 3.12.** When triangulating with two cameras, if the cameras have **rotated but not translated** (a degenerate stereo pair), the triangulated points should theoretically fly off **to infinity**. But digging in revealed something: a point that has flown to infinity, when **reprojected (projecting the 3D point back into the 2D image), lands exactly back on the original pixel**. In other words, "reprojection error" — a metric that looks perfectly natural — **cannot detect** this degenerate case. The final fix was a different method: **test for the existence of parallax (disparity) itself**. Take the sets of viewing-direction vectors (the direction each camera sees) in both images, try to overlay them exactly with a single rotation (an optimal rotation alignment via the Kabsch algorithm), and look at the **median residual**. In the degenerate (pure-rotation) case this residual is **3.5×10⁻¹⁶**; in the healthy case, **1.8×10⁻²** — a decision with **fully 14 orders of magnitude of margin**. A plausible-looking metric (reprojection error) turned out useless, and only switching to a different cut — testing for the existence of parallax — made the decision reliable; personally, this was the most interesting debugging of the batch.

Why reprojection error can't see through the degeneracy, in three passes. ① **One-liner**: a point at infinity photographs onto the same pixel from any angle. ② **A bit more**: even when triangulation fails and the point flies to infinity, reprojecting that "wrong" point back through the camera lands, **by the peculiar property of points at infinity, exactly on the original pixel**. So "run input through to output and measure the loop error" — a verification move that works in many situations — is, in this one situation, **not measuring the thing it needs to measure**. ③ **Why the parallax test does see through it**: parallax is itself the evidence that "both cameras are seeing the same point from different angles." If the camera motion is pure rotation, the two sets of viewing vectors **coincide completely under a single rotation**, leaving no residual (no parallax). If reprojection error is "checking the answer," the parallax-existence test is **the check one step earlier** — "does the problem even exist to be solved?"

[![The camera-degeneracy test's ~14-order-of-magnitude margin (measured)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_kabsch_margin_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_kabsch_margin.png)

*↑ The parallax-existence test, re-measured for this figure: median Kabsch residual is 4.9×10⁻¹⁶ for the degenerate (pure-rotation) pair vs 1.5×10⁻² for the healthy pair — a margin of about 13.5 orders of magnitude, matching the 3.5×10⁻¹⁶ / 1.8×10⁻² reported in the text. The 1e-9 threshold sits comfortably far from both.*

**(d) zig/GCC's UBSan misses float→int cast overflow.** The UBSan (Undefined Behavior Sanitizer — a tool for detecting undefined behavior) used by the C code-generation tests turns out to **differ in what it detects by compiler**. GCC's `-fsanitize=undefined` **does not include** the case of a **float-to-int cast overflowing** (`float-cast-overflow`) — clang does. Worse, GCC also showed behavior ignoring no-recover (the directive to stop at the first error). The difference reproduced on real GCC 13.3 under WSL, and the fix was to add the explicit flags `-fsanitize=float-cast-overflow -fsanitize-trap=...`. "We use a sanitizer" is not enough — unless you confirm **what that sanitizer detects and doesn't detect, per compiler and version**, holes remain. This is part of the test layer supporting Fullseye's C code generation (emitting real C from an op's `c_stmt` and bit-comparing against the Python version), the layer that mechanically checks "does the generated C step on undefined behavior?" Don't trust the tool itself — **verify the tool's coverage too**: a lesson one level more abstract.

**(e) On shared CI runners, the sparse solver is slower than dense.** The sparse-matrix solver that's supposed to improve performance measured **slower than dense on shared CI runners** (measured 1.8–3.2s vs. 0.2–0.3s). Not a bug — just the plain fact that **CI's shared machines differ from a dedicated box in hardware and load**. From this I reconfirmed the discipline: "performance claims are verified only on dedicated machines." The same spirit as this article's "An Honest Word on Performance (GPU)." Shared runners fight countless other jobs for the physical machine, so **cache hit rates and memory bandwidth are a different world from a dedicated box**. This isn't something to fix; it's handled on the **operating-rules side**: "never use CI-side timing measurements as performance claims." The design decision to keep timing out of test pass/fail (benchmarks are managed separately, on dedicated hardware) also came from this incident.

### The Final Wave: "All Tests Pass" and "pip install Just Works" Are Different Gates

With Wave 2 cleared, **CI went all green**, and I published `v0.1.0` to PyPI. It would have been easy to relax there — but right after publishing I ran one more verification: **`pip install fullseye` into a clean venv (a pristine Python virtual environment) and run it**. That caught the last bug.

`recon3d` (the 3D reconstruction module) was **importing `scikit-image` unconditionally**. `scikit-image` is an extras-side dependency — a bare `pip install fullseye` (numpy + scipy only) doesn't bring it in. Result: **`import ops3d` dies on a bare install** — **exactly the same shape of bug** as Wave 1's torch, this time with scikit-image, and — the important part — **CI didn't detect it; it was found only by manual post-release verification**. CI's full suite ran in an environment with the opencv/skimage extras installed, so **CI itself was blind to this class of bug**. I fixed it and published `v0.1.1` **the same day**, this time confirming with the **full smoke-test run in a clean venv** — 0.1.1, numpy 2.4.6, 502 ops, pipeline execution, the 265 ops of ops3d, and the console scripts, all PASS together.

"All tests passing" and "working from a bare pip install" are separate verifications — that's the lesson the final wave carved in.

The reason CI missed it is simple: the full suite ran with the extras installed (scikit-image always present), so the unconditional import **never had a chance to fail**. The bare-install `core-minimal` job's scope was widened in `v0.1.1`, and CI now catches this class on its own.

### The Trajectory in Numbers, and the Lessons in Words

[![The failing-test count across the waves: ~80 → 9 → 1 → 0](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_ci_waterfall_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_ci_waterfall.png)

*↑ Failing-test count across the three waves (about 80 → 9 → 1 → 0): wave 1 = an unconditional torch import, wave 2 = nine failures caught by absolute values and signs, final wave = an unconditional scikit-image import found by clean-venv verification. Numbers are the actual counts reported in this article.*

The failing-test trajectory ran **~80 → 9 → 1 → 0** across three waves (plus one final-check item). The full suite passes locally at **6,224**. CI itself runs a **Python 3.10 / 3.11 / 3.12 matrix**, plus an independent minimal-configuration job that **actually executes, on every run, the claim "it runs on numpy + scipy alone"** (this job is what makes the next accident of the scikit-image class something CI itself catches).

Four lessons from this sequence, put into words:

1. **Optional dependencies resident locally, and gitignored runtime data, get peeled away for the first time by CI.** That it runs in your environment doesn't mean the assumptions under which it runs are correct.
2. **Ratio tests pass. Absolute values and units catch.** This is the **same shape of lesson** as this article's Bug 4 (the curvature absolute value off by 32×), reappearing in the different context of CI.
3. **Exact zero checks break at the mercy of BLAS rounding direction.** When writing code on the premise "this should theoretically be zero," suspect that the sign can flip depending on the runtime environment.
4. **"Tests green" and "works from pip" are different gates.** If the dependency combination your test suite verifies differs from the combination end users actually get, the tests are powerless.

The interesting part: lessons 1 and 4 are **the same accident in the same shape**. The unconditional torch import (Wave 1) and the unconditional scikit-image import (final wave) differ in cause and location, yet their skeleton is identical: **"a dependency that was supposed to be optional had quietly become mandatory."** Even after horizontally deploying the Wave-1 lesson (guard it; raise a clear error) across every site, **add one new module and the same hole can open again**. You could say this was re-learning, on the larger stage called CI, the house rule that appears throughout this article: "found one bug → suspect the same class of bug sleeping in sibling code." Don't stop at one fix — go as far as **embedding into CI itself a mechanism that plugs the same shape of hole** (here: the minimal-configuration job that executes "runs on numpy+scipy alone" every time). Only then can you call it recurrence prevention.

Stories like this may feel "uncool" to some, frankly. I still believe **the record of CI actually digging up mines is itself the evidence that the quality gates truly function**. An article that shows only good numbers would not contain this chapter.

---

## An Honest Word on Performance (GPU)

> **Status: Verified (measured on a real RTX 5090)** — though op coverage is still in progress (see the next chapter).

Being honest about "fast," too. The default frame-at-a-time path runs on scipy / OpenCV. The batched, fast `torch` path (`--device cuda`) accelerates the heavy, vectorizable ops.

- **On CPU**, heavy ops see roughly **1.6–2.2×**. But **light pixel-wise operations actually get slower** (the tensor-conversion overhead lands on top).
- **On GPU (a real RTX 5090), the ops that are already ported are genuinely fast, as measured**: 26 dense pixel-parallel accel ops (median **60×**, percentile **46.6×**), 3D volume operations **~64×**, the shape-matching suite **44–88×** (detected positions match the CPU), NCC matching 4–6× (argmax positions identical), and an end-to-end GPU-resident pipeline (one transfer, chained ops) at **12.6× vs CPU**. All of these sit behind a **faithfulness gate** — an op only rides the GPU if it matches the CPU implementation within interior error < 5e-3.
- The honest limitation today is **coverage**: GPU support spans only part of the ~1,000 ops so far. Pipelines that mix unported ops simply run those segments on CPU (nothing breaks).

I won't write "everything gets faster." Writing down **where it's fast (with measurements) and what still runs on CPU** is what honest disclosure means.

---

## Limitations and What's Next (No Hiding)

> **Status: Roadmap / Design proposal** — from here on, the article covers current limits and pre-implementation plans.

- **HALCON coverage is still 42.5%.** OCR, Classification, and System chapters are nearly empty. The policy of thickening the image/geometry core stays, but "under half" is the fact.
- **The unified API is still mid-migration.** Conventions historically diverged across the image registry, the algorithms, and the perception facade, and the move to the Qt-style natural API is **proceeding in stages**.
- **GPU coverage is still in progress.** The ported parts already exist with real RTX 5090 measurements (see "An Honest Word on Performance" above), but **the full ~1,000 ops aren't covered yet**. **Never pass off CPU numbers as GPU numbers** — that's the discipline.
- **3D visualization inside Studio** is also still being grown, centered on integration with existing viewers (Open3D / RViz2).

A bit more honesty on each.

The 42.5% HALCON coverage sits, as the "coverage story" section explained, on a **deliberately narrowed denominator** — but even so, the work of thickening the Filtering / Morphology / Regions / Segmentation core has no visible finish line yet. In particular, chapters that lean toward machinery — Matching (template and deformable matching), 3D Reconstruction — **don't fit comfortably in a single `fn(v, a, b)`**, and involve design decisions about how to extend the type contracts. They're not the kind of thing that grows just by adding ops.

On the unified-API migration, honestly, a large part of it is **cleaning up after history**. The naming conventions from the `imgevolve` era and the ones added while growing the Physical AI perception facade aren't fully aligned. Realizing the "readable, completion-friendly writing feel" from the design-philosophy section across the whole surface means converging **gradually**, without breaking existing callers — plodding work, more so than feature-building.

On GPU work, the accurate picture is: **the usable parts already exist and are fast, as measured on a real RTX 5090** — it's just that **the full ~1,000-op catalog isn't covered yet**. Every GPU-ported op passes a faithfulness gate (interior error < 5e-3 against the CPU implementation), because "faster but with different answers" is exactly the kind of accident this library refuses to create. The remaining work is widening coverage in the order ops are actually used.

The pile of work is tall, but **the foundation — typed ops, honest evaluation, md-as-source-of-truth docs, 6,238 tests — is set**. From here, the work is extending coverage and the natural API.

---

## Adding Measurement Modalities — What the Eight New Operator Families Let You Do

This section covers the **8 families / 111 ops** added after release. None of them were added because they were new: each one was added only after **measuring where the existing approach breaks, on the same footing**. The typed catalogue is now **511 ops** and the evolution registry **847** (`pip install -U fullseye`).

### What you can do now

| Family | What it lets you do | Entry points |
|---|---|---|
| Coherence scanning interferometry | Measure step height and surface form without phase unwrapping | `csi_stack_simulate` / `csi_height_map` |
| Acoustics & vibration diagnostics | Pull a rotating machine's defect frequency out from under a resonance | `envelope_spectrum` / `order_spectrum` |
| Light field | Change the focal plane and the viewpoint *after* a single exposure | `lf_from_mla` / `lf_refocus` / `lf_depth_from_focus` |
| Photon counting / time-resolved | Count light as particles: range, fluorescence lifetime, Poisson error bars | `tcspc_simulate` / `dtof_depth` / `photon_uncertainty` |
| Quaternion images | 3-D rotation in colour space — an operation per-channel gains cannot express | `rgb_to_quaternion` / `quat_color_rotate` |
| FMCW range-Doppler | Range, velocity and angle of arrival from one beat cube | `fmcw_beat_simulate` / `range_doppler_map` |
| Specular separation | Remove glare; recover normals that survive occluded lights | `specular_diffuse_split` / `photometric_stereo_robust` |
| Motion magnification | Measure and show a 0.2-pixel vibration you cannot see | `displacement_series` / `motion_magnify` |

For each family below: **what you can see**, and **where it breaks**. The second half is usually the more useful one. Full argument lists and units live in the Studio op help and in the 24 guides under `docs/ops/<family>/guides/`, so only the **one- or two-line entry point** appears here.

### Measuring step height — phase shifting breaks at exactly λ/4

White-light interferometry decides height from the **position of the envelope peak**, not from the fringe **phase**. Feed both methods the same input and the breaking point appears exactly where the closed form says it should.

| True step | Phase shifting | Coherence scanning |
|---|---|---|
| 0.15 µm | error 0.0000 | error 0.0000 |
| 0.20 µm | **returns −0.1000** (−λ/2) | error 0.0000 |
| 0.30 µm | **returns −0.0000** (−λ/2) | error 0.0000 |
| 1.00 µm | **returns +0.1000** (−3λ/2) | error 0.0000 |

It starts failing at **λ/4 = 0.15 µm exactly**, and the error is always an integer multiple of λ/2 — fringe orders skip, so this is a **structured lie with no exception, no NaN and no warning**. Change λ to 0.8 µm and the breaking point moves to 0.20 µm. **If your steps exceed λ/4, phase shifting is not an option.**

```python
h = fs.csi_height_map(stack, z_step_um=0.05, wavelength_um=0.6, mode="gaussian")
```

Every unit here is **µm**, and `z_step_um` must match the **actual scan step** — get that wrong and the height scales proportionally, again without an exception. `csi_design` gives you the limits before you buy anything; if you cannot scan at all, `chromatic_confocal_height` returns height from the spectral peak wavelength alone.

### Listening to a rotating machine — the defect frequency is not in the raw spectrum

An outer-race spall in a rolling bearing does not ring at the defect frequency. A structural resonance in the kHz range arrives **amplitude-modulated at a defect frequency below 200 Hz**. Staring at the raw spectrum will never show it.

| Where you look | Amplitude at 107 Hz |
|---|---|
| Raw spectrum | **4.3e-16** ← the component is not there |
| Envelope spectrum | **0.499677** (peak at **107.000000 Hz**) |

```python
sk  = fs.spectral_kurtosis(x, 25600.0)                      # let the machine pick the band
env = fs.envelope_spectrum(x, 25600.0, sk["max_freq"] - sk["bin_hz"],
                                        sk["max_freq"] + sk["bin_hz"])
print(env["peak_freq"], env["band_fraction"])               # 107.0 and ~1.0 = genuine
```

Cross-check against the frequencies the geometry predicts (`bearing_defect_frequencies(1800.0, 9, 8.0, 40.0)` → outer race 108.0 Hz, inner race 162.0 Hz) and you also know *which* part it is. When the shaft speed varies, a naive spectrum collapses to 7 % of the true amplitude and smears over 66.5 Hz. Move to the angle domain with `order_spectrum` and you get **0.999371 with a 0-bin width**.

**The dangerous argument in this family is a scalar, not an array.** Read the same recording as `rate=48000` and the defect is reported at **200.625 Hz** instead of 107 Hz — no exception. That is why the guard lives on `rate`: any real 1-D array genuinely *is* a valid acoustic signal, so declaring a separate type would protect nothing.

### Changing the focal plane after the exposure

A light field is 4-D — (view V, view U, height H, width W). The **input differs** from stereo (two eyes) or a focus stack (a real camera refocusing), so it carries its own type.

```python
sharp = fs.lf_refocus(lf, slope=2.0)                        # pick the focal plane afterwards
slope, conf = fs.lf_depth_from_focus(lf, np.linspace(-4.0, 4.0, 81))
z = fs.lf_disparity_to_depth(slope, focal_px=..., baseline=...)   # to mm
```

Decoding from the raw MLA image (`lf_from_mla` / `lf_to_mla`) **round-trips bit-exactly**, zero disparity (infinity) raises ValueError rather than a silent inf, and the camera itself is designed with `lf_plenoptic_design`.

**What you gain and what you pay come out of the same calculation.** The depth-of-field gain from refocusing matches the angular resolution exactly.

| Angular resolution | DoF (pixel-based) | DoF (after refocus) | Ratio |
|---|---|---|---|
| 6×6 | 1.656 mm | 9.939 mm | **6.0016** |
| 8×8 | 1.656 mm | 13.254 mm | **8.0038** |
| 10×10 | 1.656 mm | 16.573 mm | **10.0075** |

The ratio is not hard-coded: it is **two calls to `depth_of_field` with different circles of confusion** (the 0.0016 in 6.0016 *is* the difference between those two calculations). The price is on the other side of the same table — spatial resolution drops from 2048×2448 to 341×408 / 256×306 / 204×244. **Put those two columns side by side before you buy the camera.**

### Counting light — error bars without calibration

Photon counting is where light stops being a continuous brightness and becomes **countable particles**. Because the Poisson distribution has variance = mean, **your error bars come out without any calibration**. The noise model differs from `aug_read_noise` (additive Gaussian read noise); the two only meet in the generalised Anscombe transform.

```python
clean = fs.tcspc_background_subtract(hist, "median")        # subtract outdoor sunlight
print(fs.dtof_depth(clean, bin_ps=100.0, mode="gaussian"))  # ≈ 3.0 m
sigma = fs.photon_uncertainty(counts)                       # sqrt(N) — error bars, no calibration
```

If `photon_statistics(counts)["fano_factor"]` sits near 1.0, it really is Poisson. SPAD dead-time correction matches the textbook `m = n/(1+nτ)` **bit for bit**, the inverse round-trips at 1.7e-16, and dToF ranging returns **1.5000003 m** when you order 1.5 m.

**There is one specific way to break it.** Dead time applies to the detector's **rate stream** (Hz), not per-bin to a time-bin histogram (counts). Pass a histogram to `spad_deadtime_correct` and you get **no exception and a value indistinguishable from the identity** (relative change 1.1e-4) where a genuine count rate (1e3–1e7 Hz) would change by 33.3 %. **Saturation, the fail-closed path and the non-injective regime are never once exercised.** That is why the types are separate — without that split, this plausible pass is undetectable forever.

### An honest answer to "could quaternion images do something interesting?"

**Yes — for exactly one reason.**

A complex pixel is a 2-D value with a single rotation axis. The pure imaginary part of a quaternion, `(0,R,G,B)`, is a 3-D vector, and `q·x·q*` is a **3-D rotation in colour space**. Turning pure red 90° about the blue axis into green **cannot be produced by any per-channel gain** (the best diagonal approximation is off by `‖P−diag(P)‖₂ = 0.6667`). That is the only genuine capability difference.

```python
import fullseye as fs

q = fs.rgb_to_quaternion(rgb)
turned = fs.quaternion_to_rgb(fs.quat_color_rotate(q, (0.0, 0.0, 1.0), 1.57))
chroma = fs.quat_color_filter(q, (1.0, 1.0, 1.0), "remove")  # drop the grey axis
spec = fs.qft2(q, "left"); back = fs.iqft2(spec, "left")     # side is required; round-trip on the same side
```

**Everything else failed to sell.**

- The same rotation works with a 3×3 matrix (agreeing to 2.22e-16). The quaternion-specific gain is closure of the representation, nothing more.
- **The quaternion Fourier transform buys nothing.** It agrees with a per-channel FFT reassembly to 1.14e-13 and is **2.4× slower**. The only genuinely quaternionic property is that left and right multiplication differ.
- **The Riesz / monogenic signal lost to the complex steerable version built the same day.** With two orientations in the same octave the error is **1.30e-01 vs 4.4e-16**. Two octaves apart both reach machine precision, which pins the cause: the single-plane-wave model is false within a radial band. 25 % of pixels came out rank 0, and the theoretical win (a diagonal lattice) did not materialise either. **It wins twice only** — about 2× under noise, and 2.21× faster at magnification.

**So: narrow-band subjects → `riesz_displacement_series`; broadband → `motion_magnify` below. If you need a rotation in colour space, quaternions are the only option.**

### Far, fast, glossy, barely moving — the remaining three families

**FMCW range-Doppler (8 ops)** gets range, velocity and angle of arrival out of one beat cube. The window function's effect is measurable: a **−45 dB target is buried under −24.57 dB of leakage with a rectangular window** and comes back at **−43.56 dB** with a Hann window.

```python
rdmap = fs.range_doppler_map(fs.fmcw_window_apply(cube, "hann"), normalize=True)
peaks = fs.range_doppler_peaks(rdmap, dr, dv, n_peaks=2)["peaks"]   # dr, dv = bin widths
```

**Without `dr, dv`, the returned `range_m` is a bin index, not metres** (3.0 vs 3.5131928671875). The unit trap is concentrated in this one place.

**Specular separation (13 ops)** either removes glare by colour (one material, white illuminant) or recovers normals from multiple lights. **The shared breaking point is k=4**: once 4 of 8 lights are occluded, plain least squares collapses and both median and RANSAC fall to the noise floor. If you expect more occlusion than that, adding lights is the only remedy.

**Motion magnification (9 ops)** measures and displays a 0.2-pixel vibration. The important part is that **the cliff has a closed form**: the phase reference follows `c·J₀(k·A)`, so beyond the first zero at **2.4048/k = 3.0619 pixels** the measurement inverts.

```python
print(abs(fs.displacement_series(clip, 3.0, 5.0, 32.0)[:, 0]).max())   # 0.2003 px (true 0.2)
r = fs.motion_magnify(clip, alpha=8.0, f_lo=3.0, f_hi=5.0, fps=32.0)   # band in Hz, plus fps
print(r["motion_snr_change_db"], r["band_power_ratio"])                # -2.18 dB, 0.629
```

**The cost of magnification is inside the same return value.** SNR always drops — it never rises. The further `band_power_ratio` is from 1, the further you are from the linear assumption.

### Not carrying big 3-D data around — domain, boundary, run-length

Loading a 512³ CT volume into RAM in full is usually pure waste. **Three separate tools cut "where to compute", "what to keep" and "how much to hold at once".**

```python
part, offset = fs.vol_crop_domain(vol, mask)     # (1) where to compute
back = fs.vol_uncrop(heavy_3d_op(part), offset, vol.shape)    # exact restoration
pts  = fs.vol_boundary_points(mask, spacing=(0.5, 0.2, 0.2))  # (2) shell only, (z,y,x) mm/voxel
print(fs.vol_rle_volume(fs.vol_rle_encode(mask)))             # (3) voxel count, no dense array
```

Measured: cropping a sphere out of a 96³ synthetic CT gives **1/34 the memory**; keeping only the shell of a solid sphere leaves **19 %**; run-length encoding a 384³ part mask gives **1/145 of dense**. Volume and bounding box straight off the runs are **300–1000× faster**, and union / intersection / difference on two 192³ regions take **3.1 ms**.

**A shell reporting a slightly smaller radius is correct behaviour.** Fitting a sphere to the thinned cloud closes with a centre error of 0.000 mm and a radius of 4.33 vs 4.5 mm — the inner-boundary voxel centres sit half a voxel inside the surface. That systematic error is written into the example. **Don't chase it as a precision bug.**

This period also added CT windowing to the 3-D side (machine-verified: bone saturates in a soft-tissue window, soft tissue merges into the background in a bone window), geometric transforms, a virtual probe (2.042 mm wall thickness from one probe against a true 2.000 mm), 3-D FFT filtering and Richardson–Lucy deconvolution. On RL: the docstring claimed "RMSE halves in 10 iterations" and **the measurement was 0.81×**. It was rewritten with the reason it does not halve (the residual is dominated by the staircase at edges, which RL only fixes slowly), and replaced with what RL actually optimises — forward consistency, where re-blurring the estimate matches the observation to 0.021×. **Measure before you write a number in a docstring.**

**Looking at the data changed too.** The Studio 3-D viewer enters **first-person mode with the F key** — WASD to walk, drag to look, wheel to change walking speed, R to return to the entrance. The core of the immersion is **perspective projection**, and because that projection is our own software rasteriser, it was independently verified to agree with the analytic pinhole camera to **10⁻¹³**. Walking through a CT volume looking for defects, or through a point-cloud scan of a ruin — when "looking at data" becomes "standing inside data", you notice different things.

### Reading a skeleton as a graph, and one catalogue for 1-D

**Skeletons**: `fs.apply(mask, "em_skeleton")` thins (a clean-room implementation of the Eckhardt–Maderlechner method, 1993), `junctions_skeleton` / `r2_endpoints_skeleton` give junctions and endpoints, and on the 3-D side `skeleton_junctions3d` / `skeleton_endpoints3d` / `skeleton_prune3d` / `skeleton_branches3d` return nodes, branches and endpoints — a thick volume is thinned by the Lee method (1994) first. **Graphing a voxel skeleton is for vessel, porous-media and root-system network analysis**, and 2-D and 3-D now share one vocabulary.

Verification was a pixel-by-pixel comparison against the published EM93 results (test shape 1: 724/724 pixels, zero difference; the other two match the published pixel counts 2434/3895). That comparison is burned into the regression tests. **The one thing not done is a direct comparison against a HALCON installation** (no licence here).

[![Extracting a skeleton graph from a slime-mould network](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/thumbs/science_physarum_skeleton_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/science_physarum_skeleton.png)

*↑ **A skeleton graph pulled out of a slime-mould tube network** — a mathematical model of *Physarum* (tubes carrying more flow thicken; unused tubes decay) grown in simulation, then read with `em_skeleton` (cyan) and `junctions_skeleton` (white = junctions). Left is the exploring mesh, right is after convergence — **only the shortest path survives**. Ops used: `binary_threshold`, `em_skeleton`, `junctions_skeleton`, `dilation_circle`. The slime-mould simulation is experimental data from a separate "evolving brain" project, which will get its own article.*

**On the 1-D side the problem was not "missing" but "not connected".** The implementation matching the 1-D function family (smoothing, differentiation, extrema, matching — 23 functions) was a **complete orphan** inside the repository: imported by nobody, registered nowhere, no tests, no catalogue entry. And the facade's dispatch table already referenced that module — meaning that **in the version installed from PyPI, those 23 ops died with `ModuleNotFoundError`** (fixed as a shipping bug).

Together with 16 signal-processing functions it is now a **unified 1-D catalogue of 37 ops**, pinned by 41 analytic ground-truth tests (derivative of sin ≈ cos, zero crossings at kπ, period / time constant / delay recovered exactly from a damped oscillation). **2-D `measure1d`, the 3-D probe and sensor series all converge on "extract a profile (x, y)", and this catalogue is what comes next in that chain.**

> **The gap-audit rule**: hunting for "missing ops" is not enough. Hunt for **ops that exist but are not connected to the world** — implemented, worth testing, but with the chain broken somewhere in the catalogue, the package or the facade. That brought 23+16 functions back to life.

## Checking "Will It Even Be Visible?" Before You Buy Any Parts

The first thing an inspection system design has to settle is: **with this configuration, how small a defect can we see?** No catalogue answers that. So this layer returns **limits rather than images**.

### Start with the video

![Sweeping defect size from 20 to 400 µm, with the optical limit and the measured onset of detection](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/visionlab_sweep.gif)

Left is the virtual part as photographed; right is the inspector's answer overlaid on the ground-truth mask. As the defect grows **from 20 µm to 400 µm across 48 steps**, detection starts abruptly at a point. Every number on screen is computed on the spot.

For this system (f=35 mm, working distance 200 mm, f/4, 3.45 µm pixel pitch, 2448×2048):

| Quantity | Value | Where it comes from |
|---|---|---|
| Object-side pixel size | **16.264 µm/px** | magnification 0.21212 from the Gaussian imaging equation |
| Sampling limit (Nyquist) | **32.53 µm** | twice the pixel pitch, projected to object space |
| Diffraction limit (Airy criterion) | **30.67 µm** | 2.44λN(1+m), effective f-number 4.848 |
| **Optical limit (sampling-limited)** | **32.53 µm** | the larger of the two above |
| **Measured onset of detection** | **45.80 µm** (2.82 px) | 5 seeds × 48 sizes |

The answer for this configuration is **1.41× the optical limit**. **That ratio is the whole reading**: much larger means the algorithm or the lighting is the problem; close to 1 means the lens is.

![Sweeping working distance from 120 to 700 mm, watching the same 100 µm defect disappear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/visionlab_design.gif)

The second sweep runs the other way: hold the defect at 100 µm and move the working distance from 120 mm to 700 mm. Pixel size swells from 8.38 to 65.55 µm and the optical limit degrades from 18.40 to 131.13 µm. Three things to watch — **the binding constraint swaps over** (diffraction-limited to sampling-limited at 160.5 mm), **the optical limit passes 100 µm at about 551.6 mm** (beyond that it is unsolvable in principle), and **detection actually holds only to about 403.3 mm**. The practical limit arrives about 150 mm before the theoretical one.

### How to call it

```python
import numpy as np, fullseye as fs

system = fs.VisionSystem(focal_mm=35.0, working_distance_mm=200.0,
                         pixel_pitch_um=3.45, width_px=2448, height_px=2048,
                         f_number=4.0, depth_tolerance_mm=1.0)

sweep = fs.inspection_sweep(system, np.linspace(20.0, 400.0, 48),
                            kind="scratch", seeds=5, contrast=-0.25)
print(fs.detection_report(sweep))
```

`defect_um_grid` is in **µm**; `depth_tolerance_mm` is how far the part may drift off the focal plane, in **mm**. Pass your own inspection function as `detector=` and you get **your algorithm's onset of detection** on the same footing. `kind` is `scratch` / `pits` / `crack` and so on, with defects generated as stochastic geometry (scratches as random walks, pitting as a point process, cracks as branching paths). **The point of that view is not that the pictures look nice — it is that a pixel-perfect ground-truth mask falls out of the definition for free.** There is no annotation step.

There are three layers: `visiondesign` holds the closed-form optics (Gaussian imaging equation, Nyquist, Airy criterion, circle of confusion, cos⁴ law), `defectgen` generates defects, and `visionlab` chains design → limits → build the part → image it → inspect → decide. **Having no renderer** is what settled the design: Monte-Carlo light transport fits neither the dependency policy nor the compute policy. Resolution, depth of field, vignetting and contrast transfer have all been in textbooks for decades, so the implementation is **just an arrangement of them**.

### Never fold the optical limit and the detection limit into one verdict

The worst bug in this layer: **the report said "optical limit not reached" while the lens was resolving perfectly well.** One verdict, `resolvable`, had folded together two independent axes — **lateral resolution** and **depth of field**.

In one configuration the lateral limit was 30.7 µm, so a 60 µm defect was resolved with room to spare, but a depth of field of 0.52 mm fell short of the 1.00 mm tolerance — so no size was ever promoted to `resolvable`, and the headline read "optical limit not reached". **Anyone reading that goes shopping for a lens, when what needs changing is the aperture, the tolerance or the focus mechanism.**

Now they are always reported separately:

```
optical limit  : 30.7 um (diffraction-limited)
detection limit: 60.0 um
depth of field : 0.52 mm < 1.00 mm required — resolvable laterally, but the part drifts out of focus
  -> nothing is rated "resolvable" for that reason alone; the lens is not the thing to change.
```

A second bug of the same character: the sweep tally was mixing **"too small to render at sub-pixel size"** and **"the externally supplied detector threw"** into a 0 % detection rate. `unrenderable` and `detector_failed` are now counted separately, and if zero trials could be evaluated the rate is `None`, not `0%`.

> **Rule**: when you tally failures, **do not mix in the reason for the failure**. Mixing blames the design or the algorithm unfairly. And a quantity with a closed form always produces a number — there is no place to write "not reached".

### Making industry primary sources a standing input for op ideas

`docs/INDUSTRY_SIGNALS.md` is a procedure for reading industrial-vision trade shows and awards as primary sources when looking for op ideas. The reason is that **the criterion differs from a paper corpus**. A reviewer asks "is this academically novel?"; a judge asks "**has industry decided, right now, that this is worth paying for?**" The latter means **the specification is settled and there are numbers to verify against**.

The inventory trap is written into the procedure too. **Never conclude "zero" from a single keyword** — searching `hyperspect` and `spectral` almost led to "we have no hyperspectral", when in fact 14 ops carried a `spec_` prefix. So findings are recorded not as a binary present/absent but in **four states**, including "present but unregistered" and "present but off-convention".

And **13 rejected candidates are kept with their reasons**. Camera transport interfaces are permanently out of scope ("a transport layer, not an op"); edge AI processors are hardware; learning-based defect classification violates the dependency policy and admits no closed-form ground truth; a light-transport renderer is an honest "cannot". **Without that record, you make the same round trip again next time.**

## The Third Layer of QA — Shaking Ops as a Chain

After unit tests and adversarial review, a third layer hunts **bugs that only appear when ops are chained**. And then it turned out that **that layer lies too**. This section is a procedure for anyone putting the same thing on their own library.

### How it works, and how to run it

**Typed pool + random chaining + signature convergence.** Following each op's declaration (in-type → out-type), draw arguments from the pool, chain ops at random (**diffusion**), and put the products back. Every exception or anomaly is collapsed into a **signature** — (class, op, exception, message) — and counted (**convergence**).

The classification is the heart of it.

| Class | Meaning |
|---|---|
| **CONTRACT** | A documented ValueError = clean |
| **SUSPECT** | A raw TypeError / IndexError = a hole in the contract |
| **TYPEMISS** | Returned a type other than declared = the type is lying |
| **NONFINITE** | Silent NaN / Inf |
| **GROWTH** | A product exceeded the pool cap (recorded, never silently dropped) |

```bash
py -3.11 tools/chain_fuzz.py --chains 1500 --length 6 --seed 7001 \
    --coverage-out coverage.json --explore 0.3
py -3.11 tools/chain_fuzz.py --minimize findings.jsonl --only fit_zernike   # shrink to a minimal repro
py -3.11 tools/chain_fuzz.py --replay 7001 --script "op_a,op_b,op_c"        # confirm the repro
```

`--coverage-out` is the point of this section. `--explore` is the probability of preferring ops that produce types not yet in the pool; 0 is uniform (the old behaviour).

**The fuzzer itself was hardened twice in the field.** The first run hit exponential volume growth from a chain of upsampling ops and stalled with a radius-1 morphology pinned to a 34 GB voxel array for 20 minutes. The second stalled when **a TPS fit over 40,000 control points allocated a 12 GB dense matrix internally** — which a pool cap cannot prevent. **Small input, enormous internal allocation** is its own family of adversarial finding. The same pattern was swept out of PSF generation (an order-of-magnitude σ gives 64 GB) and the CPD correspondence matrix; the ops got fail-closed caps, and the TPS warp was chunked into bounded memory **bit-for-bit identically**.

**One representative catch.** `fit_zernike` occasionally returned all-NaN coefficients — never reproducible in isolation, carried as "grey" across three waves. The chain trace pinned it: **a value of order 1e39, finite in float64 (a product of amplifying chains), becomes inf when cast to float32 on the torch path**, after which `grid_sample` and `lstsq` return NaN **silently**. The fix is one helper that validates finiteness after the cast — but the same cast appears in 20 places, so **1e39 was actually pushed through each of them** and only the 4 ops that produced silent NaN were changed (`sobel3d` and others measured clean and were left alone).

**A second lesson: inf is not a bug — the question is whether it is a contract.** `sdf_subtract`'s inf output came from `esdf`'s **documented** contract ("+inf if everything is free space"), propagated with mathematical precision by min/max algebra — innocent. But `sdf_smooth_union` in the same family is arithmetic internally (inf−inf, inf×0) and returned **all-NaN on inf input** — a real bug, fixed by degenerating exactly to `min` where the blend band |a−b|<k degenerates. **Don't blame the op that emitted a non-finite value; trace where it came from and whether that is a contract.**

### "Zero findings" is not robustness — four disguises and how to detect them

**This is the part of the article that transfers most directly to other projects.** A fuzzer's "zero findings" disguises **never-executed** as **robust** in four different ways. All four were hit in a single project.

**1. Arguments with defaults could not be overridden at all.** An op whose default clashes with the pool's dimensions is rejected with ValueError every time and counted as "zero findings" **without ever running**. Concretely: `lf_from_mla`'s default `angular=(5,5)` does not divide 32×32, and it never ran once in 1200 chains.
→ **Detection**: let op-targeted hints override defaults too (name-level hints are left alone, since applying those to defaults would shift the behaviour of every existing op at once).

**2. Coverage reported only a count.** "304/417" does not say whether the remaining 113 are **robust** or **unreachable**.
→ **Detection**: break it down per family. The moment that appeared, the photon family showed `10/17` — **fail-closed working so well that 7 ops had never executed** (the generic `signal` pool is a sine wave with negative values, and non-negativity is a contract for photon counts, so they were cleanly rejected every time). **The defence worked perfectly, and therefore nothing behind the defence was ever tested.**

**3. Signatures split on numbers inside the message.** The better the error message, the more likely it contains **run-specific numbers** ("127 negative bins, min −1.176"), so one issue produces a new signature every run. Almost the entire growth from 99 to 238 signatures was this.
→ **Detection**: mask numbers before forming the signature. 238 → **40**.

**4. Required arguments could not be bound, and it was skipped without a record.** The 3-D family ran only 204 of 310 ops in 1500 chains — not because the ops were robust, but because the fuzzer was silently skipping them.

```
skipped silently, could not bind a required argument   70
input type absent from the pool (must be chained)      21
bindable (simply never drawn)                           9
```

What was missing were ordinary arguments: camera intrinsics, a pose, a RANSAC threshold, voxelisation bounds and resolution. The moment hints opened those paths, **five genuine type mismatches came out of code that had never run**.

```
project_points        declared out image2d -> actually a tuple (uv(160,2), depth(160,))
alpha_shape_boundary  declared out points  -> actually indices (38,) int64
segment_rigid_motions declared out labels  -> actually dict{labels, motions}
pnp_ransac            declared in image2d  -> 2nd argument is actually 2-D points -> raw IndexError
surface type          folded a polynomial model and a B-spline model under one name
```

A health check across the whole ledger then found **seven more of the same class**. The three that could not be fixed are listed with reasons, and the check asserts **exactly that set** — it fails if a listed one is fixed but left in, and it fails if a new divergence appears.

**Reachability is not a guess; it is a fixed point.** Start from the initial pool's types, add the output types of every op whose inputs are all present, and repeat until closed. Measured across 434 ops, **exactly one was structurally unreachable**. Everything else had simply never been drawn.

A run looks like this:

```
== diffusion 1500 chains x len 6 (seed 7001, 45s)
== op coverage: 321/434
== per-family: 1d 34/34  2d 12/12  3d 204/310  lightfield 17/17  math 20/26  optics 17/18  photon 17/17
== findings (raw): {'CONTRACT': 284} / 40 signatures
```

### When to split a type — does mixing raise, or return a plausible wrong number?

"Same shape, so same type" builds systems that are quietly wrong. **There is one criterion.**

> **If mixing them raises, one type is fine. If mixing them returns a plausible wrong number, split them.**

The strongest example was polarisation. **A polariser sweep and a multi-light stack are both non-negative `(N,H,W)` arrays and structurally indistinguishable.** And mixing them **lies silently in both directions**.

- Feed a genuine light stack to polarisation separation and it **fabricates 5.4 % degree of polarisation** with no polariser and no polarised light anywhere in the scene (50 of 50 random light layouts accepted).
- Feed a genuine polariser sweep to photometric stereo and it returns a normal **34° off** from the true `(0,0,1)` of a flat surface, at 21 % residual. The same op on genuine photometric data gives 0.000115°. **A factor of 296,000** (independently re-measured at 35.15° vs 0.000000°).

No exception, no NaN — a confident lie. The same judgement was applied to time-first video (T,H,W) vs spatial voxels, time-of-arrival cubes (H,W,T), colour quaternions vs monogenic signals, complex beat cubes vs real photon histograms, and z-scan stacks — **six times, each backed by measurement**.

**The counter-example is the acoustic signal**, which was *not* split: any real 1-D array genuinely is a valid acoustic signal, so declaring a type would not be a lie but would also protect nothing. The danger was in a scalar, so the guard went there instead.

**One pitfall when you do split**: **always place the entry op and the consuming ops in the same mode, together.** Adding only the consumers means nothing ever produces that type, so all you gain is **dead vocabulary that is permanently unreachable** — the same trap as in the fuzzer.

## An Evolutionary Algorithm Development Environment — Vocabulary and Workload

> **Status: PoC** — demonstrated on four problems. General-purpose automatic design is still not claimed here.

This continues Layer 2. **Widening the vocabulary to 511 ops does nothing if there is no work that uses it.** Here are the measurements.

### The vocabulary did not actually grow

Right after 34 ops were added to the catalogue, **the evolution search vocabulary had grown by exactly zero.** Zero bridging ops. The reason came in two stages.

First, there was no corresponding type on the evolution side. That part is easy to add. But adding it was not enough, because **each family's entry op** (image → light field, depth → time-of-arrival cube) **takes an existing image type as input**. Putting those into the default vocabulary shifts the candidate list of an existing type, **which changes the genome→op mapping and silently rewrites past champions**.

The conclusion is the same as the previous section: **entry and consumers together, in the same mode**. The default vocabulary was left at 801 ops with nothing moved (preserving mapping invariance), while the wide (opt-in) vocabulary went 873 → **890 ops** and the bridges into the new families 5 → **22**. The invariant is pinned by a test: it fails whenever **an op that consumes a type is in the vocabulary while no op produces it**.

### The problems only accepted old types

Running the evolution loop, the top reason for rejection was this:

```
rejected  5  problem does not accept this input type (histcube)
rejected  4  problem does not accept this input type (lightfield)
rejected  2  problem does not accept this input type (counts)
```

**All 12 problems used old types.** Four problems on the new types were added; the ground truth for each is constructed exactly from a forward model (synthesise the input knowing the answer).

### Scoring on a locked holdout — two wins, one loss

```bash
py -3.11 robust.py --problem photon_denoise --seeds 3 --gens 12 --pop 12
```

`robust.py` runs N independent seeds, **selects strictly on TRAIN**, and reports the **locked holdout** — the genuinely untouched split, scored exactly once against the final champion — together with the seed-to-seed spread.

| Problem | Identity | Hand (best single existing op) | Evolved | vs hand |
|---|---|---|---|---|
| Photon histogram denoising | 0.2664 | 0.5371 | **0.7760** | **+44.5 %** |
| Map of where things vibrate | 0.0000 | 0.6973 | **0.8868** | **+27.2 %** |
| Light-field disparity map | 0.0000 | 0.5794 | 0.5907 | +2.0 % |
| Specular removal | 0.4115 | 0.8406 | 0.6039 | **−28.2 %** |

The photon champion is **a composition closed entirely within the photon family**:

```
irf_convolve → background_subtract → deadtime_correct
```

That is the first case where a new family delivered value **as a chained procedure** rather than as an individually useful op.

**The most useful row is the loss.** For specular removal, evolution found a champion that **crosses families through the quaternion ops** (colour image → quaternion → colour-space rotation → colour image). On the observed split it read 0.776, close to the hand baseline of 0.84 — **on the untouched split it fell to 0.628**, with a seed-to-seed standard deviation of 0.190. The winning vibration map, by contrast, had a standard deviation of 0.001 on the untouched split.

> **Rule**: looking only at the observed split, this reads as "so close". **Until you report the locked holdout and the spread together, nothing has been won.**

## Building "Honesty" Into the System (continued)

Continuing the chapter of the same name earlier. Three cases of **turning a discipline into a check**.

### Turning provenance discipline from prose into a test

The answer to "is it a problem to implement something under the same name?" is: **however independently the code was written, provenance is whatever you wrote down**. In practice, a commercial product name ended up in a new module's docstring as *the reason the module exists*. The code was raised independently from public literature, and the provenance record was polluted anyway.

The discipline was rewritten as a three-way split:

| Use | Verdict | Reason |
|---|---|---|
| Attaching another company's name to **something of ours** (module name, op name, API name, "why this exists") | **Forbidden** | It creates a false provenance record regardless of how the code was actually written |
| **An interoperability identifier** (a string that selects a device driver, an alias table for people arriving from another tool) | Allowed | It is the de-facto name of something that really exists over there; removing it lowers availability without raising independence |
| **An attributed citation** (recording which award went to whom, with a URL) | Allowed | This is a citation; removing it makes the claim unverifiable. **Attribution is the opposite of plagiarism** |

The test is "**does this name refer to something of ours, or to something of theirs?**" Pointing at theirs with attribution is citation; pasting theirs onto ours is the thing you must never do.

**The old rule said "never write it anywhere in the documentation" — and the repository itself did not comply.** A rule nobody can follow cannot be audited either. It was rewritten to match reality and then turned into a machine check, scanning four surfaces (module names, function names, module docstrings, public docstrings), with a written reason required for every exemption.

```bash
py -3.11 -m pytest tests/test_provenance_naming.py -q      # 7 passed
```

### Building a fidelity gate? Then attack the gate itself

GPU acceleration runs behind a fidelity gate: **only ops that numerically match the CPU reference get loaded**. That gate had three holes. **Here they all are, for anyone building the same thing.**

**1. `reflect` padding is not the same in torch and scipy.** Whether the edge pixel is duplicated differs. The fix for that difference had only been applied to some kernels; applying it everywhere brought **7 ops including sobel and median into exact agreement out to the edges**. It also turned out that DoG (difference of Gaussians), which had been **excluded with the conclusion that it was impossible to make faithful in principle**, had this padding as its real culprit. **When a port disagrees at the border, suspect the padding convention first.**

**2. The gate tested at a single parameter point.** With large kernels the edge intrudes into the inspection margin. Strengthened to a 5-point sweep with a margin tied to kernel radius.

**3. The strengthened version had a second hole.** **On a flat (constant) image, normalisation amplifies float32 rounding noise to full scale.** It breaks spectacularly — canny turns a constant input entirely into foreground. Constant and quantised images were added to the inspection set, and **all 90 mappings now agree**.

**The automated alias search had the same trap.** Ops with identical implementations under different names were mined by brute-force comparison of every unsupported op against every GPU kernel — but the first test image was **binary salt noise**, and the degeneracy "erode it and everything vanishes" **mass-produced false matches**: **all-zero agrees with all-zero for any reason at all.** Re-run on a structured blob image, only the 42 confirmed at 5 parameter points were adopted (one that behaves differently on greyscale was rejected despite matching numerically). GPU coverage across the 20 shipping recipes went **45 % → 79 %**.

### Five rules that decide whether a number can be trusted

Five of my own and the AI's errors from this period, stated as **rules** rather than stories.

1. **Always compare on the same split.** A hand baseline of 0.3945 next to an evolved 0.546 was nearly written up as "+38 %" — **those two numbers came from different draws**. Re-measured on the same split it is +2.0 %. **Comparing across draws inflates by nearly 20×.**
2. **The hand baseline is not "the first op you thought of" but "the best existing op".** The promotion gate searched exhaustively and found an op more than twice as strong as the one placed by hand. A weak baseline makes the problem look easier than it is.
3. **Write type predicates on shape, not on type.** A `pose` check written with `isinstance(np.ndarray)` flagged 6 items, of which 4 were the predicate's own fault — GPU-capable ops return torch tensors by convention here. Rewritten on shape, the remaining 3 were genuine (one declared `pose` while carrying neither R nor t).
4. **Re-measure the numbers that favour you, first.** A report claimed quaternion superiority: "composing quaternions 100,000 times drifts by 0.0; matrices by 4.4e-10". That 4.4e-10 came from a *different* bug in `pose_quat` (adding 1e-12 to the denominator during normalisation) feeding it non-orthogonal matrices. The correct figure is **4.33e-14** — four orders smaller, plain rounding error, and no advantage at all.
5. **A number written in a comment is, at the time of writing, unmeasured.** Writing a guide surfaced an unmeasured value; measuring it showed the behaviour was **worse than written at high padding** (reporting a strong transient of +4.09 that does not exist in pure white noise) and **milder at low padding**. One invented pair of numbers cannot convey that scale dependence.

### The API had 28 unwired functions the day after release

Checking the inventory during the quaternion discussion revealed that **28 quaternion and dual-quaternion functions existed and not one was reachable from either facade**. Wiring them up immediately surfaced three silent errors.

- `quat_normalize([0,0,0,0])` returned `[0,0,0,0]`, which becomes the **identity matrix** as a rotation — "rotation undefined" turns into "no rotation".
- A rotation request about a zero axis produced a non-unit quaternion of norm 0.878.
- `|RᵀR − I| = 4.0e-12` — not rounding error but a **one-directional shrink**, accumulating with every composition.

The cause was dividing by `norm + 1e-12`. **Making zero length fail-closed and using exact division brings the orthogonality error to 4.4e-16.** The 4.0e-12 figure, it turned out, arose because `quat_to_hom_mat3d` calls `quat_normalize` internally, so **ε was applied twice**; reproducing only the outer formula does not show it in the current code.

**Sweep the same class of miss through sibling code.** A size cap that took effect **after promotion to float64**, and therefore failed to prevent the allocation it existed to prevent, was fixed in two modules (verified with a 0-byte view rejected in 0.0000 s).

Across the 8 families, adversarial review found and fixed **more than 30 real bugs** — every one of them the "**silently returns a wrong number**" kind rather than the "raises" kind: an angle folded by a sine so that 95° and 85° become **bit-identical**, an array with no aperture **confidently returning −90°**, a frame straddling a pad looking the most dramatic and **reporting a transient that does not exist**, an envelope clipped at the edge **returning a height that is 76 % wrong**, an nm/µm wavelength mix-up that is **completely asymptomatic**. None of these are visible without running and measuring.

### What you get today

Here is what `pip install -U fullseye` gives you, listed by capability.

| What you want | Entry point | The number to remember |
|---|---|---|
| Step height / surface form, no unwrapping | `csi_stack_simulate` / `csi_height_map` | phase shifting breaks at **λ/4** |
| Rotating-machine defect diagnosis | `envelope_spectrum` / `order_spectrum` | the defect frequency is **not in** the raw spectrum |
| Change focus and viewpoint afterwards | `lf_refocus` / `lf_depth_from_focus` | gain = angular resolution; you pay in spatial resolution |
| Photon-level metrology with error bars | `tcspc_simulate` / `dtof_depth` / `photon_uncertainty` | Poisson: variance = mean (no calibration) |
| 3-D rotation in colour space | `rgb_to_quaternion` / `quat_color_rotate` | the **only** quaternion-specific gain |
| Range, velocity, angle of arrival | `fmcw_beat_simulate` / `range_doppler_map` | without bin widths, the units are bin indices |
| Glare removal / robust normals | `specular_diffuse_split` / `photometric_stereo_robust` | breaking point is **k=4** occluded lights |
| Measure and show invisible vibration | `displacement_series` / `motion_magnify` | the cliff is **3.0619 px** (first zero of J₀) |
| Not carrying big 3-D data around | `vol_crop_domain` / `vol_boundary` / `vol_rle_encode` | 1/34 · 19 % · 1/145 |
| Reading a skeleton as a graph | `apply(mask, "em_skeleton")` / `junctions_skeleton` / `skeleton_branches3d` | pixel-exact against EM93 |
| 1-D profile analysis | `derivate_funct_1d` / `zero_crossings_funct_1d` and 37 ops | converges with 2-D measure1d and the 3-D probe |
| Digging out chained bugs | `tools/chain_fuzz.py --coverage-out` | always read the coverage **breakdown** |
| Designing pipelines by evolution | `robust.py --problem <name>` | locked holdout and spread, together |

Per-family usage in detail (units, breaking conditions, comparisons against existing methods) lives in 24 guides under `docs/ops/<family>/guides/`. The test suite stands at **8,169 passing**.

## Summary

**Fullseye** carries roughly **1,000 explainable classical-vision algorithms as "skills,"** and lets you choose, behind one typed interface, whether to

- **use them directly (apply / pipeline)**,
- **design with them by evolution (evolve, with honest evaluation)**, or
- **use them as a robot's eyes (the Physical AI perception stack)** —

a numpy-native, self-built library. **42.5% against the HALCON yardstick (measured)**, **6,238 tests**, a documentation system with **Markdown as its single source of truth**, and the **HDevelop-style Studio**. Every deep dependency is optional, and **the core runs on nothing but numpy + scipy**.

What I most want to convey is neither the scale nor the coverage rate, but the stance of **making honesty a mechanism**. Hold-out data never selects. Coverage is disclosed as measured. **When a bug is found, the article keeps the bug — together with the quality assurance that caught it.** Over flash, the priorities are being **explainable, reproducible, and maintainable for the long haul** — built up steadily.

The CI story in "The Night Before Release" connects to the same root. Publishing the whole path from ~80 failures down to zero, without hiding it, is this discipline in practice: **keep the evidence that quality assurance actually works, with the same standing as the good numbers**.

One more thing worth adding: Fullseye is a library with **footholds in both the industrial-vision lineage and Physical AI**. As the section "The Workhorses of Factory Inspection Lines, One pip Away" describes, the inspection-line staples — defect detection, subpixel metrology, shape matching, blob analysis — carry straight over into Physical AI robot perception (object separation for bin picking, LiDAR clustering, grasp-point detection). Rather than saying the two were deliberately balanced, the more accurate phrasing is: **build one "system of ops connected by types," and it naturally reaches both floors.**

This is a fresh release, so **there may still be a few rough edges**. It's built to be touched, spun, and verified though — so please do give it a casual try (and if you catch something misbehaving, an [issue](https://github.com/furuse-kazufumi/fullseye/issues) would make my day). If this made you want to try it, installation is about five minutes away in the "[Getting Started](#getting-started-installation-up-front)" section near the top. The tastiest way to use it is the combination of **Claude Code + `fullseye-rag`** (turning it into an AI's toolbox). If you haven't set up Claude Code yet, [the author's referral link](https://claude.ai/referral/0sqPw8E_lw) is there if you'd like to start.

---

## To Be Continued

One preview of the next installment's protagonist (click to play the video):

[![evis's 700-muscle activation heatmap — tendon colors driven by real activations during a real physics re-simulation (click to play mp4)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_muscle_heatmap_thumb.jpg)](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/evis_muscle_heatmap.mp4)

*↑ ▶ The body of Fullseye's customer number one, evis — a muscle-activation heatmap where the colors of all 700 tendons update every frame from real activations (d.act) during a real physics re-simulation (arm raise → walking). **This is a re-encode of experimental footage from the evis-side project; no Fullseye processing is involved** — supplying this body with "eyes" is exactly what Fullseye's layer ③ is for.*

This article was the "map." Next, I'll walk its regions. Candidates:

- **What happens when you add one op** — the internals of the machinery by which the registry, evolution, code generation, and documentation all follow automatically.
- **How to grow HALCON's 42.5%** — a build log of filling uncovered operators one by one through the honest gate.
- **Physical AI's eyes** — evis's vision pipeline end to end, from stereo through 6-DoF pose to "pinching" with 700 muscles.
- **Technical follow-ups on the mines CI dug up** — each bug from "The Night Before Release," down to the fix commits and how the tests were written.

This ran much longer than originally planned. From Layer 1's type contracts through the six sensors, Studio's working workflow, AI-as-RAG operation, and the mines CI dug up — the reason for packing it all into one article is that I wanted to show, without carving it apart, that **inside the single library called Fullseye, all of these rest on the same design decisions**. Each topic alone is a pile of unglamorous craft; lined up together, one thread runs through them — "make honesty structural." If that came through, I'm glad.

Thank you for reading. If there's a "tell me more about this part," that will become the next article.

---

<!--
Publication notes (not shown in the article body):
- All numbers are measured (ops 735/731, 3D 265, HALCON 982/2313=42.5%, tests 6238). Re-measure before updating any of them.
- Prefer Mermaid over images where possible (native to Qiita; avoids SVG path/cache issues). If figures become SVG, always apply raw absolute URL + HTTP 200 check + ?v=N cache-bust.
- Apache-2.0 and reimplemented-from-public-knowledge are stated explicitly (the no-derivation-from-commercial-products line).
- Release logistics: queue as a private draft, and publish when a slot opens, avoiding Qiita's consecutive-post 502.
-->
