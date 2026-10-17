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
DISPENSER = 'button'  # 'button': side push-button + lever; 'front': front press-down lever (v5, prototype);
                      # 'side': v3 wall slider; 'rear': finger notch; None: plain
SLOT_H = 1.9      # dispenser slot height: one 1 mm blank passes with room for bridge sag, two (2 mm) don't
LINTEL = 3.0      # solid strip above the slot: bridges side wall to side wall and stops the stack
# (v1 had a 1.6 mm slot under a 2 mm lintel; the bridge sagged until blanks bound in the slot)
# Button trays have no slot bridge at all: the front is open in the middle, and a stop grows out of each side
# wall (a short flat ledge, then a 45 degree underside) that holds back every blank but the bottom one by its
# corners. Nothing spans the opening, so nothing sags or strings. (The 65 mm slot bridge always drooped and
# left strings that caught the blank, even at 1.9 mm with reduced bridge flow.)
FRONT_GAP = 2.2       # gap under the stops as drawn. The flat ledge droops ~0.5 mm when printed, leaving ~1.7:
                      # the bottom blank passes freely and the next is still caught (a drawn 1.5 printed at ~1.0
                      # and caught the first blank too, 2026-10-15). 4R front-section tests at 2.0, 2.2 and 2.4
                      # all fed one blank and held the next; the full 4R tray at 2.0 was tight, so 2.2 for
                      # margin at every size (user, 2026-10-16)
FRONT_STOP = 3.0      # flat part of each stop, from the side wall (a short overhang, no bridge)
FRONT_STUB = 15.5     # each stop widens at 45 degrees to this, then runs straight up (room for the label)
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
SEAM_DY_BUTTON = -40.0   # button trays: seam 40 mm in front of centre, clear of the lever, button and sled ear
                         # (all at mid depth) and behind the spring pocket; it crosses only the straight groove
LABEL_D = 0.6
SIDE_LABEL_H = 16.0   # big size label on the left outer wall of button trays (the front stop only fits 5 mm)
TICK_D = 0.4
GAP = 25.0
LID_ROW_Y = -330.0
ONLY = ()         # sizes to build, e.g. ('2R',); () builds every size

# Side dispenser: a sled in a floor groove near the right wall, a zigzag spring printed on its front,
# and a knob whose arm passes through a window in the right wall and slides a dovetail into the sled.
SIDE_FLOOR = 6.0      # floor high enough that the knob arm clears the rim of the tray below
GROOVE_IN = 6.0       # groove centre, measured in from the right pocket wall
GROOVE_W = 6.6        # sled 6.0 + 0.3 clearance per side
GROOVE_D = 2.4        # groove depth below the floor
SLED_W = 6.0
SLED_H = 2.2          # sled top stays 0.2 below the floor
BLADE_UP = 0.7        # blade height above the floor: catches the bottom blank only
BLADE_T = 1.6         # blade thickness, front to back
TRAVEL = 15.0         # pushes ~10 mm of blank out of the front slot: enough to pinch
# Return spring: a short meander (serpentine) printed flat, with round U-bends. Sharp corners
# concentrate stress and crack printed springs. Bar strain ~ 3 * t * d / L^2: thinner bars and more of
# them last longer; thick, short springs are stiffer but strain more and wear out sooner. 0.8 mm (two
# perimeters) is the thinnest bar that prints reliably. PETG lasts longer than PLA.
SPRINGS = {
    'A': dict(beam=0.8, segs=11, pitch=3.0),   # long life, ~1.0% strain
    'B': dict(beam=0.8, segs=9, pitch=3.3),    # previous design, ~1.2%
    'C': dict(beam=1.2, segs=7, pitch=4.2),    # short and thick, ~2.4%: stiff, wears sooner
    # button dispenser: wider, taller bars and a bigger preload, so it holds the sled on its rest stop with
    # ~0.3 N and stays under ~0.9% bar strain (PLA creeps above ~1%; print it in PETG)
    'D': dict(beam=1.0, segs=10, pitch=3.4, span=28.0, h=4.0, preload=5.5),
}
SPRING = 'C'                 # spring on the main sled (C won the A/B/C sled test, 2026-10-14)
TEST_SPRINGS = ()            # extra sleds that fit the same tray, to compare by hand; () for none
SPRING_SPAN = 20.0    # bar length across the tray (centre line)
SPRING_H = 1.8
SPRING_PAD = 2.0      # rigid full-width seat pad at the far end
HEADER_T = 2.4        # rigid full-width header on the sled front; the spring grows out of it through a U-bend
SPRING_PRELOAD = 1.0  # spring is drawn 1 mm longer than its seat, so it holds the sled on its stop
# Knob: a low-profile slider set into the right wall. Its tab fills a window through the wall, so the wall
# guides it; a thin grip plate with a thumb rib sits just outside, and an arm runs under the floor to a T-head.
# Fit the knob through the window first, then drop the sled in: a T-slot through the sled closes around the
# head, so the knob can't fall out or pull free, and it's balanced over the wall instead of hanging off it.
# (v1: a 7 mm knob cantilevered off the wall on a tongue that sat loose in an open slot; it tipped, rocked
# out of the sled when pushed off-centre, and wedged in the window.)
KNOB_Z0 = SIDE_FLOOR - GROOVE_D + 0.2  # bottom of every knob feature (it prints flat on this face)
TAB_H, TAB_L = 1.9, 12.0  # tab in the wall window: height, length along the travel
WIN_CLR = 0.15        # window clearance above and below the tab
GRIP_T, GRIP_H, GRIP_L = 1.6, 8.0, 14.0  # grip plate outside the wall: thickness, height, length
GRIP_GAP = 0.3        # grip plate to wall face
RIB_T, RIB_W = 1.0, 2.0  # thumb rib on the grip's back edge; the thumb pushes it forward
ARM_T, ARM_W = 1.6, 2.4  # arm under the floor: thickness, width
HEAD_W, HEAD_L = 4.0, 1.6  # T-head on the end of the arm
NECK_X = 1.8          # T-slot neck length, from the sled's wall side
T_CLR = 0.15          # T-slot clearance per side

# Button dispenser (v4, after the v3 slider jammed): press a button on the right wall and a bell-crank lever turns
# its 5 mm into the sled's 15 mm (3:1). The parts meet only at a pivot and at pins in slots (Scotch yokes), so
# nothing is pushed off its own axis. Bottom up: the button runs in a closed tunnel through the right wall (guided
# along its whole length) beside the sled's groove; above them the lever lies in an open pocket under the blanks,
# its pins reaching down into a slot in the button and a slot in an ear on the sled. Fit the button from outside,
# drop the sled in, then the lever: the lever's pin keeps the button in, and the blanks keep the lever down.
# (v3 was pushed 11 mm off the sled's line with nothing to stop it twisting, and it jammed.)
BTN_FLOOR = 8.5               # floor raised 2.5 mm to stack the button, a roof and the lever under it
BTN_Z0, BTN_H, BTN_W = 3.4, 1.8, 9.0   # plunger: bottom (above the rim of the tray below), height, width
BTN_HEAD = (12.0, 8.0, 2.5)   # thumb head outside the wall: width, height, thickness; bottoms on the wall at full stroke
TUN_CLR = (0.25, 0.2, 0.5)    # button tunnel clearance: per side, below, above (the tunnel roof is a bridge)
ROOF_T = 0.6                  # tunnel roof = floor of the lever pocket
LEVER_R_IN, LEVER_R_OUT = 7.5, 22.5    # bell-crank arm lengths: 3:1. A 7.5 mm input arm keeps the button
                                       # tunnel clear of the pivot post, so the post stands on solid floor
LEVER_T, LEVER_W = 1.6, 6.0            # thickness; output arm width
PIVOT_D, PIVOT_CLR = 3.5, 0.3          # pivot post (part of the tray) and radial clearance in the lever
PIN_D_IN, PIN_D_OUT, PIN_CLR = 5.0, 4.0, 0.2  # lever pins (button side, sled side), clearance per side in the slots
PIN_PAD = 1.5                 # solid lever around each pin
PIN_FILLET = 0.6              # rounded pin roots spread the bending over more layers
# (the first coupon's 3 mm pins snapped at the root: they print standing up, so they bend across the layers)
EAR_WALL = 1.2                # wall around the slots in the button and the sled's ear
BTN_SPRING = 'D'

# Front press lever (v5): press a pad at the front-right DOWN and the bottom blank pushes out of the front, so the
# force goes into the shelf and nothing pushes the tray sideways (the side button had to be held). A crank in a
# housing at the front-right corner (its axle runs across the tray) swings its down-arm back; the arm's pin drives a
# fork on a pusher that runs back along the right side under the floor; the pusher's rear slot turns a straight 3:1
# lever whose long arm moves the same sled forward. The housing sits outside the pocket, so the front stops stay whole.
# Review fixes (2026-10-17): the fork is its own part, printed flat, dropped through a closed slot in a tunnel roof
# that spans to the housing wall (a cut-away roof had left an unsupported ledge); a stop block takes the overload at
# full press; the pad sits just in front of the housing (less tipping); the axle prints lying and press-fits.
FL_R_IN, FL_R_OUT = 6.5, 19.5          # straight lever arms (3:1): short arm toward the right wall
CRANK_T, CRANK_W = 3.5, 6.0            # crank plate thickness (x) and arm width
CRANK_L1, CRANK_L2 = 22.5, 9.65        # tab arm to the pad's far end, and down-arm to its pin
                                       # (9.65 x (cos 255 - cos 285) = 5 mm push)
CRANK_A0, CRANK_SWING = 15.0, 30.0     # tab arm 15 deg above horizontal at rest; it swings 30 deg down
CRANK_PIN_D, CRANK_PIN_Z = 4.0, 11.0   # crank pin; its height keeps the crank above the tunnel roof
CRANK_Y = 15.0                         # pivot behind the front face: the pad ends up just in front of the housing
PAD = (10.0, 5.5)                      # finger pad: width (x, toward the pin side), length along the tab arm
AXLE_D = 4.0                           # printed lying (with a flat); press fit in the housing's outer wall
AXLE_FREE = 4.4                        # crank and blind-hole bore
AXLE_BLIND = 1.2                       # blind hole into the right wall: leaves 1.2 mm to the blank pocket
FORK_T, FORK_TOP = 3.0, 14.4           # fork part: thickness (x), top (15.0 left 0.82 under the crank hub, and the
                                       # fork tips about 0.9 nose-up at full press; the pin top is at 13)
FORK_PRONG = (2.0, 4.5)                # front and rear (load-bearing) prong widths; the rear one was 2 mm (SF 0.6)
FORK_RELIEF = 0.4                      # slot 0.4 wider for the first 0.4 mm of the fork's bed face (elephant's foot
                                       # there met the crank pin's root fillet)
SOCKET_CLR = 0.2                       # fork stem in the pusher socket, per side (0.1 would not drop in); coupon B
CRANK_HUB_R = 4.5                      # the hub runs across the fork band too: a 6.8 mm bore keeps the crank from
                                       # tilting under the offset pad and puts the load next to the outer wall
AXLE_FLAT_DIR = 45.0                   # the axle's flat faces back and up (deg from +Y toward +Z), away from the load
PUSH_W, PUSH_GAP = 6.0, 0.3            # pusher bar width; side clearance of the crank and fork in their slot
PUSH_X = 4.0                           # pusher bar centre line, in from the pocket's right wall
TUN_TOP_FRONT, ROOF_FRONT = 0.8, 1.2   # under the bridged roof of the front section: clearance and roof thickness
HOUSE_D, HOUSE_WALL, HOUSE_H = 32.0, 2.4, 25.0   # 30 -> 32: room for the longer socket wall
TOWER_MAGNETS = DISPENSER == 'front'   # trays and lids stack in one tower of mixed sizes, fronts flush
MAGNET_D, MAGNET_T, MAGNET_CH = 6.2, 2.2, 0.4   # 6 x 2 mm magnets (6 x 3 left 0.2 mm over cavities on 3R and 4R)
MAGNET_DX, MAGNET_Y = 20.0, 55.0       # same pattern on every size: +-DX from the centre, Y back from the front face
LID_BOSS_R = 4.5                       # boss under the lid so the 2.2 mm pocket keeps a 0.8 mm floor
FRONT_COUPONS = DISPENSER == 'front'   # A/B test pieces printed with the prototype (print-engineer review 2026-10-17):
COUPON_ROOF = (1.0, 1.2)               # A: housing corner at these TUN_TOP_FRONT values (the tray itself is 0.8)
COUPON_SOCKET = (0.15, 0.25)           # B: pusher stubs at these socket clearances (the pusher itself is 0.20)
COUPON_PRESS = (4.0, 4.1, 4.2)         # C: horizontal press holes for the axle in a 2.4 mm fin
COUPON_BORE = (4.3, 4.5)               # C: vertical crank bores, 6.8 mm long (the crank itself is 4.4)

CHAMF = RIM + FIT                     # foot inset; 45 deg transition height
if DISPENSER == 'side':
    FLOOR = SIDE_FLOOR
elif DISPENSER in ('button', 'front'):
    FLOOR = BTN_FLOOR
elif DISPENSER:
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


def side_label(ctx, body, x_face, text, h, y_front, y_back, z, name):
    """Deboss text on the left outer wall (normal -X at x_face), reading left to right from outside."""
    face = next(f for f in body.faces if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                and f.evaluator.getNormalAtPoint(f.pointOnFace)[1].x < -0.99
                and abs(f.pointOnFace.x - x_face * MM) < 1e-6)
    sk = ctx.root.sketches.add(face)
    sk.name = name
    sk.isVisible = False
    # seen from -X with +Z up, left to right runs toward -Y: from the back to the front
    a = sk.modelToSketchSpace(P3.create(x_face * MM, y_back * MM, z * MM))
    b = sk.modelToSketchSpace(P3.create(x_face * MM, y_front * MM, z * MM))
    path = sk.sketchCurves.sketchLines.addByTwoPoints(a, b)
    path.isConstruction = True
    ti = sk.sketchTexts.createInput3("'%s'" % text, VI.createByReal(h * MM))
    ti.fontName = 'Arial Black'
    ti.setAsAlongPath(path, True, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, 0)
    txt = sk.sketchTexts.add(ti)
    ctx.extrude(txt, LABEL_D, adsk.fusion.FeatureOperations.CutFeatureOperation, name, body, negative=True)


def split_seam(ctx, body, cx, cy, W, H, name, dy=0.0):
    """Cut a dovetail seam across the part at y = cy + dy and name the two halves Front/Back."""
    ys = cy + dy
    pts = [(cx - W / 2 - 3, ys)]
    for k in (-1, 0, 1):
        xc = cx + k * W / 4
        pts += [(xc - 4, ys), (xc - 6, ys + 6), (xc + 6, ys + 6), (xc + 4, ys)]
    pts.append((cx + W / 2 + 3, ys))
    poly = offset_polyline(pts, KERF / 2) + list(reversed(offset_polyline(pts, -KERF / 2)))
    sk = ctx.sketch(0, name + ' Seam')
    polygon(sk, poly)
    ctx.cut_through(sk.profiles.item(0), name + ' Seam', body)
    parts = []
    for b in ctx.root.bRepBodies:
        bb = b.boundingBox
        if (bb.minPoint.x >= (cx - W / 2 - 1) * MM and bb.maxPoint.x <= (cx + W / 2 + 15) * MM   # + housing
                and bb.minPoint.y >= (cy - H / 2 - 1) * MM and bb.maxPoint.y <= (cy + H / 2 + 1) * MM):
            parts.append(b)
    if len(parts) != 2:
        raise RuntimeError('%s seam produced %d bodies' % (name, len(parts)))
    parts.sort(key=lambda b: b.boundingBox.minPoint.y)
    parts[0].name, parts[1].name = name + ' Front', name + ' Back'
    return parts


# ---------------------------------------------------------------- parts
def spring_len(sp):
    """Sled front to seat: header bend + segs flexible bars + bend into the pad (segs + 1 gaps)."""
    return (sp['segs'] + 1) * sp['pitch'] - sp['beam'] + SPRING_PAD


def side_geometry(w, h, cx, cy, spring=None):
    """Positions for the side dispenser, all in mm, at rest. The spring pocket and arm socket are sized
    for every variant in SPRINGS, so any test sled drops into the same tray."""
    sp = SPRINGS[spring or SPRING]
    W, H = dims(w, h)
    pw, ph = w + 2 * CLR, h + 2 * CLR
    g = {'W': W, 'H': H, 'pw': pw, 'ph': ph}
    g['xg'] = cx + pw / 2 - GROOVE_IN                 # groove / sled centre line
    g['y_pb'], g['y_pf'] = cy + ph / 2, cy - ph / 2   # pocket back / front faces
    g['y_sb'] = g['y_pb'] + 0.6 + BLADE_T             # sled back face: blade rests just behind the blanks
    g['y_gf'] = g['y_pf'] + 2.0                       # groove front end = spring seat
    g['sp'] = sp
    g['spring_len'] = spring_len(sp)
    g['y_sf'] = g['y_gf'] - SPRING_PRELOAD + g['spring_len']   # sled front face (spring starts here)
    g['L_s'] = g['y_sb'] - g['y_sf']
    r = sp['pitch'] / 2                               # U-bend centre-line radius
    g['sx_r'] = g['xg'] + SLED_W / 2 - r - sp['beam'] / 2      # bar ends: right bends stay inside the groove
    g['sx_l'] = g['sx_r'] - SPRING_SPAN
    g['y_sf_max'] = g['y_gf'] - SPRING_PRELOAD + max(spring_len(v) for v in SPRINGS.values())
    g['spring_x0'] = min(g['xg'] + SLED_W / 2 - v['pitch'] - v['beam'] - SPRING_SPAN - 0.4 for v in SPRINGS.values())
    g['y_k'] = g['y_sf_max'] + HEADER_T + HEAD_W / 2 + T_CLR + 1.5   # knob centre at rest, behind every variant's header
    g['win'] = (g['y_k'] - TAB_L / 2 - TRAVEL - 0.3, g['y_k'] + TAB_L / 2)   # wall window; its back end is the rest stop
    # arm channel under the floor: wide enough for the T-head to pass when the knob is fitted
    g['ch'] = (g['y_k'] - HEAD_W / 2 - T_CLR - TRAVEL - 0.3, g['y_k'] + HEAD_W / 2 + T_CLR + 0.3)
    g['z_gb'] = FLOOR - GROOVE_D                      # groove bottom
    return g


def box(ctx, name, x0, x1, y0, y1, z0, z1, op, body=None):
    sk = ctx.sketch(z0, name)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create(x0 * MM, y0 * MM, 0), P3.create(x1 * MM, y1 * MM, 0))
    return ctx.extrude(sk.profiles.item(0), z1 - z0, op, name, body)


def side_cuts(ctx, body, w, h, cx, cy):
    """Groove, blade bay, arm channel and wall window for the side dispenser."""
    g = side_geometry(w, h, cx, cy)
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    x0, x1 = g['xg'] - GROOVE_W / 2, g['xg'] + GROOVE_W / 2
    box(ctx, 'Sled Groove', x0, x1, g['y_gf'], g['y_pb'] + WALL + 1, g['z_gb'], FLOOR, cut, body)
    box(ctx, 'Spring Pocket', g['spring_x0'], x1, g['y_gf'], g['y_sf_max'] + HEADER_T + 0.5, g['z_gb'], FLOOR, cut, body)
    box(ctx, 'Blade Bay', x0, x1, g['y_pb'] - 0.01, g['y_pb'] + WALL + 1, FLOOR - 0.01, FLOOR + BLADE_UP + 0.3, cut, body)
    box(ctx, 'Arm Channel', x1 - 0.01, cx + g['pw'] / 2 + 0.01, g['ch'][0], g['ch'][1], g['z_gb'], FLOOR + 0.01, cut, body)
    box(ctx, 'Knob Window', cx + g['pw'] / 2 - 0.01, cx + g['W'] / 2 + 1, g['win'][0], g['win'][1],
        KNOB_Z0 - WIN_CLR, KNOB_Z0 + TAB_H + WIN_CLR, cut, body)


def yz_plane(ctx, x):
    """Construction plane parallel to YZ at model X = x (mm), whatever direction the YZ normal points."""
    for sign in (1, -1):
        pi = ctx.root.constructionPlanes.createInput()
        pi.setByOffset(ctx.root.yZConstructionPlane, VI.createByReal(sign * x * MM))
        pl = ctx.root.constructionPlanes.add(pi)
        if abs(pl.geometry.origin.x - x * MM) < 1e-6:
            pl.isLightBulbOn = False
            return pl
        pl.deleteMe()
    raise RuntimeError('could not place plane at x=%s' % x)


def yz_extrude(ctx, body, x, outline, dist, name):
    """Join a (y, z) outline drawn on the plane X = x to body, extruded dist mm toward +X."""
    sk = ctx.root.sketches.add(yz_plane(ctx, x))
    sk.name = name
    sk.isVisible = False
    sp = [sk.modelToSketchSpace(P3.create(x * MM, y * MM, z * MM)) for y, z in outline]
    L = sk.sketchCurves.sketchLines
    first = prev = None
    for i in range(len(sp)):
        prev = L.addByTwoPoints(prev.endSketchPoint if prev else sp[0],
                                first.startSketchPoint if i == len(sp) - 1 else sp[i + 1])
        first = first or prev
    ext = ctx.root.features.extrudeFeatures
    for direction in (adsk.fusion.ExtentDirections.PositiveExtentDirection,
                      adsk.fusion.ExtentDirections.NegativeExtentDirection):
        before = body.boundingBox.maxPoint.x
        ei = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.JoinFeatureOperation)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal(dist * MM)), direction)
        ei.participantBodies = [body]
        f = ext.add(ei)
        if body.boundingBox.maxPoint.x > before + 1e-6:
            f.name = name
            return f
        f.deleteMe()
    raise RuntimeError(name + ': could not extrude outward')


def rounded_rect_pts(yc, z0, wy, hz, r_top, r_bot, n=8):
    """Outline (y, z) of a rectangle with rounded corners; flat bottom edge sits on z0."""
    pts = []
    corners = [(yc + wy / 2 - r_bot, z0 + r_bot, r_bot, -90), (yc + wy / 2 - r_top, z0 + hz - r_top, r_top, 0),
               (yc - wy / 2 + r_top, z0 + hz - r_top, r_top, 90), (yc - wy / 2 + r_bot, z0 + r_bot, r_bot, 180)]
    for cy_, cz_, rr, a0 in corners:
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cy_ + rr * math.cos(a), cz_ + rr * math.sin(a)))
    return pts


def build_knob(ctx, lbl, g, cx):
    """Slider knob at rest: T-head and arm under the floor, tab in the wall window, grip plate and thumb rib
    outside. Every part starts at KNOB_Z0, so it prints flat on that face."""
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    x_pw, x_ow = cx + g['pw'] / 2, cx + g['W'] / 2
    yk, z0 = g['y_k'], KNOB_Z0
    x_head = g['xg'] + SLED_W / 2 - NECK_X - T_CLR     # outer face of the T-head
    knob = box(ctx, lbl + ' Knob Tab', x_pw - 0.01, x_ow + GRIP_GAP + 0.01, yk - TAB_L / 2, yk + TAB_L / 2,
               z0, z0 + TAB_H, new).bodies.item(0)
    knob.name = lbl + ' Dispenser Knob'
    box(ctx, lbl + ' Knob Arm', x_head - 0.01, x_pw + 0.01, yk - ARM_W / 2, yk + ARM_W / 2, z0, z0 + ARM_T, join, knob)
    box(ctx, lbl + ' Knob Head', x_head - HEAD_L, x_head, yk - HEAD_W / 2, yk + HEAD_W / 2, z0, z0 + ARM_T, join, knob)
    x_g = x_ow + GRIP_GAP
    yz_extrude(ctx, knob, x_g, rounded_rect_pts(yk, z0, GRIP_L, GRIP_H, 3.0, 1.0), GRIP_T, lbl + ' Knob Grip')
    rib_y = yk + GRIP_L / 2 - 1.0 - RIB_W / 2          # back edge, clear of the grip's rounded corner
    yz_extrude(ctx, knob, x_g + GRIP_T - 0.01, rounded_rect_pts(rib_y, z0, RIB_W, GRIP_H - 3.5, RIB_W / 2, 0.3),
               RIB_T + 0.01, lbl + ' Knob Rib')
    return knob


def build_mechanism(ctx, lbl, w, h, cx, cy, spring=None, with_knob=True):
    """Sled with blade and meander spring (and, with_knob, the knob with its arm) in rest positions."""
    g = side_geometry(w, h, cx, cy, spring)
    sp = g['sp']
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    xa, xb = g['xg'] - SLED_W / 2, g['xg'] + SLED_W / 2
    sled = box(ctx, lbl + ' Sled', xa, xb, g['y_sf'], g['y_sb'], g['z_gb'], g['z_gb'] + SLED_H, new).bodies.item(0)
    sled.name = lbl + (' Dispenser Sled' if with_knob else ' Test Sled %s' % spring)
    box(ctx, lbl + ' Blade', xa, xb, g['y_sb'] - BLADE_T, g['y_sb'], g['z_gb'], FLOOR + BLADE_UP, join, sled)
    # T-slot through the sled: the knob's head drops into it as the sled goes into the groove
    for part, x0_, x1_, hw in ((' Knob Neck', xb - NECK_X, xb + 0.1, ARM_W / 2 + T_CLR),
                               (' Knob Pocket', xb - NECK_X - HEAD_L - 2 * T_CLR, xb - NECK_X, HEAD_W / 2 + T_CLR)):
        box(ctx, lbl + part, x0_, x1_, g['y_k'] - hw, g['y_k'] + hw, g['z_gb'] - 0.1, g['z_gb'] + SLED_H + 0.1, cut, sled)
    # Meander spring with no thin necks: a rigid full-width header on the sled front, then round U-bends
    # and flexible bars, ending in a U-bend into a rigid full-width seat pad (drawn with preload).
    r, b, n = sp['pitch'] / 2, sp['beam'], sp['segs']
    box(ctx, lbl + ' Spring Header', g['sx_l'], xb, g['y_sf'], g['y_sf'] + HEADER_T, g['z_gb'], g['z_gb'] + SLED_H, join, sled)
    y0c = g['y_sf'] + b / 2                       # centre line of the header's front edge (virtual bar 0)
    pts = [(g['sx_l'] + 1.0, y0c), (g['sx_l'], y0c)]   # start inside the header
    for i in range(n + 1):                        # bend i joins bar i to bar i+1 (bar n+1 = the pad)
        yi = y0c - i * sp['pitch']
        x_at = g['sx_l'] if i % 2 == 0 else g['sx_r']
        side = -1 if x_at == g['sx_l'] else 1
        for k in range(1, 8):
            a = math.pi * k / 8
            pts.append((x_at + side * r * math.sin(a), yi - r + r * math.cos(a)))
        pts.append((x_at, yi - 2 * r))
        if i < n:
            pts.append((g['sx_r'] if x_at == g['sx_l'] else g['sx_l'], yi - 2 * r))
    pts.append((pts[-1][0] + (1.0 if pts[-1][0] == g['sx_l'] else -1.0), pts[-1][1]))   # end inside the pad
    poly = offset_polyline(pts, b / 2) + list(reversed(offset_polyline(pts, -b / 2)))
    sk = ctx.sketch(g['z_gb'], lbl + ' Spring')
    polygon(sk, poly)
    ctx.extrude(max(sk.profiles, key=lambda p_: p_.areaProperties().area), SPRING_H, join, lbl + ' Spring', sled)
    pad_top = y0c - (n + 1) * sp['pitch'] + b / 2
    box(ctx, lbl + ' Spring Pad', g['sx_l'] - r - b / 2, g['sx_r'] + r + b / 2, pad_top - SPRING_PAD, pad_top,
        g['z_gb'], g['z_gb'] + SPRING_H, join, sled)
    if not with_knob:
        return sled, None, g
    knob = build_knob(ctx, lbl, g, cx)
    return sled, knob, g


# ---------------------------------------------------------------- button dispenser (v4)
def stadium_pts(p0, p1, w, n=8):
    """Closed outline of a bar of width w from p0 to p1 with round ends."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    a0 = math.atan2(dy, dx)
    pts = []
    for (cx_, cy_), start in ((p1, a0 - math.pi / 2), (p0, a0 + math.pi / 2)):
        for k in range(n + 1):
            a = start + math.pi * k / n
            pts.append((cx_ + w / 2 * math.cos(a), cy_ + w / 2 * math.sin(a)))
    return pts


def sector_pts(c, r, a0, a1, n=16):
    """Closed pie slice around c from angle a0 to a1 (radians)."""
    return [c] + [(c[0] + r * math.cos(a0 + (a1 - a0) * k / n), c[1] + r * math.sin(a0 + (a1 - a0) * k / n))
                  for k in range(n + 1)]


def annulus_pts(c, r0, r1, a0, a1, n=16):
    """Closed curved slot between radii r0 and r1 from angle a0 to a1 (radians)."""
    outer = [(c[0] + r1 * math.cos(a0 + (a1 - a0) * k / n), c[1] + r1 * math.sin(a0 + (a1 - a0) * k / n))
             for k in range(n + 1)]
    inner = [(c[0] + r0 * math.cos(a1 - (a1 - a0) * k / n), c[1] + r0 * math.sin(a1 - (a1 - a0) * k / n))
             for k in range(n + 1)]
    return outer + inner


def button_geometry(w, h, cx, cy):
    """Positions for the button dispenser at rest, in mm. The lever swings +-th about its mid position."""
    sp = SPRINGS[BTN_SPRING]
    W, H = dims(w, h)
    pw, ph = w + 2 * CLR, h + 2 * CLR
    g = {'W': W, 'H': H, 'pw': pw, 'ph': ph, 'sp': sp}
    g['x_pw'], g['x_ow'] = cx + pw / 2, cx + W / 2
    g['y_pb'], g['y_pf'] = cy + ph / 2, cy - ph / 2
    th = math.asin(TRAVEL / (2 * LEVER_R_OUT))
    g['th'] = th
    g['btn_travel'] = 2 * LEVER_R_IN * math.sin(th)
    ri, ro = PIN_D_IN / 2 + PIN_CLR, PIN_D_OUT / 2 + PIN_CLR   # pin slot half-widths
    g['rp_in'], g['rp_out'] = ri, ro
    # input pin 1 mm inside the wall, and its pad on the lever 0.4 mm clear of it, so the lever lifts straight out
    px = g['x_pw'] - (LEVER_R_IN * math.sin(th) + max(ri + 1.0, PIN_D_IN / 2 + PIN_PAD + 0.4))
    py = cy
    g['pivot'] = (px, py)
    g['pin_in'] = (px + LEVER_R_IN * math.sin(th), py + LEVER_R_IN * math.cos(th))      # at rest
    g['pin_out'] = (px - LEVER_R_OUT * math.cos(th), py + LEVER_R_OUT * math.sin(th))   # at rest
    # sled: its ear carries a slot along x for the output pin (Scotch yoke), entirely clear of the sled body
    g['ear_slot'] = (px - LEVER_R_OUT - ro, px - LEVER_R_OUT * math.cos(th) + ro)
    g['xb'] = g['ear_slot'][0] - 0.3                           # sled right face
    g['xg'] = g['xb'] - SLED_W / 2
    g['ear_x1'] = g['ear_slot'][1] + EAR_WALL
    g['ear_y'] = (g['pin_out'][1] - ro - EAR_WALL, g['pin_out'][1] + ro + EAR_WALL)
    g['z_gb'] = BTN_Z0                                         # sled, ear, spring and button share this bottom
    g['y_sb'] = g['y_pb'] + 0.6 + BLADE_T
    g['y_gf'] = g['y_pf'] + 2.0
    g['spring_len'] = spring_len(sp)
    g['y_sf'] = g['y_gf'] - sp['preload'] + g['spring_len']
    r = sp['pitch'] / 2
    g['sx_r'] = g['xb'] - r - sp['beam'] / 2
    g['sx_l'] = g['sx_r'] - sp['span']
    g['spring_x0'] = g['sx_l'] - r - sp['beam'] / 2 - 0.4
    # button: a slot along y for the input pin; the head bottoms on the wall after btn_travel
    g['btn_slot_y'] = (py + LEVER_R_IN * math.cos(th) - ri, py + LEVER_R_IN + ri)
    g['y_b'] = sum(g['btn_slot_y']) / 2
    g['btn_x0'] = g['pin_in'][0] - ri - EAR_WALL               # inner end at rest
    g['lever_z0'] = BTN_Z0 + BTN_H + TUN_CLR[2] + ROOF_T + 0.2
    g['hub_r'] = PIVOT_D / 2 + PIVOT_CLR + 2.0
    if g['lever_z0'] + LEVER_T > FLOOR - 0.3:
        raise RuntimeError('lever does not fit under the floor')
    if g['y_b'] - BTN_W / 2 - TUN_CLR[0] < py + PIVOT_D / 2 + 0.3:
        raise RuntimeError('button tunnel runs under the pivot post')
    if (g['btn_slot_y'][1] - g['btn_slot_y'][0]) + 2 * 1.0 > BTN_W:
        raise RuntimeError('button too narrow for its slot')
    return g


def button_cuts(ctx, body, w, h, cx, cy):
    """Groove, spring pocket, blade bay, ear channel, button tunnel, pin slot and lever pocket; adds the pivot post."""
    g = button_geometry(w, h, cx, cy)
    sp, cut = g['sp'], adsk.fusion.FeatureOperations.CutFeatureOperation
    px, py = g['pivot']
    x0, x1 = g['xb'] - SLED_W - 0.3, g['xb'] + 0.3
    zb, th = g['z_gb'], g['th']
    box(ctx, 'Sled Groove', x0, x1, g['y_gf'], g['y_pb'] + WALL + 1, zb, FLOOR, cut, body)
    box(ctx, 'Spring Pocket', g['spring_x0'], x1, g['y_gf'], g['y_sf'] + HEADER_T + 0.5, zb, FLOOR, cut, body)
    box(ctx, 'Blade Bay', x0, x1, g['y_pb'] - 0.01, g['y_pb'] + WALL + 1, FLOOR - 0.01, FLOOR + BLADE_UP + 0.3, cut, body)
    # ear channel: its back end is the sled's rest stop; the front end is a backup stop past full stroke
    box(ctx, 'Ear Channel', x1 - 0.01, g['ear_x1'] + 0.3, g['ear_y'][0] - TRAVEL - 0.5, g['ear_y'][1], zb, FLOOR, cut, body)
    tz0, tz1 = BTN_Z0 - TUN_CLR[1], BTN_Z0 + BTN_H + TUN_CLR[2]
    box(ctx, 'Button Tunnel', g['btn_x0'] - g['btn_travel'] - 0.5, g['x_ow'] + 1,
        g['y_b'] - BTN_W / 2 - TUN_CLR[0], g['y_b'] + BTN_W / 2 + TUN_CLR[0], tz0, tz1, cut, body)
    # curved slot through the tunnel roof for the input pin
    rs = g['rp_in'] + 0.3                                   # + room for the pin's root fillet
    m = math.asin(rs / LEVER_R_IN) + math.radians(2)       # room for the whole pin at both ends of its swing
    sk = ctx.sketch(tz1 - 0.01, 'Input Pin Slot')
    polygon(sk, annulus_pts(g['pivot'], LEVER_R_IN - rs, LEVER_R_IN + rs, math.pi / 2 - th - m, math.pi / 2 + th + m))
    ctx.extrude(sk.profiles.item(0), ROOF_T + 0.22, cut, 'Input Pin Slot', body)
    # lever pocket, open to the floor: the hub plus each arm (0.5 mm oversize) at nine points across its swing
    zl = g['lever_z0'] - 0.2
    sk = ctx.sketch(zl, 'Lever Pocket')
    rh = g['hub_r'] + 0.5
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), rh * MM)
    for r_arm, mid, wd in ((LEVER_R_IN, math.pi / 2, PIN_D_IN + 2 * PIN_PAD),
                           (LEVER_R_OUT, math.pi, max(LEVER_W, PIN_D_OUT + 2 * PIN_PAD))):
        for k in range(9):
            a = mid - th + 2 * th * k / 8
            polygon(sk, stadium_pts(g['pivot'], (px + r_arm * math.cos(a), py + r_arm * math.sin(a)), wd + 1.0))
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    ctx.extrude(profs, FLOOR - zl + 0.01, cut, 'Lever Pocket', body)
    sk = ctx.sketch(zl, 'Pivot Post')
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), PIVOT_D / 2 * MM)
    ctx.extrude(sk.profiles.item(0), g['lever_z0'] + LEVER_T - zl, adsk.fusion.FeatureOperations.JoinFeatureOperation,
                'Pivot Post', body)
    return g


def meander(ctx, lbl, sled, sp, sx_l, sx_r, y_sf, z0):
    """Meander spring from the sled's header (front edge at y_sf) to a rigid seat pad, drawn at free length."""
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    r, b, n, hz = sp['pitch'] / 2, sp['beam'], sp['segs'], sp.get('h', SPRING_H)
    y0c = y_sf + b / 2
    pts = [(sx_l + 1.0, y0c), (sx_l, y0c)]
    for i in range(n + 1):
        yi = y0c - i * sp['pitch']
        x_at = sx_l if i % 2 == 0 else sx_r
        side = -1 if x_at == sx_l else 1
        for k in range(1, 8):
            a = math.pi * k / 8
            pts.append((x_at + side * r * math.sin(a), yi - r + r * math.cos(a)))
        pts.append((x_at, yi - 2 * r))
        if i < n:
            pts.append((sx_r if x_at == sx_l else sx_l, yi - 2 * r))
    pts.append((pts[-1][0] + (1.0 if pts[-1][0] == sx_l else -1.0), pts[-1][1]))
    poly = offset_polyline(pts, b / 2) + list(reversed(offset_polyline(pts, -b / 2)))
    sk = ctx.sketch(z0, lbl + ' Spring')
    polygon(sk, poly)
    ctx.extrude(max(sk.profiles, key=lambda p_: p_.areaProperties().area), hz, join, lbl + ' Spring', sled)
    pad_top = y0c - (n + 1) * sp['pitch'] + b / 2
    box(ctx, lbl + ' Spring Pad', sx_l - r - b / 2, sx_r + r + b / 2, pad_top - SPRING_PAD, pad_top, z0, z0 + hz, join, sled)


def build_button_mechanism(ctx, lbl, w, h, cx, cy):
    """Sled (blade, ear, spring), lever and button, all at rest."""
    g = button_geometry(w, h, cx, cy)
    sp, zb, th = g['sp'], g['z_gb'], g['th']
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    xb = g['xb']
    sled = box(ctx, lbl + ' Sled', xb - SLED_W, xb, g['y_sf'], g['y_sb'], zb, zb + SLED_H, new).bodies.item(0)
    sled.name = lbl + ' Dispenser Sled'
    box(ctx, lbl + ' Blade', xb - SLED_W, xb, g['y_sb'] - BLADE_T, g['y_sb'], zb, FLOOR + BLADE_UP, join, sled)
    box(ctx, lbl + ' Sled Ear', xb - 0.01, g['ear_x1'], g['ear_y'][0], g['ear_y'][1], zb, zb + SLED_H, join, sled)
    box(ctx, lbl + ' Ear Slot', g['ear_slot'][0], g['ear_slot'][1], g['pin_out'][1] - g['rp_out'], g['pin_out'][1] + g['rp_out'],
        zb - 0.1, zb + SLED_H + 0.1, cut, sled)
    box(ctx, lbl + ' Spring Header', g['sx_l'], xb, g['y_sf'], g['y_sf'] + HEADER_T, zb, zb + sp['h'], join, sled)
    meander(ctx, lbl, sled, sp, g['sx_l'], g['sx_r'], g['y_sf'], zb)

    # lever at rest (rotated -th from its mid position): hub, two arms, pins pointing down
    zl = g['lever_z0']
    sk = ctx.sketch(zl, lbl + ' Lever')
    px, py = g['pivot']
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), g['hub_r'] * MM)
    polygon(sk, stadium_pts(g['pivot'], g['pin_in'], PIN_D_IN + 2 * PIN_PAD))
    polygon(sk, stadium_pts(g['pivot'], g['pin_out'], LEVER_W))
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(g['pin_out'][0] * MM, g['pin_out'][1] * MM, 0),
                                                    (PIN_D_OUT / 2 + PIN_PAD) * MM)
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    lever = ctx.extrude(profs, LEVER_T, new, lbl + ' Lever').bodies.item(0)
    lever.name = lbl + ' Dispenser Lever'
    sk = ctx.sketch(zl, lbl + ' Lever Hole')
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), (PIVOT_D / 2 + PIVOT_CLR) * MM)
    ctx.extrude(sk.profiles.item(0), LEVER_T, cut, lbl + ' Lever Hole', lever)
    sk = ctx.sketch(zl, lbl + ' Lever Pins')
    for p_, d in ((g['pin_in'], PIN_D_IN), (g['pin_out'], PIN_D_OUT)):
        sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(p_[0] * MM, p_[1] * MM, 0), d / 2 * MM)
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    ctx.extrude(profs, zl - (BTN_Z0 + 0.3), join, lbl + ' Lever Pins', lever, negative=True)
    roots = adsk.core.ObjectCollection.create()
    for e in lever.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(c.center.z - zl * MM) < 1e-4 and any(abs(c.radius - d / 2 * MM) < 1e-4 for d in (PIN_D_IN, PIN_D_OUT)):
            roots.add(e)
    if roots.count != 2:
        raise RuntimeError('expected 2 pin root edges, found %d' % roots.count)
    fl = ctx.root.features.filletFeatures
    fi = fl.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(roots, VI.createByReal(PIN_FILLET * MM), True)
    fl.add(fi).name = lbl + ' Pin Root Fillets'

    # button: plunger with a slot along y for the input pin, and a rounded thumb head outside the wall
    x_head = g['x_ow'] + g['btn_travel']
    yb = g['y_b']
    btn = box(ctx, lbl + ' Button', g['btn_x0'], x_head + 0.01, yb - BTN_W / 2, yb + BTN_W / 2,
              BTN_Z0, BTN_Z0 + BTN_H, new).bodies.item(0)
    btn.name = lbl + ' Dispenser Button'
    box(ctx, lbl + ' Button Slot', g['pin_in'][0] - g['rp_in'], g['pin_in'][0] + g['rp_in'], g['btn_slot_y'][0], g['btn_slot_y'][1],
        BTN_Z0 - 0.1, BTN_Z0 + BTN_H + 0.1, cut, btn)
    hw, hh, ht = BTN_HEAD
    zc = BTN_Z0 + BTN_H / 2
    yz_extrude(ctx, btn, x_head, rounded_rect_pts(yb, zc - hh / 2, hw, hh, 2.5, 2.5), ht, lbl + ' Button Head')
    return sled, lever, btn, g


# ---------------------------------------------------------------- front press lever (v5)
def front_geometry(w, h, cx, cy):
    """Positions for the front press lever at rest (mm). The crank swings CRANK_SWING; the lever turns +-th."""
    sp = SPRINGS[BTN_SPRING]
    W, H = dims(w, h)
    pw, ph = w + 2 * CLR, h + 2 * CLR
    g = {'W': W, 'H': H, 'pw': pw, 'ph': ph, 'sp': sp}
    g['x_pw'], g['x_ow'] = cx + pw / 2, cx + W / 2
    g['y_o'] = cy - H / 2
    g['y_pb'], g['y_pf'] = cy + ph / 2, cy - ph / 2
    th = math.asin(TRAVEL / (2 * FL_R_OUT))
    g['th'] = th
    ri, ro = PIN_D_IN / 2 + PIN_CLR, PIN_D_OUT / 2 + PIN_CLR
    g['rp_in'], g['rp_out'] = ri, ro
    g['xr'] = g['x_pw'] - PUSH_X                       # pusher bar centre line, under the pocket floor
    px, py = g['xr'] - FL_R_IN, cy
    g['pivot'] = (px, py)
    g['push'] = 2 * FL_R_IN * math.sin(th)             # pusher travel (5 mm)
    g['pin_in'] = (px + FL_R_IN * math.cos(th), py - FL_R_IN * math.sin(th))      # at rest
    g['pin_out'] = (px - FL_R_OUT * math.cos(th), py + FL_R_OUT * math.sin(th))   # at rest
    g['ear_slot'] = (px - FL_R_OUT - ro, px - FL_R_OUT * math.cos(th) + ro)
    g['xb'] = g['ear_slot'][0] - 0.3
    g['ear_x1'] = g['ear_slot'][1] + EAR_WALL
    g['ear_y'] = (g['pin_out'][1] - ro - EAR_WALL, g['pin_out'][1] + ro + EAR_WALL)
    g['z_gb'] = BTN_Z0
    g['y_sb'] = g['y_pb'] + 0.6 + BLADE_T
    g['y_gf'] = g['y_pf'] + 2.0
    g['spring_len'] = spring_len(sp)
    g['y_sf'] = g['y_gf'] - sp['preload'] + g['spring_len']
    r = sp['pitch'] / 2
    g['sx_r'] = g['xb'] - r - sp['beam'] / 2
    g['sx_l'] = g['sx_r'] - sp['span']
    g['spring_x0'] = g['sx_l'] - r - sp['beam'] / 2 - 0.4
    g['lever_z0'] = BTN_Z0 + BTN_H + TUN_CLR[2] + ROOF_T + 0.2
    g['hub_r'] = PIVOT_D / 2 + PIVOT_CLR + 2.0
    # pusher: rear slot along x for the lever's short-arm pin (Scotch yoke), at rest
    g['slot_y'] = g['pin_in'][1]
    g['slot_x'] = (px + FL_R_IN * math.cos(th) - ri, px + FL_R_IN + ri)
    g['rear_y'] = g['slot_y'] + ri + EAR_WALL
    # tunnel front section under a roof that spans to the housing's outer wall
    g['tz1_front'] = BTN_Z0 + BTN_H + TUN_TOP_FRONT
    g['roof_top'] = g['tz1_front'] + ROOF_FRONT
    # crank housing at the front-right corner, outside the pocket: crank band, then fork band, then the outer wall
    xo = g['x_ow']
    g['crank_x'] = (xo + PUSH_GAP, xo + PUSH_GAP + CRANK_T)
    g['fork_x'] = (g['crank_x'][1] + PUSH_GAP, g['crank_x'][1] + PUSH_GAP + FORK_T)
    g['slot_x1'] = g['fork_x'][1] + PUSH_GAP
    g['house_x1'] = g['slot_x1'] + HOUSE_WALL
    a0 = math.radians(180 - CRANK_A0)                  # tab arm direction at rest: forward and up
    g['a0'] = a0
    g['swing'] = math.radians(CRANK_SWING)
    yp = g['y_o'] + CRANK_Y
    zp = CRANK_PIN_Z + CRANK_L2 * math.sin(math.radians(90 - CRANK_SWING / 2))
    g['crank_p'] = (yp, zp)
    g['cpin0'] = front_crank_pin(g, 0.0)
    g['tab0'] = (yp + CRANK_L1 * math.cos(a0), zp + CRANK_L1 * math.sin(a0))
    yc = g['cpin0'][0]
    g['fork_y'] = (yc - CRANK_PIN_D / 2 - 0.2 - FORK_PRONG[0], yc + CRANK_PIN_D / 2 + 0.2 + FORK_PRONG[1])
    g['stem_y'] = (g['fork_y'][0] + 1.5, g['fork_y'][1] - 2.0)   # socket walls 1.3 front, 4.3 behind (SF 3)
    g['jog_y'] = g['fork_y'][1] + 2.5                  # wide front section ends; the bar runs back from here
    pin_lo = min(front_crank_pin(g, g['swing'] * k / 8)[1] for k in range(9))
    g['fork_slot_z0'] = pin_lo - CRANK_PIN_D / 2 - 0.3
    g['crank_zlo'] = pin_lo - CRANK_W / 2
    g['crank_y_back'] = max(g['fork_y'][1] + g['push'], yp + 4.5) + 0.8
    # pad: the tab arm's last PAD[1] mm, widened toward the pin side; stays in front of the housing face
    u0 = CRANK_L1 - PAD[1]
    g['pad_u'] = (u0, CRANK_L1)
    g['pad_back_y'] = yp + u0 * math.cos(a0) + CRANK_W / 2 * math.sin(a0)
    if g['crank_zlo'] < g['roof_top'] + 0.4:
        raise RuntimeError('crank reaches down to the tunnel roof')
    if g['jog_y'] + g['push'] + 1.0 > g['y_o'] + HOUSE_D - HOUSE_WALL:
        raise RuntimeError('pusher front section leaves the housing')
    if g['pad_back_y'] > g['y_o'] - 0.4:
        raise RuntimeError('pad does not clear the housing front')
    if zp + g['hub_r'] + 0.5 > HOUSE_H + 2:
        raise RuntimeError('crank hub sits above the housing')
    if g['crank_p'][1] - CRANK_HUB_R < FORK_TOP + 1.2:     # 0.9 of fork tilt plus 0.3
        raise RuntimeError('crank hub reaches down to the fork')
    if g['spring_x0'] < g['x_pw'] - g['pw'] - 0.5:
        raise RuntimeError('spring does not fit the pocket width')
    return g


def sweep_pts(c, r, a0, a1, half, n=10):
    """Closed outline swept by a bar of half-width `half` from c out to radius r as it turns from a0 to a1 (rad):
    both side edges, the round ends at the two extreme positions, and the outer arc."""
    def at(cc, rr, t):
        return (cc[0] + rr * math.cos(t), cc[1] + rr * math.sin(t))
    p1, p0 = at(c, r, a1), at(c, r, a0)
    pts = [at(c, half, a1 + math.pi / 2)]
    pts += [at(p1, half, a1 + math.pi / 2 - (math.pi / 2) * k / 4) for k in range(5)]      # side edge, round end
    pts += [at(c, r + half, a1 - (a1 - a0) * k / n) for k in range(1, n)]                  # outer arc
    pts += [at(p0, half, a0 - (math.pi / 2) * k / 4) for k in range(5)]                    # round end, side edge
    pts.append(at(c, half, a0 - math.pi / 2))
    return pts


def front_crank_pin(g, phi):
    """Crank pin (y, z) when the crank has swung phi (rad) from rest; the down-arm is 90 deg past the tab arm."""
    yp, zp = g['crank_p']
    a = g['a0'] + math.pi / 2 + phi
    return (yp + CRANK_L2 * math.cos(a), zp + CRANK_L2 * math.sin(a))


def front_stop_pts(g):
    """(y, z) outline of the stop block behind the down-arm at full press: its front face is the arm's leading edge
    there, and it stands on the tunnel roof against the housing's back wall."""
    yp, zp = g['crank_p']
    a = g['a0'] + math.pi / 2 + g['swing']
    d, n = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))

    def edge(t):
        return (yp + t * d[0] + CRANK_W / 2 * n[0], zp + t * d[1] + CRANK_W / 2 * n[1])
    p0, p1 = edge(4.6), edge(CRANK_L2 + 1.9)
    yb = g['crank_y_back'] + 0.01
    return [p0, p1, (p1[0], g['roof_top'] - 0.01), (yb, g['roof_top'] - 0.01), (yb, p0[1])]


def x_hole(ctx, body, x0, x1, y, z, d, name):
    """Cut a round hole along X from x0 to x1 at (y, z)."""
    sk = ctx.root.sketches.add(yz_plane(ctx, x0))
    sk.name = name
    sk.isVisible = False
    sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(P3.create(x0 * MM, y * MM, z * MM)), d / 2 * MM)
    ext = ctx.root.features.extrudeFeatures
    for direction in (adsk.fusion.ExtentDirections.PositiveExtentDirection, adsk.fusion.ExtentDirections.NegativeExtentDirection):
        ei = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal((x1 - x0) * MM)), direction)
        ei.participantBodies = [body]
        try:
            f = ext.add(ei)
        except RuntimeError:
            continue
        probe = P3.create((x0 + (x1 - x0) / 2) * MM, y * MM, z * MM)
        if body.pointContainment(probe) != adsk.fusion.PointContainment.PointInsidePointContainment:
            f.name = name
            return f
        f.deleteMe()
    raise RuntimeError('hole failed: ' + name)


def front_cuts(ctx, body, w, h, cx, cy):
    """Housing (joined), groove, spring pocket, blade bay, ear channel, pusher tunnel and roof slot, pin slot, lever
    pocket, pivot post, crank slot, stop block and axle holes."""
    g = front_geometry(w, h, cx, cy)
    sp, cut = g['sp'], adsk.fusion.FeatureOperations.CutFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    px, py = g['pivot']
    th, zb, yo = g['th'], g['z_gb'], g['y_o']
    box(ctx, 'Lever Housing', g['x_pw'] + 0.5, g['house_x1'], yo, yo + HOUSE_D, 0, HOUSE_H, join, body)
    x0, x1 = g['xb'] - SLED_W - 0.3, g['xb'] + 0.3
    box(ctx, 'Sled Groove', x0, x1, g['y_gf'], g['y_pb'] + WALL + 1, zb, FLOOR, cut, body)
    box(ctx, 'Spring Pocket', g['spring_x0'], x1, g['y_gf'], g['y_sf'] + HEADER_T + 0.5, zb, FLOOR, cut, body)
    box(ctx, 'Blade Bay', x0, x1, g['y_pb'] - 0.01, g['y_pb'] + WALL + 1, FLOOR - 0.01, FLOOR + BLADE_UP + 0.3, cut, body)
    box(ctx, 'Ear Channel', x1 - 0.01, g['ear_x1'] + 0.3, g['ear_y'][0] - TRAVEL - 0.5, g['ear_y'][1], zb, FLOOR, cut, body)
    tz0, tz1 = BTN_Z0 - TUN_CLR[1], BTN_Z0 + BTN_H + TUN_CLR[2]
    c, xr, hw = TUN_CLR[0], g['xr'], PUSH_W / 2
    # pusher tunnel: wide front section (open at the front face to slide the pusher in), then the bar
    box(ctx, 'Pusher Tunnel Front', xr - hw - c, g['fork_x'][1] + c, yo - 1, g['jog_y'] + g['push'] + 0.5, tz0, g['tz1_front'],
        cut, body)
    box(ctx, 'Pusher Tunnel', xr - hw - c, xr + hw + c, g['jog_y'] - 1, g['rear_y'] + g['push'] + 0.5, tz0, tz1, cut, body)
    # closed slot through the roof for the fork (bounded by the housing's outer wall on +x)
    box(ctx, 'Fork Slot', g['fork_x'][0] - PUSH_GAP, g['slot_x1'], g['fork_y'][0] - 0.4, g['fork_y'][1] + g['push'] + 0.4,
        g['tz1_front'] - 0.01, g['roof_top'] + 0.01, cut, body)
    # curved slot through the tunnel roof for the short-arm pin
    rs = g['rp_in'] + 0.3
    m = math.asin(rs / FL_R_IN) + math.radians(2)
    sk = ctx.sketch(tz1 - 0.01, 'Input Pin Slot')
    polygon(sk, annulus_pts(g['pivot'], FL_R_IN - rs, FL_R_IN + rs, -th - m, th + m))
    ctx.extrude(sk.profiles.item(0), ROOF_T + 0.22, cut, 'Input Pin Slot', body)   # through the roof only
    # lever pocket, open to the floor: hub plus one outline per arm for its whole swing
    zl = g['lever_z0'] - 0.2
    sk = ctx.sketch(zl, 'Lever Pocket')
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), (g['hub_r'] + 0.9) * MM)
    for r_arm, mid, wd in ((FL_R_IN, 0.0, PIN_D_IN + 2 * PIN_PAD), (FL_R_OUT, math.pi, max(LEVER_W, PIN_D_OUT + 2 * PIN_PAD))):
        polygon(sk, sweep_pts(g['pivot'], r_arm, mid - th, mid + th, (wd + 1.0) / 2))
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    ctx.extrude(profs, FLOOR - zl + 0.01, cut, 'Lever Pocket', body)
    sk = ctx.sketch(zl, 'Pivot Post')
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), PIVOT_D / 2 * MM)
    ctx.extrude(sk.profiles.item(0), g['lever_z0'] + LEVER_T - zl, join, 'Pivot Post', body)
    # crank slot above the roof: open at the top (drop the crank in) and at the front (pad swing)
    yp, zp = g['crank_p']
    box(ctx, 'Crank Slot', g['x_ow'], g['slot_x1'], yo - 1, g['crank_y_back'], g['roof_top'], TRAY_H + 1, cut, body)
    # stop block for the down-arm at full press, in the crank band only (the fork runs beside it)
    sk = ctx.root.sketches.add(yz_plane(ctx, g['x_ow'] - 0.01))
    sk.name = 'Crank Stop'
    sk.isVisible = False
    sp_ = [sk.modelToSketchSpace(P3.create((g['x_ow'] - 0.01) * MM, y * MM, z * MM)) for y, z in front_stop_pts(g)]
    L = sk.sketchCurves.sketchLines
    first = prev = None
    for i in range(len(sp_)):
        prev = L.addByTwoPoints(prev.endSketchPoint if prev else sp_[0], first.startSketchPoint if i == len(sp_) - 1 else sp_[i + 1])
        first = first or prev
    ext = ctx.root.features.extrudeFeatures
    for direction in (adsk.fusion.ExtentDirections.PositiveExtentDirection, adsk.fusion.ExtentDirections.NegativeExtentDirection):
        ei = ext.createInput(sk.profiles.item(0), join)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal((g['crank_x'][1] - g['x_ow'] + 0.01) * MM)), direction)
        ei.participantBodies = [body]
        f = ext.add(ei)
        probe = P3.create((g['x_ow'] + 1.0) * MM, (front_stop_pts(g)[3][0] - 0.5) * MM, (g['roof_top'] + 0.5) * MM)
        if body.pointContainment(probe) == adsk.fusion.PointContainment.PointInsidePointContainment:
            f.name = 'Crank Stop'
            break
        f.deleteMe()
    # axle: free bore through the slot and blind into the right wall, press fit in the outer wall
    x_hole(ctx, body, g['x_ow'] - AXLE_BLIND, g['slot_x1'] + 0.01, yp, zp, AXLE_FREE, 'Axle Bore')
    x_hole(ctx, body, g['slot_x1'], g['house_x1'] + 0.5, yp, zp, AXLE_D, 'Axle Press Hole')
    return g


def yz_body(ctx, x, dist, loops, name):
    """New body from (y, z) loops (polygons, or ('circle', (y, z), r)) drawn on the plane X = x, extruded +X."""
    sk = ctx.root.sketches.add(yz_plane(ctx, x))
    sk.name = name
    sk.isVisible = False
    for lp in loops:
        if lp[0] == 'circle':
            sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(P3.create(x * MM, lp[1][0] * MM, lp[1][1] * MM)),
                                                            lp[2] * MM)
            continue
        sp = [sk.modelToSketchSpace(P3.create(x * MM, y * MM, z * MM)) for y, z in lp]
        L = sk.sketchCurves.sketchLines
        first = prev = None
        for i in range(len(sp)):
            prev = L.addByTwoPoints(prev.endSketchPoint if prev else sp[0], first.startSketchPoint if i == len(sp) - 1 else sp[i + 1])
            first = first or prev
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    ext = ctx.root.features.extrudeFeatures
    for direction in (adsk.fusion.ExtentDirections.PositiveExtentDirection, adsk.fusion.ExtentDirections.NegativeExtentDirection):
        ei = ext.createInput(profs, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByReal(dist * MM)), direction)
        f = ext.add(ei)
        b = f.bodies.item(0)
        if b.boundingBox.minPoint.x > (x - 0.01) * MM:
            f.name = name
            b.name = name
            return b
        f.deleteMe()
    raise RuntimeError('yz_body failed: ' + name)


def rect_along(c, a, u0, u1, half):
    """(y, z) rectangle along direction a (rad) from c, from u0 to u1 out, half-width `half`."""
    d, n = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    return [(c[0] + u * d[0] + v * n[0], c[1] + u * d[1] + v * n[1]) for u, v in ((u0, -half), (u1, -half), (u1, half), (u0, half))]


def combine(ctx, target, tools):
    ctx.root.features.combineFeatures.add(ctx.root.features.combineFeatures.createInput(
        target, adsk.core.ObjectCollection.createWithArray(tools)))


def build_front_mechanism(ctx, lbl, w, h, cx, cy):
    """Sled, straight lever, pusher, fork, crank and axle, all at rest."""
    g = front_geometry(w, h, cx, cy)
    sp, zb, th = g['sp'], g['z_gb'], g['th']
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    xb = g['xb']
    # sled: as the button version
    sled = box(ctx, lbl + ' Sled', xb - SLED_W, xb, g['y_sf'], g['y_sb'], zb, zb + SLED_H, new).bodies.item(0)
    sled.name = lbl + ' Front Sled'
    box(ctx, lbl + ' Blade', xb - SLED_W, xb, g['y_sb'] - BLADE_T, g['y_sb'], zb, FLOOR + BLADE_UP, join, sled)
    box(ctx, lbl + ' Sled Ear', xb - 0.01, g['ear_x1'], g['ear_y'][0], g['ear_y'][1], zb, zb + SLED_H, join, sled)
    box(ctx, lbl + ' Ear Slot', g['ear_slot'][0], g['ear_slot'][1], g['pin_out'][1] - g['rp_out'], g['pin_out'][1] + g['rp_out'],
        zb - 0.1, zb + SLED_H + 0.1, cut, sled)
    box(ctx, lbl + ' Spring Header', g['sx_l'], xb, g['y_sf'], g['y_sf'] + HEADER_T, zb, zb + sp['h'], join, sled)
    meander(ctx, lbl, sled, sp, g['sx_l'], g['sx_r'], g['y_sf'], zb)

    # straight 3:1 lever at rest, pins pointing down
    zl = g['lever_z0']
    px, py = g['pivot']
    sk = ctx.sketch(zl, lbl + ' Lever')
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), g['hub_r'] * MM)
    polygon(sk, stadium_pts(g['pivot'], g['pin_in'], PIN_D_IN + 2 * PIN_PAD))
    polygon(sk, stadium_pts(g['pivot'], g['pin_out'], LEVER_W))
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(g['pin_out'][0] * MM, g['pin_out'][1] * MM, 0),
                                                    (PIN_D_OUT / 2 + PIN_PAD) * MM)
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    lever = ctx.extrude(profs, LEVER_T, new, lbl + ' Lever').bodies.item(0)
    lever.name = lbl + ' Front Lever'
    sk = ctx.sketch(zl, lbl + ' Lever Hole')
    sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(px * MM, py * MM, 0), (PIVOT_D / 2 + PIVOT_CLR) * MM)
    ctx.extrude(sk.profiles.item(0), LEVER_T, cut, lbl + ' Lever Hole', lever)
    sk = ctx.sketch(zl, lbl + ' Lever Pins')
    for p_, d in ((g['pin_in'], PIN_D_IN), (g['pin_out'], PIN_D_OUT)):
        sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(p_[0] * MM, p_[1] * MM, 0), d / 2 * MM)
    profs = adsk.core.ObjectCollection.create()
    for p_ in sk.profiles:
        profs.add(p_)
    ctx.extrude(profs, zl - (BTN_Z0 + 0.3), join, lbl + ' Lever Pins', lever, negative=True)
    roots = adsk.core.ObjectCollection.create()
    for e in lever.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(c.center.z - zl * MM) < 1e-4 and any(abs(c.radius - d / 2 * MM) < 1e-4 for d in (PIN_D_IN, PIN_D_OUT)):
            roots.add(e)
    if roots.count != 2:
        raise RuntimeError('expected 2 pin root edges, found %d' % roots.count)
    fl = ctx.root.features.filletFeatures
    fi = fl.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(roots, VI.createByReal(PIN_FILLET * MM), True)
    fl.add(fi).name = lbl + ' Pin Root Fillets'

    # pusher at rest: wide front section with a socket for the fork's stem, bar back to the yoke slot
    xr, hw, z0, z1 = g['xr'], PUSH_W / 2, BTN_Z0, BTN_Z0 + BTN_H
    push = box(ctx, lbl + ' Pusher', xr - hw, g['fork_x'][1], g['fork_y'][0], g['jog_y'], z0, z1, new).bodies.item(0)
    push.name = lbl + ' Front Pusher'
    box(ctx, lbl + ' Pusher Bar', xr - hw, xr + hw, g['jog_y'] - 1, g['rear_y'], z0, z1, join, push)
    box(ctx, lbl + ' Fork Socket', g['fork_x'][0] - SOCKET_CLR, g['fork_x'][1] + 0.1, g['stem_y'][0] - SOCKET_CLR,
        g['stem_y'][1] + SOCKET_CLR, z0 - 0.1, z1 + 0.1, cut, push)
    box(ctx, lbl + ' Pusher Slot', g['slot_x'][0], g['slot_x'][1], g['slot_y'] - g['rp_in'], g['slot_y'] + g['rp_in'],
        z0 - 0.1, z1 + 0.1, cut, push)

    fork = build_fork(ctx, g, lbl + ' Front Fork')

    # crank at rest: hub, tab arm, down-arm with a pin toward the fork, and a finger pad
    yp, zp = g['crank_p']
    cp, a0 = g['cpin0'], g['a0']
    tab = g['tab0']
    loops = [('circle', (yp, zp), CRANK_HUB_R), stadium_pts((yp, zp), tab, CRANK_W), stadium_pts((yp, zp), cp, CRANK_W)]
    crank = yz_body(ctx, g['crank_x'][0], CRANK_T, loops, lbl + ' Front Crank')
    pad = yz_body(ctx, g['crank_x'][0], PAD[0], [rect_along((yp, zp), a0, g['pad_u'][0], g['pad_u'][1] + CRANK_W / 2, CRANK_W / 2)],
                  lbl + ' Crank Pad')
    pin = yz_body(ctx, g['crank_x'][1] - 0.01, g['fork_x'][1] - 0.1 - g['crank_x'][1] + 0.01, [('circle', cp, CRANK_PIN_D / 2)],
                  lbl + ' Crank Pin')
    hub = yz_body(ctx, g['crank_x'][1] - 0.01, g['fork_x'][1] - g['crank_x'][1] + 0.01, [('circle', (yp, zp), CRANK_HUB_R)],
                  lbl + ' Crank Hub')
    combine(ctx, crank, [pad, pin, hub])
    crank.name = lbl + ' Front Crank'
    x_hole(ctx, crank, g['crank_x'][0] - 0.5, g['fork_x'][1] + 0.5, yp, zp, AXLE_FREE, lbl + ' Crank Axle Hole')
    chamfer_circles(ctx, crank, 'x', g['crank_x'][0], AXLE_FREE / 2, 0.4, lbl + ' Crank bore chamfer')   # bed side
    roots = adsk.core.ObjectCollection.create()
    for e in crank.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(c.center.x - g['crank_x'][1] * MM) < 1e-4 and abs(c.radius - CRANK_PIN_D / 2 * MM) < 1e-4:
            roots.add(e)
    if roots.count:
        fi = ctx.root.features.filletFeatures.createInput()
        fi.edgeSetInputs.addConstantRadiusEdgeSet(roots, VI.createByReal(PIN_FILLET * MM), True)
        ctx.root.features.filletFeatures.add(fi).name = lbl + ' Crank Pin Root Fillet'

    # axle: shank from the blind hole through the outer wall, with a head; a 0.4 mm flat so it prints lying down
    shank = g['house_x1'] - (g['x_ow'] - AXLE_BLIND) + 0.2               # overlaps the head so they join
    axle = yz_body(ctx, g['x_ow'] - AXLE_BLIND + 0.1, shank, [('circle', (yp, zp), AXLE_D / 2)], lbl + ' Crank Axle')
    head = yz_body(ctx, g['house_x1'], 1.5, [('circle', (yp, zp), AXLE_D / 2 + 1.5)], lbl + ' Axle Head')
    combine(ctx, axle, [head])
    ua = math.radians(AXLE_FLAT_DIR)
    u, v, r0 = (math.cos(ua), math.sin(ua)), (-math.sin(ua), math.cos(ua)), AXLE_D / 2 - 0.4
    flat = [(yp + u[0] * a + v[0] * b, zp + u[1] * a + v[1] * b) for a, b in ((r0, -6), (r0 + 6, -6), (r0 + 6, 6), (r0, 6))]
    xa = g['x_ow'] - AXLE_BLIND - 1
    cutter = yz_body(ctx, xa, g['house_x1'] + 3 - xa, [flat], lbl + ' axle flat cutter')
    ctx.root.features.combineFeatures.add(_cut_input(ctx, axle, cutter))
    axle.name = lbl + ' Crank Axle'
    return sled, lever, push, fork, crank, axle, g


def deboss_top(ctx, body, text, x, y, z, h, name):
    """Small debossed text on a top face at height z, centred on (x, y), reading along +X."""
    sk = ctx.sketch(z, name)
    ti = sk.sketchTexts.createInput2(text, h * MM)
    ti.setAsMultiLine(P3.create((x - 15) * MM, (y - h) * MM, 0), P3.create((x + 15) * MM, (y + h) * MM, 0),
                      adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                      adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    ti.fontName = 'Arial Black'
    txt = sk.sketchTexts.add(ti)
    ctx.extrude(txt, 0.4, adsk.fusion.FeatureOperations.CutFeatureOperation, name, body, negative=True)


def build_front_coupons(ctx, lbl, w, h, cx, cy):
    """A/B pieces for the parts the review could not settle, printed with the prototype (placed clear of it):
    A housing corner at other roof clearances, B pusher stubs with other socket clearances (with forks),
    C press-fit holes for the axle and crank bores."""
    new = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    cut = adsk.fusion.FeatureOperations.CutFeatureOperation
    G = globals()
    W, H = dims(w, h)
    ox = cx + W / 2 + 40
    # A: whole trays built at the other roof values (the crank rises with the roof), cut down to the front-right corner
    keep_vals = (G['TUN_TOP_FRONT'], G['CRANK_PIN_Z'])
    try:
        for i, v in enumerate(COUPON_ROOF):
            G['TUN_TOP_FRONT'], G['CRANK_PIN_Z'] = v, keep_vals[1] + (v - keep_vals[0])
            x_c = ox + 100 * i
            t = build_tray(ctx, lbl, w, h, x_c, cy)
            g = front_geometry(w, h, x_c, cy)
            k = box(ctx, 'coupon A keep', g['x_ow'] - 14, g['house_x1'] + 1, g['y_o'] - 1, g['y_o'] + 36, -0.1, 12, new).bodies.item(0)
            ci = ctx.root.features.combineFeatures.createInput(t, adsk.core.ObjectCollection.createWithArray([k]))
            ci.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
            ctx.root.features.combineFeatures.add(ci)
            t.name = '%s Coupon A roof %.1f' % (lbl, v)
            side_label(ctx, t, g['x_ow'] - 14, 'A %.1f' % v, 5.0, g['y_o'] + 3, g['y_o'] + 33, 1.5, t.name + ' label')
    finally:
        G['TUN_TOP_FRONT'], G['CRANK_PIN_Z'] = keep_vals
    g = front_geometry(w, h, cx, cy)
    z0, z1 = BTN_Z0, BTN_Z0 + BTN_H
    # B: front sections of the pusher, with a fork for each
    for i, c in enumerate(COUPON_SOCKET):
        dx, dy = ox - cx + 100 * i, -70.0
        x0, x1 = g['xr'] - PUSH_W / 2 + dx, g['fork_x'][1] + dx
        n = '%s Coupon B socket %.2f' % (lbl, c)
        b = box(ctx, n, x0, x1, g['fork_y'][0] + dy, g['jog_y'] + 3 + dy, z0, z1, new).bodies.item(0)
        b.name = n
        box(ctx, n + ' socket', g['fork_x'][0] - c + dx, x1 + 0.1, g['stem_y'][0] - c + dy, g['stem_y'][1] + c + dy, z0 - 0.1, z1 + 0.1,
            cut, b)
        deboss_top(ctx, b, '%.2f' % c, (x0 + g['fork_x'][0] - c + dx) / 2, (g['fork_y'][0] + g['jog_y'] + 3) / 2 + dy, z1, 3.0, n + ' label')
        build_fork(ctx, g, '%s Coupon B fork %d' % (lbl, i + 1), dx, dy + 25)
    # C: a 2.4 mm fin (the housing's outer wall) with horizontal press holes, 2.7 mm of fin over each as in the housing
    yc0, x0 = cy - 120.0, ox
    zc = 1.6 + 6.0
    fin_top = zc + max(COUPON_PRESS) / 2 + 2.7
    n = lbl + ' Coupon C press holes'
    fin = box(ctx, n, x0, x0 + HOUSE_WALL, yc0, yc0 + 12 * len(COUPON_PRESS), 0, fin_top, new).bodies.item(0)
    box(ctx, n + ' foot', x0, x0 + HOUSE_WALL + 9.6, yc0, yc0 + 12 * len(COUPON_PRESS), 0, 1.6,
        adsk.fusion.FeatureOperations.JoinFeatureOperation, fin)
    fin.name = n
    for i, d in enumerate(COUPON_PRESS):
        y = yc0 + 6 + 12 * i
        x_hole(ctx, fin, x0 - 0.5, x0 + HOUSE_WALL + 0.5, y, zc, d, '%s %.1f' % (n, d))
        deboss_top(ctx, fin, '%.1f' % d, x0 + HOUSE_WALL + 4.8, y, 1.6, 3.0, '%s %.1f label' % (n, d))
    # C: crank bores, as long as the crank's hub
    hub_len = g['fork_x'][1] - g['crank_x'][0]
    n = lbl + ' Coupon C crank bores'
    x0 = ox + 30
    blk = box(ctx, n, x0, x0 + 14, yc0, yc0 + 13 * len(COUPON_BORE), 0, hub_len, new).bodies.item(0)
    blk.name = n
    for i, d in enumerate(COUPON_BORE):
        y = yc0 + 6.5 + 13 * i
        sk = ctx.sketch(0, '%s %.1f' % (n, d))
        sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create((x0 + 3.5) * MM, y * MM, 0), d / 2 * MM)
        ctx.extrude(sk.profiles.item(0), hub_len, cut, '%s %.1f' % (n, d), blk)
        chamfer_circles(ctx, blk, 'z', 0, d / 2, 0.4, '%s %.1f chamfer' % (n, d))   # bed side, as on the crank
        deboss_top(ctx, blk, '%.1f' % d, x0 + 9.6, y, hub_len, 3.0, '%s %.1f label' % (n, d))


def build_fork(ctx, g, name, dx=0.0, dy=0.0):
    """Fork part at rest (shifted dx, dy): plate on the pusher, stem down through its socket, round-bottom slot
    with a relief on the bed face (-X)."""
    z0, z1 = BTN_Z0, BTN_Z0 + BTN_H
    yc = g['cpin0'][0] + dy
    rsl = CRANK_PIN_D / 2 + 0.2
    zs = g['fork_slot_z0'] + rsl
    fy, sy = (g['fork_y'][0] + dy, g['fork_y'][1] + dy), (g['stem_y'][0] + dy, g['stem_y'][1] + dy)

    def slot(r):
        return [(yc - r, FORK_TOP + 0.5), (yc - r, zs)] + \
               [(yc + r * math.cos(math.radians(a)), zs + r * math.sin(math.radians(a))) for a in range(190, 360, 15)] + \
               [(yc + r, zs), (yc + r, FORK_TOP + 0.5)]
    outline = [(fy[0], z1), (sy[0], z1), (sy[0], z0), (sy[1], z0), (sy[1], z1), (fy[1], z1), (fy[1], FORK_TOP), (fy[0], FORK_TOP)]
    x0 = g['fork_x'][0] + dx
    fork = yz_body(ctx, x0, FORK_T, [outline], name)
    for cx0, depth, r in ((x0 - 0.5, FORK_T + 1.0, rsl), (x0 - 0.5, 0.5 + FORK_RELIEF, rsl + FORK_RELIEF)):
        cutter = yz_body(ctx, cx0, depth, [slot(r)], name + ' slot cutter')
        ctx.root.features.combineFeatures.add(_cut_input(ctx, fork, cutter))
    fork.name = name
    return fork


def _cut_input(ctx, target, tool):
    ci = ctx.root.features.combineFeatures.createInput(target, adsk.core.ObjectCollection.createWithArray([tool]))
    ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    return ci


def xz_prism(ctx, name, pts, y0, y1, op, body):
    """Prism along Y from y0 to y1 whose cross-section is the closed (x, z) outline pts."""
    ym = (y0 + y1) / 2
    for sign in (1, -1):
        pi = ctx.root.constructionPlanes.createInput()
        pi.setByOffset(ctx.root.xZConstructionPlane, VI.createByReal(sign * ym * MM))
        pl = ctx.root.constructionPlanes.add(pi)
        if abs(pl.geometry.origin.y - ym * MM) < 1e-6:
            break
        pl.deleteMe()
    pl.isLightBulbOn = False
    sk = ctx.root.sketches.add(pl)
    sk.name = name
    sk.isVisible = False
    sp = [sk.modelToSketchSpace(P3.create(x * MM, ym * MM, z * MM)) for x, z in pts]
    L = sk.sketchCurves.sketchLines
    first = prev = None
    for i in range(len(sp)):
        prev = L.addByTwoPoints(prev.endSketchPoint if prev else sp[0],
                                first.startSketchPoint if i == len(sp) - 1 else sp[i + 1])
        first = first or prev
    ext = ctx.root.features.extrudeFeatures
    ei = ext.createInput(sk.profiles.item(0), op)
    ei.setSymmetricExtent(VI.createByReal((y1 - y0) * MM), True)
    ei.participantBodies = [body]
    f = ext.add(ei)
    f.name = name
    return f


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
    pw = w + 2 * CLR
    slot_h = FRONT_GAP if DISPENSER in ('button', 'front') else SLOT_H
    if DISPENSER in ('button', 'front'):
        # open front: the opening narrows at 45 degrees from the two flat stops, then runs straight up
        xs, xt, zb = pw / 2 - FRONT_STOP, pw / 2 - FRONT_STUB, FLOOR + slot_h
        zt = zb + (FRONT_STUB - FRONT_STOP)
        xz_prism(ctx, n + ' Open Front', [(cx - xs, zb), (cx + xs, zb), (cx + xt, zt), (cx + xt, TRAY_H + 1),
                                          (cx - xt, TRAY_H + 1), (cx - xt, zt)], yo - 1, yi + 0.5,
                 adsk.fusion.FeatureOperations.CutFeatureOperation, body)
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
    if DISPENSER not in ('button', 'front'):
        ctx.cut_through(sk.profiles.item(0), n + ' Notch', body)

    if DISPENSER:
        # one-blank slot across the front wall, sitting on the raised floor
        sk = ctx.sketch(FLOOR, n + ' Dispenser Slot')
        # reach R_POCKET + 0.5 into the pocket: the pocket's rounded front corners would otherwise
        # catch the blank's square corners as it slides out
        sk.sketchCurves.sketchLines.addTwoPointRectangle(P3.create((cx - pw / 2) * MM, (yo - 1) * MM, 0),
                                                         P3.create((cx + pw / 2) * MM, (yi + R_POCKET + 0.5) * MM, 0))
        ctx.extrude(sk.profiles.item(0), slot_h, adsk.fusion.FeatureOperations.CutFeatureOperation,
                    n + ' Dispenser Slot', body)
    if DISPENSER == 'side':
        side_cuts(ctx, body, w, h, cx, cy)
    elif DISPENSER == 'button':
        button_cuts(ctx, body, w, h, cx, cy)
    elif DISPENSER == 'front':
        front_cuts(ctx, body, w, h, cx, cy)
    elif DISPENSER == 'rear':
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
    if DISPENSER in ('button', 'front'):   # label on the left stop, above its 45 degree part; the open front shows the stock
        x_l1 = cx - (pw / 2 - FRONT_STUB)
        lh = min(9.0, math.floor(0.8 * (x_l1 - x_l0) / (0.99 * len(lbl))))
        z_lo = FLOOR + slot_h + (FRONT_STUB - FRONT_STOP) + 0.8
    sk = ctx.root.sketches.add(left)
    sk.name = n + ' Label'
    txt = face_text(ctx, sk, lbl, lh, x_l0, x_l1, (z_lo + z_hi) / 2 - lh / 2, yo,
                    adsk.core.HorizontalAlignments.CenterHorizontalAlignment)
    ctx.extrude(txt, LABEL_D, adsk.fusion.FeatureOperations.CutFeatureOperation, n + ' Label', body, negative=True)
    if TOWER_MAGNETS:
        for sx in (-1, 1):
            sk = ctx.sketch(0, n + ' Magnet')
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                P3.create((cx + sx * MAGNET_DX) * MM, (cy - H / 2 + MAGNET_Y) * MM, 0), MAGNET_D / 2 * MM)
            ctx.extrude(sk.profiles.item(0), MAGNET_T, adsk.fusion.FeatureOperations.CutFeatureOperation,
                        n + ' Magnet', body)
        magnet_chamfers(ctx, body, n)
    if DISPENSER in ('button', 'front'):
        # the size again, big and bold, on the left wall above the floor (the right wall carries the button)
        z_mid = (FLOOR + TRAY_H - REB) / 2
        side_label(ctx, body, cx - W / 2, lbl, SIDE_LABEL_H, cy - H / 2 + R_OUT, cy + H / 2 - R_OUT,
                   z_mid - SIDE_LABEL_H / 2, n + ' Side Label')
        return body

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


def chamfer_circles(ctx, body, axis, at, r, size, name):
    """Equal chamfer on the circular edges of radius r whose centres lie on the plane axis = at ('x' or 'z')."""
    edges = adsk.core.ObjectCollection.create()
    for e in body.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(getattr(c.center, axis) - at * MM) < 1e-5 and abs(c.radius - r * MM) < 1e-4:
            edges.add(e)
    if not edges.count:
        raise RuntimeError('no edges to chamfer: ' + name)
    ci = ctx.root.features.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, VI.createByReal(size * MM), False)
    ctx.root.features.chamferFeatures.add(ci).name = name


def magnet_chamfers(ctx, body, n):
    """0.4 mm chamfer on every magnet pocket mouth (the bed face): elephant's foot would narrow it."""
    edges = adsk.core.ObjectCollection.create()
    for e in body.edges:
        c = adsk.core.Circle3D.cast(e.geometry)
        if c and abs(c.center.z) < 1e-6 and abs(c.radius - MAGNET_D / 2 * MM) < 1e-4:
            edges.add(e)
    if edges.count:
        ci = ctx.root.features.chamferFeatures.createInput2()
        ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, VI.createByReal(MAGNET_CH * MM), False)
        ctx.root.features.chamferFeatures.add(ci).name = n + ' Magnet chamfers'


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
    if TOWER_MAGNETS:
        spots = [(cx + sx * MAGNET_DX, cy + sy * (H / 2 - MAGNET_Y)) for sx in (-1, 1) for sy in (-1, 1)]
        for x, y in spots:
            sk = ctx.sketch(LID_T, n + ' Magnet boss')
            sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(x * MM, y * MM, 0), LID_BOSS_R * MM)
            ctx.extrude(sk.profiles.item(0), MAGNET_T + 0.8 - LID_T, adsk.fusion.FeatureOperations.JoinFeatureOperation,
                        n + ' Magnet boss', body)
            sk = ctx.sketch(0, n + ' Magnet')
            sk.sketchCurves.sketchCircles.addByCenterRadius(P3.create(x * MM, y * MM, 0), MAGNET_D / 2 * MM)
            ctx.extrude(sk.profiles.item(0), MAGNET_T, adsk.fusion.FeatureOperations.CutFeatureOperation,
                        n + ' Magnet', body)
        magnet_chamfers(ctx, body, n)
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
        if ONLY and lbl not in ONLY:
            continue
        W, H = dims(w, h)
        tray = build_tray(ctx, lbl, w, h, xs[lbl], 0)
        lid = build_lid(ctx, lbl, w, h, xs[lbl], LID_ROW_Y)
        if max(W, H) > BED:     # before the loose parts are built: the seam collects every body in the outline
            split_seam(ctx, tray, xs[lbl], 0, W, H, lbl + ' Tray', SEAM_DY_BUTTON if DISPENSER in ('button', 'front') else 0.0)
            split_seam(ctx, lid, xs[lbl], LID_ROW_Y, W, H, lbl + ' Lid')
        if DISPENSER == 'button':
            build_button_mechanism(ctx, lbl, w, h, xs[lbl], 0)
        elif DISPENSER == 'front':
            build_front_mechanism(ctx, lbl, w, h, xs[lbl], 0)
            if FRONT_COUPONS:
                build_front_coupons(ctx, lbl, w, h, xs[lbl], 0)
        elif DISPENSER == 'side':
            build_mechanism(ctx, lbl, w, h, xs[lbl], 0)
            for i, key in enumerate(TEST_SPRINGS):      # shifted clear of the tray, for printing
                build_mechanism(ctx, lbl, w, h, xs[lbl] + W + 20 + 30 * i, 0, key, with_knob=False)
    print('tray height %.1f mm, pocket %.1f mm deep' % (TRAY_H, POCKET_D))
    report(ctx)
