"""Main entry point for ptop application."""

import click
from pathlib import Path
from typing import Optional

from .app import PtopApp
from .config.settings import PtopSettings


@click.command()
@click.option(
    "--config", 
    "-c", 
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file"
)
@click.option(
    "--interval",
    "-i",
    type=float,
    default=1.0,
    help="Update interval in seconds (default: 1.0)"
)
@click.version_option(version="0.1.0", prog_name="ptop")
def main(config: Optional[Path], interval: float) -> None:
    """ptop - Modern Python-based system monitoring tool for Linux.
    
    A terminal-based system monitor that displays real-time information about
    CPU, memory, storage, processes, and system logs.
    """
    # Load configuration
    if config:
        settings = PtopSettings.load_from_file(config)
    else:
        settings = PtopSettings.load_from_file()
    
    # Override update intervals if specified
    if interval != 1.0:
        settings.cpu_update_interval = interval
        settings.memory_update_interval = interval
    
    # Create and run the application
    app = PtopApp()
    app.settings = settings
    app.run()


if __name__ == "__main__":
    main()