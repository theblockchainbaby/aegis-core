"""
Aegis Core v1 — Shell parameters.

Single source of truth for the wedge shell geometry, internal component
footprints, and print tolerances. Imported by generate_shell.py.

All units mm, all angles degrees. Datasheet dimensions for the v1 BOM
in docs/superpowers/specs/2026-05-10-aegis-core-v1-design.md §3.
"""

from math import radians, tan

# ── Outer envelope (spec §3.4) ─────────────────────────────────────────
SHELL_W = 170.0       # X — bumped to fit 157mm ReSpeaker 4-Mic Linear Array
SHELL_D = 105.0       # Y — depth, front to back
SHELL_H = 85.0        # Z — height
FACE_TILT_DEG = 15.0  # front face leans back this many degrees from vertical
FACE_TILT_Y = SHELL_H * tan(radians(FACE_TILT_DEG))  # how far front-top sits back from front-bottom

# ── Modernist form: taper + fillets ────────────────────────────────────
TOP_TAPER_X = 10.0    # mm narrower per side at the top
TOP_TAPER_Y = 6.0     # mm shorter at the rear edge of the top
SKIN_FILLET = 8.0     # main outer-edge fillet on the skin
PLATE_FILLET = 4.0    # outer-edge fillet on the bottom plate
FILLET_SEGMENTS = 10
BOTTOM_PLATE_INSET = 1.8

# ── Wall thicknesses ───────────────────────────────────────────────────
OUTER_SKIN_THICK = 2.4   # MJF/resin outer skin
CAGE_WALL_THICK = 2.8    # structural PETG inner cage
BOTTOM_THICK = 3.5       # bottom plate (load-bearing for non-slip pad + cable)
FROSTED_PANEL_INSET = 1.6  # how far the polycarb sits inside the skin face

# ── Frosted face cutout (where the LEDs glow through) ─────────────────
FACE_CUTOUT_W = 130.0
FACE_CUTOUT_H = 55.0
FACE_CUTOUT_MARGIN_BOTTOM = 18.0

# ── Camera window (IMX219 behind smoked acrylic, spec §3.2) ──────────
CAMERA_WIN_W = 16.0
CAMERA_WIN_H = 10.0
CAMERA_WIN_OFFSET_FROM_BOTTOM = 4.0  # on the tilted front face, measured up the slope

# ── LED strips (SK6812 RGBW, spec §3.3) ──────────────────────────────
# Two strips behind the frosted panel — one curved across the top of the
# face, one along the lower edge.
LED_STRIP_LEN_TOP = 110.0
LED_STRIP_LEN_BOT = 140.0
LED_STRIP_W = 7.0      # PCB width
LED_STRIP_DEPTH = 2.5  # standoff depth so strip can dissipate

# ── Internal component cavities ────────────────────────────────────────
# Verified against manufacturer datasheets / mechanical drawings / Eagle
# .brd files. Sources saved in hardware/shell/spec_research/.
JETSON_ORIN_NANO = (103.0, 90.5, 35.0)   # full dev kit envelope (NVIDIA SP-11324-001 Fig 4-2)
NOCTUA_NF_A4X10 = (40.0, 40.0, 10.0)     # noctua.at spec
XIAO_RP2040 = (21.0, 17.8, 3.5)          # Seeed wiki; NO mounting holes (castellated SMT only)
RESPEAKER_4MIC = (157.48, 17.145, 8.0)   # Seeed 2D drawing DXF — long linear strip
MAX98357_AMP = (17.78, 19.05, 4.5)       # Eagle source (Adafruit 3006); only 2 holes at top
SPEAKER_2W = (32.0, 32.0, 15.5)          # Dayton CE32A-4 spec PDF
SPEAKER_CHAMBER = (40.0, 40.0, 18.0)     # tight chamber around 32mm driver
MR24HPC1_MMWAVE = (30.0, 35.0, 4.0)      # Seeed MR24HPC1 datasheet (30W × 35D)
VEML7700_LIGHT = (25.4, 17.78, 4.6)      # Adafruit 4162 Eagle source
PCT2075_THERM = (25.4, 17.78, 4.6)       # Adafruit 4369 Eagle source
IMX219_CAMERA = (23.862, 25.0, 9.0)      # RPi Cam v2 mech drawing (23.862×25, NOT 25×24)
NVME_2280 = (22.0, 80.0, 4.0)            # M.2 2280 (JEDEC)

# ── External ports ─────────────────────────────────────────────────────
BARREL_JACK_DIA = 8.5      # 12V/5A panel-mount barrel jack hole
BARREL_JACK_INSET_Z = 28.0  # height above bottom on rear face
USB_C_W = 9.5              # service port cutout (hidden under skin seam)
USB_C_H = 4.0

# ── Mounting & assembly (self-tapping into resin) ──────────────────────
# Heat-set inserts crack standard resin; we use self-tapping M3 screws
# instead. Clearance holes pass the screw shank; pilot holes get tapped
# by the screw threads.
M3_HOLE_DIA = 3.4          # M3 clearance hole (screw shank passes through)
M3_PILOT_DIA = 2.7         # M3 self-tap pilot (~0.85 * 3.0mm; threads cut in resin)
M3_INSERT_OD = 4.5         # legacy — unused with self-tap fasteners
M3_INSERT_DEPTH = 5.5      # legacy — unused
SCREW_BOSS_OD = 8.0        # skin's internal corner-boss diameter
SCREW_BOSS_H = 12.0        # boss height inside the skin cavity

# ── Status LED window (hidden, only visible when tilted, spec §3.4) ──
STATUS_LED_DIA = 3.0
STATUS_LED_INSET = 12.0    # mm from rear edge on the bottom face

# ── Silicone pad recess (bottom non-slip foot) ────────────────────────
PAD_RECESS_W = 150.0
PAD_RECESS_D = 90.0
PAD_RECESS_DEPTH = 1.2

# ── Cable strain relief (rear bottom) ─────────────────────────────────
CABLE_CHANNEL_W = 7.0
CABLE_CHANNEL_H = 5.0

# ── Resin drain holes (hidden, on rear of top face) ───────────────────
# MSLA printing leaves uncured resin trapped in any sealed cavity. The
# outer skin's interior is open at the bottom but the wedge's top can
# still pool resin — add small vents in the rear-top so it escapes.
DRAIN_HOLE_DIA = 2.0
DRAIN_HOLE_COUNT = 3
DRAIN_HOLE_SPACING = 12.0
DRAIN_HOLE_INSET_FROM_REAR = 10.0  # how far forward of the rear-top edge

# ── Print tolerances ───────────────────────────────────────────────────
COMPONENT_CLEARANCE = 0.4  # added to each face of every component cavity
BOOLEAN_OVERSHOOT = 0.5    # extends a cutter past the surface to avoid coplanar faces

# ── Jetson Orin Nano Super dev kit mount plate ─────────────────────────
# Carrier 100x79mm. Hole pattern NOT published in NVIDIA spec; 93x72mm
# is a conservative default scaled from Fig 4-1. Verify against your
# physical board before final commit. Core fits between skin bosses
# (now at 8mm corner inset on the bumped 170x105 envelope).
JETSON_PLATE_W = 99.0
JETSON_PLATE_D = 72.0
JETSON_PLATE_THICK = 3.0
JETSON_HOLE_PATTERN_X = 93.0
JETSON_HOLE_PATTERN_Y = 72.0
JETSON_STANDOFF_OD = 6.0
JETSON_STANDOFF_H = 7.0
JETSON_M25_HOLE = 2.7
JETSON_TAB_W = 8.0
JETSON_TAB_D = 14.0

# ── Seeed XIAO RP2040 mount: FRICTION POCKET ───────────────────────────
# XIAO RP2040 is castellated SMT-only — no mounting holes exist. Hold it
# in a snug printed pocket; USB-C end stays open for cable access and
# reflashing.
XIAO_BOARD_W = 21.0            # PCB width
XIAO_BOARD_D = 17.8            # PCB depth
XIAO_BOARD_H = 3.5             # max component height on top side
XIAO_POCKET_TOL = 0.25         # gap per side for friction fit
XIAO_POCKET_WALL = 1.6         # pocket wall thickness
XIAO_BASE_THICK = 2.5          # pocket floor thickness
XIAO_USB_NOTCH_W = 12.0        # USB-C cable access notch width
XIAO_USB_NOTCH_D = 4.0         # notch depth into one wall

# ── Speaker baffle / chamber ───────────────────────────────────────────
# Dayton CE32A-4: 32x32mm square plastic frame, cone aperture Ø19mm,
# overall depth 15.5mm, 4 corner mounting holes Ø2.0 in a ~28mm square
# pattern. Spec PDF saved in spec_research/.
SPEAKER_DRIVER_FRAME_W = 32.0   # square plastic frame
SPEAKER_DRIVER_DIA = 20.0       # baffle cutout (Ø19 cone + 1mm gasket clearance)
SPEAKER_BOLT_PATTERN = 28.0     # square 28x28mm hole pattern (4 holes)
SPEAKER_BOLT_HOLE_DIA = 2.2     # clearance for M2
SPEAKER_CHAMBER_W = 40.0        # leaves ~4mm wall around the 32mm frame
SPEAKER_CHAMBER_D = 40.0
SPEAKER_CHAMBER_H = 20.0        # behind baffle, enough for 15.5mm driver depth
SPEAKER_BAFFLE_THICK = 3.0
SPEAKER_CHAMBER_WALL = 2.4
SPEAKER_TAB_W = 10.0

# ── mmWave bracket (MR24HPC1) ──────────────────────────────────────────
# Seeed MR24HPC1 datasheet: 30W x 35D mm PCB, 4 corner holes Ø2.2mm,
# pitch 26 x 31mm, inset 2mm from edges. Sensor faces forward through a
# 15x6mm antenna keepout in the top-center of the board.
MMWAVE_PLATE_W = 36.0
MMWAVE_PLATE_H = 41.0
MMWAVE_PLATE_THICK = 3.0
MMWAVE_HOLE_PATTERN_X = 26.0
MMWAVE_HOLE_PATTERN_Y = 31.0
MMWAVE_M2_HOLE = 2.4           # clearance for M2 (Ø2.2 board hole)
MMWAVE_BASE_W = 46.0
MMWAVE_BASE_D = 12.0
MMWAVE_BASE_THICK = 3.0

# ── ReSpeaker 4-Mic Linear Array mount ─────────────────────────────────
# Manufacturer DXF: PCB 157.48 x 17.145 mm, 2 explicit Ø3.0 mounting
# holes at 49.022mm pitch (centered along long axis), near the top edge.
RESPEAKER_PLATE_W = 165.0
RESPEAKER_PLATE_D = 28.0
RESPEAKER_PLATE_THICK = 3.0
RESPEAKER_HOLE_PITCH = 49.022   # only 2 holes — center-to-center along long axis
RESPEAKER_STANDOFF_OD = 5.0
RESPEAKER_STANDOFF_H = 4.0
RESPEAKER_M3_HOLE = 3.2         # for Ø3.0 mounting holes (M3 clearance)

# ── IMX219 Camera bracket (vertical, behind front face) ────────────────
# RPi Camera v2 mech drawing RP-008149-DS-1: PCB 23.862 x 25 mm, 4 corner
# holes Ø2.2 with pitch 14.5 x 21mm, corner offset 2mm from PCB edges.
CAMERA_PLATE_W = 30.0
CAMERA_PLATE_H = 32.0
CAMERA_PLATE_THICK = 3.0
CAMERA_HOLE_PATTERN_X = 14.5
CAMERA_HOLE_PATTERN_Y = 21.0
CAMERA_M2_HOLE = 2.4
CAMERA_BASE_W = 38.0
CAMERA_BASE_D = 14.0
CAMERA_BASE_THICK = 3.0
CAMERA_LENS_HOLE_DIA = 9.0

# ── MAX98357 I2S amp mount ─────────────────────────────────────────────
# Adafruit 3006 Eagle source: PCB 17.78 x 19.05 mm. Only TWO mounting
# holes, both on the top edge: at (2.54, 16.51) and (15.24, 16.51) —
# 12.7mm X pitch, 2.54mm down from top edge. Drill 2.5mm.
AMP_PLATE_W = 24.0
AMP_PLATE_D = 24.0
AMP_PLATE_THICK = 3.0
AMP_HOLE_PITCH = 12.7
AMP_HOLE_EDGE_OFFSET = 2.54    # holes are 2.54mm from one edge of the PCB
AMP_STANDOFF_OD = 4.5
AMP_STANDOFF_H = 3.0
AMP_M25_HOLE = 2.7

# ── Output ─────────────────────────────────────────────────────────────
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_FILES = {
    "skin": "aegis_node_outer_skin.stl",
    "bottom": "aegis_node_bottom_plate.stl",
    "jetson_plate": "aegis_node_jetson_mount.stl",
    "xiao_plate": "aegis_node_xiao_mount.stl",
    "speaker_baffle": "aegis_node_speaker_baffle.stl",
    "mmwave_bracket": "aegis_node_mmwave_bracket.stl",
    "respeaker_mount": "aegis_node_respeaker_mount.stl",
    "camera_bracket": "aegis_node_camera_bracket.stl",
    "amp_mount": "aegis_node_amp_mount.stl",
}
