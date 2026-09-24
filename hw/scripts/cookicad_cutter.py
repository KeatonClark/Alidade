#!/usr/bin/env python3

from click import command, argument, option, group, Path
from sexpdata import loads, Symbol
import ezdxf

@group()
def cli():
    pass

@cli.command()
@argument('pcb', type=Path()) 
@argument('output', type=Path())
@option('--layer', '-l', type=str, default='Eco1.User', help='Layer to use for the cookie cutter e.g "Eco1.User"')
def gen(pcb, layer, output):
    """
        Builds a 2d dxf "cookie cutter" from a gr_poly from a specific layer within a KiCad pcb.
        This can be used to "cut" away any unused supporting material from a 3d pcb model.
    """
    with open(pcb, 'r') as pcb:
        pcb = loads(pcb.read())
        if pcb[0] != Symbol('kicad_pcb'):
            raise RuntimeError(f'"{pcb}" is not a kicad_pcb file')

        setup = [field for field in pcb if field[0] == Symbol('setup')][0]
        grid_origin = tuple(([field for field in setup if field[0] == Symbol('grid_origin')][0])[1:3])
        print(f'Grid Origin: {grid_origin}')

        polys = [field for field in pcb if field[0] == Symbol('gr_poly') and [Symbol('layer'), layer] in field]
        if len(polys) != 1:
            raise RuntimeError(f'Only one poly per layer is supported by this tool, found {len(polys)}')
        poly = polys[0]
        pts = [field for field in poly if field[0] == Symbol('pts') ][0]
        points = []
        for xy in pts[1:]:
            if xy[0] != Symbol('xy'):
                raise RuntimeError(f'Malformed gr_poly.pts object: {xy}')
            # offset by grid origin and flip y axis
            points.append(tuple(
                (xy[1] - grid_origin[0], (xy[2] - grid_origin[1]) * -1)
            ))
        print(f'Number of points {len(points)}')

        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_lwpolyline(points, close=True)
        doc.saveas(output)


@cli.command()
@argument('step', type=Path())
@argument('dxf', type=Path())
@argument('output', type=Path())
def cut(step, dxf, output):
    """
        Cuts a step file using the provided 2d dxf, keeping the boolean intersection between the extruded dxf and the step
        Requires being run under freecadcmd
    """

    try:
        import FreeCAD as App
        import Part
        import Import
        import importDXF
    except:
        raise RuntimeError(f'The cut subcommand must be run under freecadcmd, e.g "freecadcmd {" ".join(sys.argv)}"')

    extrude_distance = 100.0
    extrude_direction = App.Vector(0, 0, 1)
    
    importDXF.open(dxf)
    doc = App.ActiveDocument
    dxf_shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape") and not obj.Shape.isNull()]

    if not dxf_shapes:
        raise RuntimeError(f'No valid geometry found in {dxf}')

    compound = Part.makeCompound(dxf_shapes)
    compound.scale(0.001)
    compound.translate(App.Vector(0,0,-50))
    wires = compound.Wires

    if not wires:
        raise RuntimeError(f'No closed wires found in {dxf}')

    face = Part.Face(wires[0])
    extruded = face.extrude(
            extrude_direction.normalize().multiply(extrude_distance)
    )
    extrude_obj = doc.addObject("Part::Feature", "Extrusion")
    extrude_obj.Shape = extruded
    
    Import.insert(step, doc.Name)

    doc.recompute()

    step_shapes = [
        obj.Shape
        for obj in doc.Objects
        if hasattr(obj, "Shape")
        and not obj.Shape.isNull()
        and obj.Name != extrude_obj.Name
    ]
    if not step_shapes:
        raise RuntimeError("No shapes found in imported STEP")

    step_shape = Part.makeCompound(step_shapes)
    result_shape = step_shape.common(extruded)
    result_obj = doc.addObject("Part::Feature", "Result")
    result_obj.Shape = result_shape

    doc.recompute()

    Import.export([result_obj], output)

import sys
if __name__ == "__main__":
    cli()
elif sys.argv[0].lower() == "freecadcmd":
    sys.argv = sys.argv[1:]
    sys.argv = [arg for arg in sys.argv if arg != "--pass"]
    cli()
