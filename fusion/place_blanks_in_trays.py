"""Copy the 1 mm photo blanks from the blanks document into their storage trays (fit check / renders).

Blanks are copied as exact B-Rep (base feature), centred on each tray's pocket and resting on the floor.
"""
import adsk.core, adsk.fusion

FLOOR = 1.6   # tray floor thickness, mm (see storage_trays.py)
MM = 0.1
SIZES = ['2R', '3R', '4R', '5R', '6R', '8R']
APPEARANCES = ['Plastic - Glossy (White)', 'Plastic - Matte (White)', 'Paint - Enamel Glossy (White)']


def find_design(app, body_name):
    for d in app.documents:
        des = adsk.fusion.Design.cast(d.products.itemByProductType('DesignProductType'))
        if des and des.rootComponent.bRepBodies.itemByName(body_name):
            return d, des
    raise RuntimeError('no open document contains ' + body_name)


def white(app):
    for lib in app.materialLibraries:
        for n in APPEARANCES:
            try:
                a = lib.appearances.itemByName(n)
            except Exception:
                a = None
            if a:
                return a
    return None


def run(_context: str):
    app = adsk.core.Application.get()
    _, src = find_design(app, '5R Card')
    tdoc, dst = find_design(app, '5R Tray')
    tdoc.activate()
    root = dst.rootComponent
    tbm = adsk.fusion.TemporaryBRepManager.get()

    look = white(app)
    if look and not dst.appearances.itemByName(look.name):
        look = dst.appearances.addByCopy(look, look.name)
    elif look:
        look = dst.appearances.itemByName(look.name)

    base = root.features.baseFeatures.add()
    base.name = 'Blanks (fit check)'
    base.startEdit()
    placed = []
    for lbl in SIZES:
        sb = src.rootComponent.bRepBodies.itemByName(lbl + ' Card')
        sbb = sb.boundingBox
        tray = [b for b in root.bRepBodies if b.name.startswith(lbl + ' Tray')]
        xs = [b.boundingBox.minPoint.x for b in tray] + [b.boundingBox.maxPoint.x for b in tray]
        ys = [b.boundingBox.minPoint.y for b in tray] + [b.boundingBox.maxPoint.y for b in tray]
        tcx, tcy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(
            tcx - (sbb.minPoint.x + sbb.maxPoint.x) / 2,
            tcy - (sbb.minPoint.y + sbb.maxPoint.y) / 2,
            FLOOR * MM - sbb.minPoint.z)
        tmp = tbm.copy(sb)
        tbm.transform(tmp, m)
        root.bRepBodies.add(tmp, base)
        placed.append((lbl, tray))
    base.finishEdit()

    # Bodies come back from the base feature in insertion order; name them now
    if base.bodies.count != len(placed):
        raise RuntimeError('expected %d blank bodies, got %d' % (len(placed), base.bodies.count))
    ents = adsk.core.ObjectCollection.create()
    for i, (lbl, tray) in enumerate(placed):
        b = base.bodies.item(i)
        b.name = '%s Blank (1 mm)' % lbl
        if look:
            b.appearance = look
        ents.add(b)
        for t in tray:
            ents.add(t)
    ii = dst.createInterferenceInput(ents)
    ii.areCoincidentFacesIncluded = False
    res = dst.analyzeInterference(ii)
    print('appearance:', look.name if look else 'default')
    print('interferences (excluding touching faces):', res.count)

    mm = app.measureManager
    for lbl, tray in placed:
        b = root.bRepBodies.itemByName('%s Blank (1 mm)' % lbl)
        bb = b.boundingBox
        d_wall = min(mm.measureMinimumDistance(b, t).value for t in tray)
        print('%-3s blank %6.2f x %6.2f x %.2f mm, z %.2f-%.2f | min gap to tray %.3f mm (floor contact = 0)' % (
            lbl, (bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
            (bb.maxPoint.z - bb.minPoint.z) * 10, bb.minPoint.z * 10, bb.maxPoint.z * 10, d_wall * 10))
