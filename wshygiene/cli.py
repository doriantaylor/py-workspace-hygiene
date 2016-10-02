# -*- coding: utf-8 -*-

from wshygiene import StorageProxy, Scanner
import click, os

@click.command()
@click.option('-s', '--state', default=os.path.expanduser('~/.wshygiene'),
              type=click.Path(exists=False, file_okay=False, dir_okay=True,
                              resolve_path=True))
@click.argument('root', nargs=-1, type=click.Path(
    file_okay=False, dir_okay=True, resolve_path=True))
def main(state, root):
    """workspace-hygiene"""
    click.echo(state)
    click.echo(root)

    # set up storage
    storage = StorageProxy(state)
    # set up scanner
    scanner = Scanner(storage)
    scanner.scan(root, ignore=state)

if __name__ == "__main__":
    main()
