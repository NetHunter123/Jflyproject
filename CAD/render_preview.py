"""Offscreen 4-view render of model1_cfd.stl -> _Assets/gungnear-r07a-model1.png"""
import os
import sys

import vtk

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "model1_preview.png")
STL = os.path.join(HERE, sys.argv[2] if len(sys.argv) > 2 else "model1_cfd.stl")

reader = vtk.vtkSTLReader()
reader.SetFileName(STL)
normals = vtk.vtkPolyDataNormals()
normals.SetInputConnection(reader.GetOutputPort())
normals.SetFeatureAngle(35)
normals.SplittingOn()


def model_actor():
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(normals.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(0.82, 0.84, 0.88)
    p.SetSpecular(0.35)
    p.SetSpecularPower(30)
    return a


def prop_disk_actor():
    disk = vtk.vtkDiskSource()
    disk.SetInnerRadius(0)
    disk.SetOuterRadius(139.7)
    disk.SetCircumferentialResolution(96)
    t = vtk.vtkTransform()
    t.Translate(45, 0, 0)
    t.RotateY(90)
    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetTransform(t)
    tf.SetInputConnection(disk.GetOutputPort())
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(tf.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(0.95, 0.55, 0.2)
    a.GetProperty().SetOpacity(0.25)
    return a


def edges_actor():
    fe = vtk.vtkFeatureEdges()
    fe.SetInputConnection(reader.GetOutputPort())
    fe.BoundaryEdgesOff()
    fe.ManifoldEdgesOff()
    fe.NonManifoldEdgesOff()
    fe.FeatureEdgesOn()
    fe.SetFeatureAngle(35)
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(fe.GetOutputPort())
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(0.25, 0.28, 0.35)
    a.GetProperty().SetLineWidth(1.2)
    return a


VIEWS = [
    ("Iso", (0.0, 0.5, 0.5, 1.0), (-900, -1100, 650), (0, 0, 1)),
    ("Side (x ->)", (0.5, 0.5, 1.0, 1.0), (450, -3000, 0), (0, 0, 1)),
    ("Top", (0.0, 0.0, 0.5, 0.5), (450, 0, 3000), (0, 1, 0)),
    ("Front", (0.5, 0.0, 1.0, 0.5), (-3000, 0, 0), (0, 0, 1)),
]

win = vtk.vtkRenderWindow()
win.SetOffScreenRendering(1)
win.SetSize(1800, 1300)
win.SetMultiSamples(8)

for title, vp, cam_pos, up in VIEWS:
    ren = vtk.vtkRenderer()
    ren.SetViewport(*vp)
    ren.SetBackground(0.97, 0.97, 0.98)
    ren.SetBackground2(0.86, 0.89, 0.93)
    ren.GradientBackgroundOn()
    ren.AddActor(model_actor())
    ren.AddActor(edges_actor())
    ren.AddActor(prop_disk_actor())
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(450, 0, 0)
    cam.SetPosition(*cam_pos)
    cam.SetViewUp(*up)
    if title != "Iso":
        cam.ParallelProjectionOn()
    ren.ResetCamera()
    cam.Zoom(1.25 if title == "Iso" else 1.15)
    txt = vtk.vtkTextActor()
    txt.SetInput(title)
    txt.GetTextProperty().SetFontSize(26)
    txt.GetTextProperty().SetColor(0.15, 0.18, 0.25)
    txt.GetTextProperty().BoldOn()
    txt.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    txt.GetPositionCoordinate().SetValue(0.02, 0.03)
    ren.AddViewProp(txt)
    win.AddRenderer(ren)

win.Render()
w2i = vtk.vtkWindowToImageFilter()
w2i.SetInput(win)
w2i.Update()
png = vtk.vtkPNGWriter()
png.SetFileName(OUT)
png.SetInputConnection(w2i.GetOutputPort())
png.Write()
print("wrote", OUT)
