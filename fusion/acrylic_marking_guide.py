"""Corner marking guide for acrylic sheets UV printed on the xTool O1 Omni (Autodesk Fusion API script).

One guide serves all four corners: two lips hook the sheet's edges at a corner, and a small hole HOLE_IN from
both edges takes a Sharpie, a pencil or an awl. The hole is a 45 degree funnel down to a short straight land, so
a nib or a sharpened pencil cone reaches the sheet and lands on centre. Mark all four corners, then drill
away from the guide, with the sheet clamped over scrap wood: a step bit in a hand drill, or a drill press.
(v1-v3 were drill guides. A 7.5 mm twist bit grabs as it breaks through 1/8 in acrylic, and a hand-held guide
locked to the sheet corner then spins the whole sheet; a spinning bit also wears and melts a PLA guide hole.
Nothing spinning touches this one. User's choice, 2026-10-16.)

The lips are shorter than the sheet is thick, so the guide sits flat on the sheet while the sheet lies on the
bench. A relief at the inside corner lets a burred or slightly rounded sheet corner seat fully.

Modelled as used (the sheet's top face at z = 0, the sheet at x > 0, y > 0). Print it flipped, top face down on
the plate with the lips pointing up: no overhangs, and the hole and the lips' inner faces come out true.
Always builds into a new document.
"""
import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1

HOLE_IN = 25.4             # hole centre from each sheet edge (1 in)
MARK_D = 2.5               # land hole: a Sharpie nib, pencil point or awl passes, and the mark lands within ~0.5 mm
                           # of centre (the mounting holes are drilled 7.5 mm afterwards)
LAND = 0.8                 # straight part of the hole above the sheet. A 1.5 mm cone on a 4 mm plate left a 2.5 mm
                           # bore too deep for a Sharpie nib or a pencil cone to reach the sheet (user, 2026-10-16)
LABEL = 'MARK'
SHEET_T = 3.0              # 1/8 in acrylic (nominal 3.175, often 2.8-3.0 measured)
LIP_D = 2.0                # lip depth below the sheet's top face: keep under SHEET_T
LIP_T = 4.0                # lip thickness
PLATE_T = 4.0              # plate thickness (the first 8 mm plate felt bulky; user, 2026-10-16)
SPAN = 45.0                # plate reach from each edge
R_CORNER = 3.0             # outer corners
R_RELIEF = 1.5             # inside corner relief for the sheet corner
CONE = PLATE_T - LAND      # 45 degree funnel from the top face (8.9 mm across) down to the land
TEXT_BIG, TEXT_SMALL = 8.0, 6.0   # bold lettering looks premium, and 3.5 mm letters' counters close up on the bed face
TEXT_D = 0.6               # three layers deep: crisp on the glossy bed face


def box(root, x0, y0, z0, x1, y1, z1, op, name, body=None):
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = name
    sk.isVisible = False
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(x0 * MM, y0 * MM, 0), P3.create(x1 * MM, y1 * MM, 0))
    return prism(root, sk.profiles.item(0), z0, z1, op, name, body)


def cylinder(root, x, y, r, z0, z1, op, name, body=None):
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = name
    sk.isVisible = False
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(x * MM, y * MM, 0), r * MM)
    return prism(root, sk.profiles.item(0), z0, z1, op, name, body)


def prism(root, prof, z0, z1, op, name, body):
    ext = root.features.extrudeFeatures
    ei = ext.createInput(prof, op)
    ei.startExtent = adsk.fusion.OffsetStartDefinition.create(VI.createByReal(z0 * MM))
    ei.setDistanceExtent(False, VI.createByReal((z1 - z0) * MM))
    if body:
        ei.participantBodies = [body]
    f = ext.add(ei)
    f.name = name
    return f


def text(root, s, x0, y0, x1, y1, body, h):
    pl_in = root.constructionPlanes.createInput()
    pl_in.setByOffset(root.xYConstructionPlane, VI.createByReal(PLATE_T * MM))
    pl = root.constructionPlanes.add(pl_in)
    pl.isLightBulbOn = False
    sk = root.sketches.add(pl)
    sk.isVisible = False
    ti = sk.sketchTexts.createInput2(s, h * MM)
    ti.setAsMultiLine(P3.create(x0 * MM, y0 * MM, 0), P3.create(x1 * MM, y1 * MM, 0),
                      adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                      adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    ti.fontName = 'Arial Black'
    t = sk.sketchTexts.add(ti)
    ext = root.features.extrudeFeatures
    ei = ext.createInput(t, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ei.setDistanceExtent(False, VI.createByReal(-TEXT_D * MM))
    ei.participantBodies = [body]
    ext.add(ei).name = 'Label ' + s


def run(_context: str):
    if LIP_D > SHEET_T - 0.5:
        raise RuntimeError('lips must stay at least 0.5 mm shorter than the sheet is thick')
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    new, cut = adsk.fusion.FeatureOperations.NewBodyFeatureOperation, adsk.fusion.FeatureOperations.CutFeatureOperation

    body = box(root, -LIP_T, -LIP_T, -LIP_D, SPAN, SPAN, PLATE_T, new, 'Guide').bodies.item(0)
    body.name = 'Acrylic corner marking guide (1 in)'
    box(root, 0, 0, -LIP_D - 1, SPAN + 1, SPAN + 1, 0, cut, 'Sheet', body)          # leaves the two lips
    cylinder(root, 0, 0, R_RELIEF, -LIP_D - 1, 0, cut, 'Corner Relief', body)
    cylinder(root, HOLE_IN, HOLE_IN, MARK_D / 2, -LIP_D - 1, PLATE_T + 1, cut, 'Marking Hole', body)

    corners = [(SPAN, SPAN), (SPAN, -LIP_T), (-LIP_T, SPAN), (-LIP_T, -LIP_T)]
    edges = adsk.core.ObjectCollection.create()
    for e in body.edges:
        ln = adsk.core.Line3D.cast(e.geometry)
        if ln and abs(ln.startPoint.z - ln.endPoint.z) > 1e-4 and any(
                abs(ln.startPoint.x - x * MM) < 1e-4 and abs(ln.startPoint.y - y * MM) < 1e-4 for x, y in corners):
            edges.add(e)
    if edges.count != 4:
        raise RuntimeError('expected 4 outer corner edges, found %d' % edges.count)
    fl = root.features.filletFeatures
    fi = fl.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, VI.createByReal(R_CORNER * MM), True)
    fl.add(fi).name = 'Outer Corners'

    top = None
    for e in body.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(c.center.z - PLATE_T * MM) < 1e-4 and abs(c.radius - MARK_D / 2 * MM) < 1e-4:
            top = e
    ch = root.features.chamferFeatures
    ci = ch.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(adsk.core.ObjectCollection.createWithArray([top]),
                                                      VI.createByReal(CONE * MM), False)
    ch.add(ci).name = 'Centring Cone'

    # '1 IN' in the band between the corner lips and the hole, LABEL above the hole
    cone_r = MARK_D / 2 + CONE
    text(root, '1 IN', 2, 2, SPAN - 2, HOLE_IN - cone_r - 1.5, body, TEXT_BIG)
    text(root, LABEL, 2, HOLE_IN + cone_r + 1.5, SPAN - 2, SPAN - 2, body, TEXT_SMALL)

    bb = body.boundingBox
    print('%s: %.1f x %.1f x %.1f mm, %.1f g solid; hole %.2f mm at %.1f mm from both edges; lips %.1f mm deep '
          '(sheet %.1f)' % (body.name, (bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
                            (bb.maxPoint.z - bb.minPoint.z) * 10, body.volume * 1.24, MARK_D, HOLE_IN, LIP_D,
                            SHEET_T))
