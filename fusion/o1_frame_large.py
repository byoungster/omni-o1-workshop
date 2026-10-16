"""Corner locators for the xTool O1 Omni large plate (330 x 420 mm print area) (Autodesk Fusion API script).

Four corner clips grip the plate's corners. Each wraps its corner edge: a skirt down the full edge, a rounded
corner, a lip under the plate and a thin lip on the mat that runs to the print area. The lower lip stops the
clip lifting off when bumped (the first, sit-on-top version fell off). Printed upright, as used, so the lower
lip lies on the print bed (the same as Jig Generator's proven corner clips). Their inner edges form a window the size of the print area plus
WIN_CLR, so a jig or an acrylic sheet cut to 330 x 420 drops in square. Corners rather than a full frame: four
fit one 256 mm printer bed (a full frame round a ~344 x 434 plate would be about eight pieces), they stay clear
of the plate's spring latch at mid-edge, and each one finds its own corner.

Two shapes, two of each: the front-left piece (turned 180 degrees it is the rear-right) has a relief for the
mat's pull tab, which sits on the right side near the rear and moves to the left front when the plate goes in
the other way round; the front-right piece (turned, the rear-left) has none.

Plate figures: 344 x 434 mm (xTool's mat drawings: 343 x 433 mat aligned to the plate edges), 16.6 mm thick at
the corners (user's measurement), and a lip can reach up to 26 mm under a corner when the plate is installed.
The spring latches sit at the middle of both long sides; the 70 mm corners stay clear. Always builds into a
new document.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1

AREA = (330.0, 420.0)    # print area
PLATE_W = 344.0          # plate top, left-right (third-party figures agree)
PLATE_D = 434.0          # plate top, front-back (xTool mat drawing 433 + alignment)
PLATE_R = 4.0            # corner radius (assumed same as the small plate)
CLR = 0.4                # skirt clearance to the plate edge, all round
WALL = 2.4               # skirt wall
PLATE_T = 16.6           # plate thickness at the corners (user's measurement)
SLOT_CLR = 0.4           # slot = plate thickness + this
UNDER_T, UNDER_IN = 2.0, 6.0   # lower lip under the plate: thickness, reach in from the skirt
SKIRT_D = PLATE_T + SLOT_CLR   # skirt depth down the edge, to the top of the lower lip
LIP_T = 1.6              # lip on the mat: under the 1.7 mm jigs and any acrylic sheet, so items stay highest
WIN_CLR = 0.3            # window clearance round the insert, per side
RELIEF_R = 1.0           # window corner relief
LEG = 70.0               # each piece reaches this far along both edges from the corner
TAB = (15.0, 45.0)       # mat-tab relief along the side edge, from the corner (tab at ~19-42, sticks out 6-7 mm)
INSERT_T = 1.7           # stand-in insert thickness for the fit check


def rrect(sk, w, h, r):
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    x1, y1, r = w / 2 * MM, h / 2 * MM, r * MM
    k = r * (1 - 1 / math.sqrt(2))

    def near(curve, x, y):
        a, b = curve.startSketchPoint, curve.endSketchPoint
        return a if (a.geometry.x - x) ** 2 + (a.geometry.y - y) ** 2 < (b.geometry.x - x) ** 2 + (b.geometry.y - y) ** 2 else b
    l0 = L.addByTwoPoints(P3.create(-x1 + r, -y1, 0), P3.create(x1 - r, -y1, 0))
    a0 = A.addByThreePoints(l0.endSketchPoint, P3.create(x1 - k, -y1 + k, 0), P3.create(x1, -y1 + r, 0))
    l1 = L.addByTwoPoints(near(a0, x1, -y1 + r), P3.create(x1, y1 - r, 0))
    a1 = A.addByThreePoints(l1.endSketchPoint, P3.create(x1 - k, y1 - k, 0), P3.create(x1 - r, y1, 0))
    l2 = L.addByTwoPoints(near(a1, x1 - r, y1), P3.create(-x1 + r, y1, 0))
    a2 = A.addByThreePoints(l2.endSketchPoint, P3.create(-x1 + k, y1 - k, 0), P3.create(-x1, y1 - r, 0))
    l3 = L.addByTwoPoints(near(a2, -x1, y1 - r), P3.create(-x1, -y1 + r, 0))
    A.addByThreePoints(l3.endSketchPoint, P3.create(-x1 + k, -y1 + k, 0), l0.startSketchPoint)


def plane(root, z):
    if abs(z) < 1e-9:
        return root.xYConstructionPlane
    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByReal(z * MM))
    pl = root.constructionPlanes.add(pi)
    pl.isLightBulbOn = False
    return pl


def extrude(root, z0, profs, dist, op, name, body=None):
    if not isinstance(profs, adsk.core.ObjectCollection):
        c = adsk.core.ObjectCollection.create()
        c.add(profs)
        profs = c
    ext = root.features.extrudeFeatures
    ei = ext.createInput(profs, op)
    ei.setDistanceExtent(False, VI.createByReal(dist * MM))
    if body:
        ei.participantBodies = [body]
    f = ext.add(ei)
    f.name = name
    return f


def sketch(root, z, name):
    sk = root.sketches.add(plane(root, z))
    sk.name = name
    sk.isVisible = False
    return sk


def box(root, name, x0, x1, y0, y1, z0, z1, op, body=None):
    sk = sketch(root, z0, name)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(x0 * MM, y0 * MM, 0), P3.create(x1 * MM, y1 * MM, 0))
    return extrude(root, z0, sk.profiles.item(0), z1 - z0, op, name, body)


def outer_profile(sk):
    return max(sk.profiles, key=lambda p: p.areaProperties().area)


def build(root):
    """The whole ring as used (plate top at z = 0), then cut into its four corners."""
    new, cut = adsk.fusion.FeatureOperations.NewBodyFeatureOperation, adsk.fusion.FeatureOperations.CutFeatureOperation
    off = CLR + WALL
    zb = -SKIRT_D - UNDER_T
    sk = sketch(root, zb, 'Large frame outline')
    rrect(sk, PLATE_W + 2 * off, PLATE_D + 2 * off, PLATE_R + off)
    ring = extrude(root, zb, outer_profile(sk), SKIRT_D + UNDER_T + LIP_T, new, 'Large frame').bodies.item(0)
    # lower lip: everything more than UNDER_IN inside the skirt is cut away under the plate
    sk = sketch(root, zb, 'Large frame under-lip opening')
    rrect(sk, PLATE_W + 2 * CLR - 2 * UNDER_IN, PLATE_D + 2 * CLR - 2 * UNDER_IN, PLATE_R)
    extrude(root, zb, outer_profile(sk), UNDER_T, cut, 'Large frame under-lip opening', ring)
    sk = sketch(root, -SKIRT_D, 'Large frame plate pocket')
    rrect(sk, PLATE_W + 2 * CLR, PLATE_D + 2 * CLR, PLATE_R + CLR)
    extrude(root, -SKIRT_D, outer_profile(sk), SKIRT_D, cut, 'Large frame plate pocket', ring)
    wx, wy = AREA[0] / 2 + WIN_CLR, AREA[1] / 2 + WIN_CLR
    sk = sketch(root, 0, 'Large frame window')
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(-wx * MM, -wy * MM, 0), P3.create(wx * MM, wy * MM, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                P3.create(sx * (wx - RELIEF_R * 0.3) * MM, sy * (wy - RELIEF_R * 0.3) * MM, 0), RELIEF_R * MM)
    profs = adsk.core.ObjectCollection.create()
    for p in sk.profiles:
        if p.areaProperties().area < (2 * wx * 2 * wy + 10) * MM * MM:    # the window and its reliefs, not the ring
            profs.add(p)
    extrude(root, 0, profs, LIP_T, cut, 'Large frame window', ring)
    # mat-tab reliefs through the side wall at the rear-right and front-left corners
    xo, yo = PLATE_W / 2, PLATE_D / 2
    for sx, sy in ((1, 1), (-1, -1)):
        y0, y1 = sorted((sy * (yo - TAB[0]), sy * (yo - TAB[1])))
        x0, x1 = sorted((sx * xo, sx * (xo + off + 1)))
        # the tab sticks out at mat level, under the lip: a low slot through the wall, the lip stays whole
        box(root, 'Large frame tab relief', x0, x1, y0, y1, -1.5, 0.4, cut, ring)
    # cut the ring into four corner pieces: everything farther than LEG from a corner goes
    gx, gy = PLATE_W / 2 - LEG, PLATE_D / 2 - LEG
    box(root, 'Large frame split X', -gx, gx, -yo - off - 1, yo + off + 1, zb - 0.1, LIP_T + 0.1, cut, ring)
    box(root, 'Large frame split Y', -xo - off - 1, xo + off + 1, -gy, gy, zb - 0.1, LIP_T + 0.1, cut, None)
    corners = list(root.bRepBodies)          # the cuts leave exactly the four corners (Fusion renames the pieces)
    if len(corners) != 4:
        raise RuntimeError('expected 4 corner pieces, got %d' % len(corners))
    names = {(-1, -1): 'O1 Large corner front-left (tab relief)', (1, 1): 'O1 Large corner rear-right (tab relief)',
             (1, -1): 'O1 Large corner front-right', (-1, 1): 'O1 Large corner rear-left'}
    for b in corners:
        c = b.boundingBox
        key = (1 if c.maxPoint.x + c.minPoint.x > 0 else -1, 1 if c.maxPoint.y + c.minPoint.y > 0 else -1)
        b.name = names[key]
    return corners


def fit_check(root, des, corners):
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    sk = sketch(root, -PLATE_T, 'Fit check plate')
    rrect(sk, PLATE_W, PLATE_D, PLATE_R)
    plate = extrude(root, -PLATE_T, sk.profiles.item(0), PLATE_T, new, 'Fit check plate').bodies.item(0)
    plate.name = 'Fit check plate (%g x %g)' % (PLATE_W, PLATE_D)
    sk = sketch(root, 0, 'Fit check insert')
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(-AREA[0] / 2 * MM, -AREA[1] / 2 * MM, 0),
                                                     P3.create(AREA[0] / 2 * MM, AREA[1] / 2 * MM, 0))
    ins = extrude(root, 0, sk.profiles.item(0), INSERT_T, new, 'Fit check insert').bodies.item(0)
    ins.name = 'Fit check insert (330 x 420 x %.1f)' % INSERT_T
    ents = adsk.core.ObjectCollection.create()
    for b in corners + [plate, ins]:
        ents.add(b)
    ii = des.createInterferenceInput(ents)
    ii.areCoincidentFacesIncluded = False
    res = des.analyzeInterference(ii)
    mm = adsk.core.Application.get().measureManager
    print('interference (touching excluded): %s' % ([('%s / %s' % (r.entityOne.name, r.entityTwo.name)) for r in res] or 'none'))
    print('gaps: corner-plate %.2f, corner-insert %.2f mm' % (
        min(mm.measureMinimumDistance(c, plate).value for c in corners) * 10,
        min(mm.measureMinimumDistance(c, ins).value for c in corners) * 10))
    for b in (plate, ins):
        b.opacity = 0.35


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    corners = build(root)
    for b in corners:
        bb = b.boundingBox
        print('%-42s %.1f x %.1f x %.1f mm, %.1f g PLA' % (b.name, (bb.maxPoint.x - bb.minPoint.x) * 10,
              (bb.maxPoint.y - bb.minPoint.y) * 10, (bb.maxPoint.z - bb.minPoint.z) * 10, b.volume * 1.24))
    print('lip widths: sides %.1f mm, front/back %.1f mm (plate %g x %g)' % (
        (PLATE_W - AREA[0]) / 2 - WIN_CLR, (PLATE_D - AREA[1]) / 2 - WIN_CLR, PLATE_W, PLATE_D))
    fit_check(root, des, corners)
