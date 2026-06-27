"""Rich terminal rendering for agent-loopa CLI."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from agent_loopa.models.messages import AgentOutput
from agent_loopa.models.verdicts import VerdictStatus

console = Console()

_STATUS_ICON = {
    VerdictStatus.PASS: "[green]✓[/green]",
    VerdictStatus.FAIL: "[red]✗[/red]",
    VerdictStatus.WARNING: "[yellow]⚠[/yellow]",
}


def _verdict_icon(output: AgentOutput) -> str:
    verdict = output.get_verdict()
    if verdict is None:
        # Coder agent — no verdict, just produced code
        return "[green]✓[/green]" if output.code else "[yellow]?[/yellow]"
    return _STATUS_ICON.get(verdict.status, "[white]?[/white]")


def _verdict_summary(output: AgentOutput) -> str:
    if output.code:
        lc = output.code.line_count
        return f"{output.code.filename} written ({lc} lines)"
    verdict = output.get_verdict()
    if verdict:
        return verdict.summary or verdict.status.value
    return "completed"


def render_iteration_panel(
    iteration: int,
    max_iterations: int,
    outputs: list[AgentOutput],
    gate_reason: str = "",
) -> Panel:
    """Build a Rich Panel for a completed iteration."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", min_width=22)
    table.add_column()
    table.add_column()

    for out in outputs:
        icon = _verdict_icon(out)
        summary = _verdict_summary(out)
        table.add_row(f"[{out.agent_name.replace('_', ' ').title()} Agent]", icon, summary)

    if gate_reason:
        table.add_row("", "", Text(gate_reason, style="dim"))

    title = f"agent-loopa ── iteration {iteration}/{max_iterations}"
    return Panel(table, title=title, border_style="blue")


def render_parallel_panel(outputs: list[AgentOutput]) -> Panel:
    """Build a Rich Panel for the parallel phase."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", min_width=22)
    table.add_column()
    table.add_column()

    for out in outputs:
        icon = _verdict_icon(out)
        summary = _verdict_summary(out)
        table.add_row(f"[{out.agent_name.replace('_', ' ').title()} Agent]", icon, summary)

    return Panel(table, title="parallel phase", border_style="green")


def render_summary(result: object, output_dir: str) -> None:
    """Print final summary after the run."""
    from agent_loopa.orchestrator.orchestrator import OrchestratorResult
    r: OrchestratorResult = result  # type: ignore[assignment]

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()

    if r.final_code:
        table.add_row("code:", r.final_code.filename)
    if r.test_suite and r.test_suite.test_files:
        table.add_row("tests:", r.test_suite.test_files[0].filename)
    if r.documentation:
        table.add_row("docs:", "docs.md" if r.documentation.readme_section else "inline only")
    if r.audit_log_path:
        table.add_row("audit:", str(r.audit_log_path))
    table.add_row("tokens:", str(r.total_tokens))
    table.add_row("iterations:", str(r.iterations_run))

    console.print(Panel(table, title=f"[green]Output saved to: {output_dir}[/green]", border_style="green"))


@contextmanager
def agent_spinner(agent_name: str) -> Iterator[None]:
    """Display a spinner while an agent is running."""
    label = agent_name.replace("_", " ").title() + " Agent"
    with console.status(f"[cyan]{label}[/cyan] thinking…", spinner="dots"):
        yield
