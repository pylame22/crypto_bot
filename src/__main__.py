import click

from src.commands import LoadDataCommand
from src.core.settings import get_settings


@click.group()
def cli() -> None:
    pass


@cli.command()
def load_data() -> None:
    settings = get_settings()
    command = LoadDataCommand(settings)
    command.execute()


if __name__ == "__main__":
    cli()
