"""GN+ with the nose split, slots, studs and the tail exit from Zbirka-shpilky.

Spinner ends at x=33 and is not part of the cowl. The cowl starts at x=39.
The 6 mm between them is the prop gap. Four slots behind the motor, four M3
stud holes on the nose plug and the tail plug, joiner Ø16 through the tube,
Ø20 exit in the tail face. Gutter skin is Ø80.

Run:  python gn_detail.py
Writes GN+.step, GN+.stl and GN+.png.
"""
import math
import os

import cadquery as cq

import model1
import nose_tail as nt

HERE = os.path.dirname(os.path.abspath(__file__))
model1.apply_config("light-plus")


def joiner_x():
    return model1.X_WING_LE + 0.275 * model1.CHORD


def tube():
    x0 = model1.X_NOSE_END
    x1 = model1.X_CONE_START
    outer = cq.Solid.makeCylinder(nt.R_OD, x1 - x0, cq.Vector(x0, 0, 0), cq.Vector(1, 0, 0))
    inner = cq.Solid.makeCylinder(nt.R_ID, x1 - x0 + 4, cq.Vector(x0 - 2, 0, 0), cq.Vector(1, 0, 0))
    skin = outer.cut(inner)
    # Wing rod passes through both walls. The collar stops the 0.7 mm edge going oval.
    hole = cq.Solid.makeCylinder(9.0, 140.0, cq.Vector(joiner_x(), -70.0, 0), cq.Vector(0, 1, 0))
    return skin.cut(hole)


def collar():
    x = joiner_x()
    y = nt.R_OD - 1.2
    rings = []
    for sign in (1, -1):
        outer = cq.Solid.makeCylinder(13.0, 2.4, cq.Vector(x, sign * y - sign * 1.2, 0), cq.Vector(0, sign, 0))
        inner = cq.Solid.makeCylinder(9.2, 4.0, cq.Vector(x, sign * y - sign * 2.0, 0), cq.Vector(0, sign, 0))
        rings.append(outer.cut(inner))
    return rings[0].fuse(rings[1])


def joiner_rod():
    return cq.Solid.makeCylinder(8.0, 180.0, cq.Vector(joiner_x(), -90.0, 0), cq.Vector(0, 1, 0))


def prop_on_spinner(spinner):
    """Two-blade disc sitting in the 6 mm gap, clamped to the spinner, clear of the cowl."""
    x0 = nt.SPINNER_REAR
    hub = cq.Solid.makeCylinder(14.0, 4.6, cq.Vector(x0, 0, 0), cq.Vector(1, 0, 0))
    blade = cq.Solid.makeBox(3.2, 279.4, 22.0, cq.Vector(x0 + 0.6, -139.7, -11.0))
    return spinner.fuse(hub).fuse(blade)


def fuse_all(parts):
    body = parts[0]
    for part in parts[1:]:
        body = body.fuse(part)
    return body


def build():
    cowl, spinner, _ = nt.nose()
    print("nose built", cowl.isValid(), spinner.isValid())
    tail = nt.tail()
    print("tail built", tail.isValid())
    wing_r = model1.wing_panel_right()
    wing_l = model1.mirror_y(wing_r)
    airframe = fuse_all([cowl, tube(), collar(), joiner_rod(), wing_r, wing_l, tail])
    print("airframe", airframe.isValid(), "faces", len(airframe.Faces()))
    spinning = prop_on_spinner(spinner)
    print("spinner+prop", spinning.isValid())
    return airframe, spinning


def export_stl(solid, stem):
    path = os.path.join(HERE, stem + ".stl")
    cq.exporters.export(cq.Workplane(obj=solid), path)
    return path


def render(air_stl, spin_stl, png):
    import vtk

    def read(path):
        reader = vtk.vtkSTLReader()
        reader.SetFileName(path)
        reader.Update()
        return reader.GetOutput()

    def clip_nose(poly):
        box = vtk.vtkBox()
        box.SetBounds(-5, 150, -45, 45, -50, 55)
        clip = vtk.vtkClipPolyData()
        clip.SetInputData(poly)
        clip.SetClipFunction(box)
        clip.InsideOutOn()
        clip.Update()
        return clip.GetOutput()

    air, spin = read(air_stl), read(spin_stl)

    def actor(poly, color):
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(poly)
        normals.SetFeatureAngle(32)
        normals.SplittingOn()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
        act = vtk.vtkActor()
        act.SetMapper(mapper)
        prop = act.GetProperty()
        prop.SetColor(*color)
        prop.SetSpecular(0.3)
        prop.SetSpecularPower(24)
        return act

    def label(ren, title):
        txt = vtk.vtkTextActor()
        txt.SetInput(title)
        txt.GetTextProperty().SetFontSize(22)
        txt.GetTextProperty().SetColor(0.12, 0.14, 0.2)
        txt.GetTextProperty().BoldOn()
        txt.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        txt.GetPositionCoordinate().SetValue(0.02, 0.03)
        ren.AddViewProp(txt)

    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(1800, 900)
    win.SetMultiSamples(8)

    ren = vtk.vtkRenderer()
    ren.SetViewport(0.0, 0.0, 0.50, 1.0)
    ren.SetBackground(0.96, 0.97, 0.98)
    ren.AddActor(actor(air, (0.78, 0.80, 0.84)))
    ren.AddActor(actor(spin, (0.93, 0.55, 0.18)))
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(680, 0, 30)
    cam.SetPosition(180, -1500, 420)
    cam.SetViewUp(0, 0, 1)
    ren.ResetCamera()
    cam.Zoom(1.2)
    label(ren, "GN+")
    win.AddRenderer(ren)

    ren = vtk.vtkRenderer()
    ren.SetViewport(0.50, 0.0, 1.0, 1.0)
    ren.SetBackground(0.96, 0.97, 0.98)
    ren.AddActor(actor(clip_nose(air), (0.78, 0.80, 0.84)))
    ren.AddActor(actor(clip_nose(spin), (0.93, 0.55, 0.18)))
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(48, 0, 6)
    cam.SetPosition(48, -320, 28)
    cam.SetViewUp(0, 0, 1)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(78)
    label(ren, "Nose")
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
    airframe, spinning = build()
    compound = cq.Compound.makeCompound([airframe, spinning])
    step = os.path.join(HERE, "GN+.step")
    cq.exporters.export(cq.Workplane(obj=compound), step)
    print("wrote", step, "valid", compound.isValid())
    air_stl = export_stl(airframe, "GN+_airframe")
    spin_stl = export_stl(spinning, "GN+_nose")
    # One mesh for the simulator import, spinner included, gap kept.
    export_stl(compound, "GN+")
    render(air_stl, spin_stl, os.path.join(HERE, "GN+.png"))


if __name__ == "__main__":
    main()
