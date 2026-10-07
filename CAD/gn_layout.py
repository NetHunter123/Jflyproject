"""R08: electronics layout for light+ (gutter Ø80, no hatches, stud assembly).

Every part is a box or a cylinder with datasheet dimensions (see R08-Elektronik.md).
x keeps the R07c stations: tube 120..1230.26, joiner 589.25, CG box 575..596.
Axes as model1.py: x aft, y to the right wing, z up. Units: mm, g.

Variant A (proposed): the printed nose grows by a 92 mm bay. Motor, ESC, current
sensor, FPV and the nose half of the main connector live in the removable nose.
Variant B (R07c baseline): nose unchanged, ESC and FPV in a dorsal pod on the cowl.
Only A is built as geometry. B is a mass and CG comparison.

Run:  python gn_layout.py
Writes GN+_layout.step, layout_report.json and three drawings in ../../../../_Assets.
"""
import json
import math
import os

import model1
import nose_tail as nt

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "_Assets"))
model1.apply_config("light-plus")

R_OD = nt.R_OD
R_ID = nt.R_ID                      # gutter 80 x 0.7
COWL_WALL = nt.WALL                 # printed skin 2.4
X_TUBE0 = model1.X_NOSE_END         # 120
X_TUBE1 = model1.X_CONE_START       # 1230.26
X_BASE = model1.X_BASE              # 1371.26
X_JOINER = model1.X_WING_LE + 0.275 * model1.CHORD
STUD_R = nt.STUD_R

# Nose, in the coordinates of the old cowl (before the bay is inserted).
# Scorpion SII-4035-380: Ø48.8, body 64.9. Bell front at old x 54 leaves 2.6 mm to the cowl.
MOTOR_D = 48.8
MOTOR_BODY = 64.9
OLD_BELL_FRONT = 54.0
OLD_PLATE0 = OLD_BELL_FRONT + MOTOR_BODY            # 118.9
PLATE_T = 4.0
PROP_HUB_D, PROP_HUB_T = 25.4, 14.5                 # APC 11x14 (LP11014)
OLD_HUB1 = OLD_BELL_FRONT - 5.0                     # nut, washer and shaft collar
OLD_SPINNER_REAR = OLD_HUB1 + 1.0
OLD_COWL_FRONT = OLD_SPINNER_REAR + 2.0
BAY = 92.0              # 8 phase-wire slack + 69 ESC + 15 for the input leads
NOSE_PLUG = 14.0        # was 20; the front pack starts 16 mm into the tube


def nose_shift(variant):
    """How far the old nose moves forward. A: the bay ends at the tube."""
    if variant == "B":
        return 0.0
    plate_rear_new = X_TUBE0 - BAY
    return OLD_PLATE0 + PLATE_T - plate_rear_new


def r_out(x, variant="A"):
    e = nose_shift(variant)
    if x <= X_TUBE0 - e:
        return max(nt.ogive_radius(min(x + e, X_TUBE0)), 0.0)
    if x <= X_TUBE1:
        return R_OD
    return nt.cone_radius(min(x, X_BASE))


def r_in(x, variant="A"):
    """Free radius inside the skin at x."""
    if X_TUBE0 <= x < X_TUBE0 + NOSE_PLUG or X_TUBE1 - nt.TAIL_PLUG < x <= X_TUBE1:
        return nt.R_PLUG - COWL_WALL          # plug bores
    if X_TUBE0 <= x <= X_TUBE1:
        return R_ID
    return r_out(x, variant) - COWL_WALL


# ---------------------------------------------------------------- parts
# kind "box": (x0, x1, y0, y1, z0, z1). kind "cyl": axis x, (x0, x1, r, yc, zc).
# check: inside the skin. wing parts are checked separately.

def nose_parts(e):
    def n(x):
        return x - e
    bay0 = X_TUBE0 - BAY
    esc0 = bay0 + 8.0
    parts = [
        dict(id="M", name="Мотор Scorpion SII-4035-380", kind="cyl",
             geo=(n(OLD_BELL_FRONT), n(OLD_PLATE0), MOTOR_D / 2, 0, 0), m=435, xcg=n(OLD_PLATE0) - 28.0,
             src="scorpionsystem.com", group="nose", check=True),
        dict(id="P", name="Гвинт APC 11×14 (LP11014), маточина", kind="cyl",
             geo=(n(OLD_HUB1 - PROP_HUB_T), n(OLD_HUB1), PROP_HUB_D / 2, 0, 0), m=39,
             src="apcprop.com", group="nose", check=False),
        dict(id="S", name="Кок друкований з вирізами під лопаті", kind="none",
             geo=None, m=20, xcg=n(OLD_SPINNER_REAR) - 22.0, src="оцінка", group="nose"),
        dict(id="C", name="Капот + моторна плита (друк)", kind="none",
             geo=None, m=61, xcg=n(90.0), src="R07b-V залишок групи", group="nose"),
        dict(id="BAY", name="Відсік ESC: циліндр Ø80, 92 мм (друк 1,6 мм + ребра)", kind="none",
             geo=None, m=50, xcg=bay0 + BAY / 2, src="оцінка", group="nose"),
        dict(id="E", name="ESC Castle Phoenix Edge Lite HV 80", kind="box",
             geo=(esc0, esc0 + 69.0, -15.25, 15.25, -10.7, 10.7), m=94.6,
             src="castlecreations.com / kingslynnmodelshop", group="nose", check=True),
        dict(id="I", name="Датчик струму Mauch HS-100-HV", kind="box",
             geo=(esc0 + 22.0, esc0 + 69.0, -9.0, 9.0, 12.0, 23.0), m=8,
             src="mauch-electronic.com", group="nose", check=True),
        dict(id="V", name="DJI O4 Air Unit (Lite), модуль", kind="box",
             geo=(bay0 + 12.0, bay0 + 42.0, -15.0, 15.0, 25.0, 31.0), m=5.9,
             src="DJI / getfpv", group="nose", check=True),
        dict(id="K", name="Камера O4 Lite у блістері", kind="box",
             geo=(bay0 + 2.0, bay0 + 18.5, -6.72, 6.72, 35.0, 47.36), m=6.1,
             src="DJI / getfpv", group="nose", check=False),
        dict(id="X1", name="XT90-S, пара (ніс ↔ батарея, сліпе з'єднання)", kind="box",
             geo=(X_TUBE0 + 16.0 - 49.0, X_TUBE0 + 16.0, -10.5, 10.5, -23.0, -13.0), m=15.3,
             src="Amass / rotorama", group="nose", check=True),
        dict(id="J1", name="MPX8 (ніс ↔ батарея), сигнали + шина 12S", kind="box",
             geo=(X_TUBE0 + 16.0 - 30.0, X_TUBE0 + 16.0, -7.0, 7.0, 25.0, 35.0), m=6,
             src="розмір ≈, зміряти", group="nose", check=True),
    ]
    return parts


def body_parts():
    cell_l = 70.15
    parts = [
        dict(id="B1", name="Передній блок 6S3P (18 × 21700)", kind="ring6",
             geo=(136.0, 350.25), m=1317, src="R07c / Molicel", group="body", check=True),
        dict(id="Q1", name="Передня камера вантажу Ø66", kind="cyl",
             geo=(354.25, 574.25, 33.0, 0, 0), m=0, src="R07c", group="body", check=True),
        dict(id="R", name="Кільце + XT90 (зв'язка блоків) + MPX8", kind="none",
             geo=None, m=20, xcg=X_JOINER, src="Amass / оцінка", group="body"),
        dict(id="Q2", name="Задня камера вантажу Ø66", kind="cyl",
             geo=(604.25, 824.25, 33.0, 0, 0), m=0, src="R07c", group="body", check=True),
        dict(id="B2", name="Задній блок 6S3P (18 × 21700)", kind="ring6",
             geo=(843.26, 1057.51), m=1317, src="R07c / Molicel", group="body", check=True),
        dict(id="W1", name="Провід R+ крізь передній блок (10 AWG)", kind="none",
             geo=None, m=21, xcg=220.0, src="оцінка 64 г/м", group="body"),
        dict(id="W2", name="Джгут ніс → корма: шина 12S 2×20 AWG + 6 сигналів", kind="none",
             geo=None, m=27, xcg=610.0, src="оцінка", group="body"),
        dict(id="W3", name="Проводи серв крила до корми", kind="none",
             geo=None, m=8, xcg=860.0, src="оцінка", group="body"),
    ]
    assert abs(3 * cell_l + 4.0 - (350.25 - 136.0)) < 0.3
    return parts


def rear_parts():
    x_iface0 = 1060.0
    x_bay0 = 1090.0
    servo_x1 = X_TUBE1 - 4.0
    servo_x0 = servo_x1 - 35.5
    parts = [
        dict(id="J2", name="2 × MPX8 (батарея ↔ задній модуль)", kind="box",
             geo=(x_iface0, x_iface0 + 28.0, -7.0, 7.0, -30.0, 30.0), m=12,
             src="розмір ≈, зміряти", group="rear", check=True),
        dict(id="PM", name="BEC Matek PM12S-3", kind="box",
             geo=(x_bay0, x_bay0 + 61.0, -20.0, 20.0, -20.0, -5.0), m=53,
             src="mateksys.com", group="rear", check=True),
        dict(id="FC", name="Польотник Matek H743-WING V3", kind="box",
             geo=(x_bay0 + 4.0, x_bay0 + 58.0, -18.0, 18.0, -2.0, 11.0), m=30,
             src="getfpv / mateksys", group="rear", check=True),
        dict(id="A", name="Датчик швидкості Matek ASPD-4525", kind="box",
             geo=(x_bay0 + 62.0, x_bay0 + 82.0, -10.0, 10.0, -2.0, 4.0), m=3.5,
             src="readymaderc (плата ≈20×20)", group="rear", check=True),
        dict(id="D", name="Розподіл 8 В на серви", kind="none",
             geo=None, m=5, xcg=x_bay0 + 30.0, src="оцінка", group="rear"),
        dict(id="T1", name="Серво висоти KST X10", kind="box",
             geo=(servo_x0, servo_x1, -12.0, -2.0, -14.8, 14.8), m=28,
             src="KST / buddyrc", group="cone", check=True),
        dict(id="T2", name="Серво напрямку KST X10", kind="box",
             geo=(servo_x0, servo_x1, 2.0, 12.0, -14.8, 14.8), m=28,
             src="KST / buddyrc", group="cone", check=True),
        dict(id="TR", name="Тяги, кабанчики, качалки хвоста", kind="none",
             geo=None, m=20, xcg=1280.0, src="оцінка", group="cone"),
        dict(id="G", name="GPS Matek M10Q-5883", kind="box",
             geo=(1236.0, 1256.0, -10.0, 10.0, 20.0, 32.4), m=8,
             src="readymaderc / rotorama", group="cone", check=True),
        dict(id="RX", name="Приймач RadioMaster RP3 V2 (ELRS 2,4)", kind="box",
             geo=(1262.0, 1284.0, -6.5, 6.5, 9.0, 13.0), m=4.6,
             src="buddyrc", group="cone", check=True),
    ]
    return parts


def wing_parts():
    le = model1.X_WING_LE
    c = model1.CHORD
    hinge = le + 0.75 * c
    sx0 = le + 0.48 * c - 15.0
    return [
        dict(id="WS", name="2 × серво елеронів KST X10 (у крилі)", kind="wing_servo",
             geo=(sx0, sx0 + 30.0, 345.0, 380.5, -5.0, 5.0), m=56, xcg=sx0 + 15.0,
             src="KST / buddyrc", group="wing"),
        dict(id="WL", name="Тяги, кабанчики, кришки серв крила", kind="none",
             geo=None, m=24, xcg=hinge - 10.0, src="оцінка", group="wing"),
        dict(id="PT", name="Трубка Піто + 2 × 0,9 м силікону", kind="pitot",
             geo=(le - 40.0, le + 10.0, 300.0), m=8.4, xcg=760.0, src="Matek комплект / оцінка", group="wing"),
    ]


def ring6_cells(x0, x1, gap=0.5, d=21.55, phase=30.0):
    rc = d + gap        # 6 cells around a hole: centre radius equals the pitch
    return [(rc * math.cos(math.radians(phase + 60 * k)), rc * math.sin(math.radians(phase + 60 * k))) for k in range(6)], rc, d


def part_cg(p):
    if "xcg" in p and p.get("xcg") is not None:
        return p["xcg"]
    g = p["geo"]
    if p["kind"] in ("box", "wing_servo", "cyl", "ring6"):
        return 0.5 * (g[0] + g[1])
    raise ValueError(p["id"])


# ---------------------------------------------------------------- mass and CG

BASE_MASS = 7750.0
BASE_CG = 590.6
# Electronics already inside the R07c number (R07b-V budget), removed before the new list is added.
OLD_ITEMS = [
    ("мотор 12S (бюджет)", 380, 88.0),
    ("гвинт", 39, 48.0),
    ("кок, моторама, капот", 81, 70.0),
    ("ESC у спинному обтічнику + проводка, роз'єми, запобіжник", 271, 165.0),
    ("авіоніка FC/GPS/RX/BEC у кормі", 96, 1132.0),
    ("2 серво хвоста з тягами", 75, 1142.0),
    ("4 серво крила (елерони + закрилки)", 149, 620.0),
    ("проводка після перенесення авіоніки", 20, 600.0),
]
CG_BOX = (575.0, 596.0)
FIRST_FLIGHTS = (583.0, 590.0)


def new_items(variant):
    e = nose_shift(variant)
    items = []
    for p in nose_parts(e) + body_parts() + rear_parts() + wing_parts():
        if p["id"] in ("B1", "B2", "Q1", "Q2"):
            continue          # battery and payload are already in the base at the same place
        if variant == "B" and p["id"] == "BAY":
            continue
        items.append((p["id"], p["name"], p["m"], part_cg(p)))
    if variant == "B":
        # Dorsal pod on the cowl: ESC, sensor, FPV and the main XT90-S ride in it.
        pod = {"E": 80.0, "I": 85.0, "V": 70.0, "K": 40.0, "X1": 90.0, "J1": 112.0}
        items = [(i, n, m, pod.get(i, x)) for i, n, m, x in items]
        items.append(("POD", "спинний обтічник ESC (≈75×55×28)", 18, 80.0))
    return items


def mass_cg(variant):
    m = BASE_MASS
    mx = BASE_MASS * BASE_CG
    for _, mi, xi in OLD_ITEMS:
        m -= mi
        mx -= mi * xi
    removed = sum(mi for _, mi, _ in OLD_ITEMS)
    added = 0.0
    for _, _, mi, xi in new_items(variant):
        m += mi
        mx += mi * xi
        added += mi
    return m, mx / m, removed, added


def ballast_for(target, variant, x_ballast):
    m, cg, _, _ = mass_cg(variant)
    # m*cg + b*xb = (m+b)*target
    return max(0.0, m * (cg - target) / (target - x_ballast))


# ---------------------------------------------------------------- checks

def box_corners(g):
    x0, x1, y0, y1, z0, z1 = g
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def min_radius_over(x0, x1, variant, fn=r_in, n=40):
    return min(fn(x0 + (x1 - x0) * i / n, variant) for i in range(n + 1))


def check_inside(p, variant):
    g = p["geo"]
    if p["kind"] == "box":
        need = max(math.hypot(y, z) for _, y, z in box_corners(g))
        have = min_radius_over(g[0], g[1], variant)
    elif p["kind"] == "cyl":
        need = g[2] + math.hypot(g[3], g[4])
        have = min_radius_over(g[0], g[1], variant)
    elif p["kind"] == "ring6":
        centers, rc, d = ring6_cells(*g)
        need = rc + d / 2 + 0.8          # printed sleeve
        have = min_radius_over(g[0], g[1], variant)
    else:
        return None
    return have - need


def aabb(p):
    g = p["geo"]
    if p["kind"] == "box":
        return g
    if p["kind"] == "cyl":
        x0, x1, r, yc, zc = g
        return (x0, x1, yc - r, yc + r, zc - r, zc + r)
    if p["kind"] == "ring6":
        centers, rc, d = ring6_cells(*g)
        rr = rc + d / 2 + 0.8
        return (g[0], g[1], -rr, rr, -rr, rr)
    return None


def overlap(a, b):
    return all(min(a[2 * i + 1], b[2 * i + 1]) - max(a[2 * i], b[2 * i]) > 0.01 for i in range(3))


def run_checks(variant="A"):
    e = nose_shift(variant)
    parts = nose_parts(e) + body_parts() + rear_parts()
    rows = []
    for p in parts:
        if p.get("check"):
            c = check_inside(p, variant)
            if c is not None:
                rows.append((p["id"], p["name"], round(c, 2)))
    clashes = []
    solid = [p for p in parts if aabb(p) is not None and p["id"] not in ("P",)]
    for i, a in enumerate(solid):
        for b in solid[i + 1:]:
            if overlap(aabb(a), aabb(b)):
                clashes.append((a["id"], b["id"]))
    # Studs on Ø72 at 45° against the 6-cell ring.
    centers, rc, d = ring6_cells(136.0, 350.25)
    stud_gap = min(
        math.hypot(STUD_R * math.cos(math.radians(a)) - cy, STUD_R * math.sin(math.radians(a)) - cz) - d / 2 - 1.5
        for a in nt.STUD_ANGLES for cy, cz in centers
    )
    hole = rc - d / 2
    return rows, clashes, stud_gap, hole


# ---------------------------------------------------------------- CAD

def build_step(path):
    import cadquery as cq
    e = nose_shift("A")
    asm = cq.Assembly(name="GN+_layout")

    xs = [-e - 2.5 + i * 2.0 for i in range(int((X_BASE + e + 2.5) / 2.0) + 1)] + [X_BASE]
    outer = [(x, max(r_out(x), 0.0)) for x in xs if x >= nt.nose_tip()[0] - e]
    outer = [(outer[0][0], 0.0)] + outer[1:]
    shell = nt.revolve_closed(outer)
    inner_pts = [(x, r_in(x)) for x, _ in outer[1:] if r_in(x) > 1.0]
    inner = nt.revolve_closed([(inner_pts[0][0], 0.0)] + inner_pts + [(inner_pts[-1][0], 0.0)])
    shell = shell.cut(inner)
    asm.add(shell, name="skin", color=cq.Color(0.75, 0.77, 0.80, 0.25))

    colors = {"nose": (0.85, 0.35, 0.15), "body": (0.20, 0.45, 0.75), "rear": (0.20, 0.60, 0.30),
              "cone": (0.75, 0.20, 0.20), "wing": (0.55, 0.30, 0.65)}
    for p in nose_parts(e) + body_parts() + rear_parts() + wing_parts():
        col = cq.Color(*colors[p["group"]], 1.0)
        g = p["geo"]
        if p["kind"] in ("box", "wing_servo"):
            x0, x1, y0, y1, z0, z1 = g
            if p["kind"] == "wing_servo":
                for s in (1, -1):
                    ya, yb = sorted((s * y0, s * y1))
                    zc = 6.0
                    solid = cq.Solid.makeBox(x1 - x0, yb - ya, z1 - z0, cq.Vector(x0, ya, zc + z0))
                    asm.add(solid, name=f"{p['id']}_{'R' if s > 0 else 'L'}", color=col)
                continue
            solid = cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
        elif p["kind"] == "cyl":
            x0, x1, r, yc, zc = g
            solid = cq.Solid.makeCylinder(r, x1 - x0, cq.Vector(x0, yc, zc), cq.Vector(1, 0, 0))
        elif p["kind"] == "ring6":
            centers, rc, d = ring6_cells(*g)
            cells = [cq.Solid.makeCylinder(d / 2, g[1] - g[0], cq.Vector(g[0], cy, cz), cq.Vector(1, 0, 0)) for cy, cz in centers]
            solid = cq.Compound.makeCompound(cells)
        else:
            continue
        asm.add(solid, name=p["id"], color=col)
    asm.save(path, exportType="STEP")
    return path


# ---------------------------------------------------------------- drawings

def drawings(report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    e = nose_shift("A")
    parts = nose_parts(e) + body_parts() + rear_parts()
    col = {"nose": "#d9592b", "body": "#3a73bf", "rear": "#3a9a4f", "cone": "#c03535", "wing": "#8c4fa6"}
    x_tip = nt.nose_tip()[0] - e

    # ---- side section
    fig, ax = plt.subplots(figsize=(22, 6.2), dpi=130)
    xs = [x_tip + i * 1.0 for i in range(int(X_BASE - x_tip) + 1)]
    ax.plot(xs, [r_out(x) for x in xs], color="#333", lw=1.2)
    ax.plot(xs, [-r_out(x) for x in xs], color="#333", lw=1.2)
    ax.fill_between([X_TUBE0, X_TUBE1], [R_ID] * 2, [R_OD] * 2, color="#999")
    ax.fill_between([X_TUBE0, X_TUBE1], [-R_OD] * 2, [-R_ID] * 2, color="#999")
    ax.axvspan(X_TUBE0 - BAY, X_TUBE0, color="#f6d9c9", alpha=0.45, lw=0)
    le, c = model1.X_WING_LE, model1.CHORD
    ax.add_patch(Rectangle((le, -3), c, 6, fc="none", ec="#8c4fa6", lw=1, ls="--"))
    ax.add_patch(Circle((X_JOINER, 0), 8, fc="#bbb", ec="#555"))
    for p in parts:
        g = p["geo"]
        if p["kind"] == "box":
            ax.add_patch(Rectangle((g[0], g[4]), g[1] - g[0], g[5] - g[4], fc=col[p["group"]], ec="k", lw=0.6, alpha=0.85))
            ax.text(0.5 * (g[0] + g[1]), 0.5 * (g[4] + g[5]), p["id"], ha="center", va="center", fontsize=7, color="w", weight="bold")
        elif p["kind"] == "cyl":
            fc = "none" if p["id"].startswith("Q") else col[p["group"]]
            ax.add_patch(Rectangle((g[0], -g[2]), g[1] - g[0], 2 * g[2], fc=fc, ec=col[p["group"]], lw=1.0, alpha=0.6 if fc != "none" else 1, hatch="//" if fc == "none" else None))
            ax.text(0.5 * (g[0] + g[1]), 0, p["id"], ha="center", va="center", fontsize=9, weight="bold")
        elif p["kind"] == "ring6":
            centers, rc, d = ring6_cells(*g)
            for zc in sorted({round(z, 2) for _, z in centers}):
                ax.add_patch(Rectangle((g[0], zc - d / 2), g[1] - g[0], d, fc=col["body"], ec="k", lw=0.4, alpha=0.35))
            ax.text(0.5 * (g[0] + g[1]), 0, p["id"], ha="center", va="center", fontsize=9, weight="bold")
    # motor plate, plugs, ring
    ax.add_patch(Rectangle((X_TUBE0 - BAY - PLATE_T, -36), PLATE_T, 72, fc="#666"))
    ax.add_patch(Rectangle((X_TUBE0, -38.9), NOSE_PLUG, 2.4, fc="#d9592b"))
    ax.add_patch(Rectangle((X_TUBE0, 36.5), NOSE_PLUG, 2.4, fc="#d9592b"))
    ax.add_patch(Rectangle((X_JOINER - 12, -38.9), 24, 77.8, fc="none", ec="#555", lw=1.2))
    ax.add_patch(Rectangle((X_TUBE1 - nt.TAIL_PLUG, -38.9), nt.TAIL_PLUG, 2.4, fc="#c03535"))
    ax.add_patch(Rectangle((X_TUBE1 - nt.TAIL_PLUG, 36.5), nt.TAIL_PLUG, 2.4, fc="#c03535"))
    # studs
    ax.plot([X_TUBE0 - BAY - PLATE_T, X_JOINER - 12], [STUD_R * 0.7071] * 2, color="#b8860b", lw=0.8, ls="-.")
    ax.plot([X_JOINER + 12, X_TUBE1], [STUD_R * 0.7071] * 2, color="#b8860b", lw=0.8, ls="-.")
    # CG
    m_new, cg_new = report["A"]["mass"], report["A"]["cg"]
    ax.axvspan(*CG_BOX, color="#7fd17f", alpha=0.25)
    ax.plot([BASE_CG], [0], marker="x", ms=11, color="k")
    ax.plot([cg_new], [0], marker="o", ms=9, mfc="#ffd400", mec="k")
    ax.annotate(f"ЦМ A {cg_new:.1f}", (cg_new, 0), (cg_new + 15, -62), arrowprops=dict(arrowstyle="-", lw=0.6), fontsize=8)
    # stations
    stations = [x_tip, X_TUBE0 - BAY - PLATE_T, X_TUBE0 - BAY, X_TUBE0, 136.0, 350.25, 354.25, 574.25, X_JOINER,
                604.25, 824.25, 843.26, 1057.51, 1090.0, X_TUBE1 - 39.5, X_TUBE1, X_BASE]
    for i, s in enumerate(stations):
        ax.plot([s, s], [-66, -50], color="#555", lw=0.6)
        ax.text(s, -70 - 9 * (i % 2), f"{s:.0f}", ha="center", va="top", fontsize=7)
    ax.set_xlim(x_tip - 10, X_BASE + 10)
    ax.set_ylim(-92, 68)
    ax.set_aspect("equal")
    ax.set_yticks([])
    ax.set_title(f"GN+ — розклад електроніки, варіант A (ніс +{BAY:.0f} мм відсік ESC). Бічний розріз, мм. "
                 f"Маса ≈{m_new / 1000:.2f} кг, ЦМ {cg_new:.1f} мм (коробка 575–596, × — R07c 590,6)", fontsize=10)
    legend = ("M мотор · P гвинт · E ESC · I датчик струму · V відеомодуль · K камера · X1 XT90-S · J1/J2 MPX8 · "
              "B1/B2 батарея · Q1/Q2 камери вантажу · PM BEC · FC польотник · A датчик швидкості · "
              "T1/T2 серво хвоста · G GPS · RX приймач")
    ax.text(x_tip, 60, legend, fontsize=7.5, va="top")
    fig.tight_layout()
    side = os.path.join(ASSETS, "gungnear-r08-layout-side.png")
    fig.savefig(side, bbox_inches="tight")
    plt.close(fig)

    # ---- cross-sections
    cuts = [("Перед ESC: камера", X_TUBE0 - BAY + 10), ("Відсік ESC", X_TUBE0 - BAY + 30), ("Відсік, задня частина", 100.0),
            ("Передній блок", 243.0), ("Камера вантажу", 464.0), ("Кільце, джойнер", X_JOINER),
            ("Задній модуль", 1120.0), ("Серво на конусі", 1210.0), ("Конус: GPS", 1246.0), ("Конус: RX", 1273.0)]
    fig, axs = plt.subplots(1, len(cuts), figsize=(26, 3.6), dpi=130)
    for ax, (title, x) in zip(axs, cuts):
        ro, ri = r_out(x), r_in(x)
        ax.add_patch(Circle((0, 0), ro, fc="#ddd", ec="#333"))
        ax.add_patch(Circle((0, 0), ri, fc="white", ec="#333", lw=0.6))
        for a in nt.STUD_ANGLES:
            if X_TUBE0 - BAY - PLATE_T <= x <= X_TUBE1:
                ax.add_patch(Circle((STUD_R * math.cos(math.radians(a)), STUD_R * math.sin(math.radians(a))), 1.5, fc="#b8860b"))
        for p in parts:
            g = p["geo"]
            if p["kind"] == "box" and g[0] <= x <= g[1]:
                ax.add_patch(Rectangle((g[2], g[4]), g[3] - g[2], g[5] - g[4], fc=col[p["group"]], ec="k", lw=0.5, alpha=0.85))
                ax.text(0.5 * (g[2] + g[3]), 0.5 * (g[4] + g[5]), p["id"], ha="center", va="center", fontsize=6, color="w", weight="bold")
            elif p["kind"] == "cyl" and g[0] <= x <= g[1]:
                ax.add_patch(Circle((g[3], g[4]), g[2], fc="none" if p["id"].startswith("Q") else col[p["group"]], ec=col[p["group"]], lw=1, hatch="//" if p["id"].startswith("Q") else None, alpha=0.7))
                ax.text(0, 0, p["id"], ha="center", va="center", fontsize=7)
            elif p["kind"] == "ring6" and g[0] <= x <= g[1]:
                centers, rc, d = ring6_cells(*g)
                for cy, cz in centers:
                    ax.add_patch(Circle((cy, cz), d / 2, fc=col["body"], ec="k", lw=0.5, alpha=0.6))
                ax.add_patch(Circle((0, 0), rc - d / 2, fc="none", ec="#999", ls=":"))
                ax.text(0, 0, f"отвір\nØ{2 * (rc - d / 2):.1f}", ha="center", va="center", fontsize=6)
        if abs(x - X_JOINER) < 1:
            ax.add_patch(Rectangle((-R_OD - 8, -8), 2 * R_OD + 16, 16, fc="#bbb", ec="#555"))
        ax.set_xlim(-48, 48)
        ax.set_ylim(-48, 52)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{title}\nx = {x:.0f}, вільний Ø{2 * ri:.1f}", fontsize=8)
    fig.suptitle("Поперечні розрізи (вигляд ззаду, y праворуч, z вгору). Жовті точки — шпильки М3 на Ø72", fontsize=9)
    fig.tight_layout()
    sec = os.path.join(ASSETS, "gungnear-r08-layout-sections.png")
    fig.savefig(sec, bbox_inches="tight")
    plt.close(fig)

    # ---- half wing plan
    fig, ax = plt.subplots(figsize=(10, 4.4), dpi=130)
    semi = model1.SPAN / 2
    ax.add_patch(Rectangle((0, le), semi, c, fc="#f1eaf5", ec="#333"))
    ax.add_patch(Rectangle((330, le + 0.75 * c), 310, 0.25 * c, fc="#d8c4e3", ec="#333"))
    ax.text(485, le + 0.875 * c, "елерон 310 × 56 (25 % хорди), y 330–640", ha="center", va="center", fontsize=8)
    ax.plot([0, semi], [X_JOINER] * 2, color="#555", ls="--", lw=0.8)
    ax.text(semi - 5, X_JOINER - 4, "лонжерон / джойнер x 589", ha="right", fontsize=7)
    ws = wing_parts()[0]["geo"]
    ax.add_patch(Rectangle((ws[2], ws[0]), ws[3] - ws[2], ws[1] - ws[0], fc=col["wing"], ec="k"))
    ax.text(ws[3] + 6, 0.5 * (ws[0] + ws[1]), "серво KST X10\n35,5 × 30 × 10, x 620–650, y 345–380", fontsize=7, va="center")
    pt = wing_parts()[2]["geo"]
    ax.plot([pt[2], pt[2]], [pt[0], pt[1]], color="k", lw=3)
    ax.text(pt[2] + 6, pt[0] + 4, "Піто Ø≈4, виступ 40 мм, y 300\n(поза струменем гвинта r≈140)", fontsize=7)
    ax.add_patch(Rectangle((0, le), R_OD, c, fc="#ccc", ec="#333"))
    ax.set_xlim(-10, semi + 20)
    ax.set_ylim(le + c + 15, le - 55)
    ax.set_aspect("equal")
    ax.set_xlabel("y, мм від осі")
    ax.set_ylabel("x, мм")
    ax.set_title("Праве півкрило, вигляд зверху (ліве дзеркальне)", fontsize=9)
    fig.tight_layout()
    wing = os.path.join(ASSETS, "gungnear-r08-layout-wing.png")
    fig.savefig(wing, bbox_inches="tight")
    plt.close(fig)
    return side, sec, wing


def main():
    report = {}
    for v in ("A", "B"):
        m, cg, removed, added = mass_cg(v)
        report[v] = dict(mass=round(m, 1), cg=round(cg, 2), removed=removed, added=round(added, 1),
                         nose_shift=round(nose_shift(v), 2),
                         length=round(X_BASE - (nt.nose_tip()[0] - nose_shift(v)), 1),
                         ballast_to_590=round(ballast_for(590.0, v, X_TUBE0 - BAY + 40 if v == "A" else 100.0), 1),
                         items=[dict(id=i, name=n, m=mi, x=round(xi, 1)) for i, n, mi, xi in new_items(v)])
    rows, clashes, stud_gap, hole = run_checks("A")
    report["checks"] = dict(clearance=[dict(id=i, name=n, mm=c) for i, n, c in rows], clashes=clashes,
                            stud_to_cell=round(stud_gap, 2), battery_hole_d=round(2 * hole, 2))
    e = nose_shift("A")
    report["stations_A"] = dict(
        nose_tip=round(nt.nose_tip()[0] - e, 1), spinner_rear=round(OLD_SPINNER_REAR - e, 1),
        prop_hub=(round(OLD_HUB1 - PROP_HUB_T - e, 1), round(OLD_HUB1 - e, 1)),
        cowl_front=round(OLD_COWL_FRONT - e, 1), bell_front=round(OLD_BELL_FRONT - e, 1),
        plate=(round(OLD_PLATE0 - e, 1), round(OLD_PLATE0 + PLATE_T - e, 1)), bay=(X_TUBE0 - BAY, X_TUBE0),
        bell_clearance=round(nt.ogive_radius(OLD_BELL_FRONT) - COWL_WALL - MOTOR_D / 2, 2),
    )
    with open(os.path.join(HERE, "layout_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    for v in ("A", "B"):
        r = report[v]
        print(f"{v}: mass {r['mass']} g, CG {r['cg']} mm, length {r['length']}, removed {r['removed']}, added {r['added']}, ballast to 590: {r['ballast_to_590']} g")
    print("clearances (mm, >0 fits):")
    for c in report["checks"]["clearance"]:
        print(f"  {c['id']:>3} {c['mm']:7.2f}  {c['name']}")
    print("clashes:", clashes)
    print("stud to cell:", report["checks"]["stud_to_cell"], "battery hole Ø", report["checks"]["battery_hole_d"])
    print("stations A:", report["stations_A"])
    print(drawings(report))
    print(build_step(os.path.join(HERE, "GN+_layout.step")))


if __name__ == "__main__":
    main()
