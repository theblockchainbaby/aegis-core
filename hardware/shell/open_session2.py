"""Open the session-2 combined STL (3 new component mounts) in Blender."""
import os

import bpy

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "output", "aegis_node_session2_new_mounts.stl")
bpy.ops.wm.stl_import(filepath=path)

for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        for region in area.regions:
            if region.type == "WINDOW":
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_all(center=True)
                break
        break
print(">>> Loaded session-2 combined STL.")
