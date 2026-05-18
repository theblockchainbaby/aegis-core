"""Combine the 5 small printable parts into a single multi-island STL.

Load this in Chitubox and click "Auto Arrange" — it'll detect the separate
islands and lay them out optimally on the Saturn 4 Ultra 16K bed.

Run:
    /opt/homebrew/bin/blender --background --python combine_for_chitubox.py
"""
import os

import bpy

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(THIS_DIR, "output")

# Datasheet-verified rev: bottom plate and outer skin each dominate the
# build plate so they print alone. The 7 small parts combine into one
# multi-island STL — Chitubox Auto Arrange handles the layout.
PARTS = [
    ("aegis_node_jetson_mount.stl",    0),
    ("aegis_node_respeaker_mount.stl", 140),
    ("aegis_node_speaker_baffle.stl",  320),
    ("aegis_node_mmwave_bracket.stl",  400),
    ("aegis_node_camera_bracket.stl",  460),
    ("aegis_node_xiao_mount.stl",      510),
    ("aegis_node_amp_mount.stl",       550),
]
COMBINED_NAME = "aegis_node_all_small_parts.stl"

# Clear scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

imported = []
for fname, x_offset in PARTS:
    path = os.path.join(OUT_DIR, fname)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[-1]
    obj.location.x += x_offset
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    imported.append(obj)

# Select all imported objects and join into one mesh.
bpy.ops.object.select_all(action="DESELECT")
for o in imported:
    o.select_set(True)
bpy.context.view_layer.objects.active = imported[0]
bpy.ops.object.join()
combined = bpy.context.active_object
combined.name = "Session1Combined"

# Export.
out_path = os.path.join(OUT_DIR, COMBINED_NAME)
bpy.ops.object.select_all(action="DESELECT")
combined.select_set(True)
bpy.ops.wm.stl_export(filepath=out_path, export_selected_objects=True, ascii_format=False)
print(f">>> Wrote {out_path}")
