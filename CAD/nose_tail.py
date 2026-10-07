"""Nose and tail solids for Gungnear v1 light+, stud assembly (Zbirka-shpilky).

Axes match model1.py: x from the nose rearward, y to the right wing, z up. Units: mm.
Locked 2026-09-28: gutter Ø80, skin flush with the tube, plug inside.
  Wall assumed 0.7 mm (Sarei may be 0.6 — measure). Studs M3 on a Ø72 circle
  at 45° to the wing. Plugs are short because the studs and the end face
  carry the load: nose 20 mm, tail 25 mm. Skin 2.4 mm, motor plate 4 mm.
  Motor bolt pattern is a placeholder (4 × M3 on Ø32, shaft hole Ø10).

Run:  python nose_tail.py
Writes nose_lightplus.step/.stl, tail_lightplus.step/.stl and preview PNGs.
"""
import math
import os
import sys

import cadquery as cq

import model1

HERE = os.path.dirname(os.path.abspath(__file__))

# Gutter Ø80. Wall 0.7 mm until a real pipe is measured (Sarei is often 0.6).
R_OD = 40.0
R_ID = 39.3
R_PLUG = 38.9          # 0.4 mm radial clearance if the wall is 0.7 mm
WALL = 2.4
PLATE_T = 4.0
NOSE_SLEEVE = 20.0     # studs + end face hold the cap; a long plug eats the front battery
TAIL_PLUG = 25.0       # a little longer than the nose: the fin root lands on this joint
STUD_R = 36.0          # clears the Ø70 pack and stays inside the plug wall
STUD_HOLE_R = 1.7      # M3 clearance
MOTOR_BOLT_R = 16.0    # placeholder Ø32 pattern
MOTOR_HOLE_R = 1.6
SHAFT_R = 5.0

model1.apply_config("light-plus")
X_NOSE_END = model1.X_NOSE_END
X_CONE_START = model1.X_CONE_START
X_BASE = model1.X_BASE
R_BASE = model1.R_BASE
OGIVE_RHO = model1.OGIVE_RHO
NOSE_BLUNT_R = model1.NOSE_BLUNT_R


def ogive_radius(x):
    return math.sqrt(OGIVE_RHO**2 - (X_NOSE_END - x) ** 2) - (OGIVE_RHO - R_OD)


def nose_tip():
    """Blunt ogive tip, same construction as model1.fuselage, ended at R_OD."""
    xt_c = X_NOSE_END - math.sqrt((OGIVE_RHO - NOSE_BLUNT_R) ** 2 - (OGIVE_RHO - R_OD) ** 2)
    yt = NOSE_BLUNT_R * (OGIVE_RHO - R_OD) / (OGIVE_RHO - NOSE_BLUNT_R)
    xt = xt_c - math.sqrt(NOSE_BLUNT_R**2 - yt**2)
    x_apex = xt_c - NOSE_BLUNT_R
    ang_t = math.atan2(yt, xt - xt_c)
    ang_m = 0.5 * (math.pi + ang_t)
    arc_mid = (xt_c + NOSE_BLUNT_R * math.cos(ang_m), NOSE_BLUNT_R * math.sin(ang_m))
    xs = [xt + (X_NOSE_END - xt) * (1 - math.cos(0.5 * math.pi * i / 40)) for i in range(1, 41)]
    pts = [(x, ogive_radius(x)) for x in xs]
    pts[-1] = (X_NOSE_END, R_OD)
    slope_t = (X_NOSE_END - xt) / math.sqrt(OGIVE_RHO**2 - (X_NOSE_END - xt) ** 2)
    return x_apex, arc_mid, (xt, yt), pts, slope_t


def revolve_closed(pts):
    """Revolve a polyline of (x, r), r >= 0, about the x axis. A spline gap made the cone invalid."""
    wp = cq.Workplane("XZ").moveTo(pts[0][0], -pts[0][1])
    for x, r in pts[1:]:
        wp = wp.lineTo(x, -r)
    if pts[-1][1] != 0:
        wp = wp.lineTo(pts[-1][0], 0)
    wp = wp.lineTo(pts[0][0], 0).close()
    return wp.revolve(360, (0, 0, 0), (1, 0, 0)).val()


def cylinders(radius, x0, x1, centers):
    solids = []
    for y, z in centers:
        solids.append(cq.Solid.makeCylinder(radius, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0)))
    out = solids[0]
    for s in solids[1:]:
        out = out.fuse(s)
    return out


def circle_centers(radius, degrees):
    return [(radius * math.cos(math.radians(d)), radius * math.sin(math.radians(d))) for d in degrees]


PROP_X = 36.0
SPINNER_REAR = 33.0     # spinning tip ends here; it clamps to the prop, not to the cowl
COWL_FRONT = 39.0       # 6 mm gap: cooling air enters behind the spinner
X_PLATE0 = 98.0
SLOT_X0, SLOT_X1 = 104.0, 118.0
SLOT_ANGLES = (0, 90, 180, 270)  # clear of the studs, which sit at 45°
STUD_ANGLES = (45, 135, 225, 315)
MOTOR_ANGLES = (0, 90, 180, 270)


def ogive_between(x0, x1, n=24):
    return [(x0 + (x1 - x0) * i / n, ogive_radius(x0 + (x1 - x0) * i / n)) for i in range(n + 1)]


def nose():
    """Fixed cowl and a separate spinner. The spinner bolts to the prop and is not part of the cowl."""
    x_apex, arc_mid, (xt, yt), ogive_pts, slope_t = nose_tip()
    x_plate0 = X_PLATE0
    x_plate1 = x_plate0 + PLATE_T
    x_plug1 = X_NOSE_END + NOSE_SLEEVE

    spin_ogive = [p for p in ogive_pts if SPINNER_REAR - p[0] > 0.2]
    spin_ogive.append((SPINNER_REAR, ogive_radius(SPINNER_REAR)))
    arc = [(x_apex, 0.0), (arc_mid[0], arc_mid[1]), (xt, yt)]
    spinner = revolve_closed(arc + spin_ogive)
    spin_inner = [(xt + 3.0, 0.0)]
    x = xt + 3.0
    while x < SPINNER_REAR - 2.5:
        spin_inner.append((x, max(ogive_radius(x) - 1.6, 2.0)))
        x += 1.5
    spin_inner += [
        (SPINNER_REAR - 2.5, max(ogive_radius(SPINNER_REAR) - 1.6, 2.0)),
        (SPINNER_REAR - 2.5, 0.0),
    ]
    spinner = spinner.cut(revolve_closed(spin_inner))
    spinner = spinner.cut(cq.Solid.makeCylinder(4.0, 8.0, cq.Vector(SPINNER_REAR - 6.0, 0, 0), cq.Vector(1, 0, 0)))

    cowl = revolve_closed(ogive_between(COWL_FRONT, X_NOSE_END) + [(X_NOSE_END, R_PLUG), (x_plug1, R_PLUG)])
    inner = [(COWL_FRONT, 0.0), (COWL_FRONT, ogive_radius(COWL_FRONT) - WALL)]
    x = COWL_FRONT + 2.0
    while x < x_plate0:
        inner.append((x, max(ogive_radius(x) - WALL, 2.0)))
        x += 2.0
    inner += [(x_plate0, max(ogive_radius(x_plate0) - WALL, 2.0)), (x_plate0, 0.0)]
    cowl = cowl.cut(revolve_closed(inner))
    r_in_plug = R_PLUG - WALL
    bore = cq.Solid.makeCylinder(r_in_plug, x_plug1 - x_plate1, cq.Vector(x_plate1, 0, 0), cq.Vector(1, 0, 0))
    shaft = cq.Solid.makeCylinder(SHAFT_R, 16.0, cq.Vector(x_plate0 - 6.0, 0, 0), cq.Vector(1, 0, 0))
    studs = cylinders(STUD_HOLE_R, x_plate0 - 2.0, x_plug1 + 2.0, circle_centers(STUD_R, STUD_ANGLES))
    motor_bolts = cylinders(MOTOR_HOLE_R, x_plate0 - 2.0, x_plate1 + 2.0, circle_centers(MOTOR_BOLT_R, MOTOR_ANGLES))
    cowl = cowl.cut(bore).cut(shaft).cut(studs).cut(motor_bolts)
    r_slot = ogive_radius(0.5 * (SLOT_X0 + SLOT_X1))
    for ang in SLOT_ANGLES:
        slot = box(SLOT_X0, -4.0, r_slot - 4.0, SLOT_X1 - SLOT_X0, 8.0, 12.0)
        slot = slot.rotate((0, 0, 0), (1, 0, 0), ang)
        cowl = cowl.cut(slot)
    return cowl, spinner, x_apex


def cone_radius(x):
    half_drop = 0.5 * (R_OD - R_BASE)
    length = X_BASE - X_CONE_START
    return R_BASE + half_drop * (1 + math.cos(math.pi * (x - X_CONE_START) / length))


def tail():
    x0 = X_CONE_START - TAIL_PLUG
    x_tip_solid = X_BASE - 12.0
    r_in_plug = R_PLUG - WALL

    outer_pts = [(x0, 0.0), (x0, R_PLUG), (X_CONE_START, R_PLUG), (X_CONE_START, R_OD)]
    for i in range(1, 41):
        x = X_CONE_START + (X_BASE - X_CONE_START) * i / 40
        outer_pts.append((x, cone_radius(x)))
    outer_pts.append((X_BASE, 0.0))
    outer = revolve_closed(outer_pts)
    print(f"tail shell valid={outer.isValid()} faces={len(outer.Faces())}")

    bore = cq.Solid.makeCylinder(r_in_plug, X_CONE_START - x0 - PLATE_T, cq.Vector(x0, 0, 0), cq.Vector(1, 0, 0))
    inner = [(X_CONE_START, 0.0), (X_CONE_START, cone_radius(X_CONE_START) - WALL)]
    x = X_CONE_START + 4.0
    while x < x_tip_solid:
        inner.append((x, max(cone_radius(x) - WALL, 1.0)))
        x += 4.0
    inner.append((x_tip_solid, max(cone_radius(x_tip_solid) - WALL, 1.0)))
    inner.append((x_tip_solid, 0.0))
    cavity = revolve_closed(inner)
    # Keep the fin and stabiliser on the cone. Root LE of the frozen fin sits 1.6 mm
    # ahead of the cone, which would need a slot in the gutter; shift it onto the cone.
    saved = (model1.VT_ROOT_LE, model1.VT_TIP_LE)
    shift = (X_CONE_START + 4.0) - model1.VT_ROOT_LE
    model1.VT_ROOT_LE += shift
    model1.VT_TIP_LE += shift
    fin = model1.vertical_tail()
    stab = model1.horizontal_tail()
    model1.VT_ROOT_LE, model1.VT_TIP_LE = saved

    solid = outer.cut(bore).cut(cavity).fuse(fin).fuse(stab)
    # Nothing may occupy the aluminum wall ahead of the cone.
    guard_outer = cq.Solid.makeCylinder(80.0, X_CONE_START - x0, cq.Vector(x0, 0, 0), cq.Vector(1, 0, 0))
    guard_inner = cq.Solid.makeCylinder(R_PLUG + 0.05, X_CONE_START - x0 + 1.0, cq.Vector(x0 - 0.5, 0, 0), cq.Vector(1, 0, 0))
    solid = solid.cut(guard_outer.cut(guard_inner))
    studs = cylinders(STUD_HOLE_R, x0 - 2.0, X_CONE_START + 2.0, circle_centers(STUD_R, STUD_ANGLES))
    solid = solid.cut(studs)
    # Ø20 exit in the flat Ø30 base. The last 12 mm used to be solid, so cooling air had no way out.
    exit_hole = cq.Solid.makeCylinder(10.0, 22.0, cq.Vector(X_BASE - 20.0, 0, 0), cq.Vector(1, 0, 0))
    solid = solid.cut(exit_hole)
    return solid


def export(solid, stem):
    step = os.path.join(HERE, stem + ".step")
    stl = os.path.join(HERE, stem + ".stl")
    cq.exporters.export(cq.Workplane(obj=solid), step)
    cq.exporters.export(cq.Workplane(obj=solid), stl)
    bb = solid.BoundingBox()
    print(f"{stem}: valid={solid.isValid()} faces={len(solid.Faces())}")
    print(f"  x {bb.xmin:.1f}..{bb.xmax:.1f}  y {bb.ymin:.1f}..{bb.ymax:.1f}  z {bb.zmin:.1f}..{bb.zmax:.1f}")
    print(f"  wrote {step}")
    return stl, ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)


def mesh_of(solid):
    import vtk
    tmp = os.path.join(HERE, "_schematic_tmp.stl")
    cq.exporters.export(cq.Workplane(obj=solid), tmp)
    reader = vtk.vtkSTLReader()
    reader.SetFileName(tmp)
    reader.Update()
    out = vtk.vtkPolyData()
    out.DeepCopy(reader.GetOutput())
    return out


def box(x0, y0, z0, dx, dy, dz):
    return cq.Solid.makeBox(dx, dy, dz, cq.Vector(x0, y0, z0))


def nose_schematic():
    """Prop in the cooling gap, on a 12 mm stock shaft. Spinner is a separate solid, not here."""
    x_prop = PROP_X
    x_motor0 = x_prop + 12.0
    motor_len = X_PLATE0 - x_motor0
    prop = cq.Solid.makeCylinder(14, 10, cq.Vector(x_prop - 2, 0, 0), cq.Vector(1, 0, 0))
    prop = prop.fuse(box(x_prop - 1.5, -139.7, -9, 5, 279.4, 18))
    shaft = cq.Solid.makeCylinder(3.0, 12.0, cq.Vector(x_prop, 0, 0), cq.Vector(1, 0, 0))
    motor = cq.Solid.makeCylinder(23.0, motor_len, cq.Vector(x_motor0, 0, 0), cq.Vector(1, 0, 0))
    esc = box(142.0, -16.0, -8.0, 36.0, 32.0, 16.0)
    plug = box(132.0, -8.0, 24.0, 10.0, 16.0, 12.0)
    return [
        (prop, (0.93, 0.45, 0.12)),
        (shaft, (0.75, 0.75, 0.78)),
        (motor, (0.15, 0.28, 0.62)),
        (esc, (0.15, 0.55, 0.28)),
        (plug, (0.85, 0.65, 0.15)),
    ]


def tail_schematic():
    """Two servos in the cone, pushrods, deflected elevator and rudder, connector at the plug."""
    servo_e = box(1236.0, -20.0, 4.0, 32.0, 16.0, 28.0)
    servo_r = box(1236.0, 4.0, 4.0, 32.0, 16.0, 28.0)
    rod_e = cq.Solid.makeCylinder(1.6, 70.0, cq.Vector(1268.0, -12.0, 18.0), cq.Vector(1, 0, 0))
    rod_r = cq.Solid.makeCylinder(1.6, 90.0, cq.Vector(1268.0, 12.0, 20.0), cq.Vector(0, 0, 1))
    elev = box(1336.0, -200.0, -3.0, 30.0, 400.0, 6.0)
    elev = elev.rotate((1336.0, 0.0, 0.0), (1336.0, 1.0, 0.0), -12.0)
    rud = box(1338.0, -2.5, 55.0, 28.0, 5.0, 130.0)
    rud = rud.rotate((1338.0, 0.0, 90.0), (1338.0, 0.0, 91.0), 15.0)
    conn = box(1202.0, -8.0, 22.0, 8.0, 16.0, 12.0)
    return [
        (servo_e, (0.75, 0.18, 0.18)),
        (servo_r, (0.75, 0.18, 0.18)),
        (rod_e, (0.90, 0.75, 0.15)),
        (rod_r, (0.90, 0.75, 0.15)),
        (elev, (0.93, 0.45, 0.12)),
        (rud, (0.93, 0.45, 0.12)),
        (conn, (0.85, 0.65, 0.15)),
    ]


def render(shell_stl, extras, png, focal, legend):
    import vtk

    reader = vtk.vtkSTLReader()
    reader.SetFileName(shell_stl)
    reader.Update()
    parts = [(reader.GetOutput(), (0.72, 0.75, 0.80))]
    for solid, color in extras:
        parts.append((mesh_of(solid), color))

    plane = vtk.vtkPlane()
    plane.SetOrigin(focal[0], 0.0, focal[2])
    plane.SetNormal(0.0, -1.0, 0.0)

    def actor(poly, color, clipped):
        data = poly
        if clipped:
            clip = vtk.vtkClipPolyData()
            clip.SetInputData(poly)
            clip.SetClipFunction(plane)
            clip.InsideOutOn()
            clip.Update()
            data = clip.GetOutput()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(data)
        act = vtk.vtkActor()
        act.SetMapper(mapper)
        prop = act.GetProperty()
        prop.SetColor(*color)
        prop.SetSpecular(0.25)
        prop.SetSpecularPower(20)
        return act

    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(1700, 900)
    win.SetMultiSamples(8)
    views = [
        ("Зовні", (0.0, 0.0, 0.5, 1.0), False, (focal[0] - 280, focal[1] - 700, focal[2] + 220)),
        ("Розріз", (0.5, 0.0, 1.0, 1.0), True, (focal[0] + 40, focal[1] - 900, focal[2] + 30)),
    ]
    for title, vp, clipped, cam_pos in views:
        ren = vtk.vtkRenderer()
        ren.SetViewport(*vp)
        ren.SetBackground(0.96, 0.97, 0.98)
        for poly, color in parts:
            ren.AddActor(actor(poly, color, clipped))
        cam = ren.GetActiveCamera()
        cam.SetFocalPoint(*focal)
        cam.SetPosition(*cam_pos)
        cam.SetViewUp(0, 0, 1)
        ren.ResetCamera()
        cam.Zoom(1.12)
        txt = vtk.vtkTextActor()
        txt.SetInput(title + "\n" + legend)
        txt.GetTextProperty().SetFontSize(18)
        txt.GetTextProperty().SetColor(0.12, 0.14, 0.2)
        txt.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        txt.GetPositionCoordinate().SetValue(0.02, 0.03)
        ren.AddViewProp(txt)
        win.AddRenderer(ren)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(png)
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    print("wrote", png)


def main():
    cowl, spinner, x_apex = nose()
    print(f"nose apex x={x_apex:.2f}")
    cowl_stl, _ = export(cowl, "nose_lightplus")
    export(spinner, "nose_spinner")
    tail_solid = tail()
    tail_stl, _ = export(tail_solid, "tail_lightplus")
    render(
        cowl_stl,
        [(spinner, (0.95, 0.72, 0.35))] + nose_schematic(),
        os.path.join(HERE, "nose_lightplus.png"),
        (70.0, 0.0, 0.0),
        "бежевий кок на гвинті\nсірий корпус окремо\nщілина — вхід повітря\nпази за мотором — вихід",
    )
    render(
        tail_stl,
        tail_schematic(),
        os.path.join(HERE, "tail_lightplus.png"),
        (1288.0, 0.0, 40.0),
        "червоні серво\nжовті тяги\nпомаранчеві рулі\nжовтий роз'єм",
    )


if __name__ == "__main__":
    sys.exit(main())
