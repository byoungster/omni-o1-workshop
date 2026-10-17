"""Upright file racks for O1 jig sets and 12x12 in acrylic sheets, for flat shelving (Autodesk Fusion API script).

Each rack is two identical slotted combs screwed to the shelf one behind the other, like a dish rack. A jig set or
sheet stands on its long edge across both combs, in its own labelled slot, so you can flip through and lift out the
one you need.
- Large-plate jigs: 2R 3R 4R 12x12 5R 6R 8R. Each blank-jig set is 4 tiles; the 12x12 frame set sits in the middle.
- Small-plate jigs: 2R 3R FRAME 4R plus a spare. Each set is 2 tiles; the two frame halves sit in the middle.
- Acrylic: three 1/8 in, four 1/4 in, three 1/8 in sheets, kept in their protective film. The heavy 1/4 in sheets
  sit in the middle.
Layouts are symmetric, so the back comb can face either way and the slots still line up.

Setting up (a free-standing comb tips with ~0.15 N at the top of a 305 mm sheet, so screw them down):
1. Front comb: slot labels toward you, 15-20 mm in from the front ends of the items.
2. Back comb: the same way round, at the centre spacing below, slots in line with the front comb.
   Acrylic about 240 mm. Small jigs about 100 mm. Large jigs 145 mm, or 100 mm if any tile stands on a 165 mm edge.
3. Screw each foot to the shelf with a #8 countersunk wood screw, or use strong mounting tape.
4. Load from the middle slots outward, heaviest first. Lower items straight down. To take one out, lift it
   straight up, or slide it forward about 40 mm to clear the back comb, then lift. Never rock it sideways.
Acrylic needs a shelf at least 305 mm deep and about 360 mm of headroom to lift a sheet out.

Built as printed: base on the bed, slots open upward, no overhangs. Always builds into a new document.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1

COMB_H = 50.0              # room for 7 mm slot labels between the feet and the slot bottoms
SLOT_D = 32.0              # slot depth: holds a 220 mm tile upright
TOOTH = 5.0                # between slots: 3.5 left a 0.5 mm knife top and SF 1.3 with a hand pushing a sheet (review)
FLARE = 1.5                # lead-in at the slot tops, per side (leaves a 2 mm flat on each tooth)
R_ROOT = 1.2               # rounded slot bottoms: sharp roots doubled the tooth stress
FOOT_T, FOOT_L = 6.0, 18.0     # screw-down foot at each end: thickness, reach beyond the comb
SCREW_D, CSK_D = 4.6, 9.0      # #8 countersunk wood screw
LABEL_H, LABEL_D = 7.0, 0.6
HEADER_H = 8.0
CHAR_W = 0.95              # Arial Black caps and digits run ~0.95 x the text height wide (0.78 overlapped)

E8, Q4 = 4.6, 7.8          # acrylic slots: 1/8 in (2.8-3.2 + film), 1/4 in (5.6-6.4 + film)
# name, header, comb depth, end, [(slot label, width)], [(group label, first slot, last slot)] or None
RACKS = [
    ('Large plate jigs', 'LARGE JIGS', 25.0, 6.0,
     [('2R', 8.5), ('3R', 8.5), ('4R', 8.5), ('12', 13.0), ('5R', 8.5), ('6R', 8.5), ('8R', 8.5)], None),
    ('Small plate jigs', 'SMALL JIGS', 25.0, 6.0,
     [('2R', 5.5), ('3R', 5.5), ('FRAME', 19.0), ('4R', 5.5), ('', 5.5)], None),
    ('Acrylic sheets', 'ACRYLIC 12x12', 35.0, 10.0, [('', E8)] * 3 + [('', Q4)] * 4 + [('', E8)] * 3,
     [('1/8', 0, 2), ('1/4', 3, 6), ('1/8', 7, 9)]),
]


def _plane(root, axis, pos):
    base = {'x': root.yZConstructionPlane, 'y': root.xZConstructionPlane, 'z': root.xYConstructionPlane}[axis]
    if abs(pos) < 1e-9:
        return base
    for sign in (1, -1):
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base, VI.createByReal(sign * pos * MM))
        pl = root.constructionPlanes.add(pi)
        o = pl.geometry.origin
        if abs({'x': o.x, 'y': o.y, 'z': o.z}[axis] - pos * MM) < 1e-6:
            pl.isLightBulbOn = False
            return pl
        pl.deleteMe()
    raise RuntimeError('plane %s=%g' % (axis, pos))


def slab(root, axis, lo, hi, pts, op, name, body=None):
    """Prism along `axis` from lo to hi; pts in the other two axes ((x,y) for z, (x,z) for y, (y,z) for x)."""
    mid = (lo + hi) / 2
    sk = root.sketches.add(_plane(root, axis, mid))
    sk.name = name
    sk.isVisible = False
    pt = {'z': lambda a, b: (a, b, mid), 'y': lambda a, b: (a, mid, b), 'x': lambda a, b: (mid, a, b)}[axis]
    sp = [sk.modelToSketchSpace(P3.create(*[v * MM for v in pt(a, b)])) for a, b in pts]
    L = sk.sketchCurves.sketchLines
    first = prev = None
    for i in range(len(sp)):
        prev = L.addByTwoPoints(prev.endSketchPoint if prev else sp[0], first.startSketchPoint if i == len(sp) - 1 else sp[i + 1])
        first = first or prev
    ext = root.features.extrudeFeatures
    ei = ext.createInput(max(sk.profiles, key=lambda p_: p_.areaProperties().area), op)
    ei.setSymmetricExtent(VI.createByReal((hi - lo) * MM), True)
    if body is not None:
        ei.participantBodies = [body]
    f = ext.add(ei)
    f.name = name
    return f


def face_text(root, body, face, words, h, a, b, name, up):
    """Deboss words centred between model points a and b (mm), with the letters' up along model vector `up`.
    Fusion lays along-path text out from the face sketch's axes, so measure where it landed and turn it 180 degrees
    (both flips, path on the other edge) if it came out upside down."""
    n_out = face.evaluator.getNormalAtPoint(face.pointOnFace)[1]
    for flipped in (False, True):
        sk = root.sketches.add(face)
        sk.name = name
        sk.isVisible = False
        mirror = sk.xDirection.crossProduct(sk.yDirection).dotProduct(n_out) < 0   # sketch faces inward
        off = (h / 2 if flipped else -h / 2)
        p0, p1 = [sk.modelToSketchSpace(P3.create((x + up[0] * off) * MM, (y + up[1] * off) * MM, (z + up[2] * off) * MM))
                  for x, y, z in (a, b)]
        path = sk.sketchCurves.sketchLines.addByTwoPoints(p0, p1)
        path.isConstruction = True
        ti = sk.sketchTexts.createInput3("'%s'" % words, VI.createByReal(h * MM))
        ti.fontName = 'Arial Black'
        ti.setAsAlongPath(path, True, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, 0)
        ti.isHorizontalFlip = flipped != mirror
        ti.isVerticalFlip = flipped
        t = sk.sketchTexts.add(ti)
        bb = t.boundingBox
        m = sk.sketchToModelSpace(P3.create((bb.minPoint.x + bb.maxPoint.x) / 2, (bb.minPoint.y + bb.maxPoint.y) / 2, 0))
        c = [(a[i] + b[i]) / 2 for i in range(3)]
        rise = sum(((m.x, m.y, m.z)[i] / MM - c[i]) * up[i] for i in range(3))
        if flipped or rise > -h / 4:
            ei = root.features.extrudeFeatures.createInput(t, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ei.setSymmetricExtent(VI.createByReal(2 * LABEL_D * MM), True)
            ei.participantBodies = [body]
            root.features.extrudeFeatures.add(ei).name = name
            return
        sk.deleteMe()


def comb(root, rack, header, depth, end, slots, groups, x0, y0):
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    length = 2 * end + sum(w for _, w in slots) + TOOTH * (len(slots) - 1)
    name = 'O1 file rack %s comb' % rack.lower()
    body = slab(root, 'z', 0, COMB_H, [(x0, y0), (x0 + length, y0), (x0 + length, y0 + depth), (x0, y0 + depth)],
                new, name).bodies.item(0)
    body.name = name
    # screw-down feet at both ends
    for xa, xb in ((x0 - FOOT_L, x0 + 0.01), (x0 + length - 0.01, x0 + length + FOOT_L)):
        slab(root, 'z', 0, FOOT_T, [(xa, y0), (xb, y0), (xb, y0 + depth), (xa, y0 + depth)], join, name + ' foot', body)
    zb, zt = COMB_H - SLOT_D, COMB_H
    x = x0 + end
    centres = []
    for i, (lbl, w) in enumerate(slots):
        r = min(R_ROOT, w / 2 - 0.2)
        arc_l = [(x + r + r * math.cos(math.radians(a)), zb + r + r * math.sin(math.radians(a)))
                 for a in (180, 202.5, 225, 247.5, 270)]
        arc_r = [(x + w - r + r * math.cos(math.radians(a)), zb + r + r * math.sin(math.radians(a)))
                 for a in (270, 292.5, 315, 337.5, 360)]
        pts = [(x - FLARE, zt + 0.01), (x, zt - FLARE)] + arc_l + arc_r[1:] + [(x + w, zt - FLARE), (x + w + FLARE, zt + 0.01)]
        slab(root, 'y', y0 - 1, y0 + depth + 1, pts, cut, '%s slot %d' % (name, i), body)
        centres.append((lbl, x, x + w))
        x += w + TOOTH
    for xc in (x0 - FOOT_L / 2, x0 + length + FOOT_L / 2):
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.isVisible = False
        sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(xc * MM, (y0 + depth / 2) * MM, 0), SCREW_D / 2 * MM)
        ei = root.features.extrudeFeatures.createInput(sk.profiles.item(0), cut)
        ei.setDistanceExtent(False, VI.createByReal((FOOT_T + 1) * MM))
        ei.participantBodies = [body]
        root.features.extrudeFeatures.add(ei)
    tops = adsk.core.ObjectCollection.create()
    for e in body.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(c.center.z - FOOT_T * MM) < 1e-4 and abs(c.radius - SCREW_D / 2 * MM) < 1e-4:
            tops.add(e)
    ch = root.features.chamferFeatures
    ci = ch.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(tops, VI.createByReal((CSK_D - SCREW_D) / 2 * MM), False)
    ch.add(ci).name = name + ' countersinks'

    front = max((f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                 and f.evaluator.getNormalAtPoint(f.pointOnFace)[1].y < -0.99 and abs(f.pointOnFace.y - y0 * MM) < 1e-6),
                key=lambda f: f.area)
    zl = (FOOT_T + zb) / 2 + 1.0                        # label band under the slots, above the feet
    if groups is None:
        labels = [(lbl, xa, xb) for lbl, xa, xb in centres if lbl]
    else:
        labels = [(g, centres[i][1], centres[j][2]) for g, i, j in groups]
    for lbl, xa, xb in labels:
        h = min(LABEL_H, zb - FOOT_T - 2, (xb - xa + TOOTH - 2.0) / (CHAR_W * len(lbl)))
        face_text(root, body, front, lbl, h, (xa - 1, y0, zl), (xb + 1, y0, zl), '%s label %s' % (name, lbl), (0, 0, 1))
    yb = y0 + depth
    back = max((f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                and f.evaluator.getNormalAtPoint(f.pointOnFace)[1].y > 0.99 and abs(f.pointOnFace.y - yb * MM) < 1e-6),
               key=lambda f: f.area)
    face_text(root, body, back, header, min(HEADER_H, zb - FOOT_T - 2, (length - 6) / (CHAR_W * len(header))),
              (x0 + length - 3, yb, zl), (x0 + 3, yb, zl), name + ' header', (0, 0, 1))
    return body, length


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    y = 0.0
    for rack, header, depth, end, slots, groups in RACKS:
        body, length = comb(root, rack, header, depth, end, slots, groups, 0.0, y)
        print('%-34s %5.1f x %4.1f x %4.1f mm (%5.1f with feet), %5.1f g solid; print 2; slots %s' % (
            body.name, length, depth, COMB_H, length + 2 * FOOT_L, body.volume * 1.24,
            ' '.join('%s:%.1f' % (l or '-', w) for l, w in slots)))
        y += depth + 25
