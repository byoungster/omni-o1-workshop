"""Batch jigs for the xTool O1 Omni flat bed: pocket grids for flat items (Autodesk Fusion API script).

Each jig covers a bed's print area (330 x 122 mm small plate, 330 x 420 mm large plate) with an evenly
spaced grid of pockets. Pockets are item thickness minus PROUD deep, so items sit slightly above the
jig and the O1's height sensing lands on the items, all on one plane. Corner reliefs let square
corners seat fully, and a finger notch at the front of each pocket lifts thin items out. Jigs larger
than the P1S bed are cut into tiles along straight seams; the tiles butt together on the plate
(held by the registration clips, or glued with CA). Dovetails were tried and chipped off slivers
where they crossed pockets and finger notches.

Matte, plain, contrasting jig colour (matte black for white blanks). Items that are themselves
3D printed shrink like the jig, so no shrink compensation is applied; for bought blanks (slate,
acrylic, metal) add ~0.3% to the item size. Always builds into a new document.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

BEDS = {'Small': (330.0, 122.0), 'Large': (330.0, 420.0)}  # print area (xTool also calls these mini/standard)
FLOOR = 0.8          # jig floor under each pocket
PROUD = 0.1          # item top sits this far above the jig
CLR = 0.2            # pocket clearance per side
MIN_WALL = 3.0       # minimum wall between pockets
MARGIN = 3.0         # minimum border at the jig edge
RELIEF_R = 1.0       # corner relief radius
NOTCH_R = 7.0        # finger notch radius
MAX_TILE = 250.0     # longest tile side that fits the P1S comfortably
GAP = 40.0           # spacing between jigs in the document

# name, item width, item height, item thickness (mm), beds to make it for
ITEMS = [
    ('2R photo blank', 64, 89, 1.0, ('Small', 'Large')),
    ('3R photo blank', 89, 127, 1.0, ('Small', 'Large')),
    ('4R photo blank', 102, 152, 1.0, ('Small', 'Large')),
    ('5R photo blank', 127, 178, 1.0, ('Large',)),
    ('6R photo blank', 152, 203, 1.0, ('Large',)),
    ('8R photo blank', 203, 254, 1.0, ('Large',)),
]


def layout(bed, w, h):
    """Best grid (count, cols, rows, pocket w, pocket h) for an item on a bed, trying both orientations."""
    bw, bh = BEDS[bed]
    best = None
    for pw, ph in ((w + 2 * CLR, h + 2 * CLR), (h + 2 * CLR, w + 2 * CLR)):
        nx = int((bw - 2 * MARGIN + MIN_WALL) // (pw + MIN_WALL))
        ny = int((bh - 2 * MARGIN + MIN_WALL) // (ph + MIN_WALL))
        if nx and ny and (best is None or nx * ny > best[0]):
            best = (nx * ny, nx, ny, pw, ph)
    return best


def centres(n, pocket, length):
    """Evenly spaced pocket centres along one axis (equal walls and borders)."""
    gap = (length - n * pocket) / (n + 1)
    return [gap * (i + 1) + pocket * (i + 0.5) for i in range(n)]


def cut_through(root, sk, prof, bodies, name):
    ext = root.features.extrudeFeatures
    ei = ext.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ei.setOneSideExtent(adsk.fusion.ThroughAllExtentDefinition.create(),
                        adsk.fusion.ExtentDirections.PositiveExtentDirection)
    if bodies:
        ei.participantBodies = bodies
    f = ext.add(ei)
    f.name = name
    return f


def split_at(root, bodies, axis, pos, name):
    """Split bodies with a plane at x=pos (axis 'x') or y=pos (axis 'y')."""
    base = root.yZConstructionPlane if axis == 'x' else root.xZConstructionPlane
    for sign in (1, -1):
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base, VI.createByReal(sign * pos * MM))
        pl = root.constructionPlanes.add(pi)
        o = pl.geometry.origin
        if abs((o.x if axis == 'x' else o.y) - pos * MM) < 1e-6:
            break
        pl.deleteMe()
    pl.isLightBulbOn = False
    coll = adsk.core.ObjectCollection.create()
    for b in bodies:
        coll.add(b)
    f = root.features.splitBodyFeatures.add(root.features.splitBodyFeatures.createInput(coll, pl, True))
    f.name = name


def seam_pos(centres_, pocket, length):
    """Seam position along one axis: the wall between pockets nearest the middle if both tiles still fit
    the P1S, otherwise the middle (the seam then crosses a pocket floor)."""
    walls = [(a + b) / 2 for a, b in zip(centres_, centres_[1:])]
    ok = [w for w in walls if w <= MAX_TILE and length - w <= MAX_TILE]
    return min(ok, key=lambda w: abs(w - length / 2)) if ok else length / 2


def build_jig(root, bed, item, w, h, t, x0, y0):
    count, nx, ny, pw, ph = layout(bed, w, h)
    bw, bh = BEDS[bed]
    jig_t = FLOOR + t - PROUD
    ext = root.features.extrudeFeatures
    name = '%s jig %s x%d' % (bed, item.replace(' photo blank', ''), count)

    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = name + ' Plate'
    sk.isVisible = False
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(x0 * MM, y0 * MM, 0),
                                                     P3.create((x0 + bw) * MM, (y0 + bh) * MM, 0))
    body = ext.addSimple(sk.profiles.item(0), VI.createByReal(jig_t * MM),
                         adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
    body.name = name

    # Pockets with corner reliefs, cut from the top
    pi = root.constructionPlanes.createInput()
    pi.setByOffset(root.xYConstructionPlane, VI.createByReal(jig_t * MM))
    top = root.constructionPlanes.add(pi)
    top.isLightBulbOn = False
    skp = root.sketches.add(top)
    skp.name = name + ' Pockets'
    skp.isVisible = False
    cxs, cys = centres(nx, pw, bw), centres(ny, ph, bh)
    for cx in cxs:
        for cy in cys:
            ax, ay = x0 + cx, y0 + cy
            skp.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((ax - pw / 2) * MM, (ay - ph / 2) * MM, 0),
                                                              P3.create((ax + pw / 2) * MM, (ay + ph / 2) * MM, 0))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    skp.sketchCurves.sketchCircles.addByCenterRadius(
                        P3.create((ax + sx * (pw / 2 - RELIEF_R * 0.3)) * MM, (ay + sy * (ph / 2 - RELIEF_R * 0.3)) * MM, 0),
                        RELIEF_R * MM)
    profs = adsk.core.ObjectCollection.create()
    for p in skp.profiles:
        profs.add(p)
    ei = ext.createInput(profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal((t - PROUD) * MM)),
                        adsk.fusion.ExtentDirections.NegativeExtentDirection)
    ei.participantBodies = [body]
    ext.add(ei).name = name + ' Pockets'

    # Finger notch through the jig at the front edge of each pocket
    skn = root.sketches.add(root.xYConstructionPlane)
    skn.name = name + ' Finger notches'
    skn.isVisible = False
    for cx in cxs:
        for cy in cys:
            skn.sketchCurves.sketchCircles.addByCenterRadius(P3.create((x0 + cx) * MM, (y0 + cy - ph / 2) * MM, 0),
                                                             NOTCH_R * MM)
    profs = adsk.core.ObjectCollection.create()
    for p in skn.profiles:
        profs.add(p)
    cut_through(root, skn, profs, [body], name + ' Finger notches')

    # Tiles that fit the P1S, along straight seams
    def mine():
        return [b for b in root.bRepBodies
                if b.boundingBox.minPoint.x >= (x0 - 1) * MM and b.boundingBox.maxPoint.x <= (x0 + bw + 1) * MM
                and b.boundingBox.minPoint.y >= (y0 - 1) * MM and b.boundingBox.maxPoint.y <= (y0 + bh + 1) * MM]
    sx, sy = seam_pos(cxs, pw, bw), seam_pos(cys, ph, bh)
    if bw > MAX_TILE:
        split_at(root, mine(), 'x', x0 + sx, name + ' Seam X')
    if bh > MAX_TILE:
        split_at(root, mine(), 'y', y0 + sy, name + ' Seam Y')
    tiles = mine()
    expected = (2 if bw > MAX_TILE else 1) * (2 if bh > MAX_TILE else 1)
    if len(tiles) != expected or min(b.volume for b in tiles) < 1.0:
        raise RuntimeError('%s: expected %d clean tiles, got %d (smallest %.2f cm3)' % (
            name, expected, len(tiles), min(b.volume for b in tiles)))
    for b in tiles:
        bb = b.boundingBox
        col = 'A' if (bb.minPoint.x + bb.maxPoint.x) / 2 < (x0 + sx) * MM or bw <= MAX_TILE else 'B'
        row = '1' if (bb.minPoint.y + bb.maxPoint.y) / 2 < (y0 + sy) * MM or bh <= MAX_TILE else '2'
        b.name = name + ('' if len(tiles) == 1 else ' tile %s%s' % (col, row))
    walls = ('wall' if sx in [(a + b) / 2 for a, b in zip(cxs, cxs[1:])] or bw <= MAX_TILE else 'pocket',
             'wall' if sy in [(a + b) / 2 for a, b in zip(cys, cys[1:])] or bh <= MAX_TILE else 'pocket')
    return name, count, nx, ny, len(tiles), jig_t, walls


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    y = {'Small': 0.0, 'Large': BEDS['Small'][1] + GAP}
    x = {'Small': 0.0, 'Large': 0.0}
    for item, w, h, t, beds in ITEMS:
        for bed in beds:
            name, count, nx, ny, ntiles, jig_t, walls = build_jig(root, bed, item, w, h, t, x[bed], y[bed])
            print('%-26s %2d pockets (%dx%d)  %d tile(s)  %.1f mm thick  seams in: X %s / Y %s' % (
                name, count, nx, ny, ntiles, jig_t, walls[0], walls[1]))
            x[bed] += BEDS[bed][0] + GAP
    print('bodies:', root.bRepBodies.count)
    worst = max(max((b.boundingBox.maxPoint.x - b.boundingBox.minPoint.x), (b.boundingBox.maxPoint.y - b.boundingBox.minPoint.y)) * 10
                for b in root.bRepBodies)
    print('largest tile side: %.1f mm' % worst)
