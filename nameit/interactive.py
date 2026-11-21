"""Ask the user which suggested name to use (interactive mode)."""
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from rich.console import Console
from rich.table import Table

from nameit.consensus import Candidate, Decision

SKIP, QUIT, ALL = "s", "q", "a"


class Chooser:
    """Callable used by api.plan_rename: shows the suggestions for one PDF and returns the user's pick.

    Returns the chosen Candidate, or None to skip the file. Answering `a` accepts the suggestion
    for this and every remaining file (majority vote, no more questions); `q` skips this and the rest.
    """

    def __init__(self, console: Console, render: Callable[[Candidate], str],
                 ask: Optional[Callable[[str], str]] = None):
        self.console = console
        self.render = render
        self.ask = ask or (lambda prompt: console.input(prompt))
        self.automatic = False
        self.quit = False

    def __call__(self, pdf: Path, candidates: Sequence[Candidate], decision: Decision) -> Optional[Candidate]:
        suggested = next(c for c in candidates if c.method == decision.method)
        if self.quit:
            return None
        if self.automatic:
            return suggested
        table = Table(title=f"{pdf.name}  [dim]({decision.label})[/dim]", show_lines=False,
                      header_style="bold magenta", title_justify="left")
        table.add_column("#", justify="right")
        table.add_column("Method", style="cyan")
        table.add_column("Suggested name", overflow="fold")
        for number, candidate in enumerate(candidates, 1):
            agrees = candidate.method in decision.agreeing and decision.consensus
            mark = "[green]✓[/green] " if agrees else ""
            star = " [bold](suggested)[/bold]" if candidate is suggested else ""
            table.add_row(str(number), candidate.method, f"{mark}{self.render(candidate)}{star}")
        self.console.print(table)
        default = candidates.index(suggested) + 1
        prompt = (f"Choose 1-{len(candidates)} [Enter = {default}], s = skip, "
                  f"a = accept suggestions for all remaining, q = quit: ")
        while True:
            answer = self.ask(prompt).strip().lower()
            if answer == "":
                return suggested
            if answer == SKIP:
                return None
            if answer == ALL:
                self.automatic = True
                return suggested
            if answer == QUIT:
                self.quit = True
                return None
            if answer.isdigit() and 1 <= int(answer) <= len(candidates):
                return candidates[int(answer) - 1]
            self.console.print("[yellow]Please answer with a number, Enter, s, a or q.[/yellow]")
