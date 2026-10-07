"""Model 1 — parametric CFD geometry of the current Gungnear configuration (spec: R07a-3D-Modell-CFD.md).

Axes: x from the nose rearwards, y to the right wing, z up. Units: mm.
Run:  python model1.py   ->  model1_cfd.step, model1_cfd.stl, report printed to stdout
      python model1.py --no-gear             ->  model1b_nogear  (v1 light)
      python model1.py --config light-plus   ->  model1c_lightplus  (v1 light+, R07c)
"""
import math
import os

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepGProp import BRepGProp
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt

HERE = os.path.dirname(os.path.abspath(__file__))

# --- fuselage (locked/derived) ---
R_BODY = 37.5
X_NOSE_END = 120.0
X_CONE_START = 759.0
X_BASE = 900.0
R_BASE = 15.0
OGIVE_RHO = 210.75
NOSE_BLUNT_R = 2.0

# --- wing (0.25 m² locked; AR, incidence, dihedral are assumptions) ---
# light stays on MH 32. light+ uses Clark Y (decision 2026-09-29; NACA 4412 later).
WING_AREA = 0.25e6
AIRFOIL = "mh32.dat"
ASPECT_RATIO = 6.0
SPAN = math.sqrt(ASPECT_RATIO * WING_AREA)
CHORD = WING_AREA / SPAN
X_WING_C4 = 355.0
X_WING_LE = X_WING_C4 - 0.25 * CHORD
WING_INCIDENCE = 2.0
DIHEDRAL = 2.0
TE_THICKNESS = 0.4

# --- tail (assumptions; TE at 895 so nothing sticks out behind the Ø30 base) ---
X_TAIL_TE = 895.0
HT_SPAN, HT_CHORD = 470.0, 118.0
VT_ROOT_Z, VT_ROOT_LE = 30.0, 745.0
VT_TIP_Z, VT_TIP_LE = 220.0, 795.0

# --- named configurations (overrides of the constants above; spec: R07c-Light-Plus.md) ---
# light+ = +456 mm payload bay at the joiner gap + 15 mm spacer, wing 0.30 m², tail resized for V_H 0.491 / V_V 0.0345
CONFIGS = {
    "light": {},
    "light-plus": dict(AIRFOIL="clarky.dat", X_CONE_START=1230.26, X_BASE=1371.26, WING_AREA=0.30e6, X_WING_C4=583.73,
                       X_TAIL_TE=1366.26, HT_SPAN=432.45, HT_CHORD=108.65,
                       VT_ROOT_LE=1228.68, VT_TIP_Z=204.26, VT_TIP_LE=1274.54),
}


def apply_config(name):
    g = globals()
    g.update(CONFIGS[name])
    g["SPAN"] = math.sqrt(ASPECT_RATIO * g["WING_AREA"])
    g["CHORD"] = g["WING_AREA"] / g["SPAN"]
    g["X_WING_LE"] = g["X_WING_C4"] - 0.25 * g["CHORD"]

# --- landing gear (assumptions around locked Ø60 wheels and 4×20 strap) ---
X_AXLE, Y_AXLE, Z_AXLE = 300.0, 140.0, -145.0
WHEEL_R, WHEEL_W = 30.0, 22.0
STRUT_ROOT = (300.0, 20.0, -30.0)
STRUT_CHORD, STRUT_THICK = 20.0, 4.0
# pant: superellipse section, full between xi 0.25..0.55 so both wheel sides stay covered; only ~8 mm of tyre shows
PANT_LEN = 110.0
PANT_X0 = X_AXLE - 0.4 * PANT_LEN
PANT_HALF_W, PANT_HALF_H, PANT_ZC = 17.0, 29.5, -137.5
PANT_EXPONENT = 4.0


def naca_half_thickness(x, t, closed_te=False):
    a4 = -0.1036 if closed_te else -0.1015
    return 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 + a4 * x**4)


def naca_symmetric(t, n=60, closed_te=True):
    xs = [0.5 * (1 - math.cos(math.pi * i / n)) for i in range(n + 1)]
    upper = [(x, naca_half_thickness(x, t, closed_te)) for x in reversed(xs)]
    lower = [(x, -naca_half_thickness(x, t, closed_te)) for x in xs[1:]]
    return upper + lower


def load_dat(path):
    pts = []
    with open(path, encoding="utf-8") as f:
        for line in f.readlines()[1:]:
            parts = line.split()
            if len(parts) == 2:
                pts.append((float(parts[0]), float(parts[1])))
    return pts


def thicken_te(pts, te_chord):
    """Open the trailing edge to a finite thickness (in chord units) — sharp TEs mesh badly."""
    i_le = min(range(len(pts)), key=lambda i: pts[i][0])
    out = []
    for i, (x, y) in enumerate(pts):
        sign = 1.0 if i <= i_le else -1.0
        out.append((x, y + sign * 0.5 * te_chord * x))
    return out


def section_wire(pts2d, to3d):
    """Closed wire: one spline through the airfoil points plus a straight TE segment."""
    v = [cq.Vector(*to3d(x, y)) for x, y in pts2d]
    spline = cq.Edge.makeSpline(v)
    te = cq.Edge.makeLine(v[-1], v[0])
    return cq.Wire.assembleEdges([spline, te])


def rot_y(x, z, xc, zc, deg):
    a = math.radians(deg)
    dx, dz = x - xc, z - zc
    return xc + dx * math.cos(a) + dz * math.sin(a), zc - dx * math.sin(a) + dz * math.cos(a)


def fuselage():
    xt_c = X_NOSE_END - math.sqrt((OGIVE_RHO - NOSE_BLUNT_R) ** 2 - (OGIVE_RHO - R_BODY) ** 2)
    yt = NOSE_BLUNT_R * (OGIVE_RHO - R_BODY) / (OGIVE_RHO - NOSE_BLUNT_R)
    xt = xt_c - math.sqrt(NOSE_BLUNT_R**2 - yt**2)
    x_apex = xt_c - NOSE_BLUNT_R
    ang_t = math.atan2(yt, xt - xt_c)
    ang_m = 0.5 * (math.pi + ang_t)
    arc_mid = (xt_c + NOSE_BLUNT_R * math.cos(ang_m), NOSE_BLUNT_R * math.sin(ang_m))

    def ogive(x):
        return math.sqrt(OGIVE_RHO**2 - (X_NOSE_END - x) ** 2) - (OGIVE_RHO - R_BODY)

    ogive_pts = [(xt + (X_NOSE_END - xt) * (1 - math.cos(0.5 * math.pi * i / 40)), 0) for i in range(1, 41)]
    ogive_pts = [(x, ogive(x)) for x, _ in ogive_pts]
    ogive_pts[-1] = (X_NOSE_END, R_BODY)
    slope_t = (X_NOSE_END - xt) / math.sqrt(OGIVE_RHO**2 - (X_NOSE_END - xt) ** 2)

    cone_len = X_BASE - X_CONE_START
    half_drop = 0.5 * (R_BODY - R_BASE)
    cone_pts = []
    for i in range(1, 31):
        x = X_CONE_START + cone_len * i / 30
        cone_pts.append((x, R_BASE + half_drop * (1 + math.cos(math.pi * (x - X_CONE_START) / cone_len))))
    cone_pts[-1] = (X_BASE, R_BASE)

    # profile drawn below the axis in the XZ plane so the revolve seam lies on the belly at y = 0,
    # i.e. on the symmetry plane where the half-model cut removes it
    flip = lambda pts: [(x, -r) for x, r in pts]
    profile = (
        cq.Workplane("XZ")
        .moveTo(x_apex, 0)
        .threePointArc((arc_mid[0], -arc_mid[1]), (xt, -yt))
        .spline(flip(ogive_pts), tangents=[(1, -slope_t), (1, 0)], includeCurrent=True)
        .lineTo(X_CONE_START, -R_BODY)
        .spline(flip(cone_pts), tangents=[(1, 0), (1, 0)], includeCurrent=True)
        .lineTo(X_BASE, 0)
        .close()
    )
    return profile.revolve(360, (0, 0, 0), (1, 0, 0)).val(), x_apex


def wing_panel_right():
    raw = load_dat(os.path.join(HERE, AIRFOIL))
    pts = thicken_te(raw, TE_THICKNESS / CHORD)
    y_root, y_tip = -12.0, SPAN / 2

    def at(y):
        def f(u, v):
            x, z = rot_y(X_WING_LE + u * CHORD, v * CHORD, X_WING_C4, 0.0, WING_INCIDENCE)
            return (x, y, z)
        return f

    w0, w1 = section_wire(pts, at(y_root)), section_wire(pts, at(y_tip))
    panel = cq.Solid.makeLoft([w0, w1], True)
    return panel.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), DIHEDRAL)


def horizontal_tail():
    pts = thicken_te(naca_symmetric(0.09), TE_THICKNESS / HT_CHORD)
    x_le = X_TAIL_TE - HT_CHORD

    def at(y):
        return lambda u, v: (x_le + u * HT_CHORD, y, v * HT_CHORD)

    return cq.Solid.makeLoft([section_wire(pts, at(-HT_SPAN / 2)), section_wire(pts, at(HT_SPAN / 2))], True)


def vertical_tail():
    le_slope = (VT_TIP_LE - VT_ROOT_LE) / (VT_TIP_Z - VT_ROOT_Z)
    le0 = VT_ROOT_LE - VT_ROOT_Z * le_slope

    def section(z, le):
        c = X_TAIL_TE - le
        pts = thicken_te(naca_symmetric(0.09), TE_THICKNESS / c)
        return section_wire(pts, lambda u, v: (le + u * c, v * c, z))

    return cq.Solid.makeLoft([section(0.0, le0), section(VT_TIP_Z, VT_TIP_LE)], True)


def strut_right():
    ax, ay, az = STRUT_ROOT
    d = cq.Vector(X_AXLE - ax, Y_AXLE - ay, Z_AXLE - az)
    length = d.Length
    d = d.normalized()
    ex = cq.Vector(1, 0, 0)
    n = ex.cross(d).normalized()
    t = STRUT_THICK / STRUT_CHORD
    pts = thicken_te(naca_symmetric(t, n=30), TE_THICKNESS / STRUT_CHORD)

    def at(origin):
        return lambda u, v: tuple((origin + ex * ((u - 0.5) * STRUT_CHORD) + n * (v * STRUT_CHORD)).toTuple())

    p0 = cq.Vector(ax, ay, az)
    p1 = p0 + d * (length + 8.0)
    return cq.Solid.makeLoft([section_wire(pts, at(p0)), section_wire(pts, at(p1))], True)


def pant_fullness(xi):
    """Elliptic nose, parallel middle over the wheel, smooth closing tail."""
    if xi < 0.25:
        return math.sqrt(max(0.0, 1 - ((0.25 - xi) / 0.25) ** 2))
    if xi <= 0.55:
        return 1.0
    s = (xi - 0.55) / 0.45
    return 1 - 3 * s * s + 2 * s**3


def superellipse_wire(xc, a, b, m=48):
    e = 2.0 / PANT_EXPONENT
    pts = []
    for k in range(m):
        t = 2 * math.pi * k / m
        c, s = math.cos(t), math.sin(t)
        pts.append(cq.Vector(xc, Y_AXLE + a * math.copysign(abs(c) ** e, c), PANT_ZC + b * math.copysign(abs(s) ** e, s)))
    return cq.Wire.assembleEdges([cq.Edge.makeSpline(pts, periodic=True)])


def wheel_pant_right():
    loft = BRepOffsetAPI_ThruSections(True, False, 1e-6)
    loft.AddVertex(BRepBuilderAPI_MakeVertex(gp_Pnt(PANT_X0, Y_AXLE, PANT_ZC)).Vertex())
    for xi in (0.015, 0.04, 0.08, 0.13, 0.19, 0.25, 0.4, 0.55, 0.63, 0.71, 0.79, 0.87, 0.94):
        f = pant_fullness(xi)
        loft.AddWire(superellipse_wire(PANT_X0 + xi * PANT_LEN, PANT_HALF_W * f, PANT_HALF_H * f).wrapped)
    loft.AddVertex(BRepBuilderAPI_MakeVertex(gp_Pnt(PANT_X0 + PANT_LEN, Y_AXLE, PANT_ZC)).Vertex())
    loft.Build()
    return cq.Shape.cast(loft.Shape())


def wheel_right():
    return cq.Solid.makeCylinder(
        WHEEL_R, WHEEL_W, cq.Vector(X_AXLE, Y_AXLE - WHEEL_W / 2, Z_AXLE), cq.Vector(0, 1, 0)
    )


def mirror_y(shape):
    return shape.mirror("XZ", cq.Vector(0, 0, 0))


def build(with_gear=True):
    body, x_apex = fuselage()
    wing_r = wing_panel_right()
    parts = [wing_r, mirror_y(wing_r), horizontal_tail(), vertical_tail()]
    if with_gear:
        gear_r = strut_right().fuse(wheel_pant_right()).fuse(wheel_right()).clean()
        parts += [gear_r, mirror_y(gear_r)]
    plane = body
    for p in parts:
        plane = plane.fuse(p)
    plane = plane.clean()
    return plane, {"x_apex": x_apex}


def exact_volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props, 1e-6)
    return props.Mass()


def report(shape, info):
    bb = shape.BoundingBox()
    solids = shape.Solids()
    print(f"valid={shape.isValid()} solids={len(solids)} faces={len(shape.Faces())}")
    print(f"bbox x {bb.xmin:.1f}..{bb.xmax:.1f}  y {bb.ymin:.1f}..{bb.ymax:.1f}  z {bb.zmin:.1f}..{bb.zmax:.1f}")
    print(f"volume {exact_volume(shape) / 1e6:.4f} L   area {shape.Area() / 1e6:.4f} m²")
    print(f"nose apex x={info['x_apex']:.3f}  span={SPAN:.2f}  chord={CHORD:.2f}  wing LE x={X_WING_LE:.2f}")


if __name__ == "__main__":
    # model1_cfd = CFD run 1 geometry (with gear); model1b_nogear = gear removed (decision 2026-09-25, catapult/hand launch)
    # model1c_lightplus = v1 light+ (python model1.py --config light-plus; always without gear)
    # GN+ = that same light+ solid, named for the simulator (python model1.py --config light-plus --out GN+)
    import sys
    config = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else "light"
    apply_config(config)
    with_gear = "--no-gear" not in sys.argv and config == "light"
    name = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else (
        "model1c_lightplus" if config == "light-plus" else ("model1_cfd" if with_gear else "model1b_nogear")
    )
    plane, info = build(with_gear)
    report(plane, info)
    cq.exporters.export(plane, os.path.join(HERE, f"{name}.step"))
    plane.exportStl(os.path.join(HERE, f"{name}.stl"), tolerance=0.05, angularTolerance=0.1, relative=False)
    print(f"exported {name}.step / {name}.stl")
