# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Blender(Cycles)で混載パレットを天井のカメラから描く。Blender の中で走らせる。

    blender --background --factory-startup --python tools/depal_blender_render.py -- <export_dir> <out_dir> [samples] [serve]

``export_dir`` は ``examples/poc_mixed_case_depalletizing.py`` の ``export_scene`` が書いた場所。``scene.json`` の ``frames`` の
コマ(残っている箱の組)ごとに、天井カメラの RGB(16 bit PNG、sRGB)を ``out_dir`` へ書く。
最初のコマだけ深度(Z、OpenEXR)も書く —— 数値の描画と同じ幾何かを確かめるため。
材質: 段ボール(拡散 + 反射率の画像、光沢の画像で粗さを変える)、透明テープ、
シュリンクフィルム(透過 + フレネル反射)、木のパレット、コンクリートの床。照明は倉庫の天井灯。
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
EXP = Path(argv[0])
OUT = Path(argv[1])
SAMPLES = int(argv[2]) if len(argv) > 2 else 96
OUT.mkdir(parents=True, exist_ok=True)
meta = json.loads((EXP / "scene.json").read_text(encoding="utf-8"))

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ---------------------------------------------------------------- 描画の設定
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == kind
        if any(d.use for d in prefs.devices):
            break
    except Exception:  # noqa: BLE001
        continue
import os as _os
scene.cycles.device = "CPU" if _os.environ.get("DEPAL_DEVICE", "CPU") != "GPU" else "GPU"   # 既定は CPU(GPU は呼び手がロックを取ったときだけ)
print("DEPAL_DEVICES", prefs.compute_device_type, [(d.name, d.type, d.use) for d in prefs.devices], flush=True)
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.seed = 7
scene.cycles.max_bounces = 6
cam_meta = meta["camera"]
scene.render.resolution_x = cam_meta["width"]
scene.render.resolution_y = cam_meta["height"]
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "16"
scene.render.image_settings.color_mode = "RGB"

# 世界(薄い環境光)
world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.57, 0.6, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35

# ---------------------------------------------------------------- 材質
def _img(name, colorspace="sRGB"):
    im = bpy.data.images.load(str(EXP / name), check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def mat_cardboard(top_png, gloss_png=None):
    m = bpy.data.materials.new(top_png)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _img(top_png)
    tex.interpolation = "Cubic"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.35
    if gloss_png:
        g = nt.nodes.new("ShaderNodeTexImage")
        g.image = _img(gloss_png, "Non-Color")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 0.88
        mr.inputs["To Max"].default_value = 0.10
        nt.links.new(g.outputs["Color"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.88
    # 段ボールの表面の細かい凹凸
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 900.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_film():
    m = bpy.data.materials.new("film")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.03
    fr = nt.nodes.new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.5
    nt.links.new(fr.outputs["Fac"], mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def mat_wood():
    """木の板: 板の長さ方向(x)に流れる木目 + 細かいむら。"""
    m = bpy.data.materials.new("wood")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.15, 6.0, 6.0)
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 1.5
    wave.inputs["Detail"].default_value = 3.0
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 25.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(wave.outputs["Fac"], mix.inputs["A"])
    nt.links.new(noise.outputs["Fac"], mix.inputs["B"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.40, 0.29, 0.17, 1)
    ramp.color_ramp.elements[1].color = (0.66, 0.53, 0.37, 1)
    nt.links.new(mix.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return m


def mat_concrete():
    m = bpy.data.materials.new("concrete")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40.0
    noise.inputs["Detail"].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.30, 0.30, 0.29, 1)
    ramp.color_ramp.elements[1].color = (0.50, 0.49, 0.47, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.65
    return m


def add_cube(name, center, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    return o


def import_obj(path, mat, matrix):
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    o = bpy.context.selected_objects[0]
    o.matrix_world = Matrix(matrix)
    o.data.materials.clear()
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ---------------------------------------------------------------- 床・パレット・照明・カメラ
bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, 0, 0))
floor = bpy.context.active_object
floor.data.materials.append(mat_concrete())
wood = mat_wood()
half = meta["pallet"]["size"] / 2
top = meta["pallet"]["top"]
pitch = meta["pallet"]["size"] / 9
for i in range(9):
    y0 = -half + i * pitch
    w = pitch - 0.024
    add_cube("deck%d" % i, (0, y0 + w / 2, top - 0.0105), (2 * half, w, 0.021), wood)
for j, x in enumerate((-half + 0.05, 0.0, half - 0.05)):
    add_cube("stringer%d" % j, (x, 0, (top - 0.021) / 2), (0.10, 2 * half, top - 0.021), wood)

for i, (x, y) in enumerate([(-1.2, -0.9), (1.2, -0.9), (-1.2, 0.9), (1.2, 0.9), (0.0, -1.6), (0.0, 1.6)]):
    ld = bpy.data.lights.new("bay%d" % i, "AREA")
    ld.size = 0.6
    ld.energy = float(meta.get("light_w", 22.0))
    lo = bpy.data.objects.new("bay%d" % i, ld)
    lo.location = (x, y, 5.5)
    scene.collection.objects.link(lo)

kd = bpy.data.lights.new("key", "AREA")
kd.size = 1.2
kd.energy = float(meta.get("key_w", 45.0))
ko = bpy.data.objects.new("key", kd)
ko.location = (1.0, 1.4, 4.0)
ko.rotation_euler = (math.radians(-18), math.radians(12), 0.0)
scene.collection.objects.link(ko)

cd = bpy.data.cameras.new("cam")
cd.sensor_fit = "HORIZONTAL"
cd.sensor_width = 36.0
cd.lens = cam_meta["fx"] * 36.0 / cam_meta["width"]
cam = bpy.data.objects.new("cam", cd)
cam.location = (0.0, 0.0, cam_meta["z"])
cam.rotation_euler = (0.0, 0.0, 0.0)             # 真下向き(Blender のカメラは −Z を見る)、画像の上 = +y
scene.collection.objects.link(cam)
scene.camera = cam

# ---------------------------------------------------------------- 箱
box_objs = {}
film = None
for b in meta["boxes"]:
    objs = []
    M = b["matrix"]
    mtop = mat_cardboard("top_%02d.png" % b["id"], "gloss_%02d.png" % b["id"])
    objs.append(import_obj(EXP / ("top_%02d.obj" % b["id"]), mtop, M))
    for k, name in enumerate(b["sides"]):
        ms = mat_cardboard("side_%02d_%d.png" % (b["id"], k + 1))
        objs.append(import_obj(EXP / name, ms, M))
    if b.get("shrink"):
        film = film or mat_film()
        objs.append(import_obj(EXP / ("film_top_%02d.obj" % b["id"]), film, M))
        for name in b["film_sides"]:
            objs.append(import_obj(EXP / name, film, M))
    box_objs[b["id"]] = objs

# ---------------------------------------------------------------- コマごとに描く
scene.view_layers[0].use_pass_z = True
for fi, frame in enumerate(meta["frames"]):
    keep = set(frame)
    for bid, objs in box_objs.items():
        for o in objs:
            o.hide_render = bid not in keep
    key = "_".join("%02d" % i for i in sorted(keep))
    scene.render.filepath = str(OUT / ("rgb_%s.png" % key))
    if fi == 0:
        # 深度の確かめ: 合成ノードで Z を EXR へ
        scene.use_nodes = True
        nt = scene.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        rl = nt.nodes.new("CompositorNodeRLayers")
        comp = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(rl.outputs["Image"], comp.inputs["Image"])
        fo = nt.nodes.new("CompositorNodeOutputFile")
        fo.base_path = str(OUT)
        fo.file_slots[0].path = "depth_%s_" % key
        fo.format.file_format = "OPEN_EXR"
        fo.format.color_depth = "32"
        nt.links.new(rl.outputs["Depth"], fo.inputs[0])
    else:
        scene.use_nodes = False
    bpy.ops.render.render(write_still=True)
    print("DEPAL_RENDERED", key, flush=True)
    if fi == 0:
        # EXR を Blender の中で読み、float32 の生の配列(.npy、行 0 = 画像の上)に直す
        import glob
        import numpy as np
        for f in glob.glob(str(OUT / ("depth_%s_*.exr" % key))):
            im = bpy.data.images.load(f)
            w, h = im.size
            px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, -1)[::-1, :, 0]
            np.save(str(OUT / ("depth_%s.npy" % key)), px)
            bpy.data.images.remove(im)

# ---------------------------------------------------------------- 待ち受け(--serve): 要るコマを 1 枚ずつ受けて描く
# 4 つ目の引数が "serve" のとき、OUT/req_*.json(中身 = 残っている箱の番号の列)を待ち、描いたら消す。
# OUT/quit が置かれたら終わる。場面の読み込み(数秒)を 1 回で済ませるため。
if len(argv) > 3 and argv[3] == "serve":
    import time as _time
    scene.use_nodes = False
    print("DEPAL_SERVING", flush=True)
    while not (OUT / "quit").exists():
        reqs = sorted(OUT.glob("req_*.json"))
        if not reqs:
            _time.sleep(0.05)
            continue
        for rq in reqs:
            try:
                keep = set(json.loads(rq.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue                        # 書きかけ。次の周で読む
            for bid, objs in box_objs.items():
                for o in objs:
                    o.hide_render = bid not in keep
            key = "_".join("%02d" % i for i in sorted(keep))
            tmp = OUT / ("rgb_%s.tmp.png" % key)
            scene.render.filepath = str(tmp)
            bpy.ops.render.render(write_still=True)
            tmp.replace(OUT / ("rgb_%s.png" % key))
            rq.unlink()
            print("DEPAL_RENDERED", key, flush=True)
