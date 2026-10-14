"""Stackable storage trays for the Omni O1 photo blanks (run through Fusion's MCP script runner).

Each tray holds CAP blanks flat. A tray's inset foot drops into the rebate of the
tray below; a lid (printed upside down) caps the top tray of a stack. A front notch
runs the full height so the stack edge is visible against tick marks (1 blank = 1 mm).
DISPENSER trays add a one-blank-tall slot across the front at floor level, above the stacking foot,
and a finger notch in the back wall: push the bottom blank out of the front while trays stay stacked.
Trays too long for BED are split in two with a dovetail seam (glue together).
Always builds into a new document, so it never touches an open design.
"""
import math
import adsk.core, adsk.fusion


VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

# Blanks that fit a 256 mm bed (label, width mm, height mm)
SIZES = [('2R', 64, 89), ('3R', 89, 127), ('4R', 102, 152), ('5R', 127, 178),
         ('6R', 152, 203), ('8R', 203, 254)]

CAP = 20          # blanks per tray
BLANK_T = 1.0
CLR = 0.75        # blank-to-pocket clearance per side
WALL = 2.4
RIM = 1.2         # outer rim left at the stacking rebate
FIT = 0.2         # foot/plug clearance inside the rebate
DISPENSER = True  # front slot at floor level + rear push notch (pull blanks while stacked)
SLOT_H = 1.6      # dispenser slot height: one 1 mm blank passes, two don't
LINTEL = 2.0      # solid strip above the slot: bridges side wall to side wall and stops the stack
FLOOR = 1.6
REB = 3.0         # rebate depth = foot height
HEAD = 1.0        # headroom above a full stack plus the foot of the tray above
R_POCKET = 2.0    # <= 3.4 x CLR so square blank corners still clear
NOTCH_W = 25.0
LID_T = 2.0
PLUG_H = 2.8
PLUG_WALL = 1.6
BED = 256.0
KERF = 0.25       # dovetail seam gap
LABEL_D = 0.6
TICK_D = 0.4
GAP = 25.0
LID_ROW_Y = -330.0

CHAMF = RIM + FIT                     # foot inset; 45 deg transition height
if DISPENSER:
    FLOOR = REB + CHAMF + 0.4         # raise the floor above the stacking foot so the slot clears it
POCKET_D = CAP * BLANK_T + REB + HEAD
TRAY_H = FLOOR + POCKET_D
R_OUT = R_POCKET + WALL


def dims(w, h):
    W, H = w + 2 * (CLR + WALL), h + 2 * (CLR + WALL)
    return W, H


def label_h(lbl, W):
    flat = (W - NOTCH_W) / 2 - R_OUT
    return min(9.0, math.floor(0.8 * flat / (0.99 * len(lbl))))


# ---------------------------------------------------------------- sketch helpers
def near(curve, x, y):
    a, b = curve.startSketchPoint, curve.endSketchPoint
    da = (a.geometry.x - x) ** 2 + (a.geometry.y - y) ** 2
    db = (b.geometry.x - x) ** 2 + (b.geometry.y - y) ** 2
    return a if da < db else b


def rrect(sk, cx, cy, w, h, r):
    """Closed rounded rectangle (mm) on an XY-parallel sketch."""
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    x0, x1, y0, y1, r = (cx - w / 2) * MM, (cx + w / 2) * MM, (cy - h / 2) * MM, (cy + h / 2) * MM, r * MM
    k = r * (1 - 1 / math.sqrt(2))
    l0 = L.addByTwoPoints(P3.create(x0 + r, y0, 0), P3.create(x1 - r, y0, 0))
    a0 = A.addByThreePoints(l0.endSketchPoint, P3.create(x1 - k, y0 + k, 0), P3.create(x1, y0 + r, 0))
    l1 = L.addByTwoPoints(near(a0, x1, y0 + r), P3.create(x1, y1 - r, 0))
    a1 = A.addByThreePoints(l1.endSketchPoint, P3.create(x1 - k, y1 - k, 0), P3.create(x1 - r, y1, 0))
    l2 = L.addByTwoPoints(near(a1, x1 - r, y1), P3.create(x0 + r, y1, 0))
    a2 = A.addByThreePoints(l2.endSketchPoint, P3.create(x0 + k, y1 - k, 0), P3.create(x0, y1 - r, 0))
    l3 = L.addByTwoPoints(near(a2, x0, y1 - r), P3.create(x0, y0 + r, 0))
    A.addByThreePoints(l3.endSketchPoint, P3.create(x0 + k, y0 + k, 0), l0.startSketchPoint)


def polygon(sk, pts):
    L = sk.sketchCurves.sketchLines
    first = prev = None
    for i in range(len(pts)):
        a = prev.endSketchPoint if prev else P3.create(pts[0][0] * MM, pts[0][1] * MM, 0)
        b = first.startSketchPoint if i == len(pts) - 1 else P3.create(pts[i + 1][0] * MM, pts[i + 1][1] * MM, 0)
        prev = L.addByTwoPoints(a, b)
        first = first or prev


def offset_polyline(pts, d):
    out = []
    for i, p in enumerate(pts):
        ns = []
        segs = []
        if i > 0:
            segs.append((pts[i - 1], p))
        if i < len(pts) - 1:
            segs.append((p, pts[i + 1]))
        for a, b in segs:
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy)
            ns.append((-dy / ln, dx / ln))
        mx, my = sum(n[0] for n in ns), sum(n[1] for n in ns)
        ml = math.hypot(mx, my)
        mx, my = mx / ml, my / ml
        s = d / (mx * ns[0][0] + my * ns[0][1])
        out.append((p[0] + mx * s, p[1] + my * s))
    return out


# ---------------------------------------------------------------- design helpers
class Ctx:
    def __init__(self, des):
        self.des = des
        self.root = des.rootComponent
        self.ext = self.root.features.extrudeFeatures
        self.planes = {}

    def plane(self, z):
        if z == 0:
            return self.root.xYConstructionPlane
        key = round(z, 4)
        if key not in self.planes:
            name = 'Z %.1f' % z
            pl = self.root.constructionPlanes.itemByName(name)
            if not pl:
                pi = self.root.constructionPlanes.createInput()
                pi.setByOffset(self.root.xYConstructionPlane, VI.createByReal(z * MM))
                pl = self.root.constructionPlanes.add(pi)
                pl.name = name
                pl.isLightBulbOn = False
            self.planes[key] = pl
        return self.planes[key]

    def sketch(self, z, name):
        sk = self.root.sketches.add(self.plane(z))
        sk.name = name
        sk.isVisible = False
        return sk

    def extrude(self, prof, dist, op, name, body=None, negative=False, taper=None):
        ei = self.ext.createInput(prof, op)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal(dist * MM)),
                            adsk.fusion.ExtentDirections.NegativeExtentDirection if negative
                            else adsk.fusion.ExtentDirections.PositiveExtentDirection,
                            VI.createByString('%g deg' % taper) if taper is not None else VI.createByReal(0))
        if body is not None:
            ei.participantBodies = [body]
        f = self.ext.add(ei)
        f.name = name
        return f

    def cut_through(self, prof, name, body):
        ei = self.ext.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ei.setOneSideExtent(adsk.fusion.ThroughAllExtentDefinition.create(),
                            adsk.fusion.ExtentDirections.PositiveExtentDirection)
        ei.participantBodies = [body]
        f = self.ext.add(ei)
        f.name = name
        return f


def outer_profile(sk):
    """Profile of a single closed loop sketch."""
    return sk.profiles.item(0)


def ring_profile(sk):
    for p in sk.profiles:
        if p.profileLoops.count == 2:
            return p
    raise RuntimeError('ring profile not found in ' + sk.name)


def front_faces(body, y_face, cx):
    """Largest planar face facing -Y at y_face on each side of the notch (the slot leaves thin strips).

    When the notch stops short of the bottom (dispenser trays) the front is one U-shaped face; it is
    then returned for both sides.
    """
    left = right = whole = None
    for f in body.faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.y + 1) > 1e-6 or abs(f.pointOnFace.y - y_face * MM) > 1e-6:
            continue
        bb = f.boundingBox
        if bb.maxPoint.x <= cx * MM and (left is None or f.area > left.area):
            left = f
        elif bb.minPoint.x >= cx * MM and (right is None or f.area > right.area):
            right = f
        elif whole is None or f.area > whole.area:
            whole = f
    if whole is not None and (left is None or whole.area > left.area) and (right is None or whole.area > right.area):
        return whole, whole
    return left, right


def face_text(ctx, sk, text, h, x0, x1, z, y, align):
    """Text along a construction line from model (x0,y,z) to (x1,y,z), mm."""
    a = sk.modelToSketchSpace(P3.create(x0 * MM, y * MM, z * MM))
    b = sk.modelToSketchSpace(P3.create(x1 * MM, y * MM, z * MM))
    path = sk.sketchCurves.sketchLines.addByTwoPoints(a, b)
    path.isConstruction = True
    ti = sk.sketchTexts.createInput3("'%s'" % text, VI.createByReal(h * MM))
    ti.fontName = 'Arial Black'
    ti.setAsAlongPath(path, True, align, 0)
    return sk.sketchTexts.add(ti)


def split_seam(ctx, body, cx, cy, W, H, name):
    """Cut a dovetail seam across the part at y = cy and name the two halves Front/Back."""
    pts = [(cx - W / 2 - 3, cy)]
    for k in (-1, 0, 1):
        xc = cx + k * W / 4
        pts += [(xc - 4, cy), (xc - 6, cy + 6), (xc + 6, cy + 6), (xc + 4, cy)]
    pts.append((cx + W / 2 + 3, cy))
    poly = offset_polyline(pts, KERF / 2) + list(reversed(offset_polyline(pts, -KERF / 2)))
    sk = ctx.sketch(0, name + ' Seam')
    polygon(sk, poly)
    ctx.cut_through(sk.profiles.item(0), name + ' Seam', body)
    parts = []
    for b in ctx.root.bRepBodies:
        bb = b.boundingBox
        if (bb.minPoint.x >= (cx - W / 2 - 1) * MM and bb.maxPoint.x <= (cx + W / 2 + 1) * MM
                and bb.minPoint.y >= (cy - H / 2 - 1) * MM and bb.maxPoint.y <= (cy + H / 2 + 1) * MM):
            parts.append(b)
    if len(parts) != 2:
        raise RuntimeError('%s seam produced %d bodies' % (name, len(parts)))
    parts.sort(key=lambda b: b.boundingBox.minPoint.y)
    parts[0].name, parts[1].name = name + ' Front', name + ' Back'
    return parts


# ---------------------------------------------------------------- parts
def build_tray(ctx, lbl, w, h, cx, cy):
    W, H = dims(w, h)
    n = lbl + ' Tray'
    sk = ctx.sketch(0, n + ' Foot')
    rrect(sk, cx, cy, W - 2 * CHAMF, H - 2 * CHAMF, R_OUT - CHAMF)
    body = ctx.extrude(outer_profile(sk), REB, adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                       n + ' Foot').bodies.item(0)
    body.name = n
    sk = ctx.sketch(REB, n + ' Taper')
    rrect(sk, cx, cy, W - 2 * CHAMF, H - 2 * CHAMF, R_OUT - CHAMF)
    ctx.extrude(outer_profile(sk), CHAMF, adsk.fusion.FeatureOperations.JoinFeatureOperation,
                n + ' Taper', body, taper=45)
    bb = body.boundingBox
    if abs((bb.maxPoint.x - bb.minPoint.x) - W * MM) > 1e-3:
        raise RuntimeError('taper went the wrong way: width %.3f mm' % ((bb.maxPoint.x - bb.minPoint.x) * 10))
    sk = ctx.sketch(REB + CHAMF, n + ' Wall')
    rrect(sk, cx, cy, W, H, R_OUT)
    ctx.extrude(outer_profile(sk), TRAY_H - REB - CHAMF, adsk.fusion.FeatureOperations.JoinFeatureOperation,
                n + ' Wall', body)
    sk = ctx.sketch(TRAY_H, n + ' Pocket')
    rrect(sk, cx, cy, w + 2 * CLR, h + 2 * CLR, R_POCKET)
    ctx.extrude(outer_profile(sk), POCKET_D, adsk.fusion.FeatureOperations.CutFeatureOperation,
                n + ' Pocket', body, negative=True)
    sk = ctx.sketch(TRAY_H, n + ' Rebate')
    rrect(sk, cx, cy, W - 2 * RIM, H - 2 * RIM, R_OUT - RIM)
    ctx.extrude(outer_profile(sk), REB, adsk.fusion.FeatureOperations.CutFeatureOperation,
                n + ' Rebate', body, negative=True)

    # Full-height front notch, biting into the floor so the bottom blank can be pushed up
    yo, yi, r = cy - H / 2, cy - H / 2 + WALL, NOTCH_W / 2
    # dispenser trays: the notch stops above the slot so a solid lintel spans the slot (printable bridge,
    # and it holds back every blank but the bottom one)
    sk = ctx.sketch(FLOOR + SLOT_H + LINTEL if DISPENSER else 0, n + ' Notch')
    L, A = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    la = L.addByTwoPoints(P3.create((cx - r) * MM, (yo - 1) * MM, 0), P3.create((cx + r) * MM, (yo - 1) * MM, 0))
    lb = L.addByTwoPoints(la.endSketchPoint, P3.create((cx + r) * MM, yi * MM, 0))
    lc = L.addByTwoPoints(P3.create((cx - r) * MM, yi * MM, 0), la.startSketchPoint)
    if DISPENSER:  # wall only: a hole in the floor would catch the blank sliding out
        L.addByTwoPoints(lb.endSketchPoint, lc.startSketchPoint)
    else:          # bite into the floor so the bottom blank can be pushed up from below
        A.addByThreePoints(lb.endSketchPoint, P3.create(cx * MM, (yi + r) * MM, 0), lc.startSketchPoint)
    ctx.cut_through(sk.profiles.item(0), n + ' Notch', body)

    if DISPENSER:
        # one-blank slot across the front wall, sitting on the raised floor
        pw = w + 2 * CLR
        sk = ctx.sketch(FLOOR, n + ' Dispenser Slot')
        sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((cx - pw / 2) * MM, (yo - 1) * MM, 0),
                                                         P3.create((cx + pw / 2) * MM, (yi + 0.01) * MM, 0))
        ctx.extrude(sk.profiles.item(0), SLOT_H, adsk.fusion.FeatureOperations.CutFeatureOperation,
                    n + ' Dispenser Slot', body)
        # full-height finger notch through the back wall to push the bottom blank forward
        yb = cy + H / 2
        sk = ctx.sketch(0, n + ' Push Notch')
        sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((cx - r) * MM, (yb - WALL - 0.01) * MM, 0),
                                                         P3.create((cx + r) * MM, (yb + 1) * MM, 0))
        ctx.cut_through(sk.profiles.item(0), n + ' Push Notch', body)

    # Front label (left of notch) and stock ticks + counts (right of notch)
    left, right = front_faces(body, yo, cx)
    lh = label_h(lbl, W)
    x_l0, x_l1 = cx - W / 2 + R_OUT, cx - r
    z_lo, z_hi = (FLOOR + SLOT_H + 0.8 if DISPENSER else REB + CHAMF + 0.5), TRAY_H - REB - 0.5
    sk = ctx.root.sketches.add(left)
    sk.name = n + ' Label'
    txt = face_text(ctx, sk, lbl, lh, x_l0, x_l1, (z_lo + z_hi) / 2 - lh / 2, yo,
                    adsk.core.HorizontalAlignments.CenterHorizontalAlignment)
    ctx.extrude(txt, LABEL_D, adsk.fusion.FeatureOperations.CutFeatureOperation, n + ' Label', body, negative=True)

    sk = ctx.root.sketches.add(right)
    sk.name = n + ' Stock Ticks'
    x_t0 = cx + r + 1.5
    for k in (5, 10, 15, 20):
        z = FLOOR + k * BLANK_T
        c0 = sk.modelToSketchSpace(P3.create(x_t0 * MM, yo * MM, (z - 0.4) * MM))
        c1 = sk.modelToSketchSpace(P3.create((x_t0 + 5) * MM, yo * MM, (z + 0.4) * MM))
        sk.sketchCurves.sketchLines.addTwoPointRectangle(c0, c1)
    profs = adsk.core.ObjectCollection.create()
    for p in sk.profiles:  # skip the projected face outline; keep only the tick rectangles
        bb = p.boundingBox
        dims_ = sorted((abs(bb.maxPoint.x - bb.minPoint.x), abs(bb.maxPoint.y - bb.minPoint.y)))
        if abs(dims_[0] - 0.08) < 0.005 and abs(dims_[1] - 0.5) < 0.005:  # exactly a 5 x 0.8 mm tick
            profs.add(p)
    if profs.count != 4:
        raise RuntimeError('expected 4 tick profiles, got %d' % profs.count)
    ctx.extrude(profs, TICK_D, adsk.fusion.FeatureOperations.CutFeatureOperation, n + ' Stock Ticks', body, negative=True)
    for k in (5, 10, 15, 20):
        z = FLOOR + k * BLANK_T
        t = face_text(ctx, sk, str(k), 4.0, x_t0 + 6.5, x_t0 + 30, z - 2.0, yo,
                      adsk.core.HorizontalAlignments.LeftHorizontalAlignment)
        ctx.extrude(t, TICK_D, adsk.fusion.FeatureOperations.CutFeatureOperation, '%s Stock %d' % (n, k), body,
                    negative=True)
    return body


def build_lid(ctx, lbl, w, h, cx, cy):
    W, H = dims(w, h)
    n = lbl + ' Lid'
    sk = ctx.sketch(0, n + ' Plate')
    rrect(sk, cx, cy, W, H, R_OUT)
    body = ctx.extrude(outer_profile(sk), LID_T, adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                       n + ' Plate').bodies.item(0)
    body.name = n
    sk = ctx.sketch(LID_T, n + ' Plug')
    pw, ph, pr = W - 2 * CHAMF, H - 2 * CHAMF, R_OUT - CHAMF
    rrect(sk, cx, cy, pw, ph, pr)
    rrect(sk, cx, cy, pw - 2 * PLUG_WALL, ph - 2 * PLUG_WALL, max(pr - PLUG_WALL, 0.5))
    ctx.extrude(ring_profile(sk), PLUG_H, adsk.fusion.FeatureOperations.JoinFeatureOperation, n + ' Plug', body)
    # Label on the outside (bed side while printing): reads correctly once flipped onto a tray
    bottom = next(f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                  and abs(f.boundingBox.maxPoint.z) < 1e-6)
    sk = ctx.root.sketches.add(bottom)
    sk.name = n + ' Label'
    a = sk.modelToSketchSpace(P3.create((cx - W / 2 + 5) * MM, (cy + 10) * MM, 0))
    b = sk.modelToSketchSpace(P3.create((cx + W / 2 - 5) * MM, (cy + 10) * MM, 0))
    path = sk.sketchCurves.sketchLines.addByTwoPoints(a, b)
    path.isConstruction = True
    ti = sk.sketchTexts.createInput3("'%s'" % lbl, VI.createByReal(2.0))
    ti.fontName = 'Arial Black'
    ti.setAsAlongPath(path, True, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, 0)
    txt = sk.sketchTexts.add(ti)
    ctx.extrude(txt, LABEL_D, adsk.fusion.FeatureOperations.CutFeatureOperation, n + ' Label', body, negative=True)
    return body


def layout():
    xs, x = {}, 0.0
    for i, (lbl, w, h) in enumerate(SIZES):
        W, _ = dims(w, h)
        if i:
            x += W / 2
        xs[lbl] = x
        x += W / 2 + GAP
    return xs


def report(ctx):
    for b in ctx.root.bRepBodies:
        bb = b.boundingBox
        print('%-16s %7.2f x %7.2f x %5.2f mm  %6.1f g PLA' % (
            b.name, (bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
            (bb.maxPoint.z - bb.minPoint.z) * 10, b.volume * 1.24))


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    ctx = Ctx(des)
    xs = layout()
    for lbl, w, h in SIZES:
        W, H = dims(w, h)
        tray = build_tray(ctx, lbl, w, h, xs[lbl], 0)
        lid = build_lid(ctx, lbl, w, h, xs[lbl], LID_ROW_Y)
        if max(W, H) > BED:
            split_seam(ctx, tray, xs[lbl], 0, W, H, lbl + ' Tray')
            split_seam(ctx, lid, xs[lbl], LID_ROW_Y, W, H, lbl + ' Lid')
    print('tray height %.1f mm, pocket %.1f mm deep' % (TRAY_H, POCKET_D))
    report(ctx)
