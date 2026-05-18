"""Render a clean studio shot of each printable part as PNG.

Run:
    /opt/homebrew/bin/blender --background --python render_parts.py
"""
import math
import os

import bpy

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(THIS_DIR, "output")
RENDERS_DIR = os.path.join(OUT_DIR, "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)

PARTS = [
    "aegis_node_outer_skin.stl",
    "aegis_node_bottom_plate.stl",
    "aegis_node_jetson_mount.stl",
    "aegis_node_xiao_mount.stl",
    "aegis_node_speaker_baffle.stl",
    "aegis_node_mmwave_bracket.stl",
    "aegis_node_respeaker_mount.stl",
    "aegis_node_camera_bracket.stl",
    "aegis_node_amp_mount.stl",
]


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials,
                  bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            block.remove(item)


def setup_scene(target):
    """Frame *target* with a 3/4 camera and studio lighting."""
    # Center target on world origin.
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    target.location = (0, 0, 0)

    # Smooth shading.
    bpy.ops.object.shade_smooth()

    # Material — matte light gray.
    mat = bpy.data.materials.new(name="StudioMatte")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.78, 0.78, 0.80, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
    # Metallic socket may not exist in some BSDF revs; guard.
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.05
    target.data.materials.clear()
    target.data.materials.append(mat)

    # Compute camera distance from bounding box.
    dims = target.dimensions
    extent = max(dims.x, dims.y, dims.z)
    cam_dist = extent * 2.4

    # Camera at 3/4 view.
    bpy.ops.object.camera_add(
        location=(cam_dist * 0.85, -cam_dist * 0.85, cam_dist * 0.55),
        rotation=(math.radians(60), 0, math.radians(45)),
    )
    cam = bpy.context.active_object
    cam.data.lens = 60  # mm, mild telephoto for less distortion
    bpy.context.scene.camera = cam

    # Key light.
    bpy.ops.object.light_add(type="AREA", location=(cam_dist, -cam_dist, cam_dist))
    key = bpy.context.active_object
    key.data.energy = 1200
    key.data.size = max(extent * 2, 100)
    key.rotation_euler = (math.radians(45), math.radians(20), math.radians(45))

    # Fill light (softer, opposite side).
    bpy.ops.object.light_add(type="AREA", location=(-cam_dist, cam_dist * 0.5, cam_dist * 0.7))
    fill = bpy.context.active_object
    fill.data.energy = 400
    fill.data.size = max(extent * 2, 100)

    # Soft top-down rim.
    bpy.ops.object.light_add(type="SUN", location=(0, 0, cam_dist))
    sun = bpy.context.active_object
    sun.data.energy = 1.0

    # Ground plane for soft shadow.
    bpy.ops.mesh.primitive_plane_add(size=extent * 6, location=(0, 0, -dims.z / 2 - 0.5))
    plane = bpy.context.active_object
    pmat = bpy.data.materials.new(name="Ground")
    pmat.use_nodes = True
    pmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.95, 0.95, 0.96, 1.0)
    pmat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    plane.data.materials.append(pmat)


def configure_render(out_path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False  # opaque white-ish ground
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 750
    scene.render.resolution_percentage = 100
    scene.render.filepath = out_path


def render_one(stl_filename):
    clear_scene()
    stl_path = os.path.join(OUT_DIR, stl_filename)
    bpy.ops.wm.stl_import(filepath=stl_path)
    target = bpy.context.selected_objects[-1]

    setup_scene(target)

    out_png = os.path.join(RENDERS_DIR, stl_filename.replace(".stl", ".png"))
    configure_render(out_png)
    bpy.ops.render.render(write_still=True)
    print(f"    rendered {out_png}")


def main():
    for f in PARTS:
        print(f">>> Rendering {f}...")
        render_one(f)
    print(">>> Done.")


if __name__ == "__main__":
    main()
