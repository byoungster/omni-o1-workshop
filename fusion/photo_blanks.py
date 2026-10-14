"""Standard photo-size blanks (Autodesk Fusion API script).

Builds all 11 sizes (2R-12R) as bodies in the active design, side by side. Everything is driven by
user parameters (Modify > Change Parameters): card_t and <size>_w / <size>_h.
Blanks are plain by default: the storage trays carry the size, and a debossed label thins the blank
so light shows through it. Set LABELS = True to deboss the size name into the top face again.
Print with the smooth PEI plate underneath; the bed side is the clean face for UV printing.
Run from Fusion's Scripts dialog or an MCP script runner.
"""
import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

CARD_T = '1 mm'       # blank thickness
LABELS = False        # plain blanks diffuse light evenly; True debosses the size name
DEBOSS_D = '0.2 mm'   # label depth (1 layer at 0.2 mm; deeper labels can show through the photo face)
LABEL_H = '30 mm'     # default label height

# label, parameter prefix, width mm, height mm, label height (expr or None for LABEL_H), description
SIZES = [
    ('2R',   'r2',   64,  89,  '19 mm', 'Wallet / 2R (2.5 x 3.5 in)'),
    ('3R',   'r3',   89,  127, '27 mm', '3R (3.5 x 5 in)'),
    ('4R',   'r4',   102, 152, None,    '4R (4 x 6 in)'),
    ('5R',   'r5',   127, 178, None,    '5R (5 x 7 in)'),
    ('6R',   'r6',   152, 203, None,    '6R (6 x 8 in)'),
    ('8R',   'r8',   203, 254, None,    '8R (8 x 10 in)'),
    ('S8R',  's8r',  203, 305, None,    'S8R (8 x 12 in)'),
    ('10R',  'r10',  254, 305, None,    '10R (10 x 12 in)'),
    ('S10R', 's10r', 254, 381, None,    'S10R (10 x 15 in)'),
    ('11R',  'r11',  279, 356, None,    '11R (11 x 14 in)'),
    ('12R',  'r12',  305, 381, None,    '12R (12 x 15 in)'),
]
GAP = 20  # mm between blanks in the layout row


def run(_context: str):
    des = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    up = des.userParameters

    def param(name, expr, comment):
        p = up.itemByName(name)
        if p:
            p.expression = expr
            p.comment = comment
        else:
            up.add(name, VI.createByString(expr), 'mm', comment)

    param('card_t', CARD_T, 'Blank thickness (all sizes)')
    if LABELS:
        param('deboss_d', DEBOSS_D, 'Label deboss depth')
        param('label_h', LABEL_H, 'Label text height (default)')
    for lbl, pre, w, h, lh, desc in SIZES:
        param(pre + '_w', '%d mm' % w, desc + ' width')
        param(pre + '_h', '%d mm' % h, desc + ' height')
        if lh and LABELS:
            param(pre + '_label_h', lh, lbl + ' label height (narrow blank)')

    if LABELS:
        pin = root.constructionPlanes.createInput()
        pin.setByOffset(root.xYConstructionPlane, VI.createByString('card_t'))
        top = root.constructionPlanes.add(pin)
        top.name = 'Top Face'
        top.isLightBulbOn = False

    extrudes = root.features.extrudeFeatures
    x = 0.0
    for i, (lbl, pre, w, h, lh, _) in enumerate(SIZES):
        if i:
            x += SIZES[i - 1][2] / 2 + GAP + w / 2
        x0, y0, hw, hh = x * MM, h / 2 * MM, w / 2 * MM, h / 2 * MM  # bottom edges aligned on y = 0

        # Outline: rectangle centred on a fixed point, sized by parameters (fully constrained)
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.name = lbl + ' Outline'
        sl = sk.sketchCurves.sketchLines
        lines = sl.addTwoPointRectangle(P3.create(x0 - hw, y0 - hh, 0), P3.create(x0 + hw, y0 + hh, 0))
        gc = sk.geometricConstraints
        for l in lines:
            kinds = {c.objectType for c in l.geometricConstraints}
            horizontal = abs(l.startSketchPoint.geometry.y - l.endSketchPoint.geometry.y) < 1e-6
            if horizontal and adsk.fusion.HorizontalConstraint.classType() not in kinds:
                gc.addHorizontal(l)
            elif not horizontal and adsk.fusion.VerticalConstraint.classType() not in kinds:
                gc.addVertical(l)
        pts = [p for l in lines for p in (l.startSketchPoint, l.endSketchPoint)]
        diag = sl.addByTwoPoints(min(pts, key=lambda p: p.geometry.x + p.geometry.y),
                                 max(pts, key=lambda p: p.geometry.x + p.geometry.y))
        diag.isConstruction = True
        centre = sk.sketchPoints.add(P3.create(x0, y0, 0))
        centre.isFixed = True
        gc.addMidPoint(centre, diag)
        horiz = next(l for l in lines if abs(l.startSketchPoint.geometry.y - l.endSketchPoint.geometry.y) < 1e-6)
        vert = next(l for l in lines if abs(l.startSketchPoint.geometry.x - l.endSketchPoint.geometry.x) < 1e-6)
        dims = sk.sketchDimensions
        dims.addDistanceDimension(horiz.startSketchPoint, horiz.endSketchPoint,
                                  adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                                  P3.create(x0, y0 + hh + 1.5, 0)).parameter.expression = pre + '_w'
        dims.addDistanceDimension(vert.startSketchPoint, vert.endSketchPoint,
                                  adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
                                  P3.create(x0 + hw + 1.5, y0, 0)).parameter.expression = pre + '_h'

        ext = extrudes.addSimple(sk.profiles.item(0), VI.createByString('card_t'),
                                 adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext.name = lbl + ' Blank'
        body = ext.bodies.item(0)
        body.name = lbl + ' Blank'

        if not LABELS:
            continue
        # Size label, centred, debossed into the top face
        sk2 = root.sketches.add(top)
        sk2.name = lbl + ' Label'
        bx, by = hw - 3 * MM, min(hh - 3 * MM, 3.0)
        ti = sk2.sketchTexts.createInput3("'%s'" % lbl, VI.createByString(pre + '_label_h' if lh else 'label_h'))
        ti.fontName = 'Arial Black'
        ti.setAsMultiLine(P3.create(x0 - bx, y0 - by, 0), P3.create(x0 + bx, y0 + by, 0),
                          adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                          adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
        txt = sk2.sketchTexts.add(ti)
        ei = extrudes.createInput(txt, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString('deboss_d')),
                            adsk.fusion.ExtentDirections.NegativeExtentDirection)
        ei.participantBodies = [body]
        extrudes.add(ei).name = lbl + ' Deboss'

    for lbl, pre, w, h, lh, _ in SIZES:
        bb = root.bRepBodies.itemByName(lbl + ' Blank').boundingBox
        print('%-5s %7.2f x %7.2f x %.2f mm' % (lbl, (bb.maxPoint.x - bb.minPoint.x) * 10,
                                               (bb.maxPoint.y - bb.minPoint.y) * 10, (bb.maxPoint.z - bb.minPoint.z) * 10))
