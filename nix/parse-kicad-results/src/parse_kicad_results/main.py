import json, os, sys
from click import command, argument, Path, group, option

@group()
def cli():
    pass


def _severity_label(severity, counters):
    """Map raw KiCad severity strings to display labels and bump the right counter."""
    if severity == 'error':
        counters['errors'] += 1
        return 'Error'
    elif severity == 'warning':
        counters['warnings'] += 1
        return 'Warning'
    else:
        return 'Unknown'


def _status_from_counts(err_count, warn_count):
    if err_count > 0:
        return 'errors found'
    elif warn_count > 0:
        return 'warnings only'
    else:
        return 'clean'


def _print_table(headers, rows):
    print('| ' + ' | '.join(headers) + ' |')
    print('|' + '|'.join(['---'] * len(headers)) + '|')
    for row in rows:
        print('|' + '|'.join(str(c) for c in row) + '|')


@cli.command()
@argument('erc', type=Path())
@option('--no-fatal-errors', type=bool, is_flag=True, help='Always return success')
def erc(erc, no_fatal_errors):
    """
        Parse KiCad erc.json results into a markdown summary on stdout

        ERC - Path to a KiCad erc.json
    """
    counters = {'errors': 0, 'warnings': 0}
    items = []
    with open(erc, 'r') as f:
        erc = json.load(f)
        if erc['$schema'] != 'https://schemas.kicad.org/erc.v1.json':
            raise RuntimeError("Incorrect ERC schema")
        for sheet in erc['sheets']:
            sheet_name = sheet['path']
            for violation in sheet['violations']:
                details = []
                description = violation['description']
                severity = _severity_label(violation['severity'], counters)

                for item in violation['items']:
                    details.append(f'''{item['description']} @ ({item['pos']['x']},{item['pos']['y']})''')

                details = ", ".join(details)
                items.append((severity, sheet_name, description, details))

    err_count, warn_count = counters['errors'], counters['warnings']
    status = _status_from_counts(err_count, warn_count)

    print(f'## ERC Results - {status}\n')
    print(f'{err_count} error(s), {warn_count} warning(s)\n')
    if items:
        _print_table(['Severity', 'Sheet', 'Description', 'Details'], items)
    else:
        print('No issues found.')
    sys.exit(1 if err_count > 0 and not no_fatal_errors else 0)


@cli.command()
@argument('drc', type=Path())
@option('--no-fatal-errors', type=bool, is_flag=True, help='Always return success')
def drc(drc, no_fatal_errors):
    """
        Parse KiCad drc.json results into a markdown summary on stdout

        DRC - Path to a KiCad drc.json
    """
    counters = {'errors': 0, 'warnings': 0}
    items = []
    with open(drc, 'r') as f:
        drc = json.load(f)
        if drc['$schema'] != 'https://schemas.kicad.org/drc.v1.json':
            raise RuntimeError("Incorrect DRC schema")
        for violation in drc['schematic_parity'] + drc['unconnected_items'] + drc['violations']:
            details = []
            description = violation['description']
            severity = _severity_label(violation['severity'], counters)

            for item in violation['items']:
                details.append(f'''{item['description']} @ ({item['pos']['x']},{item['pos']['y']})''')

            details = ", ".join(details)
            items.append((severity, description, details))

    err_count, warn_count = counters['errors'], counters['warnings']
    status = _status_from_counts(err_count, warn_count)

    print(f'## DRC Results - {status}\n')
    print(f'{err_count} error(s), {warn_count} warning(s)\n')
    if items:
        _print_table(['Severity', 'Description', 'Details'], items)
    else:
        print('No issues found.')
    sys.exit(1 if err_count > 0 and not no_fatal_errors else 0)


@cli.command()
@argument('stats', type=Path())
def stats(stats):
    """
        Parse KiCad board stats report json into a markdown summary on stdout

        STATS - Path to a KiCad board stats report json
    """
    with open(stats, 'r') as f:
        data = json.load(f)

    meta = data.get('metadata', {})
    board = data.get('board', {})
    pads = data.get('pads', {})
    vias = data.get('vias', {})
    components = data.get('components', {})
    drill_holes = data.get('drill_holes', [])

    print(f'''## Board Stats - {meta.get('project', 'unknown')}\n''')
    print(f'''Board: **{meta.get('board_name', 'unknown')}**\nGenerator: {meta.get('generator', 'unknown')}\n''')

    print('### Board\n')
    board_rows = [
        ('Outline present', board.get('has_outline')),
        ('Dimensions', f"{board.get('width', '?')} x {board.get('height', '?')}"),
        ('Thickness', board.get('board_thickness', '?')),
        ('Min track width', board.get('min_track_width', '?')),
        ('Min track clearance', board.get('min_track_clearance', '?')),
        ('Min drill diameter', board.get('min_drill_diameter', '?')),
        ('Front component density', board.get('front_component_density', '?')),
        ('Back component density', board.get('back_component_density', '?')),
    ]
    _print_table(['Metric', 'Value'], board_rows)

    print('\n### Components\n')
    comp_rows = []
    for kind in ('tht', 'smd', 'unspecified', 'total'):
        c = components.get(kind, {})
        label = 'Total' if kind == 'total' else kind.upper()
        comp_rows.append((label, c.get('front', 0), c.get('back', 0), c.get('total', 0)))
    _print_table(['Type', 'Front', 'Back', 'Total'], comp_rows)

    print('\n### Pads & Vias\n')
    pad_via_rows = [
        ('Through-hole pads', pads.get('through_hole', 0)),
        ('SMD pads', pads.get('smd', 0)),
        ('Connector pads', pads.get('connector', 0)),
        ('NPTH pads', pads.get('npth', 0)),
        ('Castellated pads', pads.get('castellated', 0)),
        ('Press-fit pads', pads.get('press_fit', 0)),
        ('Through vias', vias.get('through', 0)),
        ('Blind vias', vias.get('blind', 0)),
        ('Buried vias', vias.get('buried', 0)),
        ('Micro vias', vias.get('micro', 0)),
    ]
    _print_table(['Metric', 'Count'], pad_via_rows)

    print('\n### Drill Holes\n')
    if drill_holes:
        drill_rows = []
        total_holes = 0
        for hole in sorted(drill_holes, key=lambda h: h.get('count', 0), reverse=True):
            count = hole.get('count', 0)
            total_holes += count
            size = f"{hole.get('x_size', '?')} x {hole.get('y_size', '?')}" if hole.get('shape') != 'Round' or hole.get('x_size') != hole.get('y_size') else hole.get('x_size', '?')
            drill_rows.append((
                count,
                hole.get('shape', '?'),
                size,
                'Yes' if hole.get('plated') else 'No',
                hole.get('source', '?'),
                f"{hole.get('start_layer', '?')} - {hole.get('stop_layer', '?')}",
            ))
        _print_table(['Count', 'Shape', 'Size', 'Plated', 'Source', 'Layers'], drill_rows)
        print(f'\n**Total drill holes:** {total_holes}')
    else:
        print('No drill hole data found.')

    sys.exit(0)


if __name__ == "__main__":
    cli()
