# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Blender(Cycles)で混載パレットとロボット(UR10e、Menagerie)を斜めから描く動画のコマ。Blender の中で走らせる。

    blender --background --factory-startup --python tools/depal_blender_video.py -- <export_dir> <out_dir> <video.json> [samples] [start:end:step]

``export_dir`` は ``depal_export.export_scene`` が書いた場所。``scene.json`` の ``frames`` の
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
VIDEO = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
SAMPLES = int(argv[3]) if len(argv) > 3 else 16
FRAME_RANGE = [int(v) for v in argv[4].split(":")] if len(argv) > 4 else [0, len(VIDEO["frames"]), 1]
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
scene.render.resolution_x = VIDEO.get("width", 960)
scene.render.resolution_y = VIDEO.get("height", 540)
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
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
bpy.ops.mesh.primitive_plane_add(size=30.0, location=(0, 0, 0))
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


# ---------------------------------------------------------------- 箱(全部読み込み、コマごとに姿勢と表示を決める)
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


def plain(name, rgba, rough=0.45, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


# ロボット: 色は無地(灰と白)。メーカーの配色にしない
robot_mats = {"urblue": plain("arm_white", (0.78, 0.79, 0.80, 1), 0.35),
              "linkgray": plain("arm_link", (0.70, 0.71, 0.72, 1), 0.35),
              "jointgray": plain("arm_joint", (0.23, 0.24, 0.25, 1), 0.5),
              "black": plain("arm_black", (0.04, 0.04, 0.045, 1), 0.6)}
robot = {}
for mm in VIDEO["meshes"]:
    bpy.ops.wm.obj_import(filepath=mm["obj"], forward_axis="Y", up_axis="Z")
    o = bpy.context.selected_objects[0]
    o.data.materials.clear()
    o.data.materials.append(robot_mats.get(mm["material"], robot_mats["linkgray"]))
    for p in o.data.polygons:
        p.use_smooth = True
    robot[mm["name"]] = o

steel = plain("steel", (0.55, 0.56, 0.58, 1), 0.3, 0.9)
rubber = plain("rubber", (0.025, 0.025, 0.03, 1), 0.7)
paint = plain("paint", (0.86, 0.62, 0.10, 1), 0.45)             # 台座・レールの黄色い塗装
tool = VIDEO["tool"]
bpy.ops.mesh.primitive_cylinder_add(radius=tool["shaft"]["radius"], depth=tool["shaft"]["length"])
shaft = bpy.context.active_object
shaft.data.materials.append(steel)
shaft.data.transform(Matrix.Translation((0, 0, tool["shaft"]["length"] / 2)))
px, py, pz = tool["pad"]["size"]
bpy.ops.mesh.primitive_cube_add(size=1.0)
pad = bpy.context.active_object
pad.data.transform(Matrix.Diagonal((px, py, pz, 1.0)))
pad.data.transform(Matrix.Translation((0, 0, tool["length"] - pz / 2)))
pad.data.materials.append(rubber)

base = VIDEO["base"]
ps = base.get("pedestal_size", [0.24, 0.24])
ped = add_cube("pedestal", (base["x"], 0.0, base["z"] / 2), (ps[0], ps[1], base["z"]), paint)
rail = base.get("rail")
if rail:
    L = rail["max"] - rail["min"] + ps[1]
    add_cube("rail", (base["x"], (rail["max"] + rail["min"]) / 2, 0.06), (ps[0] + 0.16, L, 0.12), steel)
conv = VIDEO["conveyor"]
cx, cy, cz = conv["center"]
add_cube("belt", (cx, cy, cz - 0.01), (conv["width"], conv["length"], 0.02), rubber)
add_cube("frame_l", (cx - conv["width"] / 2 - 0.03, cy, cz - 0.05), (0.06, conv["length"], 0.12), steel)
add_cube("frame_r", (cx + conv["width"] / 2 + 0.03, cy, cz - 0.05), (0.06, conv["length"], 0.12), steel)
for sx in (-1, 1):
    for sy in (-1, 1):
        add_cube("leg", (cx + sx * (conv["width"] / 2), cy + sy * (conv["length"] / 2 - 0.05), (cz - 0.1) / 2),
                 (0.05, 0.05, cz - 0.1), steel)

# 観察のカメラ(斜め上)
vc = VIDEO["camera"]
cdat = bpy.data.cameras.new("view")
cdat.lens = vc.get("lens", 28.0)
vcam = bpy.data.objects.new("view", cdat)
scene.collection.objects.link(vcam)
from mathutils import Vector
vcam.location = Vector(vc["pos"])
direction = Vector(vc["target"]) - vcam.location
vcam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
scene.camera = vcam


def pose_matrix(p):
    from mathutils import Quaternion
    q = Quaternion((p[3], p[4], p[5], p[6]))
    M = q.to_matrix().to_4x4()
    M.translation = Vector(p[:3])
    return M


start, end, step = FRAME_RANGE
for fi in range(start, min(end, len(VIDEO["frames"])), step):
    fr = VIDEO["frames"][fi]
    for name, p in fr["parts"].items():
        robot[name].matrix_world = pose_matrix(p)
    Mf = pose_matrix(fr["flange_pose"])
    shaft.matrix_world = Mf
    pad.matrix_world = Mf
    ped.location = (base["x"], fr.get("rail_y", 0.0), base["z"] / 2)
    for bid, objs in box_objs.items():
        m = fr["boxes"].get(str(bid))
        for o in objs:
            o.hide_render = m is None
            if m is not None:
                o.matrix_world = Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    scene.render.filepath = str(OUT / ("vid_%05d.png" % fi))
    bpy.ops.render.render(write_still=True)
    print("DEPAL_VIDEO_FRAME", fi, flush=True)
