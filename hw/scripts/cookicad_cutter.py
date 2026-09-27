#!/usr/bin/env python3

from click import argument, option, group, Path
from sexpdata import loads, Symbol
import ezdxf

@group()
def cli():
    pass

def _require_offscreen_gui():
    """Shared setup for commands that need FreeCAD's Gui for color support (`cut`, `glb`):
    warns if QT_QPA_PLATFORM isn't offscreen, imports the Gui-dependent modules, brings up
    a (normally offscreen) main window, and returns (App, ImportGui)."""
    import os
    import sys

    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        print('WARNING: QT_QPA_PLATFORM is not set to "offscreen" in the environment -- '
              'this must be set in the shell/CI job before launching freecad, not in this '
              'script, or a real window may appear.')

    try:
        import FreeCAD as App
        import FreeCADGui
        import ImportGui
    except ImportError as e:
        raise RuntimeError(f'This subcommand requires the full freecad binary in console mode, '
                            f'e.g "QT_QPA_PLATFORM=offscreen freecad {" ".join(sys.argv)}" ({e})')

    FreeCADGui.getMainWindow()
    return App, ImportGui

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
@argument('output', type=Path())
def glb(step, output):
    """
        Converts a STEP file to GLB (or GLTF), preserving color. Works on both an
        original KiCad STEP export and on files produced by the `cut` command.

        Requires the full `freecad` binary (NOT freecadcmd) run with QT_QPA_PLATFORM=offscreen
        set in the shell/CI environment BEFORE freecad starts -- same requirement as `cut`,
        for the same reason: FreeCAD's glTF exporter, like its colored STEP exporter, is
        registered under ImportGui and isn't available to headless (freecadcmd) Python at all.

        Unlike `cut`, this does no leaf-flattening or per-shape processing -- it just hands
        doc.RootObjects straight to ImportGui.export(). GLB natively supports a real node
        hierarchy with instancing, so preserving the assembly tree as-is (rather than
        flattening to absolute-placed leaves, which `cut` needs for its boolean ops) is both
        simpler and a better fit for the format. This also means it works unmodified on a
        `cut`-produced STEP, which is already just a flat list of root-level Part::Feature
        objects with no further hierarchy to lose.

        Output format is selected purely by the extension of `output` (.glb or .gltf).
    """
    App, ImportGui = _require_offscreen_gui()

    doc = App.newDocument("glb_convert")
    ImportGui.insert(step, doc.Name)
    doc.recompute()

    objs = [obj for obj in doc.RootObjects if hasattr(obj, "Shape") and not obj.Shape.isNull()]
    if not objs:
        raise RuntimeError("No shapes found in imported STEP")
    print(f'{len(objs)} root objects read')

    ImportGui.export(objs, output)
    print(f'Exported to {output}')


@cli.command()
@argument('step', type=Path())
@argument('dxf', type=Path())
@argument('output', type=Path())
def cut(step, dxf, output):
    """
        Cuts a step file using the provided 2d dxf, keeping the boolean intersection between the extruded dxf and the step.

        Requires the full `freecad` binary (NOT freecadcmd) run with QT_QPA_PLATFORM=offscreen
        set in the shell/CI environment BEFORE freecad starts, e.g.:
            QT_QPA_PLATFORM=offscreen freecad alidade_cutter.py --pass cut --pass in.step --pass in.dxf --pass out.step

        Processes each solid in the STEP file individually rather than as one big compound:
          - shapes that don't overlap the cutter at all are dropped without running a boolean
          - shapes that are fully inside the cutter are kept completely unchanged, no boolean
            needed, and (since they're untouched) keep their exact original color
          - only shapes that actually straddle the cut boundary get a boolean run against them,
            and fall back to a single flat color afterwards since per-face color can't survive
            a boolean operation

        Color only round-trips through ImportGui.insert() (read) + ImportGui.export() (write) --
        the plain Import module never writes STEP color regardless of what's set on the document
        objects. ImportGui.insert() builds a full assembly tree of container objects (App::Part/
        groups) wrapping the real leaf shapes, so Group is recursively flattened down to the
        actual shape-bearing leaves. Each leaf's shape is rebuilt with its fully composed global
        placement (obj.getGlobalPlacement()), since a leaf's own .Shape only carries its own
        Placement, not its ancestors' -- without this, anything nested two or more Group levels
        deep (e.g. assembly -> component -> body) ends up in the wrong coordinate frame and
        silently fails the cutter's bounding-box test.
    """
    App, ImportGui = _require_offscreen_gui()
    import Part
    import importDXF

    # Suppress the DXF import options dialog -- confirmed via FreeCAD's own test suite
    # (Mod/Draft/drafttests/test_dxf.py) as the correct way to do this non-interactively.
    draft_params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
    draft_params.SetBool("dxfShowDialog", False)

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

    ImportGui.insert(step, doc.Name)
    doc.recompute()
    root_objs = doc.RootObjects

    def flatten(objs, seen=None):
        """Recursively expand container objects (Group only -- NOT OutList, which mixes in
        dependency references like a Link's LinkedObject template and would make us descend
        into and use the wrong, un-placed copy) down to leaf objects with their own Shape."""
        if seen is None:
            seen = set()
        leaves = []
        for obj in objs:
            if obj.Name in seen:
                continue
            seen.add(obj.Name)
            group = [c for c in (getattr(obj, "Group", None) or []) if c is not None and c.Name not in seen]
            if group:
                leaves.extend(flatten(group, seen))
            elif hasattr(obj, "Shape") and not obj.Shape.isNull():
                leaves.append(obj)
        return leaves

    source_objs = [
        obj for obj in flatten(root_objs)
        if obj.Name != extrude_obj.Name
    ]
    print(f'{len(source_objs)} leaf shapes after flattening (from {len(root_objs)} root objects, '
          f'{len(doc.Objects)} total document objects)')
    if not source_objs:
        raise RuntimeError("No shapes found in imported STEP")

    kept = []
    pending_color_copy = []  # (result_obj, source_obj, fully_contained) -- color applied after recompute
    n_discarded = n_unchanged = n_cut = 0

    for obj in source_objs:
        # obj.Shape only carries the object's OWN Placement, not its ancestors' -- for a
        # leaf nested two or more Group levels deep, that leaves it in the wrong coordinate
        # frame entirely. Rebuild it with the fully composed global placement instead.
        shape = obj.Shape.copy()
        try:
            shape.Placement = obj.getGlobalPlacement()
        except Exception as e:
            print(f'Could not get global placement for {obj.Name}, using local Shape as-is: {e}')
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

        pending_color_copy.append((result_obj, obj, fully_contained))
        kept.append(result_obj)

    print(f'{n_unchanged} unchanged, {n_cut} cut, {n_discarded} discarded (of {len(source_objs)} source shapes)')

    if not kept:
        raise RuntimeError("Nothing left after cutting")

    # Newly created objects don't get a fully-attached ViewProvider (with ShapeColor etc.)
    # until after a recompute -- accessing .ViewObject.ShapeColor right after addObject()
    # can fail. Recompute once, then copy colors in a second pass.
    doc.recompute()

    color_failures = 0
    for result_obj, obj, fully_contained in pending_color_copy:
        try:
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                result_obj.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
                result_obj.ViewObject.Transparency = obj.ViewObject.Transparency
                if fully_contained:
                    # Per-face colors only still line up when the face set is untouched.
                    result_obj.ViewObject.DiffuseColor = obj.ViewObject.DiffuseColor
        except Exception as e:
            color_failures += 1
            if color_failures <= 3:
                print(f'Could not copy color for {result_obj.Name}: {e}')
    print(f'Color copied for {len(pending_color_copy) - color_failures}/{len(pending_color_copy)} objects')

    doc.recompute()
    ImportGui.export(kept, output)
    print(f'Exported to {output}')


import sys
if __name__ == "__main__":
    cli()
elif sys.argv[0].lower() in ("freecadcmd", "freecad"):
    # Under the full `freecad` GUI binary, sys.argv[0] is "freecad" (not "freecadcmd"), so a
    # plain `== "freecadcmd"` check never matches there and cli() would silently never run.
    #
    # FreeCAD's Gui-substituted stdout/stderr proxy has been observed to crash Click's own
    # TTY-detection code, so the real system streams are restored before handing off to Click.
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    sys.argv = sys.argv[1:]
    sys.argv = [arg for arg in sys.argv if arg != "--pass"]

    exit_code = 0
    try:
        cli()
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException:
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        # Click ends a run by raising SystemExit, which freecadcmd's host respects and exits
        # on. The full `freecad` GUI binary does not -- it keeps running its own event loop
        # regardless -- so force a hard process exit here instead of relying on that exception
        # to actually stop anything.
        import os
        os._exit(exit_code)
