"""Open the three Aegis Node shell STLs in one Blender scene for review.

Run:
    /opt/homebrew/bin/blender --python open_in_blender.py
"""
import os

import bpy

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(THIS_DIR, "output")

# Clear default cube/camera/light.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

parts = [
    ("aegis_node_outer_skin.stl",      (0.85, 0.85, 0.90, 0.18)),  # translucent skin
    ("aegis_node_bottom_plate.stl",    (0.15, 0.15, 0.18, 1.00)),  # dark base
    ("aegis_node_jetson_mount.stl",    (0.30, 0.55, 0.80, 1.00)),  # blue Jetson plate
    ("aegis_node_xiao_mount.stl",      (0.85, 0.40, 0.30, 1.00)),  # orange XIAO plate
    ("aegis_node_speaker_baffle.stl",  (0.55, 0.50, 0.40, 1.00)),  # tan speaker
    ("aegis_node_mmwave_bracket.stl",  (0.40, 0.70, 0.45, 1.00)),  # green mmWave
]

for fname, rgba in parts:
    path = os.path.join(OUT, fname)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[-1]
    mat = bpy.data.materials.new(name=fname)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    if rgba[3] < 1.0:
        bsdf.inputs["Alpha"].default_value = rgba[3]
        mat.blend_method = "BLEND"
    obj.data.materials.append(mat)

# Camera looking down at the wedge from front-right.
bpy.ops.object.camera_add(location=(220, -160, 140), rotation=(1.1, 0, 0.95))
cam = bpy.context.active_object
bpy.context.scene.camera = cam

# Sun light.
bpy.ops.object.light_add(type="SUN", location=(50, -50, 180))
bpy.context.active_object.data.energy = 3.0

# Frame the geometry in 3D viewport.
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        for region in area.regions:
            if region.type == "WINDOW":
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_all(center=True)
                break
        break

print(">>> Loaded all three shell STLs.")
