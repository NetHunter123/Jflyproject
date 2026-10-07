"""GN+ outer shape for CFD (GN+_cfd.step). GN+.step itself stays untouched.

Same outer lines as gn_detail.py, three changes that the CFD needs:
  1. No prop blade. In GN+ it is a flat plate 279.4 x 22 mm facing the flow,
     about 9-10 N of drag at 50 m/s, most of the whole airplane.
  2. Solid body. No 0.7 mm wall, no cavity, no slots, no stud holes, no Ø20
     exit. Cooling is not chosen yet; the open path gets its own run later.
  3. No joiner rod and collar outside the skin. In GN+ the Ø16 rod sits at z=0
     and hangs 3-5 mm below the Clark Y lower surface over |y| 40-90.
The 6 mm spinner/cowl gap stays as a groove down to the hub (R14).

Run:  python gn_cfd.py
Writes GN+_cfd.step, GN+_cfd.stl and prints the checks.
"""
import os

import cadquery as cq

import model1
import nose_tail as nt

HERE = os.path.dirname(os.path.abspath(__file__))
model1.apply_config("light-plus")
HUB_R = 14.0


def spinner_solid():
    x_apex, arc_mid, (xt, yt), ogive_pts, _ = nt.nose_tip()
    spin = [p for p in ogive_pts if nt.SPINNER_REAR - p[0] > 0.2]
    spin.append((nt.SPINNER_REAR, nt.ogive_radius(nt.SPINNER_REAR)))
    return nt.revolve_closed([(x_apex, 0.0), (arc_mid[0], arc_mid[1]), (xt, yt)] + spin)


def hub():
    return cq.Solid.makeCylinder(HUB_R, nt.COWL_FRONT - nt.SPINNER_REAR + 1.0,
                                 cq.Vector(nt.SPINNER_REAR - 0.5, 0, 0), cq.Vector(1, 0, 0))


def cowl_solid():
    return nt.revolve_closed([(nt.COWL_FRONT, 0.0)] + nt.ogive_between(nt.COWL_FRONT, model1.X_NOSE_END))


def tube_solid():
    x0, x1 = model1.X_NOSE_END, model1.X_CONE_START
    return cq.Solid.makeCylinder(nt.R_OD, x1 - x0, cq.Vector(x0, 0, 0), cq.Vector(1, 0, 0))


def tail_solid():
    pts = [(model1.X_CONE_START, 0.0), (model1.X_CONE_START, nt.R_OD)]
    for i in range(1, 41):
        x = model1.X_CONE_START + (model1.X_BASE - model1.X_CONE_START) * i / 40
        pts.append((x, nt.cone_radius(x)))
    cone = nt.revolve_closed(pts)
    # fin shifted onto the cone exactly as nose_tail.tail() does
    saved = (model1.VT_ROOT_LE, model1.VT_TIP_LE)
    shift = (model1.X_CONE_START + 4.0) - model1.VT_ROOT_LE
    model1.VT_ROOT_LE += shift
    model1.VT_TIP_LE += shift
    fin = model1.vertical_tail()
    model1.VT_ROOT_LE, model1.VT_TIP_LE = saved
    return cone.fuse(fin).fuse(model1.horizontal_tail())


def build():
    wing_r = model1.wing_panel_right()
    parts = [spinner_solid(), hub(), cowl_solid(), tube_solid(), tail_solid(), wing_r, model1.mirror_y(wing_r)]
    body = parts[0]
    for p in parts[1:]:
        body = body.fuse(p)
    return body.clean()


def main():
    body = build()
    bb = body.BoundingBox()
    print(f"valid={body.isValid()} solids={len(body.Solids())} shells={len(body.Shells())} faces={len(body.Faces())}")
    print(f"bbox x {bb.xmin:.2f}..{bb.xmax:.2f}  y {bb.ymin:.2f}..{bb.ymax:.2f}  z {bb.zmin:.2f}..{bb.zmax:.2f}")
    print(f"volume {body.Volume() / 1e6:.4f} L  wetted area {body.Area() / 1e6:.4f} m2")
    cq.exporters.export(cq.Workplane(obj=body), os.path.join(HERE, "GN+_cfd.step"))
    body.exportStl(os.path.join(HERE, "GN+_cfd.stl"), tolerance=0.05, angularTolerance=0.1, relative=False)
    print("wrote GN+_cfd.step / GN+_cfd.stl")


if __name__ == "__main__":
    main()
