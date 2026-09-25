import json, os, sys
from click import command, argument, Path, group, option

@group()
def cli():
    pass

@cli.command()
@argument('erc', type=Path())
@argument('summary', type=Path(), required=False)
@option('--no-fatal-errors', type=bool, is_flag=True, help='Always return success')
def erc(erc, summary, no_fatal_errors):
    """
        Parse KiCad erc.json results into github action commands and optionally a markdown summary

        ERC - Path to a KiCad erc.json

        SUMMARY - File to output a markdown summary (Usually should be $GITHUB_STEP_SUMMARY)
    """
    err_count = 0
    warn_count = 0
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
                severity = violation['severity']
                if severity == 'error':
                    err_count += 1
                elif severity == 'warning':
                    warn_count += 1
                for item in violation['items']:
                    details.append(f'''{item['description']} @ ({item['pos']['x']},{item['pos']['y']})''')

                details = ", ".join(details)
                print(f'::{severity} title={description}::{sheet_name} - {details}')
                items.append((severity, sheet_name, description, details))
    if summary:
        with open(summary, 'a') as f:
            if err_count > 0:
                status = 'errors found'
            elif warn_count > 0:
                status = 'warnings only'
            else:
                status = 'clean'

            f.write(f'## ERC Results - {status}\n\n')
            f.write(f'{err_count} error(s), {warn_count} warning(s)\n\n')
            if items:
                f.write('| Severity | Sheet | Description | Details |\n')
                f.write('|----------|-------|-------------|---------|\n')
                for i in items:
                    f.write(f'''|{'|'.join(i)}|\n''')
            else:
                f.write('No issues found.\n')
    sys.exit(1 if err_count > 0 and not no_fatal_errors else 0)

@cli.command()
@argument('drc', type=Path())
@argument('summary', type=Path(), required=False)
@option('--no-fatal-errors', type=bool, is_flag=True, help='Always return success')
def drc(drc, summary, no_fatal_errors):
    """
        Parse KiCad erc.json results into github action commands and optionally a markdown summary

        DRC - Path to a KiCad drc.json

        SUMMARY - File to output a markdown summary (Usually should be $GITHUB_STEP_SUMMARY)
    """
    err_count = 0
    warn_count = 0
    items = []
    with open(drc, 'r') as f:
        drc = json.load(f)
        if drc['$schema'] != 'https://schemas.kicad.org/drc.v1.json':
            raise RuntimeError("Incorrect DRC schema")
        for violation in drc['schematic_parity'] + drc['unconnected_items'] + drc['violations']:
            details = []
            description = violation['description']
            severity = violation['severity']
            if severity == 'error':
                err_count += 1
            elif severity == 'warning':
                warn_count += 1
            for item in violation['items']:
                details.append(f'''{item['description']} @ ({item['pos']['x']},{item['pos']['y']})''')

            details = ", ".join(details)
            print(f'::{severity} title={description}::{details}')
            items.append((severity, description, details))

    if summary:
        with open(summary, 'a') as f:
            if err_count > 0:
                status = 'errors found'
            elif warn_count > 0:
                status = 'warnings only'
            else:
                status = 'clean'

            f.write(f'## DRC Results - {status}\n\n')
            f.write(f'{err_count} error(s), {warn_count} warning(s)\n\n')
            if items:
                f.write('| Severity | Description | Details |\n')
                f.write('|----------|-------------|---------|\n')
                for i in items:
                    f.write(f'''|{'|'.join(i)}|\n''')
            else:
                f.write('No issues found.\n')
    sys.exit(1 if err_count > 0 and not no_fatal_errors else 0)
    pass

if __name__ == "__main__":
    cli()
