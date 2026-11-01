# Fullseye

## An explainable and verifiable geometric vision development platform for Physical AI and industrial robotics

Turn AI-generated image-processing algorithms into **executable pipelines that people can understand, modify, and verify.**

Fullseye — the name comes from 'bullseye', the centre of a target.

---

## 01　What is Fullseye?

Fullseye is a development platform project for Physical AI, industrial robotics, and industrial machine vision. It connects the construction of image-processing and geometric-measurement algorithms with their execution, visualisation, and evaluation.

### From “working code” to development assets that can be understood and verified

AI can generate image-processing code, but that alone is not enough for sustained research and development or industrial use. We also need to understand the assumptions under which the processing works, where it fails, and what a change has improved. The final result by itself cannot fully reveal whether a problem lies in the input conditions, choice of operations, parameters, or coordinate transformations.

Fullseye aims to take generated algorithms beyond “working code” by associating the processing structure with intermediate results, execution conditions, and evaluation results, so that people can treat them as development assets they can verify and improve. To this end, it brings together classical image processing, geometric algorithms, numerical computation, visual programming, and AI-assisted development.

The same operator system also includes operators that computationally reproduce optical systems, illumination, sensors, and objects through physics simulation. Another feature of Fullseye is that verification can proceed in sequence: first build the processing under virtual imaging conditions for which the ground truth is known, and then check it against publicly available real-world data.

> **Use learning-based AI and geometric vision as complementary tools.**  
> The basic policy is to combine the recognition and reasoning capabilities of DNNs and VLMs with explicit mathematical models and geometric constraints.

## 02　Design principles supporting the development platform

### A common operator system connecting editing, execution, evaluation, and AI assistance

At the core of Fullseye is a design in which visual editing, code generation, execution, evaluation, and AI assistance share a system of operators (ops) with mathematical specifications and typed interfaces. GUI nodes, operations called by generated code, and processing candidates selected by AI are all handled under a common specification. This makes it possible to associate the intent at editing time with the processing at execution time and the evidence used in evaluation.

More than 3,600 operators are currently registered (3,623 as of November 2026). Priority areas include preprocessing, feature and contour extraction, geometric model fitting, calibration, and coordinate transformation. We envisage a platform on which the same processing can be constructed and inspected through both visual editing and code editing.

| Key requirement | Design approach |
|---|---|
| Explainability | State the mathematical definition, parameters, and processing performed by each operation. |
| Traceability | Make it possible to trace the relationships among inputs, intermediate results, operating conditions, and final outputs. |
| Reproducibility | Manage input data, execution conditions, and dependencies to support the reproduction of results. |
| Verifiability | Use tests and quantitative evaluation to check the validity and performance of the processing. |
| Computational efficiency | Understand the operation structure, memory use, and data transfers in order to improve execution efficiency. |

In this project, explainability primarily means that people can inspect the relationships among the operations, parameters, coordinate transformations, and intermediate results that make up a pipeline. It does not mean that the internal decisions of incorporated DNNs or VLMs can also be explained.

### Implementing major algorithms from mathematical models

Our policy is to implement major image-processing and geometric operations from their underlying mathematical models, in a form that allows their procedures and numerical properties to be inspected, changed, and verified. Using a numerical computing foundation centred on NumPy, we aim to manage operation procedures, data types, precision, and memory layout in a form that makes the internal structure easier to study, modify, and verify.

### An operator system with explicit types and coordinate systems

We define operator input and output types, tensor shapes, and the meaning and permitted ranges of parameters as a common specification. We also explicitly identify image, camera, world, and robot coordinate systems, transformation directions, and units, and connect them to evaluations such as residuals and reprojection error.

Mathematical transparency does not guarantee that a result is correct. It is used together with validation based on actual measurements.

## 03　Fullseye Studio — combining visualisation with code editing

Fullseye Studio is an integrated development environment that combines visual pipeline editing with direct editing of Python code. To support construction, experimentation, debugging, and verification in one consistent environment, it provides—and in some cases envisages—the following capabilities.

| Capability | Intended development experience |
|---|---|
| Visual construction | Build a pipeline by searching for, selecting, placing, and connecting operators for preprocessing, feature and contour extraction, geometric measurement, coordinate transformation, and other tasks. |
| Bidirectional code sync | Generate Python code from the GUI and use AST analysis to reflect corresponding code changes back in the GUI. |
| Inspection of intermediate results | Inspect the images, values, and parameters at each step to locate failures and identify candidates for improvement. |
| Management of experimental conditions and history | Manage inputs, configurations, parameters, software versions, and evaluation results in association with one another. |

Of these capabilities, visual construction and the inspection of intermediate results are available in the current version. For bidirectional code sync, the current implementation can export a pipeline assembled in the GUI as ordinary Python code, run that code in a separate process, and compare the results at each stage for agreement. Reflecting code changes back in the GUI is envisaged only for a defined range of supported syntax, operators, and control structures; complete conversion of arbitrary Python code into a graph is not an assumption. Management of experimental conditions and history is still at the concept stage.

## 04　From a node graph to an independent execution pipeline

We envisage converting node graphs into independent executable code. By separating the GUI editing representation from the runtime operation structure, we seek to combine development flexibility with execution efficiency through the following stages.

1. **Analyse the node graph**  
   Represent the connections as a DAG and use topological sorting to determine an execution order based on dependencies.

2. **Convert to and verify an intermediate representation**  
   Organise operators, inputs and outputs, parameters, types, and shapes into an intermediate representation (IR), then check structural and type consistency.

3. **Optimise with correctness as the priority**  
   Consider buffer reuse and the elimination of unnecessary copies in light of intermediate-data lifetimes and dependencies.

4. **Generate executable code**  
   Convert the pipeline into GUI-independent Python/NumPy code for use in independent testing, Git-based management, and integration into existing applications.

The current version provides a path that generates Python code—and C code for supported operators—from a typed intermediate representation, and checks the output of the generated code against that of the original processing. Optimisations such as buffer reuse remain future work.

Value ranges and geometric constraints that types alone cannot capture are supplemented by per-operator contract conditions and runtime verification. Performance evaluation covers throughput, latency, jitter, and memory consumption.

## 05　Verifiable collaborative development by AI and people

For AI integration, we envisage collaborative development in which generated processing is expressed through the common operator system and a verifiable execution structure. The scope extends beyond code generation to improvement through observation and evaluation of execution results.

### Generate → execute → observe → evaluate → revise

- **Specification-based generation:** AI refers to operator types, mathematical specifications, and parameter conditions to compose processing candidates.
- **An interface for AI:** The project will provide an MCP server through which AI can search for operators, execute them, and observe their results. Unknown names and connections with incompatible types will be rejected with reasons rather than silently replaced by similar alternatives.
- **Staged verification:** Syntax, types, connection consistency, unit tests, and evaluation of execution results are combined.
- **Visual feedback:** We are considering a mechanism in which a VLM observes intermediate images and final results and proposes the stage at which a problem occurs or candidates for changes.
- **Quantitative evaluation and human judgement:** Positioning error, detection accuracy, reprojection error, processing time, and memory use are compared, and people decide whether to accept a change after confirming its effect and validity.

> AI supports candidate generation and iterative improvement, while people judge the meaning of the processing and its engineering validity. Through this division of roles, we aim to improve development efficiency while preserving understandability and controllability.

## 06　Envisaged applications and research and development

| Application area | Envisaged processing and evaluation |
|---|---|
| Precision positioning and geometric measurement | Estimate position, pose, dimensions, and displacement from feature points, contours, lines, circles, and other geometry. Evaluate measurement error, repeatability, and stability under disturbances. |
| Camera–robot coordination | Establish coordinate correspondences through camera calibration, projective geometry, hand-eye calibration, and related methods. |
| Visual feedback | Use position and pose information for motion correction. Verify applicability in terms of latency, measurement accuracy, and temporal stability. |

### Example use: building and improving a component-positioning pipeline

For example, when determining the position and pose of a component from a camera image, image preprocessing, contour and feature extraction, geometric model fitting, and coordinate transformation are assembled into a single pipeline.

1. **Build the processing:** Connect operators from preprocessing through position and pose estimation, and explicitly identify the required calibration information, coordinate systems, and units.
2. **Inspect intermediate results:** Examine the preprocessed images, extracted contours and features, and model-fitting results to determine whether processing is proceeding as intended.
3. **Evaluate accuracy and performance:** Under defined input conditions and in a defined execution environment, evaluate error against reference positions and poses, repeatability, processing time, and other measures.
4. **Compare the effect of changes:** Compare the pipeline before and after human parameter adjustments or AI-generated improvement proposals under the same evaluation conditions, and confirm the effect and validity of the changes.

The aim of this development flow is to treat not only the final position and pose output, but also the processing structure and conditions that produced it and the evaluation results used to judge improvements, as one integrated whole.

### About the exhibits on this page

Each exhibit on this page is an example in which processing was assembled from Fullseye operators and its results checked against ground truth or public data. Many exhibits show not only the conditions under which a method succeeds, but also those under which it begins to break down.

### From iterative PoCs to research results that third parties can verify

In research and development, we emphasise repeated implementation, operational checks, and improvement through proofs of concept (PoCs) for individual algorithms and development capabilities. Our policy is to associate input data, evaluation conditions, execution environments, and quantitative results, and organise them as results that third parties can reproduce and verify.

Comparisons with existing libraries and representative methods cover not only speed, but also numerical accuracy, robustness, memory use, stability of execution time, and ease of development and verification. As far as possible, we plan to publish implementations, evaluation scripts, test data, experimental conditions, and benchmark results, and aim to communicate the results through conference presentations and technical papers.

> **Fullseye aims to be an open, extensible development platform that brings together the flexibility of AI and the mathematical rigour of geometric vision.**  
> Understandable. Reproducible. Verifiable. Step by step, we will connect these qualities to implementations of Physical AI and industrial robotics.

---

### Assumptions for application and evaluation

This document introduces Fullseye's philosophy, design policies, current implementation and planned capabilities, and envisaged uses. Performance and applicability are verified against the input data, evaluation conditions, and target environment. Execution based on NumPy alone does not guarantee hard real-time performance. Applying Fullseye to safety-critical robot control presupposes safety design and verification of the system as a whole, in addition to evaluation of the image processing itself.
