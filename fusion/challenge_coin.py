"""Challenge coin blank for UV printing on both faces (Autodesk Fusion API script).

Both faces are flat and plain: the UV printer prints the artwork. The bottom face prints against a smooth
PEI plate and the top face is ironed by the challenge_coin recipe, which also prints it at 100% infill so the
coin feels solid. Small chamfers on both faces and a fine reeded edge make it feel like a struck coin. Common
challenge coin sizes are 1.5, 1.75 and 2 in; set SIZES to build others. Always builds into a new document.
"""
import math

import adsk.core, adsk.fusion

VI = adsk.core.ValueInput
P3 = adsk.core.Point3D
MM = 0.1  # Fusion API lengths are cm

SIZES = [('1.75 in', 44.45)]   # label, diameter mm. Others: ('1.5 in', 38.1), ('2 in', 50.8)
THICK = 3.0                    # common challenge coin thickness
CHAMFER = 0.4                  # both face edges
REEDS = 90                     # grooves around the edge (0 for a plain edge)
REED_W, REED_D = 0.7, 0.3      # groove width and depth
GAP = 15.0


def build_coin(root, label, dia, x0):
    ext = root.features.extrudeFeatures
    name = 'Challenge Coin %s (%.1f x %.0f mm)' % (label, dia, THICK)
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.name = name
    sk.isVisible = False
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(x0 * MM, 0, 0), dia / 2 * MM)
    body = ext.addSimple(sk.profiles.item(0), VI.createByReal(THICK * MM),
                         adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
    body.name = name

    # chamfer the two circular face edges first (simple geometry), then cut the reeds through them
    edges = adsk.core.ObjectCollection.create()
    for e in body.edges:
        if adsk.core.Circle3D.cast(e.geometry):
            edges.add(e)
    ci = root.features.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, VI.createByReal(CHAMFER * MM), True)
    root.features.chamferFeatures.add(ci).name = name + ' Chamfers'

    if REEDS:
        # one groove through the full thickness at the edge, patterned around the axis
        skr = root.sketches.add(root.xYConstructionPlane)
        skr.name = name + ' Reed'
        skr.isVisible = False
        r = dia / 2
        skr.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((x0 + r - REED_D) * MM, -REED_W / 2 * MM, 0),
                                                          P3.create((x0 + r + 0.5) * MM, REED_W / 2 * MM, 0))
        prof = min(skr.profiles, key=lambda p: p.areaProperties().area)
        ei = ext.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ei.setDistanceExtent(False, VI.createByReal(THICK * MM))
        ei.participantBodies = [body]
        cut = ext.add(ei)
        cut.name = name + ' Reed'
        # pattern axis through the coin centre: the Z axis for a coin at the origin, else normal to its bottom face
        if abs(x0) < 1e-9:
            axis = root.zConstructionAxis
        else:
            bottom = min((f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType),
                         key=lambda f: f.pointOnFace.z)
            ai = root.constructionAxes.createInput()
            ai.setByNormalToFaceAtPoint(bottom, sk.sketchPoints.add(P3.create(x0 * MM, 0, 0)))
            axis = root.constructionAxes.add(ai)
            axis.isLightBulbOn = False
        ents = adsk.core.ObjectCollection.create()
        ents.add(cut)
        pi = root.features.circularPatternFeatures.createInput(ents, axis)
        pi.quantity = VI.createByReal(REEDS)
        pi.totalAngle = VI.createByString('360 deg')
        pi.isSymmetric = False
        root.features.circularPatternFeatures.add(pi).name = name + ' Reeding'
    return body


def run(_context: str):
    app = adsk.core.Application.get()
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = des.rootComponent
    x = 0.0
    for label, dia in SIZES:
        b = build_coin(root, label, dia, x)
        bb = b.boundingBox
        print('%s: %.2f x %.2f x %.2f mm, %.1f cm3, %.1f g PLA' % (
            b.name, (bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
            (bb.maxPoint.z - bb.minPoint.z) * 10, b.volume, b.volume * 1.24))
        x += dia + GAP
