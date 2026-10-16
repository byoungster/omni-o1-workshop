"""Straight C-clips that lock jig frames to the xTool O1 Omni baseplates (Autodesk Fusion API script).

Each clip is one C-shaped profile extruded along the plate edge and printed lying on that profile, so both jaws are
part of the flat outline: no overhangs, no supports, and the jaws bend along the layers (the strong direction).
(One-piece clips printed upright needed 7 mm overhangs and nearly failed.)

Large plate (344 x 434 x 16.6 mm, a lip fits up to 26 mm under the edge): eight identical edge clips, two near each
corner. The top jaw lies on the mat and reaches the print area, so the jaws of all eight form the 330 x 420 window
for jigs and acrylic sheets; the hook goes under the plate, so a bump can't lift a clip. Keep clips 50-90 mm from
the corners: clear of the mat's pull tab (15-45 mm from a corner) and the spring latches (middle of the long sides).

Small plate: the sit-on frame halves from o1_frame.py v1 locate the jigs; one end clip per end holds a half down.
Its top jaw clamps the half's end lip to the mat and its hook goes under the plate's 7.5 mm end lip (the plate is
16.5 mm thick with a handle cutout under each end). Slide it on from the end, centred.

The model is built as printed: the profile lies in the XY plane and the clip runs up Z. Always builds into a new
document.
"""
import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1

LEAD = 0.6                 # lead-in chamfer on the jaw tips, so a clip slides onto the edge easily

# Large plate edge clip. Profile coordinates: x outward from the plate edge (plate at x < 0), y up (mat top at 0).
L_PLATE_T = 16.6           # plate thickness (user's measurement)
L_REACH = 6.7              # top jaw reaches the print area edge: 7 mm margin - 0.3 clearance
L_JAW_T = 1.6              # top jaw on the mat: under the 1.7 mm jigs and acrylic sheets
L_CLR = 0.4                # wall to plate edge, and slot clearance over the plate thickness
L_WALL = 3.0
L_HOOK_T, L_HOOK_IN = 2.0, 6.0
L_LEN = 40.0

# Small plate end clip. x outward from the plate's end face, y up (mat top at 0). The v1 frame half has a ring
# 1.6 mm thick on the mat reaching from 6.7 mm inside the end to its 2.4 mm end wall outside it, and a skirt 6 mm
# down that wall.
S_RING_T, S_HALF_WALL, S_HALF_SKIRT = 1.6, 2.4, 6.0
S_LIP = 7.5                # plate end lip over the handle cutout (user's measurement)
S_JAW_T, S_JAW_IN = 1.2, 2.0    # top jaw on the ring, and how far it reaches inside the plate end
S_CLR = 0.3                # clip wall to the half's end wall
S_WALL = 3.0
S_HOOK_CLR, S_HOOK_T, S_HOOK_IN = 0.7, 2.0, 7.0   # gap under the end lip (as Jig Generator), hook, reach
S_LEN = 50.0               # the end's handle cutout is ~83 mm wide at the top; the mat tab starts 30 mm off centre


def large_profile():
    xo, yt, yh = L_CLR + L_WALL, L_JAW_T, -(L_PLATE_T + L_CLR)
    yb = yh - L_HOOK_T
    return [(-L_REACH, LEAD), (-L_REACH, yt), (xo, yt), (xo, yb), (-L_HOOK_IN, yb), (-L_HOOK_IN, yh - LEAD),
            (-L_HOOK_IN + LEAD, yh), (L_CLR, yh), (L_CLR, 0), (-L_REACH + LEAD, 0)]


def small_profile():
    xi = S_HALF_WALL + S_CLR
    xo = xi + S_WALL
    yj = S_RING_T + 0.1                      # jaw underside: just clear of the ring
    yh = -(S_LIP + S_HOOK_CLR)               # hook top
    yb = yh - S_HOOK_T
    return [(-S_JAW_IN, yj + LEAD), (-S_JAW_IN, yj + S_JAW_T), (xo, yj + S_JAW_T), (xo, yb), (-S_HOOK_IN, yb),
            (-S_HOOK_IN, yh - LEAD), (-S_HOOK_IN + LEAD, yh), (xi, yh), (xi, yj), (-S_JAW_IN + LEAD, yj)]


def polygon_body(root, pts, length, name, x0=0.0):
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = name
    sk.isVisible = False
    L = sk.sketchCurves.sketchLines
    first = prev = None
    for i in range(len(pts)):
        a = prev.endSketchPoint if prev else P3.create((pts[0][0] + x0) * MM, pts[0][1] * MM, 0)
        b = first.startSketchPoint if i == len(pts) - 1 else P3.create((pts[i + 1][0] + x0) * MM, pts[i + 1][1] * MM, 0)
        prev = L.addByTwoPoints(a, b)
        first = first or prev
    ext = root.features.extrudeFeatures
    f = ext.addSimple(sk.profiles.item(0), VI.createByReal(length * MM),
                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    f.name = name
    b = f.bodies.item(0)
    b.name = name
    return b


def check(root, clip, stand_ins, name):
    """Interference with the stand-ins as fitted, and when the clip is lifted or slid off."""
    tb = adsk.fusion.TemporaryBRepManager.get()

    def clash(dx, dy):
        a = tb.copy(clip)
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(dx * MM, dy * MM, 0)
        tb.transform(a, m)
        tot = 0.0
        for s in stand_ins:
            c = tb.copy(a)
            tb.booleanOperation(c, tb.copy(s), adsk.fusion.BooleanTypes.IntersectionBooleanType)
            tot += c.volume * 1000
        return tot
    print('%s: fitted %.2f mm3 | lifted 1 mm %.1f mm3 (caught if > 0) | slid off 12 mm %.2f mm3 (0 = clips on and off)'
          % (name, clash(0, 0), clash(0, 1.0), clash(12, 0)))


def block(root, x0, x1, y0, y1, length, name, xs=0.0):
    return polygon_body(root, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], length, name, xs)


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent

    large = polygon_body(root, large_profile(), L_LEN, 'O1 Large plate edge clip (print 8)')
    plate = block(root, -40, 0, -L_PLATE_T, 0, L_LEN, 'Stand-in large plate edge')
    check(root, large, [plate], 'large edge clip')

    xs = 60.0                                 # small clip and its stand-ins, side by side with the large one
    small = polygon_body(root, small_profile(), S_LEN, 'O1 Small plate end clip (print 2)', xs)
    lip = block(root, -40, 0, -S_LIP, 0, S_LEN, 'Stand-in small plate end lip', xs)
    ring = block(root, -6.7, S_HALF_WALL, 0, S_RING_T, S_LEN, 'Stand-in frame half ring', xs)
    wall = block(root, 0, S_HALF_WALL, -S_HALF_SKIRT, 0, S_LEN, 'Stand-in frame half end wall', xs)
    check(root, small, [lip, ring, wall], 'small end clip')
    for b in (plate, lip, ring, wall):
        b.opacity = 0.35
    for b in (large, small):
        bb = b.boundingBox
        print('%-36s %.1f x %.1f x %.1f mm, %.1f g PLA' % (b.name, (bb.maxPoint.x - bb.minPoint.x) * 10,
              (bb.maxPoint.y - bb.minPoint.y) * 10, (bb.maxPoint.z - bb.minPoint.z) * 10, b.volume * 1.24))
