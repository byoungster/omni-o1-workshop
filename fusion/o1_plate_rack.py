"""Under-shelf rack for the xTool O1 Omni baseplates (Autodesk Fusion API script).

Two slots side by side, screwed up into the underside of a wooden shelf. Each slot takes either plate (both are
344 mm wide): the standard 344 x 434 plate, or the small 344 x 128 one riding on its ends. A plate slides in on
its edges with the sticky mat facing up, a few mm under the shelf, so dust can't settle on the mat.

Each slot has a left and a right C-rail, each printed in two halves (front and back) that lock with a dovetail
in the wall. Rail profile, bottom up:
- a ledge that carries the plate 10 mm in from its edge;
- a low guide lip that centres the plate. The mat's peel tab sticks 7 mm out past the plate edge at the top and
  rides over the lip;
- the outer wall, 9 mm out from the plate edge, clear of the tab;
- a top flange that hangs on #8 pan-head screws through keyhole slots. The slots run across the flange, so the
  keyholes print standing up (a teardrop head hole, no bridge). The screws sit inboard of the ledge, so a
  screwdriver reaches them from below through the empty slot.
A lead-in at the front guides the plate in, and a wall at the back stops it.

Installing (nothing to hold overhead while driving screws):
1. Join a rail's two halves on the bench: slide the back half's dovetail tongue into the front half's socket.
2. Mark the screws: hold the joined rail in place, front flush with the shelf front, and mark through the slot
   end of each keyhole (the end toward the plate). For the opposite rail, slide a plate into the first rail and
   hold the second rail against the plate's other edge, so the plate sets the spacing. Neighbouring slots' rails
   sit back to back.
3. Drive the screws, leaving 4 mm under each head.
4. Hold the rail 10 mm toward the plate's side of its final place, push it up so the heads pass through the round
   holes, slide it 10 mm outward (away from the plate) and snug the screws from below.

Modelled as installed: the shelf underside is z = TOP, the plate rests at z = 0 and slides along +y from the
front (y = 0). Each rail prints lying on its outer wall, with the ledge, lip and flange standing up: no overhangs
past 45 degrees and no supports. The export rotates them into that position. Always builds into a new document.
"""
import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1

PLATE_W = 344.0            # both plates (the small plate is 344 x 128 and rides on its ends)
PLATE_T = 16.6             # standard plate with its mat (user's measurement; the small one is 16.5)
LARGE_D, SMALL_D = 434.0, 128.0
TAB_OUT, TAB_CLR = 7.0, 2.0   # the mat's peel tab sticks out 7 mm at the top of the plate edge (user, 2026-10-16)
EDGE_CLR = 1.0             # guide lip to plate edge, per side
WEB_T = 3.0                # outer wall: the base layers when printed
LEDGE_T = 4.5              # 3.5 was marginal (SF 2.6) for a half-pulled plate tipping onto the ledge front (review)
LEDGE_IN = 10.0            # ledge reach under the plate
LIP_H = 6.0                # guide lip on the plate's lower edge, solid back to the wall; the tab passes over it.
                           # (A 45 degree lip left a notch on the ledge's tension side: a creep risk in PLA; review)
TOP_GAP = 5.0              # mat to flange: keeps dust off without touching the mat
FL_T = 3.5
FL_IN = 30.0               # flange reach inward, past the ledge, so a screwdriver reaches the screws from below
SCREW_X = 23.0             # screw line when hung (slot end), measured in from the plate edge; clear of the ledge
KEY_D, KEY_W, KEY_SLIDE = 9.6, 4.8, 10.0   # keyhole for #8 pan-head screws (8.4 mm head, 4.2 mm shank): head hole,
                                           # slot width, slide. Hang the rail, then slide it outward. Screws driven
                                           # up through a held rail were awkward overhead (user, 2026-10-16).
# The slot runs across the flange (along p), not along the rail: printed on its side, a slot along the rail left a
# ~15 mm bridge over the hole that sagged (user, 2026-10-17). Across, the head hole gets a 45 degree teardrop top.
SEG_L = 222.0              # each rail half; 2 x 222 = 444 = plate 434 + stop + front setback, and fits a 256 bed
SCREW_Y = (25.0, SEG_L / 2, SEG_L - 25.0)
STOP_T = 4.0
STOP_H = 12.0              # back stop height: below the small plate's mat tab (top 1 mm of the plate)
LEAD = 12.0                # front lead-in: the guide lip starts here, with a 45 degree flare
DT_L, DT_W0, DT_W1 = 8.0, 8.0, 12.0   # dovetail in the wall: length, root and tip width
DT_CLR = 0.15              # per side. Test pairs at 0.15 / 0.25 / 0.35 printed on the X1C: 0.15 fit best (user,
                           # 2026-10-17); the review had guessed 0.25 to allow for first-layer squish
DT_TEST = (0.15, 0.25, 0.35)   # dovetail test pairs
JOINT_CH = 0.6             # chamfer on the back half's leading ledge and lip edges, so a plate can't catch the joint
TEXT_H, TEXT_D = 9.0, 0.6
TEST_L = 40.0              # fit-test section

Z_FL = PLATE_T + TOP_GAP   # flange underside
TOP = Z_FL + FL_T          # shelf underside
P_WI = -(TAB_OUT + TAB_CLR)    # outer wall, inner face (relative to the plate edge; negative = outward)
P_WO = P_WI - WEB_T
ZC = Z_FL / 2              # dovetail centre height
SLOT_PITCH = PLATE_W - 2 * P_WO    # rails of neighbouring slots back to back

# rail profile (p, z): p is measured from the plate edge, positive under the plate
PROFILE = [(P_WO, -LEDGE_T), (LEDGE_IN, -LEDGE_T), (LEDGE_IN, 0.0), (-EDGE_CLR, 0.0), (-EDGE_CLR, LIP_H),
           (P_WI, LIP_H), (P_WI, Z_FL - 3.0), (P_WI + 3.0, Z_FL), (FL_IN, Z_FL), (FL_IN, TOP), (P_WO, TOP)]


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


def _pt(axis, mid, a, b):
    return {'z': (a, b, mid), 'y': (a, mid, b), 'x': (mid, a, b)}[axis]


def slab(root, axis, lo, hi, pts, op, name, body=None, circle=None):
    """Prism along `axis` from lo to hi. pts: polygon in the other two axes ((x,y) for z, (x,z) for y, (y,z) for x);
    or circle=((a, b), r)."""
    mid = (lo + hi) / 2
    sk = root.sketches.add(_plane(root, axis, mid))
    sk.name = name
    sk.isVisible = False
    if circle:
        (a, b), r = circle
        c = sk.modelToSketchSpace(P3.create(*[v * MM for v in _pt(axis, mid, a, b)]))
        sk.sketchCurves.sketchCircles.addByCenterRadius(c, r * MM)
    else:
        sp = [sk.modelToSketchSpace(P3.create(*[v * MM for v in _pt(axis, mid, a, b)])) for a, b in pts]
        L = sk.sketchCurves.sketchLines
        first = prev = None
        for i in range(len(sp)):
            prev = L.addByTwoPoints(prev.endSketchPoint if prev else sp[0],
                                    first.startSketchPoint if i == len(sp) - 1 else sp[i + 1])
            first = first or prev
    prof = max(sk.profiles, key=lambda p_: p_.areaProperties().area)
    ext = root.features.extrudeFeatures
    ei = ext.createInput(prof, op)
    ei.setSymmetricExtent(VI.createByReal((hi - lo) * MM), True)
    if body is not None:
        ei.participantBodies = [body]
    f = ext.add(ei)
    f.name = name
    return f


def rail(root, side, xe, kind, y0, label, length=None, dt_clr=DT_CLR, words=None):
    """One rail half. side +1: left rail (plate at +x of xe); -1: right rail. kind: 'front', 'back' or 'test'.
    A length shorter than SEG_L makes a dovetail test stub (no keyholes, no stop)."""
    X = lambda p: xe + side * p
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    L = length or (TEST_L if kind == 'test' else SEG_L)
    stub = L < 60 and kind != 'test'
    name = 'O1 plate rack %s' % label
    body = slab(root, 'y', y0, y0 + L, [(X(p), z) for p, z in PROFILE], new, name).bodies.item(0)
    body.name = name

    r, rs = KEY_D / 2, KEY_W / 2
    ph = SCREW_X - KEY_SLIDE                       # head hole; the slot runs from it toward the plate (+p)
    for sy in (() if stub else (L / 2,) if kind == 'test' else SCREW_Y):
        ys = y0 + sy
        slab(root, 'z', Z_FL - 1, TOP + 1, None, cut, name + ' keyhole head', body, circle=((X(ph), ys), r))
        c45 = r * 0.7071                           # teardrop: 45 degree roof toward +p (up when printed)
        slab(root, 'z', Z_FL - 1, TOP + 1, [(X(ph + c45), ys - c45), (X(ph + r * 1.4142), ys), (X(ph + c45), ys + c45),
             (X(ph), ys)], cut, name + ' keyhole teardrop', body)
        slab(root, 'z', Z_FL - 1, TOP + 1, [(X(ph), ys - rs), (X(SCREW_X), ys - rs), (X(SCREW_X), ys + rs),
             (X(ph), ys + rs)], cut, name + ' keyhole slot', body)
        slab(root, 'z', Z_FL - 1, TOP + 1, None, cut, name + ' keyhole end', body, circle=((X(SCREW_X), ys), rs))

    xw = sorted((X(P_WO), X(P_WI)))
    if kind in ('front', 'test'):     # lead-in: no lip for LEAD mm, then a 45 degree flare
        slab(root, 'z', 0.0, LIP_H + 1, [(X(p), y0 + y) for p, y in
             ((-7, -1), (0, -1), (0, LEAD + 4), (-1, LEAD + 4), (-5, LEAD), (-7, LEAD))], cut, name + ' lead-in', body)
    if kind == 'front':               # dovetail socket at the back end, through the wall
        ye, c = y0 + L, dt_clr
        slab(root, 'x', xw[0] - 1, xw[1] + 1, [(ye + 1, ZC - DT_W0 / 2 - c), (ye - DT_L - c, ZC - DT_W1 / 2 - c),
             (ye - DT_L - c, ZC + DT_W1 / 2 + c), (ye + 1, ZC + DT_W0 / 2 + c)], cut, name + ' dovetail socket', body)
    if kind == 'back':                # dovetail tongue at the front end, and the stop wall at the back
        slab(root, 'x', xw[0], xw[1], [(y0 + 1, ZC - DT_W0 / 2), (y0 - DT_L, ZC - DT_W1 / 2), (y0 - DT_L, ZC + DT_W1 / 2),
             (y0 + 1, ZC + DT_W0 / 2)], join, name + ' dovetail tongue', body)
        if not stub:
            slab(root, 'y', y0 + L - STOP_T, y0 + L, [(X(P_WI), 0.0), (X(LEDGE_IN), 0.0), (X(LEDGE_IN), STOP_H),
                 (X(P_WI), STOP_H)], join, name + ' stop', body)
        # chamfer the leading ledge and lip edges at the joint, so a plate pushed in can't catch a small step
        c = JOINT_CH
        slab(root, 'x', min(X(-EDGE_CLR), X(LEDGE_IN)) - 0.1, max(X(-EDGE_CLR), X(LEDGE_IN)) + 0.1,
             [(y0 - 0.1, 0.1), (y0 + c, 0.1), (y0 - 0.1, -c - 0.1)], cut, name + ' joint chamfer', body)
        slab(root, 'z', -0.1, LIP_H + 0.1, [(X(-EDGE_CLR + 0.1), y0 - 0.1), (X(-EDGE_CLR + 0.1), y0 + c),
             (X(-EDGE_CLR - c - 0.1), y0 - 0.1)], cut, name + ' joint lip chamfer', body)

    # lettering on the outer wall (the bed face when printed); reads from outside the rail
    face = max((f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                and abs(f.boundingBox.minPoint.x - X(P_WO) * MM) < 1e-4 and abs(f.boundingBox.maxPoint.x - X(P_WO) * MM) < 1e-4),
               key=lambda f: f.area)
    words = words or ('FIT' if kind == 'test' else 'OMNI O1  ' + label.split()[0] + ' ' + kind.upper())
    upright_text(root, body, face, words, 6.0 if (kind == 'test' or stub) else TEXT_H,
                 (X(P_WO), y0 + 6, ZC), (X(P_WO), y0 + L - 6, ZC), name + ' lettering')
    return body


def upright_text(root, body, face, words, h, a, b, name):
    """Deboss words on a face, centred between model points a and b (mm), upright (+Z up). Fusion lays text out
    along a path using the face sketch's own axes, whichever way the path runs, so on some faces it comes out
    upside down (it did on the left rails). Measure where it landed: below the path means upside down, so turn it
    180 degrees (both flips) and run the path along the top instead."""
    for flipped in (False, True):
        sk = root.sketches.add(face)
        sk.name = name
        sk.isVisible = False
        zp = a[2] + (h / 2 if flipped else -h / 2)
        p0, p1 = [sk.modelToSketchSpace(P3.create(x * MM, y * MM, zp * MM)) for x, y, _ in (a, b)]
        path = sk.sketchCurves.sketchLines.addByTwoPoints(p0, p1)
        path.isConstruction = True
        ti = sk.sketchTexts.createInput3("'%s'" % words, VI.createByReal(h * MM))
        ti.fontName = 'Arial Black'
        ti.setAsAlongPath(path, True, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, 0)
        ti.isHorizontalFlip = ti.isVerticalFlip = flipped
        t = sk.sketchTexts.add(ti)
        bb = t.boundingBox                               # sketch space
        mid = sk.sketchToModelSpace(P3.create((bb.minPoint.x + bb.maxPoint.x) / 2, (bb.minPoint.y + bb.maxPoint.y) / 2, 0))
        if flipped or mid.z * 10 > zp:
            ext = root.features.extrudeFeatures
            ei = ext.createInput(t, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ei.setDistanceExtent(False, VI.createByReal(-TEXT_D * MM))
            ei.participantBodies = [body]
            ext.add(ei).name = name
            return
        sk.deleteMe()


def check(root, rails, plates):
    tb = adsk.fusion.TemporaryBRepManager.get()

    def clash(body, dx=0.0, dy=0.0, dz=0.0):
        a = tb.copy(body)
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(dx * MM, dy * MM, dz * MM)
        tb.transform(a, m)
        tot = 0.0
        for r in rails:
            c = tb.copy(a)
            tb.booleanOperation(c, tb.copy(r), adsk.fusion.BooleanTypes.IntersectionBooleanType)
            tot += c.volume * 1000
        return tot
    for p in plates:
        print('%s: home %.2f | pulled out 100 / 300 mm %.2f / %.2f | shifted 1 mm sideways %.2f / %.2f | '
              'lifted 1 mm %.2f mm3 (all 0 = slides freely)' % (p.name, clash(p), clash(p, dy=-100), clash(p, dy=-300),
                                                               clash(p, dx=1), clash(p, dx=-1), clash(p, dz=1)))
        print('   dropped 0.5 mm %.2f mm3 (> 0 = it sits on the ledges)' % clash(p, dz=-0.5))


def stand_in(root, name, x0, y0, d, t):
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    b = slab(root, 'z', 0.0, t, [(x0, y0), (x0 + PLATE_W, y0), (x0 + PLATE_W, y0 + d), (x0, y0 + d)], new, name).bodies.item(0)
    b.name = name
    for xs in (x0 - TAB_OUT, x0 + PLATE_W):      # the mat's peel tab, both edges near the front corner
        slab(root, 'z', t - 1.0, t, [(xs, y0 + 15), (xs + TAB_OUT, y0 + 15), (xs + TAB_OUT, y0 + 45), (xs, y0 + 45)],
             join, name + ' tab', b)
    b.opacity = 0.35
    return b


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent

    # one slot as installed: left rail at the plate's x = 0 edge, right rail at x = PLATE_W
    rails = [rail(root, 1, 0.0, 'front', 0.0, 'L1 left front'), rail(root, 1, 0.0, 'back', SEG_L, 'L2 left back'),
             rail(root, -1, PLATE_W, 'front', 0.0, 'R1 right front'), rail(root, -1, PLATE_W, 'back', SEG_L, 'R2 right back')]
    home = 2 * SEG_L - STOP_T
    plates = [stand_in(root, 'Stand-in standard plate', 0.0, home - LARGE_D, LARGE_D, PLATE_T),
              stand_in(root, 'Stand-in small plate', 0.0, home - SMALL_D, SMALL_D, 16.5)]
    check(root, rails, plates[:1])
    check(root, rails, plates[1:])
    test = rail(root, 1, -150.0, 'test', 0.0, 'fit test section')
    stubs = []
    for i, c in enumerate(DT_TEST):     # pairs: socket end + tongue end, 25 mm each, labelled with the clearance
        x = -150.0 - 60.0 * (i + 1)
        stubs.append(rail(root, 1, x, 'front', 0.0, 'dovetail test %.2f socket' % c, 25.0, c, '%.2f' % c))
        stubs.append(rail(root, 1, x, 'back', 25.0, 'dovetail test %.2f tongue' % c, 25.0, c, '%.2f' % c))
    for i in range(0, len(stubs), 2):
        tb_ = adsk.fusion.TemporaryBRepManager.get()
        a_ = tb_.copy(stubs[i]); tb_.booleanOperation(a_, tb_.copy(stubs[i + 1]), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        print('%s / tongue overlap %.3f mm3 (0 = fits)' % (stubs[i].name, a_.volume * 1000))
    tb = adsk.fusion.TemporaryBRepManager.get()
    for b in rails + [test]:
        bb = b.boundingBox
        print('%-34s %6.1f x %6.1f x %5.1f mm, %5.1f g solid' % (b.name, (bb.maxPoint.x - bb.minPoint.x) * 10,
              (bb.maxPoint.y - bb.minPoint.y) * 10, (bb.maxPoint.z - bb.minPoint.z) * 10, b.volume * 1.24))
    print('rack: 2 slots, %.0f mm wide, hangs %.1f mm below the shelf; plate stops %.0f mm in from the rail front' % (
          SLOT_PITCH + PLATE_W - 2 * P_WO, TOP + LEDGE_T, home - LARGE_D))
