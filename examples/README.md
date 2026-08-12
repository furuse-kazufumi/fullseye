# Examples

Runnable, self-contained templates (synthetic data, no external files) that other
projects can copy. Each has a `run()` you can import and a CLI.

| script | what it shows |
|---|---|
| `perception_pipeline.py` | rectified stereo pair → disparity → depth → point cloud → terrain heightmap → traversability, with colourised PNG + PLY export |
| `segment_and_classify.py` | segment objects → describe (Hu + shape) → identify against prototype descriptors (feature-based) |

```bash
py -3.11 examples/perception_pipeline.py --save out/demo
py -3.11 examples/segment_and_classify.py --save out/demo
```

To adapt: replace the synthetic inputs with your real frames, and (for the
perception pipeline) the camera→world transform with your robot's extrinsics. The
smoke tests in `tests/test_examples.py` keep these working.
