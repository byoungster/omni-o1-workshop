"""Registration frame for the xTool O1 Omni small plate (Autodesk Fusion API script).

Two identical halves clip onto the plate, one on each end (turn the second half 180 degrees). Each half hugs its
end, both rounded corners and the front and back faces with a skirt, and a 2 mm hook under the plate's end
clamps the end lip between the hook and the frame's top lip, so a bump can't lift it off. (The first, sit-on-top
version fell off when bumped.) Slide each half on from its end. A thin ring lies on the mat around the print
area; its window is the print area plus WIN_CLR per side, so any jig insert cut to the print area (o1_jigs.py,
330 x 122 mm) drops in at the same place every time. Swap jigs by lifting the insert out.

Plate figures: top face 344 x 128 mm with R4 corners (third-party fits and xTool's 343 x 127 mat). 16.5 mm thick
at the faces and corners; each end has a handle cutout underneath, leaving an end lip 7.5 mm thick over a
trapezoid about 9 mm high, 83 mm wide at the top (the user's measurements, matching a measured photo). Jig
Generator's proven end clip clamps that lip in an 8.2 mm gap with a 2 mm hook reaching ~8 mm under. The mat's
pull tab sticks out 6-7 mm at the right end near the rear; the plate goes in either way round, so each half has a
tab relief at diagonally opposite corners.

Built and printed upright, as used: the hook and skirts stand on the print bed, so the hook's gripping face prints
as a clean top surface. Always builds into a new document.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

AREA = (330.0, 122.0)      # print area, small plate
PLATE = (344.0, 128.0)     # plate top face (mat)
PLATE_R = 4.0              # plate corner radius (vertical corners)
PLATE_T = 16.5             # plate thickness at the faces and corners (user's measurement)
BODY_D = 129.5             # plate body depth below the mat (slightly proud of the mat front and back)
SKIRT_SPAN = 130.3         # skirt inner faces, front to back (published fits: 130.2-130.75)
END_CLR = 0.2              # end wall to the plate's end face
RING_T = 1.6               # ring on the mat: just under the 1.7 mm jig inserts, so items stay highest
WALL = 2.4                 # skirt and end wall
FLANGE = 7.5               # end lip thickness over the handle cutout (user's measurement)
HOOK_CLR, HOOK_T = 0.7, 2.0    # gap above the hook (8.2 mm total slot, as Jig Generator) and hook thickness
HOOK_IN, HOOK_W = 7.0, 80.0    # hook reach under the end lip, and width (the cutout is ~83 mm at the top)
SKIRT_D = FLANGE + HOOK_CLR + HOOK_T   # every skirt reaches the hook's bottom, so all of it starts on the print bed
WIN_CLR = 0.3              # window clearance around the insert, per side
RELIEF_R = 1.0             # window corner relief, so square insert corners seat
MID_GAP = 1.0              # gap between the halves at the centre (plate width is 344 +- 0.5)
TAB = (7.0, 36.0)          # mat-tab relief along the end, from the rear corner (tab ~9-34 mm, sticks out 6-7 mm)
NAME = 'O1 Small frame half'


def near(curve, x, y):
    a, b = curve.startSketchPoint, curve.endSketchPoint
    da = (a.geometry.x - x) ** 2 + (a.geometry.y - y) ** 2
    db = (b.geometry.x - x) ** 2 + (b.geometry.y - y) ** 2
    return a if da < db else b


def end_outline(sk, x0, x1, hy, r):
    """Closed outline (mm) from x0 to x1, y = -hy..hy, rounded with radius r at the two x1 corners."""
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    x0, x1, hy, r = x0 * MM, x1 * MM, hy * MM, r * MM
    k = r * (1 - 1 / math.sqrt(2))
    l0 = L.addByTwoPoints(P3.create(x0, -hy, 0), P3.create(x1 - r, -hy, 0))
    a0 = A.addByThreePoints(l0.endSketchPoint, P3.create(x1 - k, -hy + k, 0), P3.create(x1, -hy + r, 0))
    l1 = L.addByTwoPoints(near(a0, x1, -hy + r), P3.create(x1, hy - r, 0))
    a1 = A.addByThreePoints(l1.endSketchPoint, P3.create(x1 - k, hy - k, 0), P3.create(x1 - r, hy, 0))
    l2 = L.addByTwoPoints(near(a1, x1 - r, hy), P3.create(x0, hy, 0))
    L.addByTwoPoints(l2.endSketchPoint, l0.startSketchPoint)


def rrect(sk, w, h, r):
    """Closed rounded rectangle (mm) centred on the origin; r=0 gives sharp corners."""
    if r <= 0:
        sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(-w / 2 * MM, -h / 2 * MM, 0),
                                                         P3.create(w / 2 * MM, h / 2 * MM, 0))
        return
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    x1, y1, r = w / 2 * MM, h / 2 * MM, r * MM
    k = r * (1 - 1 / math.sqrt(2))
    l0 = L.addByTwoPoints(P3.create(-x1 + r, -y1, 0), P3.create(x1 - r, -y1, 0))
    a0 = A.addByThreePoints(l0.endSketchPoint, P3.create(x1 - k, -y1 + k, 0), P3.create(x1, -y1 + r, 0))
    l1 = L.addByTwoPoints(near(a0, x1, -y1 + r), P3.create(x1, y1 - r, 0))
    a1 = A.addByThreePoints(l1.endSketchPoint, P3.create(x1 - k, y1 - k, 0), P3.create(x1 - r, y1, 0))
    l2 = L.addByTwoPoints(near(a1, x1 - r, y1), P3.create(-x1 + r, y1, 0))
    a2 = A.addByThreePoints(l2.endSketchPoint, P3.create(-x1 + k, y1 - k, 0), P3.create(-x1, y1 - r, 0))
    l3 = L.addByTwoPoints(near(a2, -x1, y1 - r), P3.create(-x1, -y1 + r, 0))
    A.addByThreePoints(l3.endSketchPoint, P3.create(-x1 + k, -y1 + k, 0), l0.startSketchPoint)


def plane_at(root, z):
    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByReal(z * MM))
    pl = root.constructionPlanes.add(pi)
    pl.isLightBulbOn = False
    return pl


def extrude(root, sk, profs, dist, op, name, body=None):
    if not isinstance(profs, adsk.core.ObjectCollection):
        coll = adsk.core.ObjectCollection.create()
        for p in ([profs] if hasattr(profs, 'areaProperties') else profs):
            coll.add(p)
        profs = coll
    ext = root.features.extrudeFeatures
    ei = ext.createInput(profs, op)
    ei.setDistanceExtent(False, VI.createByReal(dist * MM))
    if body:
        ei.participantBodies = [body]
    f = ext.add(ei)
    f.name = name
    return f


def sketch(root, z, name):
    sk = root.sketches.add(plane_at(root, z) if z else root.xYConstructionPlane)
    sk.name = name
    sk.isVisible = False
    return sk


def box(root, z0, z1, x0, x1, y0, y1, op, name, body):
    sk = sketch(root, z0, name)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(x0 * MM, y0 * MM, 0), P3.create(x1 * MM, y1 * MM, 0))
    return extrude(root, sk, sk.profiles.item(0), z1 - z0, op, name, body)


def build_half(root):
    """One frame half for the +X end, as used: plate top (mat) at z = 0, ring above, skirts and hook below."""
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    x_end = PLATE[0] / 2 + END_CLR               # end wall inner face
    hy_in = SKIRT_SPAN / 2
    r_in = PLATE_R
    x0 = MID_GAP / 2
    zb = -SKIRT_D

    sk = sketch(root, zb, NAME + ' Outline')
    end_outline(sk, x0, x_end + WALL, hy_in + WALL, r_in + WALL)
    body = extrude(root, sk, sk.profiles.item(0), SKIRT_D + RING_T, adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                   NAME).bodies.item(0)
    body.name = NAME

    # plate pocket inside the skirts, below the ring
    sk = sketch(root, zb, NAME + ' Plate pocket')
    end_outline(sk, x0 - 1, x_end, hy_in, r_in)
    extrude(root, sk, sk.profiles.item(0), SKIRT_D, cut, NAME + ' Plate pocket', body)

    # hook under the end lip: clamps the 7.5 mm lip in an 8.2 mm gap below the ring
    box(root, zb, zb + HOOK_T, x_end - HOOK_IN, x_end + 0.01, -HOOK_W / 2, HOOK_W / 2, join, NAME + ' End hook', body)

    # window: print area half + clearance, with corner reliefs, through the ring
    wx, wy = AREA[0] / 2 + WIN_CLR, AREA[1] / 2 + WIN_CLR
    sk = sketch(root, 0, NAME + ' Window')
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((x0 - 1) * MM, -wy * MM, 0), P3.create(wx * MM, wy * MM, 0))
    for sy in (-1, 1):
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            P3.create((wx - RELIEF_R * 0.3) * MM, sy * (wy - RELIEF_R * 0.3) * MM, 0), RELIEF_R * MM)
    extrude(root, sk, list(sk.profiles), RING_T, cut, NAME + ' Window', body)

    # mat-tab relief through the end wall at mat level, at the rear corner of this (+X) end; the other half,
    # turned 180 degrees, gets it at the front-left. The hook is well below it.
    y0, y1 = PLATE[1] / 2 - TAB[1], PLATE[1] / 2 - TAB[0]
    box(root, -1.5, 0.4, x_end - 0.01, x_end + WALL + 1, y0, y1, cut, NAME + ' Tab relief', body)   # under the ring
    return body


def fit_check(root, des, half):
    """Turned copy for the other end, a stand-in plate with its end cutouts, and a jig insert."""
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    copy = root.features.copyPasteBodies.add(half).bodies.item(0)
    mv = root.features.moveFeatures
    tr = adsk.core.Matrix3D.create()
    tr.setToRotation(math.pi, adsk.core.Vector3D.create(0, 0, 1), P3.create(0, 0, 0))
    coll = adsk.core.ObjectCollection.create()
    coll.add(copy)
    mv.add(mv.createInput(coll, tr))
    copy.name = NAME + ' (other end)'

    sk = sketch(root, -PLATE_T, 'Fit check plate')
    rrect(sk, PLATE[0], BODY_D, PLATE_R + (BODY_D - PLATE[1]) / 2)
    plate = extrude(root, sk, sk.profiles.item(0), PLATE_T, new, 'Fit check plate').bodies.item(0)
    plate.name = 'Fit check plate (344 x 129.5 x %.1f)' % PLATE_T
    # handle cutout under each end: 9 mm high trapezoid, 101 wide at the bottom, 83 at the top, 12 deep
    for sx in (-1, 1):
        xe = sx * PLATE[0] / 2
        for zz, half_w in ((-PLATE_T, 101 / 2), (-PLATE_T + (PLATE_T - FLANGE) / 2, 92 / 2)):
            box(root, zz, -FLANGE if zz > -PLATE_T else -PLATE_T + (PLATE_T - FLANGE) / 2,
                min(xe, xe - sx * 12), max(xe, xe - sx * 12), -half_w, half_w, cut, 'Fit check end cutout', plate)
    sk = sketch(root, 0, 'Fit check insert')
    rrect(sk, AREA[0], AREA[1], 0)
    insert = extrude(root, sk, sk.profiles.item(0), 1.7, new, 'Fit check insert').bodies.item(0)
    insert.name = 'Fit check insert (330 x 122 x 1.7)'

    ents = adsk.core.ObjectCollection.create()
    for b in (half, copy, plate, insert):
        ents.add(b)
    ii = des.createInterferenceInput(ents)
    ii.areCoincidentFacesIncluded = False
    res = des.analyzeInterference(ii)
    clashes = ['%s / %s %.3f mm3' % (r.entityOne.name, r.entityTwo.name, r.interferenceBody.volume * 1000) for r in res]
    mm = adsk.core.Application.get().measureManager
    gap = lambda a, b: mm.measureMinimumDistance(a, b).value * 10
    print('interference (touching faces excluded): %s' % (clashes or 'none'))
    print('gaps: frame-plate %.2f, frame-insert %.2f, half-half %.2f mm' % (gap(half, plate), gap(half, insert), gap(half, copy)))

    # can it be knocked off? lift and slide copies of the half against the plate
    tb = adsk.fusion.TemporaryBRepManager.get()

    def moved_clash(dx, dz):
        a = tb.copy(half)
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(dx * MM, 0, dz * MM)
        tb.transform(a, m)
        tb.booleanOperation(a, tb.copy(plate), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        return a.volume * 1000
    print('lift 1.0 mm: %.2f mm3 (hook caught under the end lip if > 0)' % moved_clash(0, 1.0))
    print('slide off outward 3 / 8 mm: %.2f / %.2f mm3 (0 = slides on and off freely)' % (moved_clash(3, 0), moved_clash(8, 0)))
    for b in (plate, insert):
        b.opacity = 0.35
    return clashes


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    half = build_half(root)
    bb = half.boundingBox
    print('%s %.1f x %.1f x %.1f mm, %.1f g PLA' % (
        NAME, (bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
        (bb.maxPoint.z - bb.minPoint.z) * 10, half.volume * 1.24))
    if fit_check(root, des, half):
        raise RuntimeError('frame interferes with the plate or the insert')
