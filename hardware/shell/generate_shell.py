"""
Aegis Core v1 — Shell generator.

Builds the three printable parts of The Node's wedge shell and exports
STLs to output/:

  - aegis_node_outer_skin.stl     # the visible 110x90x75mm tilted wedge
  - aegis_node_inner_cage.stl     # PETG skeleton with component cavities
  - aegis_node_bottom_plate.stl   # silicone pad recess + cable relief + status LED

The wedge has its front face tilted 15 degrees back from vertical — front
edge at Y=0 stays low, top edge of the front face sits at Y=FACE_TILT_Y.
Components are placed in the cage with COMPONENT_CLEARANCE per face.

Run headless:
    /opt/homebrew/bin/blender --background --python generate_shell.py

Or open Blender, switch to Scripting workspace, paste this file, Run.
"""

import os
import sys
from math import radians

import bmesh
import bpy

# Make `parameters` importable when run via `blender --background --python`
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

import parameters as P

# ── Scene helpers ──────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


def add_cube(name, size_xyz, location, rotation_euler=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation_euler)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size_xyz
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def add_cyl(name, radius, depth, location, rotation_euler=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, rotation=rotation_euler, vertices=64
    )
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new(name=f"bool_{cutter.name}", type="BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


# ── Geometry ───────────────────────────────────────────────────────────

def build_wedge_solid(name, w=P.SHELL_W, d=P.SHELL_D, h=P.SHELL_H,
                       tilt_y=P.FACE_TILT_Y,
                       taper_x=P.TOP_TAPER_X, taper_y_rear=P.TOP_TAPER_Y):
    """Build a tapered, tilted-face wedge.

    Base is the full w x d footprint at Z=0. The top edge is inset by
    *taper_x* per side and the rear of the top is brought forward by
    *taper_y_rear*, giving a softly shouldered silhouette. The front-top
    edge slides back by *tilt_y* so the face leans 15° back (spec §3.4).
    Origin at bottom-front-left corner.
    """
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(w / 2, d / 2, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        at_top = abs(v.co.z - h) < 1e-5
        at_front = abs(v.co.y - 0.0) < 1e-5
        at_rear = abs(v.co.y - d) < 1e-5
        at_left = abs(v.co.x - 0.0) < 1e-5
        at_right = abs(v.co.x - w) < 1e-5
        if at_top:
            # Inset top X per side
            if at_left:
                v.co.x += taper_x
            if at_right:
                v.co.x -= taper_x
            # Front-top edge slides back by tilt_y; rear-top edge moves forward by taper_y_rear
            if at_front:
                v.co.y = tilt_y
            if at_rear:
                v.co.y = d - taper_y_rear
    bm.to_mesh(me)
    bm.free()
    return obj


def apply_bevel(obj, width, segments=P.FILLET_SEGMENTS, profile=0.7, angle_deg=30):
    """Round all sharp convex edges over *angle_deg* with a single bevel."""
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="ModernBevel", type="BEVEL")
    mod.width = width
    mod.segments = segments
    mod.profile = profile
    mod.limit_method = "ANGLE"
    mod.angle_limit = radians(angle_deg)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def shade_smooth(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    # Auto-smooth so the flat faces stay flat and only the beveled edges look round.
    if hasattr(obj.data, "use_auto_smooth"):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = radians(40)


def clean_mesh(obj):
    """Heal small non-manifold artifacts left by bevel+boolean stacks."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.fill_holes(sides=8)
    bpy.ops.object.mode_set(mode="OBJECT")


def face_y_at(z, h=P.SHELL_H, tilt_y=P.FACE_TILT_Y):
    """Return the Y coordinate of the tilted front face at height *z*."""
    return tilt_y * (z / h)


def add_component_cavity(name, size, location):
    """Component cutter, expanded by 2 * COMPONENT_CLEARANCE per axis."""
    c = P.COMPONENT_CLEARANCE
    sx, sy, sz = size
    return add_cube(
        name,
        (sx + 2 * c, sy + 2 * c, sz + 2 * c),
        location=(location[0], location[1], location[2]),
    )


# ── Three parts ────────────────────────────────────────────────────────

def build_outer_skin():
    skin = build_wedge_solid("OuterSkin")
    # Bevel BEFORE hollowing so the outer surface gets soft edges and the
    # inner hollow can mirror those radii for a parallel wall.
    apply_bevel(skin, width=P.SKIN_FILLET)

    t = P.OUTER_SKIN_THICK
    inner_h = P.SHELL_H - t
    inner = build_wedge_solid(
        "OuterSkinHollow",
        w=P.SHELL_W - 2 * t,
        d=P.SHELL_D - 2 * t,
        h=inner_h,
        tilt_y=P.FACE_TILT_Y * inner_h / P.SHELL_H,
        taper_x=P.TOP_TAPER_X,
        taper_y_rear=P.TOP_TAPER_Y,
    )
    inner.location = (t, t, t)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    apply_bevel(inner, width=P.SKIN_FILLET)  # same radius so walls stay parallel
    boolean(skin, inner)

    # Front face cutout for frosted polycarb panel.
    # The front face is the tilted plane from (any x, FACE_TILT_Y, SHELL_H)
    # down to (any x, 0, 0)+(perp). Approximate the cutout as a box rotated
    # by -FACE_TILT_DEG about X, positioned so it slices through the face.
    cut_w = P.FACE_CUTOUT_W
    cut_h = P.FACE_CUTOUT_H
    cut_thick = P.OUTER_SKIN_THICK + 2 * P.BOOLEAN_OVERSHOOT
    face_cut_z = P.SHELL_H / 2 + P.FACE_CUTOUT_MARGIN_BOTTOM / 2
    face_cut = add_cube(
        "FaceCutout",
        (cut_w, cut_thick, cut_h),
        location=(P.SHELL_W / 2, face_y_at(face_cut_z), face_cut_z),
        rotation_euler=(radians(P.FACE_TILT_DEG), 0, 0),
    )
    boolean(skin, face_cut)

    # Camera window — smaller rectangle below the frosted panel.
    cam_cut_z = P.CAMERA_WIN_OFFSET_FROM_BOTTOM + P.CAMERA_WIN_H / 2
    cam_cut = add_cube(
        "CameraCutout",
        (P.CAMERA_WIN_W, cut_thick, P.CAMERA_WIN_H),
        location=(P.SHELL_W / 2, face_y_at(cam_cut_z), cam_cut_z),
        rotation_euler=(radians(P.FACE_TILT_DEG), 0, 0),
    )
    boolean(skin, cam_cut)

    # Rear barrel jack hole.
    jack = add_cyl(
        "BarrelJackHole",
        radius=P.BARREL_JACK_DIA / 2,
        depth=P.OUTER_SKIN_THICK + 2 * P.BOOLEAN_OVERSHOOT,
        location=(P.SHELL_W / 2, P.SHELL_D - P.OUTER_SKIN_THICK / 2, P.BARREL_JACK_INSET_Z),
        rotation_euler=(radians(90), 0, 0),
    )
    boolean(skin, jack)

    # USB-C service port (hidden under skin seam, on left side, low and rear).
    usb = add_cube(
        "USBCHole",
        (P.OUTER_SKIN_THICK + 2 * P.BOOLEAN_OVERSHOOT, P.USB_C_W, P.USB_C_H),
        location=(P.OUTER_SKIN_THICK / 2, P.SHELL_D - 18.0, 12.0),
    )
    boolean(skin, usb)

    # Drain holes in the rear of the top surface — vent trapped resin
    # during MSLA print. Hidden when viewed from the front.
    rear_top_y = P.SHELL_D - P.TOP_TAPER_Y - P.DRAIN_HOLE_INSET_FROM_REAR
    total_span = (P.DRAIN_HOLE_COUNT - 1) * P.DRAIN_HOLE_SPACING
    drain_x0 = P.SHELL_W / 2 - total_span / 2
    for i in range(P.DRAIN_HOLE_COUNT):
        drain = add_cyl(
            f"DrainHole_{i}",
            radius=P.DRAIN_HOLE_DIA / 2,
            depth=P.OUTER_SKIN_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(drain_x0 + i * P.DRAIN_HOLE_SPACING, rear_top_y, P.SHELL_H - P.OUTER_SKIN_THICK / 2),
        )
        boolean(skin, drain)

    # Four internal corner bosses — these are what the bottom plate's M3
    # screws bite into. Self-tap pilot holes (Ø2.7mm) so M3 screws cut
    # their own threads in the resin.
    inset = P.SCREW_BOSS_OD
    boss_corners = [
        (inset, inset),
        (P.SHELL_W - inset, inset),
        (inset, P.SHELL_D - inset),
        (P.SHELL_W - inset, P.SHELL_D - inset),
    ]
    for cx, cy in boss_corners:
        boss = add_cyl(
            f"SkinBoss_{int(cx)}_{int(cy)}",
            radius=P.SCREW_BOSS_OD / 2,
            depth=P.SCREW_BOSS_H,
            location=(cx, cy, P.BOTTOM_THICK + P.SCREW_BOSS_H / 2),
        )
        mod = skin.modifiers.new(name=f"u_boss_{cx}_{cy}", type="BOOLEAN")
        mod.operation = "UNION"; mod.object = boss; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = skin
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(boss, do_unlink=True)

        pilot = add_cyl(
            f"SkinPilot_{int(cx)}_{int(cy)}",
            radius=P.M3_PILOT_DIA / 2,
            depth=P.SCREW_BOSS_H,
            location=(cx, cy, P.BOTTOM_THICK + P.SCREW_BOSS_H / 2),
        )
        boolean(skin, pilot)

    skin.location = (0, 0, 0)
    clean_mesh(skin)
    shade_smooth(skin)
    return skin


def build_jetson_mount_plate():
    """Plate that the Jetson Orin Nano Super dev kit bolts to.

    Core (99 x 72 mm) is sized to tuck between the skin's 4 internal
    corner bosses. Four M2.5 standoffs at the carrier's 93 x 72 mm hole
    pattern. Two side tabs at left/right edge midpoints carry the M3
    bolt-down holes (corners are unavailable due to the boss clearance
    requirement).
    """
    plate = add_cube(
        "JetsonPlate",
        (P.JETSON_PLATE_W, P.JETSON_PLATE_D, P.JETSON_PLATE_THICK),
        location=(P.JETSON_PLATE_W / 2, P.JETSON_PLATE_D / 2, P.JETSON_PLATE_THICK / 2),
    )

    # Side tabs for M3 bolt-down (extend outward at left/right edge midpoints).
    tab_cy = P.JETSON_PLATE_D / 2
    for sx in [-P.JETSON_TAB_W / 2, P.JETSON_PLATE_W + P.JETSON_TAB_W / 2]:
        tab = add_cube(
            f"JetsonTab_{int(sx)}",
            (P.JETSON_TAB_W, P.JETSON_TAB_D, P.JETSON_PLATE_THICK),
            location=(sx, tab_cy, P.JETSON_PLATE_THICK / 2),
        )
        mod = plate.modifiers.new(name=f"utab_{sx}", type="BOOLEAN")
        mod.operation = "UNION"; mod.object = tab; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = plate
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tab, do_unlink=True)

    apply_bevel(plate, width=1.8, segments=6)

    # 4 standoffs at the M2.5 hole pattern, centered on the core plate.
    cx0 = (P.JETSON_PLATE_W - P.JETSON_HOLE_PATTERN_X) / 2
    cy0 = (P.JETSON_PLATE_D - P.JETSON_HOLE_PATTERN_Y) / 2
    standoff_positions = [
        (cx0, cy0),
        (cx0 + P.JETSON_HOLE_PATTERN_X, cy0),
        (cx0, cy0 + P.JETSON_HOLE_PATTERN_Y),
        (cx0 + P.JETSON_HOLE_PATTERN_X, cy0 + P.JETSON_HOLE_PATTERN_Y),
    ]
    for x, y in standoff_positions:
        post = add_cyl(
            f"JetsonStandoff_{int(x)}_{int(y)}",
            radius=P.JETSON_STANDOFF_OD / 2,
            depth=P.JETSON_STANDOFF_H,
            location=(x, y, P.JETSON_PLATE_THICK + P.JETSON_STANDOFF_H / 2),
        )
        mod = plate.modifiers.new(name=f"u_{x}_{y}", type="BOOLEAN")
        mod.operation = "UNION"; mod.object = post; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = plate
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(post, do_unlink=True)

        thru = add_cyl(
            f"JetsonM25_{int(x)}_{int(y)}",
            radius=P.JETSON_M25_HOLE / 2,
            depth=P.JETSON_PLATE_THICK + P.JETSON_STANDOFF_H + 2 * P.BOOLEAN_OVERSHOOT,
            location=(x, y, (P.JETSON_PLATE_THICK + P.JETSON_STANDOFF_H) / 2),
        )
        boolean(plate, thru)

    # M3 bolt-down holes through the side tabs (centered on tab in Y).
    for cx in [-P.JETSON_TAB_W / 2, P.JETSON_PLATE_W + P.JETSON_TAB_W / 2]:
        h = add_cyl(
            f"JetsonM3Tab_{int(cx)}",
            radius=P.M3_HOLE_DIA / 2,
            depth=P.JETSON_PLATE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(cx, tab_cy, P.JETSON_PLATE_THICK / 2),
        )
        boolean(plate, h)

    clean_mesh(plate)
    shade_smooth(plate)
    return plate


def build_xiao_mount_plate():
    """Friction-fit pocket for the Seeed XIAO RP2040.

    The XIAO is castellated SMT-only — no mounting holes. The board drops
    into a snug rectangular pocket; the USB-C end has a notch so the
    cable can plug in without lifting the board out.
    """
    pocket_w = P.XIAO_BOARD_W + 2 * P.XIAO_POCKET_TOL
    pocket_d = P.XIAO_BOARD_D + 2 * P.XIAO_POCKET_TOL
    outer_w = pocket_w + 2 * P.XIAO_POCKET_WALL
    outer_d = pocket_d + 2 * P.XIAO_POCKET_WALL
    outer_h = P.XIAO_BASE_THICK + P.XIAO_BOARD_H

    body = add_cube(
        "XIAOPocketBody",
        (outer_w, outer_d, outer_h),
        location=(outer_w / 2, outer_d / 2, outer_h / 2),
    )

    # Pocket cavity.
    cavity = add_cube(
        "XIAOPocketCavity",
        (pocket_w, pocket_d, P.XIAO_BOARD_H + P.BOOLEAN_OVERSHOOT),
        location=(outer_w / 2, outer_d / 2, P.XIAO_BASE_THICK + P.XIAO_BOARD_H / 2),
    )
    boolean(body, cavity)

    # USB-C cable notch on one short edge (the X+ side).
    usb_notch = add_cube(
        "XIAOUSBNotch",
        (P.XIAO_USB_NOTCH_D + P.BOOLEAN_OVERSHOOT, P.XIAO_USB_NOTCH_W, P.XIAO_BOARD_H + P.BOOLEAN_OVERSHOOT),
        location=(outer_w - P.XIAO_USB_NOTCH_D / 2 + P.BOOLEAN_OVERSHOOT / 2,
                  outer_d / 2,
                  P.XIAO_BASE_THICK + P.XIAO_BOARD_H / 2),
    )
    boolean(body, usb_notch)

    # 2 M3 bolt-down holes on the floor of the pocket body (corners that
    # don't conflict with the pocket cavity).
    for cx, cy in [(2.5, 2.5), (outer_w - 2.5, outer_d - 2.5)]:
        if not (P.XIAO_POCKET_WALL < cx < outer_w - P.XIAO_POCKET_WALL and
                P.XIAO_POCKET_WALL < cy < outer_d - P.XIAO_POCKET_WALL):
            h = add_cyl(
                f"XIAOFix_{int(cx)}_{int(cy)}",
                radius=P.M3_HOLE_DIA / 2,
                depth=P.XIAO_BASE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
                location=(cx, cy, P.XIAO_BASE_THICK / 2),
            )
            boolean(body, h)

    body.name = "XIAOPocket"
    apply_bevel(body, width=1.0, segments=6)
    clean_mesh(body)
    shade_smooth(body)
    return body


def build_speaker_baffle():
    """Sealed chamber + baffle for the Dayton CE32A-4 (or equivalent
    32x32mm square-frame driver). Baffle has a Ø20mm cone cutout (allow
    ~1mm clearance over the Ø19 cone) and a 28mm-square 4-hole pattern
    for M2 driver screws. Chamber is open at the rear for foam install."""
    w, d, h = P.SPEAKER_CHAMBER_W, P.SPEAKER_CHAMBER_D, P.SPEAKER_CHAMBER_H
    wall = P.SPEAKER_CHAMBER_WALL
    bt = P.SPEAKER_BAFFLE_THICK

    outer = add_cube(
        "SpeakerOuter",
        (w, d, h + bt),
        location=(w / 2, d / 2, (h + bt) / 2),
    )
    hollow = add_cube(
        "SpeakerHollow",
        (w - 2 * wall, d - 2 * wall, h + P.BOOLEAN_OVERSHOOT),
        location=(w / 2, d / 2, bt + h / 2 + P.BOOLEAN_OVERSHOOT / 2),
    )
    boolean(outer, hollow)

    # Ø20 cone aperture.
    drv = add_cyl(
        "DriverHole",
        radius=P.SPEAKER_DRIVER_DIA / 2,
        depth=bt + 2 * P.BOOLEAN_OVERSHOOT,
        location=(w / 2, d / 2, bt / 2),
    )
    boolean(outer, drv)

    # 4 M2 bolt holes at the corners of a 28x28 square pattern around the cone.
    half = P.SPEAKER_BOLT_PATTERN / 2
    for dx, dy in [(-half, -half), (half, -half), (-half, half), (half, half)]:
        bh = add_cyl(
            f"SpeakerBolt_{dx}_{dy}",
            radius=P.SPEAKER_BOLT_HOLE_DIA / 2,
            depth=bt + 2 * P.BOOLEAN_OVERSHOOT,
            location=(w / 2 + dx, d / 2 + dy, bt / 2),
        )
        boolean(outer, bh)

    # Mounting tabs at the bottom (extend the bottom outward on left and right).
    tab_w = P.SPEAKER_TAB_W
    tab_t = 3.0
    for sx in [-tab_w / 2, w + tab_w / 2]:
        tab = add_cube(
            f"SpkTab_{int(sx)}",
            (tab_w, d, tab_t),
            location=(sx, d / 2, tab_t / 2),
        )
        mod = outer.modifiers.new(name=f"utab_{sx}", type="BOOLEAN")
        mod.operation = "UNION"; mod.object = tab; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = outer
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tab, do_unlink=True)
        # M3 hole through the tab center.
        cx = sx
        cy = d / 2
        hole = add_cyl(
            f"SpkTabHole_{int(sx)}",
            radius=P.M3_HOLE_DIA / 2,
            depth=tab_t + 2 * P.BOOLEAN_OVERSHOOT,
            location=(cx, cy, tab_t / 2),
        )
        boolean(outer, hole)

    outer.name = "SpeakerBaffle"
    apply_bevel(outer, width=1.5, segments=6)
    clean_mesh(outer)
    shade_smooth(outer)
    return outer


def build_mmwave_bracket():
    """Vertical plate holding the MR24HPC1 mmWave board sensor-forward."""
    plate = add_cube(
        "MMWavePlate",
        (P.MMWAVE_PLATE_W, P.MMWAVE_PLATE_THICK, P.MMWAVE_PLATE_H),
        location=(P.MMWAVE_PLATE_W / 2, P.MMWAVE_PLATE_THICK / 2, P.MMWAVE_PLATE_H / 2 + P.MMWAVE_BASE_THICK),
    )

    # Base tab — runs perpendicular along the bottom for screwing to floor.
    base = add_cube(
        "MMWaveBase",
        (P.MMWAVE_BASE_W, P.MMWAVE_BASE_D, P.MMWAVE_BASE_THICK),
        location=(P.MMWAVE_PLATE_W / 2, P.MMWAVE_BASE_D / 2 - P.MMWAVE_PLATE_THICK / 2 + P.MMWAVE_PLATE_THICK / 2, P.MMWAVE_BASE_THICK / 2),
    )
    mod = plate.modifiers.new(name="ubase", type="BOOLEAN")
    mod.operation = "UNION"; mod.object = base; mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(base, do_unlink=True)

    # 4 M2 mounting holes for the MR24HPC1 PCB (Ø2.2mm in board → Ø2.4 clearance).
    cx0 = (P.MMWAVE_PLATE_W - P.MMWAVE_HOLE_PATTERN_X) / 2
    cz0 = P.MMWAVE_BASE_THICK + (P.MMWAVE_PLATE_H - P.MMWAVE_HOLE_PATTERN_Y) / 2
    for x in [cx0, cx0 + P.MMWAVE_HOLE_PATTERN_X]:
        for z in [cz0, cz0 + P.MMWAVE_HOLE_PATTERN_Y]:
            h = add_cyl(
                f"MMWaveHole_{int(x)}_{int(z)}",
                radius=P.MMWAVE_M2_HOLE / 2,
                depth=P.MMWAVE_PLATE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
                location=(x, P.MMWAVE_PLATE_THICK / 2, z),
                rotation_euler=(radians(90), 0, 0),
            )
            boolean(plate, h)

    # 2 M3 holes through the base tab (left and right) for bolting to floor.
    for bx in [8.0, P.MMWAVE_BASE_W - 8.0]:
        h = add_cyl(
            f"MMWaveBaseHole_{int(bx)}",
            radius=P.M3_HOLE_DIA / 2,
            depth=P.MMWAVE_BASE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(bx, P.MMWAVE_BASE_D / 2, P.MMWAVE_BASE_THICK / 2),
        )
        boolean(plate, h)

    plate.name = "MMWaveBracket"
    apply_bevel(plate, width=1.2, segments=6)
    clean_mesh(plate)
    shade_smooth(plate)
    return plate


def build_respeaker_mount():
    """Long strip plate for the ReSpeaker 4-Mic Linear Array.

    Manufacturer DXF: 157.48mm-long PCB with 2 explicit Ø3.0 mounting
    holes spaced 49.022mm center-to-center. Plate is 165mm long to hold
    the board with margin; 2 Ø5 standoffs match the hole pitch. Two M3
    bolt-down holes at the ends of the plate attach to the bottom plate.
    """
    plate = add_cube(
        "ReSpeakerPlate",
        (P.RESPEAKER_PLATE_W, P.RESPEAKER_PLATE_D, P.RESPEAKER_PLATE_THICK),
        location=(P.RESPEAKER_PLATE_W / 2, P.RESPEAKER_PLATE_D / 2, P.RESPEAKER_PLATE_THICK / 2),
    )
    apply_bevel(plate, width=1.5, segments=6)

    # 2 standoffs centered on the plate, at the array's 49.022mm pitch.
    cx_center = P.RESPEAKER_PLATE_W / 2
    cy = P.RESPEAKER_PLATE_D / 2
    for sx in [cx_center - P.RESPEAKER_HOLE_PITCH / 2,
               cx_center + P.RESPEAKER_HOLE_PITCH / 2]:
        post = add_cyl(
            f"ReSpkStand_{int(sx)}",
            radius=P.RESPEAKER_STANDOFF_OD / 2,
            depth=P.RESPEAKER_STANDOFF_H,
            location=(sx, cy, P.RESPEAKER_PLATE_THICK + P.RESPEAKER_STANDOFF_H / 2),
        )
        mod = plate.modifiers.new(name=f"u_{sx}", type="BOOLEAN")
        mod.operation = "UNION"; mod.object = post; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = plate
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(post, do_unlink=True)
        thru = add_cyl(
            f"ReSpkM3_{int(sx)}",
            radius=P.RESPEAKER_M3_HOLE / 2,
            depth=P.RESPEAKER_PLATE_THICK + P.RESPEAKER_STANDOFF_H + 2 * P.BOOLEAN_OVERSHOOT,
            location=(sx, cy, (P.RESPEAKER_PLATE_THICK + P.RESPEAKER_STANDOFF_H) / 2),
        )
        boolean(plate, thru)

    # 2 M3 bolt-down holes near each end of the plate.
    for cx in [6.0, P.RESPEAKER_PLATE_W - 6.0]:
        h = add_cyl(
            f"ReSpkFix_{int(cx)}",
            radius=P.M3_HOLE_DIA / 2,
            depth=P.RESPEAKER_PLATE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(cx, cy, P.RESPEAKER_PLATE_THICK / 2),
        )
        boolean(plate, h)

    clean_mesh(plate)
    shade_smooth(plate)
    return plate


def build_camera_bracket():
    """Vertical bracket holding the IMX219 camera behind the camera window.

    Like the mmWave bracket but smaller, with a central lens-clearance hole.
    """
    plate = add_cube(
        "CameraPlate",
        (P.CAMERA_PLATE_W, P.CAMERA_PLATE_THICK, P.CAMERA_PLATE_H),
        location=(P.CAMERA_PLATE_W / 2, P.CAMERA_PLATE_THICK / 2, P.CAMERA_PLATE_H / 2 + P.CAMERA_BASE_THICK),
    )

    # Base tab perpendicular at the bottom.
    base = add_cube(
        "CameraBase",
        (P.CAMERA_BASE_W, P.CAMERA_BASE_D, P.CAMERA_BASE_THICK),
        location=(P.CAMERA_PLATE_W / 2, P.CAMERA_BASE_D / 2 - P.CAMERA_PLATE_THICK / 2 + P.CAMERA_PLATE_THICK / 2, P.CAMERA_BASE_THICK / 2),
    )
    mod = plate.modifiers.new(name="ubase", type="BOOLEAN")
    mod.operation = "UNION"; mod.object = base; mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(base, do_unlink=True)

    # 4 M2 holes for the camera PCB at its hole pattern.
    cx0 = (P.CAMERA_PLATE_W - P.CAMERA_HOLE_PATTERN_X) / 2
    cz0 = P.CAMERA_BASE_THICK + (P.CAMERA_PLATE_H - P.CAMERA_HOLE_PATTERN_Y) / 2
    for x in [cx0, cx0 + P.CAMERA_HOLE_PATTERN_X]:
        for z in [cz0, cz0 + P.CAMERA_HOLE_PATTERN_Y]:
            h = add_cyl(
                f"CamHole_{int(x)}_{int(z)}",
                radius=P.CAMERA_M2_HOLE / 2,
                depth=P.CAMERA_PLATE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
                location=(x, P.CAMERA_PLATE_THICK / 2, z),
                rotation_euler=(radians(90), 0, 0),
            )
            boolean(plate, h)

    # Central lens clearance hole so the bracket doesn't cover the sensor.
    lens = add_cyl(
        "LensClearance",
        radius=P.CAMERA_LENS_HOLE_DIA / 2,
        depth=P.CAMERA_PLATE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
        location=(P.CAMERA_PLATE_W / 2, P.CAMERA_PLATE_THICK / 2,
                  P.CAMERA_BASE_THICK + P.CAMERA_PLATE_H / 2),
        rotation_euler=(radians(90), 0, 0),
    )
    boolean(plate, lens)

    # 2 M3 base-tab holes.
    for bx in [6.0, P.CAMERA_BASE_W - 6.0]:
        h = add_cyl(
            f"CamBaseFix_{int(bx)}",
            radius=P.M3_HOLE_DIA / 2,
            depth=P.CAMERA_BASE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(bx, P.CAMERA_BASE_D / 2, P.CAMERA_BASE_THICK / 2),
        )
        boolean(plate, h)

    plate.name = "CameraBracket"
    apply_bevel(plate, width=1.0, segments=6)
    clean_mesh(plate)
    shade_smooth(plate)
    return plate


def build_amp_mount():
    """Mini-plate for the Adafruit MAX98357 I2S amp PCB.

    The board has only 2 mounting holes, both 2.54mm from one edge,
    spaced 12.7mm apart (Eagle source). Two standoffs go there; M3
    bolt-down holes live on the opposite side of the plate.
    """
    plate = add_cube(
        "AmpPlate",
        (P.AMP_PLATE_W, P.AMP_PLATE_D, P.AMP_PLATE_THICK),
        location=(P.AMP_PLATE_W / 2, P.AMP_PLATE_D / 2, P.AMP_PLATE_THICK / 2),
    )
    apply_bevel(plate, width=1.2, segments=6)

    # 2 standoffs at 12.7mm pitch along X, near the Y+ edge of the plate.
    standoff_y = P.AMP_PLATE_D - P.AMP_HOLE_EDGE_OFFSET - 1.5
    cx_center = P.AMP_PLATE_W / 2
    for sx in [cx_center - P.AMP_HOLE_PITCH / 2, cx_center + P.AMP_HOLE_PITCH / 2]:
        post = add_cyl(
            f"AmpStand_{int(sx)}",
            radius=P.AMP_STANDOFF_OD / 2,
            depth=P.AMP_STANDOFF_H,
            location=(sx, standoff_y, P.AMP_PLATE_THICK + P.AMP_STANDOFF_H / 2),
        )
        mod = plate.modifiers.new(name=f"u_amp_{sx}", type="BOOLEAN")
        mod.operation = "UNION"; mod.object = post; mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = plate
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(post, do_unlink=True)
        thru = add_cyl(
            f"AmpHole_{int(sx)}",
            radius=P.AMP_M25_HOLE / 2,
            depth=P.AMP_PLATE_THICK + P.AMP_STANDOFF_H + 2 * P.BOOLEAN_OVERSHOOT,
            location=(sx, standoff_y, (P.AMP_PLATE_THICK + P.AMP_STANDOFF_H) / 2),
        )
        boolean(plate, thru)

    # 2 M3 bolt-down holes on the opposite (Y-) side.
    for cx in [3.0, P.AMP_PLATE_W - 3.0]:
        h = add_cyl(
            f"AmpFix_{int(cx)}",
            radius=P.M3_HOLE_DIA / 2,
            depth=P.AMP_PLATE_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(cx, 3.0, P.AMP_PLATE_THICK / 2),
        )
        boolean(plate, h)

    clean_mesh(plate)
    shade_smooth(plate)
    return plate


def _UNUSED_build_inner_cage():
    """Solid block sized to fit inside the skin, then carved for components."""
    t = P.OUTER_SKIN_THICK
    wall = P.CAGE_WALL_THICK
    inner_w = P.SHELL_W - 2 * t - 1.0   # 0.5mm clearance per side from skin
    inner_d = P.SHELL_D - 2 * t - 1.0
    inner_h = P.SHELL_H - t - P.BOTTOM_THICK - 1.0

    cage = build_wedge_solid(
        "InnerCage",
        w=inner_w,
        d=inner_d,
        h=inner_h,
        tilt_y=P.FACE_TILT_Y * inner_h / P.SHELL_H,
    )
    cage.location = (t + 0.5, t + 0.5, P.BOTTOM_THICK + 0.5)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Hollow the cage so it's a shell (wall_thick walls) — components nest
    # against the inside surfaces.
    hollow = build_wedge_solid(
        "CageHollow",
        w=inner_w - 2 * wall,
        d=inner_d - 2 * wall,
        h=inner_h - wall,  # closed top, open bottom
        tilt_y=P.FACE_TILT_Y * (inner_h - wall) / P.SHELL_H,
    )
    hollow.location = (t + 0.5 + wall, t + 0.5 + wall, P.BOTTOM_THICK + 0.5 + wall)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    boolean(cage, hollow)

    # ── Component cavities ─────────────────────────────────────────────
    # All positioned relative to absolute scene origin.
    floor_z = P.BOTTOM_THICK + 0.5 + wall  # interior floor height

    placements = [
        # Jetson sits centrally, low.
        ("Jetson", P.JETSON_ORIN_NANO, (P.SHELL_W / 2, P.SHELL_D / 2 + 2, floor_z + P.JETSON_ORIN_NANO[2] / 2)),
        # NVMe lives under the Jetson — but the Jetson cavity already includes that height; leave as note.
        # Speaker chamber: front-right corner, faces forward.
        ("SpeakerChamber", P.SPEAKER_CHAMBER, (P.SHELL_W - 28, 22, floor_z + P.SPEAKER_CHAMBER[2] / 2)),
        # mmWave: low, front-center, looks forward.
        ("MMWave", P.MR24HPC1_MMWAVE, (P.SHELL_W / 2, 8, floor_z + P.MR24HPC1_MMWAVE[2] / 2 + 1)),
        # ReSpeaker 4-mic strip: along top interior, just behind frosted panel.
        ("ReSpeaker", P.RESPEAKER_4MIC, (P.SHELL_W / 2, 18, P.SHELL_H - 14)),
        # MAX98357 amp: tucked beside Jetson rear-left.
        ("AmpPCB", P.MAX98357_AMP, (14, P.SHELL_D - 22, floor_z + P.MAX98357_AMP[2] / 2)),
        # XIAO RP2040: rear corner.
        ("XIAO", P.XIAO_RP2040, (P.SHELL_W - 14, P.SHELL_D - 14, floor_z + P.XIAO_RP2040[2] / 2)),
        # Ambient light sensor: top front, above LEDs.
        ("AmbientLight", P.VEML7700_LIGHT, (24, 12, P.SHELL_H - 22)),
        # Thermal sensor: near exhaust — top rear.
        ("ThermalSense", P.PCT2075_THERM, (P.SHELL_W / 2, P.SHELL_D - 8, P.SHELL_H - 18)),
        # IMX219 camera: behind camera window on the front face.
        ("Camera", P.IMX219_CAMERA, (P.SHELL_W / 2, 14, P.CAMERA_WIN_OFFSET_FROM_BOTTOM + P.CAMERA_WIN_H / 2)),
        # Noctua fan: rear wall exhaust.
        ("FanIntake", P.NOCTUA_NF_A4X10, (P.SHELL_W / 2, P.SHELL_D - 10, P.JETSON_ORIN_NANO[2] / 2 + floor_z)),
    ]

    for name, size, loc in placements:
        cutter = add_component_cavity(f"cut_{name}", size, loc)
        boolean(cage, cutter)

    # LED strip channels — two slots behind the frosted face, both tilted
    # with the face plane. Y position sits just inside the face plane.
    led_top_z = P.SHELL_H - 18
    led_top = add_cube(
        "LEDStripTop",
        (P.LED_STRIP_LEN_TOP, P.LED_STRIP_DEPTH + P.BOOLEAN_OVERSHOOT, P.LED_STRIP_W),
        location=(P.SHELL_W / 2, face_y_at(led_top_z) + P.LED_STRIP_DEPTH, led_top_z),
        rotation_euler=(radians(P.FACE_TILT_DEG), 0, 0),
    )
    boolean(cage, led_top)
    led_bot_z = P.SHELL_H * 0.55
    led_bot = add_cube(
        "LEDStripBot",
        (P.LED_STRIP_LEN_BOT, P.LED_STRIP_DEPTH + P.BOOLEAN_OVERSHOOT, P.LED_STRIP_W),
        location=(P.SHELL_W / 2, face_y_at(led_bot_z) + P.LED_STRIP_DEPTH, led_bot_z),
        rotation_euler=(radians(P.FACE_TILT_DEG), 0, 0),
    )
    boolean(cage, led_bot)

    # M3 mounting bosses to the bottom plate — four corners on the floor.
    inset = P.SCREW_BOSS_OD
    for cx, cy in [
        (inset, inset),
        (P.SHELL_W - inset, inset),
        (inset, P.SHELL_D - inset),
        (P.SHELL_W - inset, P.SHELL_D - inset),
    ]:
        boss = add_cyl(
            f"BossFloor_{cx}_{cy}",
            radius=P.SCREW_BOSS_OD / 2,
            depth=P.SCREW_BOSS_H,
            location=(cx, cy, floor_z + P.SCREW_BOSS_H / 2),
        )
        # Union the boss into the cage.
        mod = cage.modifiers.new(name=f"u_boss_{cx}_{cy}", type="BOOLEAN")
        mod.operation = "UNION"
        mod.object = boss
        mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = cage
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(boss, do_unlink=True)

        hole = add_cyl(
            f"BossHole_{cx}_{cy}",
            radius=P.M3_INSERT_OD / 2,
            depth=P.M3_INSERT_DEPTH + P.BOOLEAN_OVERSHOOT,
            location=(cx, cy, floor_z + P.M3_INSERT_DEPTH / 2),
        )
        boolean(cage, hole)

    return cage


def build_bottom_plate():
    # Inset slightly so the plate tucks under the skin instead of sticking out.
    inset = P.BOTTOM_PLATE_INSET
    plate_w = P.SHELL_W - 2 * inset
    plate_d = P.SHELL_D - 2 * inset
    plate = add_cube(
        "BottomPlate",
        (plate_w, plate_d, P.BOTTOM_THICK),
        location=(P.SHELL_W / 2, P.SHELL_D / 2, P.BOTTOM_THICK / 2),
    )
    apply_bevel(plate, width=P.PLATE_FILLET, segments=8)

    # Silicone non-slip pad recess on the underside.
    pad_recess = add_cube(
        "PadRecess",
        (P.PAD_RECESS_W, P.PAD_RECESS_D, P.PAD_RECESS_DEPTH + P.BOOLEAN_OVERSHOOT),
        location=(P.SHELL_W / 2, P.SHELL_D / 2, P.PAD_RECESS_DEPTH / 2),
    )
    boolean(plate, pad_recess)

    # Cable strain relief channel on the rear edge underside.
    cable = add_cube(
        "CableChannel",
        (P.CABLE_CHANNEL_W, 12.0 + P.BOOLEAN_OVERSHOOT, P.CABLE_CHANNEL_H),
        location=(P.SHELL_W / 2, P.SHELL_D - 6.0, P.PAD_RECESS_DEPTH + P.CABLE_CHANNEL_H / 2),
    )
    boolean(plate, cable)

    # Hidden status LED window on the underside, near rear.
    status = add_cyl(
        "StatusLEDWin",
        radius=P.STATUS_LED_DIA / 2,
        depth=P.BOTTOM_THICK + 2 * P.BOOLEAN_OVERSHOOT,
        location=(P.SHELL_W / 2, P.SHELL_D - P.STATUS_LED_INSET, P.BOTTOM_THICK / 2),
    )
    boolean(plate, status)

    # M3 clearance holes lining up with the cage bosses.
    inset = P.SCREW_BOSS_OD
    for cx, cy in [
        (inset, inset),
        (P.SHELL_W - inset, inset),
        (inset, P.SHELL_D - inset),
        (P.SHELL_W - inset, P.SHELL_D - inset),
    ]:
        hole = add_cyl(
            f"PlateHole_{cx}_{cy}",
            radius=P.M3_HOLE_DIA / 2,
            depth=P.BOTTOM_THICK + 2 * P.BOOLEAN_OVERSHOOT,
            location=(cx, cy, P.BOTTOM_THICK / 2),
        )
        boolean(plate, hole)

    clean_mesh(plate)
    shade_smooth(plate)
    return plate


# ── Export ─────────────────────────────────────────────────────────────

def export_stl(obj, filename):
    os.makedirs(P.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(P.OUTPUT_DIR, filename)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, ascii_format=False)
    return path


def main():
    paths = []
    builds = [
        ("outer skin", build_outer_skin, "skin"),
        ("bottom plate", build_bottom_plate, "bottom"),
        ("Jetson mount plate", build_jetson_mount_plate, "jetson_plate"),
        ("XIAO mount plate", build_xiao_mount_plate, "xiao_plate"),
        ("speaker baffle", build_speaker_baffle, "speaker_baffle"),
        ("mmWave bracket", build_mmwave_bracket, "mmwave_bracket"),
        ("ReSpeaker mount", build_respeaker_mount, "respeaker_mount"),
        ("camera bracket", build_camera_bracket, "camera_bracket"),
        ("amp mount", build_amp_mount, "amp_mount"),
    ]
    for label, fn, key in builds:
        clear_scene()
        print(f">>> Building {label}...")
        obj = fn()
        path = export_stl(obj, P.OUTPUT_FILES[key])
        print(f"    wrote {path}")
        paths.append(path)
    print(">>> Done.")
    return paths


if __name__ == "__main__":
    main()
