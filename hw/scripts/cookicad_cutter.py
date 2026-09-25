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
        Cuts a step file using the provided 2d dxf, keeping the boolean intersection between the extruded dxf and the step.
        Requires being run under freecadcmd.
    """
    try:
        import FreeCAD as App
        import Part
        import Import
        import importDXF
    except ImportError:
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
    compound.translate(App.Vector(0, 0, -50))
    wires = compound.Wires

    if not wires:
        raise RuntimeError(f'No closed wires found in {dxf}')

    face = Part.Face(wires[0])
    extruded = face.extrude(
        extrude_direction.normalize().multiply(extrude_distance)
    )
    cutter_bbox = extruded.BoundBox

    extrude_obj = doc.addObject("Part::Feature", "Extrusion")
    extrude_obj.Shape = extruded

    Import.insert(step, doc.Name)
    doc.recompute()

    source_objs = [
        obj for obj in doc.Objects
        if hasattr(obj, "Shape")
        and not obj.Shape.isNull()
        and obj.Name != extrude_obj.Name
    ]
    if not source_objs:
        raise RuntimeError("No shapes found in imported STEP")

    kept = []
    n_discarded = n_unchanged = n_cut = 0

    for obj in source_objs:
        shape = obj.Shape
        bb = shape.BoundBox

        if not bb.intersect(cutter_bbox):
            # Can't possibly overlap the cutter -- drop it, no boolean needed.
            n_discarded += 1
            continue

        # Cheap pre-check: is this shape's bounding box entirely within the cutter's
        # bounding box? If so it's a *candidate* for being fully contained.
        bbox_fully_inside = (
            bb.XMin >= cutter_bbox.XMin and bb.XMax <= cutter_bbox.XMax and
            bb.YMin >= cutter_bbox.YMin and bb.YMax <= cutter_bbox.YMax and
            bb.ZMin >= cutter_bbox.ZMin and bb.ZMax <= cutter_bbox.ZMax
        )

        fully_contained = False
        if bbox_fully_inside:
            # Confirm with a cheap point-in-solid test on each vertex instead of a
            # full boolean -- this is what actually saves the time, since it's a
            # handful of point tests instead of a geometric intersection.
            fully_contained = all(
                extruded.isInside(v.Point, 1e-6, True)
                for v in shape.Vertexes
            )

        if fully_contained:
            # No boolean needed at all -- keep the original shape as-is.
            result_obj = doc.addObject("Part::Feature", f"{obj.Name}_kept")
            result_obj.Shape = shape
            n_unchanged += 1
        else:
            # Genuinely straddles the cut boundary (or bbox check was inconclusive,
            # e.g. a non-convex cutter outline) -- this is the only case that pays
            # for an actual boolean.
            result = shape.common(extruded)
            if result.isNull() or result.Volume < 1e-9:
                n_discarded += 1
                continue
            result_obj = doc.addObject("Part::Feature", f"{obj.Name}_cut")
            result_obj.Shape = result.removeSplitter()
            n_cut += 1

        kept.append(result_obj)


    if not kept:
        raise RuntimeError("Nothing left after cutting")

    doc.recompute()
    Import.export(kept, output)
    print(f'{n_unchanged} unchanged, {n_cut} cut, {n_discarded} discarded (of {len(source_objs)} source shapes)')


import sys
if __name__ == "__main__":
    cli()
elif sys.argv[0].lower() == "freecadcmd":
    sys.argv = sys.argv[1:]
    sys.argv = [arg for arg in sys.argv if arg != "--pass"]
    cli()
