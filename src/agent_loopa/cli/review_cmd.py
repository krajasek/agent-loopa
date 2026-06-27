"""loopa review — improve existing code files."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, List, Optional

import typer

from agent_loopa.cli.display import (
    console,
    render_iteration_panel,
    render_parallel_panel,
    render_summary,
)
from agent_loopa.config.loader import default_config, load_config
from agent_loopa.models.artifacts import CodeArtifact
from agent_loopa.models.messages import AgentOutput
from agent_loopa.orchestrator.orchestrator import Orchestrator, RunMode
from agent_loopa.orchestrator.pipeline import PARALLEL_STAGES


def review_command(
    files: Annotated[List[Path], typer.Option("--files", "-f", help="Files or directories to review")],
    lang: Annotated[str, typer.Option("--lang", "-l", help="Target language")] = "python",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("./output"),
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c", help="TOML config file")] = None,
    skip_agents: Annotated[Optional[str], typer.Option("--skip-agents", help="Comma-separated agent names to disable")] = None,
    max_iterations: Annotated[int, typer.Option("--max-iterations", "-n")] = 3,
) -> None:
    """Review and improve existing code files."""
    asyncio.run(_run(files, lang, output, config_path, skip_agents, max_iterations))


async def _run(
    files: list[Path],
    lang: str,
    output: Path,
    config_path: Path | None,
    skip_agents_str: str | None,
    max_iterations: int,
) -> None:
    # Load config
    if config_path:
        cfg = load_config(config_path)
    else:
        cfg = default_config()
    cfg = cfg.model_copy(update={"output_dir": str(output), "gate": cfg.gate.model_copy(update={"max_iterations": max_iterations})})

    # Parse skip_agents
    skip: set[str] = set()
    if skip_agents_str:
        skip = {s.strip() for s in skip_agents_str.split(",") if s.strip()}

    # Load source files
    existing_files: list[CodeArtifact] = []
    for path in files:
        path = Path(path)
        if path.is_dir():
            for fp in path.rglob(f"*.{lang}"):
                content = fp.read_text(encoding="utf-8", errors="replace")
                existing_files.append(CodeArtifact(language=lang, filename=fp.name, content=content))
        elif path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            existing_files.append(CodeArtifact(language=lang, filename=path.name, content=content))
        else:
            console.print(f"[yellow]Warning: file not found: {path}[/yellow]")

    if not existing_files:
        console.print("[red]No valid files found to review.[/red]")
        raise typer.Exit(1)

    orchestrator = Orchestrator(config=cfg)

    iteration_outputs: list[AgentOutput] = []
    parallel_outputs: list[AgentOutput] = []
    current_iteration = 0
    parallel_agent_names = {s.value for s in PARALLEL_STAGES}

    async def on_output(out: AgentOutput) -> None:
        nonlocal current_iteration
        if out.agent_name in parallel_agent_names:
            parallel_outputs.append(out)
        else:
            if out.iteration != current_iteration:
                if iteration_outputs:
                    console.print(render_iteration_panel(current_iteration, max_iterations, iteration_outputs, ""))
                iteration_outputs.clear()
                current_iteration = out.iteration
            iteration_outputs.append(out)

    file_names = ", ".join(f.filename for f in existing_files[:3])
    console.rule("[bold blue]agent-loopa[/bold blue] — review mode")
    console.print(f"Files: [cyan]{file_names}[/cyan]  |  Language: [cyan]{lang}[/cyan]\n")

    task_desc = f"Review and improve the provided {lang} code."
    result = await orchestrator.run(
        mode=RunMode.REVIEW,
        task_description=task_desc,
        language=lang,
        existing_files=existing_files,
        skip_agents=skip,
        on_agent_output=on_output,
    )

    if iteration_outputs:
        console.print(render_iteration_panel(current_iteration, max_iterations, iteration_outputs, ""))
    if parallel_outputs:
        console.print(render_parallel_panel(parallel_outputs))

    # Save outputs
    if result.final_code:
        output.mkdir(parents=True, exist_ok=True)
        (output / result.final_code.filename).write_text(result.final_code.content, encoding="utf-8")
        if result.test_suite:
            for tf in result.test_suite.test_files:
                (output / tf.filename).write_text(tf.content, encoding="utf-8")
        if result.documentation and result.documentation.readme_section:
            (output / "docs.md").write_text(result.documentation.readme_section, encoding="utf-8")

    render_summary(result, str(output))
