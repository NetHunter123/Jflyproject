"""Separate GN+ solids for Onshape.

GN+.step fuses the airframe into one body. Onshape can then only push faces
around. This file keeps each piece as its own part so a later channel, pin or
plug can be edited without cutting the whole airplane.

The flat blade is the old placeholder, not the APC propeller. It is its own
part so it can be deleted in Onshape.

Units are millimetres, same as the rest of CAD/.
Run:  python export_onshape.py
"""
import os

import cadquery as cq

import gn_detail as g
import nose_tail as nt

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    cowl, spinner, _ = nt.nose()
    parts = [
        ("cowl", cowl),
        ("tube", g.tube()),
        ("joiner_collar", g.collar()),
        ("joiner", g.joiner_rod()),
        ("wing_right", g.model1.wing_panel_right()),
        ("wing_left", g.model1.mirror_y(g.model1.wing_panel_right())),
        ("tail", nt.tail()),
        ("spinner", spinner),
        ("blade_placeholder", cq.Solid.makeBox(
            3.2, 279.4, 22.0, cq.Vector(nt.SPINNER_REAR + 0.6, -139.7, -11.0)
        )),
    ]
    assy = cq.Assembly(name="GN+")
    for name, solid in parts:
        if not solid.isValid():
            raise SystemExit(name + " is not a valid solid")
        assy.add(solid, name=name)
        print(name, "faces", len(solid.Faces()))
    path = os.path.join(HERE, "GN+_onshape.step")
    assy.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
