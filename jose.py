import os
from pathlib import Path
from typing import Dict, List, Union, Optional
from rich import print
from rich.panel import Panel
from rich.table import Table
from rich.console import Console

PathLike = Union[str, os.PathLike, Path]  # All supported path types


def process_folder_or_file_dry_run(
        nameit_path: PathLike,
        cli_args: argparse.Namespace,
) -> Dict[Path, Path]:
    """
    Simulates processing by recursively listing all files and directories found at the specified path,
    counting PDF files, and displaying a summary of rename operations that would occur.

    Args:
        nameit_path: The path to a file or directory (accepts str, os.PathLike, or Path)
        cli_args: Parsed command-line arguments with these attributes:
            - recursive (bool): Whether to traverse directories recursively
            - verbose (bool): Show detailed output
            - debug (bool): Show debug information
        output_console: Optional Rich Console instance for output

    Returns:
        Dictionary mapping original paths to their proposed new paths
    """
    # Convert input to Path object regardless of input type
    path = Path(nameit_path) if not isinstance(nameit_path, Path) else nameit_path
    console = output_console or Console()

    pdf_count = 0
    dir_count = 0
    rename_operations: Dict[Path, Path] = {}

    # Initialize summary table
    summary_table = Table(title="Dry Run Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    if cli_args.debug:
        console.print(f"[yellow]DEBUG: Starting dry run for path: {path}[/yellow]")

    if not path.exists():
        console.print(f"[red]Error: Path does not exist - {path}[/red]")
        return {}

    def process_item(item: Path, depth: int = 0) -> None:
        nonlocal pdf_count, dir_count
        indent = "  " * depth

        if item.is_dir():
            dir_count += 1
            if cli_args.verbose:
                console.print(f"{indent}[blue]DIR: {item.name}[/blue]")

            if cli_args.recursive:
                try:
                    for child in sorted(item.iterdir()):
                        process_item(child, depth + 1)
                except PermissionError:
                    if cli_args.debug:
                        console.print(f"{indent}[red]Permission denied: {item}[/red]")

        elif item.is_file():
            if item.suffix.lower() == '.pdf':
                pdf_count += 1
                new_name = generate_new_name(item)
                rename_operations[item] = new_name

                if cli_args.verbose:
                    console.print(f"{indent}[green]PDF: {item.name}[/green] → [yellow]{new_name.name}[/yellow]")
            elif cli_args.debug:
                console.print(f"{indent}[dim]FILE: {item.name}[/dim]")

    # Process the initial path
    if path.is_file():
        if path.suffix.lower() == '.pdf':
            pdf_count += 1
            new_name = generate_new_name(path)
            rename_operations[path] = new_name
            console.print(f"[green]PDF: {path.name}[/green] → [yellow]{new_name.name}[/yellow]")
    else:
        try:
            for item in sorted(path.iterdir()):
                process_item(item)
        except PermissionError:
            console.print(f"[red]Permission denied accessing directory: {path}[/red]")

    # Generate summary
    summary_table.add_row("Total Directories", str(dir_count))
    summary_table.add_row("Total PDF Files", str(pdf_count))
    summary_table.add_row("PDFs to be Renamed", str(len(rename_operations)))

    console.print(Panel(summary_table, title="[bold]Dry Run Results[/bold]"))

    if cli_args.debug and rename_operations:
        console.print("\n[bold yellow]DEBUG: Full rename operations list:[/bold yellow]")
        for old, new in rename_operations.items():
            console.print(f"  {old} → {new}")

    return rename_operations


def generate_new_name(filepath: Path) -> Path:
    """
    Example renaming function - replace with your actual logic
    """
    # Example: Add prefix and clean filename
    new_name = f"doc_{filepath.stem.lower().replace(' ', '_')}{filepath.suffix}"
    return filepath.parent / new_name