"""Slot stands for 1 mm photo plaques, plus a slot-width test comb (Autodesk Fusion API script).

The plaque's bottom edge drops into a slot that leans back LEAN degrees. The base reaches far enough
behind the slot to keep a tall plaque from tipping (about 15% of the plaque height). Print the test
comb first, find the slot width that holds your printed blanks snugly, then set SLOT_W.

Three styles share the same footprint:
  Minimal - smooth, chamfered (print with the photo_stands recipe)
  Fluted  - vertical ribs across the front face (photo_stands recipe)
  Rustic  - minimal geometry printed with fuzzy skin (photo_stands_rustic recipe); fuzzy skin also
            roughens the slot walls, so it gets a wider slot and its own test comb.
UV prints with raised texture are thicker than a plain blank; the Textured comb (2.2-3.4 mm) finds their slot.
Always builds into a new document, so it never touches an open design.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

PLAQUE_T = 1.0
SLOT_W = 1.4                        # 0.2 mm clearance per side; confirm with the test comb
COMB_WIDTHS = (1.2, 1.3, 1.4, 1.5, 1.6)
SLOT_W_RUSTIC = 1.8                 # fuzzy skin eats into the slot; confirm with the rustic comb
COMB_WIDTHS_RUSTIC = (1.6, 1.8, 2.0, 2.2, 2.4)
# UV prints with raised texture add 1 mm or more on top of the 1 mm blank: pick their slot with this comb
COMB_WIDTHS_TEXTURED = (2.2, 2.5, 2.8, 3.1, 3.4)
FLUTE_R = 1.5                       # fluted style: groove radius
FLUTE_PITCH = 5.0                   # groove spacing along the front face
STYLES = ('Minimal', 'Fluted', 'Rustic')
SLOT_DEPTH = 9.0                    # measured along the slot
LEAN = 15.0                         # degrees back from vertical
BASE_H = 14.0
FRONT = 14.0                        # slot top centre, measured from the front edge
CHAMFER = 2.0
LABEL_D = 0.6
MAX_LEN = 250.0                     # longest part that fits the P1S bed comfortably
GAP = 20.0

# label, US size, plaque width mm, plaque height mm (portrait)
SIZES = [('2R', '2.5x3.5', 64, 89), ('3R', '3.5x5', 89, 127), ('4R', '4x6', 102, 152),
         ('5R', '5x7', 127, 178), ('6R', '6x8', 152, 203), ('8R', '8x10', 203, 254)]


def depth_for(height):
    return FRONT + max(18.0, 0.15 * height + 6.0)


def profile_points(x0, depth):
    """Side profile (x = depth from the front edge, z = height) with chamfered top edges."""
    return [(x0, 0), (x0 + depth, 0), (x0 + depth, BASE_H - CHAMFER), (x0 + depth - CHAMFER, BASE_H),
            (x0 + CHAMFER, BASE_H), (x0, BASE_H - CHAMFER)]


def slot_points(x0, width):
    """Slot rectangle leaning back LEAN degrees, open above the top face."""
    a = math.radians(LEAN)
    d = (-math.sin(a), -math.cos(a))           # down the slot, toward the front
    n = (math.cos(a), -math.sin(a))            # across the slot
    top = (x0 + FRONT - d[0] * 2, BASE_H - d[1] * 2)   # start 2 mm above the top face
    bot = (top[0] + d[0] * (SLOT_DEPTH + 2), top[1] + d[1] * (SLOT_DEPTH + 2))
    h = width / 2
    return [(top[0] + n[0] * h, top[1] + n[1] * h), (bot[0] + n[0] * h, bot[1] + n[1] * h),
            (bot[0] - n[0] * h, bot[1] - n[1] * h), (top[0] - n[0] * h, top[1] - n[1] * h)]


def xz_plane(root, y):
    """Construction plane parallel to XZ at model Y = y (mm), whatever direction the XZ normal points."""
    if abs(y) < 1e-9:
        return root.xZConstructionPlane
    for sign in (1, -1):
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(root.xZConstructionPlane, VI.createByReal(sign * y * MM))
        pl = root.constructionPlanes.add(pi)
        if abs(pl.geometry.origin.y - y * MM) < 1e-6:
            pl.isLightBulbOn = False
            return pl
        pl.deleteMe()
    raise RuntimeError('could not place plane at y=%s' % y)


def polygon(sk, y, pts):
    L = sk.sketchCurves.sketchLines
    sp = [sk.modelToSketchSpace(P3.create(x * MM, y * MM, z * MM)) for x, z in pts]
    first = prev = None
    for i in range(len(sp)):
        a = prev.endSketchPoint if prev else sp[0]
        b = first.startSketchPoint if i == len(sp) - 1 else sp[i + 1]
        prev = L.addByTwoPoints(a, b)
        first = first or prev


def extrude_along_y(root, prof, length, op, body=None, name=''):
    """Extrude a profile drawn on an XZ-parallel plane toward +Y by `length` mm."""
    ext = root.features.extrudeFeatures
    for direction in (adsk.fusion.ExtentDirections.PositiveExtentDirection,
                      adsk.fusion.ExtentDirections.NegativeExtentDirection):
        ei = ext.createInput(prof, op)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal(length * MM)), direction)
        if body is not None:
            ei.participantBodies = [body]
        f = ext.add(ei)
        bb = f.bodies.item(0).boundingBox if f.bodies.count else None
        if op != adsk.fusion.FeatureOperations.NewBodyFeatureOperation or bb.maxPoint.y > 1e-6:
            f.name = name
            return f
        f.deleteMe()
    raise RuntimeError('extrude failed: ' + name)


def face_label(root, body, x_face, text, height, y0, y1, z, normal_x=1):
    """Deboss text on a planar face normal to X at x = x_face; the path runs y0 -> y1.

    Verified: on the back face (normal_x=+1) a path toward +Y reads left to right from behind.
    """
    face = next(f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                and normal_x * f.evaluator.getNormalAtPoint(f.pointOnFace)[1].x > 0.99
                and abs(f.pointOnFace.x - x_face * MM) < 1e-6)
    sk = root.sketches.add(face)
    sk.isVisible = False
    a = sk.modelToSketchSpace(P3.create(x_face * MM, y0 * MM, z * MM))
    b = sk.modelToSketchSpace(P3.create(x_face * MM, y1 * MM, z * MM))
    path = sk.sketchCurves.sketchLines.addByTwoPoints(a, b)
    path.isConstruction = True
    ti = sk.sketchTexts.createInput3("'%s'" % text, VI.createByReal(height * MM))
    ti.fontName = 'Arial Black'
    ti.setAsAlongPath(path, True, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, 0)
    txt = sk.sketchTexts.add(ti)
    ext = root.features.extrudeFeatures
    ei = ext.createInput(txt, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal(LABEL_D * MM)),
                        adsk.fusion.ExtentDirections.NegativeExtentDirection)
    ei.participantBodies = [body]
    ext.add(ei)


def largest_profile(sk):
    return max(sk.profiles, key=lambda p: p.areaProperties().area)


def build_stand(root, lbl, us, w, h, x0, y0=0.0, style='Minimal'):
    depth, length = depth_for(h), min(w + 6.0, MAX_LEN)
    sk = root.sketches.add(xz_plane(root, y0))
    sk.name = '%s %s Stand Profile' % (lbl, style)
    sk.isVisible = False
    polygon(sk, y0, profile_points(x0, depth))
    polygon(sk, y0, slot_points(x0, SLOT_W_RUSTIC if style == 'Rustic' else SLOT_W))
    body = extrude_along_y(root, largest_profile(sk), length, adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                           name='%s %s Stand' % (lbl, style)).bodies.item(0)
    body.name = '%s Stand %s (%s in)' % (lbl, style, us)
    if style == 'Fluted':
        # vertical half-round grooves across the front face, stopping below the top chamfer
        skf = root.sketches.add(root.xYConstructionPlane)
        skf.isVisible = False
        n = int((length - 2 * CHAMFER) // FLUTE_PITCH)
        start = y0 + (length - (n - 1) * FLUTE_PITCH) / 2
        for i in range(n):
            skf.sketchCurves.sketchCircles.addByCenterRadius(P3.create(x0 * MM, (start + i * FLUTE_PITCH) * MM, 0),
                                                             FLUTE_R * MM)
        profs = adsk.core.ObjectCollection.create()
        for p in skf.profiles:
            profs.add(p)
        ext = root.features.extrudeFeatures
        ei = ext.createInput(profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal((BASE_H - CHAMFER) * MM)),
                            adsk.fusion.ExtentDirections.PositiveExtentDirection)
        ei.participantBodies = [body]
        ext.add(ei).name = '%s Fluted grooves' % lbl
    face_label(root, body, x0 + depth, us, 6.0, y0, y0 + length, (BASE_H - CHAMFER) / 2 - 3.0)
    return body


def build_comb(root, x0, widths=COMB_WIDTHS, y0=0.0, tag=''):
    seg, wall = 10.0, 4.0
    length = len(widths) * (seg + wall) + wall
    depth = depth_for(89)
    sk = root.sketches.add(xz_plane(root, y0))
    sk.name = 'Slot Test Comb%s Profile' % tag
    sk.isVisible = False
    polygon(sk, y0, profile_points(x0, depth))
    body = extrude_along_y(root, sk.profiles.item(0), length,
                           adsk.fusion.FeatureOperations.NewBodyFeatureOperation, name='Slot Test Comb').bodies.item(0)
    body.name = 'Slot Test Comb%s (%s-%s mm)' % (tag, widths[0], widths[-1])
    for i, wdt in enumerate(widths):
        y = y0 + wall + i * (seg + wall)
        sks = root.sketches.add(xz_plane(root, y))
        sks.isVisible = False
        polygon(sks, y, slot_points(x0, wdt))
        extrude_along_y(root, largest_profile(sks), seg, adsk.fusion.FeatureOperations.CutFeatureOperation,
                        body, name='Comb slot %.1f' % wdt)
        # labels go on the back face, the orientation verified to read correctly (front-face text came out inverted)
        face_label(root, body, x0 + depth, '%.1f' % wdt, 4.0, y + seg / 2 - 6, y + seg / 2 + 6,
                   (BASE_H - CHAMFER) / 2 - 2.0)
    return body


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    row = MAX_LEN + 40.0                     # each style gets its own row along Y
    for r, style in enumerate(STYLES):
        y0 = r * row
        x = 0.0
        if style == 'Minimal':
            build_comb(root, x, COMB_WIDTHS, y0)
        elif style == 'Rustic':
            build_comb(root, x, COMB_WIDTHS_RUSTIC, y0, ' Rustic')
        x += depth_for(89) + GAP
        for lbl, us, w, h in SIZES:
            build_stand(root, lbl, us, w, h, x, y0, style)
            x += depth_for(h) + GAP
    build_comb(root, 0.0, COMB_WIDTHS_TEXTURED, len(STYLES) * row, ' Textured')
    for b in root.bRepBodies:
        bb = b.boundingBox
        print('%-32s %6.1f x %6.1f x %5.1f mm' % (
            b.name, (bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
            (bb.maxPoint.z - bb.minPoint.z) * 10))
