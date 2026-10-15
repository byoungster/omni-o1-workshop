"""Registration frame for the xTool O1 Omni small plate (Autodesk Fusion API script).

Two identical halves drop over the plate, one on each end (turn the second half 180 degrees). Each half
hugs its end face, both rounded corners and the front and back faces with a skirt, so it sits square
on the plate and cannot shift sideways. A thin ring lies on the adhesive mat around the print area. Its
window is the print area plus WIN_CLR per side, so any jig insert cut to the print area (o1_jigs.py,
330 x 122 mm) drops in at the same place every time. Swap jigs by lifting the insert out.

Plate figures (researched 2026-10-14): xTool publishes only the print area. Third-party models
agree on a 344 x 128 mm top face with R4 corners. The body is up to 129.5 mm deep, and the print area is
centred (7 mm in from each end, 3 mm in from front and rear). The mat's pull tab sticks out of the right
end near the rear corner. The plate can go in either way round, so each half has a tab relief at
diagonally opposite corners. Skirts stop short of the centre of the front and back faces, where the
plate carries a badge or latch.

Built upside down (ring on the bed, skirts up), as it prints. Always builds into a new document.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

AREA = (330.0, 122.0)      # print area, small plate
PLATE = (344.0, 128.0)     # plate top face (mat), third-party figures
PLATE_R = 4.0              # plate corner radius (vertical corners)
BODY_D = 129.5             # plate body depth below the mat (slightly proud of the mat front and back)
SKIRT_SPAN = 130.3         # skirt inner faces, front to back (three published fits: 130.2-130.75)
RING_T = 1.6               # ring on the mat: just under the 1.7 mm jig inserts, so items stay highest
WALL = 2.4                 # skirt wall
SKIRT_D = 6.0              # skirt depth down the plate faces (5-8 mm proven by others)
WIN_CLR = 0.3              # window clearance around the insert, per side
RELIEF_R = 1.0             # window corner relief, so square insert corners seat
MID_GAP = 1.0              # gap between the halves at the centre (plate width is 344 +- 0.5)
BADGE_HALF = 35.0          # no skirt within this distance of the centre, front and back
TAB = (6.0, 32.0)          # mat-tab relief, measured from the rear corner of the top face, at the right end
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
    """One frame half for the +X end, upside down: ring z 0..RING_T on the bed, skirts up to RING_T + SKIRT_D."""
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    h = RING_T + SKIRT_D
    x_end = PLATE[0] / 2                         # skirt end wall sits against the plate's end face
    hy_in = SKIRT_SPAN / 2
    r_in = PLATE_R                               # hugs the plate corner (front/back clearance keeps it clear)
    x0 = MID_GAP / 2

    sk = sketch(root, 0, NAME + ' Outline')
    end_outline(sk, x0, x_end + WALL, hy_in + WALL, r_in + WALL)
    body = extrude(root, sk, sk.profiles.item(0), h, adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                   NAME).bodies.item(0)
    body.name = NAME

    # Plate pocket inside the skirts (above the ring)
    sk = sketch(root, RING_T, NAME + ' Plate pocket')
    end_outline(sk, x0 - 1, x_end, hy_in, r_in)
    extrude(root, sk, sk.profiles.item(0), SKIRT_D, cut, NAME + ' Plate pocket', body)

    # Window: print area half + clearance, with corner reliefs, through the ring
    wx, wy = AREA[0] / 2 + WIN_CLR, AREA[1] / 2 + WIN_CLR
    sk = sketch(root, 0, NAME + ' Window')
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((x0 - 1) * MM, -wy * MM, 0), P3.create(wx * MM, wy * MM, 0))
    for sy in (-1, 1):
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            P3.create((wx - RELIEF_R * 0.3) * MM, sy * (wy - RELIEF_R * 0.3) * MM, 0), RELIEF_R * MM)
    extrude(root, sk, list(sk.profiles), RING_T, cut, NAME + ' Window', body)

    # Skirts stop short of the centre (badge or latch on the plate's front and back faces)
    box(root, RING_T, h, x0 - 1, BADGE_HALF, -hy_in - WALL - 1, hy_in + WALL + 1, cut, NAME + ' Badge relief', body)

    # Mat-tab relief through the end wall. In use the ring is on top, so the rear corner (+Y in use)
    # is at -Y here. The other half, turned 180 degrees, gets the relief at the front-left corner.
    y0, y1 = PLATE[1] / 2 - TAB[1], PLATE[1] / 2 - TAB[0]
    box(root, 0, h, x_end, x_end + WALL + 1, -y1, -y0, cut, NAME + ' Tab relief', body)
    return body


def fit_check(root, des, half):
    """Turned copy for the other end, a stand-in plate and a jig insert, then interference and gaps."""
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    copy = root.features.copyPasteBodies.add(half).bodies.item(0)
    mv = root.features.moveFeatures
    tr = adsk.core.Matrix3D.create()
    tr.setToRotation(math.pi, adsk.core.Vector3D.create(0, 0, 1), P3.create(0, 0, 0))
    coll = adsk.core.ObjectCollection.create()
    coll.add(copy)
    mv.add(mv.createInput(coll, tr))
    copy.name = NAME + ' (other end)'

    # Stand-ins, upside down like the frame: mat top on the ring at z = RING_T
    sk = sketch(root, RING_T, 'Fit check plate mat')
    rrect(sk, PLATE[0], PLATE[1], PLATE_R)
    mat = extrude(root, sk, sk.profiles.item(0), 1.5, new, 'Fit check plate mat').bodies.item(0)
    sk = sketch(root, RING_T + 1.5, 'Fit check plate body')
    rrect(sk, PLATE[0], BODY_D, PLATE_R + (BODY_D - PLATE[1]) / 2)
    plate = extrude(root, sk, sk.profiles.item(0), 15.5, new, 'Fit check plate body').bodies.item(0)
    sk = sketch(root, -0.1, 'Fit check insert')
    rrect(sk, AREA[0], AREA[1], 0)
    insert = extrude(root, sk, sk.profiles.item(0), 1.7, new, 'Fit check insert (330 x 122 x 1.7)').bodies.item(0)
    mat.name, plate.name = 'Fit check plate mat (344 x 128)', 'Fit check plate body (344 x 129.5)'
    insert.name = 'Fit check insert (330 x 122 x 1.7)'

    ents = adsk.core.ObjectCollection.create()
    for b in (half, copy, mat, plate, insert):
        ents.add(b)
    ii = des.createInterferenceInput(ents)
    ii.areCoincidentFacesIncluded = False
    res = des.analyzeInterference(ii)
    clashes = ['%s / %s %.3f mm3' % (r.entityOne.name, r.entityTwo.name, r.interferenceBody.volume * 1000) for r in res]
    mm = adsk.core.Application.get().measureManager
    gap = lambda a, b: mm.measureMinimumDistance(a, b).value * 10
    print('interference (touching faces excluded): %s' % (clashes or 'none'))
    print('gaps: frame-mat %.2f, frame-body %.2f, frame-insert %.2f, half-half %.2f mm' % (
        gap(half, mat), gap(half, plate), gap(half, insert), gap(half, copy)))
    for b in (mat, plate, insert):
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
