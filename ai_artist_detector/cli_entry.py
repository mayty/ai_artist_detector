import click

from ai_artist_detector.cli import command_groups


@click.group()
def cli_root() -> None: ...


for command_group in command_groups:
    cli_root.add_command(command_group)
