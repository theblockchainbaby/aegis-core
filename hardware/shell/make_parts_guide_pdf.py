"""Generate the printable-parts documentation PDF for Aegis Core v1."""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_PATH = "/Users/york/aegis-core/hardware/shell/output/aegis_node_parts_guide.pdf"
RENDERS_DIR = "/Users/york/aegis-core/hardware/shell/output/renders"

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "TitleC", parent=styles["Title"], fontSize=22, leading=26, spaceAfter=10,
)
subtitle_style = ParagraphStyle(
    "SubtitleC", parent=styles["Normal"], fontSize=11, leading=14,
    textColor=colors.grey, spaceAfter=18,
)
h1_style = ParagraphStyle(
    "H1C", parent=styles["Heading1"], fontSize=16, leading=20,
    spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1a1a1a"),
)
h2_style = ParagraphStyle(
    "H2C", parent=styles["Heading2"], fontSize=13, leading=17,
    spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#222222"),
)
body_style = ParagraphStyle(
    "BodyC", parent=styles["BodyText"], fontSize=10.5, leading=14,
    spaceAfter=6, alignment=TA_LEFT,
)
caption_style = ParagraphStyle(
    "CaptionC", parent=styles["Italic"], fontSize=9, leading=11,
    textColor=colors.grey, spaceAfter=12,
)
mono_style = ParagraphStyle(
    "MonoC", parent=styles["Code"], fontSize=9.5, leading=12,
    spaceAfter=4, leftIndent=8,
)

doc = SimpleDocTemplate(
    OUT_PATH, pagesize=LETTER,
    topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    leftMargin=0.9 * inch, rightMargin=0.9 * inch,
    title="Aegis Core v1 - Shell Parts Guide",
    author="York Sims",
)

story = []

# ── Cover ─────────────────────────────────────────────────────────────
story.append(Paragraph("Aegis Core v1", title_style))
story.append(Paragraph(
    "Shell Parts Guide &mdash; Printable Hardware for the Node",
    subtitle_style,
))

story.append(Paragraph("About the project", h1_style))
story.append(Paragraph(
    "Aegis Core v1 is an ambient cognitive presence desk companion. It is a "
    "wedge-shaped, Jetson-powered desk node with a single abstract LED face, "
    "smoked-acrylic perception window, far-field mic array, mmWave presence "
    "sensor, and a small acoustic-presence speaker. The full design "
    "specification lives at "
    "<font face='Courier'>docs/superpowers/specs/2026-05-10-aegis-core-v1-design.md</font>.",
    body_style,
))
story.append(Paragraph(
    "The shell houses: Jetson Orin Nano Super dev kit (the brain), Noctua "
    "NF-A4x10 40mm fan, Seeed XIAO RP2040 (the heartbeat MCU), ReSpeaker "
    "4-Mic Linear Array, MAX98357 I2S amp + 2W full-range driver in a "
    "damped chamber, Raspberry Pi IMX219 camera, Seeed MR24HPC1 mmWave "
    "presence sensor, VEML7700 ambient light sensor, PCT2075 thermal "
    "sensor near exhaust, and two SK6812 RGBW LED strips behind a deeply "
    "frosted polycarbonate panel.",
    body_style,
))

story.append(Paragraph("Two-session print plan", h1_style))
story.append(Paragraph(
    "All six parts cannot fit on the Saturn 4 Ultra 16K's 218 &times; 123mm "
    "build plate at once. Print in two sessions:",
    body_style,
))
plan_data = [
    ["Session", "STL", "Contents", "Time"],
    ["A (small parts, validate fit)",
     "aegis_node_all_small_parts.stl",
     "Jetson plate, XIAO pocket, ReSpeaker mount, speaker baffle, mmWave bracket, camera bracket, amp mount (7 islands)",
     "~50-70 min"],
    ["B (structural base)",
     "aegis_node_bottom_plate.stl",
     "Bottom plate alone (166x101mm, fills the bed)",
     "~30-45 min"],
    ["C (final)",
     "aegis_node_outer_skin.stl",
     "Outer skin alone (169x104x85mm)",
     "~90-120 min"],
]
plan_table = Table(plan_data, colWidths=[1.0 * inch, 2.3 * inch, 2.6 * inch, 0.9 * inch])
plan_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(plan_table)
story.append(Paragraph(
    "Rationale: Session 1 is the higher-risk batch (mount holes have to "
    "actually line up with your real hardware). Print it first, test-fit "
    "your Jetson and other components, iterate if needed, then commit the "
    "longer outer-skin print.",
    body_style,
))

story.append(Paragraph("Material recommendation", h1_style))
mat_data = [
    ["Part(s)", "Resin", "Why"],
    ["Outer skin",
     "Cosmetic resin (matte gray / smoke)",
     "Visible surface; no thermal or mechanical load"],
    ["Bottom plate, Jetson mount, speaker baffle, mmWave bracket, camera bracket",
     "ABS-like Resin Pro or tough engineering resin",
     "Take screws; Jetson dissipates ~15W and internal air can reach 70&deg;C. Standard resin softens at ~60&deg;C and cracks at fasteners."],
    ["XIAO mount, ReSpeaker mount, amp mount",
     "Any resin (ABS-like preferred)",
     "Smaller boards, lighter load &mdash; either works"],
]
mat_table = Table(mat_data, colWidths=[2.2 * inch, 2.3 * inch, 2.3 * inch])
mat_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(mat_table)

story.append(Paragraph("Fastener summary", h1_style))
fastener_data = [
    ["Screw", "Quantity", "Use"],
    ["M3 self-tap, ~8mm", "4", "Bottom plate to outer skin's internal corner bosses (from below)"],
    ["M3 self-tap, ~8mm", "8-14", "Mount plates and brackets to bottom plate"],
    ["M2.5, ~6mm", "4", "Jetson Orin Nano dev kit carrier to mount plate's standoffs"],
    ["M2.5, ~5mm", "4", "MAX98357 amp PCB to amp mount's standoffs"],
    ["M2, ~5mm", "2", "Seeed XIAO RP2040 to its standoffs"],
    ["M2, ~5mm", "4", "Speaker driver to baffle's bolt circle"],
    ["M2, ~5mm", "4", "MR24HPC1 mmWave to bracket"],
    ["M2, ~5mm", "4", "ReSpeaker 4-Mic Linear Array to mount standoffs"],
    ["M2, ~5mm", "4", "IMX219 camera module to bracket"],
]
fastener_table = Table(fastener_data, colWidths=[1.8 * inch, 0.9 * inch, 4.1 * inch])
fastener_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(fastener_table)
story.append(Paragraph(
    "All screws are self-tapping into resin. Pilot holes in the model "
    "are sized for M3 (2.7mm diameter, ~85% of nominal). M2.5 and M2 "
    "holes for component mounting use direct-thread sizing.",
    body_style,
))

story.append(PageBreak())

# ── Part-by-part ──────────────────────────────────────────────────────
story.append(Paragraph("The nine printable parts", h1_style))


def part_section(title, filename, dims, role, orientation, material, assembly_notes):
    elems = []
    elems.append(Paragraph(title, h2_style))

    # Render image, if present.
    img_path = os.path.join(RENDERS_DIR, filename.replace(".stl", ".png"))
    if os.path.isfile(img_path):
        img = Image(img_path, width=5.2 * inch, height=3.5 * inch, kind="proportional")
        img.hAlign = "CENTER"
        elems.append(img)
        elems.append(Spacer(1, 4))

    info = [
        ["STL file", f"<font face='Courier'>{filename}</font>"],
        ["Dimensions (X &times; Y &times; Z)", dims],
        ["Role", role],
        ["Print orientation", orientation],
        ["Material", material],
        ["Assembly", assembly_notes],
    ]
    table_rows = [[Paragraph(f"<b>{k}</b>", body_style),
                   Paragraph(v, body_style)] for k, v in info]
    t = Table(table_rows, colWidths=[1.6 * inch, 4.8 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f4f4")),
    ]))
    elems.append(t)
    return KeepTogether(elems)


story.append(part_section(
    title="1. Outer Skin",
    filename="aegis_node_outer_skin.stl",
    dims="169 &times; 104 &times; 85 mm",
    role=(
        "The visible cosmetic shell. Truncated wedge form with the front face "
        "tilted 15&deg; back so its normal points up toward a seated user "
        "(\"attentive,\" not surveillance-oriented). Features cutouts for the "
        "frosted polycarbonate LED panel (92 &times; 50mm), the smoked-acrylic "
        "camera window (16 &times; 10mm), a rear barrel-jack hole (8.5mm), and "
        "a hidden USB-C service port on the side seam. Four internal corner "
        "bosses (&Oslash;8 &times; 12mm) with M3 self-tap pilot holes for "
        "bottom-plate attachment. Three &Oslash;2mm drain vents on the rear-top "
        "for resin egress during MSLA printing."
    ),
    orientation=(
        "Open side down (bottom rim on the build plate). Tilt 30&deg; around "
        "the depth (Y) axis so the front face is the up-most surface and gets "
        "the sharpest LCD detail. The drain holes on the rear-top will end up "
        "facing up-and-back during the print, allowing trapped resin to escape."
    ),
    material="Cosmetic resin (matte gray, smoke, or white).",
    assembly_notes=(
        "Slides over the assembled interior. Bolts to the bottom plate via 4 &times; "
        "M3 self-tap screws driven up from below through the bottom plate's "
        "corner clearance holes into the skin's internal bosses."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="2. Bottom Plate",
    filename="aegis_node_bottom_plate.stl",
    dims="166 &times; 101 &times; 3.5 mm",
    role=(
        "The structural base. Tucks 1.8mm under the outer skin's footprint on "
        "each side so there is no overhang. Features a 105 &times; 80mm recess "
        "on the underside for a silicone non-slip pad, a 7 &times; 5mm cable "
        "strain-relief channel at the rear, a &Oslash;3mm hidden status-LED "
        "window near the rear edge, and 4 &times; M3 clearance holes at the "
        "corners that line up with the outer skin's bosses."
    ),
    orientation=(
        "Very mild tilt (10-15&deg; on one axis). Plate is thin; minimal "
        "supports under the underside features. Pad recess can face up or down."
    ),
    material="ABS-like Resin Pro recommended for fastener retention.",
    assembly_notes=(
        "First piece mounted in assembly. All other component plates "
        "(Jetson mount, XIAO mount, speaker baffle, mmWave bracket) bolt down "
        "into it via M3 self-tap screws. Cable from the 12V barrel jack feeds "
        "out the rear strain-relief channel."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="3. Jetson Mount Plate (v2)",
    filename="aegis_node_jetson_mount.stl",
    dims="115 &times; 78 &times; 10 mm",
    role=(
        "The plate the Jetson Orin Nano Super dev kit's carrier board bolts to. "
        "<b>Revised in Session 2</b> &mdash; original 108 &times; 87mm plate "
        "conflicted with the skin's internal corner bosses. New design: "
        "99 &times; 72mm core (fits between the bosses) plus two 8mm side tabs "
        "at the left/right edge midpoints carrying the M3 bolt-down holes. Four "
        "&Oslash;6mm standoffs (7mm tall) at the carrier's M2.5 hole pattern "
        "(93 &times; 72mm spacing) lift the board off the plate surface to "
        "clear an underside M.2 NVMe SSD."
    ),
    orientation="15-20&deg; tilt, plate-side down, standoffs facing up.",
    material="ABS-like Resin Pro &mdash; carries the heaviest single component and the heat source.",
    assembly_notes=(
        "Position centered on the bottom plate. The side tabs hold the 2 &times; "
        "M3 self-tap screws into pilot holes you'll mark and drill in the bottom "
        "plate at world positions (9, 50) and (116, 50). The Jetson carrier "
        "bolts to the standoffs with 4 &times; M2.5 screws."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="4. XIAO RP2040 Pocket",
    filename="aegis_node_xiao_mount.stl",
    dims="24.7 &times; 21.5 &times; 6 mm",
    role=(
        "Friction-fit pocket for the Seeed XIAO RP2040. <b>Important:</b> the "
        "XIAO is castellated SMT-only &mdash; it has no mounting holes. The "
        "board drops into a 21.5 &times; 18.3mm pocket (0.25mm clearance per "
        "side) and is held by friction. A notch on one short edge exposes "
        "the USB-C port so the cable can plug in without removing the board."
    ),
    orientation="Pocket-side up, 15&deg; tilt. Small print, easy.",
    material="Any resin (ABS-like recommended if you'll be pulling USB-C cables).",
    assembly_notes=(
        "Press the XIAO in until the pocket floor seats it flat. The USB-C "
        "end aligns with the cable-access notch. 2 &times; M3 screws through "
        "corner holes on the pocket floor attach to the bottom plate."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="5. Speaker Baffle",
    filename="aegis_node_speaker_baffle.stl",
    dims="60 &times; 40 &times; 23 mm (with mounting tabs)",
    role=(
        "Sized for the Dayton Audio CE32A-4 (32x32mm square frame, &Oslash;19mm "
        "cone, 15.5mm depth). 40 &times; 40 &times; 20mm sealed chamber with a "
        "&Oslash;20mm cone aperture in the baffle (1mm gasket clearance over "
        "the cone) and 4 &times; &Oslash;2.2mm bolt holes on a 28 &times; 28mm "
        "square pattern around it. Open at the rear so you can install "
        "acoustic foam by hand. Two 10mm mounting tabs at the bottom carry "
        "M3 holes for bolting to the bottom plate."
    ),
    orientation=(
        "Tilt 45&deg; with the driver hole UP and the open chamber facing the "
        "print head. The baffle face (where the driver bolts to) gets the "
        "sharpest detail in this orientation."
    ),
    material="ABS-like Resin Pro &mdash; carries acoustic vibration and the driver's weight.",
    assembly_notes=(
        "Pack the chamber with light acoustic foam before bolting the driver. "
        "Mount in the front of the shell so sound projects forward through "
        "vents or a fabric grill (not yet modeled &mdash; future iteration)."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="6. mmWave Bracket",
    filename="aegis_node_mmwave_bracket.stl",
    dims="46 &times; 12 &times; 44 mm",
    role=(
        "Vertical L-bracket for the Seeed MR24HPC1 mmWave board "
        "(30W &times; 35D mm, 4 corner holes &Oslash;2.2 at 26 &times; 31mm "
        "pitch per the manufacturer datasheet). The 36 &times; 41mm vertical "
        "plate carries the M2 hole pattern; the 12mm base tab has 2 &times; "
        "M3 holes for bolt-down."
    ),
    orientation=(
        "Lay on its side, 30&deg; tilt. Base flat against the tilt plane; "
        "vertical plate is the long axis. Add a brim &mdash; vertical plate is "
        "3mm thin &times; 33mm tall (11:1) and benefits from extra adhesion."
    ),
    material="ABS-like Resin Pro for structural rigidity.",
    assembly_notes=(
        "Position at the front of the shell, sensor facing through the lower "
        "portion of the front face or below the camera window. The MR24HPC1's "
        "field-of-view is wide so exact orientation tolerances are forgiving."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="7. ReSpeaker 4-Mic Mount",
    filename="aegis_node_respeaker_mount.stl",
    dims="165 &times; 28 &times; 7 mm",
    role=(
        "Long strip plate for the ReSpeaker 4-Mic Linear Array (manufacturer "
        "DXF: 157.48 &times; 17.145mm PCB with 2 explicit &Oslash;3.0 mounting "
        "holes spaced 49.022mm center-to-center along the long axis). Two "
        "&Oslash;5mm standoffs at exactly that pitch match the array's hole "
        "pattern. Two M3 bolt-down holes at the ends of the plate attach to "
        "the bottom plate. The shell envelope was bumped to 170 &times; 105mm "
        "specifically to accommodate this 157mm-long mic array internally."
    ),
    orientation=(
        "Plate-side down, 15&deg; tilt. Standoffs face up. Tree supports under "
        "the plate."
    ),
    material="ABS-like Resin Pro for fastener retention.",
    assembly_notes=(
        "Mount along the front-upper region of the shell, parallel to the "
        "floor, so the 4 mic capsules face up through the open front-face "
        "cutout for far-field pickup. Connect the array's USB-A cable to the "
        "Jetson at the rear of the shell."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="8. IMX219 Camera Bracket",
    filename="aegis_node_camera_bracket.stl",
    dims="38 &times; 14 &times; 35 mm",
    role=(
        "Vertical bracket for the Raspberry Pi Camera v2 (IMX219). Per the "
        "official mech drawing (RP-008149-DS-1), the PCB is 23.862 &times; 25mm "
        "with 4 corner &Oslash;2.2 holes at <b>14.5 &times; 21mm</b> pitch "
        "(NOT the commonly-cited 21 &times; 12.5). The 30 &times; 32mm vertical "
        "plate carries the correct hole pattern and a central &Oslash;9mm "
        "lens-clearance hole. The 38mm base tab has 2 &times; M3 holes."
    ),
    orientation=(
        "Same as the mmWave bracket: lay on its side, 30&deg; tilt. Add a brim "
        "for the thin vertical plate."
    ),
    material="ABS-like Resin Pro for fastener and dimensional stability.",
    assembly_notes=(
        "Position just behind the camera window cutout in the outer skin. "
        "Verify the lens center aligns with the window's geometric center. "
        "CSI ribbon cable routes from camera back to the Jetson's CSI port."
    ),
))
story.append(Spacer(1, 10))

story.append(part_section(
    title="9. MAX98357 Amp Mount",
    filename="aegis_node_amp_mount.stl",
    dims="24 &times; 24 &times; 6 mm",
    role=(
        "Mini-plate for the Adafruit MAX98357 I2S amplifier breakout (PID 3006). "
        "Per the Eagle source, this board has only <b>2 mounting holes</b>, both "
        "at the top edge, spaced 12.7mm apart. Two &Oslash;4.5mm M2.5 standoffs "
        "match that pattern. Two M3 holes at the opposite edge of the mini-plate "
        "for bolt-down."
    ),
    orientation="Plate-side down, 15&deg; tilt. Trivial.",
    material="Any resin.",
    assembly_notes=(
        "Position near the speaker baffle &mdash; the I2S amp drives the 2W "
        "driver, so keep the speaker-output cable short. Connect amp inputs to "
        "the Jetson's I2S pins via 4 wires."
    ),
))

# ── Closing notes ─────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("Print workflow on the Elegoo Saturn 4 Ultra 16K", h1_style))
story.append(Paragraph(
    "Slicer: Chitubox (Basic is sufficient) or Voxeldance Tango. Select "
    "<b>Elegoo Saturn 4 Ultra 16K</b> as the printer profile &mdash; this "
    "sets the 218 &times; 123 &times; 260mm build volume, 16K LCD resolution, "
    "and reasonable exposure defaults.",
    body_style,
))
story.append(Paragraph(
    "Recommended slice settings (starting points; adjust per resin "
    "manufacturer's spec):",
    body_style,
))
slice_data = [
    ["Setting", "Value"],
    ["Layer height", "0.05 mm"],
    ["Exposure time", "2.5 s (Standard resin) / 3.5 s (ABS-like Resin Pro)"],
    ["Bottom layers", "5"],
    ["Bottom exposure", "25-30 s"],
    ["Lift distance", "6 mm"],
    ["Lift speed", "50 mm/min"],
    ["Anti-aliasing", "Level 4"],
    ["Supports", "Tree, Medium density, auto-place"],
]
slice_table = Table(slice_data, colWidths=[1.8 * inch, 4.2 * inch])
slice_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
]))
story.append(slice_table)

story.append(Paragraph("Post-print", h1_style))
story.append(Paragraph(
    "1. Wash in IPA (Mercury XS or equivalent bath) for 5-8 minutes.<br/>"
    "2. Air-dry completely (15-30 minutes).<br/>"
    "3. UV cure for 4-6 minutes per side.<br/>"
    "4. Inspect for non-manifold artifacts or trapped uncured resin in cavities.<br/>"
    "5. Drill out pilot holes for mount-plate attachment if you elected to "
    "mark-and-drill rather than blind self-tap.",
    body_style,
))

story.append(Paragraph("Open iteration items", h1_style))
story.append(Paragraph(
    "The current parts are a v0 form study based on datasheet defaults. "
    "Before a final build, verify:",
    body_style,
))
story.append(Paragraph(
    "&bull; Jetson Orin Nano Super dev kit actual envelope with NVMe SSD + "
    "Noctua cooler installed &mdash; measure your hardware once Session 1 is "
    "test-fit<br/>"
    "&bull; LED strip backers behind the frosted face &mdash; SK6812 RGBW "
    "strips have self-adhesive backing; stick them directly to the inside of "
    "the skin behind the frosted panel. No printed part required for v1.<br/>"
    "&bull; Real connector positions on the rear wall (barrel jack, USB-C, "
    "USB-A x4, HDMI, Ethernet) &mdash; pending Jetson measurements<br/>"
    "&bull; Speaker chamber acoustic tuning (port hole, foam fill) &mdash; "
    "current chamber is a sealed placeholder<br/>"
    "&bull; Frosted polycarbonate panel and smoked-acrylic camera window "
    "&mdash; sourced separately, not 3D-printed",
    body_style,
))

story.append(Paragraph(
    "Generated from <font face='Courier'>generate_shell.py</font> and "
    "<font face='Courier'>parameters.py</font> in "
    "<font face='Courier'>aegis-core/hardware/shell/</font>. "
    "Re-run those to regenerate STLs after parameter changes.",
    caption_style,
))

doc.build(story)
print(f">>> Wrote {OUT_PATH}")
