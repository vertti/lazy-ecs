import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """A CLI tool for working with AWS services."""
    pass


@main.command()
def version() -> None:
    """Show version information."""
    console.print("lazy-ecs 0.1.0", style="bold green")


@main.group()
def ecs() -> None:
    """Commands for Amazon ECS."""
    pass


@ecs.command()
def list_clusters() -> None:
    """List ECS clusters."""
    console.print("Listing ECS clusters...", style="blue")
    # TODO: Implement actual AWS ECS listing


if __name__ == "__main__":
    main()
